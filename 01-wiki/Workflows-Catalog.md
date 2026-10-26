# Catálogo de Workflows Reutilizables 📚

Todos los workflows de `.github/workflows/` con `on: workflow_call` se consumen con:

```yaml
jobs:
  ejemplo:
    uses: grs89/github-template/.github/workflows/<archivo>.yml@main
    with:
      INPUT: valor
    secrets: inherit   # o secretos explícitos
```

> Los parámetros se pasan como `inputs` tipados (nombres en MAYÚSCULAS); los secretos se declaran en `secrets:`. Las tablas de abajo se generan desde los propios workflows.

## Equivalencias GitLab → GitHub

| Plantilla GitLab | Workflow GitHub |
|:---|:---|
| `security/license-compliance.yml` | `security-license-compliance.yml` |
| `security/strix-pentest.yml` | `security-strix-pentest.yml` |
| `security/sbom.yml` | `security-sbom.yml` |
| `security/image-signing.yml` | `security-image-signing.yml` |
| `security/slsa-provenance.yml` | `security-slsa-provenance.yml` |
| `security/ai-remediation.yml` | `security-ai-remediation.yml` |
| `security/api-security.yml` | `security-api-security.yml` |
| `security/cluster-scanning.yml` | `security-cluster-scanning.yml` |
| `security/dast-zap.yml` | `security-dast-zap.yml` |
| `security/defectdojo.yml` | `security-defectdojo.yml` |
| `security/llm-security.yml` | `security-llm-security.yml` |
| `sast/checkov.yml` | `sast-checkov.yml` |
| `sast/trivy-iac.yml` | `sast-trivy-iac.yml` |
| `sast/sonarcube-scan_generic.yml` | `sast-sonarcube-scan_generic.yml` |
| `sast/trivy-sast.yml · sast/secret-scanning.yml` | `shared-security-scan.yml · shared-lint-test.yml` |
| `quality/code-quality.yml` | `quality-code-quality.yml` |
| `quality/lint_argocd.yml` | `quality-lint-argocd.yml` |
| `quality/megalinter.yml` | `quality-megalinter.yml` |
| `quality/ai-test-generator.yml` | `quality-ai-test-generator.yml` |
| `quality/accessibility.yml · lighthouse-check.yml · lint_templates.yml` | `quality-accessibility.yml · quality-lighthouse-check.yml · quality-lint_templates.yml` |
| `test/fuzz-testing.yml` | `test-fuzz-testing.yml` |
| `test/mutation-testing.yml` | `test-mutation-testing.yml` |
| `test/playwright-e2e.yml · test/tests_generic.yml` | `test-playwright-e2e.yml · shared-lint-test.yml` |
| `observability/dora-metrics.yml` | `observability-dora-metrics.yml` |
| `observability/score-exporter.yml` | `observability-score-exporter.yml` |
| `observability/otel-pipeline-traces.yml` | `observability-otel-pipeline-traces.yml` |
| `observability/chaos-testing.yml` | `observability-chaos-testing.yml` |
| `observability/{api-contract,grafana,otel-validate,performance,smoke,uptime-kuma}` | `observability-*.yml` |
| `k8s/preview-environments.yml` | `k8s-preview-environments.yml` |
| `k8s/k8s-scale-up.yml · k8s-scale-down.yml` | `k8s-scale.yml (input ACTION=up|down)` |
| `k8s/gitops.yml` | `k8s-gitops.yml` |
| `k8s/{chaos-mesh-pod,rollout-bluegreen,analysis-template}.yml` | `k8s/*.yml (manifiestos con placeholders envsubst)` |
| `policies/policy-as-code.yml (+ kyverno/, rego/)` | `policies-policy-as-code.yml (+ policies/)` |
| `utilities/notifications.yml` | `utilities-notifications.yml` |
| `utilities/renovate.yml (+ renovate.json, default.json)` | `utilities-renovate.yml (+ renovate.json, default.json)` |
| `utilities/changelog.yml` | `utilities-changelog.yml` |
| `utilities/release.yml` | `utilities-release.yml` |
| `utilities/ai-release-notes.yml` | `utilities-ai-release-notes.yml` |
| `utilities/roadmap-sync.yml` | `utilities-roadmap-sync.yml` |
| `utilities/dependency-update.yml` | `utilities-dependency-update.yml` |
| `utilities/mr-description.yml` | `utilities-mr-description.yml (descripción del Pull Request)` |
| `utilities/semantic-release.yml` | `utilities-semantic-release.yml` |
| `utilities/{badge-generator,cleanup-registry,generate-report,detect}.yml` | `utilities-badge-generator.yml · utilities-cleanup-ghcr.yml · executive-report.yml · 03-start-init.yml` |
| `infrastructure/{terraform,infracost}.yml · 03-start/{iac,ansible-child}.yml` | `infrastructure-*.yml · 03-start-iac.yml` |
| `deploy/{canary-deploy,gitops-deploy,pages}.yml` | `deploy-*.yml` |
| `doc/{pages-generator,project-scaffold,wiki-sync}.yml` | `doc-*.yml · shared-wiki-sync.yml · wiki-publish.yml` |
| `git/{external-git,external_component-git,infra-update}.yml` | `git-*.yml` |
| `libraries/maven-lib.yml` | `libraries-maven-lib.yml` |
| `03-start/init.yml · docker-matrix-child.yml · docker-brk/dnd` | `03-start-init.yml · 03-start-docker-matrix-child.yml · docker-*.yml` |
| `container/*.yml · registry/*.yml` | `shared-build-push.yml (GHCR + Docker Hub + ECR)` |

## Workflows reutilizables

### `03-start-docker-matrix-child.yml`
**03 Start Docker Matrix Child**

| Input | Req. | Default | Descripción |
|:---|:---:|:---|:---|
| `SERVICE_PATH` |  | `.` | Directorio del microservicio |
| `SERVICE_NAME` |  | | Nombre del microservicio |
| `SERVICE_LANG` |  | `unknown` | Lenguaje del microservicio (go, python, js, java-maven, java-gradle) |
| `GITOPS_TARGET_ENV` |  | `PROD` | Entorno objetivo para GitOps (DEV, STG, PROD) |
| `TARGET_ENVIRONMENT` |  | `production` | GitHub Environment (development, staging, production) |

| Secret | Req. | Descripción |
|:---|:---:|:---|
| `GITHUB_TOKEN` |  |  |
| `GITLAB_TOKEN` |  |  |
| `COSIGN_PRIVATE_KEY` |  |  |
| `COSIGN_PASSWORD` |  |  |
| `DOCKERHUB_USERNAME` |  |  |
| `DOCKERHUB_TOKEN` |  |  |
| `SONAR_TOKEN` |  |  |
| `SONAR_HOST_URL` |  |  |
| `DEFECTDOJO_API_KEY` |  |  |
| `DEFECTDOJO_URL` |  |  |
| `GITOPS_DEPLOY_KEY` |  |  |
| `LLM_API_KEY` |  |  |
| `OPENAI_API_KEY` |  |  |
| `ANTHROPIC_API_KEY` |  |  |
| `GEMINI_API_KEY` |  |  |

### `03-start-iac.yml`
**03 Start IaC (Terraform)**

| Input | Req. | Default | Descripción |
|:---|:---:|:---|:---|
| `TF_ROOT` |  | `.` | Directorio raíz de Terraform |
| `TARGET_ENVIRONMENT` |  | `production` | GitHub Environment (development, staging, production) |

| Secret | Req. | Descripción |
|:---|:---:|:---|
| `INFRACOST_API_KEY` |  |  |
| `AWS_ACCESS_KEY_ID` |  |  |
| `AWS_SECRET_ACCESS_KEY` |  |  |
| `ARM_CLIENT_ID` |  |  |
| `ARM_CLIENT_SECRET` |  |  |
| `ARM_SUBSCRIPTION_ID` |  |  |
| `ARM_TENANT_ID` |  |  |

### `03-start-init.yml`
**03 Start Init**

| Input | Req. | Default | Descripción |
|:---|:---:|:---|:---|
| `SERVICES` |  | | Lista opcional de microservicios explícitos separados por espacio |
| `PUSH_TO_ECR` |  | `False` | Activar push a AWS ECR |
| `RUNNER_TAG` |  | `ubuntu-latest` | Runner label |

