# Guía de Contribución

Gracias por contribuir. Este repositorio es una **librería de workflows reutilizables reutilizada por otros repositorios** (vía `uses:` y `03-start-init.yml`), así que un cambio aquí afecta a todos los consumidores.

> Vulnerabilidades: no uses issues públicos, sigue [`SECURITY.md`](SECURITY.md).

## Antes de empezar

- Lee el [`README.md`](README.md) y la wiki en [`01-wiki/`](01-wiki/) (`Architecture.md`, `Usage-Guide.md`, `Workflows-Catalog.md`, `Variables.md`).
- Si la idea es grande, abre primero un issue para acordar el enfoque.

## Entorno local

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r tests/requirements-dev.txt
pip install strands-agents        # necesario para los tests de los scripts de IA
```

## Antes de abrir un Pull Request

El workflow `Template CI` ejecuta lo mismo; un PR que falle no se revisa.

```bash
python -m pytest tests -q                      # scripts + validación estática de workflows + ejecución de steps (Docker)
docker run --rm -v "$PWD:/repo" --workdir /repo rhysd/actionlint:1.7.7   # actionlint + shellcheck
```

Los tests de `tests/test_workflow_steps.py` ejecutan el shell real de los steps en un contenedor Ubuntu con stubs (`gh`, `kubectl`, colector HTTP); se omiten solos si no hay Docker.

## Reglas específicas de este repositorio

1. **Es una librería reutilizable.** Diseña para cualquier consumidor; no adaptes plantillas a un repositorio concreto.
2. **Contrato tipado:** todo parámetro es un `input` de `workflow_call` (nombres en MAYÚSCULAS, con `description` y `default`) y todo secreto está declarado en `secrets:`. `tests/test_workflows.py` lo verifica.
3. **Nada de `${{ inputs.* }}`, `${{ secrets.* }}` ni `github.event.*` dentro de `run:`** (inyección de comandos): pásalos por `env:` y usa `"$VAR"`.
4. **Mínimo privilegio:** cada job declara `permissions:`; pide `write` solo donde el job lo necesite.
5. **Acciones con versión fija** (`@v4`, `@v0.28.0` o SHA), nunca `@main`/`@master`. Dependabot/Renovate abren los PR de actualización.
6. **Los workflows no se ejecutan en contenedor `container:`** salvo necesidad real (los runners Alpine rompen las acciones JavaScript); instala la herramienta con su `setup-*` o usa `docker run`.
7. **Los scripts viven en `scripts/`** y los workflows los obtienen del propio repositorio o de `TEMPLATE_PROJECT@TEMPLATE_REF`. Un script nuevo o lógica no trivial = un test en `tests/`.
8. **No silencies fallos con `|| true`** sin justificarlo en un comentario; en steps de seguridad comprueba el código de salida.
9. **Documenta:** inputs nuevos en el propio workflow (`description`) y el workflow en [`01-wiki/Workflows-Catalog.md`](01-wiki/Workflows-Catalog.md).

## Commits

Se usan **commits convencionales**, que alimentan el changelog y las notas de versión:

```
feat(scope): descripción breve
fix(scope): descripción breve
docs|refactor|test|chore(scope): descripción breve
```

- Mensaje en español o inglés, imperativo y específico. Un commit por cambio lógico.
- El pipeline genera commits automáticos (`chore: actualizar changelog [skip ci]`): haz `git pull --rebase` antes de empujar.

## Flujo de un PR

1. Crea una rama desde `main` (`feat/…`, `fix/…`, `docs/…`).
2. Haz los cambios, ejecuta las comprobaciones y empuja.
3. Abre el PR describiendo **qué cambia, a quién afecta y cómo lo verificaste**.
4. El PR se integra cuando `Template CI` pasa y hay aprobación.

## Versionado

Las versiones siguen `vAAAA.MM.NN`. Quien consuma las plantillas y necesite una referencia inmutable debe fijar el **SHA del commit**, ya que los tags (`@v2`) pueden reapuntarse.

## Licencia

Al contribuir aceptas que tu aportación se distribuya bajo la licencia del proyecto (ver [`LICENSE`](LICENSE)).
