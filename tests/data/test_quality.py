from __future__ import annotations

import pandas as pd

from aiquantlab.data.models import CalendarPolicy, Timeframe
from aiquantlab.data.quality import ValidationOptions, validate_ohlcv


def issue_codes(report) -> set[str]:
    return {issue.code for issue in report.issues}


def test_valid_frame_passes(canonical_frame) -> None:
    report = validate_ohlcv(
        canonical_frame,
        ValidationOptions(timeframe=Timeframe.M15),
    )

    assert report.passed
    assert report.error_count == 0
    assert report.missing_candle_count == 0


def test_validation_reports_duplicates_order_and_invalid_ohlc(canonical_frame) -> None:
    bad = canonical_frame.copy()
    bad.loc[2, "high"] = bad.loc[2, "open"] - 1
    bad = pd.concat([bad.iloc[:4], bad.iloc[[2]], bad.iloc[4:]], ignore_index=True)

    report = validate_ohlcv(bad, ValidationOptions(timeframe=Timeframe.M15))

    assert not report.passed
    assert {"duplicate_timestamp", "timestamp_out_of_order", "invalid_high"} <= issue_codes(
        report
    )


def test_missing_candle_is_warning_until_vendor_session_is_confirmed(canonical_frame) -> None:
    with_gap = canonical_frame.drop(index=3).reset_index(drop=True)

    report = validate_ohlcv(
        with_gap,
        ValidationOptions(
            timeframe=Timeframe.M15,
            calendar_policy=CalendarPolicy.WEEKDAYS,
        ),
    )

    assert report.passed
    assert report.missing_candle_count == 1
    assert "missing_candle" in issue_codes(report)


def test_weekday_calendar_does_not_report_closed_weekend() -> None:
    frame = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(
                ["2024-01-05 23:45:00+00:00", "2024-01-08 00:00:00+00:00"], utc=True
            ),
            "open": [2000.0, 2001.0],
            "high": [2002.0, 2003.0],
            "low": [1999.0, 2000.0],
            "close": [2001.0, 2002.0],
            "volume": [10.0, 12.0],
        }
    )

    report = validate_ohlcv(frame, ValidationOptions(timeframe=Timeframe.M15))

    assert report.missing_candle_count == 0


def test_naive_timestamps_fail_utc_contract(canonical_frame) -> None:
    naive = canonical_frame.copy()
    naive["timestamp"] = naive["timestamp"].dt.tz_localize(None)

    report = validate_ohlcv(naive, ValidationOptions(timeframe=Timeframe.M15))

    assert not report.passed
    assert "timestamp_not_utc" in issue_codes(report)

