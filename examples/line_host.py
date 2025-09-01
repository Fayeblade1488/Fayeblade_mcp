#!/usr/bin/env python3
import subprocess, os, json, sys, time

def run_bridge(env):
    # Spawn the bridge with pipes
    env = env.copy()  # Don't modify the passed env
    env["PYTHONPATH"] = "."
    return subprocess.Popen(
        [sys.executable, "src/venice_browser_mcp.py"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        text=False,  # binary
    )

def rpc(p, method, params, mid):
    msg = json.dumps({"jsonrpc":"2.0","id":mid,"method":method,"params":params}, separators=(",",":")).encode("utf-8")
    # line framing -> one line per message
    p.stdin.write(msg + b"\n")
    p.stdin.flush()
    # read one line response
    line = p.stdout.readline()
    if not line:
        raise RuntimeError("No response from child process")
    return json.loads(line.decode("utf-8", "replace"))

if __name__ == "__main__":
    print("Navigate...")
    env = os.environ.copy()
    env["MCP_FRAMING"] = "line"
    env["HEADLESS"] = "true"
    env["PYTHONUNBUFFERED"] = "1"
    with run_bridge(env) as p:
        try:
            # give it a blink to start
            time.sleep(0.2)
            resp = rpc(p, "browser.navigate", {"url":"https://example.com"}, "nav-1")
            print(json.dumps(resp, indent=2))
            # request a clean shutdown
            resp2 = rpc(p, "mcp.shutdown", {}, "bye-1")
            print(json.dumps(resp2, indent=2))
        finally:
            try:
                p.stdin.close()
            except Exception:
                pass
            p.wait(timeout=10)
