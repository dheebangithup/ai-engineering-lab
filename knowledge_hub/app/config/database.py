from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session, DeclarativeBase
from knowledge_hub.app.config import app_settings
# Example PostgreSQL connection string

# Create engine
engine = create_engine(
    app_settings.POSTGRES_URL,
    echo=False,              # Logs SQL queries (disable in production)
    pool_size=10,           # Connection pool size
    max_overflow=20,        # Extra connections beyond pool_size
    pool_timeout=30,        # Timeout for getting a connection
    pool_recycle=1800       # Recycle connections every 30 minutes
)

# Session factory
SessionLocal = scoped_session(
    sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine
    )
)

class Base(DeclarativeBase):
    pass

# Dependency for FastAPI or other frameworks
'''
useage
db = SessionLocal()
Session = Depends(get_db)) in fastpai controller
'''
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
