"""Modelos del protocolo SQS/SNS entre Enricher y Payments Lambda."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date
from typing import Optional

from .utils.dates import to_date as _to_date


@dataclass
class MessageMetadata:
    products: list[str]                          # ["dpd", "total_amount", "vpn"]
    interest_rate: Optional[float] = None        # requerido solo para "vpn"
    paid_threshold: float = 1.0                  # fracción mínima pagada para cuota al día (default 100%)
    calc_date: Optional[date] = None             # fecha de corte; None → date.today() en el handler
    last_payment_tape_date: Optional[date] = None
    last_schedule_payment_date: Optional[date] = None
    last_payment_date: Optional[date] = None

    @classmethod
    def from_dict(cls, d: dict) -> "MessageMetadata":
        return cls(
            products=d.get("products", []),
            interest_rate=d.get("interest_rate"),
            paid_threshold=float(d.get("paid_threshold", 1.0)),
            calc_date=_to_date(d.get("calc_date")),
            last_payment_tape_date=_to_date(d.get("last_payment_tape_date")),
            last_schedule_payment_date=_to_date(d.get("last_schedule_payment_date")),
            last_payment_date=_to_date(d.get("last_payment_date")),
        )

    def to_dict(self) -> dict:
        out: dict = {"products": self.products}
        if self.interest_rate is not None:
            out["interest_rate"] = self.interest_rate
        if self.paid_threshold != 1.0:
            out["paid_threshold"] = self.paid_threshold
        if self.calc_date is not None:
            out["calc_date"] = self.calc_date.isoformat()
        if self.last_payment_tape_date:
            out["last_payment_tape_date"] = self.last_payment_tape_date.isoformat()
        if self.last_schedule_payment_date:
            out["last_schedule_payment_date"] = self.last_schedule_payment_date.isoformat()
        if self.last_payment_date:
            out["last_payment_date"] = self.last_payment_date.isoformat()
        return out


@dataclass
class InboundMessage:
    """Mensaje que recibe la Lambda desde Enricher (vía SQS)."""
    origin: str          # "ENRICHER"
    target: str          # "PAYMENTS_EXPAND"
    job_id: str
    input_file: str      # s3://bucket/path/loan_tape.csv
    output_file: str     # s3://bucket/path/output.csv
    key: str             # columna identificadora de contrato en el loan tape
    target_type: str     # "COMPANY"
    target_id: int       # company_id numérico
    metadata: MessageMetadata
    rate_type: str = "fixed"           # "fixed" | "variable"
    mode: Optional[str] = None         # "cascade" | "join" | None → ambos modos

    @classmethod
    def from_sqs_record(cls, record: dict) -> "InboundMessage":
        """Parsea un record del evento SQS de Lambda."""
        body = json.loads(record["body"]) if isinstance(record["body"], str) else record["body"]
        return cls(
            origin=body["origin"],
            target=body["target"],
            job_id=body["job_id"],
            input_file=body["input_file"],
            output_file=body["output_file"],
            key=body["key"],
            target_type=body["target_type"],
            target_id=int(body["target_id"]),
            metadata=MessageMetadata.from_dict(body.get("metadata", {})),
            rate_type=body.get("rate_type", "fixed"),
            mode=body.get("mode"),
        )


@dataclass
class OutboundMessage:
    """Mensaje que publica la Lambda de vuelta al Enricher (vía SNS)."""
    origin: str = "PAYMENTS_EXPAND"
    target: str = "ENRICHER"
    job_id: str = ""
    input_file: str = ""
    output_file: str = ""
    key: str = ""
    target_type: str = "COMPANY"
    target_id: int = 0
    metadata: MessageMetadata = field(default_factory=lambda: MessageMetadata(products=[]))

    @classmethod
    def from_inbound(cls, msg: InboundMessage) -> "OutboundMessage":
        """Construye el mensaje de respuesta a partir del mensaje de entrada."""
        return cls(
            origin="PAYMENTS_EXPAND",
            target=msg.origin,
            job_id=msg.job_id,
            input_file=msg.input_file,
            output_file=msg.output_file,
            key=msg.key,
            target_type=msg.target_type,
            target_id=msg.target_id,
            metadata=MessageMetadata(
                products=msg.metadata.products,
                interest_rate=msg.metadata.interest_rate,
            ),
        )

    def to_dict(self) -> dict:
        return {
            "origin": self.origin,
            "target": self.target,
            "job_id": self.job_id,
            "input_file": self.input_file,
            "output_file": self.output_file,
            "key": self.key,
            "target_type": self.target_type,
            "target_id": self.target_id,
            "metadata": self.metadata.to_dict(),
        }

    @property
    def message_attributes(self) -> dict:
        """MessageAttributes requeridos por el filtro SNS."""
        return {
            "origin": {"DataType": "String", "StringValue": self.origin},
            "target": {"DataType": "String", "StringValue": self.target},
        }
