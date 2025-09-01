#!/usr/bin/env python3
import subprocess, os, json, sys, re, time

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
    body = json.dumps(obj, separators=(",",":"), ensure_ascii=False).encode("utf-8")
    headers = f"Content-Length: {len(body)}\r\n\r\n".encode("ascii")
    p.stdin.write(headers + body)
    p.stdin.flush()

def read_cl(p):
    # Read headers
    headers = b""
    while True:
        line = p.stdout.readline()
        if not line:
            raise RuntimeError("EOF reading headers")
        if line in (b"\n", b"\r\n"):
            break
        headers += line
    m = re.search(br"Content-Length:\s*(\d+)", headers, flags=re.I)
    if not m:
        raise RuntimeError("No Content-Length header from child")
    length = int(m.group(1))
    body = p.stdout.read(length)
    return json.loads(body.decode("utf-8", "replace"))

if __name__ == "__main__":
    print("Navigate (content-length)...")
    env = os.environ.copy()
    env["MCP_FRAMING"] = "content-length"
    env["HEADLESS"] = "true"
    env["PYTHONUNBUFFERED"] = "1"
    with run_bridge(env) as p:
        try:
            time.sleep(0.2)
            write_cl(p, {"jsonrpc":"2.0","id":"nav-1","method":"browser.navigate","params":{"url":"https://example.com"}})
            resp = read_cl(p)
            print(json.dumps(resp, indent=2))
            write_cl(p, {"jsonrpc":"2.0","id":"bye-1","method":"mcp.shutdown","params":{}})
            resp2 = read_cl(p)
            print(json.dumps(resp2, indent=2))
        finally:
            try:
                p.stdin.close()
            except Exception:
                pass
            p.wait(timeout=10)
