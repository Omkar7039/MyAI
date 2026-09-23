from core.orchestrator import Orchestrator
from tools.workspace import Workspace


def test_orchestrator_registers_execution_tool():
    orchestrator = Orchestrator()

    assert orchestrator.tool_registry.has(
        "execute_code"
    )


def test_orchestrator_invokes_execution_tool():
    orchestrator = Orchestrator()

    result = orchestrator.invoke_tool(
        "execute_code",
        'print("orchestrator tool")',
        "python",
    )

    assert result.tool_name == "execute_code"
    assert result.success is True
    assert result.result.language == "python"
    assert result.result.stdout.strip() == "orchestrator tool"


def test_orchestrator_tool_preserves_execution_failure():
    orchestrator = Orchestrator()

    result = orchestrator.invoke_tool(
        "execute_code",
        "print(1 / 0)",
        "python",
    )

    assert result.success is True
    assert result.result.success is False
    assert result.result.exit_code != 0


def test_orchestrator_rejects_unknown_tool():
    orchestrator = Orchestrator()

    try:
        orchestrator.invoke_tool(
            "missing_tool",
        )
    except ValueError as exc:
        assert "not registered" in str(exc)
    else:
        raise AssertionError(
            "Unknown tool should be rejected"
        )


def test_orchestrator_registers_read_file_tool():
    orchestrator = Orchestrator()

    assert orchestrator.tool_registry.has("read_file")


def test_orchestrator_invokes_read_file_tool(tmp_path):
    target = tmp_path / "sample.txt"
    target.write_text(
        "hello from orchestrator",
        encoding="utf-8",
    )

    orchestrator = Orchestrator()

    orchestrator.read_file_tool.base_directory = tmp_path

    result = orchestrator.invoke_tool(
        "read_file",
        path="sample.txt",
    )

    assert result.tool_name == "read_file"
    assert result.success is True
    assert result.result == "hello from orchestrator"


def test_orchestrator_read_file_rejects_missing_file(tmp_path):
    orchestrator = Orchestrator()

    orchestrator.read_file_tool.base_directory = tmp_path

    result = orchestrator.invoke_tool(
        "read_file",
        path="missing.txt",
    )

    assert result.success is False
    assert "does not exist" in result.error


def test_orchestrator_registers_list_files_tool():
    orchestrator = Orchestrator()

    assert orchestrator.tool_registry.has("list_files")


def test_orchestrator_invokes_list_files_tool(tmp_path):
    (tmp_path / "main.py").write_text(
        "print('hello')",
        encoding="utf-8",
    )

    orchestrator = Orchestrator()

    orchestrator.list_files_tool.base_directory = tmp_path

    result = orchestrator.invoke_tool(
        "list_files",
        path=".",
    )

    assert result.tool_name == "list_files"
    assert result.success is True
    assert result.result == [
        {
            "name": "main.py",
            "type": "file",
        }
    ]


def test_orchestrator_list_files_uses_default_path(tmp_path):
    (tmp_path / "example.txt").write_text(
        "hello",
        encoding="utf-8",
    )

    orchestrator = Orchestrator()

    orchestrator.list_files_tool.base_directory = tmp_path

    result = orchestrator.invoke_tool(
        "list_files",
    )

    assert result.success is True
    assert result.result == [
        {
            "name": "example.txt",
            "type": "file",
        }
    ]


def test_orchestrator_registers_search_files_tool():
    orchestrator = Orchestrator()

    assert orchestrator.tool_registry.has("search_files")


def test_orchestrator_invokes_search_files_tool(tmp_path):
    target = tmp_path / "main.py"

    target.write_text(
        "def hello():\n"
        "    return 'hello'\n",
        encoding="utf-8",
    )

    orchestrator = Orchestrator()

    orchestrator.search_files_tool.base_directory = tmp_path

    result = orchestrator.invoke_tool(
        "search_files",
        query="hello",
        path=".",
    )

    assert result.tool_name == "search_files"
    assert result.success is True
    assert result.result == [
        {
            "path": "main.py",
            "line": 1,
            "text": "def hello():",
        },
        {
            "path": "main.py",
            "line": 2,
            "text": "    return 'hello'",
        },
    ]


