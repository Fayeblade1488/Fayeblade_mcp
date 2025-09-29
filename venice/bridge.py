import sys
import os
import json
import asyncio
import platform
from typing import Any, Dict, Optional, Tuple
from playwright.async_api import async_playwright

# -----------------------------
# Low-noise stderr logging
# -----------------------------
def log(*args, **kwargs):
    """Logs a message to stderr, which is the designated logging stream."""
    print(*args, file=sys.stderr, **kwargs)

# -----------------------------
# Safe async stdout writer
# -----------------------------
class _AsyncStdoutWriter:
    """
    A safe, asynchronous writer for stdout that avoids common pitfalls.

    This writer buffers data in memory and flushes it to the underlying stream
    atomically. It is designed to prevent accidental logging or protocol
    corruption on stdout, which is reserved for MCP communication.

    Attributes:
        _stream: The underlying stream to write to (e.g., sys.stdout).
        _buf: A bytearray used as an internal buffer.
        _lock: An asyncio.Lock to ensure atomic drain operations.
    """

    def __init__(self, stream):
        self._stream = stream
        self._buf = bytearray()
        self._lock = asyncio.Lock()

    def write(self, data):
        """
        Appends data to the internal buffer.

        Args:
            data: The data to write, either as bytes or a string. If a string,
                  it will be encoded to UTF-8.
        """
        if isinstance(data, (bytes, bytearray)):
            self._buf.extend(data)
        else:
            self._buf.extend(str(data).encode('utf-8', 'replace'))

    async def drain(self):
        """
        Asynchronously flushes the buffer to the stream.

        This method acquires a lock to ensure that the write operation is
        atomic, preventing interleaved messages.
        """
        async with self._lock:
            if not self._buf:
                return
            b = bytes(self._buf)
            self._buf.clear()
            if hasattr(self._stream, "buffer"):
                self._stream.buffer.write(b)
            else:
                # Fallback (rare on modern Python)
                self._stream.write(b.decode('utf-8', 'replace'))
            self._stream.flush()

# -----------------------------
# Framers
# -----------------------------
class LineFramer:
    """
    Implements a line-based JSON message framing protocol.

    Each JSON message is expected to be on a new line.

    Args:
        reader: An asyncio.StreamReader to read incoming data from.
        writer: An _AsyncStdoutWriter to write outgoing messages to.
        timeout: The timeout in seconds for read operations.
    """
    def __init__(self, reader: asyncio.StreamReader, writer: _AsyncStdoutWriter, timeout: int):
        self.reader = reader
        self.writer = writer
        self.timeout = timeout

    async def read_message(self) -> Optional[Dict[str, Any]]:
        """
        Reads and decodes a single line-delimited JSON message.

        Returns:
            A dictionary representing the decoded JSON message, or None if
            the end of the stream is reached.
        """
        line = await asyncio.wait_for(self.reader.readline(), self.timeout)
        if not line:
            return None
        line = line.decode('utf-8', 'replace').strip()
        if not line:
            return None
        return json.loads(line)

    async def write_message(self, obj: Dict[str, Any]) -> None:
        """
        Encodes and writes a JSON message, followed by a newline.

        Args:
            obj: The dictionary to encode as a JSON message.
        """
        data = json.dumps(obj, separators=(",", ":"), ensure_ascii=False) + "\n"
        self.writer.write(data)
        await self.writer.drain()

class ContentLengthFramer:
    """
    Implements content-length based JSON message framing, similar to LSP.

    Each message is preceded by a 'Content-Length' header.

    Args:
        reader: An asyncio.StreamReader to read incoming data from.
        writer: An _AsyncStdoutWriter to write outgoing messages to.
        timeout: The timeout in seconds for read operations.
    """
    def __init__(self, reader: asyncio.StreamReader, writer: _AsyncStdoutWriter, timeout: int):
        self.reader = reader
        self.writer = writer
        self.timeout = timeout

    async def read_message(self) -> Optional[Dict[str, Any]]:
        """
        Reads a single content-length framed message.

        This method first parses headers to find the 'Content-Length', then
        reads that many bytes from the stream for the body.

        Returns:
            A dictionary representing the decoded JSON message, or None if
            the end of the stream is reached.

        Raises:
            RuntimeError: If the 'Content-Length' header is missing or invalid.
        """
        # Read headers
        content_length = None
        while True:
            line = await asyncio.wait_for(self.reader.readline(), self.timeout)
            if not line:
                return None
            line = line.decode('utf-8', 'replace').strip()
            if line == "":
                break
            if line.lower().startswith("content-length:"):
                try:
                    content_length = int(line.split(":", 1)[1].strip())
                    if content_length < 0:
                        raise RuntimeError("Invalid Content-Length: must be non-negative")
                except ValueError:
                    raise RuntimeError("Invalid Content-Length header")

        if content_length is None:
            raise RuntimeError("Missing Content-Length header")

        body = await asyncio.wait_for(self.reader.readexactly(content_length), self.timeout)
        return json.loads(body.decode('utf-8', 'replace'))

    async def write_message(self, obj: Dict[str, Any]) -> None:
        """
        Encodes and writes a JSON message with a Content-Length header.

        Args:
            obj: The dictionary to encode as a JSON message.
        """
        body = json.dumps(obj, separators=(",", ":"), ensure_ascii=False).encode('utf-8')
        headers = f"Content-Length: {len(body)}\r\n\r\n".encode('ascii')
        self.writer.write(headers + body)
        await self.writer.drain()

