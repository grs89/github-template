# 🔑 Variables de Entorno y Secretos

El motor DevSecOps utiliza secretos inyectados dinámicamente mediante el gestor nativo de GitHub Actions para interactuar con infraestructuras externas, como registros de contenedores y servicios en la nube, sin exponer contraseñas en código duro.

> [!CAUTION]
> Almacenar `DOCKERHUB_TOKEN` o `REGISTRY_PASSWORD` en formato texto plano dentro del código fuente provocará un fallo inmediato en las políticas de seguridad SAST de Trivy y podría exponer contenedores de la compañía.

## Tabla de Secretos Requeridos

Estos secretos deben configurarse en **Settings > Secrets and variables > Actions > Repository secrets**.

| Nombre del Secreto (`Secret`) | Descripción Técnica y Propósito | Requerido | Valor de Ejemplo / Origen |
| --- | --- | :---: | --- |
| `DOCKERHUB_USERNAME` | Identificador público que será enviado al `docker/login-action`. Actúa como principal para obtener el ticket de autenticación del API de Docker Hub. | ✅ Sí | `gersonofstone` |
| `DOCKERHUB_TOKEN` | Token de Acceso Personal (PAT). Utilizado como password por Buildx. Debe tener explícitamente el "scope" de `Read & Write` para posibilitar el `docker push`. | ✅ Sí | `dckr_pat_xxxxx...` |
| `DOCKERHUB_REPO` | Ruta base del repositorio destino dentro de Docker Hub o GHCR que será procesado. Si un atacante roba este dato no puede hacer nada sin el Token. | ✅ Sí | `gersonofstone/centralizegg` |

## Variables Dinámicas Derivadas (Entorno de Ejecución)

A lo largo del pipeline, el sistema inyecta y utiliza las siguientes variables extraídas desde el contexto global para asegurar flujos agnósticos. *No necesitas configurarlas manualmente.*

| Variable de Entorno | Origen del Pipeline | Comportamiento en Tiempo de Ejecución |
| --- | --- | --- |
| `REPO_LC` | `${GITHUB_REPOSITORY,,}` | Asegura que el nombre de repositorio extraído en `detect-language` esté siempre forzado a minúsculas (`toLowerCase`). Evita que Docker rechace URLs con mayúsculas (`invalid reference format`). |
| `DETECTED_LANG` | Script Bash local | Determina el lenguaje raíz leyendo extensiones. Utilizado por `shared-lint-test.yml` para bifurcar (forkear) dinámicamente hacia las reglas `npm` o hacia las reglas `go test`. |
| `IMAGE_TAG` | Evento del Webhook | Si la ejecución es por Tag (`refs/tags/*`), vale el string semántico (`v1.0.4`). Si es ejecución manual, utiliza el fallback estático `latest`. |

## Variables Locales Opcionales (`.env` local)

En la raíz de tus proyectos que consuman este template, es altamente recomendado incluir un archivo `.env.example` que denote qué variables utilizará tu contenedor. El pipeline no hace *parseo* directo de ellas en la nube (pues deben inyectarse en el orquestador como *ConfigMaps* de Kubernetes o *Secrets*), pero sirven como esquema de metadatos estáticos.
