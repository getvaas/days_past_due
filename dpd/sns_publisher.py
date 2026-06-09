"""Publicación de respuesta en SNS con MessageAttributes para filtrado."""
from __future__ import annotations

import json
import os

import boto3

from .models import OutboundMessage


def publish_response(msg: OutboundMessage, topic_arn: str | None = None) -> str:
    """Publica el mensaje de respuesta en el SNS topic.

    origin y target van TANTO en el body como en MessageAttributes
    para que el filtro de suscripción SNS→SQS funcione correctamente.

    Returns:
        MessageId del SNS.
    """
    arn = topic_arn or os.environ["SNS_RESPONSE_TOPIC_ARN"]
    sns = boto3.client("sns")

    response = sns.publish(
        TopicArn=arn,
        Message=json.dumps(msg.to_dict()),
        MessageAttributes={
            k: {"DataType": v["DataType"], "StringValue": v["StringValue"]}
            for k, v in msg.message_attributes.items()
        },
    )
    return response["MessageId"]