# -----------------------------
# Browser (Playwright)
# -----------------------------
class BrowserEnv:
    """
    Manages the Playwright browser environment, including launch and teardown.

    This class encapsulates the Playwright instance, browser, context, and page,
    providing a clean interface for browser operations.

    Args:
        headless: Whether to run the browser in headless mode.
        storage_state: Path to a file for persisting browser state (e.g., cookies).
        nav_timeout_ms: Default navigation timeout in milliseconds.
        browser_name: The name of the browser to use ('chromium', 'firefox', 'webkit').
    """
    def __init__(self, headless: bool, storage_state: str, nav_timeout_ms: int, browser_name: str):
        self.headless = headless
        self.storage_state = storage_state
        self.nav_timeout_ms = nav_timeout_ms
        self.browser_name = browser_name.strip().lower()
        self._pw = None
        self._browser = None
        self._context = None
        self._page = None

    async def ensure(self):
        """
        Ensures the browser is running and a page is available.

        If the browser is not already running, this method will start
        Playwright, launch the specified browser, and create a new
        context and page.
        """
        if self._pw is not None:
            return
        self._pw = await async_playwright().start()
        launcher = getattr(self._pw, self.browser_name, None)
        if launcher is None:
            raise RuntimeError(f"Unsupported browser '{self.browser_name}'. Use 'chromium', 'firefox', or 'webkit'.")
        self._browser = await launcher.launch(headless=self.headless)
        state_path = self.storage_state
        use_state = bool(state_path and os.path.exists(state_path))
        self._context = await self._browser.new_context(storage_state=state_path if use_state else None)
        self._context.set_default_timeout(self.nav_timeout_ms)
        self._page = await self._context.new_page()

    async def close(self):
        """
        Gracefully closes the browser and stops Playwright.

        This method will attempt to save the browser state if a path is
        provided before closing the browser and stopping the Playwright service.
        """
        try:
            if self._context:
                # Save state if a path is provided
                if self.storage_state:
                    try:
                        await self._context.storage_state(path=self.storage_state)
                    except Exception as e:
                        log(f"[bridge] error saving storage state to '{self.storage_state}': {e}")
            if self._browser:
                await self._browser.close()
        finally:
            if self._pw:
                await self._pw.stop()
        self._pw = self._browser = self._context = self._page = None

    async def navigate(self, url: str) -> Dict[str, Any]:
        """
        Navigates the browser to a specified URL.

        Args:
            url: The URL to navigate to.

        Returns:
            A dictionary containing the result of the navigation, including
            the final URL, page title, and status.
        """
        await self.ensure()
        assert self._page is not None
        resp = await self._page.goto(url, wait_until="load", timeout=self.nav_timeout_ms)
        # Pull final URL/title regardless of response being None (file or about pages)
        final_url = self._page.url
        title = await self._page.title()
        ok = True
        status = None
        if resp:
            try:
                status = resp.status
                ok = 200 <= status < 400
            except Exception:
                pass
        return {"ok": bool(ok), "status": status, "final_url": final_url, "title": title}

# -----------------------------
# Dispatcher
# -----------------------------
class Dispatcher:
    """
    Handles incoming RPC methods by dispatching them to the correct handler.

    Args:
        browser_env: An instance of BrowserEnv to interact with the browser.
    """
    def __init__(self, browser_env: BrowserEnv):
        self.browser = browser_env

    async def dispatch(self, method: str, params: Dict[str, Any]) -> Any:
        """
        Dispatches a method to its corresponding implementation.

        Args:
            method: The name of the RPC method to call.
            params: A dictionary of parameters for the method.

        Returns:
            The result of the method call.

        Raises:
            ValueError: If the method name is unknown.
            _Shutdown: As a signal to terminate the main loop gracefully.
        """
        if not isinstance(params, dict):
            raise InvalidParamsError("The 'params' field must be an object/dictionary.")

        if method == "ping":
            echo_val = params.get("echo")
            if echo_val is not None and not isinstance(echo_val, str):
                raise InvalidParamsError("ping requires the 'echo' parameter to be a string")
            return {"echo": echo_val}
        if method == "mcp.shutdown":
            # Signal the outer loop to stop by raising a sentinel.
            # The browser will be closed in the main loop's finally block.
            raise _Shutdown()
        if method == "browser.navigate":
            url = params.get("url")
            if not url or not isinstance(url, str):
                raise InvalidParamsError("browser.navigate requires a string 'url'")
            return await self.browser.navigate(url)
        raise ValueError(f"Unknown method: {method}")

