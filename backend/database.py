"""One SQLAlchemy engine per data directory; Alembic owns schema creation."""
from contextlib import contextmanager
from functools import lru_cache
from pathlib import Path
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

DATA = Path(__file__).resolve().parent / 'data'


@lru_cache(maxsize=16)
def engine_for(data_dir=DATA):
    data_dir = Path(data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    engine = create_engine('sqlite:///' + str(data_dir / 'support.sqlite3'),
                           connect_args={'check_same_thread': False, 'timeout': 1})

    @event.listens_for(engine, 'connect')
    def configure(connection, _):
        connection.execute('PRAGMA foreign_keys=ON')
        connection.execute('PRAGMA busy_timeout=1000')
    return engine


@contextmanager
def session_scope(data_dir=DATA, write=False):
    with Session(engine_for(data_dir), expire_on_commit=False) as session:
        if write:
            # Serializes SQLite writers across API processes and the sync worker.
            session.connection().exec_driver_sql('BEGIN IMMEDIATE')
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise


def upgrade(data_dir=DATA):
    from alembic import command
    from alembic.config import Config
    cfg = Config()
    cfg.set_main_option('script_location', str(Path(__file__).resolve().parent / 'migrations'))
    with engine_for(data_dir).begin() as connection:
        cfg.attributes['connection'] = connection
        command.upgrade(cfg, 'head')
