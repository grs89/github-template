#!/usr/bin/env python3
"""
export_otel_traces.py
Exportador de Observabilidad OpenTelemetry (OTel) para GitHub Actions.
Convierte la ejecución de un workflow run (jobs de workflows reutilizables y sus steps) en trazas
compatibles con OTLP/HTTP JSON (/v1/traces) para Grafana Tempo, Jaeger y Datadog.
Totalmente no-bloqueante: ante cualquier fallo de red o API termina con código 0.
"""

import os
import re
import sys
import json
import time
import hashlib
import datetime
import urllib.error
import urllib.parse
import urllib.request


def generate_trace_id(pipeline_id, project_name):
    """Genera un TraceID hexadecimal de 32 caracteres (MD5 de project_name-pipeline_id)."""
    raw = f"{project_name}-{pipeline_id}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


def generate_span_id(unique_key):
    """Genera un SpanID hexadecimal de 16 caracteres (SHA256 truncado a 16 chars)."""
    return hashlib.sha256(str(unique_key).encode("utf-8")).hexdigest()[:16]


def iso_to_nanos(iso_str, fallback_ns=None):
    """Convierte un timestamp ISO 8601 de GitLab (ej: 2026-09-10T12:00:20.123Z) a nanosegundos Unix."""
    if not iso_str:
        return fallback_ns
    try:
        clean = iso_str.replace("Z", "+00:00")
        dt = datetime.datetime.fromisoformat(clean)
        return int(dt.timestamp() * 1e9)
    except Exception:
        return fallback_ns


def build_attributes(kv_dict):
    """Formatea un diccionario a la lista de atributos OTLP JSON."""
    attrs = []
    for k, v in kv_dict.items():
        if v is None:
            continue
        if isinstance(v, bool):
            attrs.append({"key": k, "value": {"boolValue": v}})
        elif isinstance(v, (int, float)):
            attrs.append({"key": k, "value": {"doubleValue": float(v)}})
        else:
            attrs.append({"key": k, "value": {"stringValue": str(v)}})
    return attrs


def build_span(trace_id, span_id, parent_span_id, name, start_ns, end_ns, status_str, attrs_dict):
    """Construye un objeto Span en formato OTLP."""
    # Garantizar que el end_ns sea estrictamente mayor al start_ns
    if end_ns < start_ns:
        end_ns = start_ns + 1_000_000 # +1ms
    elif end_ns == start_ns:
        end_ns = start_ns + 1_000_000 # +1ms

    # Mapeo de status OTel: 1 = OK, 2 = ERROR, 0 = UNSET
    if status_str == "success":
        status_code = 1
        status_msg = "Success"
    elif status_str in ["failed", "canceled"]:
        status_code = 2
        status_msg = f"Job {status_str}"
    else:
        status_code = 0
        status_msg = status_str or "Unknown"

    span = {
        "traceId": trace_id,
        "spanId": span_id,
        "name": name,
        "kind": 1, # SPAN_KIND_INTERNAL
        "startTimeUnixNano": str(start_ns),
        "endTimeUnixNano": str(end_ns),
        "attributes": build_attributes(attrs_dict),
        "status": {
            "code": status_code,
            "message": status_msg
        }
    }
    if parent_span_id:
        span["parentSpanId"] = parent_span_id

    return span


def send_otlp_payload(endpoint, payload, auth_token=None):
    """Envía el payload OTLP JSON hacia el OTel Collector."""
    target_url = endpoint.rstrip("/")
    if not target_url.endswith("/v1/traces"):
        target_url = f"{target_url}/v1/traces"

    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        target_url,
        data=body,
        headers={"Content-Type": "application/json"}
    )
    if auth_token:
        req.add_header("Authorization", f"Bearer {auth_token}")

    print(f"📡 Emitiendo traza OTel -> {target_url}")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status in [200, 202]:
                print(f"✅ Telemetría OTel entregada exitosamente (HTTP {resp.status}).")
                return True
            else:
                print(f"ℹ️ Colector OTel respondió HTTP {resp.status}.")
                return False
    except urllib.error.URLError as e:
        print(f"⚠️ Colector OTel no accesible ({e.reason}). Continuando pipeline de forma segura.")
    except Exception as e:
        print(f"⚠️ Telemetría OTel no enviada ({e}). Continuando pipeline.")
    return False


