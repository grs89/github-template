# Catálogo de Funcionalidades (Features) 🌟

Las plantillas de este repositorio implementan un ciclo **DevSecOps 360°** completo sobre **GitHub Actions**, agrupando las mejores herramientas de seguridad, calidad, compilación, despliegue y observabilidad del mercado, configuradas y listas para usar.

---

## 🛡️ Escaneos de Seguridad Estática (SAST) y Calidad

| Feature | Descripción ("¿Qué hace?") | Herramienta Subyacente |
| :--- | :--- | :--- |
| **SAST** (Static Application Security Testing) | Analiza tu código fuente en busca de vulnerabilidades antes de compilarlo. | Semgrep / Trivy SAST |
| **SonarQube Scanner** | Análisis estático unificado de seguridad, code smells, duplicación e ingesta de cobertura multi-lenguaje. | SonarQube / SonarCloud |
| **Trivy SAST** | Escaneo profundo de código fuente y configuraciones para detección de CVEs y secretos embebidos. | Aqua Trivy |
| **SCA / Dependency Scanning** | Analiza dependencias de terceros buscando vulnerabilidades conocidas (`npm audit`, `pip-audit`, `govulncheck`). | SCA Nativo + Trivy |
| **Secret Detection** | Escanea el historial y los commits para asegurar que nadie exponga credenciales ni llaves privadas. | Gitleaks CLI |
| **Dockerfile Linter** | Validación estática y fortificación de Dockerfiles para evitar malas prácticas e inseguridades. | Hadolint |
| **Container Scanning** | Escanea la imagen de Docker final en busca de vulnerabilidades a nivel de Sistema Operativo. | Trivy Container |

---

## 🏗️ Escaneos de Infraestructura como Código (IaC Security)

| Feature | Descripción ("¿Qué hace?") | Herramienta Subyacente |
| :--- | :--- | :--- |
| **Trivy IaC Scan** | Escanea archivos de infraestructura (Dockerfile, Terraform, Kubernetes YAML) en busca de misconfiguraciones. | Trivy IaC |
| **Checkov IaC Scan** | Análisis estático complementario de IaC con más de 1000 políticas para Terraform, CloudFormation y K8s. | Checkov (Bridgecrew) |
| **License Compliance** | Audita las licencias de dependencias detectando licencias Copyleft restrictivas prohibidas (GPL, AGPL). | Compliance Engine |

---

## 🌐 Pruebas de Seguridad Dinámica (DAST)

| Feature | Descripción ("¿Qué hace?") | Herramienta Subyacente |
| :--- | :--- | :--- |
| **DAST** (Dynamic Application Security Testing) | Ejecuta pruebas dinámicas contra tu aplicación desplegada (XSS, CSRF, headers inseguros). | OWASP ZAP |
| **API Security Scan** | Escaneo especializado de endpoints de API REST/GraphQL detectando vulnerabilidades OWASP API Top 10. | OWASP ZAP API Scan |

---

## 🤖 Seguridad en Inteligencia Artificial (OWASP LLM Top 10)

| Feature | Descripción ("¿Qué hace?") | Herramienta Subyacente |
| :--- | :--- | :--- |
| **LLM Red-Teaming (Dynamic)** | Pruebas dinámicas contra endpoints LLM evaluando resistencia contra inyección de prompts (`LLM01`), fuga de prompts (`LLM07`) y alucinaciones (`LLM09`). | PromptFoo |
| **LLM SAST Custom Rules** | Reglas Semgrep especializadas para Python, JS y TS que detectan concatenación de prompts, manejo inseguro de outputs (`LLM05`) y exposición de tokens (`LLM02`). | Semgrep LLM Rules |
| **LLM Dependency Audit** | Auditoría y escaneo continuo de librerías del ecosistema de IA (`langchain`, `openai`, `anthropic`, `transformers`). | pip-audit / npm audit |

---

## 📦 Seguridad de Cadena de Suministro (Supply Chain Security)

- **SBOM (Software Bill of Materials):** Genera inventario detallado de dependencias en formato CycloneDX.
- **SLSA Provenance:** Atestación criptográfica de procedencia de la imagen compilada.
- **Image Signing (Cosign):** Firma digitalmente la imagen de Docker utilizando Sigstore (Keyless OIDC).

---

## 🚀 Continuous Deployment & GitOps

