import logging
import re
from typing import Optional
from urllib.parse import urlparse
import httpx
from strata.config import settings

logger = logging.getLogger("strata.neon_control")

_cached_project_id: Optional[str] = None


def extract_endpoint_id(database_url: str) -> Optional[str]:
    """Extracts the endpoint ID (e.g. ep-divine-hill-a1p3fmik) from the Neon connection URL."""
    try:
        parsed = urlparse(database_url)
        host = parsed.hostname or ""
        match = re.match(r"^(ep-[a-zA-Z0-9-]+?)(?:-pooler)?\.", host)
        if match:
            return match.group(1)
    except Exception as e:
        logger.debug(f"Failed to extract endpoint_id from database_url: {e}")
    return None


async def resolve_project_id(api_key: str, endpoint_id: str) -> Optional[str]:
    """Resolves project_id by querying the Neon API v2 or reading from project-scoped key responses."""
    global _cached_project_id
    if settings.neon_project_id:
        return settings.neon_project_id
    if _cached_project_id:
        return _cached_project_id

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                "https://console.neon.tech/api/v2/projects",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Accept": "application/json",
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                projects = data.get("projects", [])
                for proj in projects:
                    proj_id = proj.get("id")
                    ep_resp = await client.get(
                        f"https://console.neon.tech/api/v2/projects/{proj_id}/endpoints",
                        headers={"Authorization": f"Bearer {api_key}"},
                    )
                    if ep_resp.status_code == 200:
                        endpoints = ep_resp.json().get("endpoints", [])
                        for ep in endpoints:
                            if ep.get("id") == endpoint_id:
                                _cached_project_id = proj_id
                                logger.info(f"Discovered Neon project_id: {proj_id} for endpoint: {endpoint_id}")
                                return proj_id
            elif resp.status_code == 404 or resp.status_code == 403:
                # If key is project-scoped, extract subject_project_id from message
                err_text = resp.text
                match = re.search(r'subject_project_id:\"([a-zA-Z0-9_-]+)\"', err_text)
                if match:
                    scoped_id = match.group(1)
                    _cached_project_id = scoped_id
                    logger.info(f"Resolved project-scoped project_id: {scoped_id}")
                    return scoped_id
    except Exception as e:
        logger.warning(f"Failed to auto-resolve Neon project_id: {e}")
    return None


async def suspend_neon_compute() -> bool:
    """Hits the Neon API v2 suspend endpoint to immediately suspend compute and save cost."""
    api_key = settings.neon_api_key
    if not api_key:
        logger.debug("NEON_API_KEY not set; skipping compute suspension.")
        return False

    endpoint_id = settings.neon_endpoint_id or extract_endpoint_id(settings.database_url)
    if not endpoint_id:
        logger.warning("Could not determine Neon endpoint_id from configuration or DATABASE_URL.")
        return False

    project_id = await resolve_project_id(api_key, endpoint_id)
    if not project_id:
        logger.warning(f"Could not resolve project_id for Neon endpoint {endpoint_id}.")
        return False

    url = f"https://console.neon.tech/api/v2/projects/{project_id}/endpoints/{endpoint_id}/suspend"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                url,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
            )
            if resp.status_code in (200, 201, 202):
                logger.info(f"Successfully requested Neon compute suspend for endpoint {endpoint_id}.")
                return True
            else:
                logger.warning(f"Neon compute suspend returned status {resp.status_code}: {resp.text}")
                return False
    except Exception as exc:
        logger.warning(f"Error calling Neon compute suspend API: {exc}")
        return False


async def maybe_suspend_neon_compute() -> None:
    """Suspends Neon compute if NEON_KEEP_ALIVE is False (default) and NEON_API_KEY is configured."""
    if settings.neon_keep_alive:
        logger.debug("NEON_KEEP_ALIVE=true; keeping compute instance active.")
        return

    await suspend_neon_compute()
