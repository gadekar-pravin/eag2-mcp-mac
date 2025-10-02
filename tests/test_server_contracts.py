import importlib
from pathlib import Path

import pytest

mcp_module = importlib.import_module("mcp_servers.mcp_server_keynote")


@pytest.fixture(autouse=True)
def reset_server_state():
    mcp_module.SERVER_STATE["last_rectangle_id"] = None
    mcp_module.SERVER_STATE["last_slide_dims"] = {"width": None, "height": None}


def test_open_keynote_success(monkeypatch):
    monkeypatch.setattr(
        mcp_module,
        "run_applescript_file",
        lambda path, args=None, timeout=15: "1920|1080",
    )

    result = mcp_module.open_keynote()
    assert result == "KEYNOTE_READY: slide=1, slide_width=1920, slide_height=1080"
    assert mcp_module.SERVER_STATE["last_slide_dims"] == {"width": 1920, "height": 1080}


def test_get_slide_size_success(monkeypatch):
    monkeypatch.setattr(
        mcp_module,
        "run_applescript_file",
        lambda path, args=None, timeout=15: "1024|768",
    )
    result = mcp_module.get_slide_size()
    assert result == "SLIDE_SIZE: width=1024, height=768"
    assert mcp_module.SERVER_STATE["last_slide_dims"] == {"width": 1024, "height": 768}


def test_draw_rectangle_updates_state(monkeypatch):
    def fake_runner(path, args=None, timeout=15):
        assert Path(path).name == "draw_rectangle.applescript"
        assert args == ["100", "200", "300", "150"]
        return "RECT-12345"

    monkeypatch.setattr(mcp_module, "run_applescript_file", fake_runner)

    result = mcp_module.draw_rectangle(100, 200, 300, 150)
    assert result == "RECTANGLE_OK: id=RECT-12345, x=100, y=200, width=300, height=150"
    assert mcp_module.SERVER_STATE["last_rectangle_id"] == "RECT-12345"


def test_add_text_requires_rectangle():
    result = mcp_module.add_text_in_keynote("hello")
    assert result == "ERROR: No rectangle context. Call draw_rectangle first."


def test_add_text_success(monkeypatch):
    mcp_module.SERVER_STATE["last_rectangle_id"] = "RECT-1"

    def fake_runner(path, args=None, timeout=15):
        assert args == ["RECT-1", "Hello | world"]
        return "12"

    monkeypatch.setattr(mcp_module, "run_applescript_file", fake_runner)

    result = mcp_module.add_text_in_keynote("Hello ¦ world")
    assert result == "TEXT_OK: id=RECT-1, characters=12"


def test_screenshot_slide_handles_error(monkeypatch):
    from mcp_servers.utils.applescript_runner import AppleScriptError

    def fake_runner(path, args=None, timeout=15):
        raise AppleScriptError("fail")

    monkeypatch.setattr(mcp_module, "run_applescript_file", fake_runner)

    result = mcp_module.screenshot_slide("~/Desktop/test.png")
    assert result == "ERROR: fail"
