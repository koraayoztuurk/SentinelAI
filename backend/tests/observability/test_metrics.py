"""Tests for the operational metrics registry (ES-031)."""

from app.observability.metrics import PlatformMetrics


def test_records_and_renders_request_counter() -> None:
    m = PlatformMetrics()
    m.record_request("get", 200, 1.5)
    m.record_request("GET", 200, 2.5)
    m.record_request("POST", 201, 4.0)

    text = m.render()

    assert 'sentinelai_requests_total{method="GET",status="200"} 2' in text
    assert 'sentinelai_requests_total{method="POST",status="201"} 1' in text
    assert "sentinelai_request_duration_ms_sum 8.000" in text
    assert "sentinelai_request_duration_ms_count 3" in text


def test_render_includes_uptime_and_prometheus_types() -> None:
    text = PlatformMetrics().render()
    assert "# TYPE sentinelai_requests_total counter" in text
    assert "sentinelai_uptime_seconds" in text
    assert text.endswith("\n")
