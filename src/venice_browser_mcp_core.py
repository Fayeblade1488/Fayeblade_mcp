import os
import sys
import asyncio
from .venice_browser_mcp_v23_impl import run_main

def _bool_env(name: str, default: bool) -> bool:
    v = os.environ.get(name)
    if v is None:
        return default
    v = v.strip().lower()
    return v in ("1","true","yes","on")

async def main():
    framing = os.environ.get("MCP_FRAMING", "line").strip().lower()
    headless = _bool_env("HEADLESS", True)
    storage_state = os.environ.get("MCP_STORAGE_STATE", "state.json")
    nav_timeout_ms = int(os.environ.get("NAV_TIMEOUT", "30000"))
    browser_name = os.environ.get("BROWSER", "chromium").strip().lower()

    # All diagnostics go to stderr
    print(f"[bridge] starting with framing={framing}, browser={browser_name}, headless={headless}", file=sys.stderr, flush=True)
    await run_main(
        framing=framing,
        headless=headless,
        storage_state=storage_state,
        nav_timeout_ms=nav_timeout_ms,
        browser_name=browser_name,
    )
