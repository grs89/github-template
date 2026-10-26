"""Ejecución real (en un contenedor Ubuntu) de la lógica de shell de los workflows, con stubs de gh/curl/kubectl."""
import json
import textwrap

import pytest

from steps import requires_docker, run_step, runner_image, step_run  # noqa: F401

pytestmark = [requires_docker, pytest.mark.usefixtures("runner_image")]

GIT_PRELUDE = """
git config --global user.name t; git config --global user.email t@t; git config --global --add safe.directory '*'
git config --global init.defaultBranch main
"""


# ───────────────────────── license compliance ─────────────────────────

def _license(tmp_path, report, **env):
    base = {"LICENSE_REPORT_FILE": "license-report.json", "LICENSE_FAIL_ON_BLOCKED": "true",
            "LICENSE_ALLOWED": "MIT,Apache-2.0", "LICENSE_BLOCKED": "GPL-3.0,AGPL-3.0", "SCAN_ERRORS": "0"}
    return run_step(tmp_path, step_run("security-license-compliance.yml", "license_compliance", "Evaluar compliance"),
                    files={"license-report.json": json.dumps(report)}, env={**base, **env})


def test_licencias_permitidas_pasan(tmp_path):
    proc, gh, _ = _license(tmp_path, [{"package": "a", "license": "MIT"}, {"package": "b", "license": "Apache-2.0"}])
    assert proc.returncode == 0, proc.stderr
    assert "| 2 | 2 | 0 | 0 |" in gh["GITHUB_STEP_SUMMARY"]


def test_licencia_bloqueada_falla_el_job(tmp_path):
    proc, gh, _ = _license(tmp_path, [{"package": "viral", "license": "GPL-3.0-only"}, {"package": "ok", "license": "MIT"}])
    assert proc.returncode == 1
    assert "viral" in proc.stdout and "::error::" in proc.stdout
    assert "| 2 | 1 | 1 | 0 |" in gh["GITHUB_STEP_SUMMARY"]


def test_licencia_bloqueada_en_modo_permisivo_solo_avisa(tmp_path):
    proc, _, _ = _license(tmp_path, [{"package": "viral", "license": "AGPL-3.0"}], LICENSE_FAIL_ON_BLOCKED="false")
    assert proc.returncode == 0 and "::warning::" in proc.stdout


def test_auditoria_incompleta_no_se_reporta_como_limpia(tmp_path):
    proc, _, work = _license(tmp_path, [{"package": "a", "license": "MIT"}], SCAN_ERRORS="1", FAILED_SERVICES=" api")
    assert proc.returncode == 0 and "incompleta" in proc.stdout
    report = json.loads((work / "license-report.json").read_text())
    assert report[-1]["scan_incomplete"] is True and report[-1]["services"] == " api"


def test_licencias_desconocidas_se_cuentan_aparte(tmp_path):
    proc, gh, _ = _license(tmp_path, [{"package": "x", "license": "Unknown"}])
    assert proc.returncode == 0 and "| 1 | 0 | 0 | 1 |" in gh["GITHUB_STEP_SUMMARY"]


# ───────────────────────── k8s scale (GitOps) ─────────────────────────

SCALE_PRELUDE = GIT_PRELUDE + """
git init -q --bare /w/bare.git
git init -q /w/seed && cd /w/seed && mkdir -p k8s/DEV
printf 'kind: Deployment\\nspec:\\n  replicas: 1\\n' > k8s/DEV/api.yaml
printf 'kind: Deployment\\nspec:\\n  replicas: 0\\n' > k8s/DEV/web.yml
git add . && git commit -qm seed && git remote add origin /w/bare.git && git push -q origin main
git clone -q /w/bare.git /w/infra_repo && cd /w/infra_repo
"""
SCALE_POST = """
echo "---LOG---"; git --git-dir=/w/bare.git log --oneline -1
echo "---API---"; git --git-dir=/w/bare.git show main:k8s/DEV/api.yaml
echo "---WEB---"; git --git-dir=/w/bare.git show main:k8s/DEV/web.yml
"""


