from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .. import models, schemas, database
from ..auth import get_current_user
from decimal import Decimal
from sqlalchemy import func, extract
from app.services.presupuesto_service import evaluar_presupuesto
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from fastapi import Query
from collections import defaultdict


router = APIRouter(prefix="/movimientos", tags=["Movimientos"])


@router.post("/")
def crear_movimiento(
    movimiento: schemas.MovimientoCreate,
    db: Session = Depends(database.get_db),
    current_user: models.Usuario = Depends(get_current_user)
):

    try:
        # 🔹 Buscar cuenta del usuario
        cuenta = db.query(models.Cuenta).filter(
            models.Cuenta.id == movimiento.cuenta_id,
            models.Cuenta.usuario_id == current_user.id
        ).first()

        if not cuenta:
            raise HTTPException(status_code=404, detail="Cuenta no encontrada")

        monto = Decimal(movimiento.monto)

        # 🔥 LÓGICA FINANCIERA
        if cuenta.tipo == "credito":

            if movimiento.tipo == "gasto":

                if cuenta.cupo_disponible < monto:
                    raise HTTPException(status_code=400, detail="Cupo insuficiente")

                cuenta.cupo_disponible -= monto

            elif movimiento.tipo == "ingreso":
                # Pago a tarjeta
                cuenta.cupo_disponible += monto

                if cuenta.cupo_disponible > cuenta.cupo_total:
                    cuenta.cupo_disponible = cuenta.cupo_total


        else:  # débito, ahorro, inversión

            if movimiento.tipo == "gasto":

                if cuenta.saldo < monto:
                    raise HTTPException(status_code=400, detail="Saldo insuficiente")

                cuenta.saldo = Decimal(cuenta.saldo) - monto

            elif movimiento.tipo == "ingreso":
                cuenta.saldo = Decimal(cuenta.saldo) + monto


        # 🔹 Crear movimiento
        nuevo_movimiento = models.Movimiento(
            usuario_id=current_user.id,
            cuenta_id=cuenta.id,
            tipo=movimiento.tipo,
            monto=monto,
            descripcion=movimiento.descripcion,
            categoria=movimiento.categoria,
            transaction_id = movimiento.transaction_id or None  # 🔥 nuevo
        )

        db.add(cuenta)
        db.add(nuevo_movimiento)
        db.commit()
        db.refresh(nuevo_movimiento)

        # 🔔 Evaluación automática de presupuesto
        alerta = None

        if movimiento.tipo == "gasto":
            mes_actual = nuevo_movimiento.fecha.month
            anio_actual = nuevo_movimiento.fecha.year

            alerta = evaluar_presupuesto(
                db=db,
                usuario_id=current_user.id,
                categoria=nuevo_movimiento.categoria,
                mes=mes_actual,
                anio=anio_actual
            )

        return {
            "movimiento": {
                "id": nuevo_movimiento.id,
                "tipo": nuevo_movimiento.tipo,
                "monto": float(nuevo_movimiento.monto),
                "categoria": nuevo_movimiento.categoria,
                "cuenta_id": nuevo_movimiento.cuenta_id
            },
            "alerta": alerta
        }

    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500, detail="Error al procesar el movimiento")
    

@router.get("/")
def obtener_todos_movimientos(
    agrupar: bool = Query(False),
    db: Session = Depends(database.get_db),
    current_user: models.Usuario = Depends(get_current_user)
):

    movimientos = db.query(models.Movimiento)\
        .filter(models.Movimiento.usuario_id == current_user.id)\
        .order_by(models.Movimiento.fecha.desc())\
        .all()

    # 🔹 Si no se quiere agrupar
    if not agrupar:
        return movimientos

    # 🔥 Agrupar por transaction_id
    agrupados = defaultdict(list)

    for m in movimientos:
        key = m.transaction_id if m.transaction_id else f"single-{m.id}"
        agrupados[key].append(m)

    resultado = []

    for key, grupo in agrupados.items():

        # 🔹 Movimiento normal
        if grupo[0].transaction_id is None:
            m = grupo[0]
            resultado.append({
                "id": m.id,
                "tipo": m.tipo,
                "monto": float(m.monto),
                "categoria": m.categoria,
                "descripcion": m.descripcion,
                "fecha": m.fecha
            })

        # 🔥 Transferencia
        else:
            salida = next((m for m in grupo if m.tipo == "gasto"), None)
            entrada = next((m for m in grupo if m.tipo == "ingreso"), None)

            if salida and salida.usuario_id == current_user.id:
                tipo_transferencia = "transferencia_enviada"
                monto = -float(salida.monto)
                descripcion = f"Enviado a {entrada.cuenta.nombre}" if entrada else "Transferencia enviada"

            elif entrada and entrada.usuario_id == current_user.id:
                tipo_transferencia = "transferencia_recibida"
                monto = float(entrada.monto)
                descripcion = f"Recibido de {salida.cuenta.nombre}" if salida else "Transferencia recibida"

            else:
                tipo_transferencia = "transferencia"
                monto = float(grupo[0].monto)
                descripcion = "Transferencia"

            resultado.append({
                "transaction_id": key,
                "tipo": tipo_transferencia,
                "monto": monto,
                "descripcion": descripcion,
                "cuenta_origen": salida.cuenta.nombre if salida else None,
                "cuenta_destino": entrada.cuenta.nombre if entrada else None,
                "fecha": grupo[0].fecha
            })

    resultado.sort(key=lambda x: x["fecha"], reverse=True)

    return resultado



