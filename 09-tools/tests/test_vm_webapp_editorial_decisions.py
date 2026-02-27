from vm_webapp.editorial_decisions import derive_objective_key, resolve_baseline


def test_derive_objective_key_is_stable() -> None:
    a = derive_objective_key("Campanha Lancamento 2026 - Redes Sociais")
    b = derive_objective_key("campanha lancamento 2026 redes sociais")
    assert a == b


def test_resolve_baseline_priority_objective_global_previous() -> None:
    runs = [
        {"run_id": "run-3", "objective_key": "obj-a"},
        {"run_id": "run-2", "objective_key": "obj-a"},
        {"run_id": "run-1", "objective_key": "obj-b"},
    ]
    decisions = {
        "global": {"run_id": "run-1"},
        "objective": {"obj-a": {"run_id": "run-2"}},
    }
    baseline = resolve_baseline(active_run_id="run-3", active_objective_key="obj-a", runs=runs, decisions=decisions)
    assert baseline["baseline_run_id"] == "run-2"
    assert baseline["source"] == "objective_golden"
