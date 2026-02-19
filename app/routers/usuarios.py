from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .. import models, schemas, database, auth
from ..auth import verify_password, create_access_token
from fastapi.security import OAuth2PasswordRequestForm

router = APIRouter(prefix="/usuarios", tags=["Usuarios"])

@router.post("/registro")
def registrar(usuario: schemas.UsuarioCreate, db: Session = Depends(database.get_db)):
    hashed = auth.hash_password(usuario.password)

    nuevo_usuario = models.Usuario(
        nombre=usuario.nombre,
        email=usuario.email,
        password_hash=hashed
    )

    db.add(nuevo_usuario)
    db.commit()
    db.refresh(nuevo_usuario)

    return {"mensaje": "Usuario creado correctamente"}

@router.post("/login")
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(database.get_db)
):

    usuario = db.query(models.Usuario).filter(
        models.Usuario.email == form_data.username
    ).first()

    if not usuario:
        raise HTTPException(status_code=400, detail="Usuario no existe")

    if not verify_password(form_data.password, usuario.password_hash):
        raise HTTPException(status_code=400, detail="Contraseña incorrecta")

    token = create_access_token({"sub": str(usuario.id)})

    return {
        "access_token": token,
        "token_type": "bearer"
    }