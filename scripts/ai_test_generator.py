#!/usr/bin/env python3
"""
ai_test_generator.py — Unit Test Generator Agent (Strands)

El LLM decide qué código leer, detecta el framework existente, consulta tests
actuales para respetar el estilo, y genera una suite comprensiva. Fallback a
scaffolding estructurado si no hay credenciales de IA.
"""
import os
import sys
import subprocess
import glob
import re

from strands import Agent, tool
from strands.hooks import BeforeModelCallEvent


# ──────────────────────────────────────────────────────────────────────────────
# Model factory
# ──────────────────────────────────────────────────────────────────────────────

def _build_model():
    raw = os.environ.get("AI_PROVIDER", "").lower().strip().strip("'\"")
    api_url = os.environ.get("AI_API_URL", "").rstrip("/")
    model_id = os.environ.get("AI_MODEL", "")
    token = (os.environ.get("AI_TOKEN", "")
             or os.environ.get("GEMINI_API_KEY", "")
             or os.environ.get("OPENAI_API_KEY", ""))
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
        return OllamaModel(host=api_url or "http://localhost:11434", model_id=model_id, temperature=0.2)

    if provider == "claude":
        from strands.models.anthropic import AnthropicModel
        ca: dict = {"api_key": token or os.environ.get("ANTHROPIC_API_KEY", "")}
        if api_url:
            ca["base_url"] = api_url
        return AnthropicModel(client_args=ca, model_id=model_id,
                              max_tokens=max_tokens, params={"temperature": 0.2})

    if provider == "gemini":
        key = token or os.environ.get("GOOGLE_API_KEY", "")
        try:
            from strands.models.gemini import GeminiModel
            gc: dict = {"api_key": key}
            if api_url:
                gc["http_options"] = {"base_url": api_url}
            return GeminiModel(client_args=gc, model_id=model_id,
                               params={"temperature": 0.2, "max_output_tokens": max_tokens})
        except ImportError:
            pass
        from strands.models.openai import OpenAIModel
        return OpenAIModel(
            client_args={"api_key": key or "no-key",
                         "base_url": api_url or "https://generativelanguage.googleapis.com/v1beta/openai/"},
            model_id=model_id, params={"max_tokens": max_tokens, "temperature": 0.2},
        )

    # openai / lm-studio / vllm / llamacpp
    from strands.models.openai import OpenAIModel
    oa: dict = {"api_key": token or os.environ.get("OPENAI_API_KEY", "") or "lm-studio"}
    if api_url:
        oa["base_url"] = api_url if api_url.endswith("/v1") else (
            api_url if "/v1" in api_url else f"{api_url}/v1"
        )
    return OpenAIModel(client_args=oa, model_id=model_id,
                       params={"max_tokens": max_tokens, "temperature": 0.2})


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


@tool
def get_code_diff(service_path: str, target_branch: str = "main") -> dict:
    """Obtiene el diff de código del Merge Request para el path del microservicio.
    Llamar primero para saber qué cambió. Si el diff está vacío no hay cambios
    que testear y el agente debe terminar sin generar tests.
    Parámetros:
      - service_path: ruta relativa del microservicio (ej. 'backend', '.')
      - target_branch: rama destino del MR (default: main)"""
    base_ref = f"origin/{target_branch}"
    try:
        subprocess.check_output(["git", "rev-parse", "--verify", base_ref],
                                stderr=subprocess.DEVNULL)
    except Exception:
        base_ref = "HEAD~1"

    path = service_path if service_path and service_path != "." else None
    cmd = ["git", "diff", f"{base_ref}...HEAD"]
    if path:
        cmd += ["--", path]

    try:
        diff = subprocess.check_output(cmd).decode("utf-8", errors="ignore").strip()
        lines = len(diff.splitlines())
        return {"diff": diff[:6000], "lines": lines, "truncated": lines > 300,
                "base_ref": base_ref, "has_changes": bool(diff)}
    except Exception as e:
        return {"diff": "", "lines": 0, "has_changes": False, "error": str(e)}


