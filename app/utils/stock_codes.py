from __future__ import annotations

from typing import Iterable


EXCHANGE_SUFFIX_TO_NAME = {
    "SH": "SH",
    "SSE": "SH",
    "SZ": "SZ",
    "SZSE": "SZ",
    "BJ": "BJ",
    "BSE": "BJ",
}

EXCHANGE_NAME_TO_SUFFIX = {
    "SH": "SH",
    "SZ": "SZ",
    "BJ": "BJ",
}


def extract_symbol(code: str | None) -> str:
    if not code:
        return ""
    return str(code).strip().upper().split(".", 1)[0]


def infer_exchange_name(symbol: str) -> str:
    code = extract_symbol(symbol)
    if code.startswith(("6", "5")):
        return "SH"
    if code.startswith(("0", "1", "2", "3")):
        return "SZ"
    if code.startswith(("4", "8", "9")):
        return "BJ"
    return "UNKNOWN"


def normalize_exchange_name(value: str | None, symbol: str | None = None) -> str:
    if value:
        normalized = EXCHANGE_SUFFIX_TO_NAME.get(str(value).strip().upper())
        if normalized:
            return normalized
    if symbol:
        return infer_exchange_name(symbol)
    return "UNKNOWN"


def normalize_ts_code(value: str | None, symbol: str | None = None, exchange: str | None = None) -> str:
    raw = str(value or "").strip().upper()
    if raw:
        if "." in raw:
            left, right = raw.split(".", 1)
            suffix = EXCHANGE_NAME_TO_SUFFIX.get(EXCHANGE_SUFFIX_TO_NAME.get(right, right), right)
            return f"{left}.{suffix}"
        inferred_exchange = normalize_exchange_name(exchange, raw)
        suffix = EXCHANGE_NAME_TO_SUFFIX.get(inferred_exchange)
        if suffix:
            return f"{extract_symbol(raw)}.{suffix}"

    base = extract_symbol(symbol)
    inferred_exchange = normalize_exchange_name(exchange, base)
    suffix = EXCHANGE_NAME_TO_SUFFIX.get(inferred_exchange)
    if base and suffix:
        return f"{base}.{suffix}"
    return base


def build_code_variants(code: str | None) -> list[str]:
    base = extract_symbol(code)
    if not base:
        return []

    variants = {
        base,
        f"{base}.SH",
        f"{base}.SZ",
        f"{base}.BJ",
        f"{base}.SSE",
        f"{base}.SZSE",
        f"{base}.BSE",
    }

    normalized = normalize_ts_code(code)
    if normalized:
        variants.add(normalized)

    inferred_exchange = infer_exchange_name(base)
    inferred_suffix = EXCHANGE_NAME_TO_SUFFIX.get(inferred_exchange)
    if inferred_suffix:
        variants.add(f"{base}.{inferred_suffix}")

    return [item for item in variants if item]


def normalize_stock_payload(record: dict) -> dict:
    normalized = dict(record)
    symbol = extract_symbol(normalized.get("symbol") or normalized.get("code") or normalized.get("ts_code"))
    normalized_ts_code = normalize_ts_code(
        normalized.get("ts_code"),
        symbol=symbol,
        exchange=normalized.get("exchange"),
    )
    normalized["symbol"] = symbol or normalized.get("symbol")
    normalized["code"] = symbol or normalized.get("code")
    if normalized_ts_code:
        normalized["ts_code"] = normalized_ts_code
    normalized["exchange"] = normalize_exchange_name(normalized.get("exchange"), symbol)
    return normalized


def normalize_rows(rows: Iterable[dict]) -> list[dict]:
    return [normalize_stock_payload(row) for row in rows]
