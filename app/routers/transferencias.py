from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from decimal import Decimal

from app import models, schemas, database
from ..auth import get_current_user


router = APIRouter(
    prefix="/transferencias",
    tags=["Transferencias"]
)


@router.post("/")
def crear_transferencia(
    transferencia: schemas.TransferenciaCreate,
    db: Session = Depends(database.get_db),
    current_user: models.Usuario = Depends(get_current_user)
):

    # 🚫 No permitir misma cuenta
    if transferencia.cuenta_origen_id == transferencia.cuenta_destino_id:
        raise HTTPException(
            status_code=400,
            detail="No puedes transferir a la misma cuenta"
        )

    try:
        monto = Decimal(transferencia.monto)

        if monto <= 0:
            raise HTTPException(
                status_code=400,
                detail="El monto debe ser mayor a cero"
            )

        # 🔎 Buscar cuentas del usuario
        cuenta_origen = db.query(models.Cuenta).filter(
            models.Cuenta.id == transferencia.cuenta_origen_id,
            models.Cuenta.usuario_id == current_user.id
        ).first()

        cuenta_destino = db.query(models.Cuenta).filter(
            models.Cuenta.id == transferencia.cuenta_destino_id,
            models.Cuenta.usuario_id == current_user.id
        ).first()

        if not cuenta_origen or not cuenta_destino:
            raise HTTPException(
                status_code=404,
                detail="Cuenta no encontrada"
            )

        # 🚫 No permitir transferir desde crédito
        if cuenta_origen.tipo == "credito":
            raise HTTPException(
                status_code=400,
                detail="No puedes transferir desde una cuenta crédito"
            )

        # 💰 Validar saldo suficiente
        if cuenta_origen.saldo < monto:
            raise HTTPException(
                status_code=400,
                detail="Saldo insuficiente"
            )

        # 🔥 Aplicar cambios financieros
        cuenta_origen.saldo -= monto

        if cuenta_destino.tipo == "credito":
            cuenta_destino.cupo_disponible += monto

            if cuenta_destino.cupo_disponible > cuenta_destino.cupo_total:
                cuenta_destino.cupo_disponible = cuenta_destino.cupo_total
        else:
            cuenta_destino.saldo += monto

        # 🧾 Crear doble movimiento contable
        movimiento_salida = models.Movimiento(
            usuario_id=current_user.id,
            cuenta_id=cuenta_origen.id,
            tipo="gasto",
            monto=monto,
            categoria="transferencia",
            descripcion=transferencia.descripcion or "Transferencia enviada"
        )

        movimiento_entrada = models.Movimiento(
            usuario_id=current_user.id,
            cuenta_id=cuenta_destino.id,
            tipo="ingreso",
            monto=monto,
            categoria="transferencia",
            descripcion=transferencia.descripcion or "Transferencia recibida"
        )

        db.add_all([
            cuenta_origen,
            cuenta_destino,
            movimiento_salida,
            movimiento_entrada
        ])

        db.commit()

        return {
            "mensaje": "Transferencia realizada correctamente",
            "monto": float(monto),
            "cuenta_origen": cuenta_origen.id,
            "cuenta_destino": cuenta_destino.id
        }

    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Error al procesar transferencia"
        )


@router.post("/entre-usuarios")
def transferir_entre_usuarios(
    transferencia: schemas.TransferenciaUsuarioCreate,
    db: Session = Depends(database.get_db),
    current_user: models.Usuario = Depends(get_current_user)
):

    if transferencia.cuenta_origen_id == transferencia.cuenta_destino_id:
        raise HTTPException(
            status_code=400,
            detail="No puedes transferir a la misma cuenta"
        )

    try:
        monto = Decimal(transferencia.monto)

        if monto <= 0:
            raise HTTPException(
                status_code=400,
                detail="El monto debe ser mayor a cero"
            )

        # 🔎 Cuenta origen (debe pertenecer al usuario actual)
        cuenta_origen = db.query(models.Cuenta).filter(
            models.Cuenta.id == transferencia.cuenta_origen_id,
            models.Cuenta.usuario_id == current_user.id
        ).first()

        if not cuenta_origen:
            raise HTTPException(
                status_code=404,
                detail="Cuenta origen no encontrada"
            )

        # 🔎 Cuenta destino (puede ser de otro usuario)
        cuenta_destino = db.query(models.Cuenta).filter(
            models.Cuenta.id == transferencia.cuenta_destino_id
        ).first()

        if not cuenta_destino:
            raise HTTPException(
                status_code=404,
                detail="Cuenta destino no encontrada"
            )

        # 🚫 No permitir transferir desde crédito
        if cuenta_origen.tipo == "credito":
            raise HTTPException(
                status_code=400,
                detail="No puedes transferir desde una cuenta crédito"
            )

        # 💰 Validar saldo suficiente
        if cuenta_origen.saldo < monto:
            raise HTTPException(
                status_code=400,
                detail="Saldo insuficiente"
            )

        # 🔥 Aplicar cambios financieros
        cuenta_origen.saldo -= monto

        if cuenta_destino.tipo == "credito":
            cuenta_destino.cupo_disponible += monto

            if cuenta_destino.cupo_disponible > cuenta_destino.cupo_total:
                cuenta_destino.cupo_disponible = cuenta_destino.cupo_total
        else:
            cuenta_destino.saldo += monto

        # 🆔 ID único de transacción
        transaction_id = str(uuid4())

        # 🧾 Movimiento salida (usuario actual)
        movimiento_salida = models.Movimiento(
            usuario_id=current_user.id,
            cuenta_id=cuenta_origen.id,
            tipo="gasto",
            monto=monto,
            categoria="transferencia",
            descripcion=transferencia.descripcion or "Transferencia enviada",
            transaction_id=transaction_id
        )

        # 🧾 Movimiento entrada (usuario destino)
        movimiento_entrada = models.Movimiento(
            usuario_id=cuenta_destino.usuario_id,
            cuenta_id=cuenta_destino.id,
            tipo="ingreso",
            monto=monto,
            categoria="transferencia",
            descripcion=transferencia.descripcion or "Transferencia recibida",
            transaction_id=transaction_id
        )

        db.add_all([
            cuenta_origen,
            cuenta_destino,
            movimiento_salida,
            movimiento_entrada
        ])

        db.commit()

        return {
            "mensaje": "Transferencia realizada correctamente",
            "transaction_id": transaction_id,
            "monto": float(monto),
            "origen_usuario": current_user.id,
            "destino_usuario": cuenta_destino.usuario_id
        }

    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Error al procesar la transferencia"
        )