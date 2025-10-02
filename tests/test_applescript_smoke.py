from pathlib import Path

import pytest

APPLE_DIR = Path(__file__).resolve().parents[1] / "src" / "mcp_servers" / "applescript"
APPLE_FILES = [
    "open_keynote.applescript",
    "get_slide_size.applescript",
    "draw_rectangle.applescript",
    "add_text_in_keynote.applescript",
    "export_slide_png.applescript",
]


@pytest.mark.parametrize("filename", APPLE_FILES)
def test_applescript_file_present(filename):
    script_path = APPLE_DIR / filename
    assert script_path.exists(), f"Missing AppleScript file: {filename}"
    assert script_path.read_text(encoding="utf-8").strip()
