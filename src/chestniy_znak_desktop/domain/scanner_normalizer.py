"""Нормализация ввода DataMatrix от сканера."""

from __future__ import annotations

import re
from dataclasses import dataclass

GS = "\x1d"
ESC_GS_SEQ = "\x1b`\x1bb\x1bi"
AI21_MAX_SERIAL_LEN = 20
AI21_MIN_SERIAL_LEN_FOR_GS_RESTORE = 1
KNOWN_AI_FIXED_VALUE_LEN = {"91": 4, "93": 4}
KNOWN_AI_VARIABLE_TO_END = {"92"}
GROUP_SEPARATOR_TOKEN_RE = re.compile(r"(?i)(?:\\u001d|\\x1d|\\035|<GS>|\[GS\]|\{GS\})")
DECIMAL_GS_BEFORE_AI_RE = re.compile(r"0029(?=(?:91|92|93))")
BRACKETED_AI_RE = re.compile(r"\((01|21|91|92|93)\)")
GS1_CODE_START_RE = re.compile(r"01\d{14}21")
GTIN21_START_RE = re.compile(r"\d{14}21")
GTIN04_SUFFIX_21_START_RE = re.compile(r"\d{12}21")


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

    def repl(match: re.Match[str]) -> str:
        ai = match.group(1)
        if ai in {"91", "92", "93"}:
            return f"{GS}{ai}"
        return ai

    return BRACKETED_AI_RE.sub(repl, code)


def normalize_scanner_input(code: str) -> tuple[str, bool, bool]:
    """Нормализует строку сканера и возвращает признаки GS-разделителя."""

    normalized = GROUP_SEPARATOR_TOKEN_RE.sub(GS, str(code or ""))
    normalized = DECIMAL_GS_BEFORE_AI_RE.sub(GS, normalized)
    normalized = compact_bracketed_ai(normalized)
    native_gs = GS in normalized
    escaped_gs = ESC_GS_SEQ in normalized
    normalized = normalized.replace(ESC_GS_SEQ, GS)
    return normalized.strip("\r\n\t ").lstrip(GS), native_gs, escaped_gs


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


def split_tail_without_gs(tail: str) -> tuple[str, dict[str, str], list[str], bool]:
    """Разделяет serial и AI-хвост, когда scanner не прислал GS явно."""

    max_serial_len = min(AI21_MAX_SERIAL_LEN, len(tail))
    candidates: list[tuple[int, str, dict[str, str]]] = []
    for serial_len in range(max_serial_len, AI21_MIN_SERIAL_LEN_FOR_GS_RESTORE - 1, -1):
        rest = tail[serial_len:]
        if len(rest) < 2:
            continue
        if rest[:2] not in KNOWN_AI_FIXED_VALUE_LEN and rest[:2] not in KNOWN_AI_VARIABLE_TO_END:
            continue
        ai_parts, warnings = parse_ai_tail_without_gs(rest)
        if ai_parts and not warnings:
            candidates.append((serial_len, tail[:serial_len], ai_parts))
    if candidates:
        _serial_len, serial, ai_parts = max(
            candidates,
            key=lambda candidate: (len(candidate[2]), candidate[0]),
        )
        return serial, ai_parts, [], True

    serial = tail[:AI21_MAX_SERIAL_LEN]
    rest = tail[AI21_MAX_SERIAL_LEN:]
    ai_parts, warnings = parse_ai_tail_without_gs(rest)
    return serial, ai_parts, warnings, False


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
    normalized, prefix_warning = restore_missing_gs1_marking_prefix(normalized)
    if prefix_warning:
        warnings.append(prefix_warning)
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
        serial, ai_parts, tail_warnings, restored_by_ai = split_tail_without_gs(tail)
        gs_restored = True
        if restored_by_ai:
            warnings.append("GS не пришел явно; разделитель восстановлен перед известным AI")
        else:
            warnings.append("GS не пришел явно; разделитель восстановлен после 20 символов serial")
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


