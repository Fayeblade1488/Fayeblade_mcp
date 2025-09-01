import asyncio
from .venice_browser_mcp_core import main as core_main

def main():
    asyncio.run(core_main())

if __name__ == "__main__":
    main()
