# Patrones de Jenkinsfile — Vaas

Basado en el patrón de documents-api y otros proyectos de Vaas.

---

## Estructura del Jenkinsfile

El Jenkinsfile de Vaas sigue un flujo estándar de 6 etapas:

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

## Stages

### 1. Initialization
```groovy
stage("Initialization") {
    steps {
        buildDescription "Environment: ${params.Environment} - Branch: ${params.Branch}"
    }
}
```

### 2. Slack Notification (inicio)
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

### 3. Build — por tipo de proyecto

**Java/Gradle**:
```groovy
stage("CreateArtifact") {
    steps {
        script {
            sh "./gradlew clean"
            sh "./gradlew bootJar"
        }
    }
}
```

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

### 4. Docker Build
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

**Con build args** (e.g., APM agent para Java):
```groovy
sh "docker build -t ${params.Environment}-${REPOSITORY_NAME} --build-arg URL_APM_JAR=https://repo1.maven.org/maven2/co/elastic/apm/elastic-apm-agent/1.34.1/elastic-apm-agent-1.34.1.jar ."
```

### 5. Push a ECR
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

### 6. Update Task Definition
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

### Post — Slack Notification (fin)
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

## Convenciones

- El Jenkins job recibe `params.Environment` (dev/stg/prod) y `params.Branch`
- Las imágenes se tagean con `v${BUILD_ID}` (incrementa con cada build)
- El ECR repo sigue el patrón: `<env>-<service-name>-repository`
- El task definition sigue el patrón: `<env>-<service-name>`
- El script `create_new_task_definition.py` está en `~/vaas-jenkins-scripts/` en el Jenkins server
- Las credenciales de AWS están configuradas en Jenkins como "jenkins-aws-development" y "jenkins-aws-production-core"
