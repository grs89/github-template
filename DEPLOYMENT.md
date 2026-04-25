# Guía de Despliegue

Este documento describe cómo desplegar la aplicación **github-template** en diferentes entornos.

## Tabla de Contenidos

- [Requisitos Previos](#requisitos-previos)
- [Configuración Inicial](#configuración-inicial)
- [Despliegue Local (Docker Compose)](#despliegue-local-docker-compose)
- [Despliegue en Producción](#despliegue-en-producción)
- [Secrets y Credenciales](#secrets-y-credenciales)
- [Monitoreo y Logs](#monitoreo-y-logs)
- [Rollback](#rollback)
- [Troubleshooting](#troubleshooting)

---

## Requisitos Previos

### Herramientas Requeridas
- **Docker** >= 20.10
- **Docker Compose** >= 2.0
- **GitHub CLI** (`gh` v2.0+) - para autenticación
- **Git** >= 2.25
- **Make** - para comandos estándar
- **Terraform** >= 1.0 - para infraestructura (si aplica)
- **kubectl** - para Kubernetes (si aplica)

### Permisos Necesarios
- Acceso a **GitHub Container Registry (GHCR)** - `ghcr.io`
- Acceso a **GitHub Secrets** en el repositorio
- Credenciales de repositorio en `~/.ssh/` o tokens Git
- Permisos de Docker socket (`/var/run/docker.sock`)

### Variables de Entorno
```bash
# Copiar template y completar
cp .env.example .env

# Requeridas para producción
export GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxx
export REGISTRY_USERNAME=tu_usuario
export REGISTRY_TOKEN=ghcr.io_token
```

---

## Configuración Inicial

### 1. Clonar el Repositorio
```bash
git clone https://github.com/grs89/github-template.git
cd github-template
```

### 2. Autenticación con GitHub
```bash
# Autenticarse con GitHub CLI
gh auth login
# Seleccionar: GitHub.com → HTTPS → Generar token
# Copiar token en .env como GITHUB_TOKEN

# O usando Docker login
cat $GITHUB_TOKEN | docker login ghcr.io -u $REGISTRY_USERNAME --password-stdin
```

### 3. Cargar Variables de Entorno
```bash
source .env
# O en .bashrc/.zshrc para persistencia
echo "source $(pwd)/.env" >> ~/.zshrc
```

---

## Despliegue Local (Docker Compose)

### Iniciar Stack Completo
```bash
# Modo standard
docker-compose up -d

# O con logs en tiempo real
docker-compose up

# Con rebuild de imagen
docker-compose up --build
```

### Verificar Servicio
```bash
# Ver estado de contenedores
docker-compose ps

# Ver logs de app
docker-compose logs app -f

# Acceder a la app
curl http://localhost:8000

# Health check
docker-compose exec app curl http://localhost:8000/health
```

### Detener y Limpiar
```bash
# Parar servicios (mantiene datos)
docker-compose down

# Eliminar todo (volúmenes + redes)
docker-compose down -v

# Eliminar imágenes built
docker-compose down --rmi local
```

### Acceso a Base de Datos
```bash
# PostgreSQL
docker-compose exec postgres psql -U postgres -d app_db

# Redis CLI
docker-compose exec redis redis-cli

# Monitorar Trivy
curl http://localhost:8080/metrics
```

---

## Despliegue en Producción

### Opción 1: GitHub Actions (Recomendado)
La aplicación usa **GitHub Actions** para CI/CD automático. Los workflows están en `.github/workflows/`:

```yaml
Triggers:
- Push a main: Docker build + SBOM + SLSA + scan
- Pull requests: Validación lint/test/security
- Tags semánticos: Release automático
```

**Proceso:**
1. Hacer commit y push a `main`
2. GitHub Actions ejecuta automáticamente:
   - Build Docker multi-arquitectura (amd64/arm64)
   - Generación SBOM (CycloneDX)
   - Firma de imagen (Cosign)
   - Escaneo Trivy
   - Push a GHCR

3. Verificar workflow en: https://github.com/grs89/github-template/actions

### Opción 2: Kubernetes (Production-Grade)
```bash
# Actualizar imagen en manifiestos
kubectl set image deployment/github-template \
  app=ghcr.io/grs89/github-template:v1.0.0 \
  -n production

# O aplicar manifiestos YAML
kubectl apply -f k8s/deployment.yaml -n production

# Verificar rollout
kubectl rollout status deployment/github-template -n production
```

### Opción 3: Container Registry Manual
```bash
# Build local
docker build -t ghcr.io/grs89/github-template:v1.0.0 .

# Tag adicionales
docker tag ghcr.io/grs89/github-template:v1.0.0 \
           ghcr.io/grs89/github-template:latest

# Push
docker push ghcr.io/grs89/github-template:v1.0.0
docker push ghcr.io/grs89/github-template:latest

# Verificar en registry
curl -H "Authorization: Bearer $(cat ~/.docker/config.json | jq .auths | grep token)" \
  https://ghcr.io/v2/grs89/github-template/tags/list
```

---

## Secrets y Credenciales

### GitHub Secrets (Requeridos para Workflows)
```
REGISTRY_USERNAME       - Usuario Docker registry (ej: grs89)
REGISTRY_TOKEN          - Token GHCR con permisos read/write
GITHUB_TOKEN            - Token personal de GitHub (PAT)
COSIGN_KEY              - Clave privada Cosign (base64)
COSIGN_PASSWORD         - Contraseña de clave Cosign
```

Configurar en: **Settings → Secrets and variables → Actions**

```bash
# Via GitHub CLI
gh secret set REGISTRY_TOKEN --body "$(cat ~/.docker/config.json | base64)"
```

### Secrets Locales (.env)
```bash
# NUNCA commear .env, solo .env.example
cat .env >> .gitignore

# Generar secretos locales
COSIGN_KEY=$(openssl genrsa -out cosign.key 4096 && base64 cosign.key)
echo "COSIGN_KEY=$COSIGN_KEY" >> .env
```

---

## Monitoreo y Logs

### Logs en Desarrollo
```bash
# Ver todos los logs
docker-compose logs -f

# Solo aplicación
docker-compose logs app -f --tail=100

# En tiempo real con timestamp
docker-compose logs -f --timestamps

# Exportar logs
docker-compose logs app > app.log
```

### Logs en Producción
```bash
# Kubernetes
kubectl logs -f deployment/github-template -n production

# AWS CloudWatch (si aplica)
aws logs tail /aws/lambda/github-template --follow

# Ver eventos del pod
kubectl describe pod <pod-name> -n production
```

### Observabilidad
```bash
# Métricas Prometheus (si está configurado)
curl http://localhost:9090/metrics

# Traces Jaeger (si está configurado)
http://localhost:16686/

# Logs centralizados ElasticSearch (si aplica)
curl https://elasticsearch:9200/_search
```

---

## Rollback

### Rollback Local (Docker)
```bash
# Ver versiones anteriores
docker images | grep github-template

# Revertir a versión anterior
docker-compose down
git checkout HEAD~1
docker-compose up --build
```

### Rollback en Kubernetes
```bash
# Ver historial de deployments
kubectl rollout history deployment/github-template -n production

# Revertir a revisión anterior
kubectl rollout undo deployment/github-template -n production

# Revertir a revisión específica
kubectl rollout undo deployment/github-template -n production --to-revision=3

# Monitorar rollback
kubectl rollout status deployment/github-template -n production
```

### Rollback en GitHub Actions
```bash
# Re-ejecutar workflow anterior exitoso
gh run list --limit 10
gh run view <run-id> --log
gh run rerun <run-id>
```

---

## Troubleshooting

### Problema: "Image not found"
```bash
# Verificar que la imagen existe
docker images | grep github-template

# O en registry
docker pull ghcr.io/grs89/github-template:latest

# Solución
docker build -t ghcr.io/grs89/github-template:latest .
docker push ghcr.io/grs89/github-template:latest
```

### Problema: "Connection refused"
```bash
# Verificar que contenedores están corriendo
docker-compose ps

# Ver logs de error
docker-compose logs app

# Reconstruir sin caché
docker-compose up --build --force-recreate
```

### Problema: "Permission denied" - Docker socket
```bash
# Agregar usuario a grupo docker
sudo usermod -aG docker $USER
newgrp docker

# Verificar permisos
ls -la /var/run/docker.sock
```

### Problema: "Out of memory"
```bash
# Aumentar límites en docker-compose
services:
  app:
    deploy:
      resources:
        limits:
          memory: 2G

# O en Kubernetes
resources:
  limits:
    memory: "2Gi"
    cpu: "1000m"
```

### Problema: "Workflow failed in GitHub Actions"
```bash
# Ver logs detallados
gh run view <run-id> --log

# Re-ejecutar con debug
gh run rerun <run-id> --debug

# Checkear secretos están configurados
gh secret list
```

---

## Checklist de Despliegue

- [ ] `.env` completado con todas las variables
- [ ] GitHub secrets configurados (REGISTRY_TOKEN, COSIGN_KEY, etc.)
- [ ] Docker daemon ejecutándose
- [ ] Autenticación con GHCR validada
- [ ] Imágenes base (postgres, redis) descargadas (offline check)
- [ ] Puertos requeridos disponibles (8000, 5432, 6379, 8080)
- [ ] Tests locales pasando: `pytest test/`
- [ ] Build local ejecutado: `docker-compose up --build`
- [ ] Health checks pasando
- [ ] Logs sin errores críticos
- [ ] Backup de datos existentes (si aplica)

---

## Documentación Adicional

- [GitHub Actions Workflows](.github/workflows/)
- [Dockerfile - Convenciones de Build](Dockerfile)
- [Configuración Seguridad](security/)
- [Infraestructura Terraform](infrastructure/)
- [Kubernetes Manifests](k8s/)
- [README - Configuración Rápida](README.md)

---

**Última actualización:** 2026-04-25
