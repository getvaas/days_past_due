# Template: Jenkinsfile

## Template

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

## Variables a reemplazar

| Placeholder | Descripción | Ejemplo |
|------------|-------------|---------|
| `{{service-name}}` | Nombre del servicio | `documents-api` |
| `{{slack-channel}}` | Canal de Slack | `jenkins` |
| `{{build-commands}}` | Comandos de build (ver abajo) | — |
| `{{docker-build-args}}` | Args de Docker build (vacío o con --build-arg) | `""` |

## Build commands por tipo de proyecto

**Java/Gradle**:
```groovy
sh "./gradlew clean"
sh "./gradlew bootJar"
```

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
