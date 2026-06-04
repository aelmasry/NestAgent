import os

from tools.path_guard import PathGuardError, resolve_under_root
from tools.registry import ToolRegistry


def test_resolve_rejects_parent_escape(tmp_path):
    root = tmp_path / "proj"
    root.mkdir()
    try:
        resolve_under_root(root, "../outside")
        assert False, "expected PathGuardError"
    except PathGuardError:
        pass


def test_list_dir_and_read_file(tmp_path):
    root = tmp_path / "proj"
    root.mkdir()
    (root / "hello.txt").write_text("hi", encoding="utf-8")
    os.environ["NESTAGENT_ROOT"] = str(root)

    reg = ToolRegistry(str(root))
    listed = reg.execute("list_dir", path=".", max_depth=1)
    assert listed.success
    paths = {e["path"] for e in listed.output["entries"]}
    assert "hello.txt" in paths

    read = reg.execute("read_file", path="hello.txt")
    assert read.success
    assert read.output["content"] == "hi"
