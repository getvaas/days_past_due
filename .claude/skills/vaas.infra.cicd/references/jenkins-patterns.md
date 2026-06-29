# Patrones de Jenkinsfile — Vaas

Vaas tiene dos patrones de Jenkinsfile según el stack:

- **Java/Gradle** → invocación a la shared library `vaas-shared` (`ciPipeline` + `cdPipeline`).
- **Node.js / Python** → declarative pipeline completo (patrón legacy, hasta que `vaas-shared` cubra esos stacks).

---

## Java/Gradle vía `vaas-shared`

Dos archivos en la raíz del repo:

- `Jenkinsfile` — invoca `ciPipeline(...)`. Corre tests, construye la imagen y dispara el job de CD.
- `Jenkinsfile-CD` — invoca `cdPipeline(...)`. Aplica Terraform y actualiza el ECS service/task definition.

Ambos arrancan con `@Library('vaas-shared') _` para importar la shared library.

### `ciPipeline`

```groovy
@Library('vaas-shared') _

ciPipeline(
        project: '<kebab-name>',
        slackChannel: '<channel>',
        nextCdJob: 'CD-<Train-Case>',
        terraformFolder: 'terraform',
        terraformConfigBaseFolder: 'config',
        testDockerfile: 'DockerfileTest',
        testCommand: 'clean test',
        testOutputPath: '/home/app/build/reports/tests/test/index.html',
        testOutputFile: './tests.html'
)
```

| Parámetro | Para qué sirve |
|-----------|----------------|
| `project` | Nombre kebab-case del servicio. La shared lib lo usa como base para el repository name y el tag de la imagen. |
| `slackChannel` | Canal donde notifica inicio y resultado del CI. |
| `nextCdJob` | Job de CD a disparar al terminar exitosamente. Convención Vaas: `CD-<Train-Case>`, cada palabra capitalizada separada por `-` (ej: `CD-Project-Name`). |
| `terraformFolder` | Ruta a la carpeta de Terraform del proyecto, relativa al repo. |
| `terraformConfigBaseFolder` | Carpeta base de configuración Terraform (subcarpetas `dev/`, `stg/`, `prod/`). |
| `testDockerfile` | Dockerfile que corre los tests (típicamente `DockerfileTest`). |
| `testCommand` | Comando Gradle a invocar dentro del contenedor. Para tests unitarios: `clean test`. |
| `testOutputPath` | Path absoluto al reporte HTML de tests dentro del contenedor. |
| `testOutputFile` | Path relativo donde la shared lib publica el reporte fuera del contenedor (para archivar en Jenkins). |

### `cdPipeline`

```groovy
@Library('vaas-shared') _

cdPipeline(
        project: '<kebab-name>',
        slackChannel: '<channel>',
        ecsServiceName: '<kebab-name>',
        taskDefinitionName: '<kebab-name>',
        ecrRepositoryName: '<kebab-name>-repository',
        s3BucketPath: '<kebab-name>',
        terraformFolder: 'deploy/terraform',
        terraformConfigBaseFolder: 'config'
)
```

| Parámetro | Para qué sirve |
|-----------|----------------|
| `project` | Nombre kebab-case del servicio. |
| `slackChannel` | Canal donde notifica el resultado del deploy. |
| `ecsServiceName` | Nombre del ECS service. Por convención coincide con `project`. |
| `taskDefinitionName` | Nombre del task definition en ECS. Por convención coincide con `project`. |
| `ecrRepositoryName` | Nombre del repo ECR. Convención: `<project>-repository`. |
| `s3BucketPath` | Path en S3 para artefactos auxiliares (assets, dumps, etc). |
| `terraformFolder` | Ruta a la carpeta de Terraform de deploy. |
| `terraformConfigBaseFolder` | Carpeta base de configuración Terraform. |

### Lo que aporta la shared library

La shared library encapsula:

- Selección de cuenta AWS (dev/stg/prod) y de las credenciales Jenkins (`jenkins-aws-development`, `jenkins-aws-production-core`).
- Cálculo del `REPOSITORY_URL` por ambiente.
- Stages de build, docker build, push a ECR, actualización del task definition.
- Notificaciones Slack al inicio y al final.
- `buildDescription` con ambiente y branch.
- Archivo de reportes de tests.

El detalle de cómo lo hace vive en el repo `vaas-shared`; este documento describe únicamente la interfaz que consume la skill.

---

## Patrón legacy (Node.js / Python — declarative)

