import asyncio
import json
import pytest
import os
from unittest.mock import MagicMock, AsyncMock, patch

from venice.bridge import ContentLengthFramer, LineFramer, run_main, _AsyncStdoutWriter

class MockStreamReader(asyncio.StreamReader):
    def __init__(self, data):
        super().__init__()
        self.feed_data(data)
        self.feed_eof()

class MockAsyncWriter(_AsyncStdoutWriter):
    def __init__(self):
        self.written_data = bytearray()
        # We don't need the stream or lock for this mock
        self._buf = self.written_data

    async def drain(self):
        # The real drain clears the buffer, we don't want that for inspection
        pass

@pytest.fixture
def mock_browser_env_fixture():
    """Fixture to provide a mocked BrowserEnv instance."""
    with patch('venice.bridge.BrowserEnv') as MockBrowserEnv:
        mock_instance = MockBrowserEnv.return_value
        mock_instance.close = AsyncMock()
        yield mock_instance

@pytest.mark.asyncio
async def test_content_length_framer_invalid_header_is_handled(mock_browser_env_fixture):
    """
    Test that the main loop handles a malformed Content-Length header gracefully.
    """
    # 1. Prepare a malformed message
    malformed_message = b"Content-Length: not-a-number\r\n\r\n"

    # 2. Mock the environment
    mock_reader = MockStreamReader(malformed_message)
    mock_writer = MockAsyncWriter()

    # 3. Run the main loop, passing mocks directly
    await run_main(
        framing="content-length",
        headless=True,
        storage_state="",
        nav_timeout_ms=1000,
        browser_name="chromium",
        io_timeout_s=1,
        reader=mock_reader,
        writer=mock_writer,
    )

    # 4. Assert that a JSON-RPC error was written
    output_bytes = mock_writer.written_data
    # The framer should have written a valid Content-Length message for the error
    header_part, body_part = output_bytes.split(b'\r\n\r\n', 1)
    response = json.loads(body_part.decode('utf-8'))

    assert "error" in response
    assert response["error"]["code"] == -32700  # Parse Error
    assert "Invalid Content-Length header" in response["error"]["message"]

    # Assert that the browser was closed because the loop terminated
    mock_browser_env_fixture.close.assert_awaited_once()

@pytest.mark.asyncio
async def test_shutdown_command_closes_browser_gracefully(mock_browser_env_fixture):
    """
    Test that the mcp.shutdown command terminates the loop and closes the browser once.
    """
    message = b'{"id": "shutdown-1", "method": "mcp.shutdown", "params": {}}\n'
    mock_reader = MockStreamReader(message)
    mock_writer = MockAsyncWriter()

    await run_main(
        framing="line",
        headless=True,
        storage_state="",
        nav_timeout_ms=1000,
        browser_name="chromium",
        io_timeout_s=1,
        reader=mock_reader,
        writer=mock_writer,
    )

    # Assert that a success response was written
    output = mock_writer.written_data.decode('utf-8')
    response = json.loads(output)
    assert response["id"] == "shutdown-1"
    assert response["result"]["ok"] is True
    assert response["result"]["shutdown"] is True

    # Assert that close was called exactly once from the finally block
    mock_browser_env_fixture.close.assert_awaited_once()

@pytest.mark.asyncio
async def test_ping_command(mock_browser_env_fixture):
    """Test the ping command returns the echo parameter."""
    message = b'{"id": "ping-1", "method": "ping", "params": {"echo": "hello"}}\n'
    mock_reader = MockStreamReader(message)
    mock_writer = MockAsyncWriter()

    await run_main(
        framing="line",
        headless=True,
        storage_state="",
        nav_timeout_ms=1000,
        browser_name="chromium",
        io_timeout_s=1,
        reader=mock_reader,
        writer=mock_writer,
    )

    output = mock_writer.written_data.decode('utf-8')
    response = json.loads(output)
    assert response["result"]["echo"] == "hello"

@pytest.mark.asyncio
async def test_unknown_method(mock_browser_env_fixture):
    """Test that an unknown RPC method returns a proper error."""
    message = b'{"id": "unknown-1", "method": "foo.bar", "params": {}}\n'
    mock_reader = MockStreamReader(message)
    mock_writer = MockAsyncWriter()

    await run_main(
        framing="line",
        headless=True,
        storage_state="",
        nav_timeout_ms=1000,
        browser_name="chromium",
        io_timeout_s=1,
        reader=mock_reader,
        writer=mock_writer,
    )

    output = mock_writer.written_data.decode('utf-8')
    response = json.loads(output)
    assert "error" in response
    assert response["error"]["code"] == -32603
    assert "Unknown method: foo.bar" in response["error"]["message"]

