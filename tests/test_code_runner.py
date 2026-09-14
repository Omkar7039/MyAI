from tools.code_runner import PythonCodeRunner


def main():
    runner = PythonCodeRunner()

    result = runner.run(
        """
def divide(a, b):
    return a / b

print(divide(10, 0))
"""
    )

    print("EXIT CODE:", result.exit_code)
    print("STDOUT:")
    print(result.stdout)

    print("STDERR:")
    print(result.stderr)

    print("TIMED OUT:", result.timed_out)


if __name__ == "__main__":
    main()
