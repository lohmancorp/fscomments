# comments.py
Script that will re-import comments to tickets where comments have been deleted.  This is based on the original FreshDesk ticket data export and mapping the source ticket data to FDID as a custom attribute for tickets created in FreshService.

Overview

comments.py is a Python script designed for re-importing comments into FreshService tickets from FreshDesk. It is particularly useful when comments have been deleted after initial import.

    Version: 1.04
    Author: Taylor Giddens (taylor.giddens@ingrammicro.com)

Prerequisites and Installation
Python 3.6+

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

