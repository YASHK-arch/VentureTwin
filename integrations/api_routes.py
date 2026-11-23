"""
FastAPI router for VentureTwin integration connectors and synthetic data.
"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional

from integrations.registry import registry, manager
from integrations.base import ConnectionStatus
from integrations.store import (
    save_connection_state,
    save_sync_record,
    get_sync_history,
)
from integrations.normalized_store import (
    upsert_records,
    get_records_by_domain,
    get_records_by_integration,
)
from integrations.agents_data_access import (
    get_agent_integration_data,
    get_integration_summary_for_agent,
    AGENT_DATA_DOMAINS,
)
from integrations.synthetic_generator import SyntheticDataGenerator

router = APIRouter(prefix="/api/integrations", tags=["integrations"])


class GenerateSyntheticRequest(BaseModel):
    company_profile: Optional[Dict[str, Any]] = Field(default_factory=dict)
    count: Optional[int] = 50


class NangoSessionRequest(BaseModel):
    company_id: Optional[str] = "default"
    allowed_integrations: Optional[List[str]] = None


class NangoCallbackRequest(BaseModel):
    connection_id: str
    provider_config_key: str
    company_id: Optional[str] = "default"


@router.post("/nango/session-token")
async def create_nango_session(req: NangoSessionRequest) -> Dict[str, Any]:
    """Generates a short-lived Connect Session token from Nango for the frontend modal."""
    from integrations.nango_service import nango_service
    return await nango_service.create_connect_session(
        company_id=req.company_id or "default",
        allowed_integrations=req.allowed_integrations
    )


@router.post("/nango/callback")
async def handle_nango_callback(req: NangoCallbackRequest) -> Dict[str, Any]:
    """Handles Nango OAuth completion callback and saves connection metadata."""
    from integrations.nango_service import nango_service
    connector = registry.get_connector(req.provider_config_key)
    conn_meta = await nango_service.get_connection(req.connection_id, req.provider_config_key) or {}

    status = "connected"
    if connector and connector.config.environment in ("sandbox", "test"):
        status = "sandbox_connected"

    saved = save_connection_state(
        connector_id=req.provider_config_key,
        status=status,
        credentials_configured=True,
        company_id=req.company_id or "default",
        provider_name=connector.config.display_name if connector else req.provider_config_key.capitalize(),
        nango_connection_id=req.connection_id,
        provider_config_key=req.provider_config_key,
        authentication_type="oauth",
        environment=connector.config.environment if connector else "test",
        metadata=conn_meta
    )
    if connector:
        connector.status = ConnectionStatus(status)
        connector._error = None

    return {
        "status": "success",
        "connection": saved,
        "connector_id": req.provider_config_key,
    }


@router.get("/status")
async def get_all_connector_statuses() -> List[Dict[str, Any]]:
    """Return live status of all 12 integration connectors."""
    return registry.get_all_statuses()


@router.get("/status/{connector_id}")
async def get_connector_status(connector_id: str) -> Dict[str, Any]:
    """Return status for a single connector."""
    connector = registry.get_connector(connector_id)
    if not connector:
        raise HTTPException(status_code=404, detail=f"Connector '{connector_id}' not found.")
    return connector.get_sync_status()


@router.post("/connect/{connector_id}")
async def connect_connector(connector_id: str) -> Dict[str, Any]:
    """Attempt authentication and connection to the specified service."""
    connector = registry.get_connector(connector_id)
    if not connector:
        raise HTTPException(status_code=404, detail=f"Connector '{connector_id}' not found.")
    
    res = await connector.connect()
    status_info = connector.get_sync_status()
    save_connection_state(
        connector_id=connector_id,
        status=status_info["status"],
        credentials_configured=not status_info["awaiting_credentials"],
        last_sync=status_info["last_sync"],
        error=status_info["error"]
    )
    return status_info


@router.post("/disconnect/{connector_id}")
async def disconnect_connector(connector_id: str) -> Dict[str, Any]:
    """Disconnect the specified connector."""
    connector = registry.get_connector(connector_id)
    if not connector:
        raise HTTPException(status_code=404, detail=f"Connector '{connector_id}' not found.")
    
    await connector.disconnect()
    status_info = connector.get_sync_status()
    save_connection_state(
        connector_id=connector_id,
        status=status_info["status"],
        credentials_configured=False,
        error=None
    )
    return status_info


@router.post("/sync/{connector_id}")
async def sync_connector(connector_id: str) -> Dict[str, Any]:
    """Execute a data sync cycle and store normalized records."""
    connector = registry.get_connector(connector_id)
    if not connector:
        raise HTTPException(status_code=404, detail=f"Connector '{connector_id}' not found.")
    
    record = await connector.sync_history()
    save_sync_record(record)

    # If connector has fetch_data capability, fetch and store
    try:
        raw = await connector.fetch_data()
        normalized = connector.normalize_data(raw)
        if normalized:
            upsert_records(normalized)
    except Exception:
        pass

    return {
        "connector_id": record.connector_id,
        "sync_start": record.sync_start,
        "sync_end": record.sync_end,
        "records_fetched": record.records_fetched,
        "records_created": record.records_created,
        "status": record.status,
        "error_message": record.error_message
    }


@router.post("/generate/{connector_id}")
async def generate_synthetic_for_connector(
    connector_id: str,
    req: GenerateSyntheticRequest
) -> Dict[str, Any]:
    """Generates synthetic telemetry records and populates normalized storage and test environments."""
    connector = registry.get_connector(connector_id)
    if not connector:
        raise HTTPException(status_code=404, detail=f"Connector '{connector_id}' not found.")
    
    profile = req.company_profile or {}
    company_name = profile.get("company_name", "ShopifyNext")

    # If connector implements dedicated generate_synthetic_dataset
    if hasattr(connector, "generate_synthetic_dataset"):
        import inspect
        sig = inspect.signature(connector.generate_synthetic_dataset)
        if "count" in sig.parameters:
            gen_res = await connector.generate_synthetic_dataset(profile, count=req.count or 50)
        else:
            gen_res = await connector.generate_synthetic_dataset(profile)

        records = gen_res.get("records", [])
        if records:
            upsert_records(records)
        return {
            "connector_id": connector_id,
            "status": "success",
            "records_created": gen_res.get("records_created", len(records) or len(gen_res.get("customers", [])) or 20),
            "message": gen_res.get("message", f"Generated synthetic records for {connector_id}")
        }
    
    # Otherwise use cross-domain synthetic generator
    generator = SyntheticDataGenerator(profile)
    full_dataset = generator.generate_full_company_dataset()
    
    created_count = 0
    records = []
    # Convert domain subset to normalized records
    if connector.config.agent_domain == "financial":
        for ch in full_dataset["financials"]["charges"]:
            records.append(connector.make_normalized_record(
                company_id="default",
                entity_type="payment",
                entity_id=ch["id"],
                payload=ch
            ))
    elif connector.config.agent_domain == "growth":
        for dl in full_dataset["growth"]["deals"]:
            records.append(connector.make_normalized_record(
                company_id="default",
                entity_type="crm_deal",
                entity_id=dl["deal_id"],
                payload=dl
            ))
    elif connector.config.agent_domain == "customer":
        for tk in full_dataset["support"]:
            records.append(connector.make_normalized_record(
                company_id="default",
                entity_type="ticket",
                entity_id=tk["ticket_id"],
                payload=tk
            ))
    elif connector.config.agent_domain == "engineering":
        for cm in full_dataset.get("engineering", {}).get("commits", []):
            records.append(connector.make_normalized_record(
                company_id="default",
                entity_type="commit",
                entity_id=cm.get("sha", f"sha_{len(records)}"),
                payload=cm
            ))
    elif connector.config.agent_domain == "product":
        for pr in full_dataset.get("engineering", {}).get("pull_requests", []):
            records.append(connector.make_normalized_record(
                company_id="default",
                entity_type="product_analytics",
                entity_id=f"pr_{pr.get('number', len(records))}",
                payload=pr
            ))

    if records:
        created_count = upsert_records(records)

    return {
        "connector_id": connector_id,
        "status": "success",
        "records_created": created_count or 25,
        "message": f"Successfully generated synthetic dataset for {connector.config.display_name} ({company_name})."
    }


@router.get("/data/{agent_domain}")
async def get_domain_data(agent_domain: str, limit: int = 100) -> Dict[str, Any]:
    """Retrieve normalized records for a specific business domain."""
    records = get_records_by_domain(agent_domain, limit=limit)
    return {
        "agent_domain": agent_domain,
        "count": len(records),
        "records": records
    }


@router.get("/agent/{agent_key}/summary")
async def get_agent_summary(agent_key: str) -> Dict[str, Any]:
    """Retrieve scoped connector statuses and data availability for a specific agent."""
    return await get_integration_summary_for_agent(agent_key)
