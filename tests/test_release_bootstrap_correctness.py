from unittest.mock import AsyncMock, Mock

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

import app.database as database_module
import app.main as main_module


@pytest.mark.asyncio
async def test_init_db_only_checks_connectivity_without_creating_tables(tmp_path, monkeypatch):
    db_file = tmp_path / "bootstrap.sqlite3"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_file}")
    monkeypatch.setattr(database_module, "async_engine", engine)

    try:
        await database_module.init_db()

        async with engine.connect() as conn:
            table_names = (
                (
                    await conn.execute(
                        text("SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name")
                    )
                )
                .scalars()
                .all()
            )

        assert table_names == []
        assert "user_events" not in table_names
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_app_lifespan_uses_non_destructive_bootstrap(monkeypatch):
    init_db = AsyncMock()
    close_db = AsyncMock()
    stop_scheduler = Mock()

    monkeypatch.setattr(main_module, "init_db", init_db)
    monkeypatch.setattr(main_module, "close_db", close_db)
    monkeypatch.setattr(main_module, "stop_scheduler", stop_scheduler)
    monkeypatch.setattr(main_module.settings, "SCHEDULER_ENABLED", False)

    async with main_module.app.router.lifespan_context(main_module.app):
        init_db.assert_awaited_once()
        close_db.assert_not_awaited()

    close_db.assert_awaited_once()
    stop_scheduler.assert_called_once_with()
