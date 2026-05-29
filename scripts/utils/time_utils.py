from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from email.utils import parsedate_to_datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


CHINA_TZ = timezone(timedelta(hours=8))
DEFAULT_TIMEZONE_NAME = "Asia/Shanghai"
EXCEL_EPOCH = datetime(1899, 12, 30, tzinfo=CHINA_TZ)
UTC_ISO_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
CHINA_ISO_FORMAT = "%Y-%m-%d %H:%M:%S UTC+8"


def timezone_from_name(name: str):
    name = str(name or "").strip()
    if not name:
        return CHINA_TZ
    if name in {"Asia/Shanghai", "UTC+8", "CST"}:
        return CHINA_TZ
    if name.upper() in {"UTC", "Z"}:
        return timezone.utc
    try:
        return ZoneInfo(name)
    except ZoneInfoNotFoundError:
        return CHINA_TZ


def _format_utc(dt: datetime, default_timezone=CHINA_TZ) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=default_timezone)
    return dt.astimezone(timezone.utc).replace(microsecond=0).strftime(UTC_ISO_FORMAT)


def _format_china(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=CHINA_TZ)
    return dt.astimezone(CHINA_TZ).replace(microsecond=0).strftime(CHINA_ISO_FORMAT)


def utc_iso_to_china_iso(value) -> str:
    raw = str(value).strip()
    if not raw:
        return ""
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(raw)
    except ValueError:
        return ""
    return _format_china(dt)


def utc_ms_to_utc_iso(value) -> str:
    try:
        dt = datetime.fromtimestamp(int(value) / 1000.0, tz=timezone.utc)
    except Exception:
        return ""
    return _format_utc(dt)


def utc_ms_to_china_iso(value) -> str:
    try:
        dt = datetime.fromtimestamp(int(value) / 1000.0, tz=timezone.utc)
    except Exception:
        return ""
    return _format_china(dt)


def _parse_numeric_time(raw: str, default_timezone=CHINA_TZ) -> str:
    try:
        number = Decimal(raw)
    except InvalidOperation:
        return ""

    if number <= 0:
        return ""

    # Unix milliseconds are usually 13 digits. Unix seconds are usually 10 digits.
    if number >= Decimal("100000000000"):
        dt = datetime.fromtimestamp(float(number) / 1000.0, tz=timezone.utc)
        return _format_utc(dt)
    if number >= Decimal("1000000000"):
        dt = datetime.fromtimestamp(float(number), tz=timezone.utc)
        return _format_utc(dt)

    # Excel serial dates use 1899-12-30 as day 0. Treat serial dates as China
    # local wall-clock time because exported spreadsheets usually omit timezone.
    if Decimal("20000") <= number <= Decimal("80000"):
        epoch = datetime(1899, 12, 30, tzinfo=default_timezone)
        dt = epoch + timedelta(days=float(number))
        return _format_utc(dt, default_timezone)

    return ""


def parse_any_time_to_utc_iso(value, default_timezone: str = DEFAULT_TIMEZONE_NAME) -> str:
    raw = str(value).strip()
    if not raw or raw.lower() in {"nan", "none", "nat"}:
        return ""

    default_tz = timezone_from_name(default_timezone)
    numeric_result = _parse_numeric_time(raw, default_tz)
    if numeric_result:
        return numeric_result

    candidates = [raw]
    if raw.endswith("Z"):
        candidates.append(raw[:-1] + "+00:00")
    if "/" in raw:
        candidates.append(raw.replace("/", "-"))

    for candidate in candidates:
        try:
            dt = datetime.fromisoformat(candidate)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=default_tz)
            return _format_utc(dt, default_tz)
        except ValueError:
            pass

    for fmt in (
        "%Y-%m-%d %H:%M:%S",
        "%Y/%m/%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y/%m/%d %H:%M",
        "%Y-%m-%d",
        "%Y/%m/%d",
    ):
        try:
            dt = datetime.strptime(raw, fmt).replace(tzinfo=default_tz)
            return _format_utc(dt, default_tz)
        except ValueError:
            pass

    try:
        dt = parsedate_to_datetime(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=default_tz)
        return _format_utc(dt, default_tz)
    except (TypeError, ValueError, IndexError, AttributeError):
        pass

    return ""
