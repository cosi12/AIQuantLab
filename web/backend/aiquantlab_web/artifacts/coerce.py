"""宽松取值助手。

artifact 是不可变历史记录，可能使用旧 schema。这些助手在字段缺失或类型不符时返回
None 而不是抛异常，使旧实验仍然可以在界面上被浏览。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any


def as_dict(payload: Any, key: str) -> dict[str, Any]:
    value = payload.get(key) if isinstance(payload, dict) else None
    return value if isinstance(value, dict) else {}


def as_list(payload: Any, key: str) -> list[Any]:
    value = payload.get(key) if isinstance(payload, dict) else None
    return list(value) if isinstance(value, list) else []


def as_dict_list(payload: Any, key: str) -> list[dict[str, Any]]:
    return [item for item in as_list(payload, key) if isinstance(item, dict)]


def as_str(payload: Any, key: str, default: str | None = None) -> str | None:
    value = payload.get(key) if isinstance(payload, dict) else None
    if isinstance(value, str) and value:
        return value
    return default


def as_required_str(payload: Any, key: str, fallback: str) -> str:
    return as_str(payload, key) or fallback


def as_int(payload: Any, key: str) -> int | None:
    value = payload.get(key) if isinstance(payload, dict) else None
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return None


def as_float(payload: Any, key: str) -> float | None:
    value = payload.get(key) if isinstance(payload, dict) else None
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return float(value)
    return None


def as_bool(payload: Any, key: str) -> bool | None:
    value = payload.get(key) if isinstance(payload, dict) else None
    return value if isinstance(value, bool) else None


def as_str_list(payload: Any, key: str) -> list[str]:
    return [item for item in as_list(payload, key) if isinstance(item, str)]


def as_datetime(payload: Any, key: str) -> datetime | None:
    value = payload.get(key) if isinstance(payload, dict) else None
    return parse_datetime(value)


def parse_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if not isinstance(value, str) or not value:
        return None
    text = value.replace("Z", "+00:00") if value.endswith("Z") else value
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def as_float_pair(payload: Any, key: str) -> tuple[float, float] | None:
    value = payload.get(key) if isinstance(payload, dict) else None
    if not isinstance(value, list | tuple) or len(value) != 2:
        return None
    if not all(isinstance(item, int | float) and not isinstance(item, bool) for item in value):
        return None
    return (float(value[0]), float(value[1]))
