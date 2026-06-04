import socket

from tools.registry import ToolRegistry
from web.server import build_dashboard_payload, choose_port, stream_dashboard_events


def test_choose_port_falls_back_when_requested_port_busy():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        busy_port = int(sock.getsockname()[1])

        chosen = choose_port("127.0.0.1", busy_port)

    assert chosen != busy_port
    assert chosen > 0


def test_choose_port_zero_returns_available_port():
    chosen = choose_port("127.0.0.1", 0)
    assert chosen > 0


def test_dashboard_payload_shows_apartment_goal_progress():
    payload = build_dashboard_payload(
        "Find apartment under 4000 AED near metro", ToolRegistry()
    )

    assert payload["goal_parser"]["intent"] == "property_search"
    assert payload["capability_manager"]["required_capabilities"] == ["property_search"]
    assert payload["tool_registry"]["selected_tool"] == "apartment_search_mock"
    assert payload["tool_execution"]["execution_status"] == "success"
    assert len(payload["evidence_store"]["evidence"]) == 3
    assert payload["goal_validator"]["goal_status"] == "partially_achieved"

    valid_titles = {item["title"] for item in payload["goal_validator"]["valid_results"]}
    rejected_titles = {
        item["title"] for item in payload["goal_validator"]["rejected_results"]
    }
    unknown_titles = {
        item["title"] for item in payload["goal_validator"]["unknown_results"]
    }
    assert valid_titles == {"Apartment A"}
    assert rejected_titles == {"Apartment B"}
    assert unknown_titles == {"Apartment C"}


def test_dashboard_stream_events_include_required_lifecycle_events():
    events, payload = stream_dashboard_events(
        "Find apartment under 4000 AED near metro", ToolRegistry()
    )

    event_names = {event["event"] for event in events}
    assert {
        "request_received",
        "goal_parsed",
        "planning_started",
        "planning_finished",
        "tool_selected",
        "tool_started",
        "tool_finished",
        "validation_started",
        "validation_finished",
        "response_generated",
    }.issubset(event_names)
    assert payload["user_view"]["current_status"] == "partially_achieved"

    for event in events:
        assert event["timestamp"]
        assert "duration_ms" in event
        assert event["status"]
        assert event["details"]
