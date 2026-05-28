# 🌟 Características y Extensión del Sistema

El Template de CI/CD está construido para ser modular. Esta guía explica cómo comprender la lógica de negocio técnica subyacente y cómo extenderla.

## 1. Módulo de Detección Dinámica de Lenguaje

El bloque central del orquestador es el paso `Detect language and prepare metadata`. Utiliza un script bash inyectado para identificar la tecnología base del repositorio interrogando archivos críticos en la raíz.

### Cómo agregar soporte para un nuevo lenguaje (Ej. Ruby)
Si en el futuro tu ecosistema requiere soporte nativo para proyectos Ruby, debes extender el condicional bash dentro de `docker-build_push_auto.yml` y `pull-request-validation.yml`:

```bash
# ... código existente ...
elif [ -f "pyproject.toml" ] || [ -f "requirements.txt" ]; then
  LANG="python"
# 🌟 Extensión agregada para Ruby:
elif [ -f "Gemfile" ]; then
  LANG="ruby"
fi
```
Una vez que el orquestador exporta `detected_lang=ruby`, debes dirigirte a `shared-lint-test.yml` y añadir un nuevo "step" o "job" que sólo se ejecute `if: inputs.DETECTED_LANG == 'ruby'`, configurando `setup-ruby` y los comandos de pruebas nativos (RSpec, Rubocop, etc).

## 2. Inyección de Job Summaries (Markdown Nativo)

Una de las características clave es la experiencia de desarrollador (DX) libre de fricción. En lugar de forzar al desarrollador a leer logs brutos, el sistema consolida los resultados usando la variable nativa de Actions `$GITHUB_STEP_SUMMARY`.

**Extensión de reportes:**
Si agregas un nuevo linter (ej. `golangci-lint`), puedes inyectar su reporte directo en la UI así:
```yaml
- name: Escribir Reporte Linter
  if: always()
  run: |
    echo "## 🧹 Reporte Linter Go" >> $GITHUB_STEP_SUMMARY
    echo '```text' >> $GITHUB_STEP_SUMMARY
    cat linter_output.txt >> $GITHUB_STEP_SUMMARY
    echo '```' >> $GITHUB_STEP_SUMMARY
```

## 3. Matriz de Múltiples Arquitecturas (Docker Buildx)

El sistema compila contenedores OCI compatibles tanto para plataformas clásicas (AMD64) como para procesadores ARM modernos (como AWS Graviton o Apple Silicon). 
La matriz se controla desde el parámetro `PLATFORMS` en la llamada del orquestador:
```yaml
with:
  PLATFORMS: 'linux/amd64,linux/arm64'
```
> [!WARNING]
> Si una dependencia estática dentro de tu código C/C++ no soporta compilación cruzada hacia ARM, puedes restringir temporalmente este valor a `'linux/amd64'` para evitar que el pipeline colapse, mientras refactorizas las librerías nativas.

## 4. Orquestación Segura: Fallbacks de Nombres

Debido a que GitHub Actions enmascara (redacta) variables marcadas como secretos entre distintos jobs (`***`), el sistema implementa un fallback inteligente para calcular correctamente la ruta y el namespace de Docker Hub usando el nombre de la organización de GitHub, asegurando que la ruta del contenedor sea determinista y evite errores de `invalid reference format`.

## 5. Fortificación y Linter Estricto de Dockerfiles (Hadolint)

El sistema incorpora de manera automática y recursiva el linter **Hadolint** para todos los Dockerfiles del proyecto:
- **Detección Eficiente:** Mediante un script bash condicional se valida la existencia de Dockerfiles. Si no se encuentran, se omite el linter de forma segura, reduciendo minutos innecesarios de ejecución.
- **Detección de Malas Prácticas:** Hadolint valida contra reglas estrictas de la comunidad (ej. no usar `latest`, no usar `sudo`, optimización de capas `RUN`).
- **Exportación en SARIF:** Los resultados se exportan nativamente en formato SARIF (`hadolint-report.sarif`), se convierten a JSON, se cargan como artefactos y son consolidados en el PDF ejecutivo bajo la categoría **`Dockerfile Linter (Hadolint)`**.

## 6. Auditorías Nativas de Dependencias del Lenguaje (SCA Nativo)

Trivy escanea estáticamente dependencias en archivos lock, pero las herramientas nativas oficiales de cada lenguaje ofrecen firmas dinámicas y específicas sobre exploits conocidos. Por ello, el pipeline realiza un escaneo de seguridad nativo según el lenguaje detectado en el proyecto:
- **Go:** Ejecuta `govulncheck -json ./...` utilizando la herramienta oficial de vulnerabilidades de Go, con soporte NDJSON (JSON delimitado por líneas) en nuestro parser.
- **Node.js/JavaScript:** Ejecuta `npm audit --json` para alertar sobre dependencias vulnerables en la cadena de paquetes npm.
- **Python:** Ejecuta `pip-audit --format json` para auditar el ecosistema de paquetes de PyPI.
- **Soft Fail Integrado:** Todas las herramientas SCA nativas se configuran con `continue-on-error: true` (Soft Fail). Esto garantiza que el reporte contenga las alertas detalladas pero **nunca interrumpa** la compilación de producción o los despliegues ágiles, empoderando a los ingenieros de desarrollo a remediarlas progresivamente sin fricción.
