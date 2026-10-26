#!/usr/bin/env python3
"""
sync_roadmap_milestones.py

Script para parsear ROADMAP.md y sincronizar iniciativas como Milestones e Issues
en GitHub utilizando la API REST de GitHub. Soporta fecha de inicio (se documenta en la descripción),
fecha de fin (due_on) y enlace al Release oficial.
"""

import os
import sys
import re
import json
import argparse
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime


def _extract_priority(text):
    """Extrae la prioridad desde texto con emojis o texto plano."""
    text = text.strip()
    if "🔴" in text or "Alta" in text or "Critical" in text or "High" in text:
        return "Alta"
    if "🟠" in text or "Media" in text or "Medium" in text:
        return "Media"
    if "🟡" in text or "Baja" in text or "Low" in text:
        return "Baja"
    return text


def _clean_date(date_str):
    """Limpia y valida formato de fecha YYYY-MM-DD."""
    if not date_str:
        return None
    match = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", date_str)
    if match:
        return match.group(1)
    return None


def _get_default_release():
    """Obtiene la versión leyendo dinámicamente version.yml o el tag del evento."""
    env_tag = os.getenv("CI_COMMIT_TAG") or (os.getenv("GITHUB_REF_NAME") if os.getenv("GITHUB_REF_TYPE") == "tag" else None)
    if env_tag:
        return env_tag.strip()

    # Buscar version.yml en directorio de trabajo o relativo al script
    candidate_paths = [
        "version.yml",
        os.path.join(os.path.dirname(__file__), "..", "version.yml"),
        os.path.join(os.path.dirname(__file__), "version.yml")
    ]
    for path in candidate_paths:
        if os.path.isfile(path):
            try:
                with open(path, encoding="utf-8") as f:
                    for line in f:
                        clean_line = line.strip()
                        if clean_line.startswith("version:"):
                            val = clean_line.split(":", 1)[1].strip().strip('"').strip("'")
                            if val:
                                return val
            except Exception:
                pass
    return "latest"


def _clean_release(rel_str):
    """Limpia el tag del release eliminando comillas invertidas (ej. `vX.Y.Z` -> vX.Y.Z)."""
    if not rel_str:
        return None
    return rel_str.replace("`", "").strip()


def _parse_format_standard(content):
    """
    Formato estándar de las plantillas con soporte extendido para:
    - 5 columnas: | # | **Nombre** | Tendencia | Prioridad | Estado |
    - 7 columnas: | # | **Nombre** | Tendencia | Prioridad | Fecha Fin | Release | Estado |
    - 8 columnas: | # | **Nombre** | Tendencia | Prioridad | Fecha Inicio | Fecha Fin | Release | Estado |
    """
    initiatives = []
    default_release = _get_default_release()
    
    # 1. Intentar formato extendido de 8 columnas (sin cruzar saltos de línea)
    pattern_8 = re.compile(
        r"\|\s*(\d+)\s*\|\s*\*\*([^*]+)\*\*\s*\|\s*([^|\r\n]+)\|\s*([^|\r\n]+)\|\s*([^|\r\n]+)\|\s*([^|\r\n]+)\|\s*([^|\r\n]+)\|\s*([^|\r\n]+)\|"
    )
    matches_8 = pattern_8.findall(content)
    if matches_8:
        for num, name, trend, priority, start_d, due_d, rel, status in matches_8:
            initiatives.append({
                "number": num.strip(),
                "title": name.strip(),
                "trend": trend.strip(),
                "priority": _extract_priority(priority),
                "start_date": _clean_date(start_d),
                "due_date": _clean_date(due_d),
                "release": _clean_release(rel) or default_release,
                "status": status.strip(),
                "description": ""
            })
        return _attach_details(content, initiatives)

    # 2. Intentar formato estándar de 5 columnas (sin cruzar saltos de línea)
    pattern_5 = re.compile(
        r"\|\s*(\d+)\s*\|\s*\*\*([^*]+)\*\*\s*\|\s*([^|\r\n]+)\|\s*([^|\r\n]+)\|\s*([^|\r\n]+)\|"
    )
    matches_5 = pattern_5.findall(content)
    if matches_5:
        # Extraer fecha de sincronización del header si existe
        default_date = datetime.now().strftime("%Y-%m-%d")
        date_header_match = re.search(r"revisión:\*\*\s*(\d{4}-\d{2}-\d{2})", content)
        if date_header_match:
            default_date = date_header_match.group(1)

        for num, name, trend, priority, status in matches_5:
            initiatives.append({
                "number": num.strip(),
                "title": name.strip(),
                "trend": trend.strip(),
                "priority": _extract_priority(priority),
                "start_date": "2026-08-17",
                "due_date": default_date,
                "release": default_release,
                "status": status.strip(),
                "description": ""
            })
        return _attach_details(content, initiatives)

    return []


