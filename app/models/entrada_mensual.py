from datetime import datetime, timezone
from decimal import Decimal

from sqlmodel import Field, SQLModel, UniqueConstraint


class EntradaMensual(SQLModel, table=True):
    __tablename__ = "monthly_entries"
    __table_args__ = (
        UniqueConstraint("concepto_id", "anio", "mes", name="uq_entry_concepto_anio_mes"),
    )

    id: int | None = Field(default=None, primary_key=True)
    concepto_id: int = Field(foreign_key="concepts.id", index=True, ondelete="CASCADE")
    anio: int
    mes: int
    monto_planeado: Decimal = Field(max_digits=14, decimal_places=2)
    monto_pagado: Decimal | None = Field(default=None, max_digits=14, decimal_places=2)
    pagado: bool = Field(default=False)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
