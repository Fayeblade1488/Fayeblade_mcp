#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
venice_browser_mcp.py — CLI wrapper for Browser MCP Bridge
"""
import os
import argparse
import asyncio
import sys
import pathlib

from venice_browser_mcp_core import main as core_main

def main():
    """
    Entry point for the Venice Browser MCP Bridge.

    This function initializes the asyncio event loop and runs the core main
    function, which handles the application's primary logic.
    """
    asyncio.run(core_main())

if __name__ == "__main__":
    main()
