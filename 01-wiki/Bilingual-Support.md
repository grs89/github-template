# 🌍 Soporte Bilingüe y Multilingüe (Documentación)

El soporte trilingüe de este proyecto no aplica a la internacionalización del código fuente, sino a las políticas de la **Documentación Técnica Pública**, garantizando que el template de CI/CD pueda ser adoptado por organizaciones hispanohablantes, angloparlantes y lusófonas.

## 1. Arquitectura de la Documentación Trilingüe

El archivo raíz `README.md` es la única pieza que requiere ser trilingüe. La Wiki de desarrollo (`01-wiki/`) siempre debe ser escrita y mantenida en **Español** para uso interno de los ingenieros de soporte y desarrollo, para no sobrecargar el mantenimiento técnico diario de la organización.

El archivo `README.md` se divide obligatoriamente en 3 bloques secuenciales, separados por un divisor horizontal `---`:
1. `<h2 id="español">🇨🇴 Español</h2>`
2. `<h2 id="english">🇺🇸 English</h2>`
3. `<h2 id="português">🇧🇷 Português</h2>`

Las secciones internas de cada idioma (ej. `Características Principales`, `Quick Start`, `Stack Tecnológico`) deben ser exactamente un espejo de las otras. Si se agrega un nuevo paso en la guía de despliegue en inglés, **debe** traducirse a los demás bloques.

## 2. Flujo de Trabajo para Agregar o Modificar Documentación

> [!WARNING]
> No realices cambios manuales en un solo idioma asumiendo que "después" actualizarás el resto. Si no sabes un idioma, apóyate en el sistema o IA para traducir el bloque que vas a agregar en el momento del commit.

**Paso a paso para añadir una instrucción al README:**
1. Ve al bloque en **Español** y agrega tu nueva instrucción o sección de infraestructura (Ej. "Manejo de Secrets AWS").
2. Haz scroll hasta el bloque en **English** y agrega la sección equivalente: "AWS Secrets Management".
3. Desciende al bloque en **Português** y añade "Gerenciamento de Segredos da AWS".
4. Confirma que la sangría y el uso de bloques Markdown ` ```bash ` y los emojis (🌟, 🛠️) coinciden exactamente en los tres bloques.
5. Verifica los enlaces internos para asegurar que las referencias apunten al ancla correcta (`#english`, `#español`).
