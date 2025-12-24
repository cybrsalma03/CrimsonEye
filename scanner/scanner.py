#!/usr/bin/env python3
import os
import re
import yaml
import json
import csv
import argparse
import random
import time
import requests
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from rich.console import Console
from rich.table import Table
from rich.progress import Progress
import git
from nuclei_handler import NucleiHandler  # Import the Nuclei template handler

# Initialize Rich console for colored output
console = Console()

class VulnScanner:
    def __init__(self, template_dir, rate_limit, output_format, output_file, delay, user_agents_file, proxies_file, validate_templates, silent, debug, severity, tags, exclude_templates, custom_headers, follow_redirects, timeout, retries, bulk_size, interactive, list_templates, resume_file):
        self.template_dir = template_dir
        self.rate_limit = rate_limit
        self.output_format = output_format
        self.output_file = output_file
        self.delay = delay
        self.user_agents = self.load_user_agents(user_agents_file)
        self.proxies = self.load_proxies(proxies_file)
        self.validate_templates = validate_templates
        self.silent = silent
        self.debug = debug
        self.severity = severity
        self.tags = tags
        self.exclude_templates = exclude_templates
        self.custom_headers = custom_headers
        self.follow_redirects = follow_redirects
        self.timeout = timeout
        self.retries = retries
        self.bulk_size = bulk_size
        self.interactive = interactive
        self.list_templates = list_templates
        self.resume_file = resume_file
        self.results = []
        self.template_cache = {}
        self.scan_state = {"completed_targets": [], "remaining_targets": [], "templates": []}
        self.nuclei_handler = NucleiHandler()  # Initialize Nuclei template handler
        logging.basicConfig(filename="scanner.log", level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

    def load_user_agents(self, user_agents_file):
        """Load user agents from a file. If no file is provided, use a default list."""
        if not user_agents_file:
            console.print("[*] No user agents file provided. Using default user agents.", style="bold yellow")
            return [
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
            ]
        if not os.path.exists(user_agents_file):
            console.print(f"[-] User agents file not found: {user_agents_file}", style="bold red")
            console.print("[*] Using default user agents.", style="bold yellow")
            return [
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
            ]
        with open(user_agents_file, 'r') as file:
            return [line.strip() for line in file if line.strip()]

    def load_proxies(self, proxies_file):
        """Load proxies from a file. If no file is provided, return an empty list."""
        if not proxies_file:
            console.print("[*] No proxies file provided. Proxies will not be used.", style="bold yellow")
            return []
        if not os.path.exists(proxies_file):
            console.print(f"[-] Proxies file not found: {proxies_file}", style="bold red")
            console.print("[*] Proxies will not be used.", style="bold yellow")
            return []
        with open(proxies_file, 'r') as file:
            return [line.strip() for line in file if line.strip()]

    def load_all_templates(self):
        """Load all YAML templates from the template directory."""
        templates = []
        for root, _, files in os.walk(self.template_dir):
            for file in files:
                if file.endswith(".yaml") or file.endswith(".yml"):
                    templates.append(os.path.join(root, file))
        return templates

    def load_template(self, template_path):
        """Load a YAML template from cache or disk."""
        if template_path in self.template_cache:
            return self.template_cache[template_path]
        try:
            with open(template_path, 'r') as file:
                template = yaml.safe_load(file)
                self.template_cache[template_path] = template
                return template
        except Exception as e:
            logging.error(f"Error loading template {template_path}: {e}")
            console.print(f"[-] Error loading template {template_path}: {e}", style="bold red")
            return None

    def preprocess_template(self, template):
        """Preprocess template for better performance and validation."""
        return self.nuclei_handler.validate_template(template)

    def generate_dynamic_payload(self, payload):
        """Generate dynamic payloads for Nuclei templates."""
        return self.nuclei_handler.generate_payload(payload)

    def send_request(self, target, request):
        """Send an HTTP request with retries and exponential backoff."""
        retries = self.retries
        while retries >= 0:
            try:
                proxy = random.choice(self.proxies) if self.proxies else None
                url = target + request.get("path", "")
                headers = self.randomize_headers()
                payload = self.generate_dynamic_payload(request.get("data", ""))
                # Debugging: Print request details
                if self.debug:
                    console.print(f"[*] Sending request to {url}", style="bold blue")
                    console.print(f"Headers: {headers}", style="bold blue")
                    console.print(f"Payload: {payload}", style="bold blue")
                response = requests.request(
                    method=request.get('method', 'GET'),
                    url=url,
                    headers=headers,
                    params=request.get("params", {}),
                    data=payload,
                    proxies={"http": proxy, "https": proxy} if proxy else None,
                    timeout=self.timeout,
                    allow_redirects=self.follow_redirects
                )
                logging.debug(f"Received response: {response.status_code}")
                return response
            except requests.RequestException as e:
                retries -= 1
                if retries < 0:
                    logging.error(f"Error scanning {target}: {e}, URL: {url}, Headers: {headers}")
                    console.print(f"[-] Error scanning {target}: {e}, URL: {url}, Headers: {headers}", style="bold red")
                    return None
                time.sleep(2 ** (self.retries - retries))  # Exponential backoff

    def randomize_headers(self):
        """Generate random headers for each request."""
        headers = {
            "User-Agent": random.choice(self.user_agents),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Connection": "keep-alive",
        }
        if self.custom_headers:
            headers.update(self.custom_headers)
        return headers

    def exclude_template(self, template_path):
        """Check if a template should be excluded based on the exclude_templates list."""
        if not self.exclude_templates:
            return False
        for exclude in self.exclude_templates:
            if exclude in template_path:
                return True
        return False

    def filter_template_by_severity(self, template):
        """Filter templates by severity."""
        if not self.severity:
            return True
        return template.get("info", {}).get("severity", "").lower() in self.severity

    def filter_template_by_tags(self, template):
        """Filter templates by tags."""
        if not self.tags:
            return True
        template_tags = template.get("info", {}).get("tags", [])
        if isinstance(template_tags, str):
            template_tags = [template_tags]
        return any(tag.lower() in self.tags for tag in template_tags)

    def escape_html(self, text):
        """Escape HTML content to prevent XSS."""
        if not text:
            return ""
        return (
            text.replace("&", "&amp;")
                .replace("<", "<")
                .replace(">", ">")
                .replace('"', "&quot;")
                .replace("'", "&#39;")
        )

    def scan_target(self, target, template):
        """Scan a target using a specific template."""
        requests = template.get("requests", [])
        if isinstance(requests, dict):  # Handle single request case
            requests = [requests]
        for request in requests:
            response = self.send_request(target, request)
            if response:
                matchers = request.get("matchers", [])
                if isinstance(matchers, dict):  # Handle single matcher case
                    matchers = [matchers]
                for matcher in matchers:
                    if self.nuclei_handler.match_response(response, matcher):
                        self.results.append({
                            "target": target,
                            "template": template["id"],
                            "path": request.get("path", ""),
                            "matched": matcher.get("match", ""),  # Use 'match' instead of 'regex'
                            "severity": template.get("info", {}).get("severity", "N/A"),  # Add severity
                        })
                        console.print(f"[+] Vulnerability found: {template['id']} at {target}{request.get('path', '')}", style="bold green")

    def save_results(self):
        """Save scan results to a file based on the output format."""
        if not self.results:
            console.print("[-] No results to save.", style="bold red")
            return
        if self.output_format == "json":
            with open(self.output_file, 'w') as file:
                json.dump(self.results, file, indent=4)
        elif self.output_format == "csv":
            with open(self.output_file, 'w', newline='') as file:
                writer = csv.DictWriter(file, fieldnames=["target", "template", "path", "matched", "severity"])
                writer.writeheader()
                writer.writerows(self.results)
        elif self.output_format == "html":
            self.generate_html_report(self.results, self.output_file)
        elif self.output_format == "text":
            with open(self.output_file, 'w') as file:
                for result in self.results:
                    file.write(f"Target: {result['target']}\n")
                    file.write(f"Template: {result['template']}\n")
                    file.write(f"Path: {result['path']}\n")
                    file.write(f"Matched: {result['matched']}\n")
                    file.write(f"Severity: {result.get('severity', 'N/A')}\n")
                    file.write("\n")
        console.print(f"[+] Results saved to {self.output_file}", style="bold green")

    def generate_html_report(self, results, output_file):
        """Generate an HTML report using an external template."""
        template_path = os.path.join("config", "html_template.html")
        if not os.path.exists(template_path):
            console.print(f"[-] HTML template not found: {template_path}", style="bold red")
            return
        # Load the external HTML template
        with open(template_path, 'r') as file:
            html_template = file.read()
        # Generate rows for the table
        rows = ""
        for result in results:
            rows += f"""
            <tr>
                <td>{self.escape_html(result['target'])}</td>
                <td>{self.escape_html(result['template'])}</td>
                <td>{self.escape_html(result['path'])}</td>
                <td>{self.escape_html(result['matched'])}</td>  <!-- Escape the matched field -->
                <td>{self.escape_html(result.get('severity', 'N/A'))}</td>
            </tr>
            """
        # Replace the placeholder with the generated rows
        html = html_template.replace("{rows}", rows)
        # Save the final HTML report
        with open(output_file, 'w') as file:
            file.write(html)

    def update_templates(self):
        """Update templates from a remote repository."""
        try:
            repo = git.Repo(self.template_dir)
            repo.remotes.origin.pull()
            console.print("[+] Templates updated successfully.", style="bold green")
        except Exception as e:
            console.print(f"[-] Failed to update templates: {e}", style="bold red")

    def save_scan_state(self):
        """Save the current scan state to a file."""
        with open(self.resume_file, 'w') as file:
            json.dump(self.scan_state, file)
        console.print(f"[+] Scan state saved to {self.resume_file}", style="bold green")

    def load_scan_state(self):
        """Load the scan state from a file."""
        if not os.path.exists(self.resume_file):
            console.print(f"[-] Resume file not found: {self.resume_file}", style="bold red")
            return False
        with open(self.resume_file, 'r') as file:
            self.scan_state = json.load(file)
        console.print(f"[+] Scan state loaded from {self.resume_file}", style="bold green")
        return True

    def count_templates(self):
        """Count the number of valid templates and display invalid templates with suggestions."""
        templates = self.load_all_templates()
        valid_templates = []
        invalid_templates = []
        for template_path in templates:
            template = self.load_template(template_path)
            if self.validate_templates and not self.preprocess_template(template):
                invalid_templates.append((template_path, self.nuclei_handler.get_template_validation_errors(template)))
                continue
            valid_templates.append(template_path)
        console.print(f"[+] Found {len(valid_templates)} valid templates.", style="bold green")
        if invalid_templates:
            console.print(f"[-] Found {len(invalid_templates)} invalid templates:", style="bold red")
            for template_path, errors in invalid_templates:
                console.print(f"    - {template_path}: {errors}", style="bold red")
                console.print(f"      Suggested Fix: {self.nuclei_handler.suggest_fix_for_template(errors)}", style="bold yellow")
        return valid_templates

    def list_all_templates(self):
        """List all available templates with details."""
        templates = self.load_all_templates()
        table = Table(title="Available Templates", show_header=True, header_style="bold magenta")
        table.add_column("Template ID", style="cyan")
        table.add_column("Severity", style="yellow")
        table.add_column("Tags", style="green")
        table.add_column("Path", style="blue")
        for template_path in templates:
            template = self.load_template(template_path)
            if self.validate_templates and not self.preprocess_template(template):
                continue
            table.add_row(
                template.get("id", "N/A"),
                template.get("info", {}).get("severity", "N/A"),
                template.get("info", {}).get("tags", "N/A"),
                template_path
            )
        console.print(table)

    def run(self, targets):
        """Run the scanner on multiple targets."""
        if self.list_templates:
            self.list_all_templates()
            return
        valid_templates = self.count_templates()
        if not valid_templates:
            console.print("[-] No valid templates found. Exiting.", style="bold red")
            return
        if self.resume_file and self.load_scan_state():
            targets = self.scan_state["remaining_targets"]
            templates = self.scan_state["templates"]
        else:
            templates = valid_templates
            self.scan_state["remaining_targets"] = targets
            self.scan_state["templates"] = templates
        with ThreadPoolExecutor(max_workers=self.rate_limit) as executor:
            futures = []
            for template_path in templates:
                if self.exclude_template(template_path):
                    continue
                template = self.load_template(template_path)
                if self.validate_templates and not self.preprocess_template(template):
                    continue
                if not self.filter_template_by_severity(template):
                    continue
                if not self.filter_template_by_tags(template):
                    continue
                for target in targets:
                    if target in self.scan_state["completed_targets"]:
                        continue
                    futures.append(executor.submit(self.scan_target, target, template))
            with Progress() as progress:
                task = progress.add_task("[cyan]Scanning...", total=len(futures))
                paused = False
                for future in as_completed(futures):
                    if paused:
                        command = input("Enter command (resume/exit): ").strip().lower()
                        if command == "resume":
                            paused = False
                            console.print("[+] Resuming scan...", style="bold green")
                        elif command == "exit":
                            self.save_scan_state()
                            console.print("[+] Scan stopped. Use --resume to continue.", style="bold green")
                            return
                    if not paused:
                        progress.update(task, advance=1)
                        if self.interactive:
                            command = input("Enter command (pause/resume/exit/status): ").strip().lower()
                            if command == "pause":
                                paused = True
                                self.save_scan_state()
                                console.print("[+] Scan paused. Use --resume to continue.", style="bold green")
                            elif command == "status":
                                console.print(f"[+] Completed: {len(self.scan_state['completed_targets'])}, Remaining: {len(self.scan_state['remaining_targets'])}", style="bold blue")
                            elif command == "exit":
                                self.save_scan_state()
                                console.print("[+] Scan stopped. Use --resume to continue.", style="bold green")
                                return
        if self.output_file:
            self.save_results()
            if not self.silent:
                console.print(f"[bold green]Results saved to {self.output_file}[/bold green]", style="bold")


def main():
    # Display the banner
    banner = """
 ██████╗ ██╗   ██╗███████╗███████╗███████╗██████╗ 
 ██╔══██╗██║   ██║██╔════╝██╔════╝██╔════╝██╔══██╗
 ██████╔╝██║   ██║███████╗███████╗█████╗  ██████╔╝
 ██╔═══╝ ██║   ██║╚════██║╚════██║██╔══╝  ██╔══██╗
 ██║     ╚██████╔╝███████║███████║███████╗██║  ██║
 ╚═╝      ╚═════╝ ╚══════╝╚══════╝╚══════╝╚═╝  ╚═╝
 Author: Shosha
    """
    console.print(banner, style="bold red")
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description="Advanced Vulnerability Scanner",
        epilog="Examples:\n"
        "  python scanner.py -d http://example.com http://test.com -t templates\n"
        "  python scanner.py -d http://example.com -t templates -u config/user_agents.txt -p config/proxies.txt\n"
        "  python scanner.py -d http://example.com -t templates -r 5 -f csv -o results.csv\n"
        "  python scanner.py -d http://example.com -t templates --delay 2\n"
        "  python scanner.py -d http://example.com -t templates --validate-templates\n"
        "  python scanner.py -d http://example.com -t templates --silent\n"
        "  python scanner.py -d http://example.com -t templates --debug\n"
        "  python scanner.py -d http://example.com -t templates --severity high,critical\n"
        "  python scanner.py -d http://example.com -t templates --tags sqli,xss\n"
        "  python scanner.py -d http://example.com -t templates --exclude-templates dir1,dir2\n"
        "  python scanner.py -d http://example.com -t templates --custom-headers 'Authorization: Bearer token'\n"
        "  python scanner.py -d http://example.com -t templates --follow-redirects\n"
        "  python scanner.py -d http://example.com -t templates --timeout 15\n"
        "  python scanner.py -d http://example.com -t templates --retries 3\n"
        "  python scanner.py -d http://example.com -t templates --bulk-size 50\n"
        "  python scanner.py -d http://example.com -t templates --interactive\n"
        "  python scanner.py -t templates --list-templates\n"
        "  python scanner.py -d http://example.com -t templates --resume state.json",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument("-d", "--targets", nargs="+", help="List of targets to scan")
    parser.add_argument("-t", "--templates", required=True, help="Directory containing YAML templates")
    parser.add_argument("-r", "--rate-limit", type=int, default=10, help="Maximum number of concurrent requests")
    parser.add_argument("-f", "--format", choices=["json", "csv", "html", "text"], default="text", help="Output format (json, csv, html, text)")
    parser.add_argument("-o", "--output", help="Output file to save results")
    parser.add_argument("--delay", type=float, help="Random delay between requests (in seconds)")
    parser.add_argument("-u", "--user-agents", help="Path to the user agents file")
    parser.add_argument("-p", "--proxies", help="Path to the proxies file")
    parser.add_argument("--validate-templates", action="store_true", help="Validate templates before scanning")
    parser.add_argument("--silent", action="store_true", help="Display findings only")
    parser.add_argument("--debug", action="store_true", help="Show all requests and responses")
    parser.add_argument("--severity", help="Filter templates by severity (comma-separated, e.g., high,critical)")
    parser.add_argument("--tags", help="Filter templates by tags (comma-separated, e.g., sqli,xss)")
    parser.add_argument("--exclude-templates", help="Exclude specific templates or directories (comma-separated)")
    parser.add_argument("--custom-headers", help="Add custom headers to all requests (e.g., 'Authorization: Bearer token')")
    parser.add_argument("--follow-redirects", action="store_true", help="Enable following redirects for HTTP requests")
    parser.add_argument("--timeout", type=int, default=10, help="Timeout for requests (in seconds)")
    parser.add_argument("--retries", type=int, default=1, help="Number of retries for failed requests")
    parser.add_argument("--bulk-size", type=int, default=25, help="Number of hosts processed in parallel per template")
    parser.add_argument("--interactive", action="store_true", help="Enable interactive mode")
    parser.add_argument("--list-templates", action="store_true", help="List all available templates")
    parser.add_argument("--resume", help="Resume scan from a saved state file")
    args = parser.parse_args()
    if not args.silent:
        console.print("[bold]Starting Vulnerability Scanner...[/bold]", style="bold blue")
    scanner = VulnScanner(
        args.templates,
        args.rate_limit,
        args.format,
        args.output,
        args.delay,
        args.user_agents,
        args.proxies,
        args.validate_templates,
        args.silent,
        args.debug,
        args.severity.lower().split(",") if args.severity else None,
        args.tags.lower().split(",") if args.tags else None,
        args.exclude_templates.split(",") if args.exclude_templates else None,
        dict(header.split(":") for header in args.custom_headers.split(",")) if args.custom_headers else None,
        args.follow_redirects,
        args.timeout,
        args.retries,
        args.bulk_size,
        args.interactive,
        args.list_templates,
        args.resume
    )
    scanner.run(args.targets)
    if not args.silent:
        console.print("[bold]Scan completed![/bold]", style="bold blue")


if __name__ == "__main__":
    main()
