from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from app import models


def evaluar_presupuesto(
    db: Session,
    usuario_id: int,
    categoria: str,
    mes: int,
    anio: int
):

    presupuesto = db.query(models.Presupuesto).filter(
        models.Presupuesto.usuario_id == usuario_id,
        models.Presupuesto.categoria == categoria,
        models.Presupuesto.mes == mes,
        models.Presupuesto.anio == anio
    ).first()

    if not presupuesto:
        return None

    gasto_actual = db.query(
        func.coalesce(func.sum(models.Movimiento.monto), 0)
    )\
    .join(models.Cuenta)\
    .filter(
        models.Cuenta.usuario_id == usuario_id,
        models.Movimiento.tipo == "gasto",
        models.Movimiento.categoria == categoria,
        extract("month", models.Movimiento.fecha) == mes,
        extract("year", models.Movimiento.fecha) == anio
    ).scalar()

    porcentaje = (gasto_actual / presupuesto.monto_limite) * 100

    if porcentaje >= 100:
        return "🚨 EXCEDISTE TU PRESUPUESTO"
    elif porcentaje >= 80:
        return "⚠️ Estás cerca del límite"

    return None
