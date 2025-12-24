#!/usr/bin/env python3
import subprocess
import yaml
import os
import logging
import asyncio
import socket
from functools import lru_cache
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
import argparse
import time

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Print a banner for the script

def print_banner():
    banner = [
        "███████╗██╗   ██╗██████╗ ███████╗ ██████╗ ██████╗ ██╗   ██╗████████╗██╗  ██╗",
        "██╔════╝██║   ██║██╔══██╗██╔════╝██╔════╝██╔═══██╗██║   ██║╚══██╔══╝╚██╗██╔╝",
        "███████╗██║   ██║██████╔╝███████╗██║     ██║   ██║██║   ██║   ██║    ╚███╔╝ ",
        "╚════██║██║   ██║██╔══██╗╚════██║██║     ██║   ██║██║   ██║   ██║    ██╔██╗ ",
        "███████║╚██████╔╝██████╔╝███████║╚██████╗╚██████╔╝╚██████╔╝   ██║   ██╔╝ ██╗",
        "╚══════╝ ╚═════╝ ╚═════╝ ╚══════╝ ╚═════╝ ╚═════╝  ╚═════╝    ╚═╝   ╚═╝  ╚═╝"
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
    

# Load the YAML configuration file
def load_config(config_path):
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found: {config_path}")
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

# Cache DNS lookups to avoid redundant lookups
@lru_cache(maxsize=100)
def resolve_domain(domain):
    try:
        return socket.gethostbyname(domain)
    except socket.gaierror:
        raise ValueError(f"Domain {domain} cannot be resolved (DNS Error)")

# Execute a command and return its output
async def execute_command_async(command, timeout=60):
    try:
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
        if process.returncode != 0:
            logging.error(f"Command '{command}' failed with error:\n{stderr.decode()}")
            return ""
        return stdout.decode().strip()
    except asyncio.TimeoutError:
        logging.error(f"Command '{command}' timed out after {timeout} seconds.")
        return ""
    except Exception as e:
        logging.error(f"Error executing command '{command}': {e}")
        return ""

# Run a tool and collect its output
async def run_tool_async(tool_name, tool_config, domain, verbose=False):
    command = tool_config.get("command")
    if not command:
        logging.warning(f"Skipping invalid tool configuration for: {tool_name}")
        return []

    command = command.replace("{domain}", domain)

    if verbose:
        logging.info(f"[+] Running {tool_name} with command: {command}")

    output = await execute_command_async(command, timeout=tool_config.get("timeout", 60))
    if verbose:
        logging.info(f"[+] {tool_name} output:\n{output}")

    return [line.strip() for line in output.splitlines() if line.strip()]

# Main subdomain enumeration logic
async def subdomain_enum_async(config, domain, verbose=False):
    results = set()
    tools = config.get("tools", {})
    tasks = [run_tool_async(tool_name, tool_config, domain, verbose) for tool_name, tool_config in tools.items()]

    for task in tqdm(asyncio.as_completed(tasks), total=len(tasks), desc="Running tools"):
        try:
            output = await task
            results.update(output)
        except Exception as e:
            logging.error(f"Error running tool: {e}")

    return results

# Save results to a file
def save_results(results, output_file, output_dir=".", format="txt"):
    output_path = os.path.join(output_dir, output_file)
    if format == "txt":
        with open(output_path, 'w') as f:
            f.write("\n".join(sorted(results)))
        logging.info(f"[+] Results saved to {output_path}")
    elif format == "json":
        with open(output_path, 'w') as f:
            json.dump(sorted(results), f, indent=4)
        logging.info(f"[+] Results saved to {output_path} in JSON format")
    else:
        logging.error(f"Unsupported format: {format}")

# Parse command-line arguments
def parse_args():
    parser = argparse.ArgumentParser(description="Subdomain Enumeration Tool")
    parser.add_argument("-d", "--domain", help="Domain to enumerate subdomains for")
    parser.add_argument("-l", "--list", help="File containing a list of domains to enumerate")
    parser.add_argument("-c", "--config", default="config.yaml", help="Path to the configuration file")
    parser.add_argument("-o", "--output", default="subdomains.txt", help="Output file name")
    parser.add_argument("-f", "--format", choices=["txt", "json"], default="txt", help="Output format")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output")
    parser.add_argument("--timeout", type=int, default=60, help="Default timeout for each tool in seconds")
    parser.add_argument("--output-dir", default=".", help="Directory to save the output file")
    return parser.parse_args()

# Rate limiter to control the number of requests per second
class RateLimiter:
    def __init__(self, max_requests, per_seconds):
        self.max_requests = max_requests
        self.per_seconds = per_seconds
        self.timestamps = []

    async def wait(self):
        now = time.time()
        self.timestamps = [t for t in self.timestamps if now - t < self.per_seconds]
        if len(self.timestamps) >= self.max_requests:
            await asyncio.sleep(self.per_seconds - (now - self.timestamps[0]))
        self.timestamps.append(time.time())

# Main function to execute the script
async def main():
    print_banner()
    args = parse_args()

    try:
        logging.info("[+] Loading configuration...")
        config = load_config(args.config)

        if args.list:
            logging.info("[+] Processing multiple domains from file...")
            with open(args.list, 'r') as f:
                domains = [line.strip() for line in f if line.strip()]

            for domain in domains:
                try:
                    logging.info(f"[+] Processing domain: {domain}")
                    resolve_domain(domain)  # Validate domain by resolving it
                    subdomains = await subdomain_enum_async(config, domain, args.verbose)
                    output_file = f"subdomains_{domain.replace('.', '_')}.{args.format}"
                    save_results(subdomains, output_file, args.output_dir, args.format)
                except Exception as e:
                    logging.error(f"[-] Error processing domain {domain}: {e}")
        else:
            if not args.domain:
                raise ValueError("Please provide a domain using the -d/--domain flag or a list of domains using the -l/--list flag.")

            logging.info("[+] Validating domain...")
            resolve_domain(args.domain)  # Validate domain by resolving it

            logging.info("[+] Starting subdomain enumeration...")
            subdomains = await subdomain_enum_async(config, args.domain, args.verbose)

            logging.info(f"[+] Found {len(subdomains)} unique subdomains.")
            save_results(subdomains, args.output, args.output_dir, args.format)
    except Exception as e:
        logging.error(f"[-] Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())