| Feature | Descripción ("¿Qué hace?") | Herramienta Subyacente |
| :--- | :--- | :--- |
| **GitHub Environments Automáticos** | Registra despliegues nativamente en **Environments** de GitHub (`development`, `staging`, `production`) según la rama de Git. | GitHub Environments |
| **Descubrimiento Agnóstico de GitOps** | Autolocaliza cualquier carpeta de entorno en el repositorio de infraestructura (`*/k8s/DEV`, `*/k8s/STG`, `*/k8s/PROD`, ej. `idp/k8s/DEV`, `vox/k8s/DEV`). | Motor GitOps Dinámico |
| **GitOps Declarative Deploy** | Actualiza el repo de infraestructura con la nueva imagen y tag para que ArgoCD sincronice el clúster. | GitOps / ArgoCD |
| **GitOps Auto-Revert** | Revierte automáticamente el commit en GitOps si Argo Rollouts aborta el despliegue por métricas degradadas. | Revert Automation |
| **Canary Deploy** | Despliegue progresivo a un subconjunto de tráfico con verificación continua y auto-rollback. | Argo Rollouts |
| **Autodetección de Monorepo Dinámica** | `03-start-init.yml` escanea subdirectorios, detecta lenguajes y genera matrices paralelas de ejecución en GitHub Actions. | Dynamic Matrix Engine |
| **Insignias por Microservicio en Monorepos** | Genera una tabla en el `README.md` con el stack, cobertura y seguridad aislados por cada microservicio. | Badge Generator |
| **Reportes de Seguridad Aislados por Servicio** | Cada microservicio genera su propio reporte ejecutivo PDF y HTML contextualizado. | Generador PDF WeasyPrint |
| **Limpieza de Container Registry (GHCR)** | Purga automatizada de imágenes y tags antiguos no protegidos vía GitHub REST API con `GITHUB_TOKEN`. | GHCR Cleanup |
| **Automated Releases (Idempotente)** | Publicación y actualización automática de GitHub Releases con `CHANGELOG.md` asociado en eventos de Tag (`v*`). | GitHub Release CLI |
| **Job Summaries Nativos** | Inyección de resultados visuales directamente en la interfaz de GitHub Actions sin descargas previas. | `$GITHUB_STEP_SUMMARY` |

---

## 🧩 Plantillas adicionales (portadas del catálogo GitLab)

| Feature | Descripción ("¿Qué hace?") | Workflow |
| :--- | :--- | :--- |
| **License Compliance** | Audita licencias de dependencias Node/Python y bloquea copyleft (GPL/AGPL/…). | `security-license-compliance.yml` |
| **Pentest agéntico con IA** | Agentes autónomos (Strix) con PoC real y SARIF a Code Scanning. | `security-strix-pentest.yml` |
| **Policy-as-Code** | Kyverno para manifiestos K8s y OPA/Rego para planes de Terraform. | `policies-policy-as-code.yml` |
| **Fuzzing / Mutation testing** | Go fuzz + Hypothesis; go-mutesting, Stryker, mutmut, PITest. | `test-fuzz-testing.yml`, `test-mutation-testing.yml` |
| **Preview Environments** | Entorno efímero por Pull Request (namespace/ArgoCD/vcluster) con cuota FinOps y destrucción al cerrar. | `k8s-preview-environments.yml` |
| **Scale up/down GitOps** | Apaga/enciende servicios editando `replicas` en el repo de infraestructura. | `k8s-scale.yml` |
| **Chaos testing** | PodChaos (Chaos Mesh) con sondeo `/healthz` en vivo. | `observability-chaos-testing.yml` |
| **DORA / Score / OTel** | Eventos DORA, métricas a Pushgateway y trazas OTLP del run (jobs + steps). | `observability-dora-metrics.yml`, `observability-score-exporter.yml`, `observability-otel-pipeline-traces.yml` |
| **Terraform con aprobación** | validate → plan → apply/destroy con *required reviewers* y detección de drift. | `infrastructure-terraform.yml` |
| **Renovate / Changelog / Release** | Actualización de dependencias, changelog git-cliff y GitHub Release con notas (IA opcional). | `utilities-renovate.yml`, `utilities-changelog.yml`, `utilities-release.yml`, `utilities-ai-release-notes.yml` |
| **Descripción de PR y Roadmap** | Descripción/labels automáticos del PR y ROADMAP.md → Milestones/Issues. | `utilities-mr-description.yml`, `utilities-roadmap-sync.yml` |

El catálogo completo con todos los inputs y secretos está en [`Workflows-Catalog.md`](Workflows-Catalog.md).
