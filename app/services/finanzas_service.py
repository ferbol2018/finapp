from sqlalchemy.orm import Session
from app.models import Cuenta


def dashboard_financiero(usuario_id: int, db: Session):

    cuentas = db.query(Cuenta).filter(
        Cuenta.usuario_id == usuario_id
    ).all()

    liquidez = 0
    inversiones = 0
    deuda = 0

    for cuenta in cuentas:

        if cuenta.tipo in ["debito", "ahorro"]:
            liquidez += float(cuenta.saldo or 0)

        elif cuenta.tipo == "inversion":
            inversiones += float(cuenta.saldo or 0)

        elif cuenta.tipo == "credito":
            usado = float((cuenta.cupo_total or 0) - (cuenta.cupo_disponible or 0))
            deuda += usado

    patrimonio_neto = liquidez + inversiones - deuda

    # Ratio de endeudamiento
    activos = liquidez + inversiones
    if activos > 0:
        ratio_endeudamiento = round((deuda / activos) * 100, 2)
    else:
        ratio_endeudamiento = 0

    # Nivel de salud financiera
    if ratio_endeudamiento < 30:
        nivel_salud = "🟢 Saludable"
    elif ratio_endeudamiento < 60:
        nivel_salud = "🟡 Riesgo Moderado"
    else:
        nivel_salud = "🔴 Alto Riesgo"

    return {
        "resumen": {
            "liquidez": round(liquidez, 2),
            "inversiones": round(inversiones, 2),
            "deuda": round(deuda, 2),
            "patrimonio_neto": round(patrimonio_neto, 2),
        },
        "indicadores": {
            "ratio_endeudamiento_porcentaje": ratio_endeudamiento,
            "nivel_salud_financiera": nivel_salud
        }
    }
