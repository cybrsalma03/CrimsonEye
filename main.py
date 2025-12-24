#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import subprocess
import shlex  # For safely displaying commands
import shutil

# -------------------------------------------------------------------
# دالة تحويل حرف إلى قيمة "سطوع" باستخدام مجموعة حروف مرتبة من الأفتح إلى الأغمق.
# يمكنك تعديل مجموعة الحروف حسب الرغبة.
# -------------------------------------------------------------------
def char_to_brightness(ch, ascii_scale=" .:-=+*#%@"):
    if ch in ascii_scale:
        return ascii_scale.index(ch) / (len(ascii_scale) - 1)
    return 0.5

# -------------------------------------------------------------------
# دالة إعادة تحجيم ASCII art باستخدام تقسيم الكتل (Block Averaging)
#
# تُقسم الرسمة الأصلية إلى كتل بحيث يكون عددها target_width * target_height.
# لكل كتلة تُحسب قيمة متوسط "السطوع"، ثم يُستخلص منها حرف مناسب من ascii_scale.
#
# بهذه الطريقة نُحافظ على التفاصيل بقدر الإمكان عند تقليل حجم الرسمة.
# -------------------------------------------------------------------
def resize_ascii_art_block(art_lines, target_width, target_height, ascii_scale=" .:-=+*#%@"):
    if not art_lines:
        return art_lines

    original_width = max(len(line) for line in art_lines)
    # ملء الفراغات بحيث يكون طول كل سطر متساوٍ
    padded_art = [line.ljust(original_width) for line in art_lines]
    original_height = len(padded_art)

    # حساب حجم كل كتلة في الرسمة الأصلية
    block_width = original_width / target_width
    block_height = original_height / target_height

    new_art = []
    for i in range(target_height):
        line_chars = []
        for j in range(target_width):
            start_x = int(j * block_width)
            end_x = int((j + 1) * block_width)
            start_y = int(i * block_height)
            end_y = int((i + 1) * block_height)

            if end_x <= start_x:
                end_x = start_x + 1
            if end_y <= start_y:
                end_y = start_y + 1

            brightness_sum = 0.0
            count = 0
            for y in range(start_y, min(end_y, original_height)):
                for x in range(start_x, min(end_x, original_width)):
                    brightness_sum += char_to_brightness(padded_art[y][x], ascii_scale)
                    count += 1
            avg_brightness = brightness_sum / count if count > 0 else 0.5
            pos = int(round(avg_brightness * (len(ascii_scale) - 1)))
            if pos < 0:
                pos = 0
            if pos >= len(ascii_scale):
                pos = len(ascii_scale) - 1
            line_chars.append(ascii_scale[pos])
        new_art.append("".join(line_chars))
    return new_art

# -------------------------------------------------------------------
# تحديد مسار السكربت الرئيسي
# -------------------------------------------------------------------
script_dir = os.path.dirname(os.path.abspath(__file__))
print(f"[*] Crimson Eye main script running from path: {script_dir}")
print("-" * 40)

# -------------------------------------------------------------------
# دالة تشغيل السكربتات الخارجية
# -------------------------------------------------------------------
def run_external_script(script_rel_path, args_list):
    full_script_path = os.path.join(script_dir, script_rel_path)
    if not os.path.exists(full_script_path):
        print(f"\n[!] Fatal Error: Script '{script_rel_path}' not found at expected path '{full_script_path}'.")
        return

    command = [sys.executable, full_script_path]
    if args_list:
        command.extend(args_list)

    print(f"\n[*] --- Starting: {script_rel_path} ---")
    print(f"[*] Command: {shlex.join(command)}")
    print("-" * 40)
    try:
        process = subprocess.run(command, check=False)
        print("-" * 40)
        print(f"[*] --- Finished {script_rel_path} (Exit Code: {process.returncode}) ---")
    except FileNotFoundError:
        print(f"\n[!] Error: Command '{sys.executable}' not found. Ensure Python is installed and in PATH.")
    except KeyboardInterrupt:
        print(f"\n[!] {script_rel_path} interrupted by user (Ctrl+C).")
    except Exception as e:
        print(f"\n[!] An unexpected error occurred while trying to run {script_rel_path}: {e}")

