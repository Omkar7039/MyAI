from core.tool_planner import ToolDecision, ToolPlanner


def test_tool_planner_returns_none_for_empty_request():
    planner = ToolPlanner()

    assert planner.plan("") is None
    assert planner.plan("   ") is None


def test_tool_planner_selects_read_file():
    decision = ToolPlanner().plan(
        "Read the file config.py"
    )

    assert isinstance(decision, ToolDecision)
    assert decision.tool_name == "read_file"
    assert decision.confidence > 0


def test_tool_planner_selects_search_files():
    decision = ToolPlanner().plan(
        "Search for TODO in the project files"
    )

    assert decision.tool_name == "search_files"


def test_tool_planner_selects_execute_code():
    decision = ToolPlanner().plan(
        "Run this code"
    )

    assert decision.tool_name == "execute_code"


def test_tool_planner_selects_edit_file():
    decision = ToolPlanner().plan(
        "Modify the file and replace the broken function"
    )

    assert decision.tool_name == "edit_file"


def test_tool_planner_selects_write_file():
    decision = ToolPlanner().plan(
        "Create a file called example.py"
    )

    assert decision.tool_name == "write_file"


def test_tool_planner_selects_delete_file():
    decision = ToolPlanner().plan(
        "Delete the file old.py"
    )

    assert decision.tool_name == "delete_file"


def test_tool_planner_selects_move_file():
    decision = ToolPlanner().plan(
        "Move the file old.py"
    )

    assert decision.tool_name == "move_file"


def test_tool_planner_selects_copy_file():
    decision = ToolPlanner().plan(
        "Copy the file config.py"
    )

    assert decision.tool_name == "copy_file"


def test_tool_planner_selects_directory_tree():
    decision = ToolPlanner().plan(
        "Show the project tree"
    )

    assert decision.tool_name == "directory_tree"


def test_tool_planner_selects_list_files():
    decision = ToolPlanner().plan(
        "List the files here"
    )

    assert decision.tool_name == "list_files"


def test_tool_planner_selects_file_exists():
    decision = ToolPlanner().plan(
        "Check if the file config.py exists"
    )

    assert decision.tool_name == "file_exists"


def test_tool_planner_selects_file_hash():
    decision = ToolPlanner().plan(
        "Calculate the SHA-256 hash of the file"
    )

    assert decision.tool_name == "file_hash"


def test_tool_planner_selects_file_info():
    decision = ToolPlanner().plan(
        "Show information about the file"
    )

    assert decision.tool_name == "get_file_info"


def test_tool_planner_is_case_insensitive():
    decision = ToolPlanner().plan(
        "READ THE FILE config.py"
    )

    assert decision.tool_name == "read_file"


def test_tool_planner_returns_none_for_non_tool_request():
    decision = ToolPlanner().plan(
        "Explain recursion in Python"
    )

    assert decision is None
