"""Rechnen OK counts only when the chat sends the count header."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_chat_rechnen_sends_count_header():
    chat = (ROOT / "src" / "frontend" / "chat.js").read_text(encoding="utf-8")
    assert '"X-Buy-Vs-Rent-Count": "chat"' in chat
    assert chat.count('fetch("/api/compare"') == 1


def test_result_sliders_do_not_send_count_header():
    app = (ROOT / "src" / "frontend" / "app.js").read_text(encoding="utf-8")
    assert "if (options.countRechnen) headers[COMPARE_COUNT_HEADER] = " in app
    assert "run();" in app
    assert "run({ countRechnen: true })" not in app


def test_server_counts_only_with_chat_header():
    from buy_vs_rent.request_counts import compare_counts_as_rechnen

    assert compare_counts_as_rechnen("chat")
    assert not compare_counts_as_rechnen(None)
    assert not compare_counts_as_rechnen("slider")
