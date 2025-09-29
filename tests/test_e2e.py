import pytest
import subprocess
import json
import sys
import threading
from queue import Queue, Empty

def read_output(pipe, queue):
    """Reads lines from a pipe and puts them in a queue."""
    try:
        for line in iter(pipe.readline, b''):
            queue.put(line)
    finally:
        pipe.close()

@pytest.mark.e2e
def test_end_to_end_navigation():
    """
    Tests the full application lifecycle from the command line.
    - Launches the bridge as a subprocess.
    - Sends a 'browser.navigate' command via stdin.
    - Receives a response via stdout.
    - Sends a 'shutdown' command.
    """
    # 1. Launch the bridge as a subprocess under coverage
    command = [sys.executable, "-m", "coverage", "run", "--parallel-mode", "-m", "venice.cli"]
    process = subprocess.Popen(
        command,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env={"MCP_FRAMING": "line", "HEADLESS": "true", "PYTHONUNBUFFERED": "1"},
        text=False  # Work with bytes
    )

    # 2. Set up non-blocking reading of the subprocess's stdout
    q = Queue()
    t = threading.Thread(target=read_output, args=(process.stdout, q))
    t.daemon = True
    t.start()

    try:
        # 3. Send a 'browser.navigate' command
        nav_command = {
            "id": "e2e-nav-1",
            "method": "browser.navigate",
            "params": {"url": "https://example.com/"}
        }
        process.stdin.write((json.dumps(nav_command) + "\n").encode('utf-8'))
        process.stdin.flush()

        # 4. Read the response from stdout
        try:
            # Wait for a response, with a timeout
            nav_response_raw = q.get(timeout=20)
        except Empty:
            pytest.fail("Did not receive a response from the bridge in time.")

        nav_response = json.loads(nav_response_raw.decode('utf-8'))

        # 5. Assert the navigation was successful
        assert nav_response["id"] == "e2e-nav-1"
        assert nav_response["result"]["ok"] is True
        assert nav_response["result"]["final_url"] == "https://example.com/"
        assert nav_response["result"]["title"] == "Example Domain"

        # 6. Send a shutdown command
        shutdown_command = {"id": "e2e-shutdown-1", "method": "mcp.shutdown", "params": {}}
        process.stdin.write((json.dumps(shutdown_command) + "\n").encode('utf-8'))
        process.stdin.flush()

        # 7. Wait for the process to terminate
        process.wait(timeout=10)
        assert process.returncode == 0

    finally:
        # Ensure the process is terminated even if the test fails
        if process.poll() is None:
            process.kill()

        # Print stderr for debugging purposes, especially on failure
        stderr_output = process.stderr.read().decode('utf-8')
        if stderr_output:
            print("\n--- Subprocess Stderr ---\n", stderr_output)

        t.join(timeout=1)