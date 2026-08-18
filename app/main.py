from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import auth, categorias, concepts, debts, deudores, entries, summary, tareas

app = FastAPI(title="Finanzapp API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(categorias.router)
app.include_router(concepts.router)
app.include_router(debts.router)
app.include_router(deudores.router)
app.include_router(entries.router)
app.include_router(summary.router)
app.include_router(tareas.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
