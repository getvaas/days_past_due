FROM public.ecr.aws/lambda/python:3.11-arm64 AS base

WORKDIR /var/task

COPY . ./

RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.11-slim AS test-runner

WORKDIR /app

COPY tests/ ./tests/
COPY ${writeMarkdownFileFromHtmlReportPythonScript} ./

RUN pip install --no-cache-dir pytest pytest-md coverage htmltabletomd

ENV ENVIRONMENT=test
CMD ["coverage", "run", "-m", "pytest", "--junitxml=reports/output.xml", "--md=reports/unit_test.md"]

FROM base AS lambda-runtime

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]