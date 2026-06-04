from tools.apartment_mock import ApartmentSearchMockTool


def test_apartment_search_mock_returns_valid_invalid_and_unknown_examples():
    result = ApartmentSearchMockTool().run()

    assert result.success
    apartments = result.output["apartments"]
    assert len(apartments) == 3

    by_id = {apartment["id"]: apartment for apartment in apartments}
    assert by_id["apt_a"]["price"] == 3500
    assert by_id["apt_a"]["currency"] == "AED"
    assert by_id["apt_a"]["metro_distance"] == 500

    assert by_id["apt_b"]["price"] == 4500
    assert by_id["apt_b"]["metro_distance"] == 300

    assert by_id["apt_c"]["price"] == 3800
    assert by_id["apt_c"]["metro_distance"] is None

    for apartment in apartments:
        assert apartment["title"]
        assert apartment["location"]
        assert apartment["source"].startswith("mock://")
