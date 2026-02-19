from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, extract

from app import models, database
from app.auth import get_current_user
from app.services.presupuesto_service import evaluar_presupuesto

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

@router.get("/")
def obtener_dashboard(
    mes: int,
    anio: int,
    db: Session = Depends(database.get_db),
    current_user: models.Usuario = Depends(get_current_user)
):

    # 🔹 Ingresos
    ingresos = db.query(
        func.coalesce(func.sum(models.Movimiento.monto), 0)
    ).join(models.Cuenta).filter(
        models.Cuenta.usuario_id == current_user.id,
        models.Movimiento.tipo == "ingreso",
        extract("month", models.Movimiento.fecha) == mes,
        extract("year", models.Movimiento.fecha) == anio
    ).scalar()

    # 🔹 Gastos
    gastos = db.query(
        func.coalesce(func.sum(models.Movimiento.monto), 0)
    ).join(models.Cuenta).filter(
        models.Cuenta.usuario_id == current_user.id,
        models.Movimiento.tipo == "gasto",
        extract("month", models.Movimiento.fecha) == mes,
        extract("year", models.Movimiento.fecha) == anio
    ).scalar()

    balance = ingresos - gastos

    # 🔹 Gastos por categoría
    categorias = db.query(
        models.Movimiento.categoria,
        func.coalesce(func.sum(models.Movimiento.monto), 0).label("total")
    ).join(models.Cuenta).filter(
        models.Cuenta.usuario_id == current_user.id,
        models.Movimiento.tipo == "gasto",
        extract("month", models.Movimiento.fecha) == mes,
        extract("year", models.Movimiento.fecha) == anio
    ).group_by(models.Movimiento.categoria).all()

    categorias_lista = [
        {
            "categoria": c.categoria,
            "total": float(c.total)
        }
        for c in categorias
    ]

    # 🔹 Presupuestos en alerta
    presupuestos = db.query(models.Presupuesto).filter(
        models.Presupuesto.usuario_id == current_user.id,
        models.Presupuesto.mes == mes,
        models.Presupuesto.anio == anio
    ).all()

    alertas = 0

    for p in presupuestos:
        resultado = evaluar_presupuesto(
            db=db,
            usuario_id=current_user.id,
            categoria=p.categoria,
            mes=mes,
            anio=anio
        )
        if resultado:
            alertas += 1

    return {
        "ingresos": float(ingresos),
        "gastos": float(gastos),
        "balance": float(balance),
        "presupuestos_alerta": alertas,
        "categorias": categorias_lista
    }