# -------------------------------------------------------------------
# دوال استدعاء معطيات الأدوات المختلفة
# -------------------------------------------------------------------
def prompt_subscoutx_args():
    print("\n--- Settings for SubScoutX (Subdomain Enumeration) ---")
    args = []
    while True:
        target_type = input("Target type: single domain or list from file? (s/f): ").strip().lower()
        if target_type == 's':
            domain = input("Enter the target domain (e.g., example.com): ").strip()
            if domain:
                args.extend(['-d', domain])
                break
            else:
                print("[!] Input is mandatory.")
        elif target_type == 'f':
            list_path = input("Enter the path to the domains file: ").strip()
            if list_path:
                full_list_path = os.path.join(script_dir, list_path) if not os.path.isabs(list_path) else list_path
                if os.path.exists(full_list_path):
                    args.extend(['-l', list_path])
                    break
                else:
                    print(f"[!] Error: File '{list_path}' not found.")
            else:
                print("[!] Input is mandatory.")
        else:
            print("[!] Invalid option, please enter 's' or 'f'.")
    output_path = input("Enter path for the output file (optional, press Enter to skip): ").strip()
    if output_path:
        args.extend(['-o', output_path])
    default_config_rel_path = os.path.join("SubScoutX", "config.yaml")
    default_config_full_path = os.path.join(script_dir, default_config_rel_path)
    if os.path.exists(default_config_full_path):
        print(f"[*] Default config file found: '{default_config_rel_path}'. Adding '-c' argument automatically.")
        args.extend(['-c', default_config_rel_path])
    verbose = input("Enable verbose output? (y/n, default n): ").strip().lower()
    if verbose == 'y':
        args.append('-v')
    return args

def prompt_domain_pulse_args():
    print("\n--- Settings for DomainPulse (Status Code Validator) ---")
    args = []
    while True:
        domains_path = input("Enter the path to the domains file (mandatory): ").strip()
        if domains_path:
            full_domains_path = os.path.join(script_dir, domains_path) if not os.path.isabs(domains_path) else domains_path
            if os.path.exists(full_domains_path):
                args.extend(['-d', domains_path])
                break
            else:
                print(f"[!] Error: File '{domains_path}' not found.")
        else:
            print("[!] Input is mandatory.")
    output_path = input("Enter path for the output file (optional, press Enter to skip): ").strip()
    if output_path:
        args.extend(['-o', output_path])
    threads_str = input("Enter number of Threads (optional, default 5, press Enter for default): ").strip()
    if threads_str:
        try:
            threads = int(threads_str)
            if threads > 0:
                args.extend(['-t', str(threads)])
            else:
                print("[!] Warning: Threads must be greater than zero. Omitting -t argument.")
        except ValueError:
            print("[!] Warning: Invalid value for Threads. Omitting -t argument.")
    verbose = input("Enable verbose output? (y/n, default n): ").strip().lower()
    if verbose == 'y':
        args.append('-v')
    return args