def _attach_details(content, initiatives):
    """Extrae y asigna las descripciones detalladas (### 1. Nombre)."""
    detail_pattern = re.compile(
        r"###\s*(\d+)\.\s*([^\n]+)\n(.*?)(?=\n###|\n---|\Z)",
        re.DOTALL
    )
    details = {num.strip(): desc.strip() for num, _, desc in detail_pattern.findall(content)}
    for init in initiatives:
        init["description"] = details.get(init["number"], "")
    return initiatives


def _parse_format_debt(content):
    """Formato deuda técnica (DT-XX / ID alfanumérico)."""
    initiatives = []
    default_release = _get_default_release()
    table_pattern = re.compile(
        r"\|\s*([A-Z]{1,6}-\d+)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|([^|]*?)\|?"
    )
    for match in table_pattern.finditer(content):
        item_id = match.group(1).strip()
        title = match.group(2).strip()
        col3 = match.group(3).strip()
        if re.match(r"^[-:]+$", title) or title.lower() in ("área", "area", "iniciativa", "título", "titulo"):
            continue
        initiatives.append({
            "number": item_id,
            "title": title,
            "trend": col3,
            "priority": _extract_priority(col3),
            "start_date": "2026-08-17",
            "due_date": datetime.now().strftime("%Y-%m-%d"),
            "release": default_release,
            "status": "⏳ Planificado",
            "description": ""
        })

    detail_pattern = re.compile(
        r"##\s+([A-Z]{1,6}-\d+)\s*[—\-–:]\s*([^\n]+)\n(.*?)(?=\n##\s+[A-Z]{1,6}-\d+|\n---|\Z)",
        re.DOTALL
    )
    details = {num.strip(): desc.strip() for num, _, desc in detail_pattern.findall(content)}
    for init in initiatives:
        init["description"] = details.get(init["number"], "")

    return initiatives


_NUM_HDR = {"#", "id", "n°", "nº", "no", "no.", "num", "número", "numero", "nro"}
_NAME_HDR = ("iniciativa", "nombre", "título", "titulo", "name", "initiative",
             "epic", "feature", "item", "objetivo", "tarea", "entregable")
_DONE_WORDS = ("✅", "done", "completed", "hecho", "terminad", "finalizad", "listo", "completo")


def _cell(text):
    return re.sub(r"[*`_]", "", text).strip()


def _find_col(headers, keys, skip=()):
    # Por clave en orden de prioridad y como palabra completa ("etapa" no es "eta").
    for k in keys:
        pat = re.compile(rf"(?<!\w){re.escape(k)}(?!\w)")
        for i, h in enumerate(headers):
            if pat.search(h) and not any(x in h for x in skip):
                return i
    return None


def _parse_format_generic(content):
    """Fallback: cualquier tabla markdown cuyo encabezado tenga una columna de nombre.
    Columnas por nombre (no por posición); nombre sin negrita y número opcional."""
    initiatives = []
    lines = content.splitlines()
    default_release = _get_default_release()
    i = 0
    while i < len(lines) - 1:
        head, sep = lines[i].strip(), lines[i + 1].strip()
        if not (head.startswith("|") and sep.startswith("|")
                and re.fullmatch(r"\|[\s:|-]+\|?", sep) and "-" in sep):
            i += 1
            continue
        headers = [_cell(c).lower() for c in head.strip("|").split("|")]
        name_i = _find_col(headers, _NAME_HDR)
        num_i = next((k for k, h in enumerate(headers) if h in _NUM_HDR), None)
        i += 2
        rows = []
        while i < len(lines) and lines[i].strip().startswith("|"):
            rows.append([_cell(c) for c in lines[i].strip().strip("|").split("|")])
            i += 1
        if name_i is None:
            continue
        cols = {
            "trend": _find_col(headers, ("tendencia", "trend", "área", "area", "categoría", "categoria")),
            "priority": _find_col(headers, ("prioridad", "priority", "prio")),
            "status": _find_col(headers, ("estado", "status", "progreso")),
            "start": _find_col(headers, ("inicio", "start")),
            "due": _find_col(headers, ("fecha fin", "fin", "due", "target", "eta", "fecha"), skip=("inicio", "start")),
            "release": _find_col(headers, ("release", "versión", "version")),
        }
        def get(row, key):
            idx = cols[key]
            return row[idx] if idx is not None and idx < len(row) else ""
        for row in rows:
            if name_i >= len(row) or not row[name_i]:
                continue
            number = row[num_i] if num_i is not None and num_i < len(row) and row[num_i] else ""
            status = get(row, "status") or "⏳ Planificado"
            if "completado" not in status.lower() and any(w in status.lower() for w in _DONE_WORDS):
                status = f"✅ Completado ({status})"
            initiatives.append({
                "number": number or str(len(initiatives) + 1),
                "title": row[name_i],
                "trend": get(row, "trend") or "N/D",
                "priority": _extract_priority(get(row, "priority")) or "Media",
                "start_date": _clean_date(get(row, "start")),
                "due_date": _clean_date(get(row, "due")),
                "release": _clean_release(get(row, "release")) or default_release,
                "status": status,
                "description": "",
            })
    return _attach_details(content, initiatives) if initiatives else []


