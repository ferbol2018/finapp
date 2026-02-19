from pydantic import BaseModel, model_validator, Field
from typing import Optional
from decimal import Decimal

class UsuarioCreate(BaseModel):
    nombre: str
    email: str
    password: str


class LoginSchema(BaseModel):
    email: str
    password: str


class CuentaCreate(BaseModel):
    tipo: str
    nombre: str = Field(min_length=2, max_length=100)

    saldo: Optional[Decimal] = Field(default=None, gt=0)
    cupo_total: Optional[Decimal] = Field(default=None, gt=0)

    @model_validator(mode="after")
    def validar_cuenta(self):

        tipos_validos = ["debito", "ahorro", "inversion", "credito"]

        if self.tipo not in tipos_validos:
            raise ValueError("Tipo de cuenta inválido")

        # 🔹 Cuenta crédito
        if self.tipo == "credito":

            if self.cupo_total is None:
                raise ValueError("Cuenta crédito requiere cupo_total")

            if self.saldo is not None:
                raise ValueError("Cuenta crédito no debe tener saldo")

        # 🔹 Otras cuentas
        else:

            if self.saldo is None:
                raise ValueError("Esta cuenta requiere saldo inicial")

            if self.cupo_total is not None:
                raise ValueError("Solo cuentas crédito pueden tener cupo_total")

        return self

class MovimientoCreate(BaseModel):
    cuenta_id: int
    tipo: str
    monto: Decimal
    descripcion: str
    categoria: str | None = None
    # 🔥 Nuevo (opcional)
    transaction_id: Optional[str] = None

class TransferenciaCreate(BaseModel):
    cuenta_origen_id: int
    cuenta_destino_id: int
    monto: Decimal
    descripcion: str | None = None

class TransferenciaUsuarioCreate(BaseModel):
    cuenta_origen_id: int
    cuenta_destino_id: int
    monto: Decimal
    descripcion: str | None = None
