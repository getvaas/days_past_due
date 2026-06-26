# Patrones de GitHub Actions — Vaas

Basado en el patrón estándar de los proyectos de Vaas.

---

## Estructura del workflow

El workflow de GitHub Actions en Vaas se usa para **testing en PRs** (no para deployment).

---

## Java/Gradle

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

---

## Node.js

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

      - name: Test coverage
        run: npm run test:coverage

    timeout-minutes: 7
```

---

## Python

```yaml
name: Python CI
on:
  pull_request:
    types: [opened, reopened, ready_for_review, synchronize]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install pytest pytest-cov

      - name: Test
        run: pytest --cov=src --cov-report=xml

    timeout-minutes: 7
```

---

## Convenciones

- **Trigger**: Solo en PRs (no en push a branches)
- **Types**: `opened, reopened, ready_for_review, synchronize` — cubre todos los casos relevantes
- **Timeout**: 7 minutos por defecto
- **Coverage**: Se agrega como comentario en el PR
- **Secrets**: Los tokens de acceso a registros privados van como GitHub secrets (`USERNAME_TOKEN`, `PASSWORD_TOKEN`)
- El deployment NO se hace via GitHub Actions — se hace via Jenkins