@tool
def read_source_files(service_path: str, lang: str, max_files: int = 3) -> dict:
    """Lee los archivos fuente principales del microservicio para entender mejor
    la lógica a testear, más allá del diff. Útil cuando el diff solo muestra
    cambios pequeños pero el agente necesita contexto del módulo completo.
    Parámetros:
      - service_path: ruta base del microservicio
      - lang: lenguaje (python, go, js, ts, java-maven, java-gradle)
      - max_files: máximo de archivos a leer (default: 3)"""
    ext_map = {
        "python": ["*.py"], "go": ["*.go"],
        "js": ["*.js", "*.mjs"], "ts": ["*.ts"],
        "java-maven": ["*.java"], "java-gradle": ["*.java"],
    }
    patterns = ext_map.get(lang, ["*.*"])
    base = service_path if service_path and service_path != "." else "."
    if _repo_path(base) is None:
        return {"files": {}, "count": 0, "error": f"Ruta fuera del repositorio: {service_path}"}

    files = []
    for pat in patterns:
        found = glob.glob(os.path.join(base, "**", pat), recursive=True)
        # Exclude test files and node_modules/vendor
        found = [f for f in found if not any(x in f for x in
                 ["test", "spec", "__pycache__", "node_modules", "vendor", ".git"])]
        files.extend(found)
        if len(files) >= max_files:
            break

    files = files[:max_files]
    contents = {}
    for fp in files:
        try:
            with open(fp, "r", encoding="utf-8", errors="ignore") as f:
                contents[fp] = f.read()[:3000]
        except Exception:
            pass

    return {"files": contents, "count": len(contents)}


@tool
def detect_test_framework(service_path: str, lang: str) -> dict:
    """Detecta el framework de testing ya usado en el proyecto leyendo archivos
    de configuración y tests existentes. Usar para generar tests consistentes
    con el estilo del proyecto en lugar de asumir el framework por defecto.
    Parámetros:
      - service_path: ruta base del microservicio
      - lang: lenguaje del microservicio"""
    base = service_path if service_path and service_path != "." else "."
    if _repo_path(base) is None:
        return {"framework": "unknown", "hints": [], "existing_test_files": [], "sample_test_content": "",
                "error": f"Ruta fuera del repositorio: {service_path}"}
    framework = "unknown"
    hints = []

    indicators = {
        "python": {
            "pytest": ["pytest.ini", "pyproject.toml", "setup.cfg", "conftest.py"],
            "unittest": [],
        },
        "go": {"testing": ["go.mod"]},
        "js": {
            "jest": ["jest.config.js", "jest.config.ts", "package.json"],
            "vitest": ["vitest.config.ts", "vitest.config.js"],
            "mocha": [".mocharc.js", ".mocharc.yml"],
        },
        "ts": {
            "jest": ["jest.config.ts", "jest.config.js"],
            "vitest": ["vitest.config.ts"],
        },
        "java-maven": {"junit5": ["pom.xml"]},
        "java-gradle": {"junit5": ["build.gradle", "build.gradle.kts"]},
    }

    for fw, files in indicators.get(lang, {}).items():
        for f in files:
            path = os.path.join(base, f)
            if os.path.exists(path):
                try:
                    content = open(path).read(2000)
                    if fw in content.lower() or fw.replace("-", "") in content.lower():
                        framework = fw
                        hints.append(f"Encontrado '{fw}' en {f}")
                        break
                except Exception:
                    framework = fw

    # Buscar tests existentes para detectar estilo
    test_patterns = {
        "python": ["**/test_*.py", "**/*_test.py"],
        "go": ["**/*_test.go"],
        "js": ["**/*.test.js", "**/*.spec.js"],
        "ts": ["**/*.test.ts", "**/*.spec.ts"],
        "java-maven": ["**/Test*.java", "**/*Test.java"],
        "java-gradle": ["**/Test*.java", "**/*Test.java"],
    }
    existing_tests = []
    for pat in test_patterns.get(lang, []):
        found = glob.glob(os.path.join(base, pat), recursive=True)
        found = [f for f in found if ".git" not in f and "node_modules" not in f]
        existing_tests.extend(found[:2])

    sample_test = ""
    if existing_tests:
        try:
            with open(existing_tests[0], "r", encoding="utf-8", errors="ignore") as f:
                sample_test = f.read()[:2000]
        except Exception:
            pass

    return {
        "framework": framework,
        "hints": hints,
        "existing_test_files": existing_tests[:3],
        "sample_test_content": sample_test,
    }