| Secret | Req. | Descripción |
|:---|:---:|:---|
| `GITLAB_TOKEN` |  |  |
| `GITHUB_TOKEN` |  |  |
| `COSIGN_PRIVATE_KEY` |  |  |
| `COSIGN_PASSWORD` |  |  |
| `DOCKERHUB_USERNAME` |  |  |
| `DOCKERHUB_TOKEN` |  |  |
| `SONAR_TOKEN` |  |  |
| `SONAR_HOST_URL` |  |  |
| `DEFECTDOJO_API_KEY` |  |  |
| `DEFECTDOJO_URL` |  |  |
| `INFRACOST_API_KEY` |  |  |
| `OPENAI_API_KEY` |  |  |
| `ANTHROPIC_API_KEY` |  |  |
| `GEMINI_API_KEY` |  |  |

### `deploy-canary-deploy.yml`
**Deploy Canary Deploy**

| Input | Req. | Default | Descripción |
|:---|:---:|:---|:---|
| `CANARY_DISABLED` |  | `false` | CANARY_DISABLED |
| `CANARY_WEIGHT` |  | `20` | CANARY_WEIGHT |
| `CANARY_VERIFY_TIMEOUT` |  | `120` | CANARY_VERIFY_TIMEOUT |
| `K8S_NAMESPACE` |  | `default` | K8S_NAMESPACE |
| `CANARY_REPLICAS` |  | `1` | CANARY_REPLICAS |
| `CANARY_HEALTH_URL` |  | | CANARY_HEALTH_URL |
| `CANARY_ERROR_THRESHOLD` |  | `5` | CANARY_ERROR_THRESHOLD |
| `IMAGE_TAG` |  | `latest` | Tag de la imagen a desplegar en ghcr.io/<repo> |

| Secret | Req. | Descripción |
|:---|:---:|:---|
| `KUBE_CONFIG` | ✅ | kubeconfig en base64 con permisos de deploy |

### `deploy-gitops-deploy.yml`
**Deploy GitOps**

| Input | Req. | Default | Descripción |
|:---|:---:|:---|:---|
| `SERVICE_PATH` |  | `.` | Ruta del microservicio |
| `SERVICE_NAME` |  | | Nombre del microservicio |
| `GITOPS_TARGET_ENV` |  | `PROD` | Entorno destino de GitOps (DEV, STG, PROD) |
| `TARGET_ENVIRONMENT` |  | `production` | GitHub Environment (development, staging, production) |
| `IMAGE_TAG` |  | | Tag de la imagen a desplegar |
| `GITOPS_INFRA_REPO` |  | | Repositorio GitOps destino |
| `GITOPS_TARGET_DIR` |  | | Directorio explícito de despliegue en GitOps (opcional) |

| Secret | Req. | Descripción |
|:---|:---:|:---|
| `GITHUB_TOKEN` |  |  |
| `GITOPS_DEPLOY_KEY` |  |  |
| `GITLAB_TOKEN` |  |  |

### `deploy-pages.yml`
**Deploy Pages** — Publica en GitHub Pages: sitio estático (index.html en la raíz) o wiki/README compilado (+ presentación PPTX/HTML). Requiere Settings > Pages > Source = "GitHub Actions".

| Input | Req. | Default | Descripción |
|:---|:---:|:---|:---|
| `PAGES_ENABLED` |  | `true` | Publicar en GitHub Pages |
| `PAGES_STATIC_DIR` |  | `.` | Directorio a publicar cuando el repo es un sitio estático |
| `BUILD_PRESENTATIONS` |  | `True` | Generar presentación PPTX/HTML de la wiki (scripts/build_pptx.py) |
| `TEMPLATE_PROJECT` |  | `grs89/github-template` | Repositorio de plantillas que contiene scripts/ |
| `TEMPLATE_REF` |  | `main` | Rama o tag del repositorio de plantillas |

### `doc-pages-generator.yml`
**Doc Pages Generator** — Compila el wiki/README a un sitio estático (public/) y lo publica en GitHub Pages. Requiere: Settings > Pages > Source = "GitHub Actions".

| Input | Req. | Default | Descripción |
|:---|:---:|:---|:---|
| `PAGES_ENABLED` |  | `true` | Publicar en GitHub Pages |
| `TEMPLATE_PROJECT` |  | `grs89/github-template` | Repositorio de plantillas que contiene scripts/generate_docs.py |
| `TEMPLATE_REF` |  | `main` | Rama o tag del repositorio de plantillas |
| `DEPLOY` |  | `True` | Desplegar a Pages (false = solo compilar y subir artefacto) |

### `doc-project-scaffold.yml`
**Doc Project Scaffold**

| Input | Req. | Default | Descripción |
|:---|:---:|:---|:---|
| `SCAFFOLD_DISABLED` |  | `false` | SCAFFOLD_DISABLED |
| `SCAFFOLD_LANG` |  | | SCAFFOLD_LANG |
| `SCAFFOLD_NAME` |  | | SCAFFOLD_NAME |
| `SCAFFOLD_FORCE` |  | `false` | SCAFFOLD_FORCE |

| Secret | Req. | Descripción |
|:---|:---:|:---|
| `SCAFFOLD_TOKEN` |  | PAT con scope workflow (solo si SCAFFOLD_FORCE=push y se genera .github/workflows) |

### `docker-build_push_auto.yml`
**🐳 Docker Build, Push & Scan (Auto)**

| Input | Req. | Default | Descripción |
|:---|:---:|:---|:---|
| `CONTEXT_DIR` |  | `.` | Directorio del código fuente para evaluación del lenguage (eg pom.xml) |
| `DOCKERFILE_PATH` |  | `./Dockerfile` | Ruta relativa al Dockerfile (ej. ./Dockerfile o ./log_processor/Dockerfile) |

| Secret | Req. | Descripción |
|:---|:---:|:---|
| `REGISTRY` |  |  |
| `REGISTRY_USER` |  |  |
| `REGISTRY_PASSWORD` |  |  |
| `COSIGN_PRIVATE_KEY` |  |  |
| `COSIGN_PASSWORD` |  |  |
| `DOCKERHUB_USERNAME` |  |  |
| `DOCKERHUB_TOKEN` |  |  |
| `DOCKERHUB_REPO` |  |  |

### `docker-publish.yml`
**Build and Push Docker Image**

| Input | Req. | Default | Descripción |
|:---|:---:|:---|:---|
| `CONTEXT_DIR` |  | `.` | Directorio del código fuente para detección de versión (eg. pom.xml) |
| `DOCKERFILE_PATH` |  | `./Dockerfile` | Ruta relativa al Dockerfile (ej. ./Dockerfile o ./mi_app/Dockerfile) |

| Secret | Req. | Descripción |
|:---|:---:|:---|
| `DOCKERHUB_USERNAME` | ✅ |  |
| `DOCKERHUB_TOKEN` | ✅ |  |
| `DOCKERHUB_REPO` | ✅ |  |

### `executive-report.yml`
**📊 Executive Report** — Consolida los reportes de seguridad de la corrida (artefactos *report*) en un reporte ejecutivo HTML/PDF.

| Input | Req. | Default | Descripción |
|:---|:---:|:---|:---|
| `REPORTS_ARTIFACT_PATTERN` |  | `*report*` | Patrón de artefactos con reportes a consolidar |
| `TEMPLATE_PROJECT` |  | `grs89/github-template` | Repo de plantillas con .github/utilidades/generate_report.py |

### `git-external-git.yml`
**Git External Mirror** — Replica este repositorio (ramas y tags) hacia un Git externo (GitLab, Bitbucket, Gitea, ...).