def _scale(tmp_path, action):
    script = step_run("k8s-scale.yml", "scale", "Escalar")
    return run_step(tmp_path, script, env={"ACTION": action, "TARGET_PATH": "k8s/DEV", "INFRA_BRANCH": "main"},
                    prelude=SCALE_PRELUDE, post=SCALE_POST, cwd=".")


def test_scale_down_apaga_lo_que_corre_y_empuja_el_cambio(tmp_path):
    proc, _, work = _scale(tmp_path, "down")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    out = proc.stdout
    assert "Auto-scale down: 1 servicios (k8s/DEV)" in out
    assert out.split("---API---")[1].split("---WEB---")[0].count("replicas: 0") == 1
    assert 'api: "Apagado (0)"' in (work / "release_info.yml").read_text()


def test_scale_up_enciende_lo_apagado(tmp_path):
    proc, _, work = _scale(tmp_path, "up")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "replicas: 1" in proc.stdout.split("---WEB---")[1]
    assert 'web: "Encendido (1)"' in (work / "release_info.yml").read_text()


def test_scale_con_accion_invalida_falla(tmp_path):
    proc, _, _ = _scale(tmp_path, "sideways")
    assert proc.returncode != 0 and "ACTION debe ser up o down" in proc.stdout


# ───────────────────────── PR description (stub de gh) ─────────────────────────

GH_STUB_PR = """
case "$*" in
  *"/commits"*) echo '[{"sha":"abc1234","title":"feat: login"},{"sha":"def5678","title":"fix: bug"},{"sha":"0000000","title":"misc cosa"}]' ;;
  *"api repos/o/repo/pulls/5 --jq"*"changed_files"*) echo "3 120 40" ;;
  *"api repos/o/repo/pulls/5 --jq"*) printf '%s\\n' "Texto escrito por la persona autora" "" "<!-- auto-pr-description:start -->" "viejo" "<!-- auto-pr-description:end -->" ;;
  "pr edit"*"--body-file"*) cp "$5" /w/captured-body.md; echo "$@" >> /w/gh-calls.log ;;
  *) echo "$@" >> /w/gh-calls.log ;;
esac
"""


def test_descripcion_del_pr_agrupa_commits_y_conserva_el_texto_manual(tmp_path):
    script = step_run("utilities-mr-description.yml", "generate_pr_description", "Construir y publicar descripción")
    env = {"PR_NUMBER": "5", "MR_DESC_MAX_COMMITS": "50", "MR_DESC_ADD_STATS": "true", "MR_DESC_ADD_CHECKLIST": "true",
           "MR_DESC_AUTO_LABEL": "true", "GH_TOKEN": "x"}
    # stub más fiel: gh api <path> --jq <expr> → decidimos por el path y la expresión
    stub = textwrap.dedent("""
        args="$*"
        if [[ "$1" == "api" && "$2" == *"/commits"* ]]; then
          echo '[{"sha":"abc1234","title":"feat: login"},{"sha":"def5678","title":"fix: bug"},{"sha":"0000000","title":"misc cosa"}]'
        elif [[ "$1" == "api" && "$args" == *changed_files* ]]; then
          echo "3 120 40"
        elif [[ "$1" == "api" ]]; then
          printf '%s\\n' "Texto escrito por la persona autora" "" "<!-- auto-pr-description:start -->" "viejo" "<!-- auto-pr-description:end -->"
        elif [[ "$1 $2" == "pr edit" && "$args" == *--body-file* ]]; then
          cp "$7" /w/captured-body.md
        else
          echo "$args" >> /w/gh-calls.log
        fi
    """)
    proc, _, work = run_step(tmp_path, script, env=env, stubs={"gh": stub}, post="")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    body = (work / "captured-body.md").read_text()
    assert body.startswith("Texto escrito por la persona autora")
    assert "viejo" not in body                       # el bloque automático previo se reemplaza
    assert "### 🚀 Nuevas funcionalidades" in body and "feat: login (`abc1234`)" in body
    assert "### 🐛 Correcciones" in body and "### 📝 Otros" in body and "misc cosa" in body
    assert "| Commits | 3 |" in body and "+120" in body and "-40" in body
    assert "- [ ] Código revisado" in body
    assert body.count("<!-- auto-pr-description:start -->") == 1 and body.count("<!-- auto-pr-description:end -->") == 1
    calls = (work / "gh-calls.log").read_text()
    for label in ("feature", "bugfix", "size/S"):
        assert f"--add-label {label}" in calls


