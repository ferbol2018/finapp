from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.finanzas_service import dashboard_financiero

router = APIRouter(prefix="/finanzas", tags=["Finanzas"])


@router.get("/dashboard/{usuario_id}")
def obtener_dashboard(usuario_id: int, db: Session = Depends(get_db)):
    return dashboard_financiero(usuario_id, db)
