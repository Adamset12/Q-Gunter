"""Ejecutor de comandos para la máquina Manos.

Recibe comandos del MCP Server y los ejecuta localmente con:
- Lista blanca de binarios permitidos
- Timeout configurable por comando
- Captura de stdout, stderr y código de retorno
- Directorio de trabajo aislado
"""

import asyncio
import logging
import shlex
import time
from pathlib import Path
from typing import Any

from manos.whitelist import is_command_allowed

logger = logging.getLogger("manos.runner")

WORK_DIR = Path("/tmp/qgunter-workspace")
WORK_DIR.mkdir(parents=True, exist_ok=True)


async def run_command(command: str, timeout: int = 120) -> dict[str, Any]:
    """
    Ejecuta un comando bash en Manos.

    Acepta el string completo del comando (igual que Claude Code lo envía
    al tool 'bash') y lo ejecuta via subprocess.

    Args:
        command: String del comando completo, ej: "nmap -sV 10.10.11.234"
        timeout: Segundos máximos de ejecución

    Returns:
        dict con: stdout, stderr, rc, elapsed
    """
    if not command.strip():
        return {"stdout": "", "stderr": "Comando vacío", "rc": -1, "elapsed": 0.0}

    # Extraer el binario para verificar la lista blanca
    try:
        parts = shlex.split(command)
    except ValueError as e:
        return {"stdout": "", "stderr": f"Error parseando comando: {e}", "rc": -1, "elapsed": 0.0}

    binary = parts[0] if parts else ""

    if not is_command_allowed(binary):
        msg = f"[MANOS] Binario '{binary}' no está en la lista blanca."
        logger.warning(msg)
        return {"stdout": "", "stderr": msg, "rc": -1, "elapsed": 0.0}

    logger.info(f"Ejecutando: {command[:200]}")
    start = time.monotonic()

    try:
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(WORK_DIR),
        )

        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(),
                timeout=timeout,
            )
            rc = proc.returncode or 0

        except asyncio.TimeoutError:
            proc.kill()
            await proc.communicate()
            elapsed = time.monotonic() - start
            msg = f"[MANOS] Timeout ({timeout}s) para: {command[:100]}"
            logger.warning(msg)
            return {"stdout": "", "stderr": msg, "rc": -2, "elapsed": round(elapsed, 2)}

    except FileNotFoundError:
        return {
            "stdout": "",
            "stderr": f"[MANOS] Binario '{binary}' no encontrado en el sistema.",
            "rc": -3,
            "elapsed": 0.0,
        }
    except Exception as e:
        return {"stdout": "", "stderr": f"[MANOS] Error inesperado: {e}", "rc": -4, "elapsed": 0.0}

    elapsed = round(time.monotonic() - start, 2)
    stdout = stdout_bytes.decode(errors="replace")
    stderr = stderr_bytes.decode(errors="replace")

    logger.info(f"Completado rc={rc} elapsed={elapsed}s stdout_len={len(stdout)}")
    return {"stdout": stdout, "stderr": stderr, "rc": rc, "elapsed": elapsed}


async def read_file(path: str) -> dict[str, Any]:
    """Lee un fichero del filesystem de Manos."""
    try:
        content = Path(path).read_text(errors="replace")
        logger.info(f"read_file: {path} ({len(content)} chars)")
        return {"stdout": content, "stderr": "", "rc": 0, "elapsed": 0.0}
    except FileNotFoundError:
        return {"stdout": "", "stderr": f"Fichero no encontrado: {path}", "rc": 1, "elapsed": 0.0}
    except PermissionError:
        return {"stdout": "", "stderr": f"Sin permisos para leer: {path}", "rc": 1, "elapsed": 0.0}
    except Exception as e:
        return {"stdout": "", "stderr": str(e), "rc": 1, "elapsed": 0.0}


async def write_file(path: str, content: str) -> dict[str, Any]:
    """Escribe un fichero en el filesystem de Manos."""
    try:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
        logger.info(f"write_file: {path} ({len(content)} chars)")
        return {"stdout": f"Fichero escrito: {path}", "stderr": "", "rc": 0, "elapsed": 0.0}
    except PermissionError:
        return {"stdout": "", "stderr": f"Sin permisos para escribir: {path}", "rc": 1, "elapsed": 0.0}
    except Exception as e:
        return {"stdout": "", "stderr": str(e), "rc": 1, "elapsed": 0.0}

