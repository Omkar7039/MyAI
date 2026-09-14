class ContextManager:
    """
    Manages recent conversation history for MyAI.

    This is short-term memory only.
    Long-term/project memory will be added later.
    """

    def __init__(
        self,
        max_messages: int = 12,
        max_chars: int = 12000,
    ):
        self.max_messages = max_messages
        self.max_chars = max_chars
        self.messages: list[dict[str, str]] = []

    def add(self, role: str, content: str) -> None:
        self.messages.append(
            {
                "role": role,
                "content": content,
            }
        )

        self._trim()

    def get(self) -> list[dict[str, str]]:
        return list(self.messages)

    def clear(self) -> None:
        self.messages.clear()

    def _trim(self) -> None:
        if len(self.messages) > self.max_messages:
            self.messages = self.messages[-self.max_messages:]

        while (
            self._character_count() > self.max_chars
            and len(self.messages) > 2
        ):
            self.messages.pop(0)

    def _character_count(self) -> int:
        return sum(
            len(message["content"])
            for message in self.messages
        )
