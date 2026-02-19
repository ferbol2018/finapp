from sqlalchemy import Column, Integer, String, Numeric, ForeignKey, DateTime, Boolean, Float, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base

class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100))
    email = Column(String(120), unique=True, index=True)
    password_hash = Column(String)

    cuentas = relationship("Cuenta", back_populates="usuario")


class Cuenta(Base):
    __tablename__ = "cuentas"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"))
    tipo = Column(
    Enum("debito", "ahorro", "inversion", "credito", name="tipo_cuenta"),
    nullable=False
    )   
    nombre = Column(String(100))
    saldo = Column(Numeric(14,2), default=0)
    cupo_total = Column(Numeric(14,2), nullable=True)
    cupo_disponible = Column(Numeric(14,2), nullable=True)

    usuario = relationship("Usuario", back_populates="cuentas")


class Movimiento(Base):
    __tablename__ = "movimientos"

    id = Column(Integer, primary_key=True, index=True)

    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    cuenta_id = Column(Integer, ForeignKey("cuentas.id"), nullable=False)

    tipo = Column(String, nullable=False)  # ingreso / gasto
    monto = Column(Numeric(12, 2), nullable=False)
    categoria = Column(String, nullable=False)
    descripcion = Column(String, nullable=True)

    # 🔥 AQUÍ VA ESTO
    transaction_id = Column(String, nullable=True)

    fecha = Column(DateTime, default=datetime.utcnow)

    usuario = relationship("Usuario")
    cuenta = relationship("Cuenta")

class Presupuesto(Base):
    __tablename__ = "presupuestos"

    id = Column(Integer, primary_key=True, index=True)
    categoria = Column(String, nullable=False)
    monto_limite = Column(Float, nullable=False)
    mes = Column(Integer, nullable=False)
    anio = Column(Integer, nullable=False)

    usuario_id = Column(Integer, ForeignKey("usuarios.id"))
    usuario = relationship("Usuario")
