"""Configuração central do app (equivalente a TursoClient + BuildConfig do Android)."""
from __future__ import annotations

import os
import sys
from pathlib import Path


def _pasta_app() -> Path:
    """Pasta do .env: ao lado do .exe (PyInstaller) ou a pasta python-app."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


try:  # opcional: carrega .env se python-dotenv estiver instalado
    from dotenv import load_dotenv

    # override=True: o .env vale mais que variáveis antigas do Windows (evita usar token velho).
    load_dotenv(_pasta_app() / ".env", override=True)
except Exception:  # pragma: no cover
    pass

# Banco Turso (mesmo do app Android) — HTTP API v2/pipeline
TURSO_BASE_URL = os.getenv(
    "TURSO_BASE_URL",
    "https://receitas-recuperado-fiscon.aws-us-east-2.turso.io/",
).rstrip("/")

# O token NÃO fica no código: defina TURSO_AUTH_TOKEN no arquivo .env (veja .env.example).
TURSO_AUTH_TOKEN = os.getenv("TURSO_AUTH_TOKEN", "")

# Worker/servidor de IA (extract-recipe, generate-seasonal-recipe, search-video-recipes)
MEAL_AI_BASE_URL = os.getenv(
    "MEAL_AI_BASE_URL",
    "https://culinaria-meal-ai.culinaria-meal-ai-worker.workers.dev/",
).rstrip("/")

HTTP_TIMEOUT = float(os.getenv("HTTP_TIMEOUT", "30"))
AI_TIMEOUT = float(os.getenv("AI_TIMEOUT", "100"))

# Pasta onde os PDFs gerados são salvos
PDF_DIR = Path(os.getenv("PDF_DIR", Path.home() / "Documentos" / "Receitas"))

# Estado do cardápio semanal (equivalente ao SharedPreferences)
STATE_DIR = Path(os.getenv("STATE_DIR", Path.home() / ".culinaria"))

# Pasta padrão dos backups
BACKUP_DIR = Path(os.getenv("BACKUP_DIR", Path.home() / "Documentos" / "Receitas" / "backups"))