def is_complete_gs1_marking_code(code: str) -> bool:
    """Returns True when a scanner fragment is safe to treat as a complete code."""

    normalized = code.strip()
    if not has_gs1_marking_prefix(normalized):
        return False
    try:
        parsed = parse_marking_code(normalized)
    except MarkingCodeParseError:
        return False
    if not parsed.ai_parts:
        return False
    if any(key == "unknown_tail" or key.startswith("unknown_") for key in parsed.ai_parts):
        return False
    for ai, expected_len in KNOWN_AI_FIXED_VALUE_LEN.items():
        value = parsed.ai_parts.get(ai)
        if value is not None and len(value) != expected_len:
            return False
    return True


def has_gs1_marking_prefix(code: str) -> bool:
    """Returns True for regular 01+GTIN+21 or a recoverable missing prefix."""

    normalized = code.strip()
    return (
        GS1_CODE_START_RE.match(normalized) is not None
        or looks_like_missing_ai01_prefix(normalized)
        or looks_like_missing_ai01_gtin04_prefix(normalized)
    )


def has_regular_gs1_marking_prefix(code: str) -> bool:
    """Returns True only for explicit 01+GTIN+21 scanner payloads."""

    return GS1_CODE_START_RE.match(code.strip()) is not None


def looks_like_missing_ai01_prefix(code: str) -> bool:
    """Returns True when a serial scan likely lost the leading AI 01 bytes."""

    normalized = code.strip()
    return GTIN21_START_RE.match(normalized) is not None


def looks_like_missing_ai01_gtin04_prefix(code: str) -> bool:
    """Returns True when Windows HID likely dropped leading AI 01 and GTIN 04."""

    normalized = code.strip()
    return GTIN04_SUFFIX_21_START_RE.match(normalized) is not None


def restore_missing_gs1_marking_prefix(code: str) -> tuple[str, str]:
    """Restores recoverable GS1 marking prefixes lost by keyboard-wedge scanners."""

    normalized = code.strip()
    if normalized.startswith("01"):
        return normalized, ""
    if looks_like_missing_ai01_prefix(normalized):
        return f"01{normalized}", "AI 01 не пришел явно; префикс восстановлен перед GTIN"
    if looks_like_missing_ai01_gtin04_prefix(normalized):
        return (
            f"0104{normalized}",
            "AI 01 и начало GTIN 04 не пришли явно; префикс восстановлен перед GTIN",
        )
    return normalized, ""


def split_completed_gs1_buffer_text(text: str) -> tuple[list[str], str]:
    """Splits completed glued GS1 codes while keeping the active scan in the buffer."""

    starts = [match.start() for match in GS1_CODE_START_RE.finditer(text)]
    if len(starts) < 2:
        return [], text
    completed_codes: list[str] = []
    current_start = starts[0]
    for next_start in starts[1:]:
        candidate = text[current_start:next_start].strip()
        if not is_complete_gs1_marking_code(candidate):
            break
        completed_codes.append(candidate)
        current_start = next_start
    if not completed_codes:
        return [], text
    return completed_codes, text[current_start:]


def split_scanner_payload_by_gs1_starts(code: str) -> list[str]:
    """Splits a scanner payload only at starts preceded by a complete GS1 code."""

    normalized = code.strip()
    if not normalized:
        return []
    starts = [match.start() for match in GS1_CODE_START_RE.finditer(normalized)]
    if not starts:
        if not normalized[0].isdigit():
            return [normalized]
        return [normalized] if has_gs1_marking_prefix(normalized) else []
    parts: list[str] = []
    current_start = starts[0]
    for next_start in starts[1:]:
        candidate = normalized[current_start:next_start].strip()
        if not is_complete_gs1_marking_code(candidate):
            continue
        parts.append(candidate)
        current_start = next_start
    tail = normalized[current_start:].strip()
    if tail:
        parts.append(tail)
    return parts
