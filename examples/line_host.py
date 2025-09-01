#!/usr/bin/env python3
import subprocess
import os
import json
import sys
import time

# Magic number constant for response truncation
MAX_RESPONSE_CHARS = 800

def run_bridge(env):
    # Spawn the bridge with pipes
    return subprocess.Popen(
        [sys.executable, "src/venice_browser_mcp.py"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        text=False,  # binary
    )

def rpc(p, method, params, mid):
    """Send RPC request and handle errors gracefully"""
    try:
        msg = json.dumps({"jsonrpc":"2.0","id":mid,"method":method,"params":params}, separators=(",",":")).encode("utf-8")
        # line framing -> one line per message
        p.stdin.write(msg + b"\n")
        p.stdin.flush()
        # read one line response
        line = p.stdout.readline()
        if not line:
            # Return JSON-RPC error response instead of raising exception
            return {"jsonrpc":"2.0","id":mid,"error":{"code":-32603,"message":"No response from child process"}}
        return json.loads(line.decode("utf-8", "replace"))
    except json.JSONDecodeError as e:
        # Return JSON-RPC error response for decode errors
        return {"jsonrpc":"2.0","id":mid,"error":{"code":-32700,"message":f"Parse error: {str(e)}"}}
    except Exception as e:
        # Return JSON-RPC error response for other errors
        return {"jsonrpc":"2.0","id":mid,"error":{"code":-32603,"message":f"Internal error: {str(e)}"}}

if __name__ == "__main__":
    print("Navigate...")
    env = os.environ.copy()
    env["MCP_FRAMING"] = "line"
    env["HEADLESS"] = "true"
    env["PYTHONUNBUFFERED"] = "1"
    
    # Proper subprocess management with context manager
    with run_bridge(env) as p:
        try:
            # give it a blink to start
            time.sleep(0.2)
            resp = rpc(p, "browser.navigate", {"url":"https://example.com"}, "nav-1")
            print("Response:", json.dumps(resp, indent=2)[:MAX_RESPONSE_CHARS], "...")
            # request a clean shutdown
            resp2 = rpc(p, "mcp.shutdown", {}, "bye-1")
            print("Shutdown:", json.dumps(resp2, indent=2)[:MAX_RESPONSE_CHARS], "...")
        finally:
            # Ensure proper cleanup
            try:
                if p.stdin and not p.stdin.closed:
                    p.stdin.close()
            except Exception:
                pass
            try:
                p.wait(timeout=10)
            except subprocess.TimeoutExpired:
                p.terminate()
                try:
                    p.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    p.kill()
