import asyncio
import os
from unittest.mock import patch, MagicMock
import pytest
from io import StringIO

from venice.config import main as core_main, _bool_env

@pytest.fixture
def mock_run_main():
    """Fixture to mock the run_main function."""
    with patch('venice.config.run_main', new_callable=MagicMock) as mock:
        # Make the mock an async function so it can be awaited
        async def async_mock(*args, **kwargs):
            return MagicMock()
        mock.side_effect = async_mock
        yield mock

def test_invalid_nav_timeout_falls_back_to_default(mock_run_main, monkeypatch, capsys):
    """
    Test that if NAV_TIMEOUT is an invalid integer, it falls back to the default
    and logs a warning.
    """
    # 1. Set environment variable to an invalid value
    monkeypatch.setenv("NAV_TIMEOUT", "not-a-number")

    # 2. Run the core main function
    asyncio.run(core_main())

    # 3. Assert that run_main was called with the default timeout
    mock_run_main.assert_called_once()
    args, kwargs = mock_run_main.call_args
    assert kwargs.get('nav_timeout_ms') == 30000

    # 4. Assert that a warning was printed to stderr
    captured = capsys.readouterr()
    assert "[bridge] warning: invalid timeout value" in captured.err

def test_invalid_io_timeout_falls_back_to_default(mock_run_main, monkeypatch, capsys):
    """
    Test that if MCP_IO_TIMEOUT_S is an invalid integer, it falls back to the default
    and logs a warning.
    """
    monkeypatch.setenv("MCP_IO_TIMEOUT_S", "not-a-number")
    asyncio.run(core_main())
    mock_run_main.assert_called_once()
    args, kwargs = mock_run_main.call_args
    assert kwargs.get('io_timeout_s') == 60
    captured = capsys.readouterr()
    assert "[bridge] warning: invalid I/O timeout" in captured.err

def test_bool_env_handler():
    """
    Test the _bool_env helper function with various inputs.
    """
    # Test true values
    assert _bool_env("TEST_VAR", default=False) is False # Default when not set
    os.environ["TEST_VAR"] = "1"
    assert _bool_env("TEST_VAR", default=False) is True
    os.environ["TEST_VAR"] = "true"
    assert _bool_env("TEST_VAR", default=False) is True
    os.environ["TEST_VAR"] = "YES"
    assert _bool_env("TEST_VAR", default=False) is True
    os.environ["TEST_VAR"] = "on"
    assert _bool_env("TEST_VAR", default=False) is True

    # Test false values
    os.environ["TEST_VAR"] = "0"
    assert _bool_env("TEST_VAR", default=True) is False
    os.environ["TEST_VAR"] = "false"
    assert _bool_env("TEST_VAR", default=True) is False
    os.environ["TEST_VAR"] = "no"
    assert _bool_env("TEST_VAR", default=True) is False
    os.environ["TEST_VAR"] = "off"
    assert _bool_env("TEST_VAR", default=True) is False
    os.environ["TEST_VAR"] = "any other string"
    assert _bool_env("TEST_VAR", default=True) is False

    del os.environ["TEST_VAR"]
