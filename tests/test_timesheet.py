from __future__ import annotations

import datetime as dt
from pathlib import Path

import pytest

from timesheet import (
    format_duration,
    format_hhmm,
    get_day_suffix,
    month_range,
    round_minutes,
    split_by_period,
    task_key,
    week_label,
    week_minutes,
    week_number,
    week_start,
    weekly_table_data,
)

TYPE_CHECKING = False
if TYPE_CHECKING:
    from typing import Any


def make_row(
    date: str,
    duration: str,
    task: str = "Task A",
    client: str = "Client A",
    project: str = "Project A",
) -> dict[str, Any]:
    return {
        "Description": task,
        "Duration": duration,
        "Start date": date,
        "Client": client,
        "Project": project,
    }


class TestRoundMinutes:
    @pytest.mark.parametrize(
        "duration, expected",
        [
            (dt.timedelta(0), 0),
            (dt.timedelta(seconds=29), 0),
            (dt.timedelta(seconds=31), 1),
            (dt.timedelta(seconds=30), 0),  # ties to even
            (dt.timedelta(seconds=90), 2),  # ties to even
            (dt.timedelta(hours=2, minutes=5, seconds=29), 125),
            (dt.timedelta(hours=144, minutes=25), 8665),
        ],
    )
    def test_round(self, duration: dt.timedelta, expected: int) -> None:
        assert round_minutes(duration) == expected


class TestFormatDuration:
    @pytest.mark.parametrize(
        "duration, expected",
        [
            (dt.timedelta(0), "00:00"),
            (dt.timedelta(minutes=2), "00:02"),
            (dt.timedelta(hours=1, minutes=34), "01:34"),
            (dt.timedelta(minutes=59, seconds=40), "01:00"),  # rounds up
            (dt.timedelta(hours=144, minutes=25), "144:25"),
        ],
    )
    def test_format(self, duration: dt.timedelta, expected: str) -> None:
        assert format_duration(duration) == expected


class TestFormatHhmm:
    @pytest.mark.parametrize(
        "minutes, expected",
        [
            (0, "0:00"),
            (62, "1:02"),
            (1920, "32:00"),
            (8665, "144:25"),
        ],
    )
    def test_format(self, minutes: int, expected: str) -> None:
        assert format_hhmm(minutes) == expected


class TestWeekStart:
    @pytest.mark.parametrize(
        "date, expected",
        [
            (dt.date(2026, 8, 3), dt.date(2026, 8, 3)),  # Monday
            (dt.date(2026, 8, 5), dt.date(2026, 8, 3)),  # Wednesday
            (dt.date(2026, 8, 9), dt.date(2026, 8, 3)),  # Sunday
            (dt.date(2026, 8, 1), dt.date(2026, 7, 27)),  # Saturday, month spans
        ],
    )
    def test_monday(self, date: dt.date, expected: dt.date) -> None:
        assert week_start(date) == expected


class TestWeekNumber:
    @pytest.mark.parametrize(
        "week, expected",
        [
            (dt.date(2026, 7, 27), 31),
            (dt.date(2026, 8, 3), 32),
        ],
    )
    def test_iso_week(self, week: dt.date, expected: int) -> None:
        assert week_number(week) == expected


class TestWeekLabel:
    @pytest.mark.parametrize(
        "week, expected",
        [
            # Week entirely within the period
            (dt.date(2026, 8, 3), "2026-08-03 - 2026-08-09"),
            # Weeks clipped to the period's first and last days
            (dt.date(2026, 7, 27), "2026-08-01 - 2026-08-02"),
            (dt.date(2026, 8, 31), "2026-08-31 - 2026-08-31"),
        ],
    )
    def test_label(self, week: dt.date, expected: str) -> None:
        assert week_label(week, dt.date(2026, 8, 1), dt.date(2026, 8, 31)) == expected


