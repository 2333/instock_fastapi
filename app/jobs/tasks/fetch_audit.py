from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_factory


CREATE_FETCH_AUDIT_TABLE_SQL = text(
    """
    CREATE TABLE IF NOT EXISTS data_fetch_audit (
      task_name VARCHAR(64) NOT NULL,
      entity_type VARCHAR(64) NOT NULL,
      entity_key VARCHAR(128) NOT NULL,
      trade_date VARCHAR(10) NOT NULL DEFAULT '',
      status VARCHAR(32) NOT NULL,
      source VARCHAR(32) NULL,
      note TEXT NULL,
      updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
      PRIMARY KEY (task_name, entity_type, entity_key, trade_date)
    )
    """
)


async def ensure_fetch_audit_table(session: AsyncSession) -> None:
    await session.execute(CREATE_FETCH_AUDIT_TABLE_SQL)


async def upsert_fetch_audit(
    session: AsyncSession,
    *,
    task_name: str,
    entity_type: str,
    entity_key: str,
    status: str,
    source: str = "",
    trade_date: str = "",
    note: str = "",
) -> None:
    await ensure_fetch_audit_table(session)
    await session.execute(
        text(
            """
            INSERT INTO data_fetch_audit (
              task_name, entity_type, entity_key, trade_date, status, source, note, updated_at
            )
            VALUES (
              :task_name, :entity_type, :entity_key, :trade_date, :status, :source, :note, NOW()
            )
            ON CONFLICT (task_name, entity_type, entity_key, trade_date)
            DO UPDATE SET
              status = EXCLUDED.status,
              source = EXCLUDED.source,
              note = EXCLUDED.note,
              updated_at = NOW()
            """
        ),
        {
            "task_name": task_name,
            "entity_type": entity_type,
            "entity_key": entity_key,
            "trade_date": trade_date,
            "status": status,
            "source": source,
            "note": note,
        },
    )


async def record_fetch_audit(
    *,
    task_name: str,
    entity_type: str,
    entity_key: str,
    status: str,
    source: str = "",
    trade_date: str = "",
    note: str = "",
) -> None:
    async with async_session_factory() as session:
        await upsert_fetch_audit(
            session,
            task_name=task_name,
            entity_type=entity_type,
            entity_key=entity_key,
            status=status,
            source=source,
            trade_date=trade_date,
            note=note,
        )
        await session.commit()
