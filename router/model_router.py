from models.registry import ModelRegistry, ModelProfile


class ModelRouter:
    """
    Chooses a model based on task difficulty.

    The actual model switching will become useful
    once we add additional local models.
    """

    def __init__(self):
        self.registry = ModelRegistry()

    def choose(self, difficulty: str) -> ModelProfile:
        return self.registry.choose(difficulty)
