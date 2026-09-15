import pytest

from verification.regression_test_generator import (
    RegressionTestGenerator,
)


SOURCE = """
def add(a, b):
    return a + b
"""


def test_generates_direct_regression_assertion():
    result = RegressionTestGenerator().generate(
        source_code=SOURCE,
        function_name="add",
        arguments=(2, 3),
        expected=5,
        description="preserve addition behavior",
    )

    assert result.function_name == "add"
    assert result.expected == "5"
    assert result.description == "preserve addition behavior"
    assert (
        result.test_code
        == "def test_regression_add():\n"
        "    assert add(2, 3) == 5\n"
    )


def test_generates_string_arguments_safely():
    result = RegressionTestGenerator().generate(
        source_code="""
def greet(name):
    return f"Hello {name}"
""",
        function_name="greet",
        arguments=("Alice",),
        expected="Hello Alice",
    )

    assert result.test_code == (
        "def test_regression_greet():\n"
        "    assert greet('Alice') == 'Hello Alice'\n"
    )


def test_generates_nested_values():
    result = RegressionTestGenerator().generate(
        source_code="""
def identity(value):
    return value
""",
        function_name="identity",
        arguments=([1, 2, 3],),
        expected=[1, 2, 3],
    )

    assert result.test_code == (
        "def test_regression_identity():\n"
        "    assert identity([1, 2, 3]) == [1, 2, 3]\n"
    )


def test_generates_boolean_and_none_values():
    result = RegressionTestGenerator().generate(
        source_code="""
def check(value):
    return value
""",
        function_name="check",
        arguments=(True,),
        expected=None,
    )

    assert result.test_code == (
        "def test_regression_check():\n"
        "    assert check(True) == None\n"
    )


def test_missing_function_is_rejected():
    with pytest.raises(
        ValueError,
        match="function 'missing' was not found",
    ):
        RegressionTestGenerator().generate(
            source_code=SOURCE,
            function_name="missing",
            arguments=(1, 2),
            expected=3,
        )


def test_invalid_source_is_rejected():
    with pytest.raises(
        ValueError,
        match="invalid Python syntax",
    ):
        RegressionTestGenerator().generate(
            source_code="def broken(:\n    pass",
            function_name="broken",
            arguments=(),
            expected=None,
        )


def test_description_has_default():
    result = RegressionTestGenerator().generate(
        source_code=SOURCE,
        function_name="add",
        arguments=(1, 2),
        expected=3,
    )

    assert result.description == "Regression test for add"


def test_generation_is_deterministic():
    generator = RegressionTestGenerator()

    first = generator.generate(
        source_code=SOURCE,
        function_name="add",
        arguments=(-5, 10),
        expected=5,
    )
    second = generator.generate(
        source_code=SOURCE,
        function_name="add",
        arguments=(-5, 10),
        expected=5,
    )

    assert first == second
