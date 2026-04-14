from datetime import date, datetime


def parse_trade_date(value: str | date | None) -> date | None:
    if value is None:
        return None
    if isinstance(value, date):
        return value

    normalized = value.strip()
    if not normalized:
        return None
    if "-" in normalized:
        try:
            return date.fromisoformat(normalized)
        except ValueError:
            return None

    compact = normalized.replace("/", "")
    if len(compact) != 8 or not compact.isdigit():
        return None

    try:
        return datetime.strptime(compact, "%Y%m%d").date()
    except ValueError:
        return None


def trade_date_dt_param(value: str | date | None) -> str | None:
    parsed = parse_trade_date(value)
    return parsed.isoformat() if parsed else None
