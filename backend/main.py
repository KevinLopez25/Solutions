import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from api.v1.router import api_router
from core.config import settings
from core.database import Base, engine


def _print_db_banner():
    GREEN = '\033[92m'
    RED   = '\033[91m'
    BOLD  = '\033[1m'
    RESET = '\033[0m'

    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        symbol  = f'{GREEN}✓{RESET}'
        estado  = f'{GREEN}SU BASE DE DATOS ESTA CONECTADA ✅{RESET}'
    except Exception as exc:
        symbol  = f'{RED}✗{RESET}'
        estado  = f'{RED}TU BASE DE DATOS NO CONECTADA ❌ — {exc}{RESET}'

    print(f"\n{BOLD}┌─ Base de datos ─────────────────────────────┐{RESET}")
    print(f"{BOLD}│{RESET}  {symbol}  {estado}")
    print(f"{BOLD}│{RESET}  Host   : {settings.DB_HOST}:{settings.DB_PORT}")
    print(f"{BOLD}│{RESET}  BD     : {settings.DB_NAME}")
    print(f"{BOLD}│{RESET}  Usuario: {settings.DB_USER}")
    print(f"{BOLD}└─────────────────────────────────────────────┘{RESET}\n")


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as exc:
        print(f"[WARN] No se crearon las tablas: {exc}", file=sys.stderr)
    _print_db_banner()
    if not settings.GROQ_API_KEY:
        print("\n[WARN] La variable de entorno GROQ_API_KEY no está configurada. La IA no funcionará sin ella.\n")
    else:
        print("\n[INFO] GROQ_API_KEY está configurada. Servicio de IA listo.\n")
    yield


app = FastAPI(
    title="Solutions API",
    description="Generador de propuestas comerciales — Periferia IT",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/health")
def health():
    return {"status": "ok"}