from tools.runners.node_runner import NodeRunner


def main():
    runner = NodeRunner()

    result = runner.run(
        """
console.log("Hello from MyAI");
console.log(2 + 3);
"""
    )

    print("LANGUAGE:", result.language)
    print("SUCCESS:", result.success)
    print("EXIT CODE:", result.exit_code)
    print("STDOUT:")
    print(result.stdout)
    print("STDERR:")
    print(result.stderr)
    print("TIMED OUT:", result.timed_out)
    print("EXECUTION TIME:", result.execution_time)


if __name__ == "__main__":
    main()
