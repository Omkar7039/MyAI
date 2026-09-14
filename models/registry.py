from dataclasses import dataclass


@dataclass
class ModelProfile:
    name: str
    backend: str
    capability: str
    max_tokens: int


class ModelRegistry:
    """
    Central model registry.

    For now we have one verified local model.
    More models can be added later without changing the agents.
    """

    def __init__(self):
        self.models = {
            "default": ModelProfile(
                name="mlx-community/Qwen3-8B-4bit",
                backend="mlx",
                capability="general-coding",
                max_tokens=768,
            ),
        }

    def get(self, name: str = "default") -> ModelProfile:
        return self.models[name]

    def choose(self, difficulty: str) -> ModelProfile:
        """
        Current M4 16 GB policy.

        We only have one verified model right now,
        so all difficulty levels use it.
        The architecture is ready for additional models.
        """

        if difficulty == "easy":
            return self.models["default"]

        if difficulty == "medium":
            return self.models["default"]

        if difficulty == "hard":
            return self.models["default"]

        return self.models["default"]
