import pytest
from unittest.mock import AsyncMock, patch
from strata.neon_control import extract_endpoint_id, maybe_suspend_neon_compute, suspend_neon_compute
from strata.config import settings


def test_extract_endpoint_id():
    pooled_url = "postgresql://neondb_owner:pass@ep-divine-hill-a1p3fmik-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require"
    assert extract_endpoint_id(pooled_url) == "ep-divine-hill-a1p3fmik"

    direct_url = "postgresql://neondb_owner:pass@ep-divine-hill-a1p3fmik.ap-southeast-1.aws.neon.tech/neondb?sslmode=require"
    assert extract_endpoint_id(direct_url) == "ep-divine-hill-a1p3fmik"

    custom_url = "postgresql://user:pass@ep-cool-cloud-123456-pooler.us-east-2.neon.tech/db"
    assert extract_endpoint_id(custom_url) == "ep-cool-cloud-123456"

    invalid_url = "postgresql://localhost:5432/strata"
    assert extract_endpoint_id(invalid_url) is None


@pytest.mark.asyncio
async def test_maybe_suspend_neon_keep_alive_true():
    """When NEON_KEEP_ALIVE=True, suspend should NOT be called."""
    with patch("strata.neon_control.settings.neon_keep_alive", True):
        with patch("strata.neon_control.suspend_neon_compute", new_callable=AsyncMock) as mock_suspend:
            await maybe_suspend_neon_compute()
            mock_suspend.assert_not_called()


@pytest.mark.asyncio
async def test_maybe_suspend_neon_keep_alive_false():
    """When NEON_KEEP_ALIVE=False (default), suspend should be called."""
    with patch("strata.neon_control.settings.neon_keep_alive", False):
        with patch("strata.neon_control.suspend_neon_compute", new_callable=AsyncMock) as mock_suspend:
            mock_suspend.return_value = True
            await maybe_suspend_neon_compute()
            mock_suspend.assert_called_once()


@pytest.mark.asyncio
async def test_suspend_without_api_key():
    """When NEON_API_KEY is not set, gracefully skip without error."""
    with patch("strata.neon_control.settings.neon_api_key", None):
        result = await suspend_neon_compute()
        assert result is False
