"""Canonical tabular schema for OHLCV bars."""

TIMESTAMP_COLUMN = "timestamp"
PRICE_COLUMNS = ("open", "high", "low", "close")
NUMERIC_COLUMNS = (*PRICE_COLUMNS, "volume")
OHLCV_COLUMNS = (TIMESTAMP_COLUMN, *NUMERIC_COLUMNS)

