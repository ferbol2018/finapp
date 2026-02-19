import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

if not DATABASE_URL:
    raise ValueError("No se encontró DATABASE_URL")

if not SECRET_KEY:
    raise ValueError("No se encontró SECRET_KEY")
