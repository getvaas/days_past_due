#!/bin/sh

set -e

RUNTIME_ENTRYPOINT=/var/runtime/bootstrap

export _HANDLER=app.lambda_handler

if [ "${BATCH_EXECUTION:-false}" = "true" ]; then
    echo "Running in batch mode"
    exec python app.py "$@"
else
    echo "Running Lambda"
    if [ -z "${AWS_LAMBDA_RUNTIME_API}" ]; then
        echo "Running with aws-lambda-rie"
        exec /usr/local/bin/aws-lambda-rie $RUNTIME_ENTRYPOINT
    else
        exec $RUNTIME_ENTRYPOINT
    fi
fi
