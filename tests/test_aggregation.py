"""Unit tests for the Python window aggregation helper.

The ``aggregate_events_by_window`` function is used in unit tests to verify
business logic in pure Python without requiring a JVM or a live Kafka broker.
The PySpark streaming pipeline uses the equivalent Spark functions
(window(), avg(), max(), sum(when())) — see tests/test_spark_pipeline.py.
"""

from src.aggregation.window_aggregator import aggregate_events_by_window


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

FIVE_MIN_WINDOW = 300  # seconds

EVENTS = [
    # BMW-100: 3 events within a single 5-min window
    {
        "vehicle_id": "BMW-100",
        "timestamp": "2026-09-17T10:00:00+00:00",
        "speed": 60.0,
        "battery_level": 80.0,
        "temperature": 40.0,
        "fault_code": "NONE",
    },
    {
        "vehicle_id": "BMW-100",
        "timestamp": "2026-09-17T10:01:00+00:00",
        "speed": 100.0,
        "battery_level": 60.0,
        "temperature": 50.0,
        "fault_code": "TEMP_HIGH",
    },
    {
        "vehicle_id": "BMW-100",
        "timestamp": "2026-09-17T10:02:00+00:00",
        "speed": 80.0,
        "battery_level": 40.0,
        "temperature": 45.0,
        "fault_code": "BATTERY_LOW",
    },
    # BMW-100: 1 event in a second 5-min window (10:05 – 10:10)
    {
        "vehicle_id": "BMW-100",
        "timestamp": "2026-09-17T10:05:00+00:00",
        "speed": 120.0,
        "battery_level": 30.0,
        "temperature": 60.0,
        "fault_code": "ENGINE_FAULT",
    },
    # BMW-200: 2 events in the first 5-min window
    {
        "vehicle_id": "BMW-200",
        "timestamp": "2026-09-17T10:00:10+00:00",
        "speed": 50.0,
        "battery_level": 90.0,
        "temperature": 35.0,
        "fault_code": "NONE",
    },
    {
        "vehicle_id": "BMW-200",
        "timestamp": "2026-09-17T10:03:00+00:00",
        "speed": 70.0,
        "battery_level": 70.0,
        "temperature": 38.0,
        "fault_code": "NONE",
    },
]


def _get(summaries, vehicle_id, window_index=0):
    """Return the nth window summary for the given vehicle."""
    windows = [s for s in summaries if s["vehicle_id"] == vehicle_id]
    return windows[window_index]


# ---------------------------------------------------------------------------
# Business rule: Average Speed
# ---------------------------------------------------------------------------

class TestAverageSpeed:
    def test_avg_speed_single_vehicle_single_window(self):
        """BMW-100 first window: (60 + 100 + 80) / 3 = 80.0"""
        summaries = aggregate_events_by_window(EVENTS, window_seconds=FIVE_MIN_WINDOW)
        result = _get(summaries, "BMW-100", window_index=0)
        assert result["avg_speed"] == 80.0

    def test_avg_speed_second_window(self):
        """BMW-100 second window: only 120 → 120.0"""
        summaries = aggregate_events_by_window(EVENTS, window_seconds=FIVE_MIN_WINDOW)
        result = _get(summaries, "BMW-100", window_index=1)
        assert result["avg_speed"] == 120.0

    def test_avg_speed_second_vehicle(self):
        """BMW-200 first window: (50 + 70) / 2 = 60.0"""
        summaries = aggregate_events_by_window(EVENTS, window_seconds=FIVE_MIN_WINDOW)
        result = _get(summaries, "BMW-200", window_index=0)
        assert result["avg_speed"] == 60.0

    def test_avg_speed_is_rounded_to_two_decimals(self):
        events = [
            {"vehicle_id": "BMW-X", "timestamp": "2026-09-17T10:00:00+00:00",
             "speed": 33.333333, "battery_level": 50, "temperature": 30, "fault_code": "NONE"},
            {"vehicle_id": "BMW-X", "timestamp": "2026-09-17T10:01:00+00:00",
             "speed": 66.666666, "battery_level": 50, "temperature": 30, "fault_code": "NONE"},
        ]
        summaries = aggregate_events_by_window(events, window_seconds=FIVE_MIN_WINDOW)
        assert summaries[0]["avg_speed"] == round((33.333333 + 66.666666) / 2, 2)


# ---------------------------------------------------------------------------
# Business rule: Average Battery Level
# ---------------------------------------------------------------------------

class TestAverageBatteryLevel:
    def test_avg_battery_first_window(self):
        """BMW-100 first window: (80 + 60 + 40) / 3 = 60.0"""
        summaries = aggregate_events_by_window(EVENTS, window_seconds=FIVE_MIN_WINDOW)
        result = _get(summaries, "BMW-100", window_index=0)
        assert result["avg_battery_level"] == 60.0

    def test_avg_battery_second_window(self):
        """BMW-100 second window: 30.0"""
        summaries = aggregate_events_by_window(EVENTS, window_seconds=FIVE_MIN_WINDOW)
        result = _get(summaries, "BMW-100", window_index=1)
        assert result["avg_battery_level"] == 30.0

    def test_avg_battery_second_vehicle(self):
        """BMW-200 first window: (90 + 70) / 2 = 80.0"""
        summaries = aggregate_events_by_window(EVENTS, window_seconds=FIVE_MIN_WINDOW)
        result = _get(summaries, "BMW-200", window_index=0)
        assert result["avg_battery_level"] == 80.0