# ───────────────────────── release (stub de gh) ─────────────────────────

CHANGELOG = textwrap.dedent("""\
    # Changelog

    ## [2.0.0] - 2026-02-01
    ### Nuevo
    - cosa 2.0

    ## [1.0.0] - 2026-01-01
    - cosa 1.0
    """)
GH_STUB_RELEASE = """
echo "$@" >> /w/gh-calls.log
if [[ "$1 $2" == "release view" ]]; then exit ${RELEASE_EXISTS:-1}; fi
if [[ "$1 $2" == "release create" || "$1 $2" == "release edit" ]]; then cp release_notes_*.md /w/captured-notes.md; fi
"""


def _release(tmp_path, tag, files, exists=False, **env):
    script = step_run("utilities-release.yml", "create_release", "Crear o actualizar release")
    return run_step(tmp_path, script, files=files, stubs={"gh": GH_STUB_RELEASE},
                    env={"RELEASE_TAG": tag, "PRERELEASE": "false", "RELEASE_EXISTS": "0" if exists else "1", **env})


def test_release_usa_la_seccion_del_tag_en_el_changelog(tmp_path):
    proc, _, work = _release(tmp_path, "v1.0.0", {"CHANGELOG.md": CHANGELOG})
    assert proc.returncode == 0, proc.stdout + proc.stderr
    notes = (work / "captured-notes.md").read_text()
    assert "cosa 1.0" in notes and "cosa 2.0" not in notes
    assert "release create v1.0.0 --title Release v1.0.0" in (work / "gh-calls.log").read_text()
    assert "--verify-tag" in (work / "gh-calls.log").read_text()


def test_release_prefiere_release_notes_de_ia(tmp_path):
    proc, _, work = _release(tmp_path, "v2.0.0", {"CHANGELOG.md": CHANGELOG, "RELEASE_NOTES.md": "# Notas IA\nhola\n"})
    assert proc.returncode == 0
    assert (work / "captured-notes.md").read_text().startswith("# Notas IA")


def test_release_actualiza_si_ya_existe_y_marca_prerelease(tmp_path):
    proc, _, work = _release(tmp_path, "v2.0.0", {"CHANGELOG.md": CHANGELOG}, exists=True, PRERELEASE="true")
    assert proc.returncode == 0
    calls = (work / "gh-calls.log").read_text()
    assert "release edit v2.0.0" in calls and "--prerelease" in calls and "release create" not in calls


def test_release_sin_notas_usa_el_fallback(tmp_path):
    proc, _, work = _release(tmp_path, "v9.9.9", {})
    assert proc.returncode == 0
    assert (work / "captured-notes.md").read_text().strip() == "## Release v9.9.9"


# ───────────────────────── terraform: credenciales cloud ─────────────────────────

def test_credenciales_cloud_van_a_github_env_y_se_enmascaran(tmp_path):
    script = step_run("infrastructure-terraform.yml", "tf_plan", "Credenciales cloud")
    proc, gh, _ = run_step(tmp_path, script, env={"TF_CLOUD_ENV": "AWS_ACCESS_KEY_ID=AKIA123\n\nAWS_SECRET_ACCESS_KEY=s3cr=et\n"})
    assert proc.returncode == 0, proc.stderr
    assert gh["GITHUB_ENV"].splitlines() == ["AWS_ACCESS_KEY_ID=AKIA123", "AWS_SECRET_ACCESS_KEY=s3cr=et"]
    assert "::add-mask::AKIA123" in proc.stdout and "::add-mask::s3cr=et" in proc.stdout


