from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .. import models, schemas, database
from ..auth import get_current_user

router = APIRouter(prefix="/cuentas", tags=["Cuentas"])

@router.post("/")
def crear_cuenta(
    cuenta: schemas.CuentaCreate,
    db: Session = Depends(database.get_db),
    current_user: models.Usuario = Depends(get_current_user)
):

    if cuenta.tipo == "credito":
        nueva_cuenta = models.Cuenta(
            usuario_id=current_user.id,
            tipo=cuenta.tipo,
            nombre=cuenta.nombre,
            saldo=None,
            cupo_total=cuenta.cupo_total,
            cupo_disponible=cuenta.cupo_total
        )
    else:
        nueva_cuenta = models.Cuenta(
            usuario_id=current_user.id,
            tipo=cuenta.tipo,
            nombre=cuenta.nombre,
            saldo=cuenta.saldo,
            cupo_total=None,
            cupo_disponible=None
        )

    db.add(nueva_cuenta)
    db.commit()
    db.refresh(nueva_cuenta)

    return nueva_cuenta

