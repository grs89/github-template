# 🔐 Estándares de Seguridad y Privacidad (DevSecOps)

La seguridad no es un paso posterior al despliegue, sino una política integrada ("Shift-Left") en el ADN de este pipeline de Integración y Entrega Continua. A continuación se documentan los estándares de protección y escaneo de vulnerabilidades.

## 1. Trivy (Escaneo de Software y Contenedores)

El pipeline integra Aqua Security **Trivy** en múltiples etapas del ciclo de vida del software.

### SAST (Static Application Security Testing)
Durante el CI, Trivy analiza el sistema de archivos (`fs scan`) para encontrar dependencias desactualizadas en tu lenguaje base (ej. `package-lock.json` o `go.mod` vulnerables) y credenciales en texto plano, interceptándolas antes del merge.

### Escaneo de Imagen (Container Scan)
Tras construir el contenedor, Trivy analiza la imagen binaria (`image scan`) comprobando vulnerabilidades en el SO base (ej. Alpine, Debian) y paquetes instalados vía `apt` o `apk`.

> [!NOTE]
> Sólo las vulnerabilidades de nivel `HIGH` y `CRITICAL` son reportadas y detenidas por defecto, para equilibrar la seguridad con la velocidad de desarrollo.

## 2. Checkov (Infraestructura como Código)

La configuración de infraestructura (IaC) es igual de susceptible a errores humanos.
- **Checkov** escanea el `Dockerfile` y, de existir, archivos de Terraform o manifiestos de Kubernetes en el repositorio.
- Comprueba el cumplimiento normativo contra buenas prácticas (ej. exigir `HEALTHCHECK`, prohibir ejecución de contenedores como usuario `root`).
- **Política de Soft Fail:** Checkov está configurado para ejecutarse en modo `soft_fail: true`. Esto significa que anotará sus hallazgos en el reporte PDF y en los registros, pero no abortará bruscamente el pipeline para no congelar las entregas ágiles.

## 3. Firmas Criptográficas (Sigstore Cosign)

Para certificar que el contenedor publicado proviene innegablemente de los repositorios y flujos oficiales aprobados, se utiliza **Cosign Keyless**.
- Al completar la subida de la imagen, GitHub Actions solicita un certificado OIDC a Sigstore vinculando de manera inmutable el `sha256` de la imagen con el usuario de GitHub y el ID de ejecución del pipeline.
- Se publica el anexo `.sig` directamente al registro contenedor.

## 4. SBOM y SLSA Nivel 3

El proyecto cumple nativamente con **SLSA Nivel 3** (Supply chain Levels for Software Artifacts):
- **Build Providence:** Se adjunta información rastreable de la procedencia (quién, qué y cuándo se compiló).
- **SBOM (Software Bill of Materials):** Se exporta un manifiesto en formato estándar `SPDX` de todos los subcomponentes contenidos dentro del empaquetado final, garantizando transparencia absoluta frente a los escáneres de ciberseguridad gubernamentales y corporativos.

## 5. Dependabot (Mantenimiento Continuo)

El archivo `.github/dependabot.yml` se incluye en la plantilla para revisar semanalmente:
1. Actualizaciones menores en las librerías nativas del lenguaje de tu aplicación (vía GitHub Package Manager).
2. Actualizaciones en los propios *Actions* de GitHub (ej. pasar de `actions/checkout@v3` a `v4`) evitando que el pipeline se vuelva obsoleto y se degrade silenciosamente.
