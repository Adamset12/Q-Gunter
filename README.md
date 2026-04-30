# Q-Gunter

AI-Powered Autonomous Penetration Testing Agent — by Q-Gunter Team

## Quick Start

```bash
# Install
git clone https://github.com/tu-org/q-gunter.git
cd q-gunter
uv sync

# Authenticate with Claude (first time only)
claude login

# Run
uv run q-gunter --target 10.10.11.234
```
## Quick Start modo distribuido
## PARTE 3 — Cómo arrancarlo

### Paso 1 — Arrancar Manos (primero siempre)

```bash
# En la máquina Manos
cd q-gunter-manos
cp .env.example .env
# Editar .env y poner el token
python run_manos.py
```

Deberías ver:
```
INFO  Manos MCP Server arrancando en puerto 7331
INFO  Uvicorn running on http://0.0.0.0:7331
```

### Paso 2 — Verificar conectividad desde Cerebro

```bash
# Desde Cerebro — verificar que Manos responde
curl http://192.168.1.100:7331/health
# Esperado: {"status":"ok","machine":"manos"}

# Verificar autenticación
curl -H "Authorization: Bearer tu_token" http://192.168.1.100:7331/
# Esperado: JSON con la lista de herramientas MCP
```

### Paso 3 — Arrancar Cerebro

```bash
# En la máquina Cerebro
claude login  # si no está hecho ya
uv run q-gunter --target 10.10.11.234
```

Claude Code en Cerebro se conectará al MCP Server de Manos.
Toda ejecución de bash ocurrirá en Manos. El razonamiento, en Cerebro.

---
