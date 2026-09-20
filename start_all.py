"""
NutriAgent - Unified Service Launcher & Health Monitor
------------------------------------------------------
Starts all 4 agents, monitors real-time health, renders a clean
terminal dashboard, and auto-opens the Security Web UI.
"""

import os
import sys
import time
import signal
import subprocess
import webbrowser
import json
from urllib import request, error

# Enable ANSI Virtual Terminal Sequences on Windows 10/11 CMD & PowerShell
def enable_windows_ansi():
    if sys.platform == "win32":
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            # STD_OUTPUT_HANDLE = -11
            handle = kernel32.GetStdHandle(-11)
            mode = ctypes.c_ulong()
            if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
                # ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
                kernel32.SetConsoleMode(handle, mode.value | 0x0004)
        except Exception:
            pass
        os.system("")

enable_windows_ansi()

# Color definitions
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"

AGENTS = [
    {
        "id": "security",
        "name": "Security & Validation Agent",
        "module": "security_agent.main:app",
        "port": 8001,
        "health_url": "http://localhost:8001/health",
    },
    {
        "id": "intake",
        "name": "Intake & Profile Agent",
        "module": "intake_agent.main:app",
        "port": 8002,
        "health_url": "http://localhost:8002/health",
    },
    {
        "id": "ir",
        "name": "Nutrition IR Agent",
        "module": "ir_agent.main:app",
        "port": 8003,
        "health_url": "http://localhost:8003/health",
    },
    {
        "id": "planning",
        "name": "Meal Planning Agent",
        "module": "planning_agent.main:app",
        "port": 8004,
        "health_url": "http://localhost:8004/health",
    },
]

processes = []
log_files = []


def check_health(url: str, timeout: float = 1.5) -> dict | None:
    try:
        req = request.Request(url, headers={"User-Agent": "NutriAgent-HealthCheck/1.0"})
        with request.urlopen(req, timeout=timeout) as response:
            if response.status == 200:
                data = response.read().decode("utf-8")
                return json.loads(data)
    except Exception:
        return None
    return None


