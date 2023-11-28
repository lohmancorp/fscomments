################################################################################
# setup.py is a script to setup comments.py
#
# Author: Taylor Giddens - taylor.giddens@ingrammicro.com
# Version: 1.01
################################################################################

import os
import subprocess
import sys

def check_python():
    if sys.version_info < (3, 6):
        raise Exception("Python 3.6 or higher is required. Please install it.")
    print("Python version check passed.")

def install_packages():
    required_packages = ["requests", "python-dotenv"]
    for package in required_packages:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
    print("Required packages installed successfully.")

def setup_env_file():
    env_variables = {
        'API_KEY': '',
        'STAGING_ENDPOINT': '',
        'PRODUCTION_ENDPOINT': '',
        'LOG_DIRECTORY': ''
    }

    print("\nSetting up environment variables...")
    if not os.path.isfile('.env'):
        with open('.env', 'w') as file:
            for key in env_variables:
                value = input(f"Enter value for {key}: ")
                file.write(f"{key}={value}\n")
                print(f"{key} set successfully.")
    else:
        print(".env file already exists.")

def create_directories():
    directories = ['./versions', './documentation', './logs']
    print("\nCreating necessary directories...")
    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory)
            print(f"Directory {directory} created.")
        else:
            print(f"Directory {directory} already exists.")
    print("All necessary directories created successfully.")

def main():
    print("Starting setup script for comments.py...")
    check_python()
    install_packages()
    setup_env_file()
    create_directories()
    print("\nSetup completed successfully.")

if __name__ == "__main__":
    main()

