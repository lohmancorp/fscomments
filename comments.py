################################################################################
# comments.py is a script designed to re-import comments into FreshService
# from FreshDesk that were deleted after initial import was already completed.
#
# Author: Taylor Giddens - taylor.giddens@ingrammicro.com
# Version: 1.01
################################################################################

# Import necessary libraries
import argparse
import os
import logging
import requests
import base64
import json
import time
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Script Variables:
SCRIPT_NAME = 'comments.py'
SCRIPT_VERSION = '1.01'  # Update as per versioning requirements

# Environment variables
API_KEY = os.getenv('API_KEY')
FRESH_SERVICE_ENDPOINTS = {
    'staging': os.getenv('STAGING_ENDPOINT'),
    'production': os.getenv('PRODUCTION_ENDPOINT'),
}
LOG_DIRECTORY = os.getenv('LOG_DIRECTORY')
ERROR_PAYLOAD_DIRECTORY = os.getenv('ERROR_PAYLOAD_DIRECTORY')

# Global variables for tracking
original_time_wait = None
start_time = None
successful_tickets = 0
errored_tickets = []
tickets_with_many_comments = []
total_api_response_time = 0
api_calls_made = 0

# Argument Parsing - Adjusted
def parse_arguments():
    parser = argparse.ArgumentParser(description='Script to restore comments to FreshService tickets')
    parser.add_argument('-i', '--input-file', required=True, help='Path to the input JSON file')
    parser.add_argument('-m', '--mode', required=True, choices=['staging', 'production'], help='API mode: staging or production')
    parser.add_argument('-t', '--time-wait', type=int, required=True, help='Time in milliseconds to wait between API calls')
    parser.add_argument('-b', '--bigcomments-support', action='store_true', help='Support tickets with 50 or more comments')
    parser.add_argument('-n', '--number-to-process', type=int, default=0, help='Number of tickets to process, 0 for all')
    parser.add_argument('-l', '--log-level', choices=['WARNING', 'DEBUG'], default='WARNING', help='Logging level')
    parser.add_argument('-v', '--version', default=SCRIPT_VERSION, help='Version of the script to use')
    return parser.parse_args()

# Logging Configuration with Iteration
def setup_logging(args):
    today = datetime.now().strftime("%Y-%m-%d")
    input_filename = os.path.basename(args.input_file).split('.')[0]
    
    # Iterating to find a log file name that doesn't exist yet
    iteration = 1
    while True:
        log_filename = f"{today}-{input_filename}_{iteration}.log"
        full_log_path = os.path.join(LOG_DIRECTORY, log_filename)
        if not os.path.exists(full_log_path):
            break
        iteration += 1

    logging.basicConfig(filename=full_log_path, filemode='a',
                        level=getattr(logging, args.log_level.upper()), format='%(asctime)s - %(levelname)s - %(message)s')

# Function to read the input JSON file
def read_input_file(file_path):
    try:
        with open(file_path, 'r') as file:
            return json.load(file)
    except Exception as e:
        logging.error(f"Error reading input file: {e}")
        raise

# Function to estimate total script running time
def estimate_total_run_time(tickets_data):
    total_comments = sum(len(ticket['helpdesk_ticket']['notes']) for ticket in tickets_data)
    total_time_seconds = total_comments  # 1 second per comment
    return str(timedelta(seconds=total_time_seconds))

# User Confirmation to Proceed
def user_confirmation(message):
    while True:
        user_input = input(message).lower()
        if user_input in ['y', 'n']:
            return user_input == 'y'
        else:
            print("Please enter 'y' for yes or 'n' for no.")

# Generate the authorization header for API requests
def generate_auth_header(api_key):
    encoded_credentials = base64.b64encode(f"{api_key}:X".encode('utf-8')).decode('utf-8')
    return {
        "Content-Type": "application/json",
        "Authorization": f"Basic {encoded_credentials}"
    }

# Function to check the rate limit and adjust wait time if needed
def check_and_adjust_rate_limit(response, args):
    remaining_calls = int(response.headers.get('X-Ratelimit-Remaining', 0))
    if remaining_calls <= 40:
        args.time_wait = max(args.time_wait, 1000)  # Slowing down API calls
    else:
        args.time_wait = original_time_wait  # Resetting to original time wait

# Function to handle API requests with retries for timeouts
def make_api_request(method, url, headers, data=None, retries=2):
    try:
        response = requests.request(method, url, headers=headers, json=data)
        response.raise_for_status()  # Will raise an HTTPError for bad requests (4xx or 5xx)
        return response
    except requests.exceptions.Timeout:
        if retries > 0:
            time.sleep(2)  # Waiting for 2 seconds before retrying
            return make_api_request(method, url, headers, data, retries - 1)
        else:
            raise
    except requests.exceptions.RequestException as e:
        logging.error(f"API request failed: {e}")
        raise

# Function to check if comments exist for a ticket
def check_comments_exist(fsid, headers, args):
    url = FRESH_SERVICE_ENDPOINTS[args.mode] + f"/tickets/{fsid}/conversations"
    response = make_api_request("GET", url, headers)
    check_and_adjust_rate_limit(response, args)

    conversations = response.json().get('conversations', [])
    return len(conversations) == 0

# Function to check for specific activity on a ticket
def check_activity(fsid, headers, args):
    url = FRESH_SERVICE_ENDPOINTS[args.mode] + f"/tickets/{fsid}/activities"
    response = make_api_request("GET", url, headers)
    check_and_adjust_rate_limit(response, args)

    activities = response.json().get('activities', [])
    return any(activity['actor']['id'] == 23000972474 for activity in activities)