| Input | Req. | Default | Descripción |
|:---|:---:|:---|:---|
| `EXTERNAL_REPO_URL` | ✅ | | URL del repo destino sin credenciales (https://gitlab.com/grupo/repo.git o git@gitlab.com:grupo/repo.git) |
| `EXTERNAL_GIT_USER` |  | `oauth2` | Usuario para HTTPS con token (oauth2 en GitLab, x-token-auth en Bitbucket) |
| `SYNC_ALL_BRANCHES` |  | `True` | Sincronizar todas las ramas (false = solo la rama actual) |
| `SYNC_ALL_TAGS` |  | `True` | Sincronizar todos los tags |

| Secret | Req. | Descripción |
|:---|:---:|:---|
| `EXTERNAL_GIT_TOKEN` |  | Token de acceso con permiso de escritura (para URLs https) |
| `EXTERNAL_GIT_SSH_KEY` |  | Llave SSH privada con permiso de escritura (para URLs git@) |

### `git-external_component-git.yml`
**Git External_Component Git**

| Input | Req. | Default | Descripción |
|:---|:---:|:---|:---|
| `REPO_ENTREGA_URL` | ✅ | | Repo destino (https://... o host:org/repo.git para SSH) |
| `REPO_ENTREGA_COMPONENT` |  | | Prefijo del repo de cada componente (vacío = prefijo del entorno) |
| `RELEASE_FILE` |  | `release_info.yml` | Archivo de release generado por git-infra-update |
| `RELEASE_ARTIFACT` |  | `release-info` | Artefacto que contiene RELEASE_FILE (vacío = ya está en el workspace) |

| Secret | Req. | Descripción |
|:---|:---:|:---|
| `DEPLOY_KEY` |  | Llave SSH privada con escritura en el repo destino (solo para URLs SSH) |

### `git-infra-update.yml`
**Git Infra Update**

| Input | Req. | Default | Descripción |
|:---|:---:|:---|:---|
| `INFRA_REPO_URL` | ✅ | | Repo de infraestructura en formato host:org/repo.git (se clona vía SSH como git@host:org/repo.git) |
| `TARGET_FILE_PATH` |  | | Directorio dentro del repo de infraestructura donde buscar <servicio>.yaml |
| `IMAGE_TAG` |  | | Tag de la imagen (vacío = <rama>_<run_number>) |

| Secret | Req. | Descripción |
|:---|:---:|:---|
| `DEPLOY_KEY` | ✅ | Llave SSH privada con permiso de escritura en el repo de infraestructura |

### `infrastructure-ansible.yml`
**Infrastructure Ansible**

| Input | Req. | Default | Descripción |
|:---|:---:|:---|:---|
| `TEMPLATE_PROJECT` |  | `grs89/github-template` | Repo de plantillas con .github/utilidades/generate_report.py |

### `infrastructure-infracost.yml`
**Infrastructure Infracost** — Estimación de costos (FinOps) de cambios Terraform, comentada en el Pull Request.

| Input | Req. | Default | Descripción |
|:---|:---:|:---|:---|
| `TF_ROOT` |  | `.` | Directorio raíz de Terraform |

| Secret | Req. | Descripción |
|:---|:---:|:---|
| `INFRACOST_API_KEY` | ✅ | API key de Infracost |

### `infrastructure-terraform.yml`
**Infrastructure Terraform** — validate -> plan -> apply (aprobación manual vía GitHub Environment) | destroy | drift detection. El estado debe vivir en un backend remoto (S3, GCS, azurerm, ...). Credenciales cloud: secret TF_CLOUD_ENV.

| Input | Req. | Default | Descripción |
|:---|:---:|:---|:---|
| `TF_DISABLED` |  | `false` | Deshabilitar el pipeline de Terraform |
| `TF_VERSION` |  | `1.9.8` | Versión de Terraform |
| `TF_ROOT` |  | `.` | Directorio raíz de Terraform |
| `TF_VAR_FILE` |  | | Archivo -var-file (vacío = terraform.<rama>.tfvars si existe) |
| `TF_EXTRA_ARGS` |  | | Argumentos extra para plan/apply |
| `TF_BACKEND_ARGS` |  | | Argumentos -backend-config para terraform init (ej. "-backend-config=bucket=mi-estado") |
| `TF_WORKSPACE` |  | | Workspace de Terraform (vacío = nombre de la rama) |
| `TF_LINT_FAIL` |  | `False` | Fallar el job si tflint reporta hallazgos |
| `TF_APPLY` |  | `True` | Habilitar apply en tags (v*) |
| `TF_DESTROY` |  | `False` | Habilitar el job destroy (solo en tags, con aprobación del environment) |
| `TF_APPLY_ENVIRONMENT` |  | `production` | GitHub Environment con required reviewers para apply/destroy |

| Secret | Req. | Descripción |
|:---|:---:|:---|
| `TF_CLOUD_ENV` |  | Variables de entorno cloud, una por línea KEY=VALUE (ej. AWS_ACCESS_KEY_ID=...) |

### `k8s-gitops.yml`
**K8S GitOps Validation**

| Input | Req. | Default | Descripción |
|:---|:---:|:---|:---|
| `CHECK_DIR` |  | `.` | Directorio con manifiestos Kubernetes |
| `KUBERNETES_VERSION` |  | `1.30.0` | Versión de Kubernetes contra la que validar esquemas (kubeconform) |

### `k8s-k8s-deploy.yml`
**K8S K8S Deploy**

| Input | Req. | Default | Descripción |
|:---|:---:|:---|:---|
| `DEPLOY_DISABLED` |  | `false` | DEPLOY_DISABLED |
| `K8S_NAMESPACE` |  | | K8S_NAMESPACE |
| `KUSTOMIZE_DIR` |  | | KUSTOMIZE_DIR |
| `KUSTOMIZE_FALLBACK_DIR` |  | `k8s` | KUSTOMIZE_FALLBACK_DIR |
| `HELM_CHART_PATH` |  | `helm/` | HELM_CHART_PATH |
| `HELM_RELEASE_NAME` |  | | HELM_RELEASE_NAME |
| `HELM_VALUES_FILE` |  | | HELM_VALUES_FILE |
| `HELM_EXTRA_ARGS` |  | | HELM_EXTRA_ARGS |
| `K8S_MANIFESTS_DIR` |  | `k8s/` | K8S_MANIFESTS_DIR |
| `IMAGE_TAG` |  | | Tag de la imagen (vacío = latest) |
| `DEPLOY_METHOD` |  | `kustomize` | kustomize, helm o manifest |

| Secret | Req. | Descripción |
|:---|:---:|:---|
| `KUBE_CONFIG` | ✅ | kubeconfig en base64 |

### `k8s-preview-environments.yml`
**K8S Preview Environments** — Entorno efímero por Pull Request (namespace | argocd | vcluster) con ResourceQuota FinOps y NetworkPolicy. Úsalo desde un workflow con `on: pull_request: types: [opened, synchronize, reopened, closed]`: PREVIEW_ACTION=auto despliega en opened/synchronize/reopened y destruye en closed.

| Input | Req. | Default | Descripción |
|:---|:---:|:---|:---|
| `PREVIEW_ACTION` |  | `auto` | auto \| deploy \| stop |
| `SERVICE_NAME` |  | `app` | Nombre del servicio (monorepo) |
| `SERVICE_PATH` |  | `.` | Directorio del servicio (para el modo argocd: <path>/k8s) |
| `PREVIEW_BASE_DOMAIN` |  | `preview.example.com` | Dominio base de las URLs efímeras |
| `PREVIEW_NAMESPACE_PREFIX` |  | `preview-pr` | Prefijo del namespace |
| `PREVIEW_ISOLATION_MODE` |  | `namespace` | namespace \| argocd \| vcluster |

| Secret | Req. | Descripción |
|:---|:---:|:---|
| `KUBE_CONFIG` | ✅ | kubeconfig en base64 |

### `k8s-rollback.yml`
**K8S Rollback**

| Input | Req. | Default | Descripción |
|:---|:---:|:---|:---|
| `ROLLBACK_DISABLED` |  | `false` | ROLLBACK_DISABLED |
| `K8S_NAMESPACE` |  | | K8S_NAMESPACE |
| `ROLLBACK_DEPLOYMENT` |  | | ROLLBACK_DEPLOYMENT |
| `ROLLBACK_REVISION` |  | | ROLLBACK_REVISION |
| `ROLLBACK_VERIFY` |  | `true` | ROLLBACK_VERIFY |
| `ROLLBACK_VERIFY_TIMEOUT` |  | `120` | ROLLBACK_VERIFY_TIMEOUT |

| Secret | Req. | Descripción |
|:---|:---:|:---|
| `KUBECONFIG_CONTENT` |  | kubeconfig en base64 |
| `KUBE_URL` |  | URL del API server (alternativa a kubeconfig) |
| `KUBE_TOKEN` |  | Token de ServiceAccount (alternativa a kubeconfig) |

### `k8s-scale.yml`
**K8S Scale (GitOps)** — Apaga (replicas: 1 -> 0) o enciende (replicas: 0 -> 1) todos los servicios de un directorio del repo de infraestructura GitOps. Se publica un resumen (release_info.yml) usable por utilities-notifications.

| Input | Req. | Default | Descripción |
|:---|:---:|:---|:---|
| `ACTION` | ✅ | | down (1 -> 0) \| up (0 -> 1) |
| `INFRA_REPO` | ✅ | | Repo de infraestructura (owner/repo) |
| `TARGET_PATH` | ✅ | | Directorio dentro del repo de infraestructura (ej. idp/k8s/DEV) |
| `INFRA_BRANCH` |  | `main` | Rama del repo de infraestructura |

| Secret | Req. | Descripción |
|:---|:---:|:---|
| `INFRA_REPO_TOKEN` | ✅ | PAT/fine-grained token con contents:write sobre el repo de infraestructura |

### `libraries-maven-lib.yml`
**Libraries Maven Lib**

| Input | Req. | Default | Descripción |
|:---|:---:|:---|:---|
| `JAVA_VERSION` |  | `17` | Versión de JDK (Temurin) |
| `MAVEN_OPTS` |  | `-Dorg.slf4j.simpleLogger.log.level=warn` | MAVEN_OPTS |
| `MAVEN_CLI_OPTS` |  | `--batch-mode --errors --fail-at-end --show-version` | Flags de Maven |
| `DEPLOY` |  | `True` | Publicar en GitHub Packages (solo en ramas main/stg/dev/qa y tags) |
| `TEMPLATE_PROJECT` |  | `grs89/github-template` | Repo de plantillas con .github/utilidades/generate_report.py |

### `observability-api-contract-tests.yml`
**Observability Api Contract Tests**

| Input | Req. | Default | Descripción |
|:---|:---:|:---|:---|
| `CONTRACT_DISABLED` |  | `false` | CONTRACT_DISABLED |
| `API_SPEC_PATH` |  | | API_SPEC_PATH |
| `API_SPEC_URL` |  | | API_SPEC_URL |
| `API_BASE_URL` |  | | API_BASE_URL |
| `CONTRACT_FAIL_ON_ERROR` |  | `false` | CONTRACT_FAIL_ON_ERROR |
| `SPECTRAL_RULESET` |  | | SPECTRAL_RULESET |

### `observability-chaos-testing.yml`
**Observability Chaos Testing** — Chaos Mesh (PodChaos) sobre el servicio preview mientras se sondea /healthz; falla si no es resiliente. Requiere Chaos Mesh instalado en el clúster y un Service <app>-preview.

| Input | Req. | Default | Descripción |
|:---|:---:|:---|:---|
| `CHAOS_ENABLED` |  | `false` | true para ejecutar el experimento |
| `CHAOS_DURATION_SECONDS` |  | `60` | Duración del experimento |
| `APP_NAME` |  | | Nombre de la app (vacío = nombre del repo) |
| `K8S_NAMESPACE` |  | `default` | Namespace del servicio preview |
| `CHAOS_MAX_FAILURES` |  | `3` | Fallos tolerados bajo caos antes de abortar |
| `TEMPLATE_PROJECT` |  | `grs89/github-template` | Repo de plantillas con k8s/chaos-mesh-pod.yml |
| `TEMPLATE_REF` |  | `main` | Rama o tag del repo de plantillas |

| Secret | Req. | Descripción |
|:---|:---:|:---|
| `KUBE_CONFIG` | ✅ | kubeconfig en base64 |

### `observability-dora-metrics.yml`
**Observability DORA Metrics** — Registra eventos DORA (deployment, deployment_recovery/MTTR, ...) en un colector central. Para MTTR: dispara este workflow con repository_dispatch (type: deployment-recovery) desde el webhook de ArgoCD.

| Input | Req. | Default | Descripción |
|:---|:---:|:---|:---|
| `DORA_COLLECTOR_URL` | ✅ | | URL del colector DORA (POST JSON) |
| `DORA_EVENT` |  | `deployment_recovery` | Tipo de evento: deployment \| deployment_recovery \| deployment_failure |
| `DORA_ENV` |  | `production` | Entorno afectado |

| Secret | Req. | Descripción |
|:---|:---:|:---|
| `DORA_API_TOKEN` |  | Bearer token del colector |

### `observability-grafana-annotations.yml`
**Observability Grafana Annotations**

| Input | Req. | Default | Descripción |
|:---|:---:|:---|:---|
| `GRAFANA_DISABLED` |  | `false` | GRAFANA_DISABLED |
| `GRAFANA_URL` |  | | GRAFANA_URL |
| `GRAFANA_DASHBOARD_ID` |  | | GRAFANA_DASHBOARD_ID |
| `GRAFANA_TAGS` |  | `deploy,ci` | GRAFANA_TAGS |
| `GRAFANA_TEXT` |  | | GRAFANA_TEXT |
| `IMAGE_TAG` |  | | Tag de la imagen desplegada (informativo) |

| Secret | Req. | Descripción |
|:---|:---:|:---|
| `GRAFANA_API_KEY` |  |  |

### `observability-otel-pipeline-traces.yml`
**Observability OTel Pipeline Traces** — Exporta el run de GitHub Actions (jobs y steps, incluyendo workflows reutilizables) como trazas OTLP hacia Grafana Tempo / Jaeger / OTel Collector. No bloqueante. Ejecútalo como último job (needs: [...] + if: always()).

| Input | Req. | Default | Descripción |
|:---|:---:|:---|:---|
| `OTEL_COLLECTOR_URL` |  | | Endpoint OTLP/HTTP (ej. http://otel-collector:4318); vacío = omite |
| `GRAFANA_URL` |  | | URL de Grafana para generar el enlace directo a la traza |
| `GRAFANA_TEMPO_DATASOURCE_NAME` |  | `Tempo` | Nombre del datasource de Tempo en Grafana |
| `TEMPLATE_PROJECT` |  | `grs89/github-template` | Repo de plantillas que contiene scripts/export_otel_traces.py |
| `TEMPLATE_REF` |  | `main` | Rama o tag del repo de plantillas |

| Secret | Req. | Descripción |
|:---|:---:|:---|
| `OTEL_AUTH_TOKEN` |  | Bearer token opcional del colector |

### `observability-otel-validate.yml`
**Observability Otel Validate**

| Input | Req. | Default | Descripción |
|:---|:---:|:---|:---|
| `OTEL_VALIDATE_DISABLED` |  | `false` | OTEL_VALIDATE_DISABLED |
| `OTEL_SERVICE_URL` |  | | OTEL_SERVICE_URL |
| `OTEL_COLLECTOR_URL` |  | | OTEL_COLLECTOR_URL |
| `OTEL_EXPECTED_SPANS` |  | | OTEL_EXPECTED_SPANS |
| `OTEL_EXPECTED_METRICS` |  | | OTEL_EXPECTED_METRICS |
| `OTEL_WAIT_SECONDS` |  | `15` | OTEL_WAIT_SECONDS |
| `OTEL_PROTOCOL` |  | `http` | OTEL_PROTOCOL |
| `OTEL_FAIL_ON_MISSING` |  | `true` | OTEL_FAIL_ON_MISSING |

### `observability-performance-tests.yml`
**Observability Performance Tests**

| Input | Req. | Default | Descripción |
|:---|:---:|:---|:---|
| `PERF_DISABLED` |  | `false` | PERF_DISABLED |
| `PERF_TARGET_URL` |  | | PERF_TARGET_URL |
| `PERF_DURATION` |  | `30s` | PERF_DURATION |
| `PERF_VUS` |  | `10` | PERF_VUS |
| `PERF_THRESHOLD_P95` |  | `500` | PERF_THRESHOLD_P95 |
| `PERF_THRESHOLD_ERROR_RATE` |  | `0.1` | PERF_THRESHOLD_ERROR_RATE |
| `PERF_SCRIPT` |  | | PERF_SCRIPT |
| `PERF_FAIL_ON_THRESHOLD` |  | `false` | PERF_FAIL_ON_THRESHOLD |

### `observability-score-exporter.yml`
**Observability Score Exporter** — Exporta a Prometheus Pushgateway el health score y las vulnerabilidades del reporte de seguridad consolidado.

| Input | Req. | Default | Descripción |
|:---|:---:|:---|:---|
| `PUSHGATEWAY_URL` |  | | URL de la Pushgateway (vacío = no exporta) |
| `DORA_ENV` |  | `production` | Etiqueta env de las métricas |
| `REPORTS_ARTIFACT_PATTERN` |  | `*report*` | Patrón del artefacto que contiene security-report.json |
| `TEMPLATE_PROJECT` |  | `grs89/github-template` | Repo de plantillas que contiene scripts/export_metrics.py |
| `TEMPLATE_REF` |  | `main` | Rama o tag del repo de plantillas |

### `observability-smoke-tests.yml`
**Observability Smoke Tests**

| Input | Req. | Default | Descripción |
|:---|:---:|:---|:---|
| `SMOKE_DISABLED` |  | `false` | SMOKE_DISABLED |
| `SMOKE_ENDPOINTS` |  | | SMOKE_ENDPOINTS |
| `SMOKE_TIMEOUT` |  | `10` | SMOKE_TIMEOUT |
| `SMOKE_RETRIES` |  | `3` | SMOKE_RETRIES |
| `SMOKE_RETRY_DELAY` |  | `5` | SMOKE_RETRY_DELAY |
| `SMOKE_EXPECTED_STATUS` |  | `200` | SMOKE_EXPECTED_STATUS |
| `SMOKE_FAIL_ON_ERROR` |  | `false` | SMOKE_FAIL_ON_ERROR |

### `observability-uptime-kuma-alert.yml`
**Observability Uptime Kuma Alert**

| Input | Req. | Default | Descripción |
|:---|:---:|:---|:---|
| `UPTIME_KUMA_DISABLED` |  | `false` | UPTIME_KUMA_DISABLED |
| `UPTIME_KUMA_URL` |  | | UPTIME_KUMA_URL |
| `UPTIME_KUMA_MONITOR_NAME` |  | | UPTIME_KUMA_MONITOR_NAME |
| `UPTIME_KUMA_TARGET_URL` |  | | UPTIME_KUMA_TARGET_URL |
| `UPTIME_KUMA_MONITOR_TYPE` |  | `http` | UPTIME_KUMA_MONITOR_TYPE |
| `UPTIME_KUMA_INTERVAL` |  | `60` | UPTIME_KUMA_INTERVAL |
| `UPTIME_KUMA_ACTION` |  | `notify` | UPTIME_KUMA_ACTION |
| `UPTIME_KUMA_KEYWORD` |  | | UPTIME_KUMA_KEYWORD |
| `UPTIME_KUMA_NOTIFY_ON` |  | `deploy` | UPTIME_KUMA_NOTIFY_ON |

| Secret | Req. | Descripción |
|:---|:---:|:---|
| `UPTIME_KUMA_API_KEY` |  |  |

### `policies-policy-as-code.yml`
**Policies Policy-as-Code** — Valida manifiestos Kubernetes con Kyverno y planes de Terraform (JSON) con OPA/Rego.

| Input | Req. | Default | Descripción |
|:---|:---:|:---|:---|
| `PAC_DISABLED` |  | `false` | Deshabilitar Policy-as-Code |
| `PAC_ENFORCE_FAIL` |  | `true` | true = una violación falla el job; false = solo aviso (modo auditoría) |
| `PAC_SCAN_PATH` |  | `.` | Directorio a evaluar |
| `TEMPLATE_PROJECT` |  | `grs89/github-template` | Repo de plantillas con policies/ (si el repo no trae las suyas) |
| `TEMPLATE_REF` |  | `main` | Rama o tag del repo de plantillas |

### `quality-accessibility.yml`
**Quality Accessibility**

| Input | Req. | Default | Descripción |
|:---|:---:|:---|:---|
| `PA11Y_TARGET_URL` | ✅ | | URL a auditar con pa11y (WCAG 2) |
| `PA11Y_STANDARD` |  | `WCAG2AA` | Estándar pa11y (WCAG2A, WCAG2AA, WCAG2AAA) |

### `quality-ai-test-generator.yml`
**Quality AI Test Generator** — Genera suites de pruebas unitarias con un agente LLM (Strands) analizando el diff del Pull Request.

| Input | Req. | Default | Descripción |
|:---|:---:|:---|:---|
| `AI_TEST_GENERATOR_DISABLED` |  | `false` | true para desactivar |
| `AI_PROVIDER` | ✅ | | ollama, gemini, claude, openai, lm-studio |
| `AI_MODEL` | ✅ | | Modelo del proveedor |
| `AI_API_URL` |  | | Endpoint (ollama / lm-studio) |
| `AI_MAX_TURNS` |  | `20` | Máximo de turnos del agente |
| `AI_MAX_TOKENS` |  | `4096` | Máximo de tokens por respuesta |
| `SERVICE_PATH` |  | `.` | Directorio del servicio |
| `SERVICE_LANG` |  | `unknown` | Lenguaje del servicio (python, js, go, java, ...) |
| `TEMPLATE_PROJECT` |  | `grs89/github-template` | Repo de plantillas con scripts/ai_test_generator.py |
| `TEMPLATE_REF` |  | `main` | Rama o tag del repo de plantillas |

| Secret | Req. | Descripción |
|:---|:---:|:---|
| `AI_TOKEN` |  | API key del proveedor externo |

### `quality-code-quality.yml`
**Quality Code Quality** — Análisis de calidad de código con Code Climate (engines por lenguaje). Se omite si SonarQube está configurado.

| Input | Req. | Default | Descripción |
|:---|:---:|:---|:---|
| `CODE_QUALITY_DISABLED` |  | `false` | Deshabilitar el análisis |
| `CQ_SOURCE_PATH` |  | `.` | Directorio a analizar |
| `DETECTED_LANG` |  | | Lenguaje (python, js, ts, go, java*) para generar .codeclimate.yml |
| `SONAR_HOST_URL` |  | | Si está definido (SonarQube configurado) se omite Code Climate para evitar redundancia |

### `quality-lighthouse-check.yml`
**Quality Lighthouse Check**

| Input | Req. | Default | Descripción |
|:---|:---:|:---|:---|
| `LIGHTHOUSE_ENABLED` |  | `true` | Habilitar la auditoría Lighthouse |
| `LIGHTHOUSE_URL` | ✅ | | URL a auditar |
| `LIGHTHOUSE_EXTRA_ARGS` |  | | Argumentos extra para lighthouse |

### `quality-lint-argocd.yml`
**Quality Lint ArgoCD** — Linting y validación de manifiestos Kubernetes / ArgoCD: yamllint + kubeconform.

| Input | Req. | Default | Descripción |
|:---|:---:|:---|:---|
| `ARGOCD_MANIFEST_PATH` |  | `.` | Directorio con los manifiestos |
| `KUBERNETES_VERSION` |  | `1.30.0` | Versión de Kubernetes para validar esquemas |

### `quality-lint_templates.yml`
**Quality Lint Templates**

| Input | Req. | Default | Descripción |
|:---|:---:|:---|:---|
| `LINT_PATH` |  | `.` | Ruta a validar con yamllint |

### `quality-megalinter.yml`
**Quality MegaLinter** — Linter universal multi-lenguaje (MegaLinter).

| Input | Req. | Default | Descripción |
|:---|:---:|:---|:---|
| `MEGALINTER_FLAVOR` |  | `cupcake` | Flavor de MegaLinter (all, cupcake, python, javascript, java, go, terraform, ...) |
| `MEGALINTER_FAIL` |  | `False` | true = los hallazgos fallan el job; false = solo reporte |

### `sast-checkov.yml`
**SAST Checkov**

| Input | Req. | Default | Descripción |
|:---|:---:|:---|:---|
| `CHECK_DIR` |  | `.` | Directorio a escanear |
| `CHECKOV_FRAMEWORK` |  | `all` | Framework de Checkov (all, terraform, kubernetes, dockerfile, ...) |
| `CHECKOV_SOFT_FAIL` |  | `True` | No fallar el job al encontrar hallazgos |
| `UPLOAD_SARIF` |  | `False` | Publicar SARIF en GitHub Code Scanning (requiere GHAS o repo público) |

### `sast-sonarcube-scan_generic.yml`
**Sast Sonarcube Scan_Generic**

| Input | Req. | Default | Descripción |
|:---|:---:|:---|:---|
| `SONAR_HOST_URL` | ✅ | | SONAR_HOST_URL |
| `SONAR_PROJECT_KEY` |  | | SONAR_PROJECT_KEY |
| `SONAR_SOURCES` |  | | SONAR_SOURCES |
| `SONAR_EXCLUSIONS` |  | | SONAR_EXCLUSIONS |
| `SONAR_TESTS` |  | | SONAR_TESTS |
| `SONAR_TEST_INCLUSIONS` |  | | SONAR_TEST_INCLUSIONS |
| `SONAR_JAVA_BINARIES` |  | | SONAR_JAVA_BINARIES |
| `SONAR_JACOCO_REPORT_PATHS` |  | | SONAR_JACOCO_REPORT_PATHS |
| `SONAR_LCOV_REPORT_PATHS` |  | | SONAR_LCOV_REPORT_PATHS |
| `SONAR_COVERAGE_EXCLUSIONS` |  | | SONAR_COVERAGE_EXCLUSIONS |
| `SONAR_USE_PROJECT_PROPERTIES` |  | | SONAR_USE_PROJECT_PROPERTIES |

| Secret | Req. | Descripción |
|:---|:---:|:---|
| `SONAR_TOKEN` | ✅ |  |

### `sast-trivy-iac.yml`
**SAST Trivy IaC**

| Input | Req. | Default | Descripción |
|:---|:---:|:---|:---|
| `SCAN_PATH` |  | `.` | Ruta a escanear |
| `TRIVY_SEVERITY` |  | `HIGH,CRITICAL` | Severidades a reportar |
| `UPLOAD_SARIF` |  | `False` | Publicar SARIF en GitHub Code Scanning (requiere GHAS o repo público) |

### `security-ai-remediation.yml`
**Security AI Remediation** — Lee reportes SARIF / gl-sast-*.json de la corrida y publica sugerencias de corrección generadas por un LLM como comentarios de revisión (bloques `suggestion`) en el Pull Request.

| Input | Req. | Default | Descripción |
|:---|:---:|:---|:---|
| `AI_PROVIDER` |  | `ollama` | ollama, openai, lm-studio, gemini o claude |
| `AI_API_URL` |  | `http://ollama-service.local:11434` | URL del servidor LLM (ollama / lm-studio) |
| `AI_MODEL` |  | `codegemma` | Modelo a utilizar |
| `AI_MAX_SUGGESTIONS` |  | `10` | Máximo de sugerencias por corrida (acota el consumo de cuota del LLM) |
| `REPORTS_ARTIFACT_PATTERN` |  | `*report*` | Patrón de artefactos con reportes SARIF a analizar |
| `TEMPLATE_PROJECT` |  | `grs89/github-template` | Repo de plantillas que contiene scripts/ai_remediation.py |
| `TEMPLATE_REF` |  | `main` | Rama o tag del repo de plantillas |

| Secret | Req. | Descripción |
|:---|:---:|:---|
| `AI_TOKEN` |  | API key del proveedor LLM |

### `security-api-security.yml`
**Security API Security**

| Input | Req. | Default | Descripción |
|:---|:---:|:---|:---|
| `API_SEC_OPENAPI` | ✅ | | Ruta local o URL del spec OpenAPI |
| `API_SEC_TARGET_URL` | ✅ | | URL base de la API desplegada a escanear |
| `API_SEC_EXTRA_ARGS` |  | | Argumentos extra para zap-api-scan.py |

### `security-cluster-scanning.yml`
**Security Cluster Scanning**

| Input | Req. | Default | Descripción |
|:---|:---:|:---|:---|
| `CLUSTER_SCAN_NAMESPACE` |  | | Namespace a escanear (vacío = todo el clúster) |
| `TRIVY_SEVERITY` |  | `HIGH,CRITICAL` | Severidades a reportar |

| Secret | Req. | Descripción |
|:---|:---:|:---|
| `KUBE_CONFIG` | ✅ | kubeconfig codificado en base64 con acceso de lectura al clúster |

### `security-dast-scan.yml`
**Security DAST Scan**

| Input | Req. | Default | Descripción |
|:---|:---:|:---|:---|
| `DAST_DISABLED` |  | `false` | Deshabilitar el escaneo DAST |
| `DAST_TARGET_URL` | ✅ | | URL del ambiente a escanear (ej. https://staging.myapp.com) |
| `DAST_SCAN_TYPE` |  | `baseline` | baseline (pasivo), full (activo) o api |
| `DAST_API_SPEC` |  | | URL del spec OpenAPI (solo scan api; si está vacío se autodetecta) |
| `DAST_EXTRA_ARGS` |  | | Argumentos extra para el script de ZAP |

### `security-dast-zap.yml`
**Security DAST ZAP**

| Input | Req. | Default | Descripción |
|:---|:---:|:---|:---|
| `DAST_ZAP_DISABLED` |  | `false` | Deshabilitar el escaneo DAST ZAP |
| `DAST_ZAP_TARGET` |  | | URL objetivo (si está vacía se usa SITE_URL) |
| `SITE_URL` |  | | URL del sitio, usada si DAST_ZAP_TARGET está vacía |
| `DAST_ZAP_SCAN_TYPE` |  | `baseline` | baseline, full o api |
| `DAST_ZAP_EXTRA_ARGS` |  | | Argumentos extra para el script de ZAP |

### `security-defectdojo.yml`
**Security DefectDojo** — Sube a DefectDojo los reportes (SARIF, Trivy, Checkov, ZAP, Gitleaks) generados en la corrida.

| Input | Req. | Default | Descripción |
|:---|:---:|:---|:---|
| `DEFECTDOJO_URL` | ✅ | | URL base de DefectDojo |
| `DEFECTDOJO_PRODUCT` |  | | Producto (vacío = owner/repo) |
| `DEFECTDOJO_ENGAGEMENT` |  | | Engagement (vacío = Pipeline #<run> - Branch: <rama>) |
| `REPORTS_ARTIFACT_PATTERN` |  | `*report*` | Patrón de artefactos con reportes a subir |
| `TEMPLATE_PROJECT` |  | `grs89/github-template` | Repo de plantillas que contiene scripts/upload_defectdojo.py |
| `TEMPLATE_REF` |  | `main` | Rama o tag del repo de plantillas |

| Secret | Req. | Descripción |
|:---|:---:|:---|
| `DEFECTDOJO_TOKEN` | ✅ | API token de DefectDojo |

### `security-image-signing.yml`
**Security Image Signing** — Firma una imagen con Cosign (keyless, OIDC de GitHub / Sigstore) y verifica la firma resultante. Se firma por digest (image@sha256:...), nunca por tag mutable.

| Input | Req. | Default | Descripción |
|:---|:---:|:---|:---|
| `image` | ✅ | | Referencia con digest: ghcr.io/org/app@sha256:... |
| `registry` |  | `ghcr.io` | Registry para autenticar el push de la firma |

### `security-license-compliance.yml`
**Security License Compliance** — Audita las licencias de las dependencias (Node, Python; lista Go/Java para revisión manual) y bloquea licencias copyleft restrictivas.

| Input | Req. | Default | Descripción |
|:---|:---:|:---|:---|
| `LICENSE_DISABLED` |  | `false` | Deshabilitar la auditoría de licencias |
| `SERVICES` |  | `.` | Directorios a auditar separados por espacio (monorepo) |
| `LICENSE_ALLOWED` |  | `MIT,Apache-2.0,BSD-2-Clause,BSD-3-Clause,ISC,0BSD,Unlicense,CC0-1.0,WTFPL,Zlib,BlueOak-1.0.0,Python-2.0,PSF-2.0` | Licencias permitidas (SPDX, separadas por coma) |
| `LICENSE_BLOCKED` |  | `GPL-2.0,GPL-3.0,AGPL-3.0,LGPL-2.1,LGPL-3.0,SSPL-1.0,EUPL-1.1,EUPL-1.2` | Licencias bloqueadas (SPDX, separadas por coma) |
| `LICENSE_FAIL_ON_BLOCKED` |  | `true` | true = falla el job con licencias bloqueadas; false = solo aviso |
| `LICENSE_REPORT_FILE` |  | `license-report.json` | Nombre del reporte JSON |

### `security-llm-security.yml`
**Security LLM Security**

| Input | Req. | Default | Descripción |
|:---|:---:|:---|:---|
| `SERVICE_PATH` |  | `.` | Directorio del servicio |
| `SERVICE_NAME` |  | | Nombre del servicio |
| `LLM_PROVIDER` |  | `openai` | Proveedor LLM (openai, anthropic, gemini, ollama) |
| `LLM_MODEL` |  | `gpt-4o-mini` | Modelo LLM |
| `LLM_ENDPOINT` |  | | Endpoint HTTP del LLM para red-teaming |
| `LLM_SCAN_DISABLED` |  | `False` | Desactivar escaneos de LLM |

| Secret | Req. | Descripción |
|:---|:---:|:---|
| `LLM_API_KEY` |  |  |
| `OPENAI_API_KEY` |  |  |
| `ANTHROPIC_API_KEY` |  |  |
| `GEMINI_API_KEY` |  |  |

### `security-sbom.yml`
**Security SBOM** — Genera el SBOM (CycloneDX) de una imagen de contenedor o del código fuente, y opcionalmente lo atesta.

| Input | Req. | Default | Descripción |
|:---|:---:|:---|:---|
| `image` |  | | Imagen a inventariar (ej. ghcr.io/org/app:tag). Vacío = escanear el código fuente |
| `registry` |  | `ghcr.io` | Registry para autenticar el pull de la imagen |
| `attest` |  | `False` | Adjuntar el SBOM como atestación firmada (requiere image con digest, ej. image@sha256:...) |

### `security-slsa-provenance.yml`
**Security SLSA Provenance** — Atestación de procedencia SLSA (build provenance firmada con Sigstore) para una imagen ya publicada.

| Input | Req. | Default | Descripción |
|:---|:---:|:---|:---|
| `subject-name` | ✅ | | Nombre de la imagen sin tag ni digest (ej. ghcr.io/org/app) |
| `subject-digest` | ✅ | | Digest de la imagen (sha256:...) |

### `security-strix-pentest.yml`
**Security Strix Pentest** — 🦉 Pentesting agéntico con IA (Strix): agentes autónomos ejecutan la aplicación, encadenan exploits y los validan con PoC real. Strix levanta su sandbox en Docker (disponible en ubuntu-latest). Consume tokens de LLM: úsalo manualmente o en ramas protegidas, con STRIX_MAX_BUDGET acotado.

| Input | Req. | Default | Descripción |
|:---|:---:|:---|:---|
| `STRIX_DISABLED` |  | `false` | true para desactivar el job |
| `STRIX_SCAN_MODE` |  | `standard` | quick \| standard \| deep |
| `STRIX_MAX_BUDGET` |  | `15` | Techo de gasto por scan en USD |
| `STRIX_FAIL_ON` |  | | Vacío \| low \| medium \| high \| critical (falla con hallazgos de esa severidad o mayor) |
| `STRIX_TARGET` |  | | Ruta o URL a escanear (vacío = SERVICE_PATH) |
| `STRIX_VERSION` |  | `1.7.0` | Versión de strix-agent en PyPI |
| `SERVICE_PATH` |  | `.` | Directorio del servicio (monorepo) |
| `SERVICE_NAME` |  | | Nombre del servicio (para nombrar artefactos) |
| `AI_PROVIDER` | ✅ | | ollama, lmstudio, vllm, local, gemini, claude, openai, ... |
| `AI_MODEL` | ✅ | | Modelo del proveedor |
| `AI_API_URL` |  | | Endpoint (solo proveedores locales) |
| `SECURITY_FAIL_ON_FINDINGS` |  | `true` | true = hallazgos de SECURITY_FAIL_SEVERITY bloquean el job; false = solo aviso |
| `SECURITY_FAIL_SEVERITY` |  | `CRITICAL` | Severidades que bloquean (separadas por coma) |

| Secret | Req. | Descripción |
|:---|:---:|:---|
| `AI_TOKEN` |  | API key del proveedor externo |

### `shared-build-push.yml`
**Shared Build & Push**

| Input | Req. | Default | Descripción |
|:---|:---:|:---|:---|
| `DETECTED_LANG` |  | `unknown` |  |
| `IMAGE_TAG` |  | |  |
| `REPO_LC` |  | |  |
| `CONTEXT_DIR` |  | `.` |  |
| `SERVICE_NAME` |  | |  |
| `DOCKERFILE_PATH` |  | `Dockerfile` |  |
| `REGISTRY` |  | `ghcr.io` |  |
| `PLATFORMS` |  | `linux/amd64,linux/arm64` |  |
| `PUSH_TO_ECR` |  | `False` |  |
| `AWS_REGION` |  | `us-east-1` |  |

| Secret | Req. | Descripción |
|:---|:---:|:---|
| `GITHUB_TOKEN` |  |  |
| `DOCKERHUB_USERNAME` |  |  |
| `DOCKERHUB_TOKEN` |  |  |
| `AWS_ACCESS_KEY_ID` |  |  |
| `AWS_SECRET_ACCESS_KEY` |  |  |
| `ECR_REGISTRY` |  |  |
| `COSIGN_PRIVATE_KEY` |  |  |
| `COSIGN_PASSWORD` |  |  |

### `shared-lint-test.yml`
**Shared Lint & Test**

| Input | Req. | Default | Descripción |
|:---|:---:|:---|:---|
| `DETECTED_LANG` | ✅ | | Lenguaje detectado del proyecto |
| `CONTEXT_DIR` | ✅ | | Directorio del contexto |

### `shared-security-scan.yml`
**Shared Security Scan**

| Input | Req. | Default | Descripción |
|:---|:---:|:---|:---|
| `CONTEXT_DIR` | ✅ | |  |
| `IMAGE_TAG` |  | | Tag de la imagen ya publicada (vacío = se omiten los escaneos de imagen y DAST) |
| `REPO_LC` |  | |  |
| `REGISTRY` |  | `ghcr.io` |  |
| `SITE_URL` |  | |  |
| `DETECTED_LANG` |  | `unknown` |  |

| Secret | Req. | Descripción |
|:---|:---:|:---|
| `REGISTRY_USER` |  |  |
| `REGISTRY_PASSWORD` |  |  |
| `DOCKERHUB_USERNAME` |  |  |
| `DOCKERHUB_TOKEN` |  |  |
| `DOCKERHUB_REPO` |  |  |
| `SITE_URL` |  |  |

### `shared-wiki-sync.yml`
**Shared Wiki Sync**

| Input | Req. | Default | Descripción |
|:---|:---:|:---|:---|
| `WIKI_DIR` |  | `01-wiki` | Directorio que contiene los archivos de la Wiki (.md) |
| `DRY_RUN` |  | `False` | Si es true, solo simula el proceso sin subir los cambios |

| Secret | Req. | Descripción |
|:---|:---:|:---|
| `WIKI_TOKEN` |  | Token de acceso personalizado (PAT) con permisos de escritura. Si no se provee, se usará el GITHUB_TOKEN por defecto |

### `test-fuzz-testing.yml`
**Test Fuzz Testing** — Fuzzing por ecosistema: Go (go test -fuzz) y Python (Hypothesis). Pensado para ejecuciones programadas (schedule).

| Input | Req. | Default | Descripción |
|:---|:---:|:---|:---|
| `SERVICE_PATH` |  | `.` | Directorio del servicio |
| `FUZZ_TIME_LIMIT` |  | `5m` | Límite de fuzzing por target (ej. 5m) |

### `test-mutation-testing.yml`
**Test Mutation Testing** — Mutation testing por ecosistema: Go (go-mutesting), JS (Stryker), Python (mutmut), Java (PITest). Informativo: mutantes sobrevivientes generan un aviso, no rompen el pipeline.

| Input | Req. | Default | Descripción |
|:---|:---:|:---|:---|
| `SERVICE_PATH` |  | `.` | Directorio del servicio |
| `MUTATION_FAIL` |  | `False` | true = mutantes sobrevivientes/herramienta fallida falla el job |

### `test-playwright-e2e.yml`
**Test Playwright E2E**

| Input | Req. | Default | Descripción |
|:---|:---:|:---|:---|
| `PLAYWRIGHT_DISABLED` |  | `false` | PLAYWRIGHT_DISABLED |
| `PLAYWRIGHT_BASE_URL` |  | | PLAYWRIGHT_BASE_URL |
| `PLAYWRIGHT_BROWSER` |  | `chromium` | PLAYWRIGHT_BROWSER |
| `PLAYWRIGHT_WORKERS` |  | `2` | PLAYWRIGHT_WORKERS |
| `PLAYWRIGHT_RETRIES` |  | `1` | PLAYWRIGHT_RETRIES |
| `PLAYWRIGHT_TIMEOUT` |  | `30000` | PLAYWRIGHT_TIMEOUT |
| `PLAYWRIGHT_REPORT_DIR` |  | `playwright-report` | PLAYWRIGHT_REPORT_DIR |
| `PLAYWRIGHT_SCREENSHOT` |  | `only-on-failure` | PLAYWRIGHT_SCREENSHOT |
| `PLAYWRIGHT_VIDEO` |  | `retain-on-failure` | PLAYWRIGHT_VIDEO |

### `utilities-ai-release-notes.yml`
**Utilities AI Release Notes** — Genera RELEASE_NOTES.md categorizado con un agente LLM (Strands) al publicar un tag.

| Input | Req. | Default | Descripción |
|:---|:---:|:---|:---|
| `AI_PROVIDER` | ✅ | | ollama, gemini, claude, openai, lm-studio |
| `AI_MODEL` | ✅ | | Modelo del proveedor |
| `AI_API_URL` |  | | Endpoint (ollama / lm-studio) |
| `AI_MAX_TURNS` |  | `15` | Máximo de turnos del agente |
| `AI_MAX_TOKENS` |  | `4096` | Máximo de tokens por respuesta |
| `TEMPLATE_PROJECT` |  | `grs89/github-template` | Repo de plantillas con scripts/ai_release_notes.py |
| `TEMPLATE_REF` |  | `main` | Rama o tag del repo de plantillas |

| Secret | Req. | Descripción |
|:---|:---:|:---|
| `AI_TOKEN` |  | API key del proveedor externo |

### `utilities-badge-generator.yml`
**Utilities Badge Generator**

| Input | Req. | Default | Descripción |
|:---|:---:|:---|:---|
| `SERVICE_PATH` |  | `.` | Directorio del microservicio |
| `SERVICE_NAME` |  | | Nombre del microservicio |
| `BADGE_DISABLED` |  | `False` | Desactivar generación de insignias |
| `BADGE_STYLE` |  | `for-the-badge` | Estilo visual de shields.io |
| `BADGE_AUTO_UPDATE_README` |  | `True` | Actualizar README.md automáticamente |

| Secret | Req. | Descripción |
|:---|:---:|:---|
| `GITHUB_TOKEN` |  |  |

### `utilities-changelog.yml`
**Utilities Changelog** — Genera CHANGELOG.md (o changelog.json) con git-cliff a partir de commits convencionales.

| Input | Req. | Default | Descripción |
|:---|:---:|:---|:---|
| `CHANGELOG_DISABLED` |  | `false` | Deshabilitar la generación |
| `CHANGELOG_FORMAT` |  | `markdown` | markdown \| json |
| `CHANGELOG_FILE` |  | `CHANGELOG.md` | Archivo de salida (markdown) |
| `CHANGELOG_RANGE` |  | | Rango de commits de git-cliff (vacío = todo el historial) |
| `CHANGELOG_COMMIT_PUSH` |  | `True` | Commitear el changelog a la rama (requiere permisos de escritura) |

### `utilities-cleanup-ghcr.yml`
**Utilities Cleanup GHCR**

| Input | Req. | Default | Descripción |
|:---|:---:|:---|:---|
| `CLEANUP_DISABLED` |  | `False` | Desactivar limpieza del container registry |
| `CLEANUP_KEEP_LATEST` |  | `10` | Número de tags/versiones recientes a conservar |
| `CLEANUP_OLDER_THAN_DAYS` |  | `30` | Umbral de antigüedad en días |
| `CLEANUP_DRY_RUN` |  | `False` | Modo simulación (sin borrado real) |

| Secret | Req. | Descripción |
|:---|:---:|:---|
| `GITHUB_TOKEN` |  |  |

### `utilities-dependency-update.yml`
**Utilities Dependency Update**

| Input | Req. | Default | Descripción |
|:---|:---:|:---|:---|
| `DEPUPDATE_DISABLED` |  | `false` | Deshabilitar el chequeo |
| `SERVICE_PATH` |  | `.` | Servicio (monorepo); '.' autodetecta servicios con Dockerfile |
| `SECURITY_FAIL_ON_FINDINGS` |  | `true` | true = una vulnerabilidad conocida bloquea el job |

### `utilities-mr-description.yml`
**Utilities PR Description** — Genera/actualiza una sección automática en la descripción del Pull Request con los commits agrupados por tipo (conventional commits), estadísticas, checklist y labels. El texto escrito por la persona autora se conserva: solo se reemplaza el bloque entre los marcadores.

| Input | Req. | Default | Descripción |
|:---|:---:|:---|:---|
| `MR_DESC_DISABLED` |  | `false` | Deshabilitar el generador |
| `MR_DESC_MAX_COMMITS` |  | `50` | Máximo de commits a listar |
| `MR_DESC_ADD_STATS` |  | `true` | Agregar tabla de estadísticas |
| `MR_DESC_ADD_CHECKLIST` |  | `true` | Agregar checklist de revisión |
| `MR_DESC_AUTO_LABEL` |  | `true` | Asignar labels automáticos (feature, bugfix, size/*) |

### `utilities-notifications.yml`
**Utilities Notifications** — Notifica a Google Chat el resultado del pipeline (con resumen de release/componentes si existen). Úsalo como último job: needs: [...] y if: always(), pasando STATUS: ${{ needs.<job>.result }}.

| Input | Req. | Default | Descripción |
|:---|:---:|:---|:---|
| `STATUS` |  | `success` | success \| failure (cualquier otro valor se trata como failure) |
| `NOTIFY_ONLY_ON_TAGS_SUCCESS` |  | `True` | true = en éxito solo notifica en tags (los fallos siempre notifican) |
| `RELEASE_ARTIFACT` |  | | Artefacto con release_info.yml (opcional) |
| `RELEASE_FILE` |  | `release_info.yml` | Archivo de release dentro del artefacto |
| `COMPONENT_ARTIFACT` |  | | Artefacto con component.yml (opcional) |
| `COMPONENT_FILE` |  | `component.yml` | Archivo de componentes dentro del artefacto |

| Secret | Req. | Descripción |
|:---|:---:|:---|
| `GOOGLE_CHAT_WEBHOOK` |  | Webhook de Google Chat |

### `utilities-release.yml`
**Utilities Release** — Crea o actualiza el GitHub Release de un tag usando RELEASE_NOTES.md (IA) o la sección del CHANGELOG.md.

| Input | Req. | Default | Descripción |
|:---|:---:|:---|:---|
| `TAG` |  | | Tag a publicar (vacío = ref actual, debe ser un tag) |
| `RELEASE_NOTES_ARTIFACT` |  | | Artefacto con RELEASE_NOTES.md (ej. release-notes) — opcional |
| `CHANGELOG_ARTIFACT` |  | | Artefacto con CHANGELOG.md (ej. changelog) — opcional |
| `PRERELEASE` |  | `False` | Marcar como pre-release |

### `utilities-renovate.yml`
**Utilities Renovate** — Renovate self-hosted: mantiene al día imágenes de contenedor y dependencias abriendo Pull Requests (sin automerge). Úsalo con schedule/workflow_dispatch. Si prefieres la GitHub App oficial de Renovate, no necesitas este workflow. El preset compartido vive en renovate.json de este repo: { "extends": ["github>grs89/github-template"] }

| Input | Req. | Default | Descripción |
|:---|:---:|:---|:---|
| `RENOVATE_ENABLED` |  | `true` | false para desactivarlo en un proyecto |
| `RENOVATE_IMAGE` |  | `renovate/renovate:44` | Imagen de Renovate |
| `RENOVATE_LOG_LEVEL` |  | `info` | Nivel de log |
| `RENOVATE_DRY_RUN` |  | | Simulación (extract \| lookup \| full); vacío = ejecución real |

| Secret | Req. | Descripción |
|:---|:---:|:---|
| `RENOVATE_TOKEN` |  | PAT / token de GitHub App con contents + pull-requests (GITHUB_TOKEN no dispara checks en los PRs que crea) |

### `utilities-roadmap-sync.yml`
**Utilities Roadmap Sync** — Sincroniza ROADMAP.md con Milestones e Issues de GitHub (idempotente: crea/actualiza/cierra).

| Input | Req. | Default | Descripción |
|:---|:---:|:---|:---|
| `ROADMAP_FILE` |  | `ROADMAP.md` | Ruta del ROADMAP.md |
| `DRY_RUN` |  | `False` | Simular sin escribir en GitHub |
| `TEMPLATE_PROJECT` |  | `grs89/github-template` | Repo de plantillas con scripts/sync_roadmap_milestones.py |
| `TEMPLATE_REF` |  | `main` | Rama o tag del repo de plantillas |

### `utilities-semantic-release.yml`
**Utilities Semantic Release**

| Input | Req. | Default | Descripción |
|:---|:---:|:---|:---|
| `SEMANTIC_RELEASE_DISABLED` |  | `false` | SEMANTIC_RELEASE_DISABLED |

## Workflows propios del repositorio (no reutilizables)

| Archivo | Nombre |
|:---|:---|
| `docker-brk.yml` | 🐳 Docker BRK (BuildKit Premium) |
| `docker-dnd.yml` | 📦 Docker DnD (Standard Dind) |
| `docker-matrix.yml` | 🧩 Docker Matrix (BuildKit + Matrix) |
| `pull-request-validation.yml` | ⚡ PR Validation (CI) |
| `template-ci.yml` | Template CI |
| `wiki-publish.yml` | Publish Wiki |
