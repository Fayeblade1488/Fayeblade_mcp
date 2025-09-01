#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
venice_browser_mcp.py — CLI wrapper for Browser MCP Bridge (v2.4)
Safe for stand-alone execution (python src/venice_browser_mcp.py) and package import.
"""
import os
import argparse
import asyncio
import sys
import pathlib

# Ensure this file's directory is on sys.path so imports work in stand-alone mode
THIS_DIR = pathlib.Path(__file__).resolve().parent
if str(THIS_DIR) not in sys.path:
    sys.path.insert(0, str(THIS_DIR))

from venice_browser_mcp_core import main as core_main

def parse_args():
    p = argparse.ArgumentParser(description="Venice Browser MCP Bridge")
    p.add_argument("--framing", choices=["line", "content-length"], help="Message framing mode")
    p.add_argument("--persist", action="store_true", help="Persist browser context (cookies/session)")
    p.add_argument("--storage", default=None, help="Path to storage_state JSON file")
    p.add_argument("--headless", choices=["1","0"], help="Headless browser (1=headless, 0=headed)")
    p.add_argument("--nav-timeout-ms", type=int, help="Navigation timeout in ms")
    p.add_argument("--sel-timeout-ms", type=int, help="Selector timeout in ms")
    p.add_argument("--max-content-chars", type=int, help="Trim page text/html to this many chars")
    p.add_argument("--max-base64-bytes", type=int, help="Max base64 size for screenshots (bytes)")
    p.add_argument("--user-agent", help="Override browser User-Agent string")
    p.add_argument("--save-state-every", choices=["1","0"], help="Save storage_state after each request (1) or only on exit (0)")
    return p.parse_args()

def main():
    a = parse_args()
    if a.framing: os.environ["MCP_FRAMING"] = a.framing
    if a.persist: os.environ["MCP_PERSIST_CONTEXT"] = "1"
    if a.storage: os.environ["MCP_STORAGE_STATE"] = a.storage
    if a.headless: os.environ["MCP_HEADLESS"] = a.headless
    if a.nav_timeout_ms is not None: os.environ["MCP_NAV_TIMEOUT_MS"] = str(a.nav_timeout_ms)
    if a.sel_timeout_ms is not None: os.environ["MCP_SEL_TIMEOUT_MS"] = str(a.sel_timeout_ms)
    if a.max_content_chars is not None: os.environ["MCP_MAX_CONTENT_CHARS"] = str(a.max_content_chars)
    if a.max_base64_bytes is not None: os.environ["MCP_MAX_BASE64_BYTES"] = str(a.max_base64_bytes)
    if a.user_agent: os.environ["MCP_USER_AGENT"] = a.user_agent
    if a.save_state_every: os.environ["MCP_SAVE_STATE_EVERY"] = a.save_state_every
    asyncio.run(core_main())

if __name__ == "__main__":
    main()
