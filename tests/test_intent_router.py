from router.intent_router import IntentRouter


def main():
    router = IntentRouter()

    tests = [
        "What is dependency injection?",
        "Write a Python function to reverse a string.",
        "Debug this Python code.",
        "Fix the error in my JavaScript program.",
        "Make this code shorter and cleaner.",
        "Review this code for security problems.",
        "Analyze this code and explain how it works.",
        "Scan my repository and find the problem.",
        "def add(a, b): return a + b",
    ]

    for text in tests:
        intent = router.route(text)

        print(
            f"{intent.name:15} "
            f"{intent.confidence:.2f}  "
            f"{text}"
        )


if __name__ == "__main__":
    main()