@router.get("/cuenta/{cuenta_id}")
def obtener_movimientos(
    cuenta_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.Usuario = Depends(get_current_user)
):
    cuenta = db.query(models.Cuenta).filter(
        models.Cuenta.id == cuenta_id,
        models.Cuenta.usuario_id == current_user.id
    ).first()

    if not cuenta:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada")

    movimientos = db.query(models.Movimiento).filter(
        models.Movimiento.cuenta_id == cuenta_id
    ).order_by(models.Movimiento.fecha.desc()).all()

    return movimientos

@router.get("/resumen")
def resumen_financiero(
    db: Session = Depends(database.get_db),
    current_user: models.Usuario = Depends(get_current_user)
):

    total_ingresos = db.query(func.coalesce(func.sum(models.Movimiento.monto), 0))\
        .join(models.Cuenta)\
        .filter(
            models.Cuenta.usuario_id == current_user.id,
            models.Movimiento.tipo == "ingreso"
        ).scalar()

    total_gastos = db.query(func.coalesce(func.sum(models.Movimiento.monto), 0))\
        .join(models.Cuenta)\
        .filter(
            models.Cuenta.usuario_id == current_user.id,
            models.Movimiento.tipo == "gasto"
        ).scalar()

    balance = total_ingresos - total_gastos

    total_cuentas = db.query(models.Cuenta)\
        .filter(models.Cuenta.usuario_id == current_user.id)\
        .count()

    return {
        "total_ingresos": total_ingresos,
        "total_gastos": total_gastos,
        "balance_actual": balance,
        "total_cuentas": total_cuentas
    }

@router.get("/resumen-mensual")
def resumen_mensual(
    anio: int,
    mes: int,
    db: Session = Depends(database.get_db),
    current_user: models.Usuario = Depends(get_current_user)
):

    ingresos = db.query(func.coalesce(func.sum(models.Movimiento.monto), 0))\
        .join(models.Cuenta)\
        .filter(
            models.Cuenta.usuario_id == current_user.id,
            models.Movimiento.tipo == "ingreso",
            extract("year", models.Movimiento.fecha) == anio,
            extract("month", models.Movimiento.fecha) == mes
        ).scalar()

    gastos = db.query(func.coalesce(func.sum(models.Movimiento.monto), 0))\
        .join(models.Cuenta)\
        .filter(
            models.Cuenta.usuario_id == current_user.id,
            models.Movimiento.tipo == "gasto",
            extract("year", models.Movimiento.fecha) == anio,
            extract("month", models.Movimiento.fecha) == mes
        ).scalar()

    return {
        "anio": anio,
        "mes": mes,
        "ingresos": ingresos,
        "gastos": gastos,
        "balance": ingresos - gastos
    }

@router.get("/comparativo-anual")
def comparativo_anual(
    anio: int,
    db: Session = Depends(database.get_db),
    current_user: models.Usuario = Depends(get_current_user)
):

    resultados = db.query(
        extract("month", models.Movimiento.fecha).label("mes"),
        models.Movimiento.tipo,
        func.coalesce(func.sum(models.Movimiento.monto), 0).label("total")
    )\
    .join(models.Cuenta)\
    .filter(
        models.Cuenta.usuario_id == current_user.id,
        extract("year", models.Movimiento.fecha) == anio
    )\
    .group_by("mes", models.Movimiento.tipo)\
    .all()

    # 🔥 Crear estructura base con los 12 meses
    resumen = {
        mes: {
            "mes": mes,
            "ingresos": 0,
            "gastos": 0,
            "balance": 0
        }
        for mes in range(1, 13)
    }

    # 🔥 Llenar con datos reales
    for mes, tipo, total in resultados:
        mes = int(mes)

        if tipo == "ingreso":
            resumen[mes]["ingresos"] = total
        elif tipo == "gasto":
            resumen[mes]["gastos"] = total

    # 🔥 Calcular balance
    for mes in resumen:
        resumen[mes]["balance"] = (
            resumen[mes]["ingresos"] - resumen[mes]["gastos"]
        )

    # 🔥 Retornar lista ordenada
    return list(resumen.values())

