# 🔐 Estándares de Seguridad y Privacidad (DevSecOps)

La seguridad no es un paso posterior al despliegue, sino una política integrada ("Shift-Left") en el ADN de este pipeline de Integración y Entrega Continua. A continuación se documentan los estándares de protección, escaneo de vulnerabilidades y cumplimiento implementados en la plataforma.

---

## 1. Detección de Secretos en el Pipeline (Gitleaks)

Para prevenir la fuga accidental de credenciales, API keys, tokens de acceso o claves SSH, el pipeline integra **Gitleaks** de forma nativa en su etapa de validación (`shared-lint-test.yml`).
- **Análisis Pre-Merge/Push:** Escanea el repositorio completo en busca de patrones sensibles antes de compilar la imagen.
- **Reporte Descargable:** Genera un artefacto estructurado `gitleaks-report.json`.
- **Job DX:** Publica una alerta instantánea y un resumen Markdown directo en el **Github Step Summary** en caso de detectar posibles credenciales filtradas.

---

## 2. Trivy (SAST y Container Scanning)

El pipeline integra Aqua Security **Trivy** en múltiples etapas clave:
* **SAST (Static Application Security Testing):** Durante el CI, Trivy analiza el sistema de archivos (`fs scan`) para encontrar dependencias desactualizadas o librerías vulnerables (ej. `package-lock.json` o `go.mod`).
* **Escaneo de Imagen (Container Scan):** Tras construir la imagen del contenedor, Trivy analiza la imagen binaria (`image scan`) comprobando vulnerabilidades en el SO base (ej. Alpine, Debian) y paquetes instalados vía empaquetadores nativos.

> [!NOTE]
> Sólo las vulnerabilidades de nivel `HIGH` y `CRITICAL` son reportadas y catalogadas de forma estricta, lo que permite equilibrar la agilidad de desarrollo con la gobernanza de seguridad.

---

## 3. Auditorías Nativas de Dependencias del Lenguaje (SCA Nativo)

Complementando los escaneos generales de Trivy, el pipeline ejecuta auditorías nativas dinámicas según el lenguaje detectado para identificar vulnerabilidades específicas publicadas por los gestores de paquetes oficiales:
- **Go (`govulncheck`):** Evalúa la base de código del proyecto contra la base de datos de vulnerabilidades oficiales de Go (Go Vulnerability Database) generando reportes de flujo de ejecución detallados en formato NDJSON.
- **Node.js/JavaScript (`npm audit`):** Inspecciona el árbol de dependencias instalado en busca de brechas y exploits publicados en el registro público de npm.
- **Python (`pip-audit`):** Audita los paquetes instalados contra la base de datos de vulnerabilidades de PyPI de forma exhaustiva.
- **Política de Soft Fail (Tolerante):** Estas auditorías se ejecutan con `continue-on-error: true`. De este modo, los hallazgos son parseados e incluidos bajo la categoría **`SCA Nativo (npm/pip/govulncheck)`** en el reporte PDF y en el Step Summary, pero no bloquean la compilación principal.

---

## 4. Dynamic Application Security Testing (DAST) Ephemeral

Para cerrar la brecha entre el análisis estático y la seguridad en ejecución, el pipeline implementa **DAST Ephemeral con OWASP ZAP**:
- **Activación Condicional:** Se ejecuta únicamente si la variable o secreto de repositorio `SITE_URL` se encuentra configurada.
- **Entorno Aislado e Inteligente:** Levanta la imagen recién publicada de forma efímera en segundo plano (`docker run -d -P`), autodetecta su puerto de escucha HTTP, realiza una prueba de disponibilidad (health check) y corre el escáner.
- **OWASP ZAP Baseline Scan:** Escanea la aplicación local buscando inyecciones SQL, XSS, cabeceras HTTP inseguras o cookies mal configuradas en tiempo de ejecución.
- **Bucle Completo:** Los hallazgos se integran automáticamente en `zap-report.json` para su posterior consolidación y el contenedor efímero es destruido de inmediato para no consumir recursos del runner.

---

## 5. Checkov (Infraestructura como Código - IaC)

La configuración de infraestructura en contenedores (IaC) es susceptible a errores humanos:
- **Checkov** escanea el `Dockerfile` y, de existir, manifiestos de Kubernetes o Terraform en el repositorio.
- Comprueba el cumplimiento normativo contra buenas prácticas (ej. exigir `HEALTHCHECK`, prohibir ejecución de contenedores como usuario `root`).
- **Política de Soft Fail:** Checkov está configurado con `soft_fail: true` para que los hallazgos se reporten en el PDF consolidado sin abortar bruscamente el pipeline, permitiendo un desarrollo continuo sin fricciones innecesarias.

---

## 6. Linter Estricto de Dockerfiles (Hadolint)

El pipeline integra el linter especializado **Hadolint** para asegurar que la construcción de contenedores Docker cumpla con las máximas directrices de seguridad de la industria:
- **Análisis de Capas Docker:** Hadolint audita sintáctica y estructuralmente cada instrucción de tus Dockerfiles de forma recursiva.
- **Bypass Inteligente:** El pipeline detecta la presencia de archivos `Dockerfile`. Si el proyecto no cuenta con contenedores, el job se omite de forma elegante evitando el consumo innecesario de recursos.
- **Detección Temprana de Riesgos:** Evita el uso de credenciales en instrucciones `ENV`, el uso de tags mutables como `latest`, y la ejecución de instaladores sin limpiar cachés. Los resultados se añaden al PDF final como **`Dockerfile Linter (Hadolint)`**.

---

## 7. Firmas Criptográficas (Sigstore Cosign)

Para certificar que el contenedor publicado proviene innegablemente de los repositorios y flujos oficiales aprobados de la organización, se realiza la firma digital con **Cosign**:
- **Cosign Keyless & Private Key:** Admite firmas mediante par de claves privadas (`COSIGN_PRIVATE_KEY`) o firmas sin llave (Keyless) basadas en OIDC de Sigstore vinculadas a la identidad segura del pipeline de GitHub Actions.
- Se publica el anexo `.sig` y la atestación directamente al registro del contenedor junto a la imagen.

---

## 8. Software Bill of Materials (SBOM) Firmado y Exportable

El proyecto cumple de forma nativa con los estándares más estrictos de seguridad de cadena de suministro de software (**SLSA Nivel 3**):
- **Generación CycloneDX:** Genera automáticamente el inventario de software completo (**SBOM**) en formato estándar **CycloneDX** utilizando Trivy.
- **Atestación Firmada:** Se registra y firma la atestación del SBOM en el registro del contenedor usando **Cosign** (`cosign attest`).
- **Manifiesto Descargable:** Adicionalmente, el archivo `sbom.json` se exporta como un artefacto descargable del workflow para auditorías rápidas de cumplimiento.

---

## 9. Dependabot (Mantenimiento Continuo)

El archivo `.github/dependabot.yml` se incluye en la plantilla para revisar semanalmente:
1. Actualizaciones en librerías nativas del lenguaje de tu aplicación (vía GitHub Package Manager).
2. Actualizaciones en los propios *Actions* de GitHub (ej. pasar de `actions/checkout@v3` a `v4`) evitando obsolescencia y fallos silenciosos.
