"""Database session and lightweight schema upkeep.

SQLite is the default store, so `create_all` cannot add columns to a table
that already exists. `_ensure_columns` performs the minimal ALTER TABLE needed
to keep an existing database in step with the models. It is idempotent and
only runs when the database file already contains the table.
"""
import logging

from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.database.models import Base

logger = logging.getLogger("jarvis.db")

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False, "timeout": 30},
    pool_pre_ping=False,
)


@event.listens_for(engine, "connect")
def _tune_sqlite(dbapi_connection, _record):
    """WAL mode keeps reads fast while the app writes in the background."""
    try:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA busy_timeout=30000")
        cursor.execute("PRAGMA cache_size=-20000")
        cursor.close()
    except Exception as exc:  # noqa: BLE001
        logger.warning("could not tune sqlite pragmas: %s", exc)


SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base.metadata.create_all(bind=engine)


def _ensure_columns() -> None:
    """Add any model column that the live database is missing."""
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    for table in Base.metadata.sorted_tables:
        if table.name not in existing_tables:
            continue
        present = {c["name"] for c in inspector.get_columns(table.name)}
        for column in table.columns:
            if column.name in present:
                continue
            ddl = _column_ddl(table.name, column)
            if not ddl:
                continue
            try:
                with engine.begin() as conn:
                    conn.execute(text(ddl))
                logger.info("schema: added %s.%s", table.name, column.name)
            except Exception as exc:  # noqa: BLE001
                logger.warning("schema: could not add %s.%s (%s)", table.name, column.name, exc)


def _column_ddl(table_name: str, column) -> str | None:
    try:
        col_type = column.type.compile(dialect=engine.dialect)
    except Exception:  # noqa: BLE001
        return None
    if column.default is not None and getattr(column.default, "is_scalar", False):
        default = column.default.arg
        if isinstance(default, str):
            escaped = default.replace("'", "''")
            return f"ALTER TABLE {table_name} ADD COLUMN {column.name} {col_type} DEFAULT '{escaped}'"
        if isinstance(default, bool):
            return f"ALTER TABLE {table_name} ADD COLUMN {column.name} {col_type} DEFAULT {1 if default else 0}"
        if isinstance(default, (int, float)):
            return f"ALTER TABLE {table_name} ADD COLUMN {column.name} {col_type} DEFAULT {default}"
    return f"ALTER TABLE {table_name} ADD COLUMN {column.name} {col_type}"


_ensure_columns()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
