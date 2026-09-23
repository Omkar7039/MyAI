from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class ToolArguments:
    """
    Arguments extracted from a natural-language tool request.
    """

    tool_name: str
    arguments: dict[str, object]


class ToolArgumentExtractor:
    """
    Extract basic tool arguments from natural-language requests.

    This component intentionally handles only deterministic patterns.
    More advanced model-assisted extraction can be added later.
    """

    def extract(
        self,
        tool_name: str,
        request: str,
    ) -> ToolArguments:
        normalized_tool = tool_name.strip().lower()
        text = request.strip()

        if not normalized_tool:
            raise ValueError("Tool name cannot be empty.")

        if not text:
            raise ValueError("Request cannot be empty.")

        extractor = getattr(
            self,
            f"_extract_{normalized_tool}",
            None,
        )

        if extractor is None:
            return ToolArguments(
                tool_name=normalized_tool,
                arguments={},
            )

        return ToolArguments(
            tool_name=normalized_tool,
            arguments=extractor(text),
        )

    def _extract_read_file(
        self,
        text: str,
    ) -> dict[str, object]:
        path = self._extract_path(text)

        if path is None:
            raise ValueError(
                "Could not determine the file path."
            )

        arguments: dict[str, object] = {
            "path": path,
        }

        line_match = re.search(
            r"(?:lines?|line)\s+(\d+)\s*(?:-|to)\s*(\d+)",
            text,
            re.IGNORECASE,
        )

        if line_match:
            arguments["start_line"] = int(
                line_match.group(1)
            )
            arguments["end_line"] = int(
                line_match.group(2)
            )

        return arguments

    def _extract_list_files(
        self,
        text: str,
    ) -> dict[str, object]:
        path = self._extract_list_path(text)

        if path is None:
            return {}

        return {"path": path}

    def _extract_directory_tree(
        self,
        text: str,
    ) -> dict[str, object]:
        path = self._extract_path(text)

        arguments: dict[str, object] = {}

        if path is not None:
            arguments["path"] = path

        depth_match = re.search(
            r"(?:depth|max(?:imum)?\s+depth)\s*(?:=|:)?\s*(\d+)",
            text,
            re.IGNORECASE,
        )

        if depth_match:
            arguments["max_depth"] = int(
                depth_match.group(1)
            )

        return arguments

    def _extract_search_files(
        self,
        text: str,
    ) -> dict[str, object]:
        match = re.search(
            r"(?:search\s+for|find\s+in\s+files|find\s+this\s+in\s+the\s+files?)\s+[\"']?(.+?)[\"']?(?:\s+in\s+(.+))?$",
            text,
            re.IGNORECASE,
        )

        if match:
            query = match.group(1).strip()
            path = (
                match.group(2).strip()
                if match.group(2)
                else "."
            )

            return {
                "query": query,
                "path": path,
            }

        raise ValueError(
            "Could not determine the search query."
        )

    def _extract_file_exists(
        self,
        text: str,
    ) -> dict[str, object]:
        path = self._extract_path(text)

        if path is None:
            raise ValueError(
                "Could not determine the file path."
            )

        return {"path": path}

    def _extract_get_file_info(
        self,
        text: str,
    ) -> dict[str, object]:
        path = self._extract_path(text)

        if path is None:
            raise ValueError(
                "Could not determine the file path."
            )

        return {"path": path}

    def _extract_file_hash(
        self,
        text: str,
    ) -> dict[str, object]:
        path = self._extract_path(text)

        if path is None:
            raise ValueError(
                "Could not determine the file path."
            )

        return {"path": path}

    def _extract_delete_file(
        self,
        text: str,
    ) -> dict[str, object]:
        path = self._extract_path(text)

        if path is None:
            raise ValueError(
                "Could not determine the file path."
            )

        return {"path": path}

    def _extract_create_directory(
        self,
        text: str,
    ) -> dict[str, object]:
        path = self._extract_path(text)

        if path is None:
            raise ValueError(
                "Could not determine the directory path."
            )

        return {"path": path}

    def _extract_write_file(
        self,
        text: str,
    ) -> dict[str, object]:
        content_match = re.search(
            r"(?:with\s+content|containing|contents?)\s*[:=]?\s*(.+)$",
            text,
            re.IGNORECASE | re.DOTALL,
        )

        if not content_match:
            raise ValueError(
                "Could not determine the file content."
            )

        content = content_match.group(1).strip()

        path_text = text[:content_match.start()]
        path = self._extract_path(
            path_text
        )

        if path is None:
            raise ValueError(
                "Could not determine the file path."
            )

        return {
            "path": path,
            "content": content,
        }

    @staticmethod
    def _extract_path(
        text: str,
    ) -> str | None:
        quoted = re.search(
            r"[\"']([^\"']+)[\"']",
            text,
        )

        if quoted:
            return quoted.group(1).strip()

        path_match = re.search(
            r"(?<!\w)([\w./~_-]+\.[A-Za-z0-9_-]+)(?!\w)",
            text,
        )

        if path_match:
            return path_match.group(1).strip()

        directory_match = re.search(
            r"(?:directory|folder)\s+([^\s,]+)",
            text,
            re.IGNORECASE,
        )

        if directory_match:
            return directory_match.group(1).strip()

        return None

    @staticmethod
    def _extract_list_path(
        text: str,
    ) -> str | None:
        directory_match = re.search(
            r"(?:in|inside|under)\s+([\w./~_-]+)",
            text,
            re.IGNORECASE,
        )

        if directory_match:
            return directory_match.group(1).strip()

        return ToolArgumentExtractor._extract_path(text)
