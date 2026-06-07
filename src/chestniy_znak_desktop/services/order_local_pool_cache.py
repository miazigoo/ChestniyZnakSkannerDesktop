"""SQLite-кэш локального пула кодов заказов для Desktop."""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path

from chestniy_znak_desktop.api.models.orders import (
    LocalCodePoolDto,
    LocalCodePoolPageDto,
    LocalPoolCodeDto,
    WorkOrderDto,
)


class OrderLocalPoolCache:
    """Хранит snapshot кодов заказа для local-first упаковки."""

    def __init__(self, db_path: Path) -> None:
        """Создает кэш и применяет схему."""

        self._db_path = db_path
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._migrate()

    def save_page(self, page: LocalCodePoolPageDto) -> None:
        """Сохраняет страницу local-pool, полученную от backend."""

        pool = page.data
        now = int(time.time())
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO local_orders (
                    order_id, plant_id, supplier_id, order_number, external_number,
                    status, scan_required, planned_date, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(order_id) DO UPDATE SET
                    plant_id = excluded.plant_id,
                    supplier_id = excluded.supplier_id,
                    order_number = excluded.order_number,
                    external_number = excluded.external_number,
                    status = excluded.status,
                    scan_required = excluded.scan_required,
                    planned_date = excluded.planned_date,
                    updated_at = excluded.updated_at
                """,
                (
                    pool.order.id,
                    pool.order.plant_id,
                    pool.order.supplier_id,
                    pool.order.order_number,
                    pool.order.external_number,
                    pool.order.status,
                    int(pool.order.scan_required),
                    pool.order.planned_date,
                    now,
                ),
            )
            connection.executemany(
                """
                INSERT INTO local_order_codes (
                    order_id, code, remote_code_id, status, order_line_id,
                    package_unit_id, package_code, package_status,
                    package_closed_at, remote_updated_at, synced_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(order_id, code) DO UPDATE SET
                    remote_code_id = excluded.remote_code_id,
                    status = excluded.status,
                    order_line_id = excluded.order_line_id,
                    package_unit_id = excluded.package_unit_id,
                    package_code = excluded.package_code,
                    package_status = excluded.package_status,
                    package_closed_at = excluded.package_closed_at,
                    remote_updated_at = excluded.remote_updated_at,
                    synced_at = excluded.synced_at
                """,
                [
                    (
                        pool.order.id,
                        code.code,
                        code.id,
                        code.status,
                        code.order_line_id,
                        code.package_unit_id,
                        code.package_code,
                        code.package_status,
                        code.package_closed_at,
                        code.updated_at,
                        now,
                    )
                    for code in pool.codes
                ],
            )

    def load_page(self, order_id: str, *, limit: int, offset: int) -> LocalCodePoolPageDto | None:
        """Возвращает страницу из SQLite или `None`, если заказа нет в кэше."""

        with self._connect() as connection:
            order_row = connection.execute(
                """
                SELECT order_id, plant_id, supplier_id, order_number, external_number,
                       status, scan_required, planned_date
                FROM local_orders
                WHERE order_id = ?
                """,
                (order_id,),
            ).fetchone()
            if order_row is None:
                return None
            total = int(
                connection.execute(
                    "SELECT COUNT(*) FROM local_order_codes WHERE order_id = ?",
                    (order_id,),
                ).fetchone()[0]
            )
            rows = connection.execute(
                """
                SELECT remote_code_id, code, status, order_line_id, package_unit_id,
                       package_code, package_status, package_closed_at, remote_updated_at
                FROM local_order_codes
                WHERE order_id = ?
                ORDER BY rowid ASC
                LIMIT ? OFFSET ?
                """,
                (order_id, limit, offset),
            ).fetchall()

        next_offset = offset + len(rows)
        order = WorkOrderDto(
            id=str(order_row["order_id"]),
            plant_id=str(order_row["plant_id"]),
            supplier_id=str(order_row["supplier_id"]),
            order_number=str(order_row["order_number"]),
            external_number=order_row["external_number"],
            status=str(order_row["status"]),
            scan_required=bool(order_row["scan_required"]),
            planned_date=order_row["planned_date"],
            lines=[],
        )
        return LocalCodePoolPageDto(
            data=LocalCodePoolDto(
                order=order,
                codes=[
                    LocalPoolCodeDto(
                        id=str(row["remote_code_id"] or ""),
                        code=str(row["code"]),
                        status=str(row["status"]),
                        order_line_id=row["order_line_id"],
                        package_unit_id=row["package_unit_id"],
                        package_code=row["package_code"],
                        package_status=row["package_status"],
                        package_closed_at=row["package_closed_at"],
                        updated_at=row["remote_updated_at"],
                    )
                    for row in rows
                ],
                total=total,
                count=len(rows),
                limit=limit,
                offset=offset,
                next_offset=next_offset if next_offset < total else None,
                has_more=next_offset < total,
            )
        )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _migrate(self) -> None:
        with self._connect() as connection:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("""
                CREATE TABLE IF NOT EXISTS local_orders (
                    order_id TEXT PRIMARY KEY,
                    plant_id TEXT NOT NULL,
                    supplier_id TEXT NOT NULL,
                    order_number TEXT NOT NULL,
                    external_number TEXT,
                    status TEXT NOT NULL,
                    scan_required INTEGER NOT NULL DEFAULT 1,
                    planned_date TEXT,
                    updated_at INTEGER NOT NULL
                )
                """)
            connection.execute("""
                CREATE TABLE IF NOT EXISTS local_order_codes (
                    order_id TEXT NOT NULL,
                    code TEXT NOT NULL,
                    remote_code_id TEXT,
                    status TEXT NOT NULL,
                    order_line_id TEXT,
                    package_unit_id TEXT,
                    package_code TEXT,
                    package_status TEXT,
                    package_closed_at TEXT,
                    remote_updated_at TEXT,
                    synced_at INTEGER NOT NULL,
                    PRIMARY KEY(order_id, code)
                )
                """)
            connection.execute("""
                CREATE INDEX IF NOT EXISTS idx_local_order_codes_package
                ON local_order_codes(order_id, package_code)
                """)
