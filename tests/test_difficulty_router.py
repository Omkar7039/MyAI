from router.difficulty_router import DifficultyRouter


def main():
    router = DifficultyRouter()

    tests = [
        (
            "What is a Python list?",
            None,
            "unknown",
        ),
        (
            "Write a Python function to sort a list.",
            None,
            "python",
        ),
        (
            "Debug this concurrency race condition in production.",
            "def worker():\n    pass\n",
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
        result = router.analyze(
            text=text,
            code=code,
            language=language,
        )

        print(
            f"{result.level:7} "
            f"{result.score:3} "
            f"{text}"
        )


if __name__ == "__main__":
    main()
