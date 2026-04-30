"""Punto de entrada de la máquina Manos.

Arranca el MCP Server HTTP que Claude Code usa desde Cerebro.

Uso:
    python run_manos.py

Variables de entorno requeridas (en .env):
    MANOS_TOKEN  — token compartido con Cerebro
    MANOS_PORT   — puerto HTTP (por defecto 7331)
    MANOS_HOST   — IP donde escuchar (por defecto 0.0.0.0)
"""

import os
import sys

from dotenv import load_dotenv

load_dotenv()

# Verificar configuración mínima antes de arrancar
if not os.environ.get("MANOS_TOKEN"):
    print("[ERROR] MANOS_TOKEN no configurado.")
    print("Crea un fichero .env con:")
    print("  MANOS_TOKEN=tu_token_secreto_compartido_con_cerebro")
    sys.exit(1)

import uvicorn
from manos.server import app

host = os.environ.get("MANOS_HOST", "0.0.0.0")
port = int(os.environ.get("MANOS_PORT", "7331"))

if __name__ == "__main__":
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info",
    )
