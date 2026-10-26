# Política de Seguridad

Este repositorio es una **librería de workflows reutilizables de GitHub Actions** que otros repositorios invocan con `uses:`. Una vulnerabilidad aquí puede propagarse a todos los proyectos que la consumen, por eso se trata con prioridad.

> Los controles que el catálogo ofrece a tus pipelines (SAST, SBOM, firma de imágenes…) están en [`01-wiki/Security-and-Privacy.md`](01-wiki/Security-and-Privacy.md). Este documento trata de **cómo reportar problemas del propio repositorio**.

## Cómo reportar una vulnerabilidad

**No abras un issue ni un pull request públicos con el detalle.**

1. Usa **Security → Report a vulnerability** (reporte privado de GitHub) en este repositorio.
2. Incluye: workflow o script afectado (ruta y, si puedes, línea), versión o tag, pasos para reproducir y el impacto que observas.
3. No incluyas secretos reales ni datos de terceros; usa valores de prueba.

## Plazos de respuesta

| Etapa | Objetivo |
|:---|:---|
| Acuse de recibo | 5 días hábiles |
| Evaluación inicial (confirmada, rechazada, necesita datos) | 10 días hábiles |
| Corrección o mitigación de un hallazgo confirmado | Según severidad; se comunica en la evaluación |

Son objetivos de un mantenimiento a cargo de una persona, no un SLA contractual.

## Versiones soportadas

| Referencia | Soporte |
|:---|:---:|
| Rama `main` | ✅ |
| Tag mayor vigente (`@v2`) | ✅ |
| Tags anteriores | ❌ |

> [!WARNING]
> Los tags móviles (`@v2`, `@main`) **se reapuntan** a commits más recientes. Si necesitas una referencia inmutable, fija el **SHA completo del commit** en `uses: grs89/github-template/.github/workflows/<archivo>.yml@<sha>`.

## Alcance

**Dentro del alcance:**

- Workflows y scripts (`.github/workflows/`, `scripts/`, `policies/`, `k8s/`) que filtren secretos, ejecuten código no confiable (inyección de comandos vía `inputs`/`github.event`), o amplíen permisos del `GITHUB_TOKEN` de forma indebida.
- Descarga de scripts o binarios sin verificación de integridad.
- Los agentes de IA (`scripts/ai_remediation.py`, `ai_test_generator.py`, `ai_release_notes.py`): inyección de instrucciones desde el código de un PR, escritura fuera del repositorio o publicación de contenido no revisado.
- Flujos de supply chain: firma (Cosign), SBOM, procedencia (SLSA).

**Fuera del alcance:**

- Hallazgos que los escáneres reporten en **tu** código o en repositorios consumidores.
- Configuración de tu organización de GitHub, runners o registry.
- Ataques que requieran acceso de escritura previo al repositorio o a los secretos del consumidor.

## Divulgación

Pedimos divulgación coordinada: no publiques el detalle hasta que exista una corrección disponible o hayan pasado 90 días desde el reporte, lo que ocurra primero.

## Buenas prácticas para quien consume las plantillas

- Fija las referencias `@ref` de `uses:` a un **SHA** que hayas revisado y actualízalo de forma deliberada (Dependabot/Renovate pueden hacerlo).
- Concede el mínimo `permissions:` en el workflow llamador: un workflow reutilizable nunca obtiene más permisos de los que le da quien lo llama.
- Pasa los secretos de forma explícita (`secrets:`) en lugar de `secrets: inherit` cuando sea viable; usa PATs/GitHub Apps de alcance mínimo (`RENOVATE_TOKEN`, `INFRA_REPO_TOKEN`, `SCAFFOLD_TOKEN`).
- Protege los entornos de despliegue y destrucción (`production`, `scale-down`, `scale-up`) con *required reviewers*: los workflows `infrastructure-terraform` (apply/destroy) y `k8s-scale` dependen de esa aprobación manual.
- Revisa siempre las sugerencias que publique el agente de IA antes de aplicarlas; los reportes SARIF contienen hallazgos sin corregir, trátalos como información sensible.
- Verifica una imagen firmada con:

  ```bash
  cosign verify ghcr.io/<owner>/<imagen>@sha256:<digest> \
    --certificate-identity-regexp "^https://github.com/<owner>/<repo>/" \
    --certificate-oidc-issuer https://token.actions.githubusercontent.com
  ```
