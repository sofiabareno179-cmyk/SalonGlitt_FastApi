"""Configuracion de entorno aislado para las pruebas."""
import os

os.environ.setdefault("SGE_SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("SGE_DATABASE_URL", "sqlite+aiosqlite:///:memory:")