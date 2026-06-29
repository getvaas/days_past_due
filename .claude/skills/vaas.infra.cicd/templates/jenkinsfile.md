# Template: Jenkinsfile

Vaas tiene dos formas de generar Jenkinsfiles según el stack:

- **Java/Gradle** → invoca la shared library `vaas-shared` (`ciPipeline` + `cdPipeline`). Es el camino recomendado y el que la skill genera por defecto cuando detecta Java/Gradle.
- **Otros stacks (Node.js / Python)** → declarative pipeline completo. Se mantiene hasta que la shared library cubra esos casos.

---

## Java/Gradle (vía `vaas-shared`)

Genera dos archivos en la raíz del proyecto: `Jenkinsfile` (CI) y `Jenkinsfile-CD` (CD).

### `Jenkinsfile` (CI)

```groovy
@Library('vaas-shared') _

ciPipeline(
        project: '%project_name_kebab_case%',
        slackChannel: 'slack-channel',
        nextCdJob: 'CD-%project_name_train_case%',
        terraformFolder: 'terraform',
        terraformConfigBaseFolder: 'config',
        testDockerfile: 'DockerfileTest',
        testCommand: 'clean test',
        testOutputPath: '/home/app/build/reports/tests/test/index.html',
        testOutputFile: './tests.html'
)
```

### `Jenkinsfile-CD` (CD)

```groovy
@Library('vaas-shared') _

cdPipeline(
        project: '%project_name_kebab_case%',
        slackChannel: 'slack-channel',
        ecsServiceName: '%project_name_kebab_case%',
        taskDefinitionName: '%project_name_kebab_case%',
        ecrRepositoryName: '%project_name_kebab_case%-repository',
        s3BucketPath: '%project_name_kebab_case%',
        terraformFolder: 'deploy/terraform',
        terraformConfigBaseFolder: 'config'
)
```

### Placeholders a reemplazar

| Placeholder | Descripción | Ejemplo resuelto |
|------------|-------------|------------------|
| `%project_name_kebab_case%` | Nombre del proyecto en kebab-case | `project-name` |
| `%project_name_train_case%` | Nombre del proyecto en Train-Case: cada palabra capitalizada separada por `-` (derivado del kebab-case) | `Project-Name` |
| `slack-channel` | Canal de Slack para notificaciones | `project-name-alerts` |

### Parámetros relevantes de `ciPipeline`

| Parámetro | Significado |
|-----------|-------------|
| `project` | Nombre kebab-case del servicio. Lo usa la shared lib para el repository name y el ECR tag. |
| `slackChannel` | Canal donde se notifica el resultado del CI. |
| `nextCdJob` | Nombre exacto del job de CD que se dispara al terminar el CI exitosamente. Convención: `CD-<Train-Case>` (ej: `CD-Emi-Test-Lambda`). |
| `terraformFolder` / `terraformConfigBaseFolder` | Ruta a Terraform y a su carpeta de configuración (relativos a la raíz del repo). |
| `testDockerfile` | Dockerfile que corre los tests. Convención: `DockerfileTest`. |
| `testCommand` | Comando Gradle a invocar dentro del contenedor (`clean test`, `clean integrationTest`, etc). |
| `testOutputPath` | Path absoluto al reporte HTML dentro del contenedor. |
| `testOutputFile` | Path relativo donde se publica el reporte fuera del contenedor. |

### Parámetros relevantes de `cdPipeline`

| Parámetro | Significado |
|-----------|-------------|
| `project` | Nombre kebab-case del servicio. |
| `slackChannel` | Canal de notificación del deploy. |
| `ecsServiceName` | Nombre del ECS service (suele coincidir con `project`). |
| `taskDefinitionName` | Nombre del task definition en ECS (suele coincidir con `project`). |
| `ecrRepositoryName` | Repositorio ECR. Convención: `<project>-repository`. |
| `s3BucketPath` | Path en S3 para artefactos auxiliares (suele coincidir con `project`). |
| `terraformFolder` / `terraformConfigBaseFolder` | Ruta a Terraform de deploy y su config. |

---

## Otros stacks (Node.js / Python — declarative)

Mientras la shared library no cubre estos casos, la skill genera el Jenkinsfile completo con las 6 stages.

```groovy
def TASK_DEFINITION_NAME = "{{service-name}}"
def REPOSITORY_NAME = "{{service-name}}-repository"
def COLOR_MAP = [
    SUCCESS: 'good',
    FAILURE: 'danger'
]

def REPOSITORY_URL
def JENKINS_CREDENTIALS

if (params.Environment == "prod") {
    REPOSITORY_URL = "387023001980.dkr.ecr.us-east-1.amazonaws.com"
    JENKINS_CREDENTIALS = "jenkins-aws-production-core"
} else {
    REPOSITORY_URL = "052650215423.dkr.ecr.us-east-1.amazonaws.com"
    JENKINS_CREDENTIALS = "jenkins-aws-development"
}

pipeline {
    agent any
    stages {
        stage("Initialization") {
            steps {
                buildDescription "Environment: ${params.Environment} - Branch: ${params.Branch}"
            }
        }
        stage("NotificateAction") {
            steps {
                slackSend(
                    channel: "{{slack-channel}}",
                    color: "warning",
                    message: "*Action:* Beginning the CI\n*Environment:* ${params.Environment}\n*JobName:* ${JOB_BASE_NAME}\n*Version:* v${BUILD_ID}\n*Username:* ${BUILD_USER}"
                )
            }
        }
        stage("CreateArtifact") {
            steps {
                script {
                    {{build-commands}}
                }
            }
        }
        stage("BuildImage") {
            steps {
                script {
                    sh "docker build -t ${params.Environment}-${REPOSITORY_NAME} {{docker-build-args}}."
                    sh "docker tag ${params.Environment}-${REPOSITORY_NAME}:latest ${REPOSITORY_URL}/${params.Environment}-${REPOSITORY_NAME}:v${BUILD_ID}"
                }
            }
        }
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
    }
    post {
        always {
            slackSend(
                channel: "{{slack-channel}}",
                color: COLOR_MAP[currentBuild.currentResult],
                message: "*Action:* Finished CI\n*Environment:* ${params.Environment}\n*JobName:* ${JOB_BASE_NAME}\n*Version:* v${BUILD_ID}\n*Username:* ${BUILD_USER}\n*Status:* ${currentBuild.currentResult}"
            )
        }
    }
}
```

### Variables a reemplazar (declarative)

| Placeholder | Descripción | Ejemplo |
|------------|-------------|---------|
| `{{service-name}}` | Nombre del servicio | `project-name` |
| `{{slack-channel}}` | Canal de Slack | `jenkins` |
| `{{build-commands}}` | Comandos de build (ver abajo) | — |
| `{{docker-build-args}}` | Args de Docker build (vacío o con --build-arg) | `""` |

### Build commands por stack

**Node.js**:
```groovy
sh "npm ci"
sh "npm run build"
```

**Python**:
```groovy
sh "pip install -r requirements.txt"
sh "python setup.py bdist_wheel"
```
