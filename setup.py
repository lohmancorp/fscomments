################################################################################
# setup.py is a script to setup comments.py
#
# Author: Taylor Giddens - taylor.giddens@ingrammicro.com
# Version: 1.05
################################################################################

import os
import requests
import subprocess
import sys
from dotenv import load_dotenv

def check_python():
    if sys.version_info < (3, 6):
        raise Exception("Python 3.6 or higher is required. Please install it.")
    print("Python version check passed.")

def install_packages():
    required_packages = ["requests", "python-dotenv"]
    for package in required_packages:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
    print("Required packages installed successfully.")

def download_file_from_github(file_url, destination):
    response = requests.get(file_url)
    if response.status_code == 200:
        with open(destination, 'wb') as file:
            file.write(response.content)
        print(f"Downloaded {destination}")
    else:
        print(f"Failed to download {destination}")

def setup_env_file():
    env_variables = {
        'API_KEY': '',
        'STAGING_ENDPOINT': '',
        'PRODUCTION_ENDPOINT': '',
        'LOG_DIRECTORY': ''
    }

    if not os.path.isfile('.env'):
        with open('.env', 'w') as file:
            for key in env_variables:
                value = input(f"Enter value for {key}: ")
                file.write(f"{key}=\"{value}\"\n")  # Enclosing the value in quotes
                print(f"{key} set successfully.")
    else:
        print(".env file already exists.")

def create_directories():
    # Load the environment variables from .env file
    load_dotenv()
    
    log_directory = os.getenv('LOG_DIRECTORY', './logs')
    directories = ['./documentation', log_directory]

    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory)
            print(f"Directory {directory} created.")
    print("All necessary directories created successfully.")

def main():
    print("Starting setup script for comments.py...")
    check_python()
    install_packages()
    setup_env_file()
    create_directories()

    # URLs for the raw content on GitHub
    comments_py_url = "https://raw.githubusercontent.com/lohmancorp/fscomments/main/comments.py"
    documentation_url = "https://raw.githubusercontent.com/lohmancorp/fscomments/main/comments_script.pdf"

    # Downloading the files
    download_file_from_github(comments_py_url, "comments.py")
    download_file_from_github(documentation_url, "./documentation/comments_script.pdf")

    print("\nSetup completed successfully.")

if __name__ == "__main__":
    main()
