#!/usr/bin/env python3
"""
ai_release_notes.py — Release Notes Agent (Strands)

El LLM decide qué commits analizar, si necesita mensajes completos, si leer el
CHANGELOG existente, y cómo estructurar las notas. Guarda RELEASE_NOTES.md.
"""
import os
import re
import sys
import subprocess

from strands import Agent, tool
from strands.hooks import BeforeModelCallEvent


# ──────────────────────────────────────────────────────────────────────────────
# Model factory (misma lógica que ai_remediation.py)
# ──────────────────────────────────────────────────────────────────────────────

def _build_model():
    raw = os.environ.get("AI_PROVIDER", "").lower().strip().strip("'\"")
    api_url = os.environ.get("AI_API_URL", "").rstrip("/")
    model_id = os.environ.get("AI_MODEL", "")
    token = os.environ.get("AI_TOKEN", "") or os.environ.get("GEMINI_API_KEY", "") or os.environ.get("OPENAI_API_KEY", "")
    max_tokens = int(os.environ.get("AI_MAX_TOKENS", "4096"))

    if raw in ("ollama", "ollama-service", "ollama_service"):
        provider = "ollama"
    elif raw in ("claude", "anthropic", "claude-3", "claude-3-5", "claude3"):
        provider = "claude"
    elif raw in ("gemini", "google", "google-gemini"):
        provider = "gemini"
    elif raw:
        provider = "openai"
    else:
        provider = ""

    missing = []
    if not raw:
        missing.append("AI_PROVIDER")
    if not model_id:
        missing.append("AI_MODEL")
    if provider == "ollama" and not api_url:
        missing.append("AI_API_URL")
    if provider == "claude" and not (token or os.environ.get("ANTHROPIC_API_KEY", "")):
        missing.append("AI_TOKEN")
    if provider == "gemini" and not token and not api_url:
        missing.append("AI_TOKEN")
    if provider == "openai" and not token and not api_url:
        missing.append("AI_TOKEN o AI_API_URL")
    if missing:
        print(f"❌ Variables requeridas no configuradas: {', '.join(missing)}")
        print(f"   Proveedor detectado: '{provider or raw or '(no configurado)'}'")
        print("   Defínelas como inputs/secrets del workflow o variables/secrets del repositorio u organización.")
        print("   Valores válidos para AI_PROVIDER: ollama | gemini | claude | openai | lm-studio | ls-studio")
        sys.exit(1)

    if provider == "ollama":
        from strands.models.ollama import OllamaModel
        return OllamaModel(host=api_url, model_id=model_id, temperature=0.2)

    if provider == "claude":
        from strands.models.anthropic import AnthropicModel
        return AnthropicModel(
            client_args={"api_key": token or os.environ.get("ANTHROPIC_API_KEY", "")},
            model_id=model_id,
            max_tokens=max_tokens,
            params={"temperature": 0.2},
        )

    if provider == "gemini":
        from strands.models.openai import OpenAIModel
        return OpenAIModel(
            client_args={
                "api_key": token or os.environ.get("GOOGLE_API_KEY", "") or "no-key",
                "base_url": api_url or "https://generativelanguage.googleapis.com/v1beta/openai/",
            },
            model_id=model_id,
            params={"max_tokens": max_tokens, "temperature": 0.2},
        )

    # openai / lm-studio / vllm / llamacpp / cualquier compatible OpenAI
    from strands.models.openai import OpenAIModel
    client_args: dict = {"api_key": token or "lm-studio"}
    if api_url:
        client_args["base_url"] = api_url if "/v1" in api_url else f"{api_url}/v1"
    return OpenAIModel(
        client_args=client_args,
        model_id=model_id,
        params={"max_tokens": max_tokens, "temperature": 0.2},
    )


# ──────────────────────────────────────────────────────────────────────────────
# Tools
# ──────────────────────────────────────────────────────────────────────────────

# Los argumentos de las herramientas los decide el LLM: no son confiables. Todo acceso a ficheros se confina al
# repositorio (GITHUB_WORKSPACE, CI_PROJECT_DIR o el directorio actual), sin .git y sin ficheros de infraestructura CI al escribir.
def _repo_path(path, write=False):
    """Ruta real dentro del repo, o None si sale de el (../, absoluta, symlink) o toca .git / infra CI al escribir."""
    base = os.path.realpath(os.environ.get("GITHUB_WORKSPACE") or os.environ.get("CI_PROJECT_DIR") or os.getcwd())
    real = os.path.realpath(os.path.join(base, str(path or ".")))
    parts = os.path.relpath(real, base).split(os.sep)
    if parts[0] == ".." or ".git" in parts:
        return None
    name = parts[-1].lower()
    if write and (name.endswith((".gitlab-ci.yml", ".gitlab-ci.yaml")) or ".github" in parts[:-1] or name.startswith("dockerfile") or name.endswith(".tf")):
        return None
    return real


