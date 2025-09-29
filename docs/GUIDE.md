# A True Beginner's Guide to the Venice Browser Bridge

Welcome! This guide is designed to walk you through every single step of setting up and running the Venice Browser Bridge. We will assume you have no prior experience with Python or command-line tools and explain everything along the way.

## Table of Contents
1.  [What Are We Doing?](#what-are-we-doing)
2.  [Step 1: Install Python](#step-1-install-python)
3.  [Step 2: Get the Project Code](#step-2-get-the-project-code)
4.  [Step 3: Use the Command Line](#step-3-use-the-command-line)
5.  [Step 4: Create a Virtual Environment](#step-4-create-a-virtual-environment)
6.  [Step 5: Install the Bridge](#step-5-install-the-bridge)
7.  [Step 6: Run the Bridge](#step-6-run-the-bridge)
8.  [Step 7: Talk to the Bridge](#step-7-talk-to-the-bridge)
9.  [Understanding the Magic](#understanding-the-magic)
10. [What's Next?](#whats-next)

---

### What Are We Doing?

Imagine you have a robot that can use a web browser. The Venice Browser Bridge is like the robot's brain. It's a program that runs silently, waiting for instructions. Another program (which we'll call a "host") can send it simple text commands, like "navigate to example.com". The bridge receives the command, tells the browser what to do, and then reports back to the host what happened.

By the end of this guide, you will:
- Have the bridge program running.
- Use a second program (an example "host") to send it a command.
- See the successful result.

---

### Step 1: Install Python

Python is the programming language this project is written in. You need to have it installed on your computer.

- **On Windows**:
    1.  Go to the [official Python website's download page](https://www.python.org/downloads/windows/).
    2.  Download the latest stable release (e.g., Python 3.12).
    3.  Run the installer. **This is the most important step:** On the very first screen of the installer, check the box at the bottom that says **"Add Python to PATH"**.
    4.  Click "Install Now" and let it finish.

- **On macOS or Linux**:
    1.  Python is usually pre-installed. To check, open the `Terminal` app and type `python3 --version`.
    2.  If you see a version number like `3.8.x` or higher, you're ready.
    3.  If not, follow the installation instructions for your specific OS (e.g., using Homebrew on macOS or `apt` on Ubuntu).

---

### Step 2: Get the Project Code

The "repository" is just the collection of all the files for this project.

1.  On the project's GitHub page, click the green **"Code"** button.
2.  In the dropdown, click **"Download ZIP"**.
3.  Find the downloaded ZIP file on your computer and **extract it**. This will create a folder, likely named `venice-browser-mcp-main`. This is your project folder.

---

### Step 3: Use the Command Line

The command line (or "terminal" or "command prompt") is a text-based way to interact with your computer.

1.  **Open your command line application.**
    -   Windows: Press `Win+R`, type `cmd`, and press Enter.
    -   macOS/Linux: Open the `Terminal` app from your applications list.

2.  **Navigate to your project folder.** We use the `cd` (change directory) command for this. The path you type will depend on where you extracted the folder.
    -   *Example*: If the `venice-browser-mcp-main` folder is on your Desktop, you would type:
        ```bash
        # The 'cd' command moves you into a directory.
        cd Desktop/venice-browser-mcp-main
        ```
    -   *Tip*: You can often drag and drop a folder onto the terminal window to paste its full path.

---

### Step 4: Create a Virtual Environment

This is a best practice for any Python project. It creates a clean, isolated "sandbox" for your project so its dependencies don't interfere with other Python projects on your system.

1.  **Make sure you are inside the project folder** in your terminal (from the step above).
2.  **Run the command to create the environment:**
    ```bash
    # This tells Python to run its 'venv' module and create a folder named '.venv'
    python3 -m venv .venv
    ```
    > **What just happened?** You created a subfolder named `.venv` that contains a private copy of Python and its package installer, `pip`.

3.  **Activate the environment.** This "turns on" the sandbox for your current terminal session.
    -   **Windows**:
        ```cmd
        .venv\Scripts\activate
        ```
    -   **macOS/Linux**:
        ```bash
        source .venv/bin/activate
        ```
    > **What just happened?** Your command prompt should now have `(.venv)` at the beginning. This tells you the virtual environment is active. Any Python or `pip` command you run now will use the sandbox inside the `.venv` folder.

---

### Step 5: Install the Bridge

Now we'll install the Venice bridge package and its dependencies into your active virtual environment.

1.  **Install the package using `pip`**:
    ```bash
    # The '.' tells pip to look for an installable project in the current directory.
    pip install .
    ```
    > **What just happened?** `pip` read the `pyproject.toml` file, found the project's name and its dependencies (like `playwright`), and installed them into your `.venv` sandbox. This also created the `venice` command-line tool.

2.  **Install the web browser for Playwright**:
    ```bash
    # This command downloads a version of Chromium that Playwright can control.
    playwright install chromium
    ```

---

### Step 6: Run the Bridge

The bridge is now ready to run.

-   In your terminal (with `.venv` still active), run the `venice` command:
    ```bash
    venice
    ```
-   The terminal will appear to do nothing. This is correct! The bridge is now running silently in the foreground, waiting for another program to connect and give it commands.

---

### Step 7: Talk to the Bridge

To send commands, you need a new, separate terminal.

1.  **Open a second terminal window.** Leave the first one running!
2.  In this new terminal, **navigate to the same project folder** and **activate the same virtual environment** again.
    ```bash
    # Go to the project folder
    cd path/to/your/venice-browser-mcp-main

    # Activate the environment (use the command for your OS)
    source .venv/bin/activate
    ```

3.  **Run the example host program.** This is a simple Python script we've provided that knows how to send a command to the bridge.
    ```bash
    python3 examples/line_host.py
    ```

4.  **Check the output!** The second terminal should immediately print:
    ```
    Navigate...
    {"id":"nav-1","result":{"ok":true,"final_url":"https://example.com/","title":"Example Domain"}}
    ```
    > **What just happened?** The `line_host.py` script started the bridge process, sent it a `browser.navigate` command through its `stdin`, and read the successful JSON response from its `stdout`.

Congratulations! You have successfully set up, run, and communicated with the Venice Browser Bridge.

---

### Understanding the Magic

-   The **first terminal** runs the **bridge (`venice`)**. It's a server waiting for commands.
-   The **second terminal** runs the **host (`examples/line_host.py`)**. It's a client that sends commands.
-   They communicate through standard input/output streams, a fundamental way programs can talk to each other.

---

### What's Next?

-   You can look at `examples/line_host.py` to see how to format and send other commands, like `ping`.
-   You can modify the `dispatch` method in `venice/bridge.py` to add your own custom commands.
-   To stop the bridge, go to its terminal window and press `Ctrl+C`. To leave the virtual environment in either terminal, simply type the command `deactivate`.