def prompt_param_forge_args():
    print("\n--- Settings for ParamForge (Parameter Finder) ---")
    args = []
    while True:
        target_type = input("Target type: single domain or list from file? (s/f): ").strip().lower()
        if target_type == 's':
            domain = input("Enter the target domain (e.g., https://example.com): ").strip()
            if domain:
                args.extend(['-d', domain])
                break
            else:
                print("[!] Input is mandatory.")
        elif target_type == 'f':
            list_path = input("Enter the path to the domains file: ").strip()
            if list_path:
                full_list_path = os.path.join(script_dir, list_path) if not os.path.isabs(list_path) else list_path
                if os.path.exists(full_list_path):
                    args.extend(['-l', list_path])
                    break
                else:
                    print(f"[!] Error: File '{list_path}' not found.")
            else:
                print("[!] Input is mandatory.")
        else:
            print("[!] Invalid option, please enter 's' or 'f'.")
    while True:
        wordlist_path = input("Enter the path to the parameter wordlist file (mandatory): ").strip()
        if wordlist_path:
            full_wordlist_path = os.path.join(script_dir, wordlist_path) if not os.path.isabs(wordlist_path) else wordlist_path
            if os.path.exists(full_wordlist_path):
                args.extend(['-w', wordlist_path])
                break
            else:
                print(f"[!] Error: File '{wordlist_path}' not found.")
        else:
            print("[!] Input is mandatory.")
    output_path = input("Enter path for the output file (optional, press Enter to skip): ").strip()
    if output_path:
        args.extend(['-o', output_path])
    threads_str = input("Enter number of Threads (optional, default 10, press Enter for default): ").strip()
    if threads_str:
        try:
            threads = int(threads_str)
            if threads > 0:
                args.extend(['-t', str(threads)])
            else:
                print("[!] Warning: Threads must be greater than zero. Omitting -t argument.")
        except ValueError:
            print("[!] Warning: Invalid value for Threads. Omitting -t argument.")
    verbose = input("Enable verbose output? (y/n, default n): ").strip().lower()
    if verbose == 'y':
        args.append('-v')
    return args

def prompt_scanner_args():
    print("\n--- Settings for Scanner (Vulnerability Scanner) ---")
    args = []
    default_template_dir = os.path.join("scanner", "nuclei-templates")
    template_dir_input = input(f"Enter path to templates directory (press Enter for default '{default_template_dir}'): ").strip()
    template_dir = template_dir_input if template_dir_input else default_template_dir
    full_template_dir = os.path.join(script_dir, template_dir) if not os.path.isabs(template_dir) else template_dir
    if not os.path.isdir(full_template_dir):
        print(f"[!] Warning: Template directory '{template_dir}' might not exist or is not a directory.")
    args.extend(['-t', template_dir])
    while True:
        targets_str = input("Enter target(s) separated by spaces (e.g., http://a.com https://b.com) (mandatory): ").strip()
        if targets_str:
            targets_list = targets_str.split()
            args.append('-d')
            args.extend(targets_list)
            break
        else:
            print("[!] At least one target must be provided.")
    output_path = input("Enter path for the output file (optional, press Enter to skip): ").strip()
    if output_path:
        args.extend(['-o', output_path])
    formats = ['json', 'csv', 'html', 'text']
    format_input = input(f"Enter output format {formats} (optional, default text, press Enter for default): ").strip().lower()
    if format_input:
        if format_input in formats:
            args.extend(['-f', format_input])
        else:
            print(f"[!] Warning: Invalid format '{format_input}'. Omitting -f argument.")
    severity = input("Filter by severity (e.g., high,critical, optional, press Enter for all): ").strip()
    if severity:
        args.extend(['--severity', severity])
    tags = input("Filter by tags (e.g., sqli,rce, optional, press Enter for all): ").strip()
    if tags:
        args.extend(['--tags', tags])
    rate_limit_str = input("Enter rate-limit (optional, press Enter for default): ").strip()
    if rate_limit_str:
        try:
            rate = int(rate_limit_str)
            if rate > 0:
                args.extend(['-r', str(rate)])
            else:
                print("[!] Warning: Rate limit must be greater than zero. Omitting -r argument.")
        except ValueError:
            print("[!] Warning: Invalid value for rate limit. Omitting -r argument.")
    return args

