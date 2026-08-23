# 🛡️ Seguridad y Privacidad (DevSecOps 360° en GitHub Actions)

Este documento describe el modelo de seguridad integral implementado en `github-template` para mitigar riesgos de vulnerabilidades, fuga de credenciales, riesgos de IA y ataques a la cadena de suministro.

---

## 1. Escaneo Estático (SAST) y Secretos
- **Gitleaks:** Escaneo estricto de commits previos y nuevos para prevenir que credenciales, tokens o llaves SSH ingresen al repositorio.
- **Trivy SAST & Semgrep:** Análisis estático de código fuente con detección de inyecciones SQL, XSS y vulnerabilidades lógicas.
- **Hadolint:** Validación de seguridad en Dockerfiles para evitar ejecutar como root o usar imágenes no fijadas.

---

## 2. Seguridad en Inteligencia Artificial (OWASP LLM Top 10)
- **Reglas Semgrep LLM:** Detección de concatenación insegura de entradas de usuario en prompts (`LLM01`), exposición de API keys (`LLM02`), ejecución directa de respuestas de LLM sin sanitizar (`LLM05`) y llamadas sin límite de tokens (`LLM10`).
- **Auditoría de Librerías IA:** Escaneo de dependencias (`langchain`, `openai`, `transformers`) con `pip-audit` y `npm audit`.
- **Red-Teaming Dinámico con PromptFoo:** Pruebas dinámicas contra endpoints de IA evaluando resistencia ante fuga de instrucciones del sistema y jailbreaks.

---

## 3. Seguridad en Infraestructura como Código (IaC)
- **Checkov & Trivy IaC:** Más de 1000 políticas de cumplimiento de seguridad para Terraform, Kubernetes y Helm Charts.
- **Infracost:** Auditoría financiera en Pull Requests para detectar aumentos no autorizados en costos de nube.

---

## 4. Cadena de Suministro (Supply Chain Security)
- **Cosign (Sigstore Keyless):** Firma criptográfica de contenedores atada a la identidad de GitHub Actions (OIDC).
- **CycloneDX SBOM:** Generación de inventario completo de dependencias de software con cada compilación de imagen.
- **SLSA Provenance:** Atestación verificable de que el contenedor fue construido exclusivamente por el pipeline oficial.

---

## 5. Gestión de Hallazgos y Health Score
- Todos los hallazgos se unifican mediante `generate_report.py`, generando un reporte ejecutivo en PDF y HTML con cálculo del **Health Score** ponderado:
  - 🔴 **CRITICAL**: 25 pts | 🟠 **HIGH**: 10 pts | 🟡 **MEDIUM**: 3 pts | 🟢 **LOW**: 1 pt
  - **Calificación:** **A+** (0 pts) | **A** (≤5 pts) | **B** (≤15 pts) | **C** (≤40 pts) | **D** (≤80 pts) | **F** (>80 pts)
