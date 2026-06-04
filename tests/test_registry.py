from tools.registry import ToolRegistry


def test_builtin_tools_registered():
    reg = ToolRegistry()
    assert reg.has("echo")
    assert reg.has("environment_check")
    assert reg.has("list_dir")
    assert reg.has("read_file")
    assert reg.has("apartment_search_mock")


def test_echo_tool():
    reg = ToolRegistry()
    result = reg.execute("echo", message="hello")
    assert result.success
    assert result.output == {"message": "hello"}
