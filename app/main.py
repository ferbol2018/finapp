from fastapi import FastAPI
from .database import engine
from . import models
from .routers import usuarios
from .routers import cuentas
from .routers import movimientos
from app.routers import dashboard
from app.routers import finanzas
from app.routers import transferencias
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

app = FastAPI(default_response_class=JSONResponse)

""" origins = [
    "http://localhost:49744",
    "http://localhost",
    "http://127.0.0.1:49744",
]  """

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
    "https://finanza-personal.netlify.app"
    ], #En PRO poner https://finanza-personal.netlify.app
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def force_utf8(request, call_next):
    response = await call_next(request)
    response.headers["Content-Type"] = "application/json; charset=utf-8"
    return response

app.include_router(usuarios.router)
app.include_router(cuentas.router)
app.include_router(movimientos.router)
app.include_router(dashboard.router)
app.include_router(finanzas.router)
app.include_router(transferencias.router)

@app.get("/")
def root():
    return {"mensaje": "API Finanzas funcionando"}




