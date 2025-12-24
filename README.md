# 🔴 Crimson Eye Suite

Crimson Eye Suite is a Linux-based modular vulnerability scanning framework designed to support both **offensive security testing** and **defensive security operations**.  
It integrates multiple reconnaissance and scanning tools into a single, lightweight, and extensible framework while maintaining the ability for each module to run independently.

The suite focuses on **speed, modularity, and automation**, making it suitable for penetration testers, security researchers, and SOC teams.


## 🚀 Features

- Modular architecture with independent tools
- Interactive terminal-based launcher
- Clickable executable icon for easy execution on Linux
- YAML-based vulnerability scanning (Nuclei-like)
- Supports both offensive and defensive use cases
- Generates clear and actionable outputs
- Designed for performance with minimal overhead


## 🧰 Tools Included

### 🔍 SubScoutX
A subdomain enumeration tool that performs active and passive discovery to uncover hidden subdomains and expand the attack surface.

### 🌐 DomainPulse
A domain and endpoint status checker that validates HTTP response codes to quickly identify live and accessible assets.

### 🧪 ParamForge
A parameter discovery tool inspired by ParamSpider that identifies hidden GET and POST parameters using customizable wordlists.

### 🛡 Scanner
A YAML-based vulnerability scanner inspired by Nuclei that executes predefined or custom templates to detect common vulnerabilities and misconfigurations.


## 🖥 How It Works

- The suite can be launched:
  - As a normal Linux command (after adding it to `$PATH`)
  - By clicking the provided executable icon (`.desktop` file)
- Launching the suite opens an **interactive shell**
- Users select tools from a numbered CLI menu
- Tools can run independently or in a chained workflow
- Outputs from one tool can be reused by others
- A final report can be generated summarizing findings


## 📦 Installation

### Requirements
- Linux-based OS
- Python 3.9+
- Git
- Required Python libraries (see below)

### Clone the Repository
```bash
git clone https://github.com/cybrsalma03/CrimsonEye.git
cd CrimsonEye
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Make Launcher Executable

```bash
chmod +x main.py
```

(Optional) Add to PATH:

```bash
sudo cp main.py /usr/local/bin/crimson-eye
```


## ▶ Running the Suite

### Run as a Command

```bash
crimson-eye
```

### Run via Clickable Icon

* Use the provided `.desktop` file
* Clicking the icon opens an interactive terminal and launches the suite


## 📄 Templates

The Scanner module uses YAML templates similar to Nuclei.

Example:

```yaml
id: sql-injection
info:
  name: SQL Injection
  severity: high
requests:
  - method: GET
    path: /vuln.php
    params:
      id: "1 OR 1=1"
```


## 🛡 Defensive Use Cases

* Shadow IT discovery
* Phishing domain detection
* Infrastructure change monitoring
* Proactive vulnerability assessment
* Compliance and audit support


## ⚔ Offensive Use Cases

* Attack surface expansion
* Hidden parameter discovery
* Automated vulnerability scanning
* Multi-stage exploitation simulation

> ⚠️ This project is intended **for educational and authorized security testing only**.


## ⚖ Ethical Use & License

Crimson Eye Suite is a **dual-use security framework**.

* Use only on systems you own or have explicit permission to test
* The developers are **not responsible for misuse**

📜 **License:**
This project is released under the **MIT License**.


## 👥 Development Team

Developed as a graduation project by a cybersecurity-focused team with interests in:

* Penetration Testing
* SOC Operations
* Vulnerability Research
* Defensive Security Engineering

Supervised under academic guidance.


## 📌 Future Enhancements

* Advanced reporting and visualization
* More vulnerability templates
* Improved integration with SIEM platforms
* Enhanced automation and scheduling
* Performance optimizations


## ⭐ Acknowledgments

* Inspired by tools such as Nuclei, Amass, and ParamSpider
* Thanks to our supervisor for guidance and support
* Thanks to the open-source security community



> **Crimson Eye Suite bridges the gap between offensive reconnaissance and defensive security operations, delivering a fast, modular, and practical cybersecurity framework.**
