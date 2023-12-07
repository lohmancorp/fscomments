################################################################################
# setup.py
# A script to setup and manage the comments.py environment.
# Author: Taylor Giddens - taylor.giddens@ingrammicro.com
# Version: 1.09
################################################################################


import subprocess
import sys
import os
import shutil
import argparse

# Function to install required Python packages using pip.
def install(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])

# Check and install necessary Python packages ('requests' and 'python-dotenv').
def check_and_install_packages():
    for package in ["requests", "python-dotenv"]:
        try:
            __import__(package)
        except ImportError:
            install(package)

# Import the 'dotenv' package after ensuring it is installed.
def import_dotenv():
    global load_dotenv
    from dotenv import load_dotenv

# Function to check if the Python version meets the minimum requirement.
def check_python():
    if sys.version_info < (3, 6):
        raise Exception("Python 3.6 or higher is required. Please install it.")
    print("Python version check passed.")

# Function to download files from GitHub and save them locally.
def download_file_from_github(file_url, destination):
    import requests
    response = requests.get(file_url)
    if response.status_code == 200:
        if os.path.exists(destination):
            os.remove(destination)
        with open(destination, 'wb') as file:
            file.write(response.content)
        print(f"Downloaded and updated {destination}")
    else:
        print(f"Failed to download {destination}")

# Function to get user confirmation for default values.
def user_confirm_default(message, default_value):
    user_input = input(f"{message} Use default ({default_value})? [y/n]: ").lower()
    return default_value if user_input in ['y', 'yes'] else input("Enter new value: ")

# Function to set up the .env file with environment variables.
def setup_env_file():
    env_variables = {
        'API_KEY': input("Enter value for API_KEY: "),
        'STAGING_ENDPOINT': user_confirm_default("Staging Endpoint", "https://cbportal-fs-sandbox.freshservice.com/api/v2/"),
        'PRODUCTION_ENDPOINT': user_confirm_default("Production Endpoint", "https://cbportal.freshservice.com/api/v2/"),
        'LOG_DIRECTORY': user_confirm_default("Log Directory", "./logs/")
    }
    if not os.path.isfile('.env'):
        with open('.env', 'w') as file:
            for key, value in env_variables.items():
                file.write(f"{key}=\"{value}\"\n")
            print("Environment variables set successfully.")
    else:
        print(".env file already exists.")

# Function to create necessary directories based on .env configuration.
def create_directories():
    load_dotenv()
    log_directory = os.getenv('LOG_DIRECTORY', './logs')
    directories = ['./documentation', log_directory]
    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory)
            print(f"Directory {directory} created.")
    print("All necessary directories created successfully.")

# Function to parse command-line arguments for the setup script.
def parse_arguments():
    parser = argparse.ArgumentParser(description='Setup script for comments.py')
    parser.add_argument('-c', '--clean', action='store_true', help='Clean up existing setup')
    parser.add_argument('-u', '--update', action='store_true', help='Update comments.py script')
    return parser.parse_args()

# Function to clean up the existing setup.
def clean_setup():
    print("Cleaning up...")
    if os.path.exists('.env'):
        os.remove('.env')
    if os.path.exists('comments.py'):
        os.remove('comments.py')
    for root, dirs, files in os.walk('.', topdown=False):
        for name in dirs:
            shutil.rmtree(os.path.join(root, name))

# Function to update the comments.py script and its documentation.
def update_comments_script():
    print("Upgrading comments.py and documentation...")
    comments_py_url = "https://raw.githubusercontent.com/lohmancorp/fscomments/main/release/comments.py"
    documentation_url = "https://raw.githubusercontent.com/lohmancorp/fscomments/main/documentation/Comments_Documentation.pdf"
    download_file_from_github(comments_py_url, "comments.py")
    download_file_from_github(documentation_url, "./documentation/Comments_Documentation.pdf")
    print("Update completed successfully.")

# Main function to control the setup script.
def main():
    args = parse_arguments()
    if args.clean:
        clean_setup()
        return

    if args.update:
        check_and_install_packages()
        update_comments_script()
        return

    print("Starting setup script for comments.py...")
    check_python()
    check_and_install_packages()
    import_dotenv()  # Importing dotenv after ensuring it's installed
    setup_env_file()
    create_directories()

    documentation_url = "https://raw.githubusercontent.com/lohmancorp/fscomments/main/documentation/Comments_Documentation.pdf"
    download_file_from_github("https://raw.githubusercontent.com/lohmancorp/fscomments/main/release/comments.py", "comments.py")
    download_file_from_github(documentation_url, "./documentation/Comments_Documentation.pdf")

    print("\nSetup completed successfully.")

if __name__ == "__main__":
    main()