# ---------------------------------------------------------------------------
# Business rule: Maximum Temperature
# ---------------------------------------------------------------------------

class TestMaximumTemperature:
    def test_max_temp_first_window(self):
        """BMW-100 first window: max(40, 50, 45) = 50.0"""
        summaries = aggregate_events_by_window(EVENTS, window_seconds=FIVE_MIN_WINDOW)
        result = _get(summaries, "BMW-100", window_index=0)
        assert result["max_temperature"] == 50.0

    def test_max_temp_second_window(self):
        """BMW-100 second window: 60.0"""
        summaries = aggregate_events_by_window(EVENTS, window_seconds=FIVE_MIN_WINDOW)
        result = _get(summaries, "BMW-100", window_index=1)
        assert result["max_temperature"] == 60.0

    def test_max_temp_second_vehicle(self):
        """BMW-200 first window: max(35, 38) = 38.0"""
        summaries = aggregate_events_by_window(EVENTS, window_seconds=FIVE_MIN_WINDOW)
        result = _get(summaries, "BMW-200", window_index=0)
        assert result["max_temperature"] == 38.0


# ---------------------------------------------------------------------------
# Business rule: Fault Count
# ---------------------------------------------------------------------------

class TestFaultCount:
    def test_fault_count_first_window(self):
        """BMW-100 first window: NONE, TEMP_HIGH, BATTERY_LOW → 2 faults"""
        summaries = aggregate_events_by_window(EVENTS, window_seconds=FIVE_MIN_WINDOW)
        result = _get(summaries, "BMW-100", window_index=0)
        assert result["fault_count"] == 2

    def test_fault_count_second_window(self):
        """BMW-100 second window: ENGINE_FAULT → 1 fault"""
        summaries = aggregate_events_by_window(EVENTS, window_seconds=FIVE_MIN_WINDOW)
        result = _get(summaries, "BMW-100", window_index=1)
        assert result["fault_count"] == 1

    def test_fault_count_zero_faults(self):
        """BMW-200: both events NONE → 0 faults"""
        summaries = aggregate_events_by_window(EVENTS, window_seconds=FIVE_MIN_WINDOW)
        result = _get(summaries, "BMW-200", window_index=0)
        assert result["fault_count"] == 0


# ---------------------------------------------------------------------------
# Window boundaries and event count
# ---------------------------------------------------------------------------

class TestWindowBoundaries:
    def test_correct_number_of_windows_for_bmw_100(self):
        """BMW-100 events span two 5-min windows."""
        summaries = aggregate_events_by_window(EVENTS, window_seconds=FIVE_MIN_WINDOW)
        bmw100_windows = [s for s in summaries if s["vehicle_id"] == "BMW-100"]
        assert len(bmw100_windows) == 2

    def test_event_count_first_window(self):
        summaries = aggregate_events_by_window(EVENTS, window_seconds=FIVE_MIN_WINDOW)
        result = _get(summaries, "BMW-100", window_index=0)
        assert result["event_count"] == 3

    def test_event_count_second_window(self):
        summaries = aggregate_events_by_window(EVENTS, window_seconds=FIVE_MIN_WINDOW)
        result = _get(summaries, "BMW-100", window_index=1)
        assert result["event_count"] == 1

    def test_multi_vehicle_isolation(self):
        """Each vehicle's windows are independent."""
        summaries = aggregate_events_by_window(EVENTS, window_seconds=FIVE_MIN_WINDOW)
        vehicle_ids = {s["vehicle_id"] for s in summaries}
        assert vehicle_ids == {"BMW-100", "BMW-200"}

    def test_configurable_window_seconds_short(self):
        """60-second window splits 10:00 and 10:01 into separate windows."""
        events = [
            {"vehicle_id": "BMW-T", "timestamp": "2026-09-17T10:00:00+00:00",
             "speed": 50, "battery_level": 80, "temperature": 30, "fault_code": "NONE"},
            {"vehicle_id": "BMW-T", "timestamp": "2026-09-17T10:01:00+00:00",
             "speed": 70, "battery_level": 60, "temperature": 35, "fault_code": "NONE"},
        ]
        summaries = aggregate_events_by_window(events, window_seconds=60)
        assert len(summaries) == 2

    def test_invalid_window_seconds_raises(self):
        import pytest
        with pytest.raises(ValueError):
            aggregate_events_by_window(EVENTS, window_seconds=0)

    def test_output_is_sorted_by_vehicle_then_window(self):
        summaries = aggregate_events_by_window(EVENTS, window_seconds=FIVE_MIN_WINDOW)
        keys = [(s["vehicle_id"], s["window_start"]) for s in summaries]
        assert keys == sorted(keys)
