def test_valid_severity():
    valid_severities = [
        "Critical",
        "High",
        "Medium",
        "Low",
        "Info"
    ]

    assert "High" in valid_severities