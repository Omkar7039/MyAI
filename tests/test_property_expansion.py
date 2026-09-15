from verification.property_expansion import PropertyExpansionEngine


def test_add_expands_to_multiple_properties():
    result = PropertyExpansionEngine().expand("add", "add")

    assert len(result) == 4
    assert [case.name for case in result] == [
        "add_commutative",
        "add_zero_left",
        "add_zero_right",
        "add_negative_pair",
    ]


def test_add_properties_target_requested_function():
    result = PropertyExpansionEngine().expand("sum_values", "add")

    expressions = [case.expression for case in result]

    assert "sum_values(2, 7) == sum_values(7, 2)" in expressions
    assert "sum_values(0, 7) == 7" in expressions


def test_sort_expands_to_boundary_and_duplicate_cases():
    result = PropertyExpansionEngine().expand("sort_values", "sort")

    assert len(result) == 4
    assert any(
        "sort_values([]) == []" == case.expression
        for case in result
    )
    assert any(
        "sort_values([2, 1, 2]) == [1, 2, 2]" == case.expression
        for case in result
    )


def test_reverse_expands_to_involution_property():
    result = PropertyExpansionEngine().expand("reverse_values", "reverse")

    assert len(result) == 4
    assert any(
        "reverse_values(reverse_values([1, 2, 3])) == [1, 2, 3]"
        == case.expression
        for case in result
    )


def test_unknown_operation_is_safe():
    result = PropertyExpansionEngine().expand(
        "process",
        "unknown",
    )

    assert result == ()


def test_operation_matching_is_case_insensitive():
    result = PropertyExpansionEngine().expand("add", "ADD")

    assert len(result) == 4


def test_property_descriptions_are_present():
    result = PropertyExpansionEngine().expand("add", "add")

    assert all(case.description for case in result)


def test_property_names_are_unique():
    result = PropertyExpansionEngine().expand("reverse", "reverse")

    names = [case.name for case in result]

    assert len(names) == len(set(names))


def test_generation_is_deterministic():
    engine = PropertyExpansionEngine()

    first = engine.expand("sort_values", "sort")
    second = engine.expand("sort_values", "sort")

    assert first == second
