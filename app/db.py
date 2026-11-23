from pathlib import Path
from typing import Generator
from sqlmodel import Session, SQLModel, create_engine
from .config import BASE_DIR, settings

# Ensure data directory exists
data_dir = BASE_DIR / "data"
data_dir.mkdir(parents=True, exist_ok=True)

connect_args = {}
if settings.database_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    settings.database_url,
    echo=False,
    connect_args=connect_args,
)


def init_db() -> None:
    """Create all SQLModel database tables if they do not exist."""
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    """Dependency for yielding database sessions."""
    with Session(engine) as session:
        yield session