# ───────────────────────── scaffold ─────────────────────────

def test_scaffold_genera_workflow_de_github_y_dockerfile(tmp_path):
    script = step_run("doc-project-scaffold.yml", "project_scaffold", "Scaffold del proyecto")
    proc, _, work = run_step(tmp_path, script, files={"go.mod": "module x\n"},
                             env={"SCAFFOLD_DISABLED": "false", "SCAFFOLD_LANG": "", "SCAFFOLD_NAME": "svc", "SCAFFOLD_FORCE": "false"})
    assert proc.returncode == 0, proc.stdout + proc.stderr
    ci = (work / ".github" / "workflows" / "ci-cd.yml").read_text()
    assert "uses: grs89/github-template/.github/workflows/03-start-init.yml@main" in ci and "secrets: inherit" in ci
    assert (work / "Dockerfile").read_text().startswith("FROM golang")
    assert not (work / ".gitlab-ci.yml").exists()
    assert "Lenguaje detectado: go" in proc.stdout


def test_scaffold_no_pisa_un_workflow_existente(tmp_path):
    script = step_run("doc-project-scaffold.yml", "project_scaffold", "Scaffold del proyecto")
    proc, _, work = run_step(tmp_path, script, files={".github/workflows/ci-cd.yml": "mio\n", "package.json": "{}"},
                             env={"SCAFFOLD_DISABLED": "false", "SCAFFOLD_LANG": "", "SCAFFOLD_NAME": "svc", "SCAFFOLD_FORCE": "false"})
    assert proc.returncode == 0
    assert (work / ".github" / "workflows" / "ci-cd.yml").read_text() == "mio\n"


# ───────────────────────── smoke tests (script portado) ─────────────────────────

def test_smoke_tests_contra_servidor_local(tmp_path):
    script = step_run("observability-smoke-tests.yml", "smoke_tests", "smoke tests")
    server = ("python3 -c \"import http.server as h\n"
              "class H(h.BaseHTTPRequestHandler):\n"
              "    def do_GET(s):\n"
              "        s.send_response(200 if s.path=='/ok' else 500); s.end_headers()\n"
              "    def log_message(s,*a): pass\n"
              "h.HTTPServer(('127.0.0.1',8765),H).serve_forever()\" & sleep 1\n")
    env = {"SMOKE_DISABLED": "false", "SMOKE_TIMEOUT": "2", "SMOKE_RETRIES": "1", "SMOKE_RETRY_DELAY": "0",
           "SMOKE_EXPECTED_STATUS": "200", "SMOKE_FAIL_ON_ERROR": "true"}
    ok, _, work = run_step(tmp_path / "a", script, env={**env, "SMOKE_ENDPOINTS": "http://127.0.0.1:8765/ok"}, prelude=server)
    assert ok.returncode == 0, ok.stdout + ok.stderr
    assert json.loads((work / "smoke-test-report.json").read_text())[0]["result"] == "pass"
    bad, _, work = run_step(tmp_path / "b", script, env={**env, "SMOKE_ENDPOINTS": "http://127.0.0.1:8765/ok,http://127.0.0.1:8765/boom"}, prelude=server)
    assert bad.returncode == 1 and "1 smoke tests fallidos" in bad.stdout


# ───────────────────────── notificaciones y DORA (colector HTTP local) ─────────────────────────

