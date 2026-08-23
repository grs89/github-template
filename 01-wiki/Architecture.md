# 🏗️ Arquitectura y Diseño del Sistema CI/CD (GitHub Actions)

Nuestras plantillas implementan un ciclo **DevSecOps 360°** modular y escalable para **GitHub Actions**, soportando tanto proyectos monolíticos como **Monorepos políglotas** complejos con compilación paralela y GitOps declarativo.

---

## 1. Patrón Orquestador y Matriz Dinámica (`03-start-init.yml`)

En lugar de crear archivos `.github/workflows/` duplicados en cada repositorio, los proyectos clientes importan un único punto de entrada:

```mermaid
graph TD
    Parent["👑 Orquestador Inicial (03-start-init.yml)"] --> Gen["🔍 detect_matrix<br/>(Escanea Dockerfiles, TF, Maven, Ansible)"]
    Gen --> Matrix["⚡ Matriz Paralela de Disparo"]
    Matrix --> Child1["👶 App 1: backend/<br/>(Python SAST + Build + Trivy + LLM Scan)"]
    Matrix --> Child2["👶 App 2: frontend/<br/>(JS SAST + Build + Trivy + DAST)"]
    Matrix --> Child3["👶 App 3: services/auth/<br/>(Go SAST + Build + Trivy + Cosign)"]
```

### Ventajas del diseño:
- **Aislamiento Total:** Si un microservicio falla sus pruebas unitarias, los demás continúan su ciclo de compilación y despliegue sin bloquearse.
- **Ejecución Paralela:** Todos los microservicios se compilan y escanean al mismo tiempo en runners independientes.
- **Especialización por Lenguaje:** El runner de Python ejecuta `pytest`/`pip-audit` y el runner de Node.js ejecuta `npm test`/`npm audit`.

---

## 2. Flujo Completo DevSecOps 360° en Contenedores

```mermaid
graph TD
    A([Inicio de Pipeline]) --> B(🕵️ Detección de Lenguaje)
    B --> C{Tiene Dockerfile?}
    C -- Sí --> D[🏗️ Docker Buildx GHA Cache]
    C -- No --> E[⏭️ Saltar Build]
    
    D --> F[💾 Caché en GitHub Actions]
    D --> G[📦 Push a GHCR / DockerHub]
    G --> H(🔐 Firmado con Cosign Keyless)
    G --> I(🛡️ Container Scanning - Trivy)
    I --> J(🌐 DAST - OWASP ZAP)
    J --> K(🔑 API Security Scan)
    K --> L{Deploy GitOps?}
    L -- Sí --> M[🚀 GitOps Deploy Agnostico]
    M --> N[🧪 Smoke & Perf Tests]
    N --> O{Verificación OK?}
    O -- No --> P[⏪ Auto-Rollback Git Revert]
    O -- Sí --> Q[✅ Promote to Stable]
    Q --> R(📄 Dashboard PDF/HTML)
```

---

## 3. Orquestadores y Puntos de Entrada

| Orquestador | Arquitectura | Motor Docker | Caso de Uso Ideal |
| :--- | :--- | :--- | :--- |
| **`03-start-init.yml`** | Enrutador Dinámico | N/A | **Cualquier proyecto**. Punto de entrada recomendado para delegar el descubrimiento a la lógica del pipeline. |
| **`03-start-docker-matrix-child.yml`** | Reusable Workflow | Docker BuildKit (Buildx) | Pipeline secundario de microservicios contenedorizados. |
| **`03-start-iac.yml`** | Especialidad Terraform | N/A | Repositorios de infraestructura gestionados con Terraform y FinOps (Infracost). |
| **`infrastructure-ansible.yml`** | Especialidad Ansible | N/A | Automatización de configuración y playbooks de Ansible. |
| **`libraries-maven-lib.yml`** | Especialidad Java | N/A | Librerías compartidas Java/Maven con escaneo y publicación a GitHub Packages. |
| **`k8s-gitops.yml`** | Especialidad GitOps | N/A | Validación de manifiestos YAML y esquemas K8s. |
