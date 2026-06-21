"""Tests for the agent's tools (Step 2).

Each test runs against a pytest `tmp_path`, so nothing touches the real project
or your home directory. We test both the implementation functions directly (for
behaviour) and `execute_tool` (for dispatch + error handling).
"""

import pytest

from agent import tools

# --------------------------------------------------------------------------- #
# read
# --------------------------------------------------------------------------- #


def test_read_returns_contents(tmp_path):
    f = tmp_path / "note.txt"
    f.write_text("hello\nworld\n", encoding="utf-8")
    assert tools._read(str(f)) == "hello\nworld\n"


# --------------------------------------------------------------------------- #
# write
# --------------------------------------------------------------------------- #


def test_write_creates_file(tmp_path):
    f = tmp_path / "out.txt"
    result = tools._write(str(f), "data")
    assert f.read_text(encoding="utf-8") == "data"
    assert "4 characters" in result


def test_write_overwrites_existing(tmp_path):
    f = tmp_path / "out.txt"
    f.write_text("old", encoding="utf-8")
    tools._write(str(f), "new")
    assert f.read_text(encoding="utf-8") == "new"


# --------------------------------------------------------------------------- #
# update
# --------------------------------------------------------------------------- #


def test_update_replaces_text(tmp_path):
    f = tmp_path / "code.py"
    f.write_text("print('Hello')", encoding="utf-8")
    result = tools._update(str(f), "Hello", "Goodbye")
    assert f.read_text(encoding="utf-8") == "print('Goodbye')"
    assert "Replaced 1" in result


def test_update_replaces_all_occurrences(tmp_path):
    f = tmp_path / "code.py"
    f.write_text("a a a", encoding="utf-8")
    result = tools._update(str(f), "a", "b")
    assert f.read_text(encoding="utf-8") == "b b b"
    assert "Replaced 3" in result


def test_update_missing_text_raises(tmp_path):
    f = tmp_path / "code.py"
    f.write_text("hello", encoding="utf-8")
    with pytest.raises(ValueError, match="not found"):
        tools._update(str(f), "absent", "x")


# --------------------------------------------------------------------------- #
# delete
# --------------------------------------------------------------------------- #


def test_delete_removes_file(tmp_path):
    f = tmp_path / "gone.txt"
    f.write_text("bye", encoding="utf-8")
    result = tools._delete(str(f))
    assert not f.exists()
    assert "Deleted" in result


# --------------------------------------------------------------------------- #
# list
# --------------------------------------------------------------------------- #


def test_list_shows_entries_with_dir_slash(tmp_path):
    (tmp_path / "file.txt").write_text("x", encoding="utf-8")
    (tmp_path / "subdir").mkdir()
    result = tools._list(str(tmp_path))
    assert result == "file.txt\nsubdir/"


def test_list_empty_directory(tmp_path):
    result = tools._list(str(tmp_path))
    assert "empty" in result


def test_list_defaults_to_cwd(tmp_path, monkeypatch):
    (tmp_path / "here.txt").write_text("x", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    assert tools._list() == "here.txt"


# --------------------------------------------------------------------------- #
# execute
# --------------------------------------------------------------------------- #


def test_execute_captures_stdout_and_exit_code():
    result = tools._execute("echo hello")
    assert "exit code: 0" in result
    assert "hello" in result


def test_execute_reports_nonzero_exit_and_stderr():
    result = tools._execute("echo oops >&2; exit 3")
    assert "exit code: 3" in result
    assert "oops" in result


def test_execute_runs_in_current_directory(tmp_path, monkeypatch):
    (tmp_path / "marker.txt").write_text("x", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    result = tools._execute("ls")
    assert "marker.txt" in result


# --------------------------------------------------------------------------- #
# execute_tool dispatcher: routing + error handling
# --------------------------------------------------------------------------- #


def test_execute_tool_dispatches_by_name(tmp_path):
    f = tmp_path / "x.txt"
    tools.execute_tool("write", {"path": str(f), "content": "hi"})
    assert tools.execute_tool("read", {"path": str(f)}) == "hi"


def test_execute_tool_unknown_tool():
    assert "unknown tool" in tools.execute_tool("frobnicate", {})


def test_execute_tool_wraps_exceptions(tmp_path):
    # Reading a missing file raises inside the tool; the dispatcher must turn
    # that into an error string instead of propagating.
    result = tools.execute_tool("read", {"path": str(tmp_path / "missing.txt")})
    assert result.startswith("Error:")
    assert "FileNotFoundError" in result


def test_execute_tool_wraps_bad_arguments(tmp_path):
    # Missing required argument -> TypeError from the handler -> error string.
    result = tools.execute_tool("write", {"path": str(tmp_path / "a.txt")})
    assert result.startswith("Error:")


def test_execute_tool_respects_timeout(monkeypatch):
    # Shrink the timeout so a slow command is killed quickly; the dispatcher
    # turns the resulting TimeoutExpired into an error string.
    monkeypatch.setattr(tools, "EXECUTE_TIMEOUT", 0.3)
    result = tools.execute_tool("execute", {"command": "sleep 5"})
    assert result.startswith("Error:")
    assert "Timeout" in result
