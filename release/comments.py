################################################################################
# comments.py is a script designed to re-import comments into FreshService
# from FreshDesk that were deleted after initial import was already completed.
#
# Author: Taylor Giddens - taylor.giddens@ingrammicro.com
# Version: 1.09.1
################################################################################

# Import necessary libraries
import argparse
import os
import logging
import requests
import base64
import json
import time
import signal
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Script Variables:
SCRIPT_NAME = 'comments.py'
SCRIPT_VERSION = '1.09.1'  # Update as per versioning requirements

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
skipped_tickets = 0
interrupted = False

# Argument Parsing - Adjusted
def parse_arguments():
    parser = argparse.ArgumentParser(description='Script to restore comments to FreshService tickets')
    parser.add_argument('-i', '--input-file', required=True, help='Path to the input JSON file')
    parser.add_argument('-m', '--mode', required=True, choices=['staging', 'production'], help='API mode: staging or production')
    parser.add_argument('-t', '--time-wait', type=int, required=True, help='Time in milliseconds to wait between API calls')
    parser.add_argument('-b', '--bigcomments-support', action='store_true', help='Support tickets with 50 or more comments')
    parser.add_argument('-a1', '--actor1', type=int, required=True, help='Primary Actor ID for checking specific activity')
    parser.add_argument('-a2', '--actor2', type=int, required=False, help='Secondary Actor ID for skipping already updated tickets')
    parser.add_argument('-n', '--number-to-process', type=int, default=0, help='Number of tickets to process, 0 for all')
    parser.add_argument('-d', '--dryrun', action='store_true', help='Dry run mode (no actual changes will be made)')
    parser.add_argument('-l', '--log-level', choices=['WARNING', 'DEBUG'], default='WARNING', help='Logging level')
    parser.add_argument('-v', '--version', default=SCRIPT_VERSION, help='Version of the script to use')
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_arguments()

    # Check if the input file exists
    if not os.path.isfile(args.input_file):
        print(f"The file {args.input_file} does not exist or the path used is incorrect.")
        print("Please check that the file exists and has the correct path and try again.")
        exit(1)
        
# Signal handler for handling Ctrl+C
def signal_handler(signum, frame):
    global interrupted
    interrupted = True
    print("\nInterrupt received, finishing current ticket and exiting... \n\n")

# Register the signal handler
signal.signal(signal.SIGINT, signal_handler)

# Logging Configuration with Iteration
def setup_logging(args):
    today = datetime.now().strftime("%Y-%m-%d")
    input_filename = os.path.basename(args.input_file).split('.')[0]

    iteration = 1
    while True:
        log_filename = f"{today}-{input_filename}_{iteration}.log"
        full_log_path = os.path.join(LOG_DIRECTORY, log_filename)
        if not os.path.exists(full_log_path):
            break
        iteration += 1

    # Set the baseline logging level to INFO
    logging.basicConfig(filename=full_log_path, filemode='a',
                        level=logging.INFO, 
                        format='%(asctime)s - %(levelname)s - %(message)s')

    # If the user's selected log level is DEBUG, adjust logging level accordingly
    if args.log_level.upper() == 'DEBUG':
        logging.getLogger().setLevel(logging.DEBUG)

# Function to read the input JSON file
def read_input_file(file_path):
    try:
        with open(file_path, 'r') as file:
            return json.load(file)
    except Exception as e:
        logging.error(f"Error reading input file: {e}")
        raise

# Function to estimate total script running time
# Function to estimate total script running time
def estimate_total_run_time(tickets_data, number_to_process):
    limited_tickets = tickets_data[:number_to_process] if number_to_process else tickets_data
    total_comments = sum(len(ticket['helpdesk_ticket']['notes']) for ticket in limited_tickets)
    total_time_seconds = total_comments  # 1 second per comment
    hours, remainder = divmod(total_time_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours}h {minutes}m {seconds}s"

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

# Function to handle API requests with retries for timeouts and handle specific error codes
def make_api_request(method, url, headers, data=None, retries=2):
    try:
        response = requests.request(method, url, headers=headers, json=data)
        if response.status_code == 403:  # Handling 403 Forbidden Error
            logging.error(f"403 Forbidden error encountered. URL: {url} Method: {method}")
            print("It looks like FreshWorks doesn't like what you were doing and the user was locked.")
            print("Please check in FreshService that the user who your API KEY corresponds to is not locked.")
            print("https://support.cloudblue.com/agents")
            exit(1)
        elif response.status_code == 401:  # Handling 401 Unauthorized Error
            logging.error(f"401 Unauthorized error encountered. URL: {url} Method: {method}")
            print("It looks like the API KEY you provided has a problem.")
            print("Follow these instructions to make sure you are getting the correct API KEY:")
            print("https://support.freshservice.com/en/support/solutions/articles/50000000306-where-do-i-find-my-api-key-")
            print("Once you have the correct API KEY, open the .env file located in the root folder of the script to update the value.")
            exit(1)
        elif response.status_code == 429:  # Handling 429 Too Many Requests Error
            logging.error(f"429 Too Many Requests error encountered. URL: {url} Method: {method}")
            print("It looks like you exceeded the API rate limit.")
            print("Go get a coffee, check your user isn't locked, and try again.")
            exit(1)
        response.raise_for_status()
        return response
    except requests.exceptions.Timeout:
        if retries > 0:
            time.sleep(2)
            return make_api_request(method, url, headers, data, retries - 1)
        else:
            raise
    except requests.exceptions.RequestException as e:
        logging.error(f"API request failed: {e}")
        raise

