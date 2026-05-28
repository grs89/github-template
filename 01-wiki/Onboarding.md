# 🚀 Guía de Inducción Pedagógica (Onboarding)

¡Hola y bienvenido(a) al equipo! 🎉 Si eres nuevo en DevOps, CI/CD o en la cultura de desarrollo de software seguro, esta guía es para ti. Nuestro objetivo es que entiendas no solo *cómo* usar nuestro sistema automatizado de GitHub, sino también el *por qué* detrás de cada pieza técnica.

## 🗺️ Roadmap Visual: Tu Camino de Aprendizaje

Te sugerimos leer nuestra base de conocimiento en el siguiente orden para no abrumarte:

```mermaid
flowchart LR
    A[1. Onboarding<br/>(¡Estás aquí!)] --> B[2. Installation<br/>Configurar tu Repo]
    B --> C[3. Usage-Guide<br/>Cómo usar y probar]
    C --> D[4. Variables<br/>Entender los Secretos]
    D --> E[5. Security<br/>¿Por qué falla el pipeline?]
    E --> F[6. Architecture<br/>Detalles profundos]
```

## 🤔 1. Conceptos Básicos: ¿Por qué usamos CI/CD?

Imagina que desarrollas un código en tu computadora local. Funciona perfecto. Se lo pasas a tu compañero, y en su computadora ¡no funciona! O peor, subes el código al servidor de producción, sobreescribes archivos, y de repente toda la aplicación de la compañía se cae.

**CI/CD (Continuous Integration / Continuous Deployment)** resuelve este problema:
- **CI (Integración Continua):** Cada vez que abres un Pull Request, un servidor en la nube de GitHub clona tu código y lo evalúa. Verifica que esté formateado correctamente y que pase las pruebas (`npm test`, `go test`). Si hay un error, rechaza tu código antes de que rompas la aplicación principal.
- **CD (Despliegue Continuo):** Cuando tu código está aprobado, el sistema crea un "contenedor" (`Docker`) que empaqueta tu programa junto con todo lo necesario para correr (sistema operativo, librerías, etc). Este paquete se sube a un registro en internet para que los servidores de producción lo descarguen y lo corran de manera idéntica a tu computadora.

## 🐳 2. Concepto Clave: Docker y Contenedores

En nuestra documentación (`Architecture.md` y `Installation.md`) verás mucho la palabra **Docker**.
Docker es como una "caja mágica". En lugar de instalar lenguajes y bases de datos directamente en tu Windows o Mac, Docker empaca tu código en una "caja de Linux" estandarizada llamada "Contenedor".

- **Dockerfile:** Es la "receta de cocina" que dice cómo construir la caja.
- **Image (Imagen):** Es la caja terminada y congelada lista para ser compartida.

> [!NOTE]
> Nuestro pipeline no solo construye esta imagen para una arquitectura de procesador, sino para varias al mismo tiempo (`amd64` que usan las computadoras normales, y `arm64` que usan los procesadores M1 de Apple o servidores modernos).

## 🔑 3. Entendiendo las Variables y Secretos

En el archivo `Variables.md` te pedimos configurar cosas como `DOCKERHUB_TOKEN`.
¿Por qué no simplemente guardamos la contraseña en un archivo `.env` o en el código fuente?

> [!CAUTION]
> Si subes un token, contraseña o clave API a un repositorio público, hay bots maliciosos en internet que lo robarán en milisegundos y lo usarán para minar criptomonedas o borrar bases de datos a nombre de la empresa.

Por esto usamos **GitHub Secrets**. Cuando guardas una contraseña en GitHub Secrets, ni siquiera tú puedes volver a verla; queda cifrada. Cuando el pipeline (nuestro código automatizado) necesita conectarse a Docker Hub para subir tu imagen, GitHub inyecta esa clave de forma segura en la memoria RAM, hace el trabajo, y la destruye.

## 🛡️ 4. Seguridad: Trivy y Checkov

¿Has notado que a veces el pipeline se pone en rojo (Falla) aunque tu código funcione perfecto?
En `Security-and-Privacy.md` hablamos de **Trivy** y **Checkov**. Estas son herramientas de ciberseguridad.

- **Checkov:** Se asegura de que tu `Dockerfile` esté bien escrito. Por ejemplo, si intentas ejecutar tu aplicación dentro de Docker usando el usuario `root` (administrador absoluto), Checkov detendrá tu pipeline. ¿Por qué? Si un hacker vulnera tu app y eres `root`, el hacker toma control de toda la máquina. Si no eres `root`, el hacker queda atrapado en tu contenedor.
- **Trivy:** Lee tus dependencias (`package.json`, `go.mod`) y verifica si estás usando una versión antigua de una librería que tiene un virus conocido a nivel mundial.

### 🐛 Troubleshooting (Solución de problemas comunes)

Si el pipeline falla (X roja), sigue estos pasos:
1. Haz clic en el nombre del pipeline fallido.
2. Mira el **Job Summary** o el panel de Logs a la izquierda.
3. Si dice `Failed to compile`, significa que escribiste mal una línea de código y el linter lo detuvo. Busca en el log qué archivo y qué línea tiene el error (ej. `SyntaxError: unexpected token`).
4. Si falla en el paso `Checkov IaC Scan`, descarga el PDF de seguridad generado. Seguramente te dirá qué regla rompiste (ej. "Te falta un HEALTHCHECK en tu Dockerfile").

## 🌎 5. Soporte Bilingüe

Queremos que este repositorio base sea útil para equipos en varios países. Por eso nuestro `README.md` tiene tres secciones (Español, Inglés y Portugués).
Si en el futuro te piden agregar una nueva funcionalidad al pipeline y quieres documentar cómo se usa en el `README.md`, asegúrate de actualizar **los tres bloques de idioma** para mantener la consistencia. Puedes leer más sobre este estándar en la guía `Bilingual-Support.md`.

---
¡Eso es todo por ahora! No dudes en experimentar, romper código en ramas de prueba y ver cómo responde el pipeline. ¡Esa es la mejor forma de aprender!
