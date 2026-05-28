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