# Function to show a progress bar in the UI of the shell to monitor progress.
def show_progress_bar(current, total):
    """
    Displays a progress bar in the console.

    Args:
        current: Current item number being processed.
        total: Total number of items to process.
    """
    bar_length = 300  # Length of the progress bar in characters
    progress = current / total
    block = int(round(bar_length * progress))
    text = f"\rProgress: [{'#' * block}{'-' * (bar_length - block)}] {int(progress * 100)}% ({current}/{total})\n"
    sys.stdout.write(text)
    sys.stdout.flush()  # Ensure the progress bar updates are displayed immediately

# Function to check if comments exist for a ticket
def check_comments_exist(fsid, headers, args):
    url = FRESH_SERVICE_ENDPOINTS[args.mode] + f"/tickets/{fsid}/conversations"
    response = make_api_request("GET", url, headers)
    check_and_adjust_rate_limit(response, args)

    conversations = response.json().get('conversations', [])
    return len(conversations) == 0

# Function to check for specific activity (public note added) on a ticket
def check_activity(fsid, headers, actor1, conversations):
    url = FRESH_SERVICE_ENDPOINTS[args.mode] + f"/tickets/{fsid}/activities"
    response = make_api_request("GET", url, headers)
    check_and_adjust_rate_limit(response, args)

    activities = response.json().get('activities', [])
    # Check if actor1 added a public or private note
    actor1_notes = [act for act in activities if 'actor' in act and act['actor'].get('id') == actor1 and 
                    ("added a public note" in act.get('content', '') or "added a private note" in act.get('content', ''))]
    
    # Extract creation times of actor1's notes
    actor1_notes_times = {act['created_at'] for act in actor1_notes}

    # Check if any of actor1's notes are not in conversations
    return not any(conv['created_at'] in actor1_notes_times for conv in conversations if conv.get('user_id') == actor1)

# Function to get conversations for a ticket
def get_conversations(fsid, headers, args):
    url = FRESH_SERVICE_ENDPOINTS[args.mode] + f"/tickets/{fsid}/conversations"
    response = make_api_request("GET", url, headers)
    check_and_adjust_rate_limit(response, args)
    return response.json().get('conversations', [])

# Function to process and post notes to FreshService - Revised for tracking and logging
def process_notes(fsid, ticket, headers, args):
    global successful_tickets, total_api_response_time, api_calls_made, errored_tickets, tickets_with_many_comments
    notes = ticket['helpdesk_ticket']['notes']
    
    if not args.bigcomments_support and len(notes) >= 50:
        tickets_with_many_comments.append(fsid)
        logging.warning(f"Skipping ticket FDID {ticket['helpdesk_ticket']['display_id']}, FSID: {fsid} due to 50 or more comments.")
        print(f"Skipping ticket FDID {ticket['helpdesk_ticket']['display_id']}, FSID: {fsid} due to 50 or more comments.")
        return

    for note in notes:
        created_at = note.get('created_at', '')
        support_email = note.get('support_email', '')
        body_html = note.get('body_html', '')

        # Prepare the note content
        note_content = created_at
        if support_email and support_email.lower() != "none":
            note_content += f" <br>{support_email}"
        note_content += f" <br> <br>{body_html}"
        
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
            print(f"Failed to post note for FDID {ticket['helpdesk_ticket']['display_id']}, FSID: {fsid}: {e}")

        time.sleep(args.time_wait / 1000)  # Wait between posting each note

    # Log completion of updating the ticket
    logging.info(f"Completed updating ticket FDID {ticket['helpdesk_ticket']['display_id']}, FSID: {fsid}")
    print(f"Completed updating ticket FDID {ticket['helpdesk_ticket']['display_id']}, FSID: {fsid}")

