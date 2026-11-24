"""
Abstract base class and shared types for all VentureTwin integration connectors.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Literal
from enum import Enum


class ConnectionStatus(str, Enum):
    NOT_CONNECTED = "not_connected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    SYNCING = "syncing"
    ERROR = "error"
    SANDBOX_CONNECTED = "sandbox_connected"
    AWAITING_CREDENTIALS = "awaiting_credentials"


class ProvenanceType(str, Enum):
    REAL_API = "real_api"
    SYNTHETIC_EXTERNAL = "synthetic_external"
    SYNTHETIC_INTERNAL = "synthetic_internal"
    EXTERNAL_RESEARCH = "external_research"
    DERIVED = "derived"


@dataclass
class ConnectorConfig:
    connector_id: str
    display_name: str
    agent_domain: str              # financial, growth, engineering, customer, product, intelligence
    environment: str               # sandbox, test, developer, production, cloud
    credential_env_vars: List[str] # list of env var names required
    supports_write: bool = False
    supports_synthetic_generation: bool = False
    oauth_required: bool = False


@dataclass
class SyncRecord:
    connector_id: str
    sync_start: str
    sync_end: Optional[str]
    records_fetched: int
    records_created: int
    status: str
    error_message: Optional[str] = None


class AbstractConnector(ABC):
    def __init__(self, config: ConnectorConfig):
        self.config = config
        self.status = ConnectionStatus.NOT_CONNECTED
        self._credentials: Dict[str, str] = {}
        self._last_sync: Optional[str] = None
        self._error: Optional[str] = None

    def get_nango_connection(self, company_id: str = "default") -> Optional[Dict[str, Any]]:
        """Check if an active Nango connection exists in persistent store."""
        try:
            from integrations.store import get_connection_state
            conn = get_connection_state(self.config.connector_id, company_id=company_id)
            if conn and conn.get("nango_connection_id") and conn.get("connection_status") in ("connected", "sandbox_connected"):
                return conn
            return None
        except Exception:
            return None

    def load_credentials(self, company_id: str = "default") -> bool:
        """
        Load credentials from Nango connection or environment variables.
        Returns True if authenticated via Nango or all required direct env vars are present.
        """
        import os
        # Check active Nango connection first
        nango_conn = self.get_nango_connection(company_id=company_id)
        if nango_conn:
            self.status = ConnectionStatus.CONNECTED if self.config.environment != "sandbox" else ConnectionStatus.SANDBOX_CONNECTED
            self._error = None
            return True

        self._credentials = {}
        missing = []
        from pathlib import Path
        env_file = Path(".env")
        if env_file.exists():
            try:
                for line in env_file.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if "=" in line and not line.startswith("#"):
                        k, v = line.split("=", 1)
                        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
            except Exception:
                pass

        for var in self.config.credential_env_vars:
            val = os.getenv(var)
            if val:
                self._credentials[var] = val
            else:
                missing.append(var)
        if missing:
            self.status = ConnectionStatus.AWAITING_CREDENTIALS
            self._error = f"Missing env vars: {', '.join(missing)}"
            return False
        return True

    @abstractmethod
    async def connect(self) -> Dict[str, Any]: ...

    @abstractmethod
    async def disconnect(self) -> None: ...

    @abstractmethod
    async def validate_connection(self) -> bool: ...

    @abstractmethod
    async def fetch_data(self, entity_types: Optional[List[str]] = None, since: Optional[str] = None) -> List[Dict[str, Any]]: ...

    @abstractmethod
    def normalize_data(self, raw: List[Dict[str, Any]]) -> List[Dict[str, Any]]: ...

    async def sync_history(self, since: Optional[str] = None) -> SyncRecord:
        """Full sync cycle: fetch + normalize + return record."""
        self.status = ConnectionStatus.SYNCING
        start = datetime.now(timezone.utc).isoformat()
        try:
            raw = await self.fetch_data(since=since)
            normalized = self.normalize_data(raw)
            if normalized:
                try:
                    from integrations.normalized_store import upsert_records
                    upsert_records(normalized)
                except Exception:
                    pass
            self._last_sync = datetime.now(timezone.utc).isoformat()
            self.status = ConnectionStatus.CONNECTED
            return SyncRecord(
                connector_id=self.config.connector_id,
                sync_start=start,
                sync_end=self._last_sync,
                records_fetched=len(raw),
                records_created=len(normalized),
                status="success"
            )
        except Exception as e:
            self.status = ConnectionStatus.ERROR
            self._error = str(e)
            return SyncRecord(
                connector_id=self.config.connector_id,
                sync_start=start,
                sync_end=datetime.now(timezone.utc).isoformat(),
                records_fetched=0,
                records_created=0,
                status="error",
                error_message=str(e)
            )

    def get_sync_status(self) -> Dict[str, Any]:
        return {
            "connector_id": self.config.connector_id,
            "display_name": self.config.display_name,
            "status": self.status.value,
            "environment": self.config.environment,
            "last_sync": self._last_sync,
            "error": self._error,
            "agent_domain": self.config.agent_domain,
            "supports_write": self.config.supports_write,
            "supports_synthetic_generation": self.config.supports_synthetic_generation,
            "awaiting_credentials": self.status == ConnectionStatus.AWAITING_CREDENTIALS,
            "missing_env_vars": [v for v in self.config.credential_env_vars if not __import__('os').getenv(v)]
        }

    def make_normalized_record(
        self,
        company_id: str,
        entity_type: str,
        entity_id: str,
        payload: Dict[str, Any],
        provenance_type: ProvenanceType = ProvenanceType.REAL_API
    ) -> Dict[str, Any]:
        return {
            "company_id": company_id,
            "integration": self.config.connector_id,
            "agent_domain": self.config.agent_domain,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "provenance": {
                "type": provenance_type.value,
                "source": "venturetwin_connector" if provenance_type == ProvenanceType.REAL_API else "venturetwin_generator"
            },
            "payload": payload
        }
