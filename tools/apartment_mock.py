"""Mock apartment search data for the NestAgent v2 MVP vertical slice."""

from __future__ import annotations

from typing import Any

from tools.base import Tool, ToolResult


class ApartmentSearchMockTool(Tool):
    name = "apartment_search_mock"
    description = "Return mock apartment listings with valid, rejected, and unknown cases."

    def run(self, **kwargs: Any) -> ToolResult:
        apartments = [
            {
                "id": "apt_a",
                "title": "Apartment A",
                "price": 3500,
                "currency": "AED",
                "metro_distance": 500,
                "location": "Dubai Marina",
                "source": "mock://apartments/apt_a",
            },
            {
                "id": "apt_b",
                "title": "Apartment B",
                "price": 4500,
                "currency": "AED",
                "metro_distance": 300,
                "location": "JLT",
                "source": "mock://apartments/apt_b",
            },
            {
                "id": "apt_c",
                "title": "Apartment C",
                "price": 3800,
                "currency": "AED",
                "metro_distance": None,
                "location": "Deira",
                "source": "mock://apartments/apt_c",
            },
        ]
        return ToolResult(
            success=True,
            output={"apartments": apartments},
            message="mock apartment search completed",
        )
