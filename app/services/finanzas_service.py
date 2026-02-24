from sqlalchemy.orm import Session
from app.models import Cuenta
import re

def dashboard_financiero(usuario_id: int, db: Session):

    cuentas = db.query(Cuenta).filter(
        Cuenta.usuario_id == usuario_id
    ).all()

    liquidez = 0
    inversiones = 0
    deuda = 0

    for cuenta in cuentas:

        if cuenta.tipo_cuenta in ["debito", "ahorro"]:
            liquidez += float(cuenta.saldo or 0)

        elif cuenta.tipo_cuenta == "inversion":
            inversiones += float(cuenta.saldo or 0)

        elif cuenta.tipo_cuenta == "credito":
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


def parsear_movimiento(texto: str):

    texto_lower = texto.lower()

    # 🔹 detectar tipo
    ingreso_keywords = ["salario", "ingreso", "me pagaron", "deposito", "gané"]

    tipo = "ingreso" if any(k in texto_lower for k in ingreso_keywords) else "gasto"

    # 🔹 detectar monto
    match = re.search(r'(\d[\d\.,]*)', texto_lower)
    monto = float(match.group(1).replace(".", "").replace(",", "")) if match else 0

    # 🔹 detectar categoria
    categorias = {
        "Alimentación": ["verduras", "comida", "frutas", "mercado", "olimpica", "exito", "Ara"],
        "Transporte": ["uber", "bus", "taxi", "gasolina"],
        "Ocio": ["cine", "juegos", "netflix"],
        "Salud": ["medico", "farmacia"],
        "Recibos": ["luz", "agua", "gas", "internet", "plan movil"],
    }

    categoria_detectada = "General"

    for cat, palabras in categorias.items():
        if any(p in texto_lower for p in palabras):
            categoria_detectada = cat
            break

    # 🔹 limpiar descripcion
    descripcion = re.sub(r'\d[\d\.,]*', '', texto)
    descripcion = descripcion.replace("por", "").strip()

    return {
        "tipo": tipo,
        "monto": monto,
        "categoria": categoria_detectada,
        "descripcion": descripcion
    }