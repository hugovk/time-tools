from __future__ import annotations

import datetime as dt

import pytest

from timesheet import (
    cap_weekly_hours,
    format_duration,
    format_hhmm,
    format_hms,
    format_hours,
    get_day_suffix,
    round_minutes,
    task_key,
    week_label,
    week_minutes,
    week_number,
    week_start,
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


class TestFormatHms:
    @pytest.mark.parametrize(
        "duration, expected",
        [
            (dt.timedelta(0), "0:00:00"),
            (dt.timedelta(hours=1, minutes=2, seconds=3), "1:02:03"),
            (dt.timedelta(minutes=39, seconds=40), "0:39:40"),
            (dt.timedelta(hours=30), "30:00:00"),
        ],
    )
    def test_format(self, duration: dt.timedelta, expected: str) -> None:
        assert format_hms(duration) == expected


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


class TestFormatHours:
    @pytest.mark.parametrize(
        "minutes, expected",
        [
            (105, "    1:45    1.75"),
            (1920, "   32:00   32.00"),
        ],
    )
    def test_format(self, minutes: int, expected: str) -> None:
        assert format_hours(minutes) == expected


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


class TestTaskKey:
    def test_groups_by_date_client_project_and_task(self) -> None:
        # Arrange
        row = make_row("2026-08-03", "1:00:00")

        # Act
        key = task_key(row)

        # Assert
        assert key == ("2026-08-03", "Client A", "Project A", "Task A")


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


class TestCapWeeklyHours:
    @pytest.mark.parametrize(
        "data, max_hours, expected",
        [
            pytest.param(
                [
                    make_row("2026-08-03", "8:00:00"),
                    make_row("2026-08-04", "7:59:59", task="Task B"),
                ],
                32,
                [("2026-08-03", "8:00:00"), ("2026-08-04", "7:59:59")],
                id="under-cap-unchanged",
            ),
            # Mon-Sun week of 2026-08-03: 30h + 4h crosses a 32h cap
            pytest.param(
                [
                    make_row("2026-08-03", "30:00:00"),
                    make_row("2026-08-04", "4:00:00", task="Task B"),
                ],
                32,
                [("2026-08-03", "30:00:00"), ("2026-08-04", "2:00:00")],
                id="trims-entry-crossing-cap",
            ),
            pytest.param(
                [
                    make_row("2026-08-03", "30:00:00"),
                    make_row("2026-08-04", "2:00:00", task="Task B"),
                    make_row("2026-08-05", "1:00:00", task="Task C"),
                ],
                32,
                [("2026-08-03", "30:00:00"), ("2026-08-04", "2:00:00")],
                id="drops-entries-after-cap",
            ),
            # 2026-08-09 is a Sunday and 2026-08-10 a Monday
            pytest.param(
                [
                    make_row("2026-08-03", "33:00:00"),
                    make_row("2026-08-09", "1:00:00", task="Task B"),
                    make_row("2026-08-10", "33:00:00"),
                ],
                32,
                [("2026-08-03", "32:00:00"), ("2026-08-10", "32:00:00")],
                id="caps-each-week-independently",
            ),
            pytest.param(
                [
                    make_row("2026-08-05", "4:00:00", task="Task B"),
                    make_row("2026-08-03", "30:00:00"),
                ],
                32,
                [("2026-08-03", "30:00:00"), ("2026-08-05", "2:00:00")],
                id="entries-processed-chronologically",
            ),
            # Two entries of the same task row (same date, client, project and
            # task): the trim lands the row's rounded duration exactly on the
            # cap, accounting for the first entry's seconds
            pytest.param(
                [
                    make_row("2026-08-03", "0:20:20"),
                    make_row("2026-08-03", "0:50:00"),
                ],
                1,
                [("2026-08-03", "0:20:20"), ("2026-08-03", "0:39:40")],
                id="trim-lands-task-row-on-whole-minutes",
            ),
            # First task row displays as 20 minutes, leaving 40 for the second
            pytest.param(
                [
                    make_row("2026-08-03", "0:20:20"),
                    make_row("2026-08-04", "0:50:00", task="Task B"),
                ],
                1,
                [("2026-08-03", "0:20:20"), ("2026-08-04", "0:40:00")],
                id="trim-counts-other-rounded-task-rows",
            ),
            pytest.param(
                [
                    make_row("2026-08-03", "32:00:00"),
                    make_row("2026-08-04", "1:00:00", task="Task B"),
                ],
                32,
                [("2026-08-03", "32:00:00")],
                id="drops-entry-trimmed-to-nothing",
            ),
        ],
    )
    def test_cap(
        self,
        data: list[dict[str, Any]],
        max_hours: int,
        expected: list[tuple[str, str]],
    ) -> None:
        # Act
        capped = cap_weekly_hours(data, max_hours)

        # Assert
        assert [(row["Start date"], row["Duration"]) for row in capped] == expected

    def test_preserves_other_columns(self) -> None:
        # Arrange
        data = [make_row("2026-08-03", "33:00:00") | {"Email": "user@example.com"}]

        # Act
        capped = cap_weekly_hours(data, 32)

        # Assert
        assert capped[0]["Email"] == "user@example.com"
        assert capped[0]["Client"] == "Client A"
        assert capped[0]["Project"] == "Project A"
        assert capped[0]["Description"] == "Task A"

    def test_does_not_mutate_input(self) -> None:
        # Arrange
        data = [make_row("2026-08-03", "33:00:00")]

        # Act
        cap_weekly_hours(data, 32)

        # Assert
        assert data[0]["Duration"] == "33:00:00"


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
