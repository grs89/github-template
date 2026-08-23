# Guía de Uso 📘 (GitHub Actions)

¡Tu proyecto ya incluyó las plantillas de GitHub Actions! En esta guía aprenderás cómo interactuar con el pipeline en el día a día.

---

## 🚀 Disparando el Pipeline

El pipeline se ejecutará automáticamente bajo las siguientes condiciones:
1. Cuando hagas un `git push` a una rama de desarrollo (`dev`, `development`, `stg`, `staging`, `qa`).
2. Cuando hagas un `git push` a la rama principal (`main`, `master`).
3. Cuando abras un **Pull Request**.
4. Cuando crees un **Tag** de Git (`v1.0.0`, `v2026.08.04`).

---

## 🌐 Mapeo Automático de Entornos (GitHub Environments & GitOps)

Al incluir `03-start-init.yml`, el pipeline mapea y registra automáticamente el despliegue en **Settings > Environments** de GitHub y sincroniza el repositorio de GitOps de forma agnóstica según la rama:

| Rama / Evento | Entorno Registrado en GitHub | Carpeta GitOps Descubierta | Acción |
| :--- | :---: | :---: | :--- |
| `git push` a **`dev`** / **`development`** | 🟢 **`development`** | `*/k8s/DEV` | Sincroniza y despliega en Development |
| `git push` a **`stg`** / **`staging`** / **`qa`** | 🟡 **`staging`** | `*/k8s/STG` | Sincroniza y despliega en Staging |
| `git push` a **`main`** / **`master`** / **Tag** | 🔴 **`production`** | `*/k8s/PROD` | Sincroniza y despliega en Producción |

> [!TIP]
> **Búsqueda Agnóstica:** El motor de GitOps autodescubre cualquier carpeta que contenga `k8s/DEV`, `k8s/STG` o `k8s/PROD` (ej. `idp/k8s/DEV`, `vox/k8s/DEV`, `app/k8s/STG`) sin importar el nombre del microservicio o proyecto.

---

## 📦 Publicación Automática de Releases Oficiales

Cuando creas y subes un tag de Git (`git tag vX.Y.Z && git push origin vX.Y.Z`), el pipeline:
1. Ejecuta todos los escaneos de seguridad, pruebas y compilación de imágenes Docker.
2. Si todo finaliza exitosamente, ejecuta el job **`create_release`**.
3. Publica automáticamente un **GitHub Release** con:
   - Nombre de la versión (`Release vX.Y.Z`).
   - Notas de versión extraídas automáticamente de `CHANGELOG.md`.
   - Enlaces a los paquetes e imágenes en GHCR.
4. **Idempotencia:** Si el release ya existía en GitHub, el pipeline actualizará la descripción sin fallar.

---

## 📊 Visualizando los Resultados (El Reporte PDF Ejecutivo)

En la etapa final de cada microservicio, se ejecuta el consolidado de seguridad:
1. Ve a la pestaña **Actions** en tu repositorio de GitHub.
2. Haz clic en la última ejecución del workflow.
3. En la sección **Artifacts** en la parte inferior, descarga el archivo `executive-security-report-<servicio>`.
4. Abre el PDF o HTML para ver el **Dashboard Ejecutivo GRS** con el Health Score (A+ a F), matriz OWASP LLM Top 10 y métricas de seguridad.
