# Instalación y Configuración 🛠️ (GitHub Actions)

La inclusión de las plantillas en tu repositorio de GitHub se realiza mediante un archivo de workflow en `.github/workflows/ci-cd.yml`.

---

## 🚀 Paso a Paso: Incluir la Plantilla

### Opción A: Inicializador Dinámico (Recomendado)
Para cualquier proyecto. Detectará automáticamente la tecnología del repositorio (Microservicio App con Dockerfile, Infraestructura Terraform, Librería Java con Maven o Ansible) y ejecutará los flujos correspondientes en paralelo:

Crea el archivo `.github/workflows/ci-cd.yml` en tu repositorio:

```yaml
name: CI/CD DevSecOps Pipeline

on:
  push:
    branches: [main, master, dev, development, stg, staging, qa]
    tags: ['v*']
  pull_request:
    branches: [main, master, dev, development, stg, staging, qa]
  schedule:
    - cron: '0 0 * * *'
  workflow_dispatch:

jobs:
  pipeline:
    uses: grs89/github-template/.github/workflows/03-start-init.yml@main
    secrets: inherit
```

---

### Opción B: Inclusión Directa de Microservicio
Si deseas ejecutar directamente el ciclo de un microservicio sin enrutador dinámico:

```yaml
name: App Pipeline

on:
  push:
    branches: [main, dev, stg]

jobs:
  app:
    uses: grs89/github-template/.github/workflows/03-start-docker-matrix-child.yml@main
    with:
      SERVICE_PATH: '.'
      SERVICE_NAME: 'mi-microservicio'
      SERVICE_LANG: 'python'
    secrets: inherit
```

---

### Opción C: Infraestructura con Terraform
Para repositorios de infraestructura gestionados con Terraform:

```yaml
name: IaC Pipeline

on:
  push:
    branches: [main, dev, stg]
  pull_request:
    branches: [main]

jobs:
  iac:
    uses: grs89/github-template/.github/workflows/03-start-iac.yml@main
    with:
      TF_ROOT: '.'
    secrets: inherit
```
