import asyncio
import pytest
import os
from unittest.mock import AsyncMock, patch

from venice.bridge import BrowserEnv

@pytest.mark.asyncio
async def test_storage_state_save_error_is_logged(capsys):
    """
    Test that if saving storage_state fails, an error is logged to stderr.
    """
    # 1. Create a BrowserEnv instance with a problematic path
    # A directory is a good choice, as Playwright can't write a file to it.
    error_path = "a_directory"
    os.makedirs(error_path, exist_ok=True)

    browser_env = BrowserEnv(
        headless=True,
        storage_state=error_path,
        nav_timeout_ms=1000,
        browser_name="chromium"
    )

    # 2. Mock the internal Playwright objects
    browser_env._context = AsyncMock()
    browser_env._browser = AsyncMock()
    browser_env._pw = AsyncMock()

    # Configure the mock to raise an error when storage_state is called
    browser_env._context.storage_state.side_effect = Exception("Cannot write to a directory")

    # 3. Call close()
    await browser_env.close()

    # 4. Assert that the error was logged to stderr
    captured = capsys.readouterr()
    assert "[bridge] error saving storage state" in captured.err
    assert f"'{error_path}'" in captured.err
    assert "Cannot write to a directory" in captured.err

    # Clean up the directory
    os.rmdir(error_path)

@pytest.mark.asyncio
async def test_unsupported_browser_name_raises_error():
    """
    Test that using an unsupported browser name raises a RuntimeError.
    """
    browser_env = BrowserEnv(
        headless=True,
        storage_state="",
        nav_timeout_ms=1000,
        browser_name="netscape" # Unsupported
    )

    with pytest.raises(RuntimeError) as excinfo:
        await browser_env.ensure()

    assert "Unsupported browser 'netscape'" in str(excinfo.value)

@pytest.mark.asyncio
async def test_browser_name_is_case_insensitive():
    """
    Test that the browser name is treated as case-insensitive.
    """
    with patch('venice.bridge.async_playwright') as mock_async_playwright:
        # Configure the mock setup
        mock_manager = mock_async_playwright.return_value
        mock_manager.start = AsyncMock()
        mock_pw_instance = mock_manager.start.return_value
        mock_pw_instance.chromium.launch = AsyncMock()
        mock_browser = mock_pw_instance.chromium.launch.return_value
        mock_context = mock_browser.new_context.return_value
        mock_context.set_default_timeout = AsyncMock()
        mock_context.new_page = AsyncMock()

        browser_env = BrowserEnv(
            headless=True,
            storage_state="",
            nav_timeout_ms=1000,
            browser_name="Chromium"  # Mixed case
        )

        await browser_env.ensure()

        # Assert that the lowercase version of the launcher was called
        mock_manager.start.assert_awaited_once()
        mock_pw_instance.chromium.launch.assert_awaited_once()
