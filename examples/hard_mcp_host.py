#!/usr/bin/env python3
import subprocess
import os
import json
import sys
import re
import time

# Magic number constant for response truncation
MAX_RESPONSE_CHARS = 800

def run_bridge(env):
    return subprocess.Popen(
        [sys.executable, "src/venice_browser_mcp.py"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        text=False,  # binary
    )

def write_cl(p, obj):
    """Write content-length framed message"""
    try:
        body = json.dumps(obj, separators=(",",":"), ensure_ascii=False).encode("utf-8")
        headers = f"Content-Length: {len(body)}\r\n\r\n".encode("ascii")
        p.stdin.write(headers + body)
        p.stdin.flush()
    except Exception as e:
        print(f"Error writing message: {e}", file=sys.stderr)
        raise

def read_cl(p):
    """Read content-length framed message with proper error handling"""
    try:
        # Read headers
        headers = b""
        while True:
            line = p.stdout.readline()
            if not line:
                # Return JSON-RPC error instead of raising exception
                return {"jsonrpc":"2.0","id":None,"error":{"code":-32603,"message":"EOF reading headers"}}
            if line in (b"\n", b"\r\n"):
                break
            headers += line
        
        m = re.search(br"Content-Length:\s*(\d+)", headers, flags=re.I)
        if not m:
            return {"jsonrpc":"2.0","id":None,"error":{"code":-32603,"message":"No Content-Length header from child"}}
        
        length = int(m.group(1))
        body = p.stdout.read(length)
        if len(body) != length:
            return {"jsonrpc":"2.0","id":None,"error":{"code":-32603,"message":"Incomplete body read"}}
        
        return json.loads(body.decode("utf-8", "replace"))
        
    except json.JSONDecodeError as e:
        return {"jsonrpc":"2.0","id":None,"error":{"code":-32700,"message":f"Parse error: {str(e)}"}}
    except Exception as e:
        return {"jsonrpc":"2.0","id":None,"error":{"code":-32603,"message":f"Internal error: {str(e)}"}}

if __name__ == "__main__":
    print("Navigate (content-length)...")
    env = os.environ.copy()
    env["MCP_FRAMING"] = "content-length"
    env["HEADLESS"] = "true"
    env["PYTHONUNBUFFERED"] = "1"
    
    # Proper subprocess management with context manager
    with run_bridge(env) as p:
        try:
            time.sleep(0.2)
            write_cl(p, {"jsonrpc":"2.0","id":"nav-1","method":"browser.navigate","params":{"url":"https://example.com"}})
            resp = read_cl(p)
            print("Response:", json.dumps(resp, indent=2)[:MAX_RESPONSE_CHARS], "...")
            write_cl(p, {"jsonrpc":"2.0","id":"bye-1","method":"mcp.shutdown","params":{}})
            resp2 = read_cl(p)
            print("Shutdown:", json.dumps(resp2, indent=2)[:MAX_RESPONSE_CHARS], "...")
        finally:
            # Ensure proper cleanup
            try:
                if p.stdin is not None and not p.stdin.closed:
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
