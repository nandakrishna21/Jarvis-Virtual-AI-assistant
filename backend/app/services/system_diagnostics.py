"""Local system diagnostics for JARVIS.

Read-only checks: CPU, RAM, disk, battery, network, top processes, and optional
OpenJarvis doctor. No files are modified.
"""
from __future__ import annotations

import os
import platform
import shutil
import subprocess
import time
from pathlib import Path

import psutil


ROOT = Path(__file__).resolve().parents[2]
OJ = ROOT / "external" / "OpenJarvis"


def _bytes_gb(value: float | int | None) -> float:
    return round(float(value or 0) / (1024 ** 3), 2)


def _disk_usage() -> list[dict]:
    disks = []
    seen = set()
    for part in psutil.disk_partitions(all=False):
        if os.name == "nt":
            key = part.device.upper()
        else:
            key = part.mountpoint
        if key in seen:
            continue
        seen.add(key)
        try:
            usage = psutil.disk_usage(part.mountpoint)
        except Exception:
            continue
        disks.append({
            "device": part.device,
            "mount": part.mountpoint,
            "fs": part.fstype,
            "total_gb": _bytes_gb(usage.total),
            "used_gb": _bytes_gb(usage.used),
            "free_gb": _bytes_gb(usage.free),
            "percent": usage.percent,
        })
    return disks


def _top_processes(limit: int = 5) -> list[dict]:
    procs = []
    for proc in psutil.process_iter(["pid", "name", "memory_percent", "cpu_percent"]):
        try:
            info = proc.info
            procs.append({
                "pid": info.get("pid"),
                "name": info.get("name") or "unknown",
                "memory_percent": round(float(info.get("memory_percent") or 0), 2),
                "cpu_percent": round(float(info.get("cpu_percent") or 0), 2),
            })
        except Exception:
            continue
    procs.sort(key=lambda p: (p["memory_percent"], p["cpu_percent"]), reverse=True)
    return procs[:limit]


def _battery() -> dict | None:
    try:
        b = psutil.sensors_battery()
    except Exception:
        b = None
    if not b:
        return None
    return {
        "percent": b.percent,
        "plugged_in": bool(b.power_plugged),
        "secs_left": b.secsleft,
    }


def _openjarvis_doctor(timeout: int = 120) -> dict:
    if not OJ.exists():
        return {"ok": False, "error": "OpenJarvis submodule not installed"}
    uv = shutil.which("uv")
    if not uv:
        return {"ok": False, "error": "uv not found in PATH"}
    cmd = [uv, "run", "jarvis", "doctor"]
    try:
        p = subprocess.run(cmd, cwd=str(OJ), capture_output=True, text=True, timeout=timeout)
        out = (p.stdout or "") + ("\n" + p.stderr if p.stderr else "")
        out = out.strip()
        tail = "\n".join(out.splitlines()[-60:])
        return {"ok": p.returncode == 0, "returncode": p.returncode, "output_tail": tail}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def quick_scan(include_openjarvis: bool = False) -> dict:
    vm = psutil.virtual_memory()
    cpu = psutil.cpu_percent(interval=0.4)
    disks = _disk_usage()
    top = _top_processes()
    battery = _battery()
    boot = None
    try:
        boot = int(psutil.boot_time())
    except Exception:
        pass
    result = {
        "ok": True,
        "type": "quick_scan",
        "timestamp": int(time.time()),
        "system": {
            "platform": platform.platform(),
            "python": platform.python_version(),
            "processor": platform.processor(),
            "hostname": platform.node(),
            "uptime_seconds": int(time.time() - boot) if boot else None,
        },
        "cpu": {"percent": cpu, "cores_logical": psutil.cpu_count(logical=True), "cores_physical": psutil.cpu_count(logical=False)},
        "memory": {
            "total_gb": _bytes_gb(vm.total),
            "available_gb": _bytes_gb(vm.available),
            "used_gb": _bytes_gb(vm.used),
            "percent": vm.percent,
        },
        "disks": disks,
        "top_processes": top,
        "battery": battery,
    }
    if include_openjarvis:
        result["openjarvis_doctor"] = _openjarvis_doctor()
    return result


def summarize(scan: dict) -> str:
    mem = scan.get("memory", {})
    cpu = scan.get("cpu", {})
    disks = scan.get("disks", [])
    lines = [
        f"Quick scan: CPU {cpu.get('percent', '?')}%, RAM {mem.get('used_gb', '?')}/{mem.get('total_gb', '?')} GB used ({mem.get('percent', '?')}%), free {mem.get('available_gb', '?')} GB.",
    ]
    for d in disks[:4]:
        lines.append(f"Disk {d.get('mount')}: {d.get('free_gb')} GB free of {d.get('total_gb')} GB ({d.get('percent')}% used).")
    batt = scan.get("battery")
    if batt:
        state = "plugged in" if batt.get("plugged_in") else "on battery"
        lines.append(f"Battery: {batt.get('percent')}% ({state}).")
    top = scan.get("top_processes", [])[:3]
    if top:
        procs = ", ".join(f"{p['name']} {p['memory_percent']}%" for p in top)
        lines.append(f"Top memory processes: {procs}.")
    oj = scan.get("openjarvis_doctor")
    if oj:
        lines.append("OpenJarvis doctor: " + ("ok" if oj.get("ok") else f"issue ({oj.get('error') or oj.get('returncode')})"))
    return " ".join(lines)