def print_grafana_link(trace_id):
    """Genera e imprime el enlace directo hacia Grafana Explore para la traza actual."""
    grafana_url = os.getenv("GRAFANA_URL", "").rstrip("/")
    if not grafana_url:
        return None

    ds_name = os.getenv("GRAFANA_TEMPO_DATASOURCE_NAME", "Tempo")
    explore_payload = {
        "datasource": ds_name,
        "queries": [
            {"refId": "A", "queryType": "traceql", "query": trace_id}
        ]
    }
    explore_query_encoded = urllib.parse.quote(json.dumps(explore_payload))
    explore_url = f"{grafana_url}/explore?left={explore_query_encoded}"

    print("")
    print("════════════════════════════════════════════════════════════════")
    print("🚀 Telemetría CI/CD lista en Grafana Tempo.")
    print("🔗 Ver Cascada de Pipeline (1-Clic):")
    print(f"   {explore_url}")
    print("════════════════════════════════════════════════════════════════")
    print("")

    # Generar archivo de redirección HTML como artefacto descargable / visualizable
    try:
        html_content = f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta http-equiv="refresh" content="0; url='{explore_url}'" />
  <title>Redirigiendo a Grafana Tempo...</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #111217; color: #fff; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }}
    .card {{ background: #181b1f; padding: 2rem; border-radius: 8px; border: 1px solid #22252b; text-align: center; max-width: 500px; }}
    a {{ color: #3274d9; text-decoration: none; font-weight: bold; }}
    a:hover {{ text-decoration: underline; }}
  </style>
</head>
<body>
  <div class="card">
    <h2>📊 Pipeline Observability — Grafana Tempo</h2>
    <p>Redirigiendo a la traza en tu Grafana remoto...</p>
    <p><a href="{explore_url}">Haz clic aquí si tu navegador no redirige automáticamente</a></p>
  </div>
</body>
</html>"""
        with open("grafana_trace.html", "w", encoding="utf-8") as f:
            f.write(html_content)
        print("📄 Archivo de acceso directo creado: grafana_trace.html")
    except Exception as e:
        print(f"ℹ️ No se pudo crear grafana_trace.html: {e}")

    return explore_url


def github_api_get(url, token=None):
    """GET autenticado a la API REST de GitHub. Devuelve JSON o None."""
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    req.add_header("User-Agent", "github-templates-otel/1.0")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status == 200:
                return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print(f"ℹ️ GitHub API {e.code} en {url}: {e.reason}")
    except Exception as e:
        print(f"ℹ️ No se pudo consultar GitHub API ({url}): {e}")
    return None


def extract_service_name(job_name, default):
    """Servicio a partir del nombre del job: '... [svc] / job' o 'caller / job'; si no, el proyecto."""
    m = re.search(r"\[\s*([^,\s\]]+)", job_name or "")
    if m:
        return m.group(1).strip()
    return default


def conclusion_to_status(conclusion):
    """Mapea conclusion de GitHub al vocabulario de build_span (success / failed / otro)."""
    if conclusion == "success":
        return "success"
    if conclusion in ("failure", "cancelled", "timed_out", "startup_failure"):
        return "failed"
    return conclusion or "unknown"


def fetch_jobs(api_url, repo, run_id, token, max_pages=10):
    """Jobs del run (incluye los de workflows reutilizables), paginados."""
    jobs = []
    for page in range(1, max_pages + 1):
        data = github_api_get(f"{api_url}/repos/{repo}/actions/runs/{run_id}/jobs?per_page=100&page={page}", token)
        batch = (data or {}).get("jobs", [])
        jobs.extend(batch)
        if len(batch) < 100:
            break
    return jobs


def build_trace_payload(run, jobs, project_name, now_ns):
    """Construye el payload OTLP (resourceSpans) de un run: raíz + jobs + steps, agrupado por servicio."""
    run_id = run.get("id", "0")
    trace_id = generate_trace_id(run_id, project_name)
    root_span_id = generate_span_id(f"run-{run_id}")
    ref = run.get("head_branch", "")
    sha = run.get("head_sha", "")

    run_start = iso_to_nanos(run.get("run_started_at") or run.get("created_at"), now_ns)
    run_end = iso_to_nanos(run.get("updated_at"), now_ns)
    root_attrs = {
        "ci.pipeline.id": str(run_id),
        "ci.pipeline.url": run.get("html_url", ""),
        "ci.pipeline.ref": ref,
        "vcs.commit.sha": sha,
        "ci.pipeline.status": run.get("conclusion") or run.get("status"),
    }
    root_span = build_span(trace_id, root_span_id, None, f"workflow: {run.get('name', 'run')} #{run.get('run_number', run_id)} ({ref})",
                           run_start, run_end, conclusion_to_status(run.get("conclusion")), root_attrs)

    by_service = {project_name: [root_span]}
    for job in jobs:
        j_name = job.get("name", f"job-{job.get('id')}")
        svc = extract_service_name(j_name, project_name)
        j_start = iso_to_nanos(job.get("started_at"), run_start)
        j_end = iso_to_nanos(job.get("completed_at"), now_ns)
        job_span_id = generate_span_id(f"job-{job.get('id')}")
        by_service.setdefault(svc, []).append(build_span(
            trace_id, job_span_id, root_span_id, j_name, j_start, j_end,
            conclusion_to_status(job.get("conclusion")),
            {"ci.job.id": str(job.get("id")), "ci.job.name": j_name, "ci.job.status": job.get("conclusion") or job.get("status"),
             "ci.job.url": job.get("html_url", ""), "ci.runner.name": job.get("runner_name", ""),
             "ci.service.name": svc, "ci.pipeline.id": str(run_id)}))
        for step in job.get("steps") or []:
            s_start = iso_to_nanos(step.get("started_at"), j_start)
            s_end = iso_to_nanos(step.get("completed_at"), s_start)
            by_service[svc].append(build_span(
                trace_id, generate_span_id(f"step-{job.get('id')}-{step.get('number')}"), job_span_id,
                step.get("name", "step"), s_start, s_end, conclusion_to_status(step.get("conclusion")),
                {"ci.step.number": step.get("number"), "ci.step.name": step.get("name"), "ci.service.name": svc}))

    resource_spans = []
    for svc, spans in by_service.items():
        name = project_name if svc == project_name else f"{project_name}:{svc}"
        resource_spans.append({
            "resource": {"attributes": build_attributes({
                "service.name": name, "service.namespace": "ci-cd", "ci.pipeline.id": str(run_id),
                "ci.pipeline.ref": ref, "vcs.commit.sha": sha})},
            "scopeSpans": [{"scope": {"name": "github-actions-telemetry", "version": "1.0.0"}, "spans": spans}],
        })
    return {"resourceSpans": resource_spans}, trace_id


def export_full_run_trace(endpoint, auth_token=None):
    api_url = os.getenv("GITHUB_API_URL", "https://api.github.com")
    repo = os.getenv("GITHUB_REPOSITORY", "")
    run_id = os.getenv("GITHUB_RUN_ID", "")
    token = os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN")
    project_name = repo.split("/")[-1] or "pipeline"
    now_ns = int(time.time() * 1e9)

    print(f"🔍 Consultando run #{run_id} de {repo} en la API de GitHub...")
    run = github_api_get(f"{api_url}/repos/{repo}/actions/runs/{run_id}", token)
    if not run:
        print("⚠️ No se pudo consultar el run. Omitiendo telemetría de forma segura.")
        return False
    jobs = fetch_jobs(api_url, repo, run_id, token)
    payload, trace_id = build_trace_payload(run, jobs, project_name, now_ns)
    spans = sum(len(s["scopeSpans"][0]["spans"]) for s in payload["resourceSpans"])
    print(f"📊 TraceID: {trace_id} | spans: {spans} | servicios: {len(payload['resourceSpans'])}")
    ok = send_otlp_payload(endpoint, payload, auth_token)
    print_grafana_link(trace_id)
    return ok


def main():
    endpoint = os.getenv("OTEL_COLLECTOR_URL", os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", ""))
    auth_token = os.getenv("OTEL_AUTH_TOKEN", "")
    if not endpoint:
        print("ℹ️ OTEL_COLLECTOR_URL no configurado. Omitiendo emisión de telemetría de forma segura.")
        return
    if not (os.getenv("GITHUB_RUN_ID") and os.getenv("GITHUB_REPOSITORY")):
        print("ℹ️ Fuera de GitHub Actions (GITHUB_RUN_ID/GITHUB_REPOSITORY ausentes). Omitiendo.")
        return
    export_full_run_trace(endpoint, auth_token)


if __name__ == "__main__":
    main()
