#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
venice.cli — CLI wrapper for Browser MCP Bridge
"""
import asyncio
import sys

from venice.config import main as core_main

def main():
    """
    Entry point for the Venice Browser MCP Bridge.

    This function initializes the asyncio event loop and runs the core main
    function, which handles the application's primary logic.
    """
    asyncio.run(core_main())

if __name__ == "__main__":
    main()