# Function to process and post notes to FreshService - Revised for tracking and logging
def process_notes(fsid, ticket, headers, args):
    global successful_tickets, total_api_response_time, api_calls_made, errored_tickets, tickets_with_many_comments
    notes = ticket['helpdesk_ticket']['notes']
    
    if not args.no_skip and len(notes) >= 50:
        tickets_with_many_comments.append(fsid)
        logging.warning(f"Skipping ticket FDID {ticket['helpdesk_ticket']['display_id']}, FSID: {fsid} due to 50 or more comments.")
        return

    for note in notes:
        note_content = note.get('body_html', '')
        payload = {"body": note_content, "private": note.get('private', False)}
        post_note_url = FRESH_SERVICE_ENDPOINTS[args.mode] + f"/tickets/{fsid}/notes"

        start_response_time = time.time()
        try:
            response = make_api_request("POST", post_note_url, headers, data=payload)
            successful_tickets += 1
            end_response_time = time.time()
            total_api_response_time += (end_response_time - start_response_time)
            api_calls_made += 1
            logging.info(f"Note posted successfully for FDID {ticket['helpdesk_ticket']['display_id']}, FSID: {fsid}")
        except Exception as e:
            errored_tickets.append((response.status_code, fsid))
            logging.error(f"Failed to post note for FDID {ticket['helpdesk_ticket']['display_id']}, FSID: {fsid}: {e}")

        time.sleep(args.time_wait / 1000)  # Wait between posting each note

# Main processing function for tickets - Adjusted for --number-to-process
def process_tickets(args, tickets_data):
    headers = generate_auth_header(API_KEY)
    processed_count = 0

    for ticket in tickets_data:
        if args.number_to_process and processed_count >= args.number_to_process:
            break

        fdid = ticket['helpdesk_ticket']['display_id']
        # Step 6a: Find the ticket in FreshService using display_id
        filter_url = FRESH_SERVICE_ENDPOINTS[args.mode] + f"/tickets/filter?query=\"fdid:{fdid}\""
        response = make_api_request("GET", filter_url, headers)
        check_and_adjust_rate_limit(response, args)

        tickets_response = response.json()
        total_found = tickets_response['total']

        # Handle different cases based on the total tickets found
        if total_found == 0:
            logging.error(f"fdid: {fdid} not found in Fresh Service")
        elif total_found > 1:
            logging.error(f"Multiple Fresh Service duplicate tickets for fdid: {fdid}")
        else:
            fsid = tickets_response['tickets'][0]['id']
            logging.info(f"Starting to update ticket fdid: {fdid}, fsid: {fsid}")

            # Check for existing comments and specific activity
            if check_comments_exist(fsid, headers, args) and check_activity(fsid, headers, args):
                process_notes(fsid, ticket, headers, args)
            else:
                logging.info(f"Conditions not met for FDID: {ticket['helpdesk_ticket']['display_id']}, FSID: {fsid}")

        processed_count += 1
        time.sleep(args.time_wait / 1000)  # Wait time between processing each ticket

# Final summary and logging - Updated
def finalize_script_execution(args, tickets_data):
    global start_time, successful_tickets, errored_tickets, tickets_with_many_comments, total_api_response_time, api_calls_made
    total_runtime = datetime.now() - start_time
    avg_processing_time = total_runtime / len(tickets_data) if tickets_data else timedelta(0)
    avg_api_response_time = (total_api_response_time / api_calls_made) * 1000 if api_calls_made else 0

    final_summary_msg = (f"Script Execution Completed\n"
                         f"Total Running Time: {str(total_runtime)}\n"
                         f"Average Processing Time per Ticket: {str(avg_processing_time)}\n"
                         f"Average API Response Time: {avg_api_response_time} milliseconds\n"
                         f"Total Successful Tickets: {successful_tickets}\n"
                         f"Errored Tickets: {errored_tickets}\n"
                         f"Tickets w/ 50+ Comments: {tickets_with_many_comments}")
    print(final_summary_msg)
    logging.info(final_summary_msg)

# Main Function - Adjusted
def main():
    global original_time_wait
    global start_time
    start_time = datetime.now()
    
    args = parse_arguments()
    setup_logging(args)
    
    # Set the global original_time_wait based on the argument
    original_time_wait = args.time_wait
    
    tickets_data = read_input_file(args.input_file)
    total_tickets = len(tickets_data)
    total_comments = sum(len(ticket['helpdesk_ticket']['notes']) for ticket in tickets_data)
    total_run_time_estimate = estimate_total_run_time(tickets_data)

    # Display and log total tickets, comments, estimated running time, script name, version, and start time
    total_info_msg = (f"Script Name: {SCRIPT_NAME}\n"
                      f"Script Version: {SCRIPT_VERSION}\n"
                      f"Script Start Time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
                      f"Total Tickets: {total_tickets}\n"
                      f"Total Comments: {total_comments}\n"
                      f"Estimated Total Running Time: {total_run_time_estimate}")
    print(total_info_msg)
    logging.info(total_info_msg)

    if not user_confirmation("Do you want to proceed? (y/n): "):
        logging.info("User opted not to proceed. Exiting script.")
        return

    process_tickets(args, tickets_data)

    # Finalize and summarize the script execution
    finalize_script_execution(args, tickets_data)

if __name__ == "__main__":
    main()

