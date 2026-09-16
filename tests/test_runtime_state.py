from core.runtime_state import (
    RuntimeState,
    RuntimeStateStore,
)


def make_store(tmp_path):
    return RuntimeStateStore(
        tmp_path / "runtime.db"
    )


def test_store_initializes_with_schema_version(tmp_path):
    store = make_store(tmp_path)

    assert store.schema_version() == 1


def test_set_and_get_round_trip(tmp_path):
    store = make_store(tmp_path)

    state = store.set(
        "runtime.status",
        "ready",
    )

    assert isinstance(state, RuntimeState)
    assert state.key == "runtime.status"
    assert state.value == "ready"

    loaded = store.get("runtime.status")

    assert loaded is not None
    assert loaded.key == "runtime.status"
    assert loaded.value == "ready"
    assert loaded.updated_at


def test_value_returns_default_for_missing_key(tmp_path):
    store = make_store(tmp_path)

    assert store.value(
        "missing",
        "fallback",
    ) == "fallback"


def test_value_returns_stored_value(tmp_path):
    store = make_store(tmp_path)

    store.set(
        "runtime.status",
        "ready",
    )

    assert store.value(
        "runtime.status",
    ) == "ready"


def test_set_updates_existing_value(tmp_path):
    store = make_store(tmp_path)

    first = store.set(
        "runtime.status",
        "starting",
    )
    second = store.set(
        "runtime.status",
        "ready",
    )

    assert first.key == second.key
    assert store.value("runtime.status") == "ready"
    assert len(store.all()) == 1


def test_keys_are_normalized(tmp_path):
    store = make_store(tmp_path)

    store.set(
        "  runtime.status  ",
        "ready",
    )

    assert store.value(
        "runtime.status",
    ) == "ready"


def test_all_is_sorted_by_key(tmp_path):
    store = make_store(tmp_path)

    store.set("z", "3")
    store.set("a", "1")
    store.set("m", "2")

    assert tuple(
        item.key
        for item in store.all()
    ) == ("a", "m", "z")


def test_delete_existing_key(tmp_path):
    store = make_store(tmp_path)

    store.set(
        "runtime.status",
        "ready",
    )

    assert store.delete("runtime.status") is True
    assert store.get("runtime.status") is None
    assert store.delete("runtime.status") is False


def test_clear_removes_runtime_state(tmp_path):
    store = make_store(tmp_path)

    store.set("a", "1")
    store.set("b", "2")

    store.clear()

    assert store.all() == ()


def test_empty_key_is_rejected(tmp_path):
    store = make_store(tmp_path)

    try:
        store.set(" ", "value")
    except ValueError as exc:
        assert str(exc) == "key must not be empty"
    else:
        raise AssertionError("expected ValueError")


def test_empty_get_key_is_rejected(tmp_path):
    store = make_store(tmp_path)

    try:
        store.get(" ")
    except ValueError as exc:
        assert str(exc) == "key must not be empty"
    else:
        raise AssertionError("expected ValueError")


def test_empty_delete_key_is_rejected(tmp_path):
    store = make_store(tmp_path)

    try:
        store.delete(" ")
    except ValueError as exc:
        assert str(exc) == "key must not be empty"
    else:
        raise AssertionError("expected ValueError")


def test_state_survives_new_store_instance(tmp_path):
    db = tmp_path / "runtime.db"

    first = RuntimeStateStore(db)
    first.set(
        "runtime.instance",
        "myai",
    )

    second = RuntimeStateStore(db)

    assert second.value(
        "runtime.instance",
    ) == "myai"
