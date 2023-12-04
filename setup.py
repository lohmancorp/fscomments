################################################################################
# setup.py is a script to setup comments.py
#
# Author: Taylor Giddens - taylor.giddens@ingrammicro.com
# Version: 1.06
################################################################################

import os
import requests
import subprocess
import sys
import argparse
from shutil import rmtree
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

def user_confirm_default(message, default_value):
    user_input = input(f"{message} Use default ({default_value})? [y/n]: ").lower()
    if user_input in ['y', 'yes']:
        return default_value
    else:
        return input("Enter new value: ")

def setup_env_file():
    env_variables = {
        'API_KEY': '',
        'STAGING_ENDPOINT': user_confirm_default("Staging Endpoint", "https://cbportal-fs-sandbox.freshservice.com/api/v2/"),
        'PRODUCTION_ENDPOINT': user_confirm_default("Production Endpoint", "https://cbportal.freshservice.com/api/v2/"),
        'LOG_DIRECTORY': user_confirm_default("Log Directory", "./logs/")
    }

    if not os.path.isfile('.env'):
        with open('.env', 'w') as file:
            for key, value in env_variables.items():
                file.write(f"{key}=\"{value}\"\n")
                print(f"{key} set to {value}.")
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

def clean_directories():
    directories_to_clean = ['./documentation', os.getenv('LOG_DIRECTORY', './logs')]
    for directory in directories_to_clean:
        if os.path.exists(directory):
            rmtree(directory)
            print(f"Deleted directory {directory}")
    if os.path.exists('comments.py'):
        os.remove('comments.py')
        print("Deleted comments.py")
    if os.path.exists('.env'):
        os.remove('.env')
        print("Deleted .env file")

def parse_arguments():
    parser = argparse.ArgumentParser(description='Setup script for comments.py')
    parser.add_argument('-c', '--clean', action='store_true', help='Clean up directories, comments.py, and .env file')
    parser.add_argument('-u', '--update', action='store_true', help='Update comments.py from GitHub')
    return parser.parse_args()

def main():
    args = parse_arguments()

    if args.clean:
        print("Cleaning up...")
        clean_directories()
        return

    print("Starting setup script for comments.py...")
    check_python()
    install_packages()

    if args.update:
        print("Updating comments.py from GitHub...")
        comments_py_url = "https://raw.githubusercontent.com/lohmancorp/fscomments/main/release/comments.py"
        download_file_from_github(comments_py_url, "comments.py")
        return

    setup_env_file()
    create_directories()

    # URLs for the raw content on GitHub
    comments_py_url = "https://raw.githubusercontent.com/lohmancorp/fscomments/main/release/comments.py"
    documentation_url = "https://raw.githubusercontent.com/lohmancorp/fscomments/main/documentation/Comments_Documentation.pdf"

    # Downloading the files
    download_file_from_github(comments_py_url, "comments.py")
    download_file_from_github(documentation_url, "./documentation/Comments_Documentation.pdf")

    print("\nSetup completed successfully.")

if __name__ == "__main__":
    main()
