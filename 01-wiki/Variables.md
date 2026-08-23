# 🔑 Variables y Secretos de Configuración (GitHub Actions)

Este documento detalla los `inputs` y `secrets` disponibles en las plantillas DevSecOps de GitHub Actions.

---

## 📌 1. Variables Globales y de Orquestación (`inputs`)

| Input | Valor por Defecto | Tipo | Descripción |
| :--- | :---: | :---: | :--- |
| `SERVICES` | `""` | `string` | Lista opcional de carpetas de microservicios separadas por espacio. Si está vacía, se autodetectan. |
| `SERVICE_PATH` | `"."` | `string` | Directorio relativo del microservicio dentro del repositorio. |
| `SERVICE_NAME` | `""` | `string` | Nombre del microservicio utilizado para etiquetar imágenes y reportes. |
| `SERVICE_LANG` | `"unknown"` | `string` | Lenguaje del microservicio (`python`, `go`, `js`, `java-maven`, `java-gradle`). |
| `RUNNER_TAG` | `"ubuntu-latest"` | `string` | Etiqueta del runner de GitHub Actions donde ejecutar los jobs. |
| `GITOPS_TARGET_ENV`| `"PROD"` | `string` | Nombre del entorno destino para GitOps (`DEV`, `STG`, `PROD`). |
| `TARGET_ENVIRONMENT`| `"production"` | `string` | Nombre del Environment de GitHub (`development`, `staging`, `production`). |

---

## 🔐 2. Secretos de Configuración (`secrets`)

| Secreto | Requerido | Descripción |
| :--- | :---: | :--- |
| `GITHUB_TOKEN` | Sí (nativo) | Token de acceso de GitHub para autenticar en GHCR, crear releases y comentar PRs. |
| `GITOPS_DEPLOY_KEY` | Opcional | Clave SSH privada con permisos de escritura en el repositorio de GitOps. |
| `GITLAB_TOKEN` | Opcional | Token de GitLab si el repositorio GitOps se encuentra alojado en GitLab. |
| `DOCKERHUB_USERNAME` | Opcional | Usuario de Docker Hub para publicación secundaria. |
| `DOCKERHUB_TOKEN` | Opcional | Token de acceso de Docker Hub. |
| `SONAR_TOKEN` | Opcional | Token de autenticación para SonarQube / SonarCloud. |
| `SONAR_HOST_URL` | Opcional | URL del servidor de SonarQube. |
| `DEFECTDOJO_API_KEY`| Opcional | API Key para subir hallazgos a DefectDojo. |
| `DEFECTDOJO_URL` | Opcional | URL de la instancia de DefectDojo. |
| `INFRACOST_API_KEY` | Opcional | API Key para estimación de costos en Merge/Pull Requests. |
| `OPENAI_API_KEY` | Opcional | Clave para pruebas dinámicas de red-teaming de IA con PromptFoo. |
| `ANTHROPIC_API_KEY`| Opcional | Clave de Anthropic para red-teaming de LLMs. |
| `GEMINI_API_KEY` | Opcional | Clave de Google Gemini para red-teaming de LLMs. |

---

## 🧹 3. Limpieza de Contenedores (GHCR Cleanup)

| Input | Valor por Defecto | Tipo | Descripción |
| :--- | :---: | :---: | :--- |
| `CLEANUP_DISABLED` | `false` | `boolean` | Desactiva por completo la depuración de paquetes en GHCR. |
| `CLEANUP_KEEP_LATEST` | `10` | `number` | Número de imágenes/versiones recientes a conservar. |
| `CLEANUP_OLDER_THAN_DAYS` | `30` | `number` | Umbral de días para considerar una imagen como candidata a purga. |
| `CLEANUP_DRY_RUN` | `false` | `boolean` | Simula la purga sin borrar efectivamente paquetes. |