def test_orchestrator_search_files_returns_no_match(tmp_path):
    target = tmp_path / "main.py"

    target.write_text(
        "print('hello')\n",
        encoding="utf-8",
    )

    orchestrator = Orchestrator()

    orchestrator.search_files_tool.base_directory = tmp_path

    result = orchestrator.invoke_tool(
        "search_files",
        query="missing",
    )

    assert result.success is True
    assert result.result == []


def test_orchestrator_filesystem_tools_share_workspace():
    orchestrator = Orchestrator()

    assert orchestrator.read_file_tool.workspace is orchestrator.workspace
    assert orchestrator.list_files_tool.workspace is orchestrator.workspace
    assert orchestrator.search_files_tool.workspace is orchestrator.workspace


def test_orchestrator_registers_write_file():
    orchestrator = Orchestrator()

    assert orchestrator.tool_registry.has("write_file")


def test_orchestrator_write_file_uses_shared_workspace(tmp_path):
    orchestrator = Orchestrator()

    orchestrator.write_file_tool.base_directory = tmp_path

    result = orchestrator.invoke_tool(
        "write_file",
        path="example.txt",
        content="hello",
    )

    assert result.success is True
    assert (
        (tmp_path / "example.txt").read_text(
            encoding="utf-8"
        )
        == "hello"
    )


def test_orchestrator_write_file_rejects_path_escape(tmp_path):
    orchestrator = Orchestrator()

    orchestrator.write_file_tool.base_directory = tmp_path

    result = orchestrator.invoke_tool(
        "write_file",
        path="../outside.txt",
        content="secret",
    )

    assert result.success is False
    assert (
        "outside the allowed base directory"
        in result.error
    )


def test_orchestrator_registers_edit_file():
    orchestrator = Orchestrator()

    assert orchestrator.tool_registry.has("edit_file")


def test_orchestrator_edit_file_uses_shared_workspace(tmp_path):
    orchestrator = Orchestrator()

    orchestrator.edit_file_tool.base_directory = tmp_path

    target = tmp_path / "example.txt"
    target.write_text(
        "before",
        encoding="utf-8",
    )

    result = orchestrator.invoke_tool(
        "edit_file",
        path="example.txt",
        old_text="before",
        new_text="after",
    )

    assert result.success is True
    assert target.read_text(
        encoding="utf-8"
    ) == "after"


def test_orchestrator_edit_file_rejects_ambiguous_edit(tmp_path):
    orchestrator = Orchestrator()

    orchestrator.edit_file_tool.base_directory = tmp_path

    target = tmp_path / "example.txt"
    target.write_text(
        "same\nsame\n",
        encoding="utf-8",
    )

    result = orchestrator.invoke_tool(
        "edit_file",
        path="example.txt",
        old_text="same",
        new_text="changed",
    )

    assert result.success is False
    assert "occurs multiple times" in result.error


def test_orchestrator_edit_file_rejects_path_escape(tmp_path):
    orchestrator = Orchestrator()

    orchestrator.edit_file_tool.base_directory = tmp_path

    result = orchestrator.invoke_tool(
        "edit_file",
        path="../outside.txt",
        old_text="old",
        new_text="new",
    )

    assert result.success is False
    assert (
        "outside the allowed base directory"
        in result.error
    )


def test_orchestrator_registers_delete_file():
    orchestrator = Orchestrator()

    assert orchestrator.tool_registry.has("delete_file")


def test_orchestrator_delete_file_uses_shared_workspace(tmp_path):
    orchestrator = Orchestrator()

    orchestrator.delete_file_tool.base_directory = tmp_path

    target = tmp_path / "example.txt"
    target.write_text(
        "hello",
        encoding="utf-8",
    )

    result = orchestrator.invoke_tool(
        "delete_file",
        path="example.txt",
    )

    assert result.success is True
    assert result.result["deleted"] is True
    assert not target.exists()


def test_orchestrator_delete_file_rejects_path_escape(tmp_path):
    orchestrator = Orchestrator()

    orchestrator.delete_file_tool.base_directory = tmp_path

    result = orchestrator.invoke_tool(
        "delete_file",
        path="../outside.txt",
    )

    assert result.success is False
    assert (
        "outside the allowed base directory"
        in result.error
    )


def test_orchestrator_registers_create_directory():
    orchestrator = Orchestrator()

    assert orchestrator.tool_registry.has(
        "create_directory"
    )