COLLECTOR = """
cat > /tmp/collector.py <<'PY'
import http.server as h, sys
class H(h.BaseHTTPRequestHandler):
    def do_POST(s):
        body = s.rfile.read(int(s.headers['Content-Length']))
        open('/w/captured.json', 'wb').write(body)
        open('/w/captured.auth', 'w').write(s.headers.get('Authorization') or '')
        s.send_response(200); s.end_headers()
    def log_message(s, *a): pass
h.HTTPServer(('127.0.0.1', 8766), H).serve_forever()
PY
python3 /tmp/collector.py & sleep 1
"""


def test_dora_envia_el_evento_con_lead_time_y_bearer(tmp_path):
    script = step_run("observability-dora-metrics.yml", "dora_record", "Enviar evento")
    proc, _, work = run_step(tmp_path, script, prelude=GIT_PRELUDE + "git init -q /w && git -C /w commit -q --allow-empty -m x\n" + COLLECTOR,
                             env={"DORA_COLLECTOR_URL": "http://127.0.0.1:8766/events", "DORA_EVENT": "deployment_recovery",
                                  "DORA_ENV": "production", "DORA_API_TOKEN": "tok", "REPO_NAME": "repo", "GITHUB_SHA": "HEAD"})
    assert proc.returncode == 0, proc.stdout + proc.stderr
    payload = json.loads((work / "captured.json").read_text())
    assert payload["event_type"] == "deployment_recovery" and payload["service_name"] == "repo"
    assert payload["environment"] == "production" and payload["pipeline_id"] == "99" and payload["author"] == "tester"
    assert isinstance(payload["lead_time_seconds"], int) and payload["timestamp"].endswith("Z")
    assert (work / "captured.auth").read_text() == "Bearer tok"


def test_notificacion_google_chat_incluye_resumen_de_release(tmp_path):
    script = step_run("utilities-notifications.yml", "notify", "Enviar notificación")
    release = 'last_update: "2026-01-01 10:00:00"\nenvironment: "k8s/DEV"\nmicroservicios:\n  api: "v1"\n'
    proc, _, work = run_step(tmp_path, script, files={"release_info.yml": release}, prelude=COLLECTOR,
                             env={"GOOGLE_CHAT_WEBHOOK": "http://127.0.0.1:8766/hook", "JOB_STATUS": "failure",
                                  "RELEASE_FILE": "release_info.yml", "COMPONENT_FILE": "nope.yml", "COMMIT_TITLE": "feat: algo\ncuerpo",
                                  "PIPELINE_URL": "https://github.com/o/repo/actions/runs/99", "REPO_NAME": "repo"})
    assert proc.returncode == 0, proc.stdout + proc.stderr
    card = json.loads((work / "captured.json").read_text())["cards"][0]
    assert card["header"]["title"] == "❌ repo: Pipeline fallido" and card["header"]["subtitle"] == "Run #7 - Rama: main"
    widgets = card["sections"][0]["widgets"]
    assert widgets[0]["keyValue"]["content"] == "feat: algo"            # solo la primera línea del commit
    assert any("k8s/DEV" in w.get("textParagraph", {}).get("text", "") for w in widgets)
    assert widgets[-1]["buttons"][0]["textButton"]["onClick"]["openLink"]["url"].endswith("/runs/99")


def test_notificacion_sin_webhook_no_falla(tmp_path):
    script = step_run("utilities-notifications.yml", "notify", "Enviar notificación")
    proc, _, _ = run_step(tmp_path, script, env={"GOOGLE_CHAT_WEBHOOK": "", "JOB_STATUS": "success", "RELEASE_FILE": "x", "COMPONENT_FILE": "y"})
    assert proc.returncode == 0 and "GOOGLE_CHAT_WEBHOOK no está configurado" in proc.stdout


# ───────────────────────── changelog: commit y push ─────────────────────────

