# 🐳 GitHub Template - CI/CD DevSecOps Pipeline

[![Build, Push & Scan (Auto)](https://github.com/YOUR_USERNAME/github-template/actions/workflows/docker-build_push_auto.yml/badge.svg)](https://github.com/YOUR_USERNAME/github-template/actions/workflows/docker-build_push_auto.yml)
[![PR Validation](https://github.com/YOUR_USERNAME/github-template/actions/workflows/pull-request-validation.yml/badge.svg)](https://github.com/YOUR_USERNAME/github-template/actions/workflows/pull-request-validation.yml)
[![Security Scan](https://img.shields.io/badge/Security-Trivy-blue)](https://trivy.dev/)
[![Docker](https://img.shields.io/badge/Docker-Multi--Arch-2496ED?logo=docker)](https://www.docker.com/)

Plantilla de repositorio **Estado del Arte** para GitHub con pipelines CI/CD modulares, ultra rápidos y seguros. Diseñado para ofrecer una experiencia de desarrollador (DX) superior, compilaciones Docker multi-arquitectura optimizadas, Integración Continua en ramas efímeras y estándares completos de seguridad automatizada.

---

## 📋 Tabla de Contenidos

- [Características Destacadas](#-características-destacadas)
- [Arquitectura Reutilizable (Workflows)](#-arquitectura-reutilizable-workflows)
- [Requisitos Previos](#-requisitos-previos)
- [Configuración Rápida](#-configuración-rápida)
- [Uso y Disparadores Automáticos](#-uso-y-disparadores-automáticos)
- [Estructura del Proyecto](#-estructura-del-proyecto)
- [Migración OIDC y Entornos](#-migración-oidc-y-entornos-avanzado)
- [Licencia](#-licencia)

---

## ✨ Características Destacadas

| 🚀 Tecnologías Modernas | Qué soluciona en tu proyecto |
| --- | --- |
| **Arquitectura Modular (`uses:`)** | Facilita el mantenimiento. Los flujos gigantes se dividieron en 3 bloques reutilizables (Lint/Test, Build/Push, y Security). |
| **Continuous Integration Ágil** | El Action secundario **`pull-request-validation.yml`** escanea calidad de código y SAST en *segundos* al revisar PRs interceptando bugs antes de llegar a `main`. |
| **Caché Avanzada (GHA)** | La compilación Docker usa el caché nativo de GitHub Actions ultrarápido en lugar de usar exportadores lentos al Registro Remoto. |
| **SLSA Provenance & SBOM Nivel 3** | Las imágenes publicadas certifican automáticamente tus vulnerabilidades (SBOM, SPDX) y sus huellas digitales anticopia. |
| **Auto-cancelación Redundante** | Utiliza reglas de `concurrency:` para abortar despliegues superpuestos en paralelo, ahorrando billes en minutos perdidos en la nube. |
| **DX Nativo: Job Summaries** | Resultados de cobertura (`go test`, `jest`, etc) y vulnerabilidades se inyectan en Markdown nativo (`$GITHUB_STEP_SUMMARY`) por lo que no hace falta abrir ni descargar ZIP/PDFs para el desarrollador. |
| **Dependabot Configurado** | Reglas activas para actualizar tus propias acciones y librerías base de Docker automáticamente de modo semanal. |

---

## 🏛️ Arquitectura Reutilizable (Workflows)

```mermaid
flowchart TD
    A[Push a un Tag v*.*.*] --> B{docker-build_push_auto.yml<br/>(Orquestador Principal)}
    PR[Abres Pull Request] --> PRV{pull-request-validation.yml<br/>(Orquestador Ligero)}

    subgraph "Workflows Específicos de Negocio (CD)"
        B -->|Paso 1: Detectar Lenguaje| B
        B -->|Paso 2: uses| C(shared-lint-test.yml)
        B -->|Paso 3: uses| D(shared-build-push.yml)
        B -->|Paso 4: uses| E(shared-security-scan.yml)
    end

    subgraph "Validación Ágil para Desarrolladores (CI)"
        PRV -->|Paso 1: usa| C
        PRV -->|Paso 2: Análisis rápido| SAST[trivy-sast]
    end
    
    C -.-> |Imprime Job Summary Cobertura| JS1[UI de GitHub GITHUB_STEP_SUMMARY]
    E -.-> |Imprime Job Summary Seguridad| JS1
    SAST -.-> |Imprime Job Summary SAST| JS1
    D --> |Firma Cosign + SLSA| DOC[Docker Hub y GHCR]
```

### Orquestadores vs Flujos Compartidos

- **Orquestadores:** Son los archivos que interceptan el evento del usuario (crear un PR o subir un tag de versión). Interrogan el lenguaje del proyecto (`go.mod`, `pom.xml`, `package.json`) y llaman a los flujos siguientes según corresponda. Su rol es únicamente decidir y pasar datos.
- **`shared-*.yml`:** Tienen toda la carne de ejecución por dentro sin saber quién los activa. Permite que múltiples microservicios u otros repositorios apunten a este repositorio base unificando infraestructuras de tu organización.

---

## 📋 Requisitos Previos

- Cuenta de [Docker Hub](https://hub.docker.com/) o GHCR.
- Repositorio GitHub
- Archivo o paquete rastreable en la raíz del proyecto para la detección `[go.mod, package.json, pom.xml, etc]`. Para casos custom, crear un archivo `version.yml`.

---

## ⚡ Configuración Rápida

### 1️⃣ Inicializar
1. Haz clic en **"Use this template"** en GitHub en el panel superior para instanciar tu copia operativa.

### 2️⃣ Secretos Clásicos o Standard
Navega a **Settings → Secrets and variables → Actions** y añade:

| Secret (Variable de GitHub) | Descripción |
|--------|-------------|
| `DOCKERHUB_USERNAME` | Tu nombre de usuario público |
| `DOCKERHUB_TOKEN` | Token de acceso (Generado en Docker Hub Security) |
| `DOCKERHUB_REPO` | El container de destino, ej. `mi-app-back` |

---

## 🚀 Uso y Disparadores Automáticos

### 1. Desarrollo Continuo y Review de Pull Requests

Cuando tu equipo abra un Pull Request desde una rama (e.g. `feat/nueva-base`), el workflow ultra rápido de `pull-request-validation.yml` se activará en pocos segundos:
1. Validará el formateo/linter de tu código.
2. Correrá las pruebas unitarias e imprimirá la **Cobertura** directamente a tu pantalla de Actions de GH.
3. Buscará credenciales o vulnerabilidades estáticas quemadas en tus ramas (SAST - Trivy) también pintando la solución en Markdown.
*💡 Si empujas nuevos commits velozmente a esta rama, los workflows de Actions previos se cancelarán automáticamente liberando recursos de cómputo.*

### 2. Disparo a Producción (Tags Semánticos)

Crea un tag con versión de software en la base de la rama principal:

```bash
git tag v1.0.0
git push origin v1.0.0
```

Se activará el orquestador principal (`docker-build_push_auto.yml`), llamando a todas las tuberías de validación, procediendo por fin con la construcción Multi-Arquitectura veloz usando caché GHA, añadiendo una certificación **SLSA de Nivel 3 y SBOM transparente**, finalizando por publicar tus contenedores con tu firma in-toto/Cosign anexada.

---

## 📁 Estructura del Proyecto

```text
github-template/
├── .github/
│   ├── dependabot.yml                      # Actualizador automático de Actions y base Docker (Semanal)
│   ├── trivy/
│   │   └── action.yml                      # Composite Action estándar
│   ├── workflows/
│   │   ├── docker-build_push_auto.yml      # ** Orquestador CD principal (Para Tags)
│   │   ├── docker-publish.yml              # Variación antigua de Docker simple
│   │   ├── pull-request-validation.yml     # ** Orquestador CI ultra rápido (Para ramas PR)
│   │   ├── shared-build-push.yml           # Bloque REUTILIZABLE para Docker, GHA Cache y SBOM SLSA
│   │   ├── shared-lint-test.yml            # Bloque REUTILIZABLE para calidad y DX Cobertura visual
│   │   └── shared-security-scan.yml        # Bloque REUTILIZABLE para Escáner final 
├── src/ o app/                             # Tu código de aplicación
├── Dockerfile                              # Tu receta Docker
└── README.md                               # <-- Usted está aquí
```

---

## 🔐 Migración OIDC y Entornos (Avanzado)

Para elevar tu seguridad al extremo en proyectos empresariales grandes:

### Zero-Trust mediante AWS/Azure/GCP (Sin secretos fijos)

Este template soporta federación de identidad `OpenID Connect` porque todos los roles tienen `id-token: write` por defecto. Si requieres publicar no a Docker Hub sino a contenedores privados en la nube como una instancia Elastic Container Registry (AWS ECR):

Dirígete a `shared-build-push.yml` y antes de usar tu plugin de login normal, asume un rol usando tu Amazon ARN. Así removerás cualquier `AWS_ACCESS_KEY_ID` estática expuesta a ser robada:

```yaml
- name: 🔐 Configure AWS Credentials OIDC
  uses: aws-actions/configure-aws-credentials@v4
  with:
    role-to-assume: arn:aws:iam::1234567890:role/MiGithubActionsRoles
    aws-region: us-east-1
```

### GitHub Environments para interrupción manual
Si requieres que un manager aplique su firma o botón antes de permitir construir un Docker Multi Arch (para evitar sobrescribir producción), navega al repositorio Orquestador y declara tu ambiente al nivel del llamado al `build-and-push`:

```yaml
  build-and-push:
    name: 🏗️ Build, Push & Sign
    needs: [detect-language, lint-and-test]
    uses: ./.github/workflows/shared-build-push.yml
    environment: production   # <-- REQUERIRA UN MANAGER DANDO CLICK EN 'REVIEW' DESDE GITHUB UI
    with:
      #...
```

---

## 📜 Licencia

Este proyecto está bajo la Licencia MIT. Consulta el archivo [LICENSE](LICENSE) para más detalles.

---

<div align="center">

**[⬆ Volver arriba](#-github-template---cicd-devsecops-pipeline)**

Escrito y refactorizado a la altura del Arte para infraestructuras DevSecOps robustas. ❤️

</div>
