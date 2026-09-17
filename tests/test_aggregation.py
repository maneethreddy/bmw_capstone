from src.aggregation.window_aggregator import aggregate_events_by_window


EVENTS = [
    {
        "vehicle_id": "BMW-100",
        "timestamp": "2026-09-17T10:00:00+00:00",
        "speed": 50,
        "battery_level": 90,
        "temperature": 42,
        "fault_code": "NONE",
    },
    {
        "vehicle_id": "BMW-100",
        "timestamp": "2026-09-17T10:00:30+00:00",
        "speed": 70,
        "battery_level": 80,
        "temperature": 48,
        "fault_code": "TEMP_HIGH",
    },
    {
        "vehicle_id": "BMW-100",
        "timestamp": "2026-09-17T10:04:00+00:00",
        "speed": 60,
        "battery_level": 70,
        "temperature": 45,
        "fault_code": "NONE",
    },
    {
        "vehicle_id": "BMW-200",
        "timestamp": "2026-09-17T10:00:10+00:00",
        "speed": 40,
        "battery_level": 85,
        "temperature": 35,
        "fault_code": "NONE",
    },
    {
        "vehicle_id": "BMW-100",
        "timestamp": "2026-09-17T10:05:00+00:00",
        "speed": 80,
        "battery_level": 65,
        "temperature": 50,
        "fault_code": "BATTERY_LOW",
    },
]


def test_aggregate_events_by_window_returns_summary_metrics():
    summaries = aggregate_events_by_window(EVENTS, window_seconds=300)

    assert len(summaries) >= 2
    assert all("vehicle_id" in summary for summary in summaries)
    assert all("window_start" in summary for summary in summaries)
    assert all("avg_speed" in summary for summary in summaries)
    assert all("avg_battery_level" in summary for summary in summaries)
    assert all("max_temperature" in summary for summary in summaries)
    assert all("fault_count" in summary for summary in summaries)

    bmw_100 = next(item for item in summaries if item["vehicle_id"] == "BMW-100")
    assert bmw_100["fault_count"] >= 1
    assert bmw_100["avg_speed"] > 0
    assert bmw_100["max_temperature"] >= 42


def test_aggregate_events_by_window_honors_window_duration():
    summaries = aggregate_events_by_window(EVENTS, window_seconds=300)

    bmw_100_windows = [item for item in summaries if item["vehicle_id"] == "BMW-100"]

    assert len(bmw_100_windows) == 2
    assert bmw_100_windows[0]["event_count"] == 3
    assert bmw_100_windows[1]["event_count"] == 1