def test_changelog_se_commitea_y_empuja(tmp_path):
    script = step_run("utilities-changelog.yml", "generate_changelog", "Commit del changelog")
    prelude = GIT_PRELUDE + """
git init -q --bare /w/bare.git
git init -q /w/repo && cd /w/repo && git commit -q --allow-empty -m init && git remote add origin /w/bare.git && git push -q origin main
echo '# Changelog' > CHANGELOG.md
"""
    proc, _, work = run_step(tmp_path, script, prelude=prelude, cwd=".",
                             env={"CHANGELOG_FILE": "CHANGELOG.md", "CHANGELOG_COMMIT_PUSH": "true"},
                             post="git --git-dir=/w/bare.git log --oneline -1")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "chore: actualizar changelog [skip ci]" in proc.stdout


# ───────────────────────── strix: conteo de severidades del SARIF ─────────────────────────

def test_strix_cuenta_hallazgos_bloqueantes_desde_sarif(tmp_path):
    run = step_run("security-strix-pentest.yml", "ai_strix_pentest", "Ejecutar Strix")
    py = run.split("<<'PYEOF'\n")[1].split("\nPYEOF")[0]
    sarif = {"runs": [{"tool": {"driver": {"rules": [{"id": "A", "properties": {"security-severity": "9.8"}},
                                                      {"id": "B", "properties": {"security-severity": "5.0"}}]}},
                       "results": [{"ruleId": "A"}, {"ruleId": "B"}, {"ruleId": "C", "level": "error"}]}]}
    for want, expected in (("CRITICAL", "1"), ("CRITICAL,HIGH", "2"), ("medium", "1")):
        proc, _, _ = run_step(tmp_path / want.replace(",", "_"), "python3 /w/count.py", files={"strix.sarif": json.dumps(sarif), "count.py": py},
                              env={"SECURITY_FAIL_SEVERITY": want})
        assert proc.stdout.strip() == expected, (want, proc.stdout, proc.stderr)


# ───────────────────────── canary (stub de kubectl) ─────────────────────────

KUBECTL_STUB = """
echo "kubectl $*" >> /w/kubectl.log
if [[ "$*" == *"apply"* ]]; then cat >> /w/applied.yaml; fi
if [[ "$*" == "get deployment"* && "$*" == *"-o yaml"* ]]; then exit ${HAS_STABLE:-1}; fi
exit 0
"""
CANARY_ENV = {"CANARY_WEIGHT": "20", "CANARY_REPLICAS": "2", "K8S_NAMESPACE": "prod", "IMAGE_TAG": "v1.2.3",
              "REGISTRY": "ghcr.io", "REPO_NAME": "app", "GITHUB_REPOSITORY": "org/app"}


def test_canary_primera_version_crea_deployment_con_la_imagen_de_ghcr(tmp_path):
    script = step_run("deploy-canary-deploy.yml", "canary_deploy", "canary deploy")
    proc, _, work = run_step(tmp_path, script, stubs={"kubectl": KUBECTL_STUB}, env=CANARY_ENV)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    applied = (work / "applied.yaml").read_text()
    assert "name: app-canary" in applied and "image: ghcr.io/org/app:v1.2.3" in applied and "replicas: 2" in applied
    log = (work / "kubectl.log").read_text()
    assert "rollout status deployment/app-canary -n prod" in log


def test_canary_promote_actualiza_el_estable_y_borra_el_canary(tmp_path):
    script = step_run("deploy-canary-deploy.yml", "canary_promote", "canary promote")
    proc, _, work = run_step(tmp_path, script, stubs={"kubectl": KUBECTL_STUB}, env=CANARY_ENV)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    log = (work / "kubectl.log").read_text()
    assert "set image deployment/app app=ghcr.io/org/app:v1.2.3 -n prod" in log
    assert "delete deployment app-canary -n prod --ignore-not-found=true" in log


# ───────────────────────── grafana (colector HTTP local) ─────────────────────────

