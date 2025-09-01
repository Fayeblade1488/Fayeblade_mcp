#!/usr/bin/env python3
import json, subprocess, sys, os

SCRIPT = os.path.join(os.path.dirname(__file__), "..", "src", "venice_browser_mcp.py")
env = os.environ.copy()
env["MCP_FRAMING"] = "line"

p = subprocess.Popen([sys.executable, SCRIPT], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, env=env)

def rpc(method, params, id_):
    msg = {"jsonrpc":"2.0","id":id_,"method":method,"params":params}
    p.stdin.write(json.dumps(msg) + "\n")
    p.stdin.flush()
    return json.loads(p.stdout.readline())

print("Navigate...")
resp = rpc("browser.navigate", {"url":"https://example.com"}, "nav-1")
print("Response:", json.dumps(resp, indent=2)[:800], "...")
p.stdin.close(); p.terminate()
