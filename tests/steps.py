"""Ejecuta el `run:` de un step de un workflow dentro de un contenedor Ubuntu (≈ runner de GitHub).

Sirve para probar la lógica de shell de las plantillas con stubs de `gh`/`kubectl`/... sin depender de GitHub.
Los tests que lo usan se omiten si Docker no está disponible.
"""
import os
import shutil
import subprocess
import textwrap
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
WORKFLOWS = ROOT / ".github" / "workflows"
IMAGE = "gha-step-runner:test"


def docker_ready():
    if not shutil.which("docker"):
        return False
    return subprocess.run(["docker", "info"], capture_output=True).returncode == 0


def ensure_image():
    if subprocess.run(["docker", "image", "inspect", IMAGE], capture_output=True).returncode != 0:
        subprocess.run(["docker", "build", "-q", "-t", IMAGE, "-f", str(ROOT / "tests" / "step-runner.Dockerfile"),
                        str(ROOT / "tests")], check=True, capture_output=True)


def step_run(workflow, job, step_name):
    doc = yaml.safe_load((WORKFLOWS / workflow).read_text(encoding="utf-8"))
    for step in doc["jobs"][job]["steps"]:
        if step.get("name") == step_name:
            return step["run"]
    raise KeyError(f"{workflow}:{job}:{step_name}")


def run_step(tmp_path, script, files=None, env=None, stubs=None, cwd=".", prelude="", post=""):
    """Devuelve (CompletedProcess, dict de archivos GITHUB_ENV/OUTPUT/SUMMARY). tmp_path se monta en /w."""
    work = tmp_path / "w"
    work.mkdir(parents=True)
    for rel, content in (files or {}).items():
        p = work / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
    bin_dir = work / ".stubs"
    bin_dir.mkdir()
    for name, body in (stubs or {}).items():
        stub = bin_dir / name
        stub.write_text("#!/usr/bin/env bash\n" + textwrap.dedent(body), encoding="utf-8")
        stub.chmod(0o755)
    for gh_file in ("GITHUB_ENV", "GITHUB_OUTPUT", "GITHUB_STEP_SUMMARY", "GITHUB_PATH"):
        (work / f".{gh_file}").write_text("")
    (work / ".step.sh").write_text(prelude + "\n" + script + "\n" + post, encoding="utf-8")
    full_env = {
        "GITHUB_WORKSPACE": "/w", "RUNNER_TEMP": "/tmp", "GITHUB_ENV": "/w/.GITHUB_ENV", "GITHUB_OUTPUT": "/w/.GITHUB_OUTPUT",
        "GITHUB_STEP_SUMMARY": "/w/.GITHUB_STEP_SUMMARY", "GITHUB_PATH": "/w/.GITHUB_PATH", "GITHUB_REPOSITORY": "o/repo",
        "GITHUB_REF_NAME": "main", "GITHUB_RUN_ID": "99", "GITHUB_RUN_NUMBER": "7", "GITHUB_ACTOR": "tester",
        "GITHUB_SHA": "0123456789abcdef", "GITHUB_SERVER_URL": "https://github.com", **(env or {}),
        "PATH": "/w/.stubs:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
    }
    args = ["docker", "run", "--rm", "-v", f"{work}:/w", "-w", f"/w/{cwd}"]
    for k, v in full_env.items():
        args += ["-e", f"{k}={v}"]
    args += [IMAGE, "bash", "--noprofile", "--norc", "-eo", "pipefail", "/w/.step.sh"]
    proc = subprocess.run(args, capture_output=True, text=True, timeout=180)
    gh = {k: (work / f".{k}").read_text() for k in ("GITHUB_ENV", "GITHUB_OUTPUT", "GITHUB_STEP_SUMMARY")}
    return proc, gh, work


requires_docker = pytest.mark.skipif(not docker_ready(), reason="Docker no disponible")


@pytest.fixture(scope="session", autouse=False)
def runner_image():
    if docker_ready():
        ensure_image()
