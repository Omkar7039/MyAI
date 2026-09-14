from core.context import ContextManager


def main():
    context = ContextManager(
        max_messages=4,
        max_chars=200,
    )

    context.add("user", "Hello")
    context.add("assistant", "Hello Omkar")
    context.add("user", "Write Python code")
    context.add("assistant", "Sure")

    print("MESSAGES:")
    print(context.get())

    context.clear()

    print("AFTER CLEAR:")
    print(context.get())


if __name__ == "__main__":
    main()
