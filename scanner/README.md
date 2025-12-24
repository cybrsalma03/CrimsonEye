# Vulnerability Scanner

## Overview
The **Vulnerability Scanner** is a powerful tool designed to identify security vulnerabilities in web applications. It uses YAML-based templates to define scanning rules and supports multi-threading for efficient scanning. The tool is highly customizable, allowing users to define their own templates, set scan parameters, and generate detailed reports in various formats.

## Features
- **Template-Based Scanning**: Define custom scanning rules using YAML templates.
- **Multi-Threading**: Scan multiple targets simultaneously for faster results.
- **Dynamic Payload Generation**: Automatically generate payloads for fuzzing and mutation.
- **Customizable Headers**: Add custom HTTP headers to requests.
- **Proxy Support**: Route requests through proxies for anonymity.
- **Interactive Mode**: Pause, resume, or stop scans interactively.
- **Report Generation**: Generate reports in JSON, CSV, HTML, or plain text formats.
- **Template Validation**: Validate YAML templates before scanning.
- **Resume Scans**: Save and resume scan progress from a state file.
- **Banner Display**: Display a custom banner at the start of the scan.

## Installation

### Prerequisites
- Python 3.7 or higher
- `pip` (Python package manager)

### Steps
1. Clone the repository:
   ```bash
   git clone https://github.com/your-username/vulnerability-scanner.git
   cd vulnerability-scanner
   ```
2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the scanner:
   ```bash
   python scanner.py --help
   ```

## Usage

### Basic Command
```bash
python scanner.py -d http://example.com -t templates
```

### Command-Line Options

| Option                  | Description                                                                 |
|-------------------------|-----------------------------------------------------------------------------|
| `-d, --targets`         | List of targets to scan (e.g., http://example.com).                        |
| `-t, --templates`       | Directory containing YAML templates.                                       |
| `-r, --rate-limit`      | Maximum number of concurrent requests (default: 10).                      |
| `-f, --format`          | Output format (json, csv, html, text).                                     |
| `-o, --output`          | Output file to save results.                                               |
| `--delay`               | Random delay between requests (in seconds).                               |
| `-u, --user-agents`     | Path to the user agents file.                                              |
| `-p, --proxies`         | Path to the proxies file.                                                  |
| `--validate-templates`  | Validate templates before scanning.                                        |
| `--silent`              | Display findings only.                                                    |
| `--debug`               | Show all requests and responses.                                          |
| `--severity`            | Filter templates by severity (e.g., high,critical).                       |
| `--tags`                | Filter templates by tags (e.g., sqli,xss).                                |
| `--exclude-templates`   | Exclude specific templates or directories (e.g., dir1,dir2).              |
| `--custom-headers`      | Add custom headers to requests (e.g., Authorization: Bearer token).       |
| `--follow-redirects`    | Enable following redirects for HTTP requests.                             |
| `--timeout`             | Timeout for requests (in seconds, default: 10).                          |
| `--retries`             | Number of retries for failed requests (default: 1).                       |
| `--bulk-size`           | Number of hosts processed in parallel per template (default: 25).         |
| `--interactive`         | Enable interactive mode (pause/resume/exit scans).                        |
| `--list-templates`      | List all available templates.                                              |
| `--resume`              | Resume scan from a saved state file.                                      |

## Template Structure

Templates are defined in YAML format. Below is an example template:

```yaml
id: example-template
info:
  name: Example Template
  severity: high
  tags: sqli
requests:
  - method: GET
    path: /vulnerable-endpoint
    matchers:
      - type: regex
        regex: "SQL syntax error"
```

### Fields
- `id`: Unique identifier for the template.
- `info`: Metadata about the template (e.g., name, severity, tags).
- `requests`: List of HTTP requests to perform.
  - `method`: HTTP method (e.g., GET, POST).
  - `path`: Path to the endpoint.
  - `matchers`: List of matchers to identify vulnerabilities.
    - `type`: Type of matcher (e.g., regex).
    - `regex`: Regular expression to match in the response.

## Examples

### Scan a Single Target
```bash
python scanner.py -d http://example.com -t templates
```

### Scan Multiple Targets
```bash
python scanner.py -d http://example.com http://test.com -t templates
```

### Generate HTML Report
```bash
python scanner.py -d http://example.com -t templates -f html -o report.html
```

### Resume a Scan
```bash
python scanner.py -d http://example.com -t templates --resume state.json
