import pytest
from app.utils.formatters import (
    format_bytes,
    format_progress_bar,
    format_uptime,
    format_status_badge,
    format_health_badge,
    safe_html,
)

def test_format_bytes():
    assert format_bytes(500) == "500.0 B"
    assert format_bytes(1024) == "1.0 KB"
    assert format_bytes(1048576) == "1.0 MB"
    assert format_bytes(1073741824) == "1.0 GB"
    assert format_bytes(1073741824 * 2.5) == "2.5 GB"
    assert format_bytes(-10) == "0.0 B"

def test_format_progress_bar():
    bar_0 = format_progress_bar(0, length=10)
    assert bar_0 == "[░░░░░░░░░░]"
    
    bar_50 = format_progress_bar(50, length=10)
    assert bar_50 == "[█████░░░░░]"

    bar_100 = format_progress_bar(100, length=10)
    assert bar_100 == "[██████████]"

    # Защита от выхода за границы
    assert format_progress_bar(-20, length=10) == "[░░░░░░░░░░]"
    assert format_progress_bar(150, length=10) == "[██████████]"

def test_format_uptime():
    assert format_uptime(45) == "45 сек"
    assert format_uptime(125) == "2 мин 5 сек"
    assert format_uptime(3665) == "1 ч 1 мин"
    assert format_uptime(90000) == "1 дн 1 ч"

def test_format_badges():
    assert "🟢" in format_status_badge("running")
    assert "🔴" in format_status_badge("exited")
    assert "⏸" in format_status_badge("paused")
    
    assert "💚" in format_health_badge("healthy")
    assert "💔" in format_health_badge("unhealthy")
    assert format_health_badge(None) == "—"

def test_safe_html():
    assert safe_html("Hello <world> & 'test'") == "Hello &lt;world&gt; &amp; &#x27;test&#x27;"
    assert safe_html(None) == ""
