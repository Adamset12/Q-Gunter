"""
MCP Server HTTP para la máquina Manos.

Implementa el protocolo MCP (Model Context Protocol) sobre HTTP+SSE.
Claude Code en Cerebro conecta aquí y envía tool_calls.
Este servidor las ejecuta localmente en Manos y devuelve los resultados.

Endpoints:
  GET  /          → manifest con lista de herramientas disponibles
  POST /tools/call → ejecutar una herramienta
  GET  /sse       → stream SSE para notificaciones (requerido por MCP)
  GET  /health    → verificación de estado
"""

import asyncio
import json
import logging
import os
import time
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from manos.auth import verify_token
from manos.runner import read_file, run_command, write_file
from manos.whitelist import get_tool_definitions

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("manos.server")

security = HTTPBearer()


# ── Modelos de request/response MCP ──────────────────────────────────────────

class ToolCallRequest(BaseModel):
    name: str
    arguments: dict[str, Any] = {}


class ToolCallResponse(BaseModel):
    content: list[dict[str, Any]]
    isError: bool = False


# ── Autenticación ─────────────────────────────────────────────────────────────

async def require_auth(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> str:
    token = credentials.credentials
    if not verify_token(token):
        logger.warning(f"Token inválido recibido")
        raise HTTPException(status_code=401, detail="Token inválido")
    return token


# ── App ───────────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info(f"Manos MCP Server arrancando en puerto {os.environ.get('MANOS_PORT', 7331)}")
    yield
    logger.info("Manos MCP Server detenido")


app = FastAPI(
    title="Q-Gunter Manos — MCP Server",
    version="1.0.0",
    lifespan=lifespan,
)


# ── Endpoints MCP ─────────────────────────────────────────────────────────────

@app.get("/health")
async def health() -> dict[str, str]:
    """Endpoint de verificación — no requiere auth."""
    return {"status": "ok", "machine": "manos"}


@app.get("/")
async def manifest(_: str = Depends(require_auth)) -> dict[str, Any]:
    """
    Manifest MCP: devuelve la lista de herramientas disponibles.
    Claude Code lee esto al conectarse para saber qué puede usar.
    """
    return {
        "protocolVersion": "2024-11-05",
        "serverInfo": {
            "name": "qgunter-manos",
            "version": "1.0.0",
        },
        "capabilities": {
            "tools": {},
        },
        "tools": get_tool_definitions(),
    }


@app.post("/tools/call")
async def call_tool(
    request: ToolCallRequest,
    _: str = Depends(require_auth),
) -> ToolCallResponse:
    """
    Ejecuta una herramienta en Manos.
    Claude Code llama aquí cuando quiere ejecutar bash, leer un fichero, etc.
    """
    tool_name = request.name
    args = request.arguments

    logger.info(f"Tool call: {tool_name} args={json.dumps(args)[:200]}")
    start = time.monotonic()

    try:
        if tool_name == "bash":
            command = args.get("command", "")
            timeout = int(args.get("timeout", 120))
            result = await run_command(command, timeout=timeout)

        elif tool_name == "read_file":
            path = args.get("path", "")
            result = await read_file(path)

        elif tool_name == "write_file":
            path = args.get("path", "")
            content = args.get("content", "")
            result = await write_file(path, content)

        else:
            return ToolCallResponse(
                content=[{"type": "text", "text": f"Herramienta '{tool_name}' no disponible en Manos."}],
                isError=True,
            )

        elapsed = round(time.monotonic() - start, 2)
        logger.info(f"Tool {tool_name} completada en {elapsed}s — rc={result.get('rc', '?')}")

        # Formatear output para Claude
        output_parts = []
        if result.get("stdout"):
            output_parts.append(result["stdout"])
        if result.get("stderr"):
            output_parts.append(f"[stderr]\n{result['stderr']}")
        if not output_parts:
            output_parts.append("(sin output)")

        is_error = result.get("rc", 0) != 0

        return ToolCallResponse(
            content=[{"type": "text", "text": "\n".join(output_parts)}],
            isError=is_error,
        )

    except Exception as e:
        logger.error(f"Error ejecutando {tool_name}: {e}")
        return ToolCallResponse(
            content=[{"type": "text", "text": f"Error en Manos: {e!s}"}],
            isError=True,
        )


@app.get("/sse")
async def sse_endpoint(
    request: Request,
    _: str = Depends(require_auth),
) -> StreamingResponse:
    """
    Endpoint SSE requerido por el protocolo MCP.
    Claude Code se suscribe aquí para recibir notificaciones del servidor.
    Mantiene la conexión abierta con heartbeats.
    """
    async def event_stream() -> AsyncGenerator[str, None]:
        yield "data: {\"type\": \"connected\", \"server\": \"manos\"}\n\n"
        try:
            while True:
                if await request.is_disconnected():
                    break
                yield ": heartbeat\n\n"
                await asyncio.sleep(15)
        except asyncio.CancelledError:
            pass

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
