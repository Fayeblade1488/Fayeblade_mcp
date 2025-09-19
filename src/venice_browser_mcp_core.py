import os
import sys
import asyncio
from venice_browser_mcp_v23_impl import run_main

def _bool_env(name: str, default: bool) -> bool:
    """
    Retrieves a boolean value from an environment variable.

    Args:
        name: The name of the environment variable.
        default: The default value to return if the variable is not set.

    Returns:
        True if the environment variable is one of "1", "true", "yes", "on"
        (case-insensitive). False otherwise.
    """
    v = os.environ.get(name)
    if v is None:
        return default
    v = v.strip().lower()
    return v in ("1", "true", "yes", "on")


async def main():
    """
    Configures and runs the main application logic.

    This async function reads configuration from environment variables,
    prints a startup message to stderr, and then calls the `run_main`
    function from the implementation module with the resolved config.
    """
    framing = os.environ.get("MCP_FRAMING", "line").strip().lower()
    # Support both new MCP_* and legacy environment variables for backward compatibility
    headless = _bool_env("MCP_HEADLESS", _bool_env("HEADLESS", True))
    storage_state = os.environ.get("MCP_STORAGE_STATE", "state.json")
    try:
        nav_timeout_ms = int(os.environ.get("MCP_NAV_TIMEOUT_MS", os.environ.get("NAV_TIMEOUT", "30000")))
    except ValueError:
        nav_timeout_ms = 30000
        print(f"[bridge] warning: invalid timeout value; falling back to {nav_timeout_ms}ms", file=sys.stderr, flush=True)
    browser_name = os.environ.get("MCP_BROWSER", os.environ.get("BROWSER", "chromium")).strip().lower()

    # All diagnostics go to stderr
    print(f"[bridge] starting with framing={framing}, browser={browser_name}, headless={headless}", file=sys.stderr, flush=True)
    await run_main(
        framing=framing,
        headless=headless,
        storage_state=storage_state,
        nav_timeout_ms=nav_timeout_ms,
        browser_name=browser_name,
    )
