# comments.py
Script that will re-import comments to tickets where comments have been deleted.  This is based on the original FreshDesk ticket data export and mapping the source ticket data to FDID as a custom attribute for tickets created in FreshService.

Overview

comments.py is a Python script designed for re-importing comments into FreshService tickets from FreshDesk. It is particularly useful when comments have been deleted after initial import.

    Version: 1.04
    Author: Taylor Giddens (taylor.giddens@ingrammicro.com)

Prerequisites and Installation
For Windows Users:

    Python Installation:
        Download and install Python from python.org.
        Ensure 'Add Python to PATH' is selected during installation.
        Verify installation: Open Command Prompt and type python --version.

    Command Line Interface:
        Use Command Prompt or PowerShell.

For macOS Users:

    Python Installation:
        Verify with python3 --version in Terminal.
        If not installed or another version is needed, download from python.org or install via Homebrew (brew install python).

    Terminal Usage:
        Utilize the built-in Terminal application.

Setup Script (setup.py)

    Download setup.py Script:
        Download setup.py from the GitHub repository: setup.py GitHub link.

    Run setup.py:
        In Terminal or Command Line, navigate to the directory with setup.py.
        Execute the script: python setup.py or python3 setup.py.

    Script Execution:
        The script will automatically:
            Check Python version.
            Install necessary packages (requests, python-dotenv).
            Prompt for .env file configuration.
            Create necessary directories.
            Download comments.py and documentation from GitHub.

    Setup Completion:
        A message "Setup completed successfully" indicates the script is ready.

Running comments.py Script

    Required Input Variables for Running the Script:
        -i, --input-file: Path to the input JSON file with ticket data. Contact Taylor Giddens for the export of ticket data required to perform the re-import.
        -m, --mode: API mode (staging or production).
        -t, --time-wait: Time in milliseconds between API calls. Do not put lower than 200.
        --actor: Actor ID to check specific activity. This is the ID of the user that was likely deleted and led to the comments being removed. Use 23000972474 for re-import.

    Optional Input Variables:
        --number-to-process: Number of tickets to process (0 for all). Start with "1" for testing.
        -b, --bigcomments-support: Flag for supporting tickets with 50+ comments.
        --log-level: Set logging level (WARNING, DEBUG).

    Execute comments.py:
        Use the command: python comments.py --input-file 'tickets.json' --mode 'staging' --actor 12345 --time-wait 500.

    Monitor Script Execution:
        Check the log files for process details and troubleshooting.

Errors and Common Problems

    Error 403 (Forbidden):
        Indicates the user associated with the API key is locked.
        Solution: Check FreshService user status and unlock if necessary.
        URL for checking: FreshService User Management.

    Error 401 (Unauthorized):
        Suggests an issue with the provided API key.
        Solution: Verify the API key's correctness using instructions at FreshService API Key Guide.

    Error 429 (Too Many Requests):
        Implies exceeding the API rate limit.
        Solution: Wait before making further requests and ensure the user isn't locked.