class TestMonthRange:
    @pytest.mark.parametrize(
        "filename, expected",
        [
            ("toggl-2026-08.csv", (dt.date(2026, 8, 1), dt.date(2026, 8, 31))),
            ("toggl-2026-02.csv", (dt.date(2026, 2, 1), dt.date(2026, 2, 28))),
            ("toggl-2026-12.csv", (dt.date(2026, 12, 1), dt.date(2026, 12, 31))),
        ],
    )
    def test_month_bounds(
        self, filename: str, expected: tuple[dt.date, dt.date]
    ) -> None:
        assert month_range(Path(filename)) == expected

    @pytest.mark.parametrize(
        "filename",
        [
            "toggl-2026-08-32h.csv",
            "Toggl_time_entries_2026-08-01_to_2026-08-31.csv",
        ],
    )
    def test_other_filenames(self, filename: str) -> None:
        assert month_range(Path(filename)) is None


class TestTaskKey:
    def test_groups_by_date_client_project_and_task(self) -> None:
        # Arrange
        row = make_row("2026-08-03", "1:00:00")

        # Act
        key = task_key(row)

        # Assert
        assert key == ("2026-08-03", "Client A", "Project A", "Task A")


class TestSplitByPeriod:
    def test_splits_on_inclusive_bounds(self) -> None:
        # Arrange
        data = [
            make_row("2026-08-31", "1:00:00"),
            make_row("2026-09-01", "1:00:00"),
            make_row("2026-09-30", "1:00:00"),
            make_row("2026-10-01", "1:00:00"),
        ]

        # Act
        inside, outside = split_by_period(
            data, dt.date(2026, 9, 1), dt.date(2026, 9, 30)
        )

        # Assert
        assert [row["Start date"] for row in inside] == ["2026-09-01", "2026-09-30"]
        assert [row["Start date"] for row in outside] == ["2026-08-31", "2026-10-01"]


class TestWeekMinutes:
    def test_sums_task_rows_before_rounding(self) -> None:
        # Arrange
        # Two 40-second entries of the same task row round together
        # (80s -> 1 minute), not separately (2 x 1 minute)
        data = [
            make_row("2026-08-03", "0:00:40"),
            make_row("2026-08-03", "0:00:40"),
            make_row("2026-08-04", "1:00:00", task="Task B"),
        ]

        # Act / Assert
        assert week_minutes(data) == {dt.date(2026, 8, 3): 61}

    def test_totals_per_week(self) -> None:
        # Arrange
        # 2026-08-09 is a Sunday and 2026-08-10 a Monday
        data = [
            make_row("2026-08-09", "1:00:00"),
            make_row("2026-08-10", "2:00:00"),
        ]

        # Act / Assert
        assert week_minutes(data) == {
            dt.date(2026, 8, 3): 60,
            dt.date(2026, 8, 10): 120,
        }


class TestGetDaySuffix:
    @pytest.mark.parametrize(
        "day, expected",
        [
            (1, "st"),
            (2, "nd"),
            (3, "rd"),
            (4, "th"),
            (11, "th"),
            (12, "th"),
            (13, "th"),
            (20, "th"),
            (21, "st"),
            (22, "nd"),
            (23, "rd"),
            (24, "th"),
            (30, "th"),
            (31, "st"),
        ],
    )
    def test_suffix(self, day: int, expected: str) -> None:
        assert get_day_suffix(day) == expected


class TestWeeklyTableData:
    def test_rows(self) -> None:
        # Arrange
        # Week 36 starts Mon 2026-08-31, week 40 ends Sun 2026-10-04
        minutes = {dt.date(2026, 9, 28): 1556, dt.date(2026, 8, 31): 1287}
        first, last = dt.date(2026, 9, 1), dt.date(2026, 9, 30)

        # Act
        rows = weekly_table_data(minutes, first, last)

        # Assert
        assert rows == [
            ["Week", "Dates", "h:mm", "hh.dd"],
            ["36", "2026-09-01 - 2026-09-06", "21:27", "21.45"],
            ["40", "2026-09-28 - 2026-09-30", "25:56", "25.93"],
            ["", "Total", "47:23", "47.38"],
        ]

    def test_empty(self) -> None:
        assert weekly_table_data({}, dt.date(2026, 9, 1), dt.date(2026, 9, 30)) == [
            ["Week", "Dates", "h:mm", "hh.dd"],
            ["", "Total", "0:00", "0.00"],
        ]