def cleanup(signum=None, frame=None):
    print(f"\n\n{YELLOW}Stopping all NutriAgent services...{RESET}")
    for p in processes:
        try:
            if sys.platform == "win32":
                subprocess.call(
                    ["taskkill", "/F", "/T", "/PID", str(p.pid)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            else:
                p.terminate()
        except Exception:
            pass
    for f in log_files:
        try:
            f.close()
        except Exception:
            pass
    print(f"{GREEN}All services stopped cleanly. Goodbye!{RESET}")
    sys.exit(0)


def main():
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)

    root_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(root_dir)
    logs_dir = os.path.join(root_dir, "logs")
    os.makedirs(logs_dir, exist_ok=True)

    # Clear terminal screen
    os.system("cls" if sys.platform == "win32" else "clear")

    print(f"{CYAN}{BOLD}")
    print("==========================================================================")
    print("           NUTRIAGENT - MULTI-AGENT SYSTEM LAUNCHER & MONITOR")
    print("==========================================================================")
    print(f"{RESET}")
    print(f" Root Directory : {root_dir}")
    print(f" Service Logs   : {logs_dir}")
    print("--------------------------------------------------------------------------\n")

    # Start all 4 agents
    for agent in AGENTS:
        log_path = os.path.join(logs_dir, f"{agent['id']}.log")
        log_file = open(log_path, "w", encoding="utf-8")
        log_files.append(log_file)

        cmd = [
            sys.executable,
            "-m",
            "uvicorn",
            agent["module"],
            "--port",
            str(agent["port"]),
        ]

        print(f" Launching {agent['name']:<30} [Port {agent['port']}] ...")
        proc = subprocess.Popen(
            cmd,
            cwd=root_dir,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            env=os.environ.copy(),
        )
        processes.append(proc)

    print(f"\n{YELLOW}Waiting for agents to become healthy (models loading)...{RESET}\n")

    # Poll status
    agent_status = {a["id"]: {"online": False, "details": "Initializing..."} for a in AGENTS}
    max_wait = 45  # allow time for spacy and sentence-transformers
    start_time = time.time()
    opened_browser = False

    while time.time() - start_time < max_wait:
        all_online = True

        for i, agent in enumerate(AGENTS):
            aid = agent["id"]
            proc = processes[i]

            # Check if process crashed
            if proc.poll() is not None:
                agent_status[aid]["online"] = False
                agent_status[aid]["details"] = f"CRASHED (Exit code {proc.returncode})"
                all_online = False
                continue

            # If already online, skip checking
            if agent_status[aid]["online"]:
                continue

            health = check_health(agent["health_url"])
            if health:
                agent_status[aid]["online"] = True
                detail = f"Healthy (agent: {health.get('agent', aid)})"
                if "indexed_items" in health:
                    detail += f" - {health['indexed_items']} items"
                agent_status[aid]["details"] = detail
                print(f"  {GREEN}[ONLINE]{RESET}  {agent['name']:<30} (Port {agent['port']}) -> {detail}")
            else:
                all_online = False

        if all_online:
            break

        time.sleep(1.5)

    # Print final summary table
    print("\n" + "=" * 74)
    print(f" {BOLD}{'Agent Service':<32} {'Port':<8} {'Status':<14} {'Details':<20}{RESET}")
    print("-" * 74)
    for agent in AGENTS:
        info = agent_status[agent["id"]]
        name = agent["name"]
        port = str(agent["port"])
        if info["online"]:
            status = f"{GREEN}ONLINE{RESET}"
        else:
            status = f"{RED}FAILED{RESET}"
        print(f" {name:<32} {port:<8} {status:<18} {info['details']}")
    print("=" * 74)

    all_ok = all(s["online"] for s in agent_status.values())

    if all_ok:
        print(f"\n{GREEN}{BOLD} SUCCESS: All 4 agents are ONLINE and integrated!{RESET}")
        print(f"\n Opening Security Console UI in your browser: {CYAN}http://localhost:8001{RESET}")
        webbrowser.open("http://localhost:8001")
    else:
        print(f"\n{YELLOW} WARNING: One or more agents did not start.{RESET}")
        print(" Check the relevant log file in the 'logs/' folder:")
        for agent in AGENTS:
            if not agent_status[agent["id"]]["online"]:
                log_p = os.path.join(logs_dir, f"{agent['id']}.log")
                print(f"   -> logs/{agent['id']}.log")
                if os.path.exists(log_p):
                    with open(log_p, "r", encoding="utf-8", errors="replace") as lf:
                        lines = [line.strip() for line in lf.readlines() if line.strip()]
                        if lines:
                            print(f"      Last error: {lines[-1]}")

    print("\n--------------------------------------------------------------------------")
    print(" Interactive Endpoints:")
    print(f"   * Security Console UI  : {CYAN}http://localhost:8001{RESET}")
    print(f"   * Security API Docs    : {CYAN}http://localhost:8001/docs{RESET}")
    print(f"   * Intake API Docs      : {CYAN}http://localhost:8002/docs{RESET}")
    print(f"   * Nutrition IR Docs    : {CYAN}http://localhost:8003/docs{RESET}")
    print(f"   * Planning API Docs    : {CYAN}http://localhost:8004/docs{RESET}")
    print("--------------------------------------------------------------------------")
    print(f" {BOLD}Press Ctrl+C at any time to shut down all agents.{RESET}\n")

    # Keep alive loop
    try:
        while True:
            time.sleep(5)
            for i, p in enumerate(processes):
                if p.poll() is not None:
                    agent = AGENTS[i]
                    print(f" {RED}[ALERT] {agent['name']} exited with code {p.returncode}. Check logs/{agent['id']}.log{RESET}")
    except KeyboardInterrupt:
        cleanup()


if __name__ == "__main__":
    main()