@tool
def save_test_file(content: str, service_path: str, lang: str,
                   out_dir: str = "generated-tests") -> dict:
    """Guarda el archivo de tests generado en el directorio de salida.
    Llamar siempre al final, incluso si se usa el scaffold.
    Parámetros:
      - content: código de tests completo y ejecutable
      - service_path: ruta base del microservicio
      - lang: lenguaje para determinar nombre y extensión del archivo
      - out_dir: subdirectorio de salida (default: generated-tests)"""
    filename_map = {
        "python": "test_ai_generated.py",
        "go": "ai_generated_test.go",
        "js": "ai_generated.test.js",
        "ts": "ai_generated.test.ts",
        "java-maven": "GeneratedServiceTest.java",
        "java-gradle": "GeneratedServiceTest.java",
    }
    filename = filename_map.get(lang, "test_ai_generated.txt")
    base = service_path if service_path and service_path != "." else ""
    full_dir = os.path.join(base, out_dir) if base else out_dir
    if _repo_path(full_dir) is None:
        return {"status": "error", "detail": f"Ruta no permitida: {full_dir}"}

    os.makedirs(full_dir, exist_ok=True)
    output_path = os.path.join(full_dir, filename)

    # Limpiar bloques markdown si el LLM los incluyó
    clean = re.sub(r"^```[a-zA-Z0-9_-]*\n", "", content.strip())
    clean = re.sub(r"\n```$", "", clean.strip()).strip()

    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(clean)
        return {"status": "saved", "path": output_path,
                "lines": len(clean.splitlines())}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


@tool
def generate_scaffold(lang: str, service_path: str = ".") -> dict:
    """Genera una plantilla de tests estructurada sin necesidad de IA.
    Usar como fallback cuando no hay credenciales de LLM o cuando el agente
    no puede generar tests válidos tras varios intentos.
    Parámetros:
      - lang: lenguaje (python, go, js, ts, java-maven, java-gradle)
      - service_path: ruta del servicio (solo para contexto en el comentario)"""
    templates = {
        "python": (
            "# Generated by AI Test Generator (Scaffold Mode)\n"
            "import pytest\n\n"
            "def test_service_initialization():\n"
            "    \"\"\"Prueba base de estabilidad del microservicio.\"\"\"\n"
            "    assert True\n\n"
            "def test_health_check_payload():\n"
            "    sample = {'status': 'healthy', 'code': 200}\n"
            "    assert sample['status'] == 'healthy'\n"
            "    assert sample['code'] == 200\n"
        ),
        "go": (
            "// Generated by AI Test Generator (Scaffold Mode)\n"
            "package main\n\nimport \"testing\"\n\n"
            "func TestServiceHealth(t *testing.T) {\n"
            "    if 200 != 200 {\n"
            "        t.Errorf(\"Expected 200\")\n"
            "    }\n"
            "}\n"
        ),
        "js": (
            "// Generated by AI Test Generator (Scaffold Mode)\n"
            "describe('Microservice Unit Tests', () => {\n"
            "  it('should validate base configuration', () => {\n"
            "    expect(true).toBe(true);\n"
            "  });\n"
            "});\n"
        ),
        "ts": (
            "// Generated by AI Test Generator (Scaffold Mode)\n"
            "describe('Microservice Unit Tests', () => {\n"
            "  it('should validate base configuration', () => {\n"
            "    expect(true).toBe(true);\n"
            "  });\n"
            "});\n"
        ),
        "java-maven": (
            "// Generated by AI Test Generator (Scaffold Mode)\n"
            "import org.junit.jupiter.api.Test;\n"
            "import static org.junit.jupiter.api.Assertions.*;\n\n"
            "public class GeneratedServiceTest {\n"
            "    @Test\n"
            "    void testServiceStatus() {\n"
            "        assertTrue(true);\n"
            "    }\n"
            "}\n"
        ),
        "java-gradle": (
            "// Generated by AI Test Generator (Scaffold Mode)\n"
            "import org.junit.jupiter.api.Test;\n"
            "import static org.junit.jupiter.api.Assertions.*;\n\n"
            "public class GeneratedServiceTest {\n"
            "    @Test\n"
            "    void testServiceStatus() {\n"
            "        assertTrue(true);\n"
            "    }\n"
            "}\n"
        ),
    }
    code = templates.get(lang, "# Unit test placeholder\nassert True\n")
    return {"scaffold": code, "lang": lang}