class _Shutdown(Exception):
    """Sentinel exception to signal a graceful shutdown."""
    pass

class InvalidParamsError(ValueError):
    """Exception raised for invalid RPC parameters."""
    pass

# -----------------------------
# Main loop
# -----------------------------
def stdin_reader_thread(loop: asyncio.AbstractEventLoop, reader: asyncio.StreamReader):
    """
    Reads data from stdin in a separate thread and feeds it to a StreamReader.
    This is used on Windows where pipes for stdin are not supported by asyncio.
    """
    try:
        while True:
            chunk = sys.stdin.buffer.read(1)
            if not chunk:
                break
            loop.call_soon_threadsafe(reader.feed_data, chunk)
    except Exception:
        # This can happen if the main process closes stdin.
        pass
    finally:
        loop.call_soon_threadsafe(reader.feed_eof)

async def run_main(
    *,
    framing: str,
    headless: bool,
    storage_state: str,
    nav_timeout_ms: int,
    browser_name: str,
    io_timeout_s: int,
    reader: Optional[asyncio.StreamReader] = None,
    writer: Optional[_AsyncStdoutWriter] = None,
):
    """
    The main execution loop for the browser bridge.

    This function sets up the framer, browser environment, and dispatcher,
    then enters a loop to read, process, and respond to messages.

    Args:
        framing: The framing protocol to use ('line' or 'content-length').
        headless: Whether to run the browser in headless mode.
        storage_state: Path for browser state persistence.
        nav_timeout_ms: Navigation timeout in milliseconds.
        browser_name: The name of the browser to use.
        io_timeout_s: Timeout in seconds for I/O read operations.
        reader: (For testing) An asyncio.StreamReader to read from.
        writer: (For testing) An _AsyncStdoutWriter to write to.
    """
    loop = asyncio.get_running_loop()

    # If reader/writer are not provided, create them from stdin/stdout
    if reader is None:
        reader = asyncio.StreamReader()
        if platform.system() == "Windows":
            # On Windows, asyncio doesn't support reading from stdin via pipes.
            # We run a blocking read in a thread and feed the data to the stream.
            loop.run_in_executor(
                None, stdin_reader_thread, loop, reader
            )
        else:
            # On Unix-like systems, use the more efficient pipe transport.
            rproto = asyncio.StreamReaderProtocol(reader)
            await loop.connect_read_pipe(lambda: rproto, sys.stdin)

    if writer is None:
        writer = _AsyncStdoutWriter(sys.stdout)

    if framing == "content-length":
        framer = ContentLengthFramer(reader, writer, timeout=io_timeout_s)
    else:
        framer = LineFramer(reader, writer, timeout=io_timeout_s)

    browser_env = BrowserEnv(headless=headless, storage_state=storage_state, nav_timeout_ms=nav_timeout_ms, browser_name=browser_name)
    dispatcher = Dispatcher(browser_env)

    async def handle_one(msg: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        mid = msg.get("id")
        method = msg.get("method")
        params = msg.get("params") or {}
        try:
            result = await dispatcher.dispatch(method, params)
            return {"jsonrpc": "2.0", "id": mid, "result": result}
        except _Shutdown:
            return {"jsonrpc": "2.0", "id": mid, "result": {"ok": True, "shutdown": True}}
        except InvalidParamsError as e:
            return {"jsonrpc": "2.0", "id": mid, "error": {"code": -32602, "message": f"Invalid params: {e}"}}
        except Exception as e:
            # return an error object; still avoid stdout noise
            return {"jsonrpc": "2.0", "id": mid, "error": {"code": -32603, "message": f"Internal error: {e}"}}

    try:
        while True:
            msg = None
            try:
                msg = await framer.read_message()
            except (json.JSONDecodeError, RuntimeError) as e:
                log(f"[bridge] Unrecoverable read/parse error: {e}")
                error_resp = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32700, "message": f"Parse Error: {e}"},
                }
                await framer.write_message(error_resp)
                break  # Terminate connection
            except asyncio.TimeoutError:
                log(f"[bridge] I/O read timed out after {io_timeout_s}s")
                error_resp = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32000, "message": "Read operation timed out"},
                }
                await framer.write_message(error_resp)
                break # Terminate connection

            if msg is None:
                break
            resp = await handle_one(msg)
            if resp is not None:
                await framer.write_message(resp)
            # If shutdown was requested, exit after replying
            if resp and isinstance(resp.get("result"), dict) and resp["result"].get("shutdown"):
                break
    finally:
        try:
            # Ensure browser is closed on exit
            if 'browser_env' in locals() and browser_env:
                await browser_env.close()
        except Exception:
            # This can happen if the browser is already closing.
            # Avoids noisy errors on shutdown.
            pass
