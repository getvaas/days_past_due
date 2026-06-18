# Ejemplo: CI/CD para proyecto Node.js

## Contexto

Proyecto `notifications-api` — API Node.js 20 + NestJS, desplegada en ECS.

---

## Jenkinsfile

```groovy
def TASK_DEFINITION_NAME = "notifications-api"
def REPOSITORY_NAME = "notifications-api-repository"
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
                    channel: "jenkins",
                    color: "warning",
                    message: "*Action:* Beginning the CI\n*Environment:* ${params.Environment}\n*JobName:* ${JOB_BASE_NAME}\n*Version:* v${BUILD_ID}\n*Username:* ${BUILD_USER}"
                )
            }
        }
        stage("CreateArtifact") {
            steps {
                script {
                    sh "npm ci"
                    sh "npm run build"
                }
            }
        }
        stage("BuildImage") {
            steps {
                script {
                    sh "docker build -t ${params.Environment}-${REPOSITORY_NAME} ."
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
                channel: "jenkins",
                color: COLOR_MAP[currentBuild.currentResult],
                message: "*Action:* Finished CI\n*Environment:* ${params.Environment}\n*JobName:* ${JOB_BASE_NAME}\n*Version:* v${BUILD_ID}\n*Username:* ${BUILD_USER}\n*Status:* ${currentBuild.currentResult}"
            )
        }
    }
}
```

---

## .github/workflows/github-actions.yaml

```yaml
name: Node CI
on:
  pull_request:
    types: [opened, reopened, ready_for_review, synchronize]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - uses: actions/setup-node@v3
        with:
          node-version: '20'
          cache: 'npm'

      - name: Install dependencies
        run: npm ci

      - name: Lint
        run: npm run lint

      - name: Test
        run: npm test

    timeout-minutes: 7
```

---

## Diferencias con Java/Gradle

| Aspecto | Java/Gradle | Node.js |
|---------|------------|---------|
| Build command | `./gradlew clean bootJar` | `npm ci && npm run build` |
| Docker build args | APM agent JAR | Ninguno |
| Test command (GH Actions) | `./gradlew test` | `npm test` |
| Coverage report | JaCoCo | (depende del framework) |
| Setup action | `actions/setup-java@v3` | `actions/setup-node@v3` |
