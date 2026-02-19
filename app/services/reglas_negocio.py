def validar_saldo(cuenta, monto):
    if cuenta.saldo < monto:
        raise Exception("Saldo insuficiente")

def validar_cupo(tarjeta, monto):
    if tarjeta.cupo_disponible < monto:
        raise Exception("Cupo insuficiente")
