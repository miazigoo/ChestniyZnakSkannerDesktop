"""Mock-тесты API-сервисов."""

from __future__ import annotations

from typing import Any

from chestniy_znak_desktop.api.services.box_edit_service import BoxEditService
from chestniy_znak_desktop.api.services.chestniy_znak_service import ChestniyZnakService
from chestniy_znak_desktop.api.services.packing_service import PackingService
from chestniy_znak_desktop.api.services.printer_service import PrinterService


class FakeApiClient:
    """Простой fake API-клиент для проверки сервисного слоя."""

    def __init__(self) -> None:
        """Создает хранилище последнего вызова."""

        self.last_call: tuple[str, str, dict[str, Any]] | None = None

    def get(self, url: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Возвращает payload для GET-сценария."""

        self.last_call = ("GET", url, {"params": params})
        if url.endswith("catalog/stats"):
            return {"codes_count": 10, "scans_count": 3}
        if url.endswith("packing/boxes/1"):
            return {
                "ok": True,
                "reason_code": "box_loaded",
                "box": _box_detail_payload(),
            }
        if url.endswith("printer/printers"):
            return {
                "ok": True,
                "device_id": "pc-1",
                "selected_printer_id": None,
                "printers": [
                    {
                        "id": 1,
                        "name": "Zebra",
                        "ip_address": "172.16.8.120",
                        "section": "A",
                        "is_active": True,
                    }
                ],
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
        if url.endswith("printer/boxes/1/print"):
            return {
                "ok": True,
                "reason_code": "printed",
                "box": _box_payload(),
                "print_ok": True,
                "print_error": "",
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
        if url.endswith("printer-selection"):
            return {
                "ok": True,
                "device_id": "pc-1",
                "selected_printer_id": 1,
                "selected_printer": {
                    "id": 1,
                    "name": "Zebra",
                    "ip_address": "172.16.8.120",
                    "section": "",
                    "is_active": True,
                },
                "printers": [],
            }
        return {"ok": True, "reason_code": "ok", "box": _box_payload()}

    def patch(self, url: str, json: dict[str, Any]) -> dict[str, Any]:
        """Возвращает payload для PATCH-сценария."""

        self.last_call = ("PATCH", url, {"json": json})
        return {"ok": True, "reason_code": "updated", "box": _box_payload()}

    def delete(self, url: str) -> dict[str, Any]:
        """Возвращает payload для DELETE-сценария."""

        self.last_call = ("DELETE", url, {})
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


def test_printer_service_set_selection() -> None:
    """Проверяет сохранение выбранного принтера."""

    client = FakeApiClient()
    result = PrinterService(client).set_selection(device_id="pc-1", printer_id=1)
    assert result.selected_printer_id == 1


def test_printer_service_get_selection() -> None:
    """Проверяет получение доступных принтеров."""

    client = FakeApiClient()
    result = PrinterService(client).get_selection(device_id="pc-1")
    assert result.printers[0].name == "Zebra"
    assert client.last_call == (
        "GET",
        "chestniy-znak/packing/printer/printers",
        {"params": {"device_id": "pc-1"}},
    )


def test_printer_service_print_box_label() -> None:
    """Проверяет повторную печать этикетки коробки."""

    client = FakeApiClient()
    result = PrinterService(client).print_box_label(box_id=1, device_id="pc-1")
    assert result.print_ok is True
    assert client.last_call == (
        "POST",
        "chestniy-znak/packing/printer/boxes/1/print",
        {"json": None, "params": {"device_id": "pc-1"}},
    )


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