@pytest.mark.asyncio
async def test_navigate_with_invalid_params(mock_browser_env_fixture):
    """Test that browser.navigate with invalid params returns a -32602 error."""
    # Test with a missing 'url' parameter
    message = b'{"id": "nav-1", "method": "browser.navigate", "params": {"x": 123}}\n'
    mock_reader = MockStreamReader(message)
    mock_writer = MockAsyncWriter()

    await run_main(
        framing="line",
        headless=True,
        storage_state="",
        nav_timeout_ms=1000,
        browser_name="chromium",
        io_timeout_s=1,
        reader=mock_reader,
        writer=mock_writer,
    )

    output = mock_writer.written_data.decode('utf-8')
    response = json.loads(output)
    assert "error" in response
    assert response["error"]["code"] == -32602  # Invalid Params
    assert "requires a string 'url'" in response["error"]["message"]

@pytest.mark.asyncio
async def test_ping_with_invalid_params(mock_browser_env_fixture):
    """Test that ping with a non-string 'echo' returns a -32602 error."""
    message = b'{"id": "ping-1", "method": "ping", "params": {"echo": 12345}}\n'
    mock_reader = MockStreamReader(message)
    mock_writer = MockAsyncWriter()

    await run_main(
        framing="line",
        headless=True,
        storage_state="",
        nav_timeout_ms=1000,
        browser_name="chromium",
        io_timeout_s=1,
        reader=mock_reader,
        writer=mock_writer,
    )

    output = mock_writer.written_data.decode('utf-8')
    response = json.loads(output)
    assert "error" in response
    assert response["error"]["code"] == -32602  # Invalid Params
    assert "parameter to be a string" in response["error"]["message"]

@pytest.mark.asyncio
async def test_navigate_with_non_object_params(mock_browser_env_fixture):
    """Test that a non-object 'params' field returns a -32602 error."""
    message = b'{"id": "nav-1", "method": "browser.navigate", "params": "not-an-object"}\n'
    mock_reader = MockStreamReader(message)
    mock_writer = MockAsyncWriter()

    await run_main(
        framing="line",
        headless=True,
        storage_state="",
        nav_timeout_ms=1000,
        browser_name="chromium",
        io_timeout_s=1,
        reader=mock_reader,
        writer=mock_writer,
    )

    output = mock_writer.written_data.decode('utf-8')
    response = json.loads(output)
    assert "error" in response
    assert response["error"]["code"] == -32602  # Invalid Params
    assert "must be an object" in response["error"]["message"]

@pytest.mark.asyncio
async def test_content_length_framer_negative_length(mock_browser_env_fixture):
    """Test that a negative Content-Length is handled as a fatal error."""
    message = b"Content-Length: -1\r\n\r\n"
    mock_reader = MockStreamReader(message)
    mock_writer = MockAsyncWriter()

    await run_main(
        framing="content-length",
        headless=True,
        storage_state="",
        nav_timeout_ms=1000,
        browser_name="chromium",
        io_timeout_s=1,
        reader=mock_reader,
        writer=mock_writer,
    )

    output = mock_writer.written_data.decode('utf-8')
    response = json.loads(output.split('\r\n\r\n', 1)[1]) # Parse body
    assert "error" in response
    assert response["error"]["code"] == -32700  # Parse Error
    assert "must be non-negative" in response["error"]["message"]

@pytest.mark.asyncio
async def test_line_framer_invalid_json_is_handled(mock_browser_env_fixture):
    """
    Test that the main loop handles malformed JSON with the line framer.
    """
    malformed_message = b'{"id": 1, "method": "ping", "params": {}}\nnot json\n'

    mock_reader = MockStreamReader(malformed_message)
    mock_writer = MockAsyncWriter()

    await run_main(
        framing="line",
        headless=True,
        storage_state="",
        nav_timeout_ms=1000,
        browser_name="chromium",
        io_timeout_s=1,
        reader=mock_reader,
        writer=mock_writer,
    )

    output = mock_writer.written_data.decode('utf-8').strip().split('\n')

    # First message should be a valid response
    response1 = json.loads(output[0])
    assert "result" in response1
    assert response1["id"] == 1

    # Second message should be a parse error
    response2 = json.loads(output[1])
    assert "error" in response2
    assert response2["error"]["code"] == -32700

    mock_browser_env_fixture.close.assert_awaited_once()

class HangingMockStreamReader(asyncio.StreamReader):
    def __init__(self):
        super().__init__()

    async def readline(self) -> bytes:
        # This will hang longer than the test timeout
        await asyncio.sleep(5)
        return b''

@pytest.mark.asyncio
async def test_io_read_timeout(mock_browser_env_fixture):
    """Test that a slow client causing a read timeout is handled gracefully."""
    mock_reader = HangingMockStreamReader()
    mock_writer = MockAsyncWriter()

    await run_main(
        framing="line",
        headless=True,
        storage_state="",
        nav_timeout_ms=1000,
        browser_name="chromium",
        io_timeout_s=1, # Use a short timeout for the test
        reader=mock_reader,
        writer=mock_writer,
    )

    output = mock_writer.written_data.decode('utf-8')
    response = json.loads(output)
    assert "error" in response
    assert response["error"]["code"] == -32000  # Server error
    assert "Read operation timed out" in response["error"]["message"]

    mock_browser_env_fixture.close.assert_awaited_once()