def test_orchestrator_create_directory_uses_shared_workspace(
    tmp_path,
):
    orchestrator = Orchestrator()

    orchestrator.create_directory_tool.base_directory = tmp_path

    result = orchestrator.invoke_tool(
        "create_directory",
        path="src/core",
    )

    assert result.success is True
    assert (tmp_path / "src/core").is_dir()


def test_orchestrator_create_directory_rejects_path_escape(
    tmp_path,
):
    orchestrator = Orchestrator()

    orchestrator.create_directory_tool.base_directory = tmp_path

    result = orchestrator.invoke_tool(
        "create_directory",
        path="../outside",
    )

    assert result.success is False
    assert (
        "outside the allowed base directory"
        in result.error
    )


def test_orchestrator_registers_move_file():
    orchestrator = Orchestrator()
    assert orchestrator.tool_registry.has("move_file")


def test_orchestrator_move_file_uses_shared_workspace(tmp_path):
    orchestrator = Orchestrator()
    orchestrator.move_file_tool.base_directory = tmp_path

    source = tmp_path / "old.txt"
    source.write_text("hello", encoding="utf-8")

    result = orchestrator.invoke_tool(
        "move_file",
        source="old.txt",
        destination="new.txt",
    )

    assert result.success is True
    assert not source.exists()
    assert (tmp_path / "new.txt").read_text(
        encoding="utf-8"
    ) == "hello"


def test_orchestrator_move_file_rejects_path_escape(tmp_path):
    orchestrator = Orchestrator()
    orchestrator.move_file_tool.base_directory = tmp_path

    result = orchestrator.invoke_tool(
        "move_file",
        source="../outside.txt",
        destination="inside.txt",
    )

    assert result.success is False
    assert "outside the allowed base directory" in result.error


def test_orchestrator_registers_copy_file():
    orchestrator = Orchestrator()
    assert orchestrator.tool_registry.has("copy_file")


def test_orchestrator_copy_file_uses_shared_workspace(tmp_path):
    orchestrator = Orchestrator()
    orchestrator.copy_file_tool.base_directory = tmp_path

    source = tmp_path / "source.txt"
    source.write_text("hello", encoding="utf-8")

    result = orchestrator.invoke_tool(
        "copy_file",
        source="source.txt",
        destination="copy.txt",
    )

    assert result.success is True
    assert source.exists()
    assert (tmp_path / "copy.txt").read_text(
        encoding="utf-8"
    ) == "hello"


def test_orchestrator_copy_file_rejects_path_escape(tmp_path):
    orchestrator = Orchestrator()
    orchestrator.copy_file_tool.base_directory = tmp_path

    result = orchestrator.invoke_tool(
        "copy_file",
        source="../outside.txt",
        destination="inside.txt",
    )

    assert result.success is False
    assert "outside the allowed base directory" in result.error


def test_orchestrator_registers_list_files_tool():
    orchestrator = Orchestrator()

    assert orchestrator.tool_registry.has("list_files")


def test_orchestrator_invokes_list_files_tool(tmp_path):
    (tmp_path / "main.py").write_text(
        "print('hello')",
        encoding="utf-8",
    )

    orchestrator = Orchestrator()

    orchestrator.list_files_tool.base_directory = tmp_path

    result = orchestrator.invoke_tool(
        "list_files",
        path=".",
    )

    assert result.tool_name == "list_files"
    assert result.success is True
    assert result.result == [
        {
            "name": "main.py",
            "type": "file",
        }
    ]


def test_orchestrator_list_files_uses_default_path(tmp_path):
    (tmp_path / "example.txt").write_text(
        "hello",
        encoding="utf-8",
    )

    orchestrator = Orchestrator()

    orchestrator.list_files_tool.base_directory = tmp_path

    result = orchestrator.invoke_tool(
        "list_files",
    )

    assert result.success is True
    assert result.result == [
        {
            "name": "example.txt",
            "type": "file",
        }
    ]


def test_orchestrator_registers_get_file_info():
    orchestrator = Orchestrator()
    assert orchestrator.tool_registry.has("get_file_info")


def test_orchestrator_get_file_info_uses_shared_workspace(tmp_path):
    orchestrator = Orchestrator()
    orchestrator.get_file_info_tool.base_directory = tmp_path

    target = tmp_path / "example.txt"
    target.write_text("hello", encoding="utf-8")

    result = orchestrator.invoke_tool(
        "get_file_info",
        path="example.txt",
    )

    assert result.success is True
    assert result.result["type"] == "file"
    assert result.result["size"] == 5


