from core.runtime_services import RuntimeServices
from core.runtime_state import RuntimeStateStore
from experience.learning_state import LearningAppliedChange


def make_services(tmp_path):
    store = RuntimeStateStore(tmp_path / "runtime.db")
    return RuntimeServices.create(
        store,
        max_rollback_entries=1,
    )


def test_status_command_is_handled(tmp_path, capsys):
    from main import handle_runtime_command

    services = make_services(tmp_path)
    services.store.set("runtime.status", "ready")

    handled = handle_runtime_command(
        "/status",
        services,
    )

    assert handled is True

    output = capsys.readouterr().out

    assert "Runtime status: ready" in output
    assert "Healthy: True" in output
    assert "Active strategies: none" in output


def test_retention_command_is_preview_only(tmp_path, capsys):
    from main import handle_runtime_command

    services = make_services(tmp_path)

    first = LearningAppliedChange(
        strategy="property",
        previous_score=None,
        applied_score=80.0,
        observations=5,
        confidence=70.0,
    )
    second = LearningAppliedChange(
        strategy="property",
        previous_score=80.0,
        applied_score=90.0,
        observations=5,
        confidence=75.0,
    )

    services.learning_state.save(
        (second,),
        {
            "property": [
                first,
                second,
            ],
        },
    )

    handled = handle_runtime_command(
        "/retention",
        services,
    )

    assert handled is True

    output = capsys.readouterr().out

    assert "Learning retention preview:" in output
    assert "Entries to prune: 1" in output

    _, history = services.learning_state.load_with_history()

    assert len(history["property"]) == 2


def test_retention_apply_command_mutates_state(tmp_path, capsys):
    from main import handle_runtime_command

    services = make_services(tmp_path)

    first = LearningAppliedChange(
        strategy="property",
        previous_score=None,
        applied_score=80.0,
        observations=5,
        confidence=70.0,
    )
    second = LearningAppliedChange(
        strategy="property",
        previous_score=80.0,
        applied_score=90.0,
        observations=5,
        confidence=75.0,
    )

    services.learning_state.save(
        (second,),
        {
            "property": [
                first,
                second,
            ],
        },
    )

    handled = handle_runtime_command(
        "/retention apply",
        services,
    )

    assert handled is True

    output = capsys.readouterr().out

    assert "Learning retention applied:" in output
    assert "Entries pruned: 1" in output

    _, history = services.learning_state.load_with_history()

    assert len(history["property"]) == 1
    assert history["property"][0].applied_score == 90.0


def test_unknown_runtime_command_is_not_handled(tmp_path):
    from main import handle_runtime_command

    services = make_services(tmp_path)

    assert (
        handle_runtime_command(
            "/unknown-runtime-command",
            services,
        )
        is False
    )
