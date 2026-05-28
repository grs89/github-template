# 📖 Guía de Uso y Ejecución de Pipelines

Esta guía detalla los métodos de operación y mantenimiento de los ciclos de vida de GitHub Actions utilizando esta plantilla.

## 1. Disparadores de Pipelines (Triggers)

Los pipelines están programados para reaccionar a flujos de trabajo específicos y estandarizados.

### Pull Requests (Validación CI)
**Comportamiento esperado:** Al abrir o actualizar un PR hacia la rama `main`, se dispara inmediatamente `pull-request-validation.yml`.
- El flujo clonará el código de la rama en cuestión.
- Descargará dependencias y correrá SAST y Pruebas Unitarias.
- Bloqueará el *Merge* si el código no compila o los tests fallan.

> [!TIP]
> Si descubres un bug, haces un fix rápido y haces un `git push` a la misma rama, GitHub Actions abortará automáticamente la ejecución anterior que aún esté corriendo y comenzará una nueva. Esto optimiza el uso de minutos gratis de GitHub.

### Publicación de Tags (Deploy CD)
**Comportamiento esperado:** El despliegue de contenedores sólo se activa cuando un tag semántico válido es empujado al repositorio.
```bash
git tag v1.0.4
git push origin v1.0.4
```
Esto activará el orquestador principal (`docker-build_push_auto.yml`), el cual ejecutará el escaneo de seguridad profundo, la compilación de la imagen y su publicación al registro de destino (ej. Docker Hub).

### Disparador Manual (Workflow Dispatch)
Si por alguna razón necesitas re-ejecutar el pipeline principal de construcción sin empujar código ni tags:
1. Ve a la pestaña **Actions**.
2. Selecciona **Build and Push Docker Image**.
3. Haz clic en **Run workflow**.
4. Selecciona la rama sobre la cual deseas forzar el despliegue.

## 2. Inspección de Resultados (Job Summaries)

No es necesario buscar manualmente entre miles de líneas de logs de consola. Para revisar el reporte de salud de tu despliegue:

1. Ve a la ejecución del pipeline en la pestaña **Actions**.
2. Haz clic en el panel **Summary** de la ejecución.
3. Desplázate hacia abajo para ver el panel inyectado con Markdown. Allí encontrarás la cobertura de tus pruebas unitarias y los resúmenes rápidos de vulnerabilidades emitidos por Trivy y Checkov.

## 3. Revisión de Artefactos (Artefacts)

Al final del flujo `Security Scan`, el sistema comprimirá y alojará un archivo `zip` descargable. Este archivo contiene los reportes técnicos en formato nativo JSON/SARIF y, si está configurado, el **Reporte Consolidado en formato PDF** que combina resultados del código estático, la imagen base e IaC. Este documento puede usarse para cumplimiento y auditoría corporativa.
