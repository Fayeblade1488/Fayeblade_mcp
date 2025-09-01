#!/usr/bin/env python3
import subprocess, sys, os, json

SCRIPT = os.path.join(os.path.dirname(__file__), "..", "src", "venice_browser_mcp.py")
env = os.environ.copy()
env["MCP_FRAMING"] = "content-length"

def send_msg(p, obj):
    body = json.dumps(obj).encode("utf-8")
    header = f"Content-Length: {len(body)}\r\n\r\n".encode("ascii")
    p.stdin.write(header + body); p.stdin.flush()

def read_msg(p):
    content_length = None
    while True:
        line = p.stdout.readline()
        if not line: return None
        s = line.decode("utf-8", errors="replace")
        if s in ("\n", "\r\n"): break
        k, _, v = s.partition(":")
        if k.lower().strip() == "content-length": content_length = int(v.strip())
    body = p.stdout.read(content_length)
    return json.loads(body.decode("utf-8"))

p = subprocess.Popen([sys.executable, SCRIPT], stdin=subprocess.PIPE, stdout=subprocess.PIPE, env=env)
send_msg(p, {"jsonrpc":"2.0","id":"nav-1","method":"browser.navigate","params":{"url":"https://example.com"}})
print("Response:", json.dumps(read_msg(p), indent=2)[:800], "...")
p.stdin.close(); p.terminate()