def test_orchestrator_get_file_info_rejects_path_escape(tmp_path):
    orchestrator = Orchestrator()
    orchestrator.get_file_info_tool.base_directory = tmp_path

    result = orchestrator.invoke_tool(
        "get_file_info",
        path="../outside.txt",
    )

    assert result.success is False
    assert "outside the allowed base directory" in result.error


def test_orchestrator_registers_directory_tree():
    orchestrator = Orchestrator()
    assert orchestrator.tool_registry.has("directory_tree")


def test_orchestrator_directory_tree_uses_shared_workspace(tmp_path):
    orchestrator = Orchestrator()
    orchestrator.directory_tree_tool.base_directory = tmp_path

    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text(
        "hello",
        encoding="utf-8",
    )

    result = orchestrator.invoke_tool(
        "directory_tree",
        path=".",
        max_depth=1,
    )

    assert result.success is True

    paths = [
        entry["path"]
        for entry in result.result["entries"]
    ]

    assert "src" in paths
    assert "src/main.py" in paths


def test_orchestrator_directory_tree_rejects_path_escape(tmp_path):
    orchestrator = Orchestrator()
    orchestrator.directory_tree_tool.base_directory = tmp_path

    result = orchestrator.invoke_tool(
        "directory_tree",
        path="../outside",
    )

    assert result.success is False
    assert "outside the allowed base directory" in result.error


def test_orchestrator_directory_tree_schema_rejects_invalid_depth():
    orchestrator = Orchestrator()

    try:
        orchestrator.invoke_tool(
            "directory_tree",
            path=".",
            max_depth="bad",
        )
    except ValueError as exc:
        assert "must be an integer" in str(exc)
    else:
        raise AssertionError("Expected ValueError.")


def test_orchestrator_registers_file_exists():
    orchestrator = Orchestrator()
    assert orchestrator.tool_registry.has("file_exists")


def test_orchestrator_file_exists_uses_shared_workspace(tmp_path):
    orchestrator = Orchestrator()
    orchestrator.file_exists_tool.base_directory = tmp_path

    (tmp_path / "example.txt").write_text(
        "hello",
        encoding="utf-8",
    )

    result = orchestrator.invoke_tool(
        "file_exists",
        path="example.txt",
    )

    assert result.success is True
    assert result.result["exists"] is True
    assert result.result["type"] == "file"


def test_orchestrator_file_exists_reports_missing_path(tmp_path):
    orchestrator = Orchestrator()
    orchestrator.file_exists_tool.base_directory = tmp_path

    result = orchestrator.invoke_tool(
        "file_exists",
        path="missing.txt",
    )

    assert result.success is True
    assert result.result["exists"] is False


def test_orchestrator_file_exists_rejects_path_escape(tmp_path):
    orchestrator = Orchestrator()
    orchestrator.file_exists_tool.base_directory = tmp_path

    result = orchestrator.invoke_tool(
        "file_exists",
        path="../outside.txt",
    )

    assert result.success is False
    assert "outside the allowed base directory" in result.error


def test_orchestrator_registers_file_hash():
    orchestrator = Orchestrator()
    assert orchestrator.tool_registry.has("file_hash")


def test_orchestrator_file_hash_uses_shared_workspace(tmp_path):
    import hashlib

    orchestrator = Orchestrator()
    orchestrator.file_hash_tool.base_directory = tmp_path

    content = b"hello"
    (tmp_path / "example.txt").write_bytes(content)

    result = orchestrator.invoke_tool(
        "file_hash",
        path="example.txt",
    )

    assert result.success is True
    assert result.result["algorithm"] == "sha256"
    assert result.result["hash"] == hashlib.sha256(content).hexdigest()


def test_orchestrator_file_hash_rejects_path_escape(tmp_path):
    orchestrator = Orchestrator()
    orchestrator.file_hash_tool.base_directory = tmp_path

    result = orchestrator.invoke_tool(
        "file_hash",
        path="../outside.txt",
    )

    assert result.success is False
    assert "outside the allowed base directory" in result.error


def test_orchestrator_read_file_supports_line_range(tmp_path):
    orchestrator = Orchestrator()
    orchestrator.read_file_tool.base_directory = tmp_path

    (tmp_path / "example.txt").write_text(
        "one\ntwo\nthree\nfour\n",
        encoding="utf-8",
    )

    result = orchestrator.invoke_tool(
        "read_file",
        path="example.txt",
        start_line=2,
        end_line=3,
    )

    assert result.success is True
    assert result.result == "two\nthree\n"


