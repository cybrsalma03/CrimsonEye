import argparse
import requests
import socket
import os
import logging
from colorama import Fore, Style
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
import json

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Function to print the banner

def print_banner():
    banner = [
        " ██████╗  ██████╗ ███╗   ███╗ █████╗ ██╗███╗   ██╗██████╗ ██╗   ██╗██╗     ███████╗███████╗",
        " ██╔══██╗██╔═══██╗████╗ ████║██╔══██╗██║████╗  ██║██╔══██╗██║   ██║██║     ██╔════╝██╔════╝",
        " ██║  ██║██║   ██║██╔████╔██║███████║██║██╔██╗ ██║██████╔╝██║   ██║██║     ███████╗█████╗  ",
        " ██║  ██║██║   ██║██║╚██╔╝██║██╔══██║██║██║╚██╗██║██╔═══╝ ██║   ██║██║     ╚════██║██╔══╝  ",
        " ██████╔╝╚██████╔╝██║ ╚═╝ ██║██║  ██║██║██║ ╚████║██║     ╚██████╔╝███████╗███████║███████╗",
        " ╚═════╝  ╚═════╝ ╚═╝     ╚═╝╚═╝  ╚═╝╚═╝╚═╝  ╚═══╝╚═╝      ╚═════╝ ╚══════╝╚══════╝╚══════╝"
    ]
    
    # Print the banner with a short delay between lines
    for line in banner:
        print(line)
        time.sleep(0.1)  # Short delay (0.1 seconds)
    
    # Print "Developed by Shosha" in a centered and formatted style
    author_line = "Crimson Eye - Developed by Shosha"
    padding = (len(banner[0]) - len(author_line)) // 2  # Center the text
    print("\n" + " " * padding + author_line + "\n")
    time.sleep(0.5)  # Slightly longer delay after the author line

# Function to check domain status with improved error handling
def check_domain_status(domain, whitelist, exclude_list, timeout, user_agent, retries=3, verbose=False):
    headers = {'User-Agent': user_agent}
    for attempt in range(retries):
        try:
            # Try HTTPS first
            try:
                response = requests.get(f'https://{domain}', headers=headers, timeout=timeout)
                status_code = response.status_code
            except requests.exceptions.SSLError:
                # Fallback to HTTP if HTTPS fails
                response = requests.get(f'http://{domain}', headers=headers, timeout=timeout)
                status_code = response.status_code

            if verbose:
                logging.info(f"Response from {domain}: {response.text[:100]}...")  # Log first 100 characters of response

            if (whitelist and status_code in whitelist) or (status_code not in exclude_list):
                return format_status_output(domain, status_code)
            else:
                return None
        except socket.gaierror:
            return f"{Fore.YELLOW}[ERROR] {domain} cannot be resolved (DNS Error){Style.RESET_ALL}"
        except requests.exceptions.RequestException as e:
            if attempt == retries - 1:  # Last attempt
                return f"{Fore.YELLOW}[ERROR] {domain} is DOWN (Error: {e}){Style.RESET_ALL}"
            time.sleep(1)  # Wait before retrying

# Function to format status output with different colors for status codes
def format_status_output(domain, status_code):
    status_color = {
        200: Fore.GREEN,
        301: Fore.CYAN,
        302: Fore.CYAN,
        400: Fore.RED,
        401: Fore.RED,
        403: Fore.RED,
        404: Fore.RED,
        500: Fore.RED,
        502: Fore.YELLOW,
        503: Fore.YELLOW,
        504: Fore.YELLOW
    }

    color = status_color.get(status_code, Fore.WHITE)  # Default color is white if status code is not defined

    return f"{color}[{status_code}] {domain} {Style.RESET_ALL}"

