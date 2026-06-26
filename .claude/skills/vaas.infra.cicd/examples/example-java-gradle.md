# Ejemplo: CI/CD para proyecto Java/Gradle

## Contexto

Proyecto `project-name` — API Java 17 + Spring Boot + Gradle, desplegada en ECS.

A partir de la migración a la shared library `vaas-shared`, los Jenkinsfiles de Java/Gradle se reducen a una invocación de `ciPipeline()` / `cdPipeline()`. La shared library encapsula las stages (build, docker, push a ECR, actualización del task definition, notificación Slack) y centraliza credenciales y selección de cuenta AWS por ambiente.

---

## Jenkinsfile (CI)

Ubicación: `Jenkinsfile` en la raíz del proyecto.

```groovy
@Library('vaas-shared') _

ciPipeline(
        project: 'project-name',
        slackChannel: 'slack-channel',
        nextCdJob: 'CD-Project-Name',
        terraformFolder: 'terraform',
        terraformConfigBaseFolder: 'config',
        testDockerfile: 'DockerfileTest',
        testCommand: 'clean test',
        testOutputPath: '/home/app/build/reports/tests/test/index.html',
        testOutputFile: './tests.html'
)
```

---

## Jenkinsfile-CD

Ubicación: `Jenkinsfile-CD` en la raíz del proyecto.

```groovy
@Library('vaas-shared') _

cdPipeline(
        project: 'project-name',
        slackChannel: 'slack-channel',
        ecsServiceName: 'project-name',
        taskDefinitionName: 'project-name',
        ecrRepositoryName: 'project-name-repository',
        s3BucketPath: 'project-name',
        terraformFolder: 'deploy/terraform',
        terraformConfigBaseFolder: 'config'
)
```

---

## .github/workflows/github-actions.yaml

```yaml
name: Java CI
on:
  pull_request:
    types: [opened, reopened, ready_for_review, synchronize]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-java@v3
        with:
          java-version: '17'
          distribution: 'adopt'
          cache: gradle
      - name: Grant Permissions to gradlew
        run: chmod +x gradlew
      - name: Test
        env:
          USERNAME_TOKEN: ${{ secrets.USERNAME_TOKEN }}
          PASSWORD_TOKEN: ${{ secrets.PASSWORD_TOKEN }}
        run: ./gradlew test
      - name: Add coverage to PR
        id: jacoco
        uses: madrapps/jacoco-report@v1.3
        with:
          paths: ${{ github.workspace }}/build/reports/jacoco/test/jacocoTestReport.xml
          token: ${{ secrets.GITHUB_TOKEN }}
          min-coverage-overall: 40
          min-coverage-changed-files: 60
    timeout-minutes: 7
```