def test_orchestrator_read_file_supports_start_line_only(tmp_path):
    orchestrator = Orchestrator()
    orchestrator.read_file_tool.base_directory = tmp_path

    (tmp_path / "example.txt").write_text(
        "one\ntwo\nthree\n",
        encoding="utf-8",
    )

    result = orchestrator.invoke_tool(
        "read_file",
        path="example.txt",
        start_line=2,
    )

    assert result.success is True
    assert result.result == "two\nthree\n"


def test_orchestrator_read_file_supports_end_line_only(tmp_path):
    orchestrator = Orchestrator()
    orchestrator.read_file_tool.base_directory = tmp_path

    (tmp_path / "example.txt").write_text(
        "one\ntwo\nthree\n",
        encoding="utf-8",
    )

    result = orchestrator.invoke_tool(
        "read_file",
        path="example.txt",
        end_line=2,
    )

    assert result.success is True
    assert result.result == "one\ntwo\n"


def test_orchestrator_read_file_rejects_invalid_line_type(tmp_path):
    orchestrator = Orchestrator()
    orchestrator.read_file_tool.base_directory = tmp_path

    result = orchestrator.invoke_tool(
        "read_file",
        path="example.txt",
        start_line="2",
    )

    assert result.success is False


def test_orchestrator_normalized_tool_result(tmp_path):
    orchestrator = Orchestrator()
    orchestrator.read_file_tool.base_directory = tmp_path

    (tmp_path / "example.txt").write_text(
        "hello\n",
        encoding="utf-8",
    )

    result = orchestrator.invoke_tool_normalized(
        "read_file",
        path="example.txt",
    )

    assert result == {
        "tool_name": "read_file",
        "success": True,
        "result": "hello\n",
        "error": None,
    }


def test_orchestrator_normalized_failed_tool_result(tmp_path):
    orchestrator = Orchestrator()
    orchestrator.read_file_tool.base_directory = tmp_path

    result = orchestrator.invoke_tool_normalized(
        "read_file",
        path="missing.txt",
    )

    assert result == {
        "tool_name": "read_file",
        "success": False,
        "result": None,
        "error": "File does not exist: missing.txt",
    }


def test_orchestrator_records_successful_tool_trace(tmp_path):
    orchestrator = Orchestrator()
    orchestrator.read_file_tool.base_directory = tmp_path

    (tmp_path / "example.txt").write_text(
        "hello\n",
        encoding="utf-8",
    )

    result = orchestrator.invoke_tool(
        "read_file",
        path="example.txt",
    )

    assert result.success is True

    traces = orchestrator.tool_tracer.traces()

    assert len(traces) == 1
    assert traces[0].tool_name == "read_file"
    assert traces[0].success is True
    assert traces[0].duration_ms >= 0


def test_orchestrator_records_failed_read_trace(tmp_path):
    orchestrator = Orchestrator()
    orchestrator.read_file_tool.base_directory = tmp_path

    result = orchestrator.invoke_tool(
        "read_file",
        path="missing.txt",
    )

    assert result.success is False

    traces = orchestrator.tool_tracer.traces()

    assert len(traces) == 1
    assert traces[0].tool_name == "read_file"
    assert traces[0].success is False
    assert traces[0].error == "File does not exist: missing.txt"


def test_orchestrator_get_tool_traces(tmp_path):
    orchestrator = Orchestrator()
    orchestrator.read_file_tool.base_directory = tmp_path

    (tmp_path / "example.txt").write_text(
        "hello\n",
        encoding="utf-8",
    )

    orchestrator.invoke_tool(
        "read_file",
        path="example.txt",
    )

    traces = orchestrator.get_tool_traces()

    assert isinstance(traces, tuple)
    assert len(traces) == 1
    assert traces[0].tool_name == "read_file"


def test_orchestrator_clear_tool_traces(tmp_path):
    orchestrator = Orchestrator()
    orchestrator.read_file_tool.base_directory = tmp_path

    (tmp_path / "example.txt").write_text(
        "hello\n",
        encoding="utf-8",
    )

    orchestrator.invoke_tool(
        "read_file",
        path="example.txt",
    )

    assert len(orchestrator.get_tool_traces()) == 1

    orchestrator.clear_tool_traces()

    assert orchestrator.get_tool_traces() == ()


