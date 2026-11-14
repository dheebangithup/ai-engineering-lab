import asyncio
import json
import logging
import socket
from pathlib import Path
from typing import Optional
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
    global _pool
    if _pool is None:
        dsn = normalize_dsn(settings.database_url)
        logger.info("Initializing asyncpg pool for Neon Postgres...")

        # Neon with PgBouncer requires statement_cache_size=0
        _pool = await asyncpg.create_pool(
            dsn=dsn,
            min_size=settings.db_pool_min_size,
            max_size=settings.db_pool_max_size,
            statement_cache_size=settings.db_statement_cache_size,
            max_inactive_connection_lifetime=300.0,
            init=init_connection,
            command_timeout=30.0,
        )
        logger.info("Neon database connection pool established.")
    return _pool


async def close_db_pool() -> None:
    """Closes the connection pool."""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None
        logger.info("Neon database connection pool closed.")


async def run_migrations(migration_sql_path: Optional[str] = None) -> None:
    """Runs DDL schema migrations against Neon using DIRECT_DATABASE_URL or DATABASE_URL."""
    migration_dsn = settings.direct_database_url or settings.database_url
    dsn = normalize_dsn(migration_dsn)
    
    if migration_sql_path is None:
        base_dir = Path(__file__).resolve().parent.parent.parent
        migration_sql_path = str(base_dir / "sql" / "001_init_schema.sql")

    logger.info(f"Applying schema migration from: {migration_sql_path}")
    with open(migration_sql_path, "r", encoding="utf-8") as f:
        sql = f.read()

    # Direct connection for DDL to bypass PgBouncer transaction constraints
    conn = await asyncpg.connect(dsn, statement_cache_size=0)
    try:
        await conn.execute(sql)
        logger.info("Schema migrations applied successfully.")
    finally:
        await conn.close()


def run_migrations_cli() -> None:
    """CLI wrapper for running migrations."""
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_migrations())


if __name__ == "__main__":
    run_migrations_cli()
