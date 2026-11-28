import asyncio
import json
import logging
import socket
import ssl
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import urlparse, parse_qs, urlencode

# Resilient DNS fallback for Neon serverless PostgreSQL when ISP DNS drops/refuses AWS domains
_orig_getaddrinfo = socket.getaddrinfo
def _resilient_getaddrinfo(host, port, *args, **kwargs):
    try:
        return _orig_getaddrinfo(host, port, *args, **kwargs)
    except (socket.gaierror, OSError):
        if host and "neon.tech" in str(host):
            # Fallback to verified Neon AWS IPs (ap-southeast-1)
            for fallback_ip in ["13.228.46.236", "52.220.170.93", "13.228.184.177"]:
                return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (fallback_ip, port))]
        raise

socket.getaddrinfo = _resilient_getaddrinfo

import asyncpg
from strata.config import settings

logger = logging.getLogger("strata.db")

_pool: Optional[asyncpg.Pool] = None
_pool_loop: Optional[asyncio.AbstractEventLoop] = None


def normalize_dsn(dsn: str) -> str:
    """Ensures DSN is compatible with asyncpg, particularly handling sslmode for Neon."""
    parsed = urlparse(dsn)
    qs = parse_qs(parsed.query)

    # Remove channel_binding if present as asyncpg does not accept it as a kwarg
    qs.pop("channel_binding", None)

    # asyncpg expects ssl=require or handles standard postgresql://
    # If sslmode=require is in query, ensure asyncpg understands it
    if "sslmode" in qs:
        mode = qs.pop("sslmode")[0]
        if mode in ("require", "verify-ca", "verify-full"):
            qs["ssl"] = ["require"]

    new_query = urlencode(qs, doseq=True)
    return parsed._replace(query=new_query).geturl()


def resolve_neon_host(hostname: str) -> str:
    """Resolves Neon hostname using public DNS (8.8.8.8, 1.1.1.1) when local ISP DNS fails/refuses."""
    for dns_server in ["8.8.8.8", "1.1.1.1"]:
        try:
            out = subprocess.check_output(
                ["dig", f"@{dns_server}", hostname, "+short", "+time=2"],
                stderr=subprocess.DEVNULL,
            ).decode().strip()
            for line in out.splitlines():
                line = line.strip()
                if line and not line.endswith("."):
                    try:
                        socket.inet_aton(line)
                        return line
                    except OSError:
                        pass
        except Exception:
            pass
    # Known resilient Neon AWS ap-southeast-1 pooler IPs
    return "13.228.46.236"


def get_connection_kwargs(dsn_str: str) -> Dict[str, Any]:
    """Parses DSN and handles DNS resolution fallback for Neon when local ISP DNS fails."""
    parsed = urlparse(dsn_str)
    hostname = parsed.hostname or "localhost"
    port = parsed.port or 5432

    resolved_ip = None
    if "neon.tech" in hostname:
        try:
            _orig_getaddrinfo(hostname, port)
        except (socket.gaierror, OSError):
            resolved_ip = resolve_neon_host(hostname)
            logger.info(f"System DNS failed for {hostname}; connecting via resolved IP {resolved_ip} with Neon SNI.")

    if resolved_ip:
        endpoint_id = hostname.split(".")[0].replace("-pooler", "")
        ssl_ctx = ssl.create_default_context()
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl.CERT_NONE
        return {
            "host": resolved_ip,
            "port": port,
            "user": parsed.username,
            "password": parsed.password,
            "database": parsed.path.lstrip("/"),
            "server_settings": {"options": f"endpoint={endpoint_id}"},
            "ssl": ssl_ctx,
        }

    return {"dsn": normalize_dsn(dsn_str)}


async def init_connection(conn: asyncpg.Connection) -> None:
    """Configures connection codecs for JSON/JSONB and transaction settings."""
    await conn.set_type_codec(
        "jsonb",
        encoder=json.dumps,
        decoder=json.loads,
        schema="pg_catalog"
    )
    await conn.set_type_codec(
        "json",
        encoder=json.dumps,
        decoder=json.loads,
        schema="pg_catalog"
    )


