import pytest

from client.talk2mcp import AgentDirective, parse_agent_line


def test_parse_function_call_basic():
    directive = parse_agent_line("FUNCTION_CALL: draw_rectangle|100|200|300|400")
    assert directive == AgentDirective(
        kind="function_call",
        name="draw_rectangle",
        arguments=["100", "200", "300", "400"],
    )


def test_parse_final_answer():
    directive = parse_agent_line("FINAL_ANSWER: [done]")
    assert directive.kind == "final_answer"
    assert directive.name is None
    assert directive.arguments is None


def test_parse_invalid_line():
    with pytest.raises(ValueError):
        parse_agent_line("SAY: hello world")


def test_parse_strips_whitespace():
    directive = parse_agent_line("  FUNCTION_CALL: add_text_in_keynote| Hello world  ")
    assert directive.name == "add_text_in_keynote"
    assert directive.arguments == ["Hello world"]
