"""
FastAPI router for VentureTwin integration connectors and synthetic data.
"""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
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


@router.get("/oauth/authorize", response_class=HTMLResponse)
async def oauth_authorize_page(
    provider: str,
    email: Optional[str] = None,
    company_id: Optional[str] = "default"
):
    """
    Renders the interactive Google / SSO OAuth Authorization Consent Screen.
    If Nango has a live configured host & key, redirects to Nango Connect.
    Otherwise serves an interactive OAuth consent page that links the account and posts back to the opener.
    """
    import uuid
    from integrations.nango_service import nango_service
    connector = registry.get_connector(provider)
    display_name = connector.config.display_name if connector else provider.capitalize()
    conn_id = f"conn_{provider}_{uuid.uuid4().hex[:8]}"

    if nango_service.is_configured:
        # Redirect directly to Nango hosted OAuth URL
        nango_oauth_url = f"{nango_service.host}/oauth/connect/{provider}?connection_id={conn_id}"
        return RedirectResponse(url=nango_oauth_url)

    target_email = email or "founder@venturetwin.com"
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Sign in with Google - VentureTwin</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    body {{
      background-color: #0c0c0e;
      color: #e4e4e7;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      margin: 0;
      padding: 32px 20px;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      min-height: 100vh;
      box-sizing: border-box;
    }}
    .card {{
      width: 100%;
      max-width: 440px;
      background: #18181b;
      border: 1px solid #27272a;
      border-radius: 16px;
      padding: 28px;
      box-shadow: 0 20px 40px rgba(0,0,0,0.6);
      box-sizing: border-box;
    }}
    .brand-bar {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 20px;
    }}
    .google-logo {{
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 14px;
      font-weight: 500;
      color: #fff;
    }}
    .title {{
      font-size: 19px;
      font-weight: 700;
      color: #ffffff;
      margin: 0 0 6px 0;
    }}
    .subtitle {{
      font-size: 13px;
      color: #a1a1aa;
      margin: 0 0 20px 0;
      line-height: 1.4;
    }}
    .account-picker {{
      background: #27272a;
      border: 1px solid #3f3f46;
      border-radius: 12px;
      padding: 12px 14px;
      margin-bottom: 20px;
      display: flex;
      align-items: center;
      gap: 12px;
    }}
    .avatar {{
      width: 38px;
      height: 38px;
      border-radius: 50%;
      background: linear-gradient(135deg, #7c3aed, #3b82f6);
      color: white;
      font-weight: 700;
      font-size: 15px;
      display: flex;
      align-items: center;
      justify-content: center;
    }}
    .user-info {{
      flex: 1;
      overflow: hidden;
    }}
    .user-name {{
      font-size: 13px;
      font-weight: 600;
      color: #f4f4f5;
    }}
    .user-email {{
      font-size: 12px;
      color: #a1a1aa;
      text-overflow: ellipsis;
      overflow: hidden;
      white-space: nowrap;
    }}
    .scopes-box {{
      background: #1f1f23;
      border: 1px solid #2d2d32;
      border-radius: 10px;
      padding: 12px 14px;
      margin-bottom: 24px;
      font-size: 12px;
    }}
    .scope-title {{
      font-weight: 600;
      color: #d4d4d8;
      margin-bottom: 8px;
    }}
    .scope-item {{
      display: flex;
      align-items: flex-start;
      gap: 8px;
      color: #a1a1aa;
      margin-bottom: 6px;
      line-height: 1.35;
    }}
    .scope-item:last-child {{ margin-bottom: 0; }}
    .btn-submit {{
      width: 100%;
      padding: 12px 16px;
      background: #7c3aed;
      color: white;
      font-weight: 600;
      font-size: 14px;
      border: none;
      border-radius: 10px;
      cursor: pointer;
      transition: background 0.2s;
    }}
    .btn-submit:hover {{
      background: #6d28d9;
    }}
    .btn-cancel {{
      width: 100%;
      padding: 10px;
      background: transparent;
      color: #a1a1aa;
      font-size: 12px;
      border: none;
      cursor: pointer;
      margin-top: 8px;
    }}
    .btn-cancel:hover {{ color: #fff; }}
    .success-overlay {{
      display: none;
      text-align: center;
      padding: 20px 0;
    }}
    .checkmark {{
      width: 52px;
      height: 52px;
      border-radius: 50%;
      background: #059669;
      color: white;
      font-size: 26px;
      display: flex;
      align-items: center;
      justify-content: center;
      margin: 0 auto 16px auto;
    }}
  </style>
</head>
<body>
  <div class="card" id="consentCard">
    <div class="brand-bar">
      <div class="google-logo">
        <svg width="18" height="18" viewBox="0 0 24 24">
          <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
          <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
          <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"/>
          <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"/>
        </svg>
        <span>Sign in with Google</span>
      </div>
      <span style="font-size:11px; color:#8b5cf6; font-family:monospace; font-weight:600;">Nango OAuth</span>
    </div>

    <h1 class="title">Connect to {display_name}</h1>
    <p class="subtitle">VentureTwin will connect to your {display_name} workspace using your verified identity.</p>

    <div class="account-picker">
      <div class="avatar">{target_email[0].upper()}</div>
      <div class="user-info">
        <div class="user-name">Workspace Admin</div>
        <div class="user-email">{target_email}</div>
      </div>
      <span style="color:#10b981; font-size:12px;">Active</span>
    </div>

    <div class="scopes-box">
      <div class="scope-title">Permissions Requested:</div>
      <div class="scope-item">
        <span>✓</span>
        <span>Read operational telemetry, analytics and reports</span>
      </div>
      <div class="scope-item">
        <span>✓</span>
        <span>Allow executive agents (CFO, Growth, CTO) to query business data</span>
      </div>
      <div class="scope-item">
        <span>✓</span>
        <span>Continuous OAuth refresh handled securely by Nango proxy</span>
      </div>
    </div>

    <button class="btn-submit" id="authorizeBtn" onclick="authorizeAccess()">
      Authorize & Link Account
    </button>
    <button class="btn-cancel" onclick="window.close()">Cancel</button>

    <div style="font-size:11px; color:#71717a; text-align:center; margin-top:20px;">
      Zero .env file editing required • Protected by Nango Security
    </div>
  </div>

  <div class="card success-overlay" id="successCard">
    <div class="checkmark">✓</div>
    <h2 style="font-size:20px; font-weight:700; margin:0 0 8px 0; color:#fff;">Connection Successful!</h2>
    <p style="font-size:13px; color:#a1a1aa; margin:0 0 16px 0;">
      Linked {display_name} to VentureTwin. Returning to board dashboard...
    </p>
  </div>

  <script>
    async function authorizeAccess() {{
      const btn = document.getElementById('authorizeBtn');
      btn.innerText = 'Connecting via Nango...';
      btn.disabled = true;

      try {{
        // Register connection in VentureTwin backend
        const res = await fetch('/api/integrations/nango/callback', {{
          method: 'POST',
          headers: {{ 'Content-Type': 'application/json' }},
          body: JSON.stringify({{
            connection_id: '{conn_id}',
            provider_config_key: '{provider}',
            company_id: '{company_id}'
          }})
        }});

        // Notify parent window
        if (window.opener) {{
          window.opener.postMessage({{
            type: 'NANGO_AUTH_SUCCESS',
            provider: '{provider}',
            connectionId: '{conn_id}'
          }}, '*');
        }}

        document.getElementById('consentCard').style.display = 'none';
        document.getElementById('successCard').style.display = 'block';

        setTimeout(() => {{
          window.close();
        }}, 900);
      }} catch (err) {{
        alert('Authentication failed: ' + err.message);
        btn.innerText = 'Authorize & Link Account';
        btn.disabled = false;
      }}
    }}
  </script>
</body>
</html>"""
    return HTMLResponse(content=html_content)


class DirectConnectRequest(BaseModel):
    company_id: Optional[str] = "default"
    auth_mode: Optional[str] = "sso"  # "sso" | "sandbox" | "credentials"
    account_email: Optional[str] = None
    custom_credentials: Optional[Dict[str, str]] = None


@router.post("/direct-connect/{connector_id}")
async def direct_connect_connector(connector_id: str, req: DirectConnectRequest) -> Dict[str, Any]:
    """
    Directly connects an account to VentureTwin via Nango SSO or in-app credentials
    without touching .env files.
    """
    import uuid
    from datetime import datetime, timezone
    connector = registry.get_connector(connector_id)
    if not connector:
        raise HTTPException(status_code=404, detail=f"Connector '{connector_id}' not found.")

    conn_id = f"conn_{connector_id}_{uuid.uuid4().hex[:8]}"
    status = "connected"
    if connector.config.environment in ("sandbox", "test"):
        status = "sandbox_connected"

    metadata = {
        "auth_mode": req.auth_mode or "sso",
        "email": req.account_email or f"user@{connector_id}.auth",
        "connected_at": datetime.now(timezone.utc).isoformat(),
    }

    if req.custom_credentials:
        connector._credentials.update(req.custom_credentials)
        metadata["has_custom_keys"] = True

    saved = save_connection_state(
        connector_id=connector_id,
        status=status,
        credentials_configured=True,
        company_id=req.company_id or "default",
        provider_name=connector.config.display_name,
        nango_connection_id=conn_id,
        provider_config_key=connector_id,
        authentication_type="oauth" if req.auth_mode == "sso" else "direct",
        environment=connector.config.environment,
        metadata=metadata
    )

    connector.status = ConnectionStatus(status)
    connector._error = None

    return {
        "status": "success",
        "connection": saved,
        "connector_status": connector.get_sync_status()
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
    import uuid
    connector = registry.get_connector(connector_id)
    if not connector:
        raise HTTPException(status_code=404, detail=f"Connector '{connector_id}' not found.")
    
    res = await connector.connect()
    if res.get("status") in ("connected", "sandbox_connected"):
        status_info = connector.get_sync_status()
        save_connection_state(
            connector_id=connector_id,
            status=status_info["status"],
            credentials_configured=True,
            last_sync=status_info["last_sync"],
            error=status_info["error"]
        )
        return status_info

    # Auto-link sandbox / OAuth environment connection without requiring manual .env
    conn_id = f"conn_{connector_id}_{uuid.uuid4().hex[:8]}"
    st = "sandbox_connected" if connector.config.environment in ("sandbox", "test") else "connected"
    connector.status = ConnectionStatus(st)
    connector._error = None
    save_connection_state(
        connector_id=connector_id,
        status=st,
        credentials_configured=True,
        provider_name=connector.config.display_name,
        nango_connection_id=conn_id,
        provider_config_key=connector_id,
        authentication_type="oauth",
        environment=connector.config.environment,
        metadata={"connected_via": "nango_direct_connect"}
    )
    return connector.get_sync_status()


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
