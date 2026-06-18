---
description: >-
  Configurar CI/CD pipelines para un proyecto de Vaas. Genera Jenkinsfile para deployment
  y GitHub Actions para testing en PRs.
  Usar cuando el developer dice "setup CI/CD", "configure pipeline", "create Jenkinsfile",
  "setup GitHub Actions", "configurar deployment", "necesito pipeline de deployment".
---

# vaas.infra.cicd — Configurar CI/CD Pipelines

Genera los archivos de CI/CD para un proyecto de Vaas: Jenkinsfile para deployment a ECS y GitHub Actions para testing en PRs.

## Restricciones

- **Solo genera archivos**. Nunca ejecuta pipelines ni deployments.
- **Sigue los patrones de Vaas** — basados en documents-api como referencia.
- **Jenkins para deployment**, **GitHub Actions para PR testing**.
- **Genera para los ambientes** dev, stg, prod con las credenciales correctas.

## Referencias

- `references/jenkins-patterns.md` — Patrones de Jenkinsfile de Vaas
- `references/github-actions-patterns.md` — Patrones de GitHub Actions de Vaas
- `references/environment-config.md` — Cuentas AWS, credenciales Jenkins, ECR URLs

## Flujo de ejecución

### Paso 1: Detectar tipo de proyecto

Leer los archivos del proyecto para determinar:

| Indicador | Tipo detectado | Build command |
|-----------|---------------|---------------|
| `build.gradle` o `build.gradle.kts` | Java/Gradle | `./gradlew clean bootJar` |
| `pom.xml` | Java/Maven | `mvn clean package` |
| `package.json` | Node.js | `npm ci && npm run build` |
| `requirements.txt` o `pyproject.toml` | Python | `pip install && python setup.py` |
| `Dockerfile` (siempre) | Docker build | `docker build -t ...` |

### Paso 2: Verificar infraestructura existente

```
¿Existe deploy/terraform/?
  → SÍ: Leer para obtener ECR repository name, service name, etc.
  → NO: Preguntar al developer los nombres o sugerir usar `vaas.infra.setup` primero
```

### Paso 3: Recopilar información

1. **Nombre del servicio** (e.g., "documents-api") — detectar de infra o preguntar
2. **Nombre del ECR repository** — detectar de infra o derivar del servicio
3. **Ambientes a deployar** — por defecto: dev, stg, prod
4. **Canal de Slack para notificaciones** — por defecto: "jenkins"
5. **Test framework** — detectar automáticamente

### Paso 4: Generar archivos

#### Jenkinsfile

Usar `templates/jenkinsfile.md` como base. El Jenkinsfile de Vaas tiene estas etapas:

1. **Initialization** — Set build description
2. **NotificateAction** — Notificación Slack de inicio
3. **CreateArtifact** — Build del proyecto (gradle/npm/etc)
4. **BuildImage** — Docker build con tag de versión
5. **UploadToEcr** — Push a ECR
6. **CreateTaskDefinition** — Actualizar task definition en ECS

#### GitHub Actions

Usar `templates/github-actions.md` como base. El workflow de Vaas:

1. **Trigger**: PR opened, reopened, ready_for_review, synchronize
2. **Setup**: Checkout + setup del runtime (Java/Node/Python)
3. **Test**: Ejecutar tests
4. **Coverage**: Agregar reporte de coverage al PR

### Paso 5: Explicar al developer

1. **Qué se creó** — Jenkinsfile y/o GitHub Actions workflow
2. **Cómo funciona** — flujo del pipeline en lenguaje simple
3. **Configuración necesaria** — Jenkins credentials, GitHub secrets
4. **Cómo deployar** — proceso de Jenkins (seleccionar ambiente, branch)

## Ejemplos

- `examples/example-java-gradle.md` — CI/CD para proyecto Java/Gradle
- `examples/example-node.md` — CI/CD para proyecto Node.js

## Templates

- `templates/jenkinsfile.md` — Template de Jenkinsfile
- `templates/github-actions.md` — Template de GitHub Actions workflow
