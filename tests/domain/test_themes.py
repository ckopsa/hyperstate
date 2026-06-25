from datetime import date

import pytest

from app.domain.shared.themes import Theme, WEEKDAY_THEMES, theme_for


# Week beginning Monday 2026-03-16, one date per weekday.
WEEK = {
    "monday": date(2026, 3, 16),
    "tuesday": date(2026, 3, 17),
    "wednesday": date(2026, 3, 18),
    "thursday": date(2026, 3, 19),
    "friday": date(2026, 3, 20),
    "saturday": date(2026, 3, 21),
    "sunday": date(2026, 3, 22),
}


class TestWeekdayThemes:
    def test_covers_all_seven_weekdays_exactly_once(self):
        assert sorted(WEEKDAY_THEMES.keys()) == [0, 1, 2, 3, 4, 5, 6]

    def test_every_theme_used_exactly_once(self):
        themes = list(WEEKDAY_THEMES.values())
        assert len(themes) == len(set(themes)) == len(Theme)

    def test_full_weekday_mapping(self):
        assert WEEKDAY_THEMES == {
            0: Theme.ITALIAN,    # Monday
            1: Theme.MEXICAN,    # Tuesday
            2: Theme.AMERICAN,   # Wednesday
            3: Theme.ASIAN,      # Thursday
            4: Theme.PIZZA,      # Friday
            5: Theme.BBQ,        # Saturday
            6: Theme.ROTATING,   # Sunday
        }


class TestThemeFor:
    @pytest.mark.parametrize(
        "day, expected",
        [
            (WEEK["monday"], Theme.ITALIAN),
            (WEEK["tuesday"], Theme.MEXICAN),
            (WEEK["wednesday"], Theme.AMERICAN),
            (WEEK["thursday"], Theme.ASIAN),
            (WEEK["friday"], Theme.PIZZA),
            (WEEK["saturday"], Theme.BBQ),
            (WEEK["sunday"], Theme.ROTATING),
        ],
    )
    def test_theme_for_each_weekday(self, day, expected):
        assert theme_for(day) == expected

    def test_tuesday_is_mexican(self):
        assert theme_for(WEEK["tuesday"]) == Theme.MEXICAN

    def test_consistent_across_weeks(self):
        # A different Tuesday (2026-06-23) must resolve to the same theme.
        assert theme_for(date(2026, 6, 23)) == theme_for(WEEK["tuesday"])