Mientras la shared library no cubra estos stacks, los proyectos siguen usando el Jenkinsfile declarativo completo. Estructura:

```groovy
// Variables de configuración
def TASK_DEFINITION_NAME = "{{service-name}}"
def REPOSITORY_NAME = "{{service-name}}-repository"
def COLOR_MAP = [
    SUCCESS: 'good',
    FAILURE: 'danger'
]

// Selección de cuenta AWS según ambiente
def REPOSITORY_URL
def JENKINS_CREDENTIALS

if (params.Environment == "prod") {
    REPOSITORY_URL = "387023001980.dkr.ecr.us-east-1.amazonaws.com"
    JENKINS_CREDENTIALS = "jenkins-aws-production-core"
} else {
    REPOSITORY_URL = "052650215423.dkr.ecr.us-east-1.amazonaws.com"
    JENKINS_CREDENTIALS = "jenkins-aws-development"
}
```

### Stages

#### 1. Initialization
```groovy
stage("Initialization") {
    steps {
        buildDescription "Environment: ${params.Environment} - Branch: ${params.Branch}"
    }
}
```

#### 2. Slack Notification (inicio)
```groovy
stage("NotificateAction") {
    steps {
        slackSend(
            channel: "jenkins",
            color: "warning",
            message: "*Action:* Beginning the CI\n*Environment:* ${params.Environment}\n*JobName:* ${JOB_BASE_NAME}\n*Version:* v${BUILD_ID}\n*Username:* ${BUILD_USER}"
        )
    }
}
```

#### 3. Build por stack

**Node.js**:
```groovy
stage("CreateArtifact") {
    steps {
        script {
            sh "npm ci"
            sh "npm run build"
        }
    }
}
```

**Python**:
```groovy
stage("CreateArtifact") {
    steps {
        script {
            sh "pip install -r requirements.txt"
            sh "python setup.py bdist_wheel"
        }
    }
}
```

#### 4. Docker Build
```groovy
stage("BuildImage") {
    steps {
        script {
            sh "docker build -t ${params.Environment}-${REPOSITORY_NAME} ."
            sh "docker tag ${params.Environment}-${REPOSITORY_NAME}:latest ${REPOSITORY_URL}/${params.Environment}-${REPOSITORY_NAME}:v${BUILD_ID}"
        }
    }
}
```

#### 5. Push a ECR
```groovy
stage("UploadToEcr") {
    steps {
        script {
            withAWS(credentials: JENKINS_CREDENTIALS, region: "us-east-1") {
                sh "aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin ${REPOSITORY_URL}"
                sh "docker push ${REPOSITORY_URL}/${params.Environment}-${REPOSITORY_NAME}:v${BUILD_ID}"
            }
        }
    }
}
```

#### 6. Update Task Definition
```groovy
stage("CreateTaskDefinition") {
    steps {
        script {
            withAWS(credentials: JENKINS_CREDENTIALS, region: "us-east-1") {
                sh "cp ~/vaas-jenkins-scripts/create_new_task_definition.py ./create_new_task_definition.py"
                sh "python3 create_new_task_definition.py v${BUILD_ID} ${params.Environment}-${TASK_DEFINITION_NAME}"
                sh "rm create_new_task_definition.py"
            }
        }
    }
}
```

#### Post — Slack Notification (fin)
```groovy
post {
    always {
        slackSend(
            channel: "jenkins",
            color: COLOR_MAP[currentBuild.currentResult],
            message: "*Action:* Finished CI\n*Environment:* ${params.Environment}\n*JobName:* ${JOB_BASE_NAME}\n*Version:* v${BUILD_ID}\n*Username:* ${BUILD_USER}\n*Status:* ${currentBuild.currentResult}"
        )
    }
}
```

---

## Convenciones (ambos patrones)

- El Jenkins job recibe `params.Environment` (dev/stg/prod) y `params.Branch`.
- Las imágenes se tagean con `v${BUILD_ID}` (incrementa con cada build).
- El ECR repo sigue el patrón: `<env>-<service-name>-repository`.
- El task definition sigue el patrón: `<env>-<service-name>`.
- El script `create_new_task_definition.py` está en `~/vaas-jenkins-scripts/` en el Jenkins server (lo usa la shared lib internamente para Java/Gradle y aparece explícito en el patrón legacy).
- Las credenciales AWS están configuradas en Jenkins como `jenkins-aws-development` y `jenkins-aws-production-core`.
- El job de CD se llama `CD-<Train-Case>`, cada palabra capitalizada separada por `-` (ej: `CD-Project-Name`).
