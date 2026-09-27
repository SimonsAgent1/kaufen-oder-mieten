from buy_vs_rent.compare_limit import allow_compare, reset_compare_limit_for_tests


def test_allow_compare_hand_worked_window(monkeypatch):
    """Three slots in a 10 s window; the fourth at t=9 s is refused."""
    monkeypatch.setattr("buy_vs_rent.compare_limit._WINDOW_SEC", 10.0)
    monkeypatch.setattr("buy_vs_rent.compare_limit._MAX_CALLS", 3)
    reset_compare_limit_for_tests()
    assert allow_compare(100.0) is True
    assert allow_compare(101.0) is True
    assert allow_compare(102.0) is True
    assert allow_compare(109.0) is False
    assert allow_compare(111.0) is True