def test_orchestrator_allows_read_tools(tmp_path):
    orchestrator = Orchestrator()
    orchestrator.read_file_tool.base_directory = tmp_path

    (tmp_path / "example.txt").write_text(
        "hello\n",
        encoding="utf-8",
    )

    result = orchestrator.invoke_tool(
        "read_file",
        path="example.txt",
    )

    assert result.success is True


def test_orchestrator_allows_write_tools(tmp_path):
    orchestrator = Orchestrator()
    orchestrator.write_file_tool.base_directory = tmp_path

    result = orchestrator.invoke_tool(
        "write_file",
        path="example.txt",
        content="hello\n",
    )

    assert result.success is True
    assert (tmp_path / "example.txt").read_text(
        encoding="utf-8"
    ) == "hello\n"


def test_orchestrator_uses_permissive_tool_mode():
    from tools.policy_guard import ToolExecutionMode

    orchestrator = Orchestrator()

    assert (
        orchestrator.tool_policy_guard.mode
        == ToolExecutionMode.PERMISSIVE
    )


def test_orchestrator_can_use_restricted_tool_mode():
    from tools.policy_guard import ToolExecutionMode

    orchestrator = Orchestrator(
        tool_execution_mode=ToolExecutionMode.RESTRICTED,
    )

    assert (
        orchestrator.tool_policy_guard.mode
        == ToolExecutionMode.RESTRICTED
    )

    assert orchestrator.tool_policy_guard.is_allowed(
        "read_file"
    )

    assert not orchestrator.tool_policy_guard.is_allowed(
        "delete_file"
    )

    assert not orchestrator.tool_policy_guard.is_allowed(
        "execute_code"
    )


def test_orchestrator_default_tool_mode_remains_permissive():
    from tools.policy_guard import ToolExecutionMode

    orchestrator = Orchestrator()

    assert (
        orchestrator.tool_policy_guard.mode
        == ToolExecutionMode.PERMISSIVE
    )

    assert orchestrator.tool_policy_guard.is_allowed(
        "delete_file"
    )

    assert orchestrator.tool_policy_guard.is_allowed(
        "execute_code"
    )


def test_restricted_orchestrator_blocks_execute_code():
    from tools.policy_guard import ToolExecutionMode

    orchestrator = Orchestrator(
        tool_execution_mode=ToolExecutionMode.RESTRICTED,
    )

    try:
        orchestrator.invoke_tool(
            "execute_code",
            "print('should not run')",
            "python",
        )
    except PermissionError as exc:
        assert str(exc) == (
            "Tool 'execute_code' is blocked by "
            "the tool policy (execute)."
        )
    else:
        raise AssertionError(
            "Restricted mode allowed execute_code."
        )


def test_restricted_orchestrator_blocks_delete_file(tmp_path):
    from tools.policy_guard import ToolExecutionMode

    orchestrator = Orchestrator(
        tool_execution_mode=ToolExecutionMode.RESTRICTED,
    )

    orchestrator.workspace = Workspace(tmp_path)

    with open(tmp_path / "sample.txt", "w") as file:
        file.write("sample")

    orchestrator.delete_file_tool.workspace = orchestrator.workspace

    try:
        orchestrator.invoke_tool(
            "delete_file",
            path="sample.txt",
        )
    except PermissionError as exc:
        assert str(exc) == (
            "Tool 'delete_file' is blocked by "
            "the tool policy (destructive)."
        )
    else:
        raise AssertionError(
            "Restricted mode allowed delete_file."
        )

    assert (tmp_path / "sample.txt").exists()


def test_restricted_orchestrator_allows_read_file(tmp_path):
    from tools.policy_guard import ToolExecutionMode

    orchestrator = Orchestrator(
        tool_execution_mode=ToolExecutionMode.RESTRICTED,
    )

    orchestrator.workspace = Workspace(tmp_path)

    (tmp_path / "sample.txt").write_text(
        "hello\nworld\n",
        encoding="utf-8",
    )

    orchestrator.read_file_tool.workspace = orchestrator.workspace

    result = orchestrator.invoke_tool(
        "read_file",
        path="sample.txt",
    )

    assert result.success is True
    assert result.result == "hello\nworld\n"