def _safe_ref(ref):
    """Referencia git valida: sin espacios y sin '-' inicial (evita que git la lea como una opcion, p. ej. --output=)."""
    return bool(ref) and not ref.startswith("-") and re.fullmatch(r"[A-Za-z0-9._/@^~+:{}-]+", ref) is not None


@tool
def get_previous_tag(current_tag: str) -> dict:
    """Busca el tag anterior al tag actual en el historial de git.
    Usar para determinar el rango de commits a incluir en las release notes.
    Parámetros:
      - current_tag: tag actual (ej. 'v2026.10.03')
    Retorna el tag anterior o None si no existe."""
    if not _safe_ref(current_tag):
        return {"found": False, "previous_tag": None}
    try:
        prev = subprocess.check_output(
            ["git", "describe", "--tags", "--abbrev=0", f"{current_tag}^"],
            stderr=subprocess.DEVNULL,
        ).decode().strip()
        return {"found": True, "previous_tag": prev}
    except Exception:
        return {"found": False, "previous_tag": None}


@tool
def get_commit_log(from_ref: str, to_ref: str, full_messages: bool = False) -> dict:
    """Obtiene el log de commits entre dos referencias git.
    Llamar primero con full_messages=False para ver los subjects.
    Si los mensajes son ambiguos o muy cortos, llamar de nuevo con full_messages=True
    para obtener el cuerpo completo de cada commit y entender mejor el cambio.
    Parámetros:
      - from_ref: referencia de inicio (tag anterior, SHA, rama)
      - to_ref: referencia de fin (tag actual, HEAD)
      - full_messages: False = solo subject; True = subject + body completo"""
    if not _safe_ref(to_ref) or (from_ref and not _safe_ref(from_ref)):
        return {"commits": "chore: release update", "count": 0, "error": "referencia git no valida"}
    if full_messages:
        fmt = "--pretty=format:--- COMMIT ---%n%h%n%s%n%b"
    else:
        fmt = "--pretty=format:%h %s"

    try:
        if from_ref and from_ref != to_ref:
            cmd = ["git", "log", f"{from_ref}..{to_ref}", fmt]
        else:
            cmd = ["git", "log", "-n", "50", fmt]

        output = subprocess.check_output(cmd, stderr=subprocess.DEVNULL).decode("utf-8").strip()
        commits = output if output else "chore: no commits found"
        count = len([l for l in output.splitlines() if l.startswith("---") or (not full_messages and l.strip())])
        return {"commits": commits, "count": count, "from": from_ref, "to": to_ref}
    except Exception as e:
        return {"commits": "chore: release update", "count": 0, "error": str(e)}