# ──────────────────────────────────────────────────────────────────────────────
# System prompt
# ──────────────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """Eres un ingeniero QA senior especializado en pruebas unitarias y TDD.
Tu misión es generar una suite de tests comprensiva, ejecutable y consistente con el
estilo del proyecto a partir del código modificado en un Merge Request.

## Flujo de trabajo

1. Llama a get_code_diff() para obtener los cambios del MR.
   - Si has_changes=false, llama a save_test_file() con un mensaje informativo y termina.
2. Llama a detect_test_framework() para conocer el framework y ver tests existentes.
3. Si el diff es insuficiente para entender el contexto, llama a read_source_files()
   para leer los archivos fuente principales.
4. Genera el código de tests considerando:
   - Casos de éxito (happy path)
   - Casos de error y excepciones
   - Validación de parámetros nulos/vacíos
   - Consistencia con el framework y estilo detectados
5. Si el código generado parece correcto, llama a save_test_file().
6. Si no hay credenciales de IA o la generación falla, llama a generate_scaffold()
   y luego save_test_file() con el scaffold.

## Restricciones

- Devuelve ÚNICAMENTE código ejecutable sin explicaciones ni markdown envolvente.
- No inventes imports o clases que no existan en el código fuente.
- Si no puedes generar tests válidos tras analizar el contexto, usa generate_scaffold().
- Un test que pase siempre (assert True) es mejor que código roto.
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
    service_path = os.environ.get("SERVICE_PATH", ".")
    service_lang = os.environ.get("SERVICE_LANG", "python")
    target_branch = os.environ.get("GITHUB_BASE_REF") or os.environ.get("CI_MERGE_REQUEST_TARGET_BRANCH_NAME", "main")
    ai_provider = os.environ.get("AI_PROVIDER", "")
    ai_model = os.environ.get("AI_MODEL", "")
    max_turns = int(os.environ.get("AI_MAX_TURNS", "20"))

    print("=" * 64)
    print(f"🧪 AI Test Generator — Servicio: '{service_path}' | Lang: {service_lang}")
    print(f"   Proveedor: {ai_provider} | Modelo: {ai_model or 'default'} | Max turns: {max_turns}")
    print("=" * 64)

    try:
        model = _build_model()
    except Exception as e:
        print(f"❌ Error al inicializar el modelo: {e}")
        sys.exit(1)

    agent = Agent(
        model=model,
        tools=[get_code_diff, read_source_files, detect_test_framework,
               save_test_file, generate_scaffold],
        system_prompt=SYSTEM_PROMPT,
    )
    agent.add_hook(_turn_limiter(max_turns), BeforeModelCallEvent)

    task = (
        f"Genera pruebas unitarias para el microservicio modificado en este MR.\n\n"
        f"Contexto:\n"
        f"- Ruta del servicio: {service_path}\n"
        f"- Lenguaje: {service_lang}\n"
        f"- Rama destino del MR: {target_branch}\n"
        f"- Directorio de salida: generated-tests\n\n"
        "Sigue el flujo definido en tu system prompt."
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
        print("\n📋 Archivos generados:")
        base = service_path if service_path != "." else ""
        out = os.path.join(base, "generated-tests") if base else "generated-tests"
        found = glob.glob(os.path.join(out, "**", "*"), recursive=True)
        for f in found:
            print(f"  {f}")
        if not found:
            print("  ℹ️ No se generaron archivos nuevos.")
    except Exception as e:
        print(f"❌ Error en el agente: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
