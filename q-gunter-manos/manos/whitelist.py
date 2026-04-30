"""Lista blanca de comandos permitidos y definiciones de herramientas MCP.

Las definiciones de herramientas son lo que Claude Code lee al conectarse
al MCP Server. Deben coincidir exactamente con lo que Claude Code espera:
bash, read_file, write_file.
"""

from typing import Any

# Binarios permitidos en Manos
ALLOWED_COMMANDS: set[str] = {
    # Reconocimiento de red
    "nmap", "masscan", "rustscan",
    # Web
    "ffuf", "gobuster", "nikto", "curl", "wget", "wfuzz", "feroxbuster",
    # Explotación web
    "sqlmap",
    # Shells y redes
    "nc", "netcat", "socat",
    # Scripting
    "python3", "python", "bash", "sh", "perl", "ruby",
    # Hashes y criptografía
    "hashcat", "john", "openssl",
    # Análisis de ficheros
    "strings", "file", "binwalk", "xxd", "hexdump", "objdump", "readelf",
    # Utilidades de sistema
    "cat", "ls", "find", "grep", "awk", "sed", "cut",
    "echo", "printf", "head", "tail", "wc", "sort", "uniq",
    "chmod", "chown", "cp", "mv", "mkdir", "rm", "touch",
    "which", "env", "id", "whoami", "uname", "hostname",
    "ps", "ss", "netstat", "ip", "ifconfig", "ping", "traceroute",
    "tar", "unzip", "gunzip", "gzip", "zip",
    # Privilege escalation
    "sudo", "su",
    # SSH
    "ssh", "scp", "ssh-keygen", "ssh-copy-id",
    # Misc pentesting
    "hydra", "medusa", "crackmapexec", "impacket-scripts",
    "msfconsole", "msfvenom",
}


def is_command_allowed(command: str) -> bool:
    """Devuelve True si el binario está en la lista blanca."""
    return command in ALLOWED_COMMANDS


def get_tool_definitions() -> list[dict[str, Any]]:
    """
    Devuelve las definiciones de herramientas en formato MCP.

    Estas son exactamente las herramientas que Claude Code espera:
    bash, read_file, write_file. Al redirigirlas al MCP Server de Manos,
    Claude Code las ejecuta aquí en lugar de localmente en Cerebro.
    """
    return [
        {
            "name": "bash",
            "description": (
                "Execute a bash command on the Hands machine. "
                "This machine has network access to the target. "
                "Use this for all reconnaissance, exploitation, and post-exploitation tasks."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The bash command to execute",
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Timeout in seconds (default: 120)",
                        "default": 120,
                    },
                },
                "required": ["command"],
            },
        },
        {
            "name": "read_file",
            "description": (
                "Read the contents of a file on the Hands machine filesystem."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Absolute path to the file",
                    },
                },
                "required": ["path"],
            },
        },
        {
            "name": "write_file",
            "description": (
                "Write content to a file on the Hands machine filesystem. "
                "Use this to create exploit scripts, payloads, wordlists, etc."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Absolute path to write the file",
                    },
                    "content": {
                        "type": "string",
                        "description": "Content to write",
                    },
                },
                "required": ["path", "content"],
            },
        },
    ]