# Main processing function for tickets - Adjusted for --number-to-process
def process_tickets(args, tickets_data):
    global successful_tickets, errored_tickets, tickets_with_many_comments, original_time_wait, skipped_tickets, interrupted
    headers = generate_auth_header(API_KEY)
    processed_tickets = set()

    # Limit the number of tickets to process if specified
    tickets_to_process = tickets_data[:args.number_to_process] if args.number_to_process else tickets_data

    total_tickets_to_process = len(tickets_to_process)
    current_ticket_count = 0

    for ticket in tickets_to_process:
        if interrupted:
            print("\nExiting after current ticket.")
            break

        fdid = ticket['helpdesk_ticket']['display_id']
        base_url = FRESH_SERVICE_ENDPOINTS[args.mode].rstrip('/')
        query = f'"fdid:{fdid}%20AND%20ticket_type:%27Incident%20or%20Problem%27"'
        filter_url = f"{base_url}/tickets/filter?query={query}"

        response = make_api_request("GET", filter_url, headers)
        check_and_adjust_rate_limit(response, args)

        tickets_response = response.json()
        total_found = tickets_response['total']

        if total_found == 0:
            logging.error(f"FDID: {fdid} not found in Fresh Service")
            errored_tickets.append(f"FDID: {fdid} not found in Fresh Service")
        elif total_found > 1:
            logging.error(f"Multiple Fresh Service duplicate tickets for FDID: {fdid}")
            errored_tickets.append(f"Multiple Fresh Service duplicate tickets for FDID: {fdid}")
        else:
            fsid = tickets_response['tickets'][0]['id']
            conversations = get_conversations(fsid, headers, args)
            actor1_involved = check_activity(fsid, headers, args.actor1, conversations)
            actor2_involved = args.actor2 and any(conv['user_id'] == args.actor2 for conv in conversations)

            if actor2_involved:
                logging.info(f"Skipping FDID: {ticket['helpdesk_ticket']['display_id']}, FSID: {fsid} - Already updated by actor2.")
                print(f"Skipping FDID: {ticket['helpdesk_ticket']['display_id']}, FSID: {fsid} - Already updated by actor2.")
                skipped_tickets += 1
            elif args.dryrun:
                print(f"Script is in dry run and fake processing of FDID {fdid} - FSID {fsid}")
            elif not conversations or actor1_involved:
                process_notes(fsid, ticket, headers, args)
                processed_tickets.add(fsid)
            else:
                logging.info(f"Skipping FDID: {ticket['helpdesk_ticket']['display_id']}, FSID: {fsid} - Conditions not met for adding comments.")
                print(f"Skipping FDID: {ticket['helpdesk_ticket']['display_id']}, FSID: {fsid} - Conditions not met for adding comments.")
                skipped_tickets += 1

        current_ticket_count += 1
        show_progress_bar(current_ticket_count, total_tickets_to_process)

        if interrupted:
            print("\nExiting after current ticket.")
            break

        time.sleep(args.time_wait / 1000)  # Wait time between processing each ticket

    successful_tickets = len(processed_tickets)  # Count unique successful tickets

def format_timedelta(td):
    total_seconds = int(td.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours}h {minutes}m {seconds}s"


# Final summary and logging - Updated
def finalize_script_execution(args, tickets_data):
    global start_time, successful_tickets, skipped_tickets, errored_tickets, tickets_with_many_comments, total_api_response_time, api_calls_made

    total_runtime = datetime.now() - start_time
    total_runtime_formatted = format_timedelta(total_runtime)
    avg_processing_time = total_runtime / len(tickets_data) if tickets_data else timedelta(0)
    avg_processing_time_formatted = format_timedelta(avg_processing_time)
    avg_api_response_time = (total_api_response_time / api_calls_made) if api_calls_made else 0

    # Determine the unit for average API response time
    if avg_api_response_time >= 1000:
        avg_api_response_time_in_seconds = round(avg_api_response_time / 1000, 2)
        avg_api_response_time_str = f"{avg_api_response_time_in_seconds} seconds"
    else:
        avg_api_response_time_rounded = round(avg_api_response_time, 2)
        avg_api_response_time_str = f"{avg_api_response_time_rounded} milliseconds"

    final_summary_msg = (f"Script Execution Completed\n"
                         f"Total Running Time: {total_runtime_formatted}\n"
                         f"Average Processing Time per Ticket: {avg_processing_time_formatted}\n"
                         f"Average API Response Time: {avg_api_response_time_str}\n"
                         f"Total Successful Tickets: {successful_tickets}\n"
                         f"Total Skipped Tickets: {skipped_tickets}\n"
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
    total_tickets = len(tickets_data[:args.number_to_process]) if args.number_to_process else len(tickets_data)
    total_comments = sum(len(ticket['helpdesk_ticket']['notes']) for ticket in tickets_data[:args.number_to_process]) if args.number_to_process else sum(len(ticket['helpdesk_ticket']['notes']) for ticket in tickets_data)
    total_run_time_estimate = estimate_total_run_time(tickets_data, args.number_to_process)

    # Display and log total tickets, comments, estimated running time, script name, version, and start time
    total_info_msg = (f"STARTING SCRIPT \n"
                      f"Script Name: {SCRIPT_NAME}\n"    
                      f"Script Version: {SCRIPT_VERSION}\n"
                      f"Script Start Time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
                      f"Total Tickets: {total_tickets}\n"
                      f"Total Comments: {total_comments}\n"
                      f"Estimated Total Running Time: {total_run_time_estimate}")

    print(total_info_msg)
    logging.info(total_info_msg)

    if not user_confirmation("Do you want to proceed? (y/n): "):
        logging.info("User opted not to proceed. Exiting script.")
        print("User opted not to proceed. Exiting script.")
        return

    process_tickets(args, tickets_data)

    # Finalize and summarize the script execution
    finalize_script_execution(args, tickets_data)

if __name__ == "__main__":
    main()