# -------------------------------------------------------------------
# دالة عرض القائمة الرئيسية مع إعادة تحجيم art.txt بحيث تكون الرسمة على اليسار ومملوءة بالألوان
#
# تمت إزالة التوسيط بحيث تُطبع الرسمة على اليسار.
# كما قمنا بتعديل اللون ليصبح أحمر باستخدام ANSI code "\033[31m".
# -------------------------------------------------------------------
def display_menu():
    if sys.platform == "win32":
        os.system("")  # تهيئة دعم ANSI على Windows

    # هنا استخدم اللون الأحمر بدل اللون الأزرق:
    RED = "\033[31m"
    WHITE_BOLD = "\033[1;97m"
    RESET = "\033[0m"

    art_lines = []
    art_file_path = os.path.join(script_dir, "art.txt")
    try:
        with open(art_file_path, 'r', encoding='utf-8') as f:
            art_lines = f.read().splitlines()
        if not art_lines:
            print(f"[!] Warning: '{art_file_path}' is empty.")
    except FileNotFoundError:
        print(f"[!] Warning: 'art.txt' not found in script directory '{script_dir}'. Skipping art display.")
    except Exception as e:
        print(f"[!] Error reading 'art.txt': {e}")

    # الحصول على أبعاد الترمينال
    try:
        terminal_size = os.get_terminal_size()
        terminal_width = terminal_size.columns
        terminal_height = terminal_size.lines
    except OSError:
        terminal_width = 80
        terminal_height = 24

    margin = 4  # لتجنب ملامسة حدود الترمينال
    target_width = max(5, int(terminal_width * 0.5))
    target_height = max(5, int(terminal_height * 0.8))

    # إعادة تحجيم art.txt باستخدام طريقة البلوك لإنتاج رسم متناسب
    if art_lines:
        art_lines = resize_ascii_art_block(art_lines, target_width, target_height)

    # إعداد بيانات القائمة
    title = "C R I M S O N   E Y E"
    menu_items = [
        "1. SubScoutX (Subdomain Enumeration)",
        "2. DomainPulse (Status Validator)",
        "3. ParamForge (Parameter Finder)",
        "4. Scanner (Vulnerability Scanner)",
    ]
    exit_item = "0. Exit"
    padding = 4

    max_item_length = len(title)
    for item in menu_items:
        if len(item) > max_item_length:
            max_item_length = len(item)
    if len(exit_item) > max_item_length:
        max_item_length = len(exit_item)
    box_width = max_item_length + padding * 2

    print("\n")
    # لطباعة الرسمة على اليسار مع اللون الأحمر
    if art_lines:
        for line in art_lines:
            print(f"{RED}{line}{RESET}")
        print("\n")

    print(f"{RED}╔{'═' * box_width}╗{RESET}")
    print(f"{RED}║{WHITE_BOLD}{title.center(box_width)}{RESET}{RED}║{RESET}")
    print(f"{RED}╠{'═' * box_width}╣{RESET}")
    for item in menu_items:
        formatted_item = f"{' ' * padding}{item}{' ' * (box_width - len(item) - padding)}"
        print(f"{RED}║{WHITE_BOLD}{formatted_item}{RESET}{RED}║{RESET}")
    print(f"{RED}║{' ' * box_width}║{RESET}")
    formatted_exit = f"{' ' * padding}{exit_item}{' ' * (box_width - len(exit_item) - padding)}"
    print(f"{RED}║{WHITE_BOLD}{formatted_exit}{RESET}{RED}║{RESET}")
    print(f"{RED}╚{'═' * box_width}╝{RESET}")

# -------------------------------------------------------------------
# الدالة الرئيسية التي تدير القائمة وتشغيل الأدوات المطلوبة
# -------------------------------------------------------------------
def main():
    tool_map = {
        '1': ("SubScoutX/SubScoutX.py", prompt_subscoutx_args),
        '2': ("DomainPulse/DomainPulse.py", prompt_domain_pulse_args),
        '3': ("ParamForge/ParamForge.py", prompt_param_forge_args),
        '4': ("scanner/scanner.py", prompt_scanner_args),
    }

    while True:
        display_menu()
        choice = input(">> Select tool number to run (or 0 to exit): ").strip()

        if choice == '0':
            print("\n[*] Exiting... Goodbye!")
            break
        elif choice in tool_map:
            script_path, prompt_func = tool_map[choice]
            arguments = prompt_func()
            if arguments is not None:
                run_external_script(script_path, arguments)
            else:
                print("[!] Tool setup cancelled or an error occurred during setup.")
        else:
            print("\n[!] Invalid choice. Please enter a number from the menu.")

        print("\n" + "=" * 40)
        input("[*] Press Enter to return to the main menu...")
        print("=" * 40 + "\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[!] Main script interrupted by user (Ctrl+C). Goodbye!")
        sys.exit(0)