# ⚙️ Guía de Instalación e Implementación

Esta guía proporciona la configuración exhaustiva para implementar el **GitHub Template** en proyectos nuevos o existentes.

## 1. Importación del Template

Para utilizar esta plantilla de CI/CD en tu organización:

1. Ve a la página principal del repositorio en GitHub.
2. Haz clic en el botón verde **"Use this template"** -> **"Create a new repository"**.
3. Nombra tu nuevo repositorio.
4. Asegúrate de marcar "Include all branches" si necesitas conservar histórico (opcional).
5. Clona el repositorio recién creado en tu máquina local:
   ```bash
   git clone git@github.com:tu_usuario/tu_nuevo_repo.git
   cd tu_nuevo_repo
   ```

## 2. Requisitos de Infraestructura

Para que los pipelines de DevSecOps se ejecuten correctamente, el repositorio de destino debe cumplir con lo siguiente:

- **Código Fuente Soportado:** El proyecto debe contener un archivo identificador en la raíz (ej. `go.mod` para Go, `package.json` para Node.js, `pom.xml` para Java) que el pipeline utiliza para auto-detectar el stack tecnológico.
- **Dockerfile:** Un archivo `Dockerfile` en la raíz (o en la ruta especificada en `DOCKERFILE_PATH`).
- **Registry:** Acceso administrativo a Docker Hub o GitHub Container Registry (GHCR) para generar tokens de acceso.

## 3. Configuración de Secretos en GitHub

Para autorizar a GitHub Actions a publicar contenedores, debes configurar credenciales estrictas.

> [!IMPORTANT]
> Nunca quemes estas credenciales en código ni en archivos `.env`. Deben ingresarse exclusivamente a través de la UI de GitHub en la sección de secretos.

Navega a **Settings** > **Secrets and variables** > **Actions** y añade:

| Secreto (`New repository secret`) | Descripción y Fuente |
| --- | --- |
| `DOCKERHUB_USERNAME` | Tu nombre de usuario público en Docker Hub. |
| `DOCKERHUB_TOKEN` | Token de acceso (PAT) generado en *Account Settings > Security* en Docker Hub. **Debe tener permisos de Read & Write**. |
| `DOCKERHUB_REPO` | El namespace completo o nombre del repositorio final (ej. `mi-usuario/mi-app`). |

## 4. Configuración de Protecciones de Rama (Branch Protection)

Para asegurar el ciclo de vida del CI/CD, es obligatorio configurar protecciones en la rama `main`:

1. Ve a **Settings** > **Branches**.
2. Añade una regla para la rama `main`.
3. Activa **"Require a pull request before merging"**.
4. Activa **"Require status checks to pass before merging"**.
5. Añade los checks requeridos: `lint-and-test`, `security-scan`.

## 5. Troubleshooting Común

### Error: "push access denied, repository does not exist or may require authorization"
- **Causa:** El `DOCKERHUB_TOKEN` expiró o no tiene permisos de *Write*.
- **Solución:** Regenera el token en Docker Hub asegurando permisos de Lectura/Escritura y actualiza el secreto en GitHub.

### Error: "Checkov IaC Scan failed"
- **Causa:** Checkov encontró vulnerabilidades en tu `Dockerfile`. A partir de la `v2`, Checkov tiene `soft_fail: true` por lo que no detendrá tu pipeline, pero la vulnerabilidad estará presente en el PDF de seguridad.
- **Solución:** Descarga el artefacto PDF del Security Scan, revisa el código de regla (ej. `CKV_DOCKER_2`) y corrige tu infraestructura.
