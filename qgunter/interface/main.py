#!/usr/bin/env python3
"""Punto de entrada principal de Q-Gunter.

Este fichero se ejecuta cuando escribes 'q-gunter' en la terminal.
Soporta dos modos:
  - CLI: Con spinner y reintentos automáticos (por defecto)
  - Raw: Salida plana para debugging/automatización (--raw)
"""

import argparse
import asyncio
import sys

from rich.console import Console
from rich.text import Text


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="q-gunter",
        description="Q-Gunter — AI-Powered CTF Challenge Solver",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  q-gunter --target 10.10.11.234
  q-gunter --target https://ctf.example.com --instruction "WordPress site"
  q-gunter --target 10.10.11.50 --raw
  q-gunter --target challenge.htb --resume
        """,
    )
    parser.add_argument("-t", "--target", required=True, help="Target (URL, IP, domain)")
    parser.add_argument("-i", "--instruction", help="Custom challenge context or hints")
    parser.add_argument("-m", "--model", help="Claude model to use")
    parser.add_argument("-d", "--debug", action="store_true", help="Debug mode")
    parser.add_argument("--raw", action="store_true", help="Raw output (no spinner, plain text)")
    parser.add_argument("--version", action="version", version="%(prog)s 1.0.0")
    parser.add_argument("-r", "--resume", action="store_true", help="Resume most recent session")
    parser.add_argument("--session-id", help="Resume specific session by ID")
    parser.add_argument("--list-sessions", action="store_true", help="List saved sessions")
    return parser.parse_args()


def print_banner() -> None:
    console = Console()
    banner = Text()
    banner.append("🚩 ", style="bold #6366f1")
    banner.append("Q-Gunter", style="bold #6366f1")
    banner.append(" v1.0.0\n", style="dim")
    banner.append("AI-Powered CTF Solver — by Q-Gunter Team", style="dim italic")
    console.print()
    console.print(banner)
    console.print()


async def run_cli_mode(args: argparse.Namespace) -> None:
    """Modo CLI: con spinner y hasta 3 reintentos automáticos."""
    from qgunter.core.agent import run_agent
    from qgunter.core.session import SessionStore

    console = Console()

    # Determinar si hay sesión a reanudar
    resume_session = args.session_id
    if args.resume and not resume_session:
        latest = SessionStore().get_latest(args.target)
        if latest:
            resume_session = latest.session_id
            console.print(f"[dim]Resuming session: {resume_session}[/]")

    console.print(f"[bold]Target:[/] {args.target}")
    if args.instruction:
        console.print(f"[bold]Context:[/] {args.instruction}")
    console.print()

    max_attempts = 3
    attempt = 1
    custom_instruction = args.instruction
    total_cost = 0.0

    while attempt <= max_attempts:
        if attempt > 1:
            console.print(f"\n[bold cyan]Attempt {attempt}/{max_attempts}[/]")

        with console.status("[bold cyan]Solving CTF challenge...", spinner="dots"):
            result = await run_agent(
                target=args.target,
                custom_instruction=custom_instruction,
                model=args.model,
                debug=args.debug,
                resume_session=resume_session if attempt == 1 else None,
            )

        total_cost += result.get("cost_usd", 0)

        if result["success"]:
            flags_found = result.get("flags_found", [])
            if flags_found:
                console.print(f"\n[bold green]🚩 Solved! {len(flags_found)} flag(s):[/]")
                for flag in flags_found:
                    f = flag.get("flag", flag) if isinstance(flag, dict) else flag
                    console.print(f"  • [bold cyan]{f}[/]")
                session_id = result.get("session_id", "")
                if session_id:
                    console.print(f"[dim]Session: {session_id}[/]")
                if total_cost > 0:
                    console.print(f"[dim]Cost: ${total_cost:.4f}[/]")
                return
            else:
                console.print("[bold red]⚠ No flags captured[/]")
                if attempt < max_attempts:
                    if custom_instruction:
                        custom_instruction += "\n\nPREVIOUS ATTEMPT: No flags found. Try harder."
                    else:
                        custom_instruction = "IMPORTANT: Previous attempt failed. Try all techniques."
                    attempt += 1
                else:
                    console.print(f"[bold red]✗ Max attempts ({max_attempts}) reached[/]")
                    sys.exit(1)
        else:
            console.print(f"[bold red]✗ Failed:[/] {result.get('error', 'Unknown error')}")
            sys.exit(1)


async def run_raw_mode(args: argparse.Namespace) -> None:
    """Modo Raw: salida plana, ideal para debugging y automatización.

    Cada línea tiene el formato: [TIPO] contenido
    Tipos: INFO, TOOL, FLAG, STATE, DONE, ERROR, WARN
    """
    from qgunter.core.config import load_config
    from qgunter.core.controller import AgentController
    from qgunter.core.events import Event, EventBus, EventType
    from qgunter.core.session import SessionStore

    print(f"[INFO] Target: {args.target}")
    if args.instruction:
        print(f"[INFO] Instruction: {args.instruction}")
    if args.model:
        print(f"[INFO] Model: {args.model}")
    print("[INFO] Starting agent...", flush=True)

    events = EventBus.get()

    def on_message(event: Event) -> None:
        text = event.data.get("text", "")
        msg_type = event.data.get("type", "info")
        if text:
            print(f"[{msg_type.upper()}] {text}", flush=True)

    def on_tool(event: Event) -> None:
        status = event.data.get("status")
        name = event.data.get("name", "unknown")
        if status == "start":
            print(f"[TOOL] {name}: {event.data.get('args', {})}", flush=True)
        else:
            print(f"[TOOL] {name} done", flush=True)

    def on_flag(event: Event) -> None:
        flag = event.data.get("flag", "")
        if flag:
            print(f"[FLAG] {flag}", flush=True)

    def on_state(event: Event) -> None:
        state = event.data.get("state", "")
        details = event.data.get("details", "")
        msg = f"[STATE] {state}: {details}" if details else f"[STATE] {state}"
        print(msg, flush=True)

    events.subscribe(EventType.MESSAGE, on_message)
    events.subscribe(EventType.TOOL, on_tool)
    events.subscribe(EventType.FLAG_FOUND, on_flag)
    events.subscribe(EventType.STATE_CHANGED, on_state)

    resume_session = args.session_id
    if args.resume and not resume_session:
        latest = SessionStore().get_latest(args.target)
        if latest:
            resume_session = latest.session_id
            print(f"[INFO] Resuming session: {resume_session}", flush=True)

    config_kwargs: dict[str, object] = {"target": args.target}
    if args.instruction:
        config_kwargs["custom_instruction"] = args.instruction
    if args.model:
        config_kwargs["llm_model"] = args.model

    config = load_config(**config_kwargs)

    task = f"Solve this CTF challenge and capture the flag(s): {args.target}"
    if args.instruction:
        task += f"\n\nChallenge context: {args.instruction}"

    controller = AgentController(config)

    try:
        result = await controller.run(task, resume_session_id=resume_session)

        if result.get("success"):
            flags = result.get("flags_found", [])
            cost = result.get("cost_usd", 0)
            session_id = result.get("session_id", "")
            print(f"[DONE] Flags: {len(flags)}, Cost: ${cost:.4f}, Session: {session_id}", flush=True)
            if not flags:
                print("[WARN] No flags captured", flush=True)
                sys.exit(1)
        else:
            print(f"[ERROR] {result.get('error', 'Unknown')}", flush=True)
            sys.exit(1)
    except Exception as e:
        print(f"[ERROR] {e!s}", flush=True)
        sys.exit(1)


def list_sessions(target: str | None = None) -> None:
    from qgunter.core.session import SessionStore
    console = Console()
    session_list = SessionStore().list_sessions(target)

    if not session_list:
        console.print("[dim]No sessions found.[/]")
        return

    console.print(f"[bold]Sessions{f' for {target}' if target else ''}:[/]\n")
    console.print(f"{'ID':<10} {'Date':<18} {'Target':<25} {'Status':<12} {'Flags':<6}")
    console.print("-" * 75)
    for s in session_list:
        date_str = s.created_at.strftime("%Y-%m-%d %H:%M")
        t = s.target[:23] + ".." if len(s.target) > 25 else s.target
        console.print(f"{s.session_id:<10} {date_str:<18} {t:<25} {s.status.value:<12} {len(s.flags_found):<6}")


def main() -> None:
    """Punto de entrada principal."""
    args = parse_arguments()

    if args.list_sessions:
        list_sessions(args.target if hasattr(args, "target") else None)
        return

    if not args.raw:
        print_banner()

    try:
        if args.raw:
            asyncio.run(run_raw_mode(args))
        else:
            asyncio.run(run_cli_mode(args))
    except KeyboardInterrupt:
        Console().print("\n[yellow]Cancelled by user[/]")
        sys.exit(130)
    except Exception as e:
        Console().print(f"\n[bold red]Error:[/] {e!s}")
        import traceback
        Console().print(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()