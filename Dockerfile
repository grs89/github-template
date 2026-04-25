# Multi-stage build para optimizar tamaño de imagen
FROM python:3.11-slim as builder

WORKDIR /app
COPY utilidades/requirements.txt .

# Compilar dependencias en etapa builder
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /app/wheels -r requirements.txt

# Etapa final
FROM python:3.11-slim

# Labels de metadatos
LABEL maintainer="GitHub Template Contributors"
LABEL description="Python application with security scanning and reporting"
LABEL version="1.0"

WORKDIR /app

# Crear usuario no-root para seguridad
RUN useradd -m -u 1000 appuser

# Copiar wheels desde builder y instalar
COPY --from=builder /app/wheels /wheels
COPY --from=builder /app/requirements.txt .
RUN pip install --no-cache /wheels/*

# Copiar código de aplicación
COPY utilidades/ .

# Cambiar permisos
RUN chmod +x generate_report.py && chown -R appuser:appuser /app

# Usuario no-root
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)" || exit 1

# Entrypoint
ENTRYPOINT ["python"]
CMD ["generate_report.py"]
