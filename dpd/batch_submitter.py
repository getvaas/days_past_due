"""Encola jobs en AWS Batch para el procesamiento de loan tapes grandes.

Cuando el loan tape supera BATCH_ROW_THRESHOLD, lambda_handler delega el
procesamiento a un job de Batch en lugar de ejecutarlo inline.
"""
from __future__ import annotations

import json
import logging

from . import config
from .utils import aws_boto_session

log = logging.getLogger(__name__)


def submit_job(payload: dict, queue: str, job_definition: str) -> str:
    """Encola un job en AWS Batch con el payload del evento SQS.

    Args:
        payload: dict con la estructura del InboundMessage (body del record SQS).
        queue: nombre o ARN del job queue de AWS Batch.
        job_definition: nombre o ARN de la job definition de AWS Batch.

    Returns:
        jobId asignado por AWS Batch.

    Raises:
        ValueError: si queue o job_definition están vacíos.
    """
    if not queue:
        raise ValueError(
            "BATCH_JOB_QUEUE no está configurado. "
            "Definí la variable de entorno antes de usar AWS Batch."
        )
    if not job_definition:
        raise ValueError(
            "BATCH_JOB_DEFINITION no está configurado. "
            "Definí la variable de entorno antes de usar AWS Batch."
        )

    client = aws_boto_session.get_session(config).client("batch")
    job_name = f"dpd-{payload.get('job_id', 'unknown')}"

    response = client.submit_job(
        jobName=job_name,
        jobQueue=queue,
        jobDefinition=job_definition,
        containerOverrides={
            "environment": [
                {"name": "DPD_BATCH_PAYLOAD", "value": json.dumps(payload)},
            ]
        },
    )

    job_id = response["jobId"]
    log.info("Job encolado en AWS Batch: jobId=%s | jobName=%s | queue=%s", job_id, job_name, queue)
    return job_id
