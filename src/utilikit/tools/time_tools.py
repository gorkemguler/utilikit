"""Time helpers: current time, epoch↔ISO, timezone conversion, cron, duration."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from dateutil import parser as dtparser
from fastapi import APIRouter, Query

from ..errors import ToolError
from ..registry import Endpoint, ToolInfo, register

router = APIRouter(prefix="/v1", tags=["time"])


def _zone(name: str) -> ZoneInfo:
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise ToolError(f"Unknown timezone {name!r} (use an IANA name like 'Europe/Istanbul').") from exc


def _describe(dt: datetime) -> dict:
    return {
        "iso": dt.isoformat(),
        "epoch": dt.timestamp(),
        "epoch_ms": int(dt.timestamp() * 1000),
        "utc": dt.astimezone(UTC).isoformat(),
        "weekday": dt.strftime("%A"),
        "week": int(dt.strftime("%V")),
        "day_of_year": int(dt.strftime("%j")),
    }


@router.get("/time/now", summary="Current time in one or more timezones")
def now(timezones: str = Query("UTC", description="Comma-separated IANA names")) -> dict:
    ref = datetime.now(UTC)
    zones = [z.strip() for z in timezones.split(",") if z.strip()]
    return {
        "utc": _describe(ref),
        "zones": {z: _describe(ref.astimezone(_zone(z))) for z in zones},
    }


@router.get("/time/convert", summary="Parse any timestamp and express it in a target timezone")
def convert(value: str, to_timezone: str = "UTC", assume_timezone: str = "UTC") -> dict:
    value = value.strip()
    try:
        if value.isdigit() or (value.startswith("-") and value[1:].isdigit()):
            n = int(value)
            secs = n / 1000 if abs(n) > 10_000_000_000 else n
            dt = datetime.fromtimestamp(secs, tz=UTC)
        else:
            dt = dtparser.parse(value)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=_zone(assume_timezone))
    except (ValueError, OverflowError, dtparser.ParserError) as exc:
        raise ToolError(f"Could not parse timestamp {value!r}: {exc}") from exc
    target = dt.astimezone(_zone(to_timezone))
    return {"input": value, "parsed_utc": dt.astimezone(UTC).isoformat(), "result": _describe(target)}


@router.get("/cron/next", summary="Next N run times for a cron expression")
def cron_next(
    expression: str,
    count: int = Query(5, ge=1, le=50),
    timezone: str = "UTC",
    after: str | None = None,
) -> dict:
    from croniter import CroniterBadCronError, croniter

    base = dtparser.parse(after) if after else datetime.now(_zone(timezone))
    if base.tzinfo is None:
        base = base.replace(tzinfo=_zone(timezone))
    try:
        it = croniter(expression, base)
    except (CroniterBadCronError, ValueError) as exc:
        raise ToolError(f"Invalid cron expression: {exc}") from exc
    runs = [it.get_next(datetime).isoformat() for _ in range(count)]
    return {"expression": expression, "timezone": timezone, "next": runs}


@router.get("/duration/humanize", summary="Turn a number of seconds into a human string")
def humanize(seconds: float) -> dict:
    neg = seconds < 0
    s = abs(int(seconds))
    parts = []
    for label, size in (("d", 86400), ("h", 3600), ("m", 60), ("s", 1)):
        if s >= size or (label == "s" and not parts):
            parts.append(f"{s // size}{label}")
            s %= size
    td = timedelta(seconds=abs(seconds))
    return {"human": ("-" if neg else "") + " ".join(parts), "iso8601": _iso_duration(td), "total_seconds": seconds}


def _iso_duration(td: timedelta) -> str:
    total = int(td.total_seconds())
    d, rem = divmod(total, 86400)
    h, rem = divmod(rem, 3600)
    m, sec = divmod(rem, 60)
    out = "P" + (f"{d}D" if d else "")
    t = "".join(x for x in (f"{h}H" if h else "", f"{m}M" if m else "", f"{sec}S" if sec else "") if x)
    return out + (f"T{t}" if t else "") if (d or t) else "PT0S"


register(
    ToolInfo(
        key="time",
        title="Time & scheduling",
        category="Time & colour",
        description="Now in many timezones, timestamp parsing/conversion, cron next-runs, duration humanising.",
        router=router,
        endpoints=[
            Endpoint("GET", "/v1/time/now", "Current time", "?timezones=Europe/Istanbul,UTC"),
            Endpoint("GET", "/v1/time/convert", "Convert timestamp", "?value=1700000000&to_timezone=Europe/Istanbul"),
            Endpoint("GET", "/v1/cron/next", "Cron next runs", "?expression=*/15 * * * *&count=3"),
            Endpoint("GET", "/v1/duration/humanize", "Humanize seconds", "?seconds=93784"),
        ],
    )
)
