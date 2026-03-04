from pathlib import Path
import os
import subprocess


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "test_battery_prerelease.sh"


def run_script(
    *args: str, env_overrides: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = "09-tools"
    if env_overrides:
        env.update(env_overrides)
    return subprocess.run(
        ["bash", str(SCRIPT), *args],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        env=env,
    )


def test_list_stages_exposes_expected_pipeline() -> None:
    completed = run_script("--list")
    assert completed.returncode == 0
    assert "preflight" in completed.stdout
    assert "gate-critico" in completed.stdout
    assert "backend-full" in completed.stdout
    assert "frontend-full" in completed.stdout
    assert "e2e-startup" in completed.stdout
    assert "evidence" in completed.stdout


def test_dry_run_outputs_commands_without_execution() -> None:
    completed = run_script("--dry-run", "--stage", "gate-critico")
    assert completed.returncode == 0
    assert "DRY-RUN" in completed.stdout
    assert "test_vm_webapp_health_probes.py" in completed.stdout


def test_invalid_stage_fails_fast() -> None:
    completed = run_script("--stage", "nao-existe")
    assert completed.returncode != 0
    assert "Unknown stage" in (completed.stderr + completed.stdout)


def test_pipeline_stops_on_gate_failure() -> None:
    completed = run_script("--dry-run", "--from", "preflight", "--to", "e2e-startup")
    assert completed.returncode == 0
    assert "preflight" in completed.stdout
    assert "gate-critico" in completed.stdout
    assert "e2e-startup" in completed.stdout


def test_dry_run_writes_summary_file(tmp_path: Path) -> None:
    completed = run_script("--dry-run", "--artifacts-dir", str(tmp_path))
    assert completed.returncode == 0
    assert (tmp_path / "summary.txt").exists()


def test_real_failure_propagates_exit_code(tmp_path: Path) -> None:
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir(parents=True, exist_ok=True)
    fake_python = fake_bin / "python3"
    fake_python.write_text("#!/usr/bin/env bash\nexit 42\n")
    fake_python.chmod(0o755)

    path = os.environ.get("PATH", "")
    completed = run_script(
        "--stage",
        "preflight",
        env_overrides={"PATH": f"{fake_bin}:{path}"},
    )

    output = completed.stdout + completed.stderr
    assert completed.returncode != 0
    assert "Comando falhou com exit code 42: python3 --version" in output
    assert "Estágio preflight falhou." in output
