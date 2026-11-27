"""Lightweight ComfyUI diagnostics via its HTTP API."""
import json
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError

def check_server(base_url, timeout=8):
    base_url=base_url.rstrip('/')
    report={"url":base_url,"reachable":False,"queue":None,"error":None}
    try:
        with urlopen(base_url+"/system_stats",timeout=timeout) as r:
            report["system"]=json.loads(r.read().decode())
        with urlopen(base_url+"/queue",timeout=timeout) as r:
            report["queue"]=json.loads(r.read().decode())
        report["reachable"]=True
    except (HTTPError,URLError,TimeoutError,OSError,ValueError) as exc:
        report["error"]=f"{type(exc).__name__}: {exc}"
    return report

def format_queue(report):
    if not report.get("reachable"):
        return "Server unavailable: "+str(report.get("error","unknown error"))
    queue=report.get("queue") or {}
    running=queue.get("queue_running",[])
    pending=queue.get("queue_pending",[])
    return f"Connected. Running jobs: {len(running)} · Pending jobs: {len(pending)}"