@tool
def read_changelog(tag: str = "") -> dict:
    """Lee el CHANGELOG.md del repositorio para obtener contexto adicional.
    Útil si los commits son poco descriptivos o para detectar breaking changes
    documentados manualmente. Opcionalmente filtra la sección de un tag específico.
    Parámetros:
      - tag: si se especifica, extrae solo la sección de ese tag; vacío = primeras 100 líneas"""
    changelog_path = "CHANGELOG.md"
    if not os.path.exists(changelog_path):
        return {"found": False, "content": ""}

    try:
        with open(changelog_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception as e:
        return {"found": False, "error": str(e)}

    if not tag:
        return {"found": True, "content": "".join(lines[:100])}

    # Extraer sección del tag específico
    tag_clean = tag.lstrip("v")
    in_section = False
    section_lines = []
    for line in lines:
        if re.match(rf"^## \[{re.escape(tag_clean)}\]|^## \[v?{re.escape(tag_clean)}\]", line):
            in_section = True
        elif in_section and line.startswith("## ["):
            break
        if in_section:
            section_lines.append(line)

    return {"found": True, "content": "".join(section_lines) if section_lines else "".join(lines[:80])}


@tool
def save_release_notes(content: str, output_file: str = "RELEASE_NOTES.md") -> dict:
    """Guarda las release notes generadas en un archivo Markdown.
    Llamar siempre como último paso, incluso si el contenido es mínimo.
    El archivo es consumido por el job create_release en init.yml para
    publicar la Release oficial en GitLab.
    Parámetros:
      - content: contenido Markdown completo de las release notes
      - output_file: nombre del archivo de salida (default: RELEASE_NOTES.md)"""
    real = _repo_path(output_file, write=True)
    if real is None or os.path.isdir(real):
        return {"status": "error", "detail": f"Ruta no permitida: {output_file}"}
    try:
        with open(real, "w", encoding="utf-8") as f:
            f.write(content)
        lines = len(content.splitlines())
        return {"status": "saved", "path": output_file, "lines": lines}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


# ──────────────────────────────────────────────────────────────────────────────
# System prompt
# ──────────────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """Eres un Release Manager experto en DevSecOps. Tu misión es generar
Release Notes profesionales, claras y ejecutivas en Markdown a partir del historial de commits.

## Flujo de trabajo

1. Llama a get_previous_tag() para encontrar el tag anterior al actual.
2. Llama a get_commit_log() con from=tag_anterior to=tag_actual.
3. Si los subjects de los commits son ambiguos o muy cortos, llama de nuevo
   con full_messages=True para leer el cuerpo completo.
4. Si el resultado sigue siendo poco descriptivo, llama a read_changelog()
   para obtener contexto adicional del CHANGELOG.md.
5. Redacta las Release Notes en Markdown con este formato:

```
# 🚀 Release Notes - <TAG>

> Breve descripción ejecutiva de la release en 1-2 frases.

### 🌟 Nuevas Funcionalidades
- ...

### 🐛 Correcciones de Errores
- ...

### 🛡️ Seguridad y Gobernanza
- ...

### 🔧 Mantenimiento y CI/CD
- ...

### ⚠️ Breaking Changes
- ... (solo si hay commits con ! o BREAKING CHANGE)
```

6. Omite secciones que no tengan contenido.
7. Llama a save_release_notes() con el Markdown generado.

## Guías de estilo

- Viñetas comprensibles para desarrolladores Y stakeholders no técnicos.
- Para commits `feat:` → Nuevas Funcionalidades.
- Para commits `fix:` → Correcciones.
- Para commits `sec:`, `security:`, CVE, audit → Seguridad.
- Para commits `chore:`, `ci:`, `build:`, `refactor:`, `docs:` → Mantenimiento.
- Commits con `!` o `BREAKING CHANGE` en el body → Breaking Changes.
- Responde SOLO con el Markdown final, sin bloques de código envolventes.
"""


# ──────────────────────────────────────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────────────────────────────────────

def _turn_limiter(max_turns: int):
    """Hook BeforeModelCallEvent: cancela la llamada al modelo tras max_turns turnos."""
    calls = 0

    def _hook(event):
        nonlocal calls
        calls += 1
        if calls > max_turns:
            event.cancel = f"AI_MAX_TURNS={max_turns} alcanzado; deteniendo agente."
    return _hook


def main():
    current_tag = os.environ.get("CI_COMMIT_TAG") or (os.environ.get("GITHUB_REF_NAME") if os.environ.get("GITHUB_REF_TYPE") == "tag" else None) or "HEAD"
    from_ref = os.environ.get("PREVIOUS_SHA") or os.environ.get("CI_COMMIT_BEFORE_SHA", "")
    output_file = os.environ.get("RELEASE_NOTES_OUTPUT", "RELEASE_NOTES.md")
    ai_provider = os.environ.get("AI_PROVIDER", "")
    ai_model = os.environ.get("AI_MODEL", "")
    max_turns = int(os.environ.get("AI_MAX_TURNS", "15"))

    print("=" * 64)
    print(f"🤖 Generando Release Notes para: {current_tag}")
    print(f"   Proveedor: {ai_provider} | Modelo: {ai_model or 'default'} | Max turns: {max_turns}")
    print("=" * 64)

    try:
        model = _build_model()
    except Exception as e:
        print(f"❌ Error al inicializar el modelo: {e}")
        sys.exit(1)

    agent = Agent(
        model=model,
        tools=[get_previous_tag, get_commit_log, read_changelog, save_release_notes],
        system_prompt=SYSTEM_PROMPT,
    )
    agent.add_hook(_turn_limiter(max_turns), BeforeModelCallEvent)

    task = (
        f"Genera las Release Notes para la versión **{current_tag}**.\n\n"
        f"Contexto:\n"
        f"- Tag actual: {current_tag}\n"
        f"- SHA anterior (hint para from_ref): {from_ref or 'no disponible'}\n"
        f"- Archivo de salida: {output_file}\n\n"
        "Sigue el flujo de trabajo definido en tu system prompt."
    )

    def _progress(**kwargs):
        if "data" in kwargs and kwargs["data"]:
            print(kwargs["data"], end="", flush=True)
        elif "current_tool_use" in kwargs:
            tool = kwargs["current_tool_use"]
            name = tool.get("name") if isinstance(tool, dict) else getattr(tool, "name", "?")
            print(f"\n  🔧 → {name}", flush=True)

    try:
        result = agent(task, callback_handler=_progress)
        print(f"\n✅ Agente finalizado.\n{result}")
        # Vista previa
        if os.path.exists(output_file):
            print("\n📋 Vista previa:")
            with open(output_file) as f:
                print("".join(f.readlines()[:25]))
    except Exception as e:
        print(f"❌ Error en el agente: {e}")
        # Fallback mínimo para no romper el pipeline
        try:
            with open(output_file, "w") as f:
                f.write(f"# 🚀 Release Notes - {current_tag}\n\n*Notas no disponibles.*\n")
        except Exception:
            pass
        sys.exit(1)


if __name__ == "__main__":
    main()