async def get_db_pool() -> asyncpg.Pool:
    """Returns the singleton asyncpg connection pool optimized for Neon Serverless."""
    global _pool, _pool_loop
    try:
        curr_loop = asyncio.get_running_loop()
    except RuntimeError:
        curr_loop = None

    if _pool is None or _pool_loop != curr_loop or (hasattr(_pool, "_loop") and _pool._loop.is_closed()):
        conn_kwargs = get_connection_kwargs(settings.database_url)
        logger.info("Initializing asyncpg pool for Neon Postgres...")

        # Neon with PgBouncer requires statement_cache_size=0
        try:
            _pool = await asyncpg.create_pool(
                **conn_kwargs,
                min_size=settings.db_pool_min_size,
                max_size=settings.db_pool_max_size,
                statement_cache_size=settings.db_statement_cache_size,
                max_inactive_connection_lifetime=300.0,
                init=init_connection,
                command_timeout=30.0,
            )
            _pool_loop = curr_loop
            logger.info("Neon database connection pool established.")
        except Exception as exc:
            parsed = urlparse(settings.database_url)
            host = parsed.hostname or "unknown"
            port = parsed.port or 5432
            logger.error(
                f"Failed to connect to PostgreSQL database at {host}:{port}. "
                f"Please ensure DATABASE_URL is set in your environment and points to an active Neon Postgres instance. "
                f"Details: {exc}"
            )
            raise
    return _pool


async def close_db_pool() -> None:
    """Closes the connection pool."""
    global _pool, _pool_loop
    if _pool is not None:
        try:
            await _pool.close()
        except Exception:
            pass
        _pool = None
        _pool_loop = None
        logger.info("Neon database connection pool closed.")


def resolve_migration_sql_path(migration_sql_path: Optional[str] = None) -> str:
    """Resolves 001_init_schema.sql across both editable checkouts and packaged wheel installs."""
    if migration_sql_path is not None:
        return migration_sql_path
    pkg_sql = Path(__file__).resolve().parent / "sql" / "001_init_schema.sql"
    if pkg_sql.exists():
        return str(pkg_sql)
    repo_sql = Path(__file__).resolve().parent.parent.parent / "sql" / "001_init_schema.sql"
    return str(repo_sql)


async def run_migrations(migration_sql_path: Optional[str] = None) -> None:
    """Runs DDL schema migrations against Neon using DIRECT_DATABASE_URL or DATABASE_URL."""
    migration_dsn = settings.direct_database_url or settings.database_url
    conn_kwargs = get_connection_kwargs(migration_dsn)
    resolved_path = resolve_migration_sql_path(migration_sql_path)

    logger.info(f"Applying schema migration from: {resolved_path}")
    with open(resolved_path, "r", encoding="utf-8") as f:
        sql = f.read()

    # Direct connection for DDL to bypass PgBouncer transaction constraints
    conn = await asyncpg.connect(**conn_kwargs, statement_cache_size=0)
    try:
        await conn.execute(sql)
        logger.info("Schema migrations applied successfully.")
    finally:
        await conn.close()


async def ensure_db_ready_and_migrate(
    auto_migrate: bool = False,
    max_attempts: int = 10,
    retry_delay_seconds: float = 2.0,
) -> None:
    """Waits for Postgres availability (helpful during Docker cold start) and runs idempotent migrations if enabled."""
    last_exc: Optional[Exception] = None
    for attempt in range(1, max_attempts + 1):
        try:
            if auto_migrate:
                await run_migrations()
            pool = await get_db_pool()
            async with pool.acquire() as conn:
                await conn.fetchval("SELECT 1;")
            return
        except Exception as exc:
            last_exc = exc
            if attempt < max_attempts:
                logger.warning(
                    f"Database not ready (attempt {attempt}/{max_attempts}): {exc}. Retrying in {retry_delay_seconds}s..."
                )
                await asyncio.sleep(retry_delay_seconds)
    raise RuntimeError(f"Database failed to become ready after {max_attempts} attempts: {last_exc}")


def run_migrations_cli() -> None:
    """CLI wrapper for running migrations."""
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_migrations())


if __name__ == "__main__":
    run_migrations_cli()
