import requests
import logging
import argparse
import json
import random
import time
import threading
from concurrent.futures import ThreadPoolExecutor
from tqdm import tqdm
from fuzzywuzzy import fuzz

# Print the banner
def print_banner():
    banner = [
        " ██████╗  █████╗ ██████╗  █████╗ ███╗   ███╗███████╗ ██████╗ ██████╗  ██████╗ ███████╗",
        " ██╔══██╗██╔══██╗██╔══██╗██╔══██╗████╗ ████║██╔════╝██╔═══██╗██╔══██╗██╔════╝ ██╔════╝",
        " ██████╔╝███████║██████╔╝███████║██╔████╔██║█████╗  ██║   ██║██████╔╝██║  ███╗█████╗  ",
        " ██╔═══╝ ██╔══██║██╔══██╗██╔══██║██║╚██╔╝██║██╔══╝  ██║   ██║██╔══██╗██║   ██║██╔══╝  ",
        " ██║     ██║  ██║██║  ██║██║  ██║██║ ╚═╝ ██║██║     ╚██████╔╝██║  ██║╚██████╔╝███████╗",
        " ╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝     ╚═╝╚═╝      ╚═════╝ ╚═╝  ╚═╝ ╚═════╝ ╚══════╝"
    ]
    
    # Print the banner with a delay
    for line in banner:
        print(line)
        time.sleep(0.2)  # Adjust the delay (in seconds) as needed
    
    # Print "Developed by Shosha" in a centered and formatted style
    author_line = "Developed by Shosha"
    padding = (len(banner[0]) - len(author_line)) // 2  # Center the text
    print("\n" + " " * padding + author_line + "\n")
    time.sleep(0.5)  # Slightly longer delay after the author line

# List of unique User-Agent strings for rotation
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:89.0) Gecko/20100101 Firefox/89.0',
    'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:89.0) Gecko/20100101 Firefox/89.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 Edg/91.0.864.59',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 OPR/77.0.4054.203',
    'Mozilla/5.0 (Linux; Android 10; SM-G975F) AppleWebKit/537.36 (KHTML, like Gecko) SamsungBrowser/14.0 Chrome/87.0.4280.141 Mobile Safari/537.36',
    'Mozilla/5.0 (Linux; Android 11; Pixel 5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.120 Mobile Safari/537.36',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Mobile/15E148 Safari/604.1',
    'Mozilla/5.0 (Windows NT 10.0; WOW64; Trident/7.0; rv:11.0) like Gecko',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 Brave/91.0.4472.124',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 Vivaldi/3.8.2259.42',
]

class ParameterDiscoverer:
    def __init__(self, target_urls, wordlist_source, threads=10, rate_limit=10, method='GET', post_data=None, timeout=5, proxy=None, headers=None, verbose=False, output_file=None):
        self.target_urls = target_urls
        self.wordlist_source = wordlist_source
        self.threads = threads
        self.rate_limit = rate_limit
        self.method = method.upper()
        self.post_data = post_data
        self.timeout = timeout
        self.proxy = proxy
        self.headers = headers if headers else {}
        self.verbose = verbose
        self.output_file = output_file
        self.baseline_responses = {}
        self.last_request_time = 0
        self.request_lock = threading.Lock()
        self.valid_parameters = []

    def fetch_wordlist(self):
        """Fetch wordlist from a URL or local file."""
        if self.wordlist_source.startswith(('http://', 'https://')):
            try:
                response = requests.get(self.wordlist_source)
                response.raise_for_status()  # Raise an error for bad status codes
                return response.text.splitlines()
            except requests.exceptions.RequestException as e:
                logging.error(f"Failed to fetch wordlist from {self.wordlist_source}: {e}")
                return []
        else:
            try:
                with open(self.wordlist_source, "r") as file:
                    return [line.strip() for line in file if line.strip()]
            except FileNotFoundError:
                logging.error(f"Wordlist file '{self.wordlist_source}' not found.")
                return []

    def get_baseline_response(self, url):
        try:
            if self.method == 'GET':
                response = requests.get(url, timeout=self.timeout, proxies=self.proxy, headers=self.headers)
            elif self.method == 'POST':
                data = self.post_data.copy() if self.post_data else {}
                response = requests.post(url, data=data, timeout=self.timeout, proxies=self.proxy, headers=self.headers)
            else:
                logging.error(f"Unsupported HTTP method: {self.method}")
                return None
            logging.info(f"Baseline response received for {url} with status code {response.status_code}")
            return response
        except requests.exceptions.RequestException as e:
            logging.error(f"Failed to get baseline response for {url}: {e}")
            return None

    def is_parameter_valid(self, test_response, url):
        baseline_response = self.baseline_responses.get(url)
        if not baseline_response:
            logging.warning(f"Baseline response not available for {url}. Cannot validate parameter.")
            return False
        # Compare response content using fuzzy matching
        similarity = fuzz.ratio(test_response.text, baseline_response.text)
        return similarity < 90  # Parameter is valid if responses are less than 90% similar

    def test_parameter(self, parameter, url):
        with self.request_lock:
            interval = 1.0 / self.rate_limit if self.rate_limit > 0 else 0
            elapsed = time.time() - self.last_request_time
            if elapsed < interval:
                time.sleep(interval - elapsed)
            self.last_request_time = time.time()

        headers = {**self.headers, 'User-Agent': random.choice(USER_AGENTS)}
        try:
            if self.method == 'GET':
                response = requests.get(url, params={parameter: "test"}, headers=headers, timeout=self.timeout, proxies=self.proxy)
            elif self.method == 'POST':
                data = self.post_data.copy() if self.post_data else {}
                data[parameter] = "test"
                response = requests.post(url, data=data, headers=headers, timeout=self.timeout, proxies=self.proxy)
            else:
                logging.error(f"Unsupported HTTP method: {self.method}")
                return

            if self.is_parameter_valid(response, url):
                self.valid_parameters.append((url, parameter))
                logging.info(f"Discovered parameter '{parameter}' for {url}")
            elif self.verbose:
                logging.debug(f"Parameter '{parameter}' not valid for {url}.")

        except requests.exceptions.RequestException as e:
            logging.error(f"Request error for parameter '{parameter}' on {url}: {e}")

    def save_results(self):
        if not self.output_file:
            return
        try:
            with open(self.output_file, "w") as file:
                for url, param in self.valid_parameters:
                    # Generate ready-to-use link
                    if self.method == 'GET':
                        link = f"{url}?{param}=test"
                    elif self.method == 'POST':
                        link = f"{url} (POST data: {param}=test)"
                    file.write(f"{link}\n")
            logging.info(f"Results saved to {self.output_file}")
        except Exception as e:
            logging.error(f"Failed to save results to {self.output_file}: {e}")

    def discover_parameters(self):
        parameters = self.fetch_wordlist()
        if not parameters:
            logging.error("No wordlist loaded. Exiting.")
            return

        for url in self.target_urls:
            self.baseline_responses[url] = self.get_baseline_response(url)
            if not self.baseline_responses[url]:
                logging.error(f"Unable to obtain baseline response for {url}. Skipping parameter discovery.")
                continue

            logging.info(f"Testing {len(parameters)} parameters on {url} using {self.method} requests...")

            with ThreadPoolExecutor(max_workers=self.threads) as executor:
                list(tqdm(executor.map(lambda param: self.test_parameter(param, url), parameters), total=len(parameters), desc=f"Scanning {url}"))

            logging.info(f"\nParameter discovery complete for {url}!")

        if self.valid_parameters:
            logging.info("Valid parameters found:")
            for url, param in self.valid_parameters:
                # Generate ready-to-use link
                if self.method == 'GET':
                    link = f"{url}?{param}=test"
                elif self.method == 'POST':
                    link = f"{url} (POST data: {param}=test)"
                logging.info(f"- {link}")
            self.save_results()
        else:
            logging.info("No valid parameters found.")

