import asyncio
import json
import pytest
import sys
import os
from unittest.mock import MagicMock, AsyncMock, patch

# Make src module available for testing
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from venice_browser_mcp_v23_impl import ContentLengthFramer, LineFramer, run_main, _AsyncStdoutWriter

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
    with patch('venice_browser_mcp_v23_impl.BrowserEnv') as MockBrowserEnv:
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
        reader=mock_reader,
        writer=mock_writer,
    )

    output = mock_writer.written_data.decode('utf-8')
    response = json.loads(output)
    assert "error" in response
    assert response["error"]["code"] == -32603
    assert "Unknown method: foo.bar" in response["error"]["message"]

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
