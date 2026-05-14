"""Нормализация ввода DataMatrix от сканера."""

from __future__ import annotations

from dataclasses import dataclass

GS = "\x1d"
ESC_GS_SEQ = "\x1b`\x1bb\x1bi"
AI21_MAX_SERIAL_LEN = 20
KNOWN_AI_FIXED_VALUE_LEN = {"91": 4, "93": 4}
KNOWN_AI_VARIABLE_TO_END = {"92"}


class MarkingCodeParseError(ValueError):
    """Ошибка разбора DataMatrix-кода Честного знака."""


@dataclass(frozen=True, slots=True)
class ParsedMarkingCode:
    """Нормализованный результат разбора DataMatrix-кода."""

    gtin: str
    serial: str
    ai_parts: dict[str, str]
    raw_code: str
    visible_code: str
    scanner_gs_native: bool
    gs_restored: bool
    warnings: list[str]

    @property
    def identity_key(self) -> str:
        """Возвращает ключ идентичности GTIN и serial."""

        return f"{self.gtin}|{self.serial}"


def visible(code: str) -> str:
    """Делает управляющие символы кода видимыми для UI и логов."""

    return (
        code.replace(GS, "<GS>").replace("\r", "<CR>").replace("\n", "<LF>").replace("\t", "<TAB>")
    )


def compact_bracketed_ai(code: str) -> str:
    """Приводит AI в скобках к компактному GS1-виду."""

    return (
        code.replace("(01)", "01")
        .replace("(21)", "21")
        .replace("(91)", f"{GS}91")
        .replace("(92)", f"{GS}92")
        .replace("(93)", f"{GS}93")
    )


def normalize_scanner_input(code: str) -> tuple[str, bool, bool]:
    """Нормализует строку сканера и возвращает признаки GS-разделителя."""

    normalized = str(code or "").replace("<GS>", GS).replace("[GS]", GS)
    normalized = normalized.replace("\\x1d", GS).replace("\\u001d", GS)
    normalized = compact_bracketed_ai(normalized)
    native_gs = GS in normalized
    escaped_gs = ESC_GS_SEQ in normalized
    normalized = normalized.replace(ESC_GS_SEQ, GS)
    return normalized.rstrip("\r\n\t ").lstrip(GS), native_gs, escaped_gs


def parse_ai_tail_with_gs(rest: str) -> tuple[dict[str, str], list[str]]:
    """Разбирает AI-хвост, где фрагменты разделены ASCII GS."""

    ai_parts: dict[str, str] = {}
    warnings: list[str] = []
    for part in rest.split(GS):
        if not part:
            continue
        if len(part) < 2 or not part[:2].isdigit():
            ai_parts[f"unknown_{len(ai_parts) + 1}"] = part
            warnings.append(f"Неизвестный AI-фрагмент: {part!r}")
            continue
        ai_parts[part[:2]] = part[2:]
    return ai_parts, warnings


def parse_ai_tail_without_gs(rest: str) -> tuple[dict[str, str], list[str]]:
    """Разбирает AI-хвост без GS по известным длинам AI."""

    ai_parts: dict[str, str] = {}
    warnings: list[str] = []
    remainder = rest

    while remainder:
        ai = remainder[:2]
        if len(ai) < 2 or not ai.isdigit():
            ai_parts["unknown_tail"] = remainder
            warnings.append("AI-хвост без GS не удалось разобрать полностью")
            break
        if ai in KNOWN_AI_FIXED_VALUE_LEN:
            value_len = KNOWN_AI_FIXED_VALUE_LEN[ai]
            value_end = 2 + value_len
            if len(remainder) < value_end:
                ai_parts[ai] = remainder[2:]
                warnings.append(f"AI {ai} короче ожидаемой длины {value_len}")
                break
            ai_parts[ai] = remainder[2:value_end]
            remainder = remainder[value_end:]
            continue
        if ai in KNOWN_AI_VARIABLE_TO_END:
            ai_parts[ai] = remainder[2:]
            break
        ai_parts["unknown_tail"] = remainder
        warnings.append(f"Неизвестный AI {ai} в хвосте без GS")
        break

    return ai_parts, warnings


def build_raw_code(gtin: str, serial: str, ai_parts: dict[str, str]) -> str:
    """Собирает нормализованный полный код из GTIN, serial и AI-хвоста."""

    prefix = f"01{gtin}21{serial}"
    if not ai_parts:
        return prefix
    tail_parts = [
        value if ai == "unknown_tail" or ai.startswith("unknown_") else f"{ai}{value}"
        for ai, value in ai_parts.items()
    ]
    return prefix + GS + GS.join(tail_parts)


def parse_marking_code(code: str) -> ParsedMarkingCode:
    """Разбирает DataMatrix ЧЗ и возвращает нормализованную структуру."""

    normalized, native_gs, escaped_gs = normalize_scanner_input(code)
    warnings: list[str] = []
    if not normalized:
        raise MarkingCodeParseError("Пустой код")
    if not normalized.startswith("01"):
        raise MarkingCodeParseError("Код должен начинаться с AI 01")
    if len(normalized) < 18:
        raise MarkingCodeParseError("Код слишком короткий для 01 + GTIN + 21")

    gtin = normalized[2:16]
    if len(gtin) != 14 or not gtin.isdigit():
        raise MarkingCodeParseError(f"Некорректный GTIN: {gtin!r}")
    if normalized[16:18] != "21":
        raise MarkingCodeParseError("После GTIN ожидается AI 21")

    tail = normalized[18:]
    if not tail:
        raise MarkingCodeParseError("После AI 21 нет серийного номера")

    gs_restored = False
    if GS in tail:
        serial, rest = tail.split(GS, 1)
        ai_parts, tail_warnings = parse_ai_tail_with_gs(rest)
    elif len(tail) > AI21_MAX_SERIAL_LEN:
        serial = tail[:AI21_MAX_SERIAL_LEN]
        rest = tail[AI21_MAX_SERIAL_LEN:]
        gs_restored = True
        warnings.append("GS не пришел явно; разделитель восстановлен после 20 символов serial")
        ai_parts, tail_warnings = parse_ai_tail_without_gs(rest)
    else:
        serial = tail
        ai_parts, tail_warnings = {}, ["GS отсутствует; AI-хвост после serial не обнаружен"]

    warnings.extend(tail_warnings)
    if not serial:
        raise MarkingCodeParseError("Пустой serial после AI 21")

    raw_code = build_raw_code(gtin=gtin, serial=serial, ai_parts=ai_parts)
    return ParsedMarkingCode(
        gtin=gtin,
        serial=serial,
        ai_parts=ai_parts,
        raw_code=raw_code,
        visible_code=visible(raw_code),
        scanner_gs_native=native_gs,
        gs_restored=gs_restored or escaped_gs,
        warnings=warnings,
    )
