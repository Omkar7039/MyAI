from core.orchestrator import Orchestrator


def main():
    # This test intentionally does not create the model.
    # We test the routing components independently.

    from router.intent_router import IntentRouter
    from router.difficulty_router import DifficultyRouter
    from router.model_router import ModelRouter

    intent_router = IntentRouter()
    difficulty_router = DifficultyRouter()
    model_router = ModelRouter()

    tests = [
        (
            "What is dependency injection?",
            None,
            "unknown",
        ),
        (
            "Write a Python function to reverse a string.",
            None,
            "python",
        ),
        (
            "Debug this concurrency race condition in production.",
            "def worker():\n    pass",
            "python",
        ),
        (
            "Analyze this distributed microservice architecture and "
            "find the memory leak and deadlock.",
            "\n".join(["x = 1"] * 300),
            "python",
        ),
    ]

    for text, code, language in tests:

        intent = intent_router.route(text)

        difficulty = difficulty_router.analyze(
            text=text,
            code=code,
            language=language,
        )

        model = model_router.choose(
            difficulty.level
        )

        print(
            f"Intent={intent.name:<15} "
            f"Difficulty={difficulty.level:<7} "
            f"Score={difficulty.score:<3} "
            f"Model={model.name}"
        )


if __name__ == "__main__":
    main()