# Function to parse command-line arguments
def parse_args():
    parser = argparse.ArgumentParser(
        description="Crimson Eye - A tool to check the status of domains with advanced features.",
        epilog="""
Examples:
1. Basic usage:
   python crimson_eye.py -d domains.txt

2. Whitelist specific status codes:
   python crimson_eye.py -d domains.txt -s 200,301

3. Exclude specific status codes:
   python crimson_eye.py -d domains.txt -e 404,500

4. Use multiple threads for faster execution:
   python crimson_eye.py -d domains.txt -t 10

5. Save results to a file:
   python crimson_eye.py -d domains.txt -o results.txt

6. Use a custom timeout and retries:
   python crimson_eye.py -d domains.txt --timeout 10 --retries 5

7. Enable verbose output:
   python crimson_eye.py -d domains.txt -v

8. Use a custom User-Agent:
   python crimson_eye.py -d domains.txt --user-agent "MyCustomUserAgent/1.0"

9. Save results in JSON format:
   python crimson_eye.py -d domains.txt -o results.json --format json
""",
        formatter_class=argparse.RawTextHelpFormatter
    )
    
    parser.add_argument('-d', '--domains', type=str, help="File containing the list of domains", required=True)
    parser.add_argument('-s', '--statuscodes', type=str, help="Whitelist of status codes, comma separated (e.g., 200,301)", default="")
    parser.add_argument('-e', '--exclude', type=str, help="Exclude specific status codes, comma separated (e.g., 404)", default="")
    parser.add_argument('-t', '--threads', type=int, help="Number of threads (default is 5)", default=5)
    parser.add_argument('-o', '--output', type=str, help="Output file name", default="")
    parser.add_argument('--timeout', type=int, help="Timeout for HTTP requests in seconds (default is 5)", default=5)
    parser.add_argument('--retries', type=int, help="Number of retries for failed requests (default is 3)", default=3)
    parser.add_argument('-v', '--verbose', action='store_true', help="Enable verbose output")
    parser.add_argument('--user-agent', type=str, help="Custom User-Agent string", default="CrimsonEye/1.0")
    parser.add_argument('--format', type=str, choices=['text', 'json'], help="Output format (default is text)", default="text")
    
    return parser.parse_args()

# Function to check the status codes for domains from a file
def check_domains_file(domains_file, whitelist, exclude_list, threads, output_file, timeout, retries, user_agent, verbose, output_format):
    if not os.path.exists(domains_file):
        logging.error(f"File not found: {domains_file}")
        return
    
    with open(domains_file, 'r') as file:
        domains = [domain.strip() for domain in file.readlines() if domain.strip()]
    
    results = []
    
    with ThreadPoolExecutor(max_workers=threads) as executor:
        futures = {executor.submit(check_domain_status, domain, whitelist, exclude_list, timeout, user_agent, retries, verbose): domain for domain in domains}
        
        for future in tqdm(as_completed(futures), total=len(domains), desc="Checking domains"):
            result = future.result()
            if result:
                results.append(result)
                print(result)  # Print results as they come in
    
    if output_file:
        save_results(results, output_file, output_format)

# Function to save results to a file
def save_results(results, output_file, output_format):
    if results:
        if output_format == 'json':
            with open(output_file, 'w') as file:
                json.dump(results, file, indent=4)
        else:
            with open(output_file, 'w') as file:
                file.write("\n".join(results))
        logging.info(f"Results saved to {output_file}")
    else:
        logging.info("No results to save.")

# Main function to execute the script
def main():
    print_banner()  # Print the banner at the start
    
    args = parse_args()
    
    # Parse whitelist and exclude lists
    whitelist = [int(code) for code in args.statuscodes.split(',') if code] if args.statuscodes else []
    exclude_list = [int(code) for code in args.exclude.split(',') if code] if args.exclude else []
    
    # Call the function to check the status of domains
    check_domains_file(
        args.domains, whitelist, exclude_list, args.threads, args.output, args.timeout, args.retries, args.user_agent, args.verbose, args.format
    )

if __name__ == "__main__":
    main()