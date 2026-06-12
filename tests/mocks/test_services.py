"""Mock-тесты API-сервисов."""

from __future__ import annotations

from typing import Any

from chestniy_znak_desktop.api.models.orders import LocalCodePoolDto
from chestniy_znak_desktop.api.models.orders import LocalCodePoolPageDto
from chestniy_znak_desktop.api.models.orders import LocalPoolCodeDto
from chestniy_znak_desktop.api.models.orders import WorkOrderDto
from chestniy_znak_desktop.api.services.box_edit_service import BoxEditService
from chestniy_znak_desktop.api.services.chestniy_znak_service import ChestniyZnakService
from chestniy_znak_desktop.api.services.order_service import OrderService
from chestniy_znak_desktop.api.services.packing_service import PackingService
from chestniy_znak_desktop.api.services.printer_service import PrinterService
from chestniy_znak_desktop.api.models.printers import PrintJobDto
from chestniy_znak_desktop.services.order_local_pool_cache import OrderLocalPoolCache


class FakeApiClient:
    """Простой fake API-клиент для проверки сервисного слоя."""

    def __init__(self) -> None:
        """Создает хранилище последнего вызова."""

        self.last_call: tuple[str, str, dict[str, Any]] | None = None
        self.calls: list[tuple[str, str, dict[str, Any]]] = []
        self.close_response: dict[str, Any] | None = None
        self.printer_selected = False

    def get(self, url: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Возвращает payload для GET-сценария."""

        self.last_call = ("GET", url, {"params": params})
        self.calls.append(self.last_call)
        if url.endswith("catalog/stats"):
            return {"codes_count": 10, "scans_count": 3}
        if url.endswith("printer/printers"):
            return {
                "ok": True,
                "device_id": (params or {}).get("device_id", ""),
                "selected_printer_id": 11 if self.printer_selected else None,
                "selected_printer": _printer_payload() if self.printer_selected else None,
                "printers": [_printer_payload()],
            }
        if url.endswith("packing/boxes/1"):
            return {
                "ok": True,
                "reason_code": "box_loaded",
                "box": _box_detail_payload(),
            }
        return {"items": [], "total": 0, "limit": 50, "offset": 0, "has_more": False}

    def post(
        self,
        url: str,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Возвращает payload для POST-сценария."""

        self.last_call = ("POST", url, {"json": json, "params": params})
        self.calls.append(self.last_call)
        if url.endswith("verify") and not url.endswith("verify/exists"):
            return {
                "status": "OK",
                "message": "Код найден",
                "scan_id": 1,
                "code": {
                    "id": 1,
                    "gtin": "04601234567890",
                    "serial": "SERIAL",
                    "visible_code": "010460123456789021SERIAL",
                    "order_name": "26-0001",
                    "device_name": "Device",
                },
                "warnings": [],
            }
        if url.endswith("verify/exists"):
            return {
                "ok": True,
                "exists": True,
                "status": "OK",
                "message": "Код найден",
                "order_name": "26-0001",
                "device_name": "Device",
                "warnings": [],
            }
        if url.endswith("laser/defect"):
            return {
                "ok": True,
                "reason_code": "defect_marked",
                "error": None,
                "verify": {
                    "status": "OK",
                    "message": "Код найден",
                    "code": {
                        "id": 1,
                        "gtin": "04601234567890",
                        "serial": "SERIAL",
                        "visible_code": "010460123456789021SERIAL",
                        "order_name": "26-0001",
                        "device_name": "Device",
                    },
                    "warnings": [],
                },
                "removed_from_box": {"box_id": 1, "sscc": "SSCC", "filled": 0},
            }
        if url.endswith("boxes/open"):
            return {
                "ok": True,
                "created": True,
                "has_active_boxes": False,
                "boxes": [],
                "box": _box_payload(),
            }
        if url.endswith("boxes/1/close") and self.close_response is not None:
            return self.close_response
        if url.endswith("printer/printer-selection"):
            self.printer_selected = True
            return {
                "ok": True,
                "device_id": (json or {}).get("device_id", ""),
                "selected_printer_id": (json or {}).get("printer_id", 11),
                "selected_printer": _printer_payload(),
                "printers": [_printer_payload()],
            }
        if url.endswith("boxes/1/print-label"):
            return {
                "ok": True,
                "reason_code": "label_print_job_ready",
                "print_status": "job_ready",
                "print_ok": False,
                "print_error_code": "",
                "print_error": "",
                "printer": _printer_payload(),
                "print_job": {
                    "format": "zpl",
                    "driver": "zpl",
                    "encoding": "utf-8",
                    "transport": "raw_tcp",
                    "payload": "^XA^XZ",
                    "printer": _printer_payload(),
                },
                "box": _box_payload(),
            }
        if url.endswith("boxes/1/print-result"):
            return {
                "ok": True,
                "reason_code": "label_printed",
                "print_status": "",
                "print_ok": bool((json or {}).get("print_ok")),
                "print_error_code": "",
                "print_error": str((json or {}).get("print_error") or ""),
                "printer": _printer_payload(),
                "print_job": None,
                "box": _box_payload(),
            }
        if url.endswith("box-edit/1/open"):
            return {"ok": True, "reason_code": "edit_opened", "box": _box_payload()}
        if url.endswith("box-edit/1/close"):
            return {"ok": True, "reason_code": "edit_closed", "box": _box_payload()}
        if url.endswith("box-edit/1/items/remove"):
            return {
                "ok": True,
                "reason_code": "item_removed",
                "box": _box_payload(),
                "removed": 1,
            }
        if url.endswith("box-edit/1/clear"):
            return {
                "ok": True,
                "reason_code": "box_cleared",
                "box": _box_payload(),
                "removed": 2,
            }
        return {"ok": True, "reason_code": "ok", "box": _box_payload()}

    def patch(self, url: str, json: dict[str, Any]) -> dict[str, Any]:
        """Возвращает payload для PATCH-сценария."""

        self.last_call = ("PATCH", url, {"json": json})
        self.calls.append(self.last_call)
        return {"ok": True, "reason_code": "updated", "box": _box_payload()}

    def delete(self, url: str) -> dict[str, Any]:
        """Возвращает payload для DELETE-сценария."""

        self.last_call = ("DELETE", url, {})
        self.calls.append(self.last_call)
        return {
            "ok": True,
            "reason_code": "empty_box_deleted",
            "box": _box_payload(),
            "removed": 1,
        }


def _box_payload() -> dict[str, Any]:
    """Возвращает минимальный payload коробки для DTO."""

    return {
        "box_id": 1,
        "order_id": None,
        "order_name": "26-0001",
        "sscc": None,
        "capacity": 20,
        "filled": 0,
        "count_in_packing": True,
        "allow_duplicate_scans": False,
        "is_closed": False,
        "is_edit_mode": False,
    }


def _printer_payload() -> dict[str, Any]:
    """Возвращает payload принтера для DTO."""

    return {
        "id": 11,
        "name": "Zebra",
        "ip_address": "192.168.1.10",
        "port": 9100,
        "section": "Line A",
        "driver": "zpl",
        "is_active": True,
    }


class FakePrintTransport:
    """Fake транспорт печати для проверки PrinterService."""

    def __init__(self) -> None:
        """Создает список отправленных заданий."""

        self.jobs: list[PrintJobDto] = []

    def send(self, job: PrintJobDto) -> tuple[bool, str]:
        """Запоминает задание и возвращает успех."""

        self.jobs.append(job)
        return True, ""


def _box_detail_payload() -> dict[str, Any]:
    """Возвращает payload детальной коробки для DTO."""

    payload = _box_payload()
    payload["items"] = [
        {
            "id": 10,
            "code_id": 100,
            "gtin": "04601234567890",
            "serial": "SERIAL",
            "visible_code": "010460123456789021SERIAL",
        }
    ]
    return payload


def test_chestniy_znak_service_verify_exists() -> None:
    """Проверяет маппинг сервиса проверки существования кода."""

    client = FakeApiClient()
    result = ChestniyZnakService(client).verify_exists("code", "desktop-com")
    assert result.exists is True
    assert result.order_name == "26-0001"
    assert client.last_call == (
        "POST",
        "chestniy-znak/verify/exists",
        {
            "json": {
                "code": "code",
                "scanner_id": "desktop-com",
                "allow_duplicate": True,
                "save_scan": True,
            },
            "params": None,
        },
    )


def test_chestniy_znak_service_verify_exists_can_skip_scan_save() -> None:
    """Проверяет проверку существования без сохранения scan."""

    client = FakeApiClient()
    ChestniyZnakService(client).verify_exists(
        "code",
        "desktop-com",
        save_scan=False,
    )

    assert client.last_call == (
        "POST",
        "chestniy-znak/verify/exists",
        {
            "json": {
                "code": "code",
                "scanner_id": "desktop-com",
                "allow_duplicate": True,
                "save_scan": False,
            },
            "params": None,
        },
    )


def test_chestniy_znak_service_verify() -> None:
    """Проверяет маппинг полной проверки кода."""

    client = FakeApiClient()
    result = ChestniyZnakService(client).verify("code", "desktop-com")
    assert result.status == "OK"
    assert result.code is not None
    assert result.code.order_name == "26-0001"
    assert client.last_call == (
        "POST",
        "chestniy-znak/verify",
        {
            "json": {
                "code": "code",
                "scanner_id": "desktop-com",
                "allow_duplicate": False,
                "save_scan": True,
            },
            "params": None,
        },
    )


def test_chestniy_znak_service_mark_defect() -> None:
    """Проверяет маппинг сервиса отправки кода в брак."""

    client = FakeApiClient()
    result = ChestniyZnakService(client).mark_defect("code", "desktop-com-defect")
    assert result.ok is True
    assert result.removed_from_box is not None
    assert result.removed_from_box.box_id == 1
    assert client.last_call == (
        "POST",
        "chestniy-znak/laser/defect",
        {"json": {"code": "code", "scanner_id": "desktop-com-defect"}, "params": None},
    )


def test_packing_service_open_box() -> None:
    """Проверяет маппинг открытия коробки."""

    client = FakeApiClient()
    result = PackingService(client).open_box(device_id="pc-1", count_in_packing=False)
    assert result.created is True
    assert result.box.box_id == 1


def test_packing_service_get_box() -> None:
    """Проверяет маппинг детальной карточки коробки."""

    client = FakeApiClient()
    result = PackingService(client).get_box(1)
    assert result.box_id == 1
    assert result.items[0].serial == "SERIAL"


def test_packing_service_close_box_only_closes_remote_box() -> None:
    """Проверяет, что рабочее место только закрывает коробку на сервере."""

    client = FakeApiClient()
    client.close_response = {
        "ok": True,
        "reason_code": "box_closed",
        "box": _box_payload(),
    }

    result = PackingService(client).close_box(box_id=1, device_id="pc-1")

    assert result.ok is True
    assert result.reason_code == "box_closed"
    assert client.last_call == (
        "POST",
        "chestniy-znak/packing/boxes/1/close",
        {"json": None, "params": {"device_id": "pc-1"}},
    )


def test_order_service_caches_local_pool_for_offline_desktop(tmp_path) -> None:
    """Desktop can keep working with a selected order when the API is temporarily unavailable."""

    client = FakeApiClient()

    def local_pool_get(url: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        client.last_call = ("GET", url, {"params": params})
        client.calls.append(client.last_call)
        if url == "orders/order-1/local-pool":
            return {
                "data": {
                    "order": {
                        "id": "order-1",
                        "plant_id": "plant-1",
                        "supplier_id": "supplier-1",
                        "order_number": "PO-1",
                        "status": "in_progress",
                        "scan_required": True,
                        "lines": [],
                    },
                    "codes": [
                        {
                            "id": "code-1",
                            "code": "010460123456789021SERIAL",
                            "status": "packed",
                            "order_line_id": "line-1",
                            "package_unit_id": "box-uuid-1",
                            "package_code": "BOX-001",
                            "package_status": "closed",
                            "package_closed_at": "2026-06-07T10:00:00+00:00",
                            "updated_at": "2026-06-07T10:00:00+00:00",
                        }
                    ],
                    "total": 1,
                    "count": 1,
                    "limit": 5000,
                    "offset": 0,
                    "next_offset": None,
                    "has_more": False,
                }
            }
        return FakeApiClient.get(client, url, params)

    client.get = local_pool_get  # type: ignore[method-assign]
    cache = OrderLocalPoolCache(tmp_path / "local_pool.sqlite3")
    service = OrderService(client, local_pool_cache=cache)

    first = service.download_local_pool("order-1")
    assert first.data.codes[0].package_code == "BOX-001"

    def failing_get(url: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        raise RuntimeError("network down")

    client.get = failing_get  # type: ignore[method-assign]
    cached = service.download_local_pool("order-1")

    assert cached.data.order.order_number == "PO-1"
    assert cached.data.codes[0].code == "010460123456789021SERIAL"
    assert cached.data.codes[0].status == "packed"
    assert cached.data.codes[0].package_code == "BOX-001"


def test_local_pool_cache_deletes_closed_order(tmp_path) -> None:
    """Проверяет очистку sqlite snapshot после закрытия заказа."""

    cache = OrderLocalPoolCache(tmp_path / "local_pool.sqlite3")
    cache.save_page(_local_pool_page(order_status="in_progress", codes=["CODE1"]))
    assert cache.load_page("order-1", limit=5000, offset=0) is not None

    cache.save_page(_local_pool_page(order_status="closed", codes=["CODE1"]))

    assert cache.load_page("order-1", limit=5000, offset=0) is None


def test_local_pool_cache_appends_new_pool_codes(tmp_path) -> None:
    """Проверяет догрузку новых кодов в локальный sqlite snapshot заказа."""

    cache = OrderLocalPoolCache(tmp_path / "local_pool.sqlite3")

    cache.save_page(_local_pool_page(order_status="in_progress", codes=["CODE1"]))
    cache.save_page(_local_pool_page(order_status="in_progress", codes=["CODE1", "CODE2"]))

    cached = cache.load_page("order-1", limit=5000, offset=0)

    assert cached is not None
    assert [code.code for code in cached.data.codes] == ["CODE1", "CODE2"]


def _local_pool_page(order_status: str, codes: list[str]) -> LocalCodePoolPageDto:
    """Создает страницу локального пула для cache-тестов."""

    return LocalCodePoolPageDto(
        data=LocalCodePoolDto(
            order=WorkOrderDto(
                id="order-1",
                plant_id="plant-1",
                supplier_id="supplier-1",
                order_number="PO-1",
                status=order_status,
                scan_required=True,
                lines=[],
            ),
            codes=[
                LocalPoolCodeDto(
                    id=f"code-{index}",
                    code=code,
                    status="downloaded",
                    order_line_id="line-1",
                )
                for index, code in enumerate(codes, start=1)
            ],
            total=len(codes),
            count=len(codes),
            limit=5000,
            offset=0,
            next_offset=None,
            has_more=False,
        )
    )


def test_printer_service_autoselects_single_printer_and_reports_print_result() -> None:
    """Проверяет полный цикл печати SSCC через локальный транспорт."""

    client = FakeApiClient()
    transport = FakePrintTransport()

    result = PrinterService(client, print_transport=transport).print_box_label(
        box_id=1,
        device_id="pc-1",
    )

    assert result.print_ok is True
    assert transport.jobs[0].payload == "^XA^XZ"
    assert [call[1] for call in client.calls] == [
        "chestniy-znak/packing/printer/printers",
        "chestniy-znak/packing/printer/printer-selection",
        "chestniy-znak/packing/boxes/1/print-label",
        "chestniy-znak/packing/boxes/1/print-result",
    ]


def test_box_edit_service_open_edit() -> None:
    """Проверяет открытие режима редактирования коробки."""

    client = FakeApiClient()
    result = BoxEditService(client).open_edit(box_id=1, reason="fix")
    assert result.ok is True
    assert result.reason_code == "edit_opened"
    assert client.last_call == (
        "POST",
        "chestniy-znak/packing/box-edit/1/open",
        {"json": {"reason": "fix"}, "params": None},
    )


def test_box_edit_service_remove_item() -> None:
    """Проверяет удаление кода из коробки."""

    client = FakeApiClient()
    result = BoxEditService(client).remove_item(box_id=1, item_id=10)
    assert result.removed == 1
    assert client.last_call == (
        "POST",
        "chestniy-znak/packing/box-edit/1/items/remove",
        {"json": {"item_id": 10}, "params": None},
    )


def test_box_edit_service_delete_empty_box() -> None:
    """Проверяет удаление пустой коробки."""

    client = FakeApiClient()
    result = BoxEditService(client).delete_empty_box(box_id=1)
    assert result.reason_code == "empty_box_deleted"
    assert client.last_call == ("DELETE", "chestniy-znak/packing/box-edit/1/empty", {})
