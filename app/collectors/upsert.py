from __future__ import annotations

from typing import Any

from sqlalchemy import and_, delete
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session


def upsert_rows(
    session: Session,
    model: type,
    rows: list[dict[str, Any]],
    conflict_cols: list[str],
    update_cols: list[str],
) -> None:
    if not rows:
        return

    bind = session.get_bind()
    dialect = bind.dialect.name if bind is not None else ""
    if dialect == "postgresql":
        stmt = insert(model).values(rows)
        stmt = stmt.on_conflict_do_update(
            index_elements=conflict_cols,
            set_={col: stmt.excluded[col] for col in update_cols},
        )
        session.execute(stmt)
        return

    # Portable path for unit tests (SQLite): delete matching keys then insert.
    for row in rows:
        filters = [getattr(model, col) == row[col] for col in conflict_cols]
        session.execute(delete(model).where(and_(*filters)))
        session.add(model(**row))
