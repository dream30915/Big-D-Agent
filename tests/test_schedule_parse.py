import pytest

from src.scheduler.parse import SpecError, describe, parse_spec


def test_interval_minutes():
    assert parse_spec("every 30m") == ("interval", "1800")


def test_interval_hours():
    assert parse_spec("every 2h") == ("interval", "7200")


def test_interval_too_short_rejected():
    with pytest.raises(SpecError):
        parse_spec("every 0m")


def test_daily():
    assert parse_spec("daily 09:00") == ("daily", "09:00")


def test_daily_bad_time():
    with pytest.raises(SpecError):
        parse_spec("daily 99:99")


def test_cron_valid():
    assert parse_spec("cron 0 9 * * *") == ("cron", "0 9 * * *")


def test_cron_wrong_field_count():
    with pytest.raises(SpecError):
        parse_spec("cron 0 9 * *")


def test_unknown_spec():
    with pytest.raises(SpecError):
        parse_spec("sometimes maybe")


def test_case_insensitive():
    assert parse_spec("EVERY 1H") == ("interval", "3600")


def test_describe_interval_and_daily():
    assert "ชม." in describe("interval", "7200")
    assert "09:00" in describe("daily", "09:00")


def test_describe_interval_days():
    # 'every 1d' -> 86400s should read as days, not "24 ชม."
    assert describe("interval", "86400") == "ทุก 1 วัน"
    assert describe("interval", "172800") == "ทุก 2 วัน"


def test_describe_interval_minutes():
    assert describe("interval", "1800") == "ทุก 30 นาที"