def test_anotacion_de_grafana_arma_payload_y_bearer(tmp_path):
    script = step_run("observability-grafana-annotations.yml", "grafana_annotation", "grafana annotation")
    prelude = COLLECTOR.replace("/events", "")  # el colector acepta cualquier path
    proc, _, work = run_step(tmp_path, script, prelude=prelude,
                             env={"GRAFANA_DISABLED": "false", "GRAFANA_URL": "http://127.0.0.1:8766", "GRAFANA_API_KEY": "key",
                                  "GRAFANA_TAGS": "deploy", "GRAFANA_TEXT": "", "GRAFANA_DASHBOARD_ID": "", "IMAGE_TAG": "v9",
                                  "REPO_NAME": "app", "GITHUB_REF_NAME": "main"})
    assert proc.returncode == 0, proc.stdout + proc.stderr
    body = json.loads((work / "captured.json").read_text())
    assert set(body["tags"]) == {"deploy", "app", "PROD"} and "Imagen: v9" in body["text"] and "Ambiente: PROD" in body["text"]
    assert (work / "captured.auth").read_text() == "Bearer key"


# ───────────────────────── kubeconform (descarga real + manifiestos) ─────────────────────────

VALID = "apiVersion: apps/v1\nkind: Deployment\nmetadata:\n  name: a\nspec:\n  replicas: 1\n  selector:\n    matchLabels: {app: a}\n  template:\n    metadata:\n      labels: {app: a}\n    spec:\n      containers:\n        - name: a\n          image: nginx:1.27\n"


def _kubeconform(tmp_path, files):
    script = step_run("quality-lint-argocd.yml", "kubeconform", "kubeconform")
    return run_step(tmp_path, script, files=files, env={"ARGOCD_MANIFEST_PATH": ".", "K8S_VERSION": "1.30.0"})


def test_kubeconform_acepta_manifiestos_validos_e_ignora_yaml_que_no_es_k8s(tmp_path):
    proc, _, _ = _kubeconform(tmp_path, {"k8s/dep.yaml": VALID, "config.yaml": "foo: bar\n"})
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "Validando 1 manifiestos" in proc.stdout


def test_kubeconform_rechaza_un_manifiesto_invalido(tmp_path):
    proc, _, _ = _kubeconform(tmp_path, {"k8s/bad.yaml": VALID.replace("replicas: 1", "replicas: muchas")})
    assert proc.returncode != 0


def test_kubeconform_sin_manifiestos_se_omite(tmp_path):
    proc, _, _ = _kubeconform(tmp_path, {"config.yaml": "foo: bar\n"})
    assert proc.returncode == 0 and "Omitiendo" in proc.stdout


# ───────────────────────── mirror a Git externo: validaciones ─────────────────────────

def _mirror(tmp_path, url, **env):
    script = step_run("git-external-git.yml", "sync_to_external", "Sincronizar")
    return run_step(tmp_path, script, prelude=GIT_PRELUDE + "git init -q /w && git commit -q --allow-empty -m x\n",
                    env={"EXTERNAL_REPO_URL": url, "EXTERNAL_GIT_USER": "oauth2", "SYNC_ALL_BRANCHES": "true",
                         "SYNC_ALL_TAGS": "true", "EXTERNAL_GIT_TOKEN": "", "EXTERNAL_GIT_SSH_KEY": "", **env})


def test_mirror_https_exige_token(tmp_path):
    proc, _, _ = _mirror(tmp_path, "https://gitlab.com/g/r.git")
    assert proc.returncode == 1 and "EXTERNAL_GIT_TOKEN" in proc.stdout


def test_mirror_ssh_exige_llave(tmp_path):
    proc, _, _ = _mirror(tmp_path, "git@gitlab.com:g/r.git")
    assert proc.returncode == 1 and "EXTERNAL_GIT_SSH_KEY" in proc.stdout


def test_mirror_rechaza_esquemas_no_soportados(tmp_path):
    proc, _, _ = _mirror(tmp_path, "http://insegura/r.git")
    assert proc.returncode == 1 and "debe ser https:// o SSH" in proc.stdout