def parse_args():
    parser = argparse.ArgumentParser(
        description="Parameter Discovery Script",
        epilog="""
Examples:
1. Single domain with GET method:
   python parameter_discoverer.py -d https://example.com -w wordlist.txt -t 10 -r 10 -v

2. List of domains with POST method and custom POST data:
   python parameter_discoverer.py -l domains.txt -w advanced_wordlist.txt -m POST --post-data '{"key": "value"}' -v

3. Use a proxy server and custom headers:
   python parameter_discoverer.py -d https://example.com -w wordlist.txt --proxy http://127.0.0.1:8080 --headers '{"X-Custom-Header": "value"}' -v

4. Set a custom timeout and rate limit:
   python parameter_discoverer.py -d https://example.com -w wordlist.txt --timeout 10 -r 5 -v

5. Enable verbose output for debugging:
   python parameter_discoverer.py -d https://example.com -w wordlist.txt -v

6. Save results to a file:
   python parameter_discoverer.py -d https://example.com -w wordlist.txt -o results.txt
""",
        formatter_class=argparse.RawTextHelpFormatter
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-d", "--domain", help="Single domain to scan (e.g., https://example.com)")
    group.add_argument("-l", "--list", help="Path to file containing list of domains to scan (one per line)")

    parser.add_argument("-w", "--wordlist", required=True, help="Path to the parameter wordlist file or URL (one parameter per line)")
    parser.add_argument("-t", "--threads", type=int, default=10, help="Number of threads to use per domain (default: 10)")
    parser.add_argument("-r", "--rate-limit", type=int, default=10, help="Maximum requests per second (default: 10)")
    parser.add_argument("-m", "--method", choices=['GET', 'POST'], default='GET', help="HTTP method to use (default: GET)")
    parser.add_argument("--post-data", type=json.loads, help="JSON string of data for POST requests (e.g., '{\"key\": \"value\"}')")
    parser.add_argument("--timeout", type=int, default=5, help="Request timeout in seconds (default: 5)")
    parser.add_argument("--proxy", help="Proxy server to use (e.g., http://127.0.0.1:8080)")
    parser.add_argument("--headers", type=json.loads, help="JSON string of custom headers to use (e.g., '{\"X-Custom-Header\": \"value\"}')")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output for debugging")
    parser.add_argument("-o", "--output", help="Save results to a text file (e.g., results.txt)")

    return parser.parse_args()

def main():
    print_banner()  # Print the banner with a delay
    args = parse_args()

    # Set up logging
    logging_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=logging_level, format='%(asctime)s - %(levelname)s - %(message)s')

    # Load target URLs
    if args.domain:
        target_urls = [args.domain]
    elif args.list:
        try:
            with open(args.list, "r") as file:
                target_urls = [line.strip() for line in file if line.strip()]
        except FileNotFoundError:
            logging.error(f"List file '{args.list}' not found.")
            exit(1)

    # Initialize the ParameterDiscoverer
    discoverer = ParameterDiscoverer(
        target_urls=target_urls,
        wordlist_source=args.wordlist,
        threads=args.threads,
        rate_limit=args.rate_limit,
        method=args.method,
        post_data=args.post_data,
        timeout=args.timeout,
        proxy={"http": args.proxy, "https": args.proxy} if args.proxy else None,
        headers=args.headers,
        verbose=args.verbose,
        output_file=args.output
    )

    # Run the parameter discovery
    discoverer.discover_parameters()

if __name__ == "__main__":
    main()