@router.get("/estadisticas-categorias")
def estadisticas_categorias(
    db: Session = Depends(database.get_db),
    current_user: models.Usuario = Depends(get_current_user)
):

    resultados = db.query(
        models.Movimiento.categoria,
        func.coalesce(func.sum(models.Movimiento.monto), 0).label("total")
    )\
    .join(models.Cuenta)\
    .filter(
        models.Cuenta.usuario_id == current_user.id,
        models.Movimiento.tipo == "gasto"
    )\
    .group_by(models.Movimiento.categoria)\
    .order_by(func.sum(models.Movimiento.monto).desc())\
    .all()

    total_general = sum(r.total for r in resultados)

    estadisticas = []

    for categoria, total in resultados:
        porcentaje = (total / total_general * 100) if total_general > 0 else 0

        estadisticas.append({
            "categoria": categoria,
            "total": total,
            "porcentaje": round(porcentaje, 2)
        })

    return estadisticas

@router.get("/comparativo-categoria")
def comparativo_categoria(
    anio: int,
    mes_actual: int,
    db: Session = Depends(database.get_db),
    current_user: models.Usuario = Depends(get_current_user)
):

    # Calcular mes anterior
    if mes_actual == 1:
        mes_anterior = 12
        anio_anterior = anio - 1
    else:
        mes_anterior = mes_actual - 1
        anio_anterior = anio

    # Consulta mes actual
    actual = db.query(
        models.Movimiento.categoria,
        func.coalesce(func.sum(models.Movimiento.monto), 0).label("total")
    )\
    .join(models.Cuenta)\
    .filter(
        models.Cuenta.usuario_id == current_user.id,
        models.Movimiento.tipo == "gasto",
        extract("year", models.Movimiento.fecha) == anio,
        extract("month", models.Movimiento.fecha) == mes_actual
    )\
    .group_by(models.Movimiento.categoria)\
    .all()

    # Consulta mes anterior
    anterior = db.query(
        models.Movimiento.categoria,
        func.coalesce(func.sum(models.Movimiento.monto), 0).label("total")
    )\
    .join(models.Cuenta)\
    .filter(
        models.Cuenta.usuario_id == current_user.id,
        models.Movimiento.tipo == "gasto",
        extract("year", models.Movimiento.fecha) == anio_anterior,
        extract("month", models.Movimiento.fecha) == mes_anterior
    )\
    .group_by(models.Movimiento.categoria)\
    .all()

    # Convertir a diccionarios
    actual_dict = {a.categoria: a.total for a in actual}
    anterior_dict = {a.categoria: a.total for a in anterior}

    # Unir categorías
    categorias = set(actual_dict.keys()) | set(anterior_dict.keys())

    resultado = []

    for categoria in categorias:
        total_actual = actual_dict.get(categoria, 0)
        total_anterior = anterior_dict.get(categoria, 0)

    if total_anterior > 0:
        variacion = ((total_actual - total_anterior) / total_anterior) * 100
    else:
        variacion = None

        resultado.append({
            "categoria": categoria,
            "mes_actual": total_actual,
            "mes_anterior": total_anterior,
            "diferencia": total_actual - total_anterior,
            "variacion_porcentual": round(variacion, 2) if variacion is not None else None
        })

    return resultado

@router.get("/alertas-categorias")
def alertas_categorias(
    anio: int,
    mes_actual: int,
    umbral: float = 20,
    db: Session = Depends(database.get_db),
    current_user: models.Usuario = Depends(get_current_user)
):

    # Calcular mes anterior
    if mes_actual == 1:
        mes_anterior = 12
        anio_anterior = anio - 1
    else:
        mes_anterior = mes_actual - 1
        anio_anterior = anio

    # Mes actual
    actual = db.query(
        models.Movimiento.categoria,
        func.coalesce(func.sum(models.Movimiento.monto), 0).label("total")
    )\
    .join(models.Cuenta)\
    .filter(
        models.Cuenta.usuario_id == current_user.id,
        models.Movimiento.tipo == "gasto",
        extract("year", models.Movimiento.fecha) == anio,
        extract("month", models.Movimiento.fecha) == mes_actual
    )\
    .group_by(models.Movimiento.categoria)\
    .all()

    # Mes anterior
    anterior = db.query(
        models.Movimiento.categoria,
        func.coalesce(func.sum(models.Movimiento.monto), 0).label("total")
    )\
    .join(models.Cuenta)\
    .filter(
        models.Cuenta.usuario_id == current_user.id,
        models.Movimiento.tipo == "gasto",
        extract("year", models.Movimiento.fecha) == anio_anterior,
        extract("month", models.Movimiento.fecha) == mes_anterior
    )\
    .group_by(models.Movimiento.categoria)\
    .all()

    actual_dict = {a.categoria: a.total for a in actual}
    anterior_dict = {a.categoria: a.total for a in anterior}

    categorias = set(actual_dict.keys()) | set(anterior_dict.keys())

    alertas = []

    for categoria in categorias:
        total_actual = actual_dict.get(categoria, 0)
        total_anterior = anterior_dict.get(categoria, 0)

        # 🔥 Caso 1: Nuevo gasto
        if total_actual > 0 and total_anterior == 0:
            alertas.append({
                "categoria": categoria,
                "tipo_alerta": "nuevo_gasto",
                "variacion_porcentual": None
            })
            continue

        # 🔥 Caso 2: Aumento significativo
        if total_anterior > 0:
            variacion = ((total_actual - total_anterior) / total_anterior) * 100
            if variacion > umbral:
                alertas.append({
                    "categoria": categoria,
                    "tipo_alerta": "aumento_significativo",
                    "variacion_porcentual": round(variacion, 2)
                })

    return alertas

@router.get("/presupuesto-sugerido")
def presupuesto_sugerido(
    anio: int,
    margen: float = 10,  # % adicional opcional
    db: Session = Depends(database.get_db),
    current_user: models.Usuario = Depends(get_current_user)
):

    resultados = db.query(
        models.Movimiento.categoria,
        extract("month", models.Movimiento.fecha).label("mes"),
        func.coalesce(func.sum(models.Movimiento.monto), 0).label("total")
    )\
    .join(models.Cuenta)\
    .filter(
        models.Cuenta.usuario_id == current_user.id,
        models.Movimiento.tipo == "gasto",
        extract("year", models.Movimiento.fecha) == anio
    )\
    .group_by(models.Movimiento.categoria, "mes")\
    .all()

    # Organizar datos por categoría
    categorias = {}

    for categoria, mes, total in resultados:
        if categoria not in categorias:
            categorias[categoria] = []
        categorias[categoria].append(total)

    presupuesto = []

    for categoria, valores in categorias.items():
        promedio = sum(valores) / len(valores)

        sugerido = promedio * (1 + margen / 100)

        presupuesto.append({
            "categoria": categoria,
            "promedio_mensual": round(promedio, 2),
            "presupuesto_sugerido": round(sugerido, 2)
        })

    return presupuesto

@router.post("/presupuestos")
def crear_presupuesto(
    categoria: str,
    monto_limite: float,
    mes: int,
    anio: int,
    db: Session = Depends(database.get_db),
    current_user: models.Usuario = Depends(get_current_user)
):

    nuevo = models.Presupuesto(
        categoria=categoria,
        monto_limite=monto_limite,
        mes=mes,
        anio=anio,
        usuario_id=current_user.id
    )

    db.add(nuevo)
    db.commit()

    return {"mensaje": "Presupuesto creado"}

@router.get("/presupuestos/alertas")
def revisar_alertas(
    mes: int,
    anio: int,
    db: Session = Depends(database.get_db),
    current_user: models.Usuario = Depends(get_current_user)
):

    presupuestos = db.query(models.Presupuesto).filter(
        models.Presupuesto.usuario_id == current_user.id,
        models.Presupuesto.mes == mes,
        models.Presupuesto.anio == anio
    ).all()

    alertas = []

    for p in presupuestos:

        gasto_actual = db.query(
            func.coalesce(func.sum(models.Movimiento.monto), 0)
        )\
        .join(models.Cuenta)\
        .filter(
            models.Cuenta.usuario_id == current_user.id,
            models.Movimiento.tipo == "gasto",
            models.Movimiento.categoria == p.categoria,
            extract("month", models.Movimiento.fecha) == mes,
            extract("year", models.Movimiento.fecha) == anio
        ).scalar()

        porcentaje = (gasto_actual / p.monto_limite) * 100 if p.monto_limite > 0 else 0

        estado = "OK"

        if porcentaje >= 100:
            estado = "EXCEDIDO"
        elif porcentaje >= 80:
            estado = "ALERTA"

        alertas.append({
            "categoria": p.categoria,
            "limite": p.monto_limite,
            "gastado": gasto_actual,
            "porcentaje": round(porcentaje, 2),
            "estado": estado
        })

    return alertas