def parse_roadmap(roadmap_path):
    """Parsea el archivo ROADMAP.md extrayendo las iniciativas."""
    if not os.path.exists(roadmap_path):
        print(f"❌ Error: Archivo {roadmap_path} no encontrado.")
        sys.exit(1)

    with open(roadmap_path, "r", encoding="utf-8") as f:
        content = f.read()

    initiatives = _parse_format_standard(content)
    if initiatives:
        print(f"📋 Formato detectado: Estándar. Iniciativas encontradas: {len(initiatives)}")
        return initiatives

    initiatives = _parse_format_debt(content)
    if initiatives:
        print(f"📋 Formato detectado: Deuda Técnica. Ítems encontrados: {len(initiatives)}")
        return initiatives

    initiatives = _parse_format_generic(content)
    if initiatives:
        print(f"📋 Formato detectado: Tabla genérica. Iniciativas encontradas: {len(initiatives)}")
        return initiatives

    print("⚠️ No se encontraron iniciativas en el ROADMAP.md. Verifica el formato de la tabla.")
    return []


def make_github_request(url, token, method="GET", data=None):
    """Realiza peticiones HTTP a la API REST de GitHub."""
    headers = {
        "User-Agent": "GitHub-Roadmap-Sync/1.0",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "Content-Type": "application/json",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    req_data = json.dumps(data).encode("utf-8") if data is not None else None
    req = urllib.request.Request(url, data=req_data, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req) as response:
            res_body = response.read().decode("utf-8")
            return json.loads(res_body) if res_body else {}
    except urllib.error.HTTPError as e:
        error_msg = e.read().decode("utf-8")
        print(f"⚠️ Error HTTP {e.code} en {method} {url}: {error_msg}")
        return None
    except Exception as e:
        print(f"⚠️ Error en petición: {e}")
        return None


def get_all_pages(url, token, max_pages=20):
    """Todas las páginas de un listado (per_page=100); sin esto, lo que pase del elemento 100 se duplicaría."""
    items = []
    sep = "&" if "?" in url else "?"
    for page in range(1, max_pages + 1):
        chunk = make_github_request(f"{url}{sep}page={page}", token)
        if not isinstance(chunk, list):
            return items if page > 1 else None
        items.extend(chunk)
        if len(chunk) < 100:
            break
    return items


def sync_to_github(initiatives, repo, token, dry_run=False, api_url="https://api.github.com", server_url="https://github.com"):
    """
    Sincroniza las iniciativas con GitHub creando, actualizando y cerrando
    los Milestones e Issues vinculados con fechas y Release oficial.
    """
    api_base = f"{api_url.rstrip('/')}/repos/{repo}"

    print(f"\n🚀 Iniciando sincronización hacia GitHub ({repo})")
    print(f"📋 Total de iniciativas encontradas en ROADMAP.md: {len(initiatives)}")
    print(f"⚙️ Modo Dry-Run: {'ACTIVADO (No se aplicarán cambios)' if dry_run else 'DESACTIVADO (Escribiendo en GitHub)'}\n")

    existing_milestones = []
    existing_issues = []
    if not dry_run:
        res_ms = get_all_pages(f"{api_base}/milestones?state=all&per_page=100", token)
        if isinstance(res_ms, list):
            existing_milestones = res_ms
            print(f"ℹ️ Milestones existentes en GitHub: {len(existing_milestones)}")
        res_iss = get_all_pages(f"{api_base}/issues?state=all&per_page=100", token)
        if isinstance(res_iss, list):
            # la API de issues también devuelve Pull Requests
            existing_issues = [i for i in res_iss if "pull_request" not in i]
            print(f"ℹ️ Issues existentes en GitHub: {len(existing_issues)}")

    milestones_by_title = {m["title"]: m for m in existing_milestones}
    issues_by_title = {i["title"]: i for i in existing_issues}

    for item in initiatives:
        milestone_title = f"#{item['number']}: {item['title']}"
        issue_title = f"Iniciativa #{item['number']}: {item['title']}"
        is_completed = "completado" in item["status"].lower() or "cerrado" in item["status"].lower()
        state = "closed" if is_completed else "open"
        labels = ["Roadmap", "DevSecOps", f"Prioridad: {item['priority']}"]

        start_date = item.get("start_date") or "2026-08-17"
        due_date = item.get("due_date") or datetime.now().strftime("%Y-%m-%d")
        release_tag = item.get("release") or _get_default_release()
        due_on = f"{due_date}T23:59:59Z"

        desc_lines = [
            f"## 🗺️ Iniciativa #{item['number']}: {item['title']}",
            "",
            f"- **Tendencia Tecnológica:** {item['trend']}",
            f"- **Prioridad:** `{item['priority']}`",
            f"- **Fecha de Inicio:** `{start_date}`",
            f"- **Fecha de Cierre (Due Date):** `{due_date}`",
            f"- **Release Oficial:** [`{release_tag}`]({server_url}/{repo}/releases/tag/{release_tag})",
            f"- **Estado en Roadmap:** `{item['status']}`",
            "",
            "---",
            "### 🚀 Detalle de Implementación:",
            item["description"] if item["description"] else "_Sin descripción adicional en ROADMAP.md_",
            "",
            "---",
            "_Sincronizado automáticamente desde ROADMAP.md por el pipeline DevSecOps._",
        ]
        full_description = "\n".join(desc_lines)

        print(f"🔹 Procesando #{item['number']}: [{item['title']}] | Inicio: {start_date} | Fin: {due_date} | Release: {release_tag} | Estado: {item['status']}")

        if dry_run:
            print(f"   [DRY-RUN] Milestone: Simulación crear/actualizar '{milestone_title}' (state: {state})")
            print(f"   [DRY-RUN] Issue: Simulación crear/actualizar '{issue_title}' (state: {state})")
            continue

        # 1. Milestone
        milestone_number = None
        payload_ms = {"description": full_description, "due_on": due_on, "state": state}
        if milestone_title in milestones_by_title:
            milestone_number = milestones_by_title[milestone_title]["number"]
            if make_github_request(f"{api_base}/milestones/{milestone_number}", token, method="PATCH", data=payload_ms):
                print(f"   ✅ Milestone actualizado y ajustado a '{state}' (#{milestone_number})")
        else:
            res = make_github_request(f"{api_base}/milestones", token, method="POST", data={"title": milestone_title, **payload_ms})
            if res and "number" in res:
                milestone_number = res["number"]
                print(f"   ✨ Milestone creado con éxito (#{milestone_number})")

        # 2. Issue asociado al Milestone
        payload_issue = {"body": full_description, "labels": labels, "state": state}
        if milestone_number:
            payload_issue["milestone"] = milestone_number
        if issue_title in issues_by_title:
            number = issues_by_title[issue_title]["number"]
            if make_github_request(f"{api_base}/issues/{number}", token, method="PATCH", data=payload_issue):
                print(f"   ✅ Issue actualizado y ajustado a '{state}' (#{number})")
        else:
            res_iss = make_github_request(f"{api_base}/issues", token, method="POST", data={"title": issue_title, **payload_issue})
            if res_iss and "number" in res_iss:
                print(f"   ✨ Issue creado y vinculado (#{res_iss['number']})")


def main():
    parser = argparse.ArgumentParser(description="Sincronizar ROADMAP.md con Milestones e Issues de GitHub.")
    parser.add_argument("--roadmap", default="ROADMAP.md", help="Ruta al archivo ROADMAP.md")
    parser.add_argument("--dry-run", action="store_true", help="Ejecutar en modo simulación sin modificar GitHub")
    parser.add_argument("--repo", default=os.getenv("GITHUB_REPOSITORY"), help="Repositorio owner/name")
    parser.add_argument("--api-url", default=os.getenv("GITHUB_API_URL", "https://api.github.com"), help="URL base de la API de GitHub")
    parser.add_argument("--token", default=os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN"), help="Token de autenticación de GitHub")

    args = parser.parse_args()

    initiatives = parse_roadmap(args.roadmap)

    if not args.dry_run and (not args.repo or not args.token):
        print("⚠️ Advertencia: No se detectaron 'GITHUB_REPOSITORY' ni token de acceso ('GH_TOKEN' / 'GITHUB_TOKEN').")
        print("Activando automáticamente modo --dry-run para validación local.")
        args.dry_run = True

    sync_to_github(
        initiatives=initiatives,
        repo=args.repo or "LOCAL_TEST",
        token=args.token,
        dry_run=args.dry_run,
        api_url=args.api_url,
        server_url=os.getenv("GITHUB_SERVER_URL", "https://github.com"),
    )


if __name__ == "__main__":
    main()
