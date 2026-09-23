from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ToolDecision:
    """
    A deterministic recommendation for the next tool to use.
    """

    tool_name: str
    reason: str
    confidence: float


class ToolPlanner:
    """
    Select the most appropriate built-in tool from a user request.

    This first version is intentionally deterministic. It provides a
    predictable foundation for the later agentic planning layer.
    """

    def plan(self, request: str) -> ToolDecision | None:
        text = request.strip().lower()

        if not text:
            return None

        if self._contains_any(
            text,
            (
                "delete file",
                "remove file",
                "delete the file",
                "remove the file",
            ),
        ):
            return ToolDecision(
                tool_name="delete_file",
                reason="The request asks to delete a file.",
                confidence=0.95,
            )

        if self._contains_any(
            text,
            (
                "move file",
                "move the file",
            ),
        ):
            return ToolDecision(
                tool_name="move_file",
                reason="The request asks to move a file.",
                confidence=0.95,
            )

        if self._contains_any(
            text,
            (
                "copy file",
                "copy the file",
            ),
        ):
            return ToolDecision(
                tool_name="copy_file",
                reason="The request asks to copy a file.",
                confidence=0.95,
            )

        if self._contains_any(
            text,
            (
                "create directory",
                "create folder",
                "make a directory",
                "make a folder",
            ),
        ):
            return ToolDecision(
                tool_name="create_directory",
                reason="The request asks to create a directory.",
                confidence=0.95,
            )

        if self._contains_any(
            text,
            (
                "write file",
                "create file",
                "create a file",
                "write to file",
            ),
        ):
            return ToolDecision(
                tool_name="write_file",
                reason="The request asks to create or write a file.",
                confidence=0.90,
            )

        if self._contains_any(
            text,
            (
                "edit file",
                "modify file",
                "modify the file",
                "change file",
                "change the file",
                "update file",
                "update the file",
                "replace in file",
                "fix the file",
            ),
        ):
            return ToolDecision(
                tool_name="edit_file",
                reason="The request asks to modify an existing file.",
                confidence=0.90,
            )

        if self._contains_any(
            text,
            (
                "run code",
                "execute code",
                "run this code",
                "execute this code",
                "run the code",
                "test this code",
                "run tests",
            ),
        ):
            return ToolDecision(
                tool_name="execute_code",
                reason="The request asks to execute or test code.",
                confidence=0.95,
            )

        if self._contains_any(
            text,
            (
                "hash file",
                "file hash",
                "sha256",
                "sha-256",
            ),
        ):
            return ToolDecision(
                tool_name="file_hash",
                reason="The request asks for a file hash.",
                confidence=0.95,
            )

        if self._contains_any(
            text,
            (
                "does the file exist",
                "does the file exists",
                "check if the file exists",
                "check if the file",
                "check whether the file exists",
                "check whether the file",
                "file exists",
            ),
        ):
            return ToolDecision(
                tool_name="file_exists",
                reason="The request asks whether a file exists.",
                confidence=0.95,
            )

        if self._contains_any(
            text,
            (
                "file info",
                "file information",
                "information about the file",
                "details about the file",
                "metadata for the file",
            ),
        ):
            return ToolDecision(
                tool_name="get_file_info",
                reason="The request asks for file metadata.",
                confidence=0.90,
            )

        if self._contains_any(
            text,
            (
                "directory tree",
                "folder tree",
                "project tree",
                "show the tree",
                "show directory structure",
            ),
        ):
            return ToolDecision(
                tool_name="directory_tree",
                reason="The request asks for directory structure.",
                confidence=0.95,
            )

        if self._contains_any(
            text,
            (
                "list files",
                "list the files",
                "show files",
                "what files are here",
                "files in the directory",
            ),
        ):
            return ToolDecision(
                tool_name="list_files",
                reason="The request asks to list files.",
                confidence=0.90,
            )

        if self._contains_any(
            text,
            (
                "search files",
                "search the files",
                "find in files",
                "search for",
                "find this in the project",
                "find this in the files",
            ),
        ):
            return ToolDecision(
                tool_name="search_files",
                reason="The request asks to search file contents.",
                confidence=0.85,
            )

        if self._contains_any(
            text,
            (
                "read file",
                "read the file",
                "show file",
                "show the file",
                "open the file",
                "contents of the file",
                "read this file",
            ),
        ):
            return ToolDecision(
                tool_name="read_file",
                reason="The request asks to read file contents.",
                confidence=0.90,
            )

        return None

    @staticmethod
    def _contains_any(
        text: str,
        phrases: tuple[str, ...],
    ) -> bool:
        return any(
            phrase in text
            for phrase in phrases
        )
