"""Point d'entrée de l'API GestionEcole."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import auth, classes, eleves, referentiel

app = FastAPI(title="GestionEcole API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(referentiel.router)
app.include_router(classes.router)
app.include_router(eleves.router)


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok"}
