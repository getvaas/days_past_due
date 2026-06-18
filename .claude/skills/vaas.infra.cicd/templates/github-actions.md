# Template: GitHub Actions Workflow

## Template

```yaml
name: {{project-type}} CI
on:
  pull_request:
    types: [opened, reopened, ready_for_review, synchronize]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      {{setup-step}}

      {{install-step}}

      {{lint-step}}

      - name: Test
        {{test-env-vars}}
        run: {{test-command}}

      {{coverage-step}}

    timeout-minutes: 7
```

## Variables por tipo de proyecto

### Java/Gradle

```yaml
# {{setup-step}}
- uses: actions/setup-java@v3
  with:
    java-version: '17'
    distribution: 'adopt'
    cache: gradle
- name: Grant Permissions to gradlew
  run: chmod +x gradlew

# {{install-step}}
# (no separate install step for Gradle)

# {{lint-step}}
# (no separate lint step for Gradle)

# {{test-env-vars}}
env:
  USERNAME_TOKEN: ${{ secrets.USERNAME_TOKEN }}
  PASSWORD_TOKEN: ${{ secrets.PASSWORD_TOKEN }}

# {{test-command}}
run: ./gradlew test

# {{coverage-step}}
- name: Add coverage to PR
  id: jacoco
  uses: madrapps/jacoco-report@v1.3
  with:
    paths: ${{ github.workspace }}/build/reports/jacoco/test/jacocoTestReport.xml
    token: ${{ secrets.GITHUB_TOKEN }}
    min-coverage-overall: 40
    min-coverage-changed-files: 60
```

### Node.js

```yaml
# {{setup-step}}
- uses: actions/setup-node@v3
  with:
    node-version: '20'
    cache: 'npm'

# {{install-step}}
- name: Install dependencies
  run: npm ci

# {{lint-step}}
- name: Lint
  run: npm run lint

# {{test-env-vars}}
# (none by default)

# {{test-command}}
run: npm test

# {{coverage-step}}
# (depends on testing framework)
```

### Python

```yaml
# {{setup-step}}
- uses: actions/setup-python@v4
  with:
    python-version: '3.11'

# {{install-step}}
- name: Install dependencies
  run: |
    python -m pip install --upgrade pip
    pip install -r requirements.txt
    pip install pytest pytest-cov

# {{lint-step}}
- name: Lint
  run: |
    pip install flake8
    flake8 src/

# {{test-env-vars}}
# (none by default)

# {{test-command}}
run: pytest --cov=src --cov-report=xml

# {{coverage-step}}
# (optional: add codecov action)
```
