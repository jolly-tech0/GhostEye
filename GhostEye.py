#!/usr/bin/env python3
"""
GhostEye v2.0
Developer : Jolly
Instagram : @laukii.i
Information Gathering & Security Utility Toolkit for Termux
"""

import os
import sys
import json
import time
import socket
import hashlib
import base64
import ssl
import string
import secrets
import re
import datetime
import urllib.parse

# ---------- Optional third-party imports (graceful fallback) ----------
try:
    import requests
except ImportError:
    requests = None

try:
    import dns.resolver
    HAS_DNS = True
except ImportError:
    HAS_DNS = False

try:
    import whois as pywhois
    HAS_WHOIS = True
except ImportError:
    HAS_WHOIS = False

try:
    from colorama import init, Fore, Style
    init(autoreset=True)
    HAS_COLOR = True
except ImportError:
    HAS_COLOR = False
    class _Dummy:
        def __getattr__(self, name):
            return ""
    Fore = _Dummy()
    Style = _Dummy()

try:
    import qrcode
    HAS_QRCODE = True
except ImportError:
    HAS_QRCODE = False

try:
    from PIL import Image, ExifTags
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

try:
    from pyzbar.pyzbar import decode as qr_decode
    HAS_PYZBAR = True
except ImportError:
    HAS_PYZBAR = False


CONFIG_FILE = os.path.join(os.path.expanduser("~"), ".ghosteye_config.json")
HISTORY_FILE = os.path.join(os.path.expanduser("~"), ".ghosteye_history.json")
REPORT_DIR = os.path.join(os.path.expanduser("~"), "GhostEye_Reports")
DEFAULT_CONFIG = {"theme": "dark", "autosave": True}


def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return DEFAULT_CONFIG.copy()
    return DEFAULT_CONFIG.copy()


def save_config(cfg):
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2)


CONFIG = load_config()


def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return []
    return []


def add_history(entry):
    hist = load_history()
    entry["time"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    hist.append(entry)
    with open(HISTORY_FILE, "w") as f:
        json.dump(hist, f, indent=2)
    if CONFIG.get("autosave"):
        save_report(entry, "json", silent=True)


# ---------------- UI helpers ----------------

def clear():
    os.system("clear" if os.name != "nt" else "cls")


def banner():
    clear()
    c1 = Fore.CYAN if HAS_COLOR else ""
    c2 = Fore.GREEN if HAS_COLOR else ""
    c3 = Fore.MAGENTA if HAS_COLOR else ""
    reset = Style.RESET_ALL if HAS_COLOR else ""
    art = r"""
   ______ __              __ ______
  / ____// /_  ____  ____ / //_  __/
 / / __ / __ \/ __ \/ ___/ /  / /
/ /_/ // / / / /_/ (__  ) /  / /
\____//_/ /_/\____/____/_/  /_/
        G h o s t E y e  v2.0
"""
    print(c1 + art + reset)
    print(c2 + "  Developer : Jolly" + reset)
    print(c2 + "  Instagram : @laukii.i" + reset)
    print(c3 + "  " + "-" * 40 + reset)


def loading_animation(text="Loading", duration=1.2):
    frames = ["|", "/", "-", "\\"]
    end_time = time.time() + duration
    i = 0
    while time.time() < end_time:
        sys.stdout.write(f"\r{text}... {frames[i % 4]}")
        sys.stdout.flush()
        time.sleep(0.1)
        i += 1
    sys.stdout.write(f"\r{text}... done!\n")


def progress_bar(total=30, delay=0.02):
    for i in range(total + 1):
        pct = int((i / total) * 100)
        bar = "#" * i + "-" * (total - i)
        sys.stdout.write(f"\r[{bar}] {pct}%")
        sys.stdout.flush()
        time.sleep(delay)
    print()


def pause():
    input("\nPress Enter to continue...")


def need(flag, name):
    if not flag:
        print(Fore.RED + f"[!] '{name}' module not installed. Run: pip install {name}" + Style.RESET_ALL)
        pause()
        return False
    return True


def about():
    clear()
    banner()
    print(Fore.CYAN + "\nGhostEye v2.0" + Style.RESET_ALL)
    print("All-in-one information gathering & security utility toolkit.")
    print("\nDeveloper : Jolly")
    print("Instagram : @laukii.i")
    print("Version   : GhostEye v2.0")
    pause()


# ---------------- Information Gathering ----------------

def dns_lookup():
    domain = input("Enter domain (e.g. example.com): ").strip()
    if not domain or not need(HAS_DNS, "dnspython"):
        return
    records = ["A", "AAAA", "MX", "TXT", "NS", "CNAME"]
    result = {}
    resolver = dns.resolver.Resolver()
    for rtype in records:
        try:
            answers = resolver.resolve(domain, rtype)
            result[rtype] = [str(r) for r in answers]
        except Exception:
            result[rtype] = []
    print(Fore.YELLOW + f"\nDNS Records for {domain}:" + Style.RESET_ALL)
    for rtype, vals in result.items():
        print(f"  {rtype}: {', '.join(vals) if vals else 'No record found'}")
    add_history({"tool": "DNS Lookup", "target": domain, "result": result})
    pause()


def whois_lookup():
    domain = input("Enter domain: ").strip()
    if not domain or not need(HAS_WHOIS, "python-whois"):
        return
    try:
        loading_animation("Fetching WHOIS data")
        w = pywhois.whois(domain)
        info = {
            "domain_name": str(w.domain_name),
            "registrar": str(w.registrar),
            "creation_date": str(w.creation_date),
            "expiration_date": str(w.expiration_date),
            "name_servers": str(w.name_servers),
            "status": str(w.status),
            "emails": str(w.emails),
        }
        print(Fore.YELLOW + f"\nWHOIS info for {domain}:" + Style.RESET_ALL)
        for k, v in info.items():
            print(f"  {k}: {v}")
        add_history({"tool": "WHOIS Lookup", "target": domain, "result": info})
    except Exception as e:
        print(Fore.RED + f"Error: {e}" + Style.RESET_ALL)
    pause()


def ip_info():
    ip = input("Enter IP address (blank = your public IP): ").strip()
    if not need(bool(requests), "requests"):
        return
    try:
        url = f"http://ip-api.com/json/{ip}" if ip else "http://ip-api.com/json/"
        r = requests.get(url, timeout=8)
        data = r.json()
        print(Fore.YELLOW + "\nIP Information:" + Style.RESET_ALL)
        for k, v in data.items():
            print(f"  {k}: {v}")
        add_history({"tool": "IP Info", "target": ip or "self", "result": data})
    except Exception as e:
        print(Fore.RED + f"Error: {e}" + Style.RESET_ALL)
    pause()


def ssl_checker():
    domain = input("Enter domain (without https://): ").strip()
    if not domain:
        return
    try:
        ctx = ssl.create_default_context()
        with socket.create_connection((domain, 443), timeout=8) as sock:
            with ctx.wrap_socket(sock, server_hostname=domain) as ssock:
                cert = ssock.getpeercert()
        issuer = dict(x[0] for x in cert.get("issuer", []))
        subject = dict(x[0] for x in cert.get("subject", []))
        not_before = cert.get("notBefore")
        not_after = cert.get("notAfter")
        expire_dt = datetime.datetime.strptime(not_after, "%b %d %H:%M:%S %Y %Z")
        days_left = (expire_dt - datetime.datetime.utcnow()).days
        print(Fore.YELLOW + f"\nSSL Certificate for {domain}:" + Style.RESET_ALL)
        print(f"  Issuer     : {issuer.get('organizationName', issuer)}")
        print(f"  Subject    : {subject.get('commonName', subject)}")
        print(f"  Valid From : {not_before}")
        print(f"  Valid Until: {not_after}")
        print(f"  Days Left  : {days_left}")
        add_history({"tool": "SSL Checker", "target": domain,
                      "result": {"issuer": issuer, "subject": subject, "expires": not_after, "days_left": days_left}})
    except Exception as e:
        print(Fore.RED + f"Error: {e}" + Style.RESET_ALL)
    pause()


def reverse_dns():
    ip = input("Enter IP address: ").strip()
    try:
        host = socket.gethostbyaddr(ip)
        print(Fore.YELLOW + f"\nReverse DNS for {ip}:" + Style.RESET_ALL)
        print(f"  Hostname: {host[0]}")
        print(f"  Aliases : {host[1]}")
        add_history({"tool": "Reverse DNS", "target": ip, "result": host[0]})
    except Exception as e:
        print(Fore.RED + f"Error: {e}" + Style.RESET_ALL)
    pause()


def _get_url():
    url = input("Enter URL (with/without http): ").strip()
    if url and not url.startswith("http"):
        url = "https://" + url
    return url


def website_status():
    url = _get_url()
    if not url or not need(bool(requests), "requests"):
        return
    try:
        start = time.time()
        r = requests.get(url, timeout=10)
        elapsed = round((time.time() - start) * 1000, 2)
        print(Fore.YELLOW + f"\nWebsite Status for {url}:" + Style.RESET_ALL)
        print(f"  Status Code: {r.status_code}")
        print(f"  Response   : {elapsed} ms")
        print(f"  Server     : {r.headers.get('Server', 'Unknown')}")
        add_history({"tool": "Website Status", "target": url, "result": {"status": r.status_code, "ms": elapsed}})
    except Exception as e:
        print(Fore.RED + f"Error: {e}" + Style.RESET_ALL)
    pause()


# ---------------- Hash & Encoding ----------------

def hash_generator(algo_name, func):
    text = input("Enter text to hash: ")
    h = func(text.encode()).hexdigest()
    print(Fore.GREEN + f"\n{algo_name}: {h}" + Style.RESET_ALL)
    add_history({"tool": f"{algo_name} Generator", "target": text[:50], "result": h})
    pause()

def md5_generator(): hash_generator("MD5", hashlib.md5)
def sha1_generator(): hash_generator("SHA1", hashlib.sha1)
def sha256_generator(): hash_generator("SHA256", hashlib.sha256)
def sha512_generator(): hash_generator("SHA512", hashlib.sha512)


def hash_verifier():
    text = input("Enter original text: ")
    given_hash = input("Enter hash to verify: ").strip().lower()
    algos = {"md5": hashlib.md5, "sha1": hashlib.sha1, "sha256": hashlib.sha256, "sha512": hashlib.sha512}
    matched = None
    for name, func in algos.items():
        if func(text.encode()).hexdigest() == given_hash:
            matched = name
            break
    if matched:
        print(Fore.GREEN + f"\n[OK] Match found! Algorithm: {matched.upper()}" + Style.RESET_ALL)
    else:
        print(Fore.RED + "\n[X] No match found." + Style.RESET_ALL)
    pause()


def base64_encode():
    text = input("Enter text: ")
    print(Fore.GREEN + f"\nEncoded: {base64.b64encode(text.encode()).decode()}" + Style.RESET_ALL)
    pause()

def base64_decode():
    text = input("Enter base64 string: ")
    try:
        print(Fore.GREEN + f"\nDecoded: {base64.b64decode(text).decode(errors='replace')}" + Style.RESET_ALL)
    except Exception as e:
        print(Fore.RED + f"Error: {e}" + Style.RESET_ALL)
    pause()

def url_encode():
    text = input("Enter text/URL: ")
    print(Fore.GREEN + f"\nEncoded: {urllib.parse.quote(text)}" + Style.RESET_ALL)
    pause()

def url_decode():
    text = input("Enter encoded URL: ")
    print(Fore.GREEN + f"\nDecoded: {urllib.parse.unquote(text)}" + Style.RESET_ALL)
    pause()


# ---------------- Password Tools ----------------

def password_strength_checker():
    pwd = input("Enter password to check: ")
    length = len(pwd)
    score = 0
    tips = []
    if length >= 8: score += 1
    else: tips.append("Use at least 8 characters")
    if length >= 12: score += 1
    if re.search(r"[a-z]", pwd): score += 1
    else: tips.append("Add lowercase letters")
    if re.search(r"[A-Z]", pwd): score += 1
    else: tips.append("Add uppercase letters")
    if re.search(r"[0-9]", pwd): score += 1
    else: tips.append("Add numbers")
    if re.search(r"[^a-zA-Z0-9]", pwd): score += 1
    else: tips.append("Add special characters")
    labels = ["Very Weak", "Weak", "Fair", "Good", "Strong", "Very Strong"]
    label = labels[min(score, 5)]
    color = Fore.RED if score <= 2 else (Fore.YELLOW if score <= 4 else Fore.GREEN)
    print(color + f"\nPassword Strength: {label} ({score}/6)" + Style.RESET_ALL)
    if tips:
        print("Suggestions:")
        for t in tips:
            print(f"  - {t}")
    pause()


def random_password_generator():
    try:
        length = int(input("Password length (default 16): ") or 16)
    except ValueError:
        length = 16
    use_symbols = input("Include symbols? (y/n, default y): ").strip().lower() != "n"
    chars = string.ascii_letters + string.digits
    if use_symbols:
        chars += "!@#$%^&*()-_=+[]{}"
    pwd = "".join(secrets.choice(chars) for _ in range(length))
    print(Fore.GREEN + f"\nGenerated Password: {pwd}" + Style.RESET_ALL)
    pause()


WORDLIST = [
    "shadow","river","stone","tiger","falcon","cloud","ember","frost","ghost","harbor",
    "island","jungle","kernel","lantern","meadow","nectar","orbit","phoenix","quartz","raven",
    "silver","thunder","umbra","velvet","willow","xenon","yonder","zenith","anchor","breeze",
    "canyon","desert","echo","forest","galaxy","horizon","ivory","jasper","knight","lunar",
    "mirror","nomad","oasis","pebble","quest","ridge","summit","twilight","utopia","voyage"
]

def passphrase_generator():
    try:
        n = int(input("Number of words (default 4): ") or 4)
    except ValueError:
        n = 4
    words = [secrets.choice(WORDLIST) for _ in range(n)]
    sep = input("Separator (default '-'): ") or "-"
    print(Fore.GREEN + f"\nGenerated Passphrase: {sep.join(words)}" + Style.RESET_ALL)
    pause()


# ---------------- File Analysis ----------------

def file_hash_generator():
    path = input("Enter file path: ").strip()
    if not os.path.isfile(path):
        print(Fore.RED + "File not found." + Style.RESET_ALL); pause(); return
    algos = {"MD5": hashlib.md5(), "SHA1": hashlib.sha1(), "SHA256": hashlib.sha256(), "SHA512": hashlib.sha512()}
    with open(path, "rb") as f:
        data = f.read()
    print(Fore.YELLOW + f"\nHashes for {path}:" + Style.RESET_ALL)
    result = {}
    for name, h in algos.items():
        h.update(data)
        result[name] = h.hexdigest()
        print(f"  {name}: {h.hexdigest()}")
    add_history({"tool": "File Hash Generator", "target": path, "result": result})
    pause()


def file_integrity_checker():
    path = input("Enter file path: ").strip()
    expected = input("Enter expected hash: ").strip().lower()
    if not os.path.isfile(path):
        print(Fore.RED + "File not found." + Style.RESET_ALL); pause(); return
    with open(path, "rb") as f:
        data = f.read()
    algos = {"md5": hashlib.md5, "sha1": hashlib.sha1, "sha256": hashlib.sha256, "sha512": hashlib.sha512}
    matched = None
    for name, func in algos.items():
        if func(data).hexdigest() == expected:
            matched = name; break
    if matched:
        print(Fore.GREEN + f"\n[OK] File integrity verified! Algorithm: {matched.upper()}" + Style.RESET_ALL)
    else:
        print(Fore.RED + "\n[X] Integrity check failed / hash mismatch." + Style.RESET_ALL)
    pause()


def file_metadata_viewer():
    path = input("Enter file path: ").strip()
    if not os.path.exists(path):
        print(Fore.RED + "File not found." + Style.RESET_ALL); pause(); return
    st = os.stat(path)
    print(Fore.YELLOW + f"\nMetadata for {path}:" + Style.RESET_ALL)
    print(f"  Size       : {st.st_size} bytes")
    print(f"  Created    : {datetime.datetime.fromtimestamp(st.st_ctime)}")
    print(f"  Modified   : {datetime.datetime.fromtimestamp(st.st_mtime)}")
    print(f"  Accessed   : {datetime.datetime.fromtimestamp(st.st_atime)}")
    print(f"  Permissions: {oct(st.st_mode)[-3:]}")
    pause()


def exif_viewer():
    path = input("Enter image path: ").strip()
    if not os.path.isfile(path):
        print(Fore.RED + "File not found." + Style.RESET_ALL); pause(); return
    if not need(HAS_PIL, "pillow"):
        return
    try:
        img = Image.open(path)
        exif_data = img.getexif()
        print(Fore.YELLOW + f"\nEXIF data for {path}:" + Style.RESET_ALL)
        if not exif_data:
            print("  No EXIF data found.")
        else:
            for tag_id, value in exif_data.items():
                tag = ExifTags.TAGS.get(tag_id, tag_id)
                print(f"  {tag}: {value}")
    except Exception as e:
        print(Fore.RED + f"Error: {e}" + Style.RESET_ALL)
    pause()


# ---------------- Website Analysis ----------------

def http_header_analyzer():
    url = _get_url()
    if not url or not need(bool(requests), "requests"):
        return
    try:
        r = requests.get(url, timeout=10)
        print(Fore.YELLOW + f"\nHTTP Headers for {url}:" + Style.RESET_ALL)
        for k, v in r.headers.items():
            print(f"  {k}: {v}")
        add_history({"tool": "HTTP Header Analyzer", "target": url, "result": dict(r.headers)})
    except Exception as e:
        print(Fore.RED + f"Error: {e}" + Style.RESET_ALL)
    pause()


def security_header_report():
    url = _get_url()
    if not url or not need(bool(requests), "requests"):
        return
    checks = ["Strict-Transport-Security", "Content-Security-Policy", "X-Frame-Options",
              "X-Content-Type-Options", "Referrer-Policy", "Permissions-Policy", "X-XSS-Protection"]
    try:
        r = requests.get(url, timeout=10)
        print(Fore.YELLOW + f"\nSecurity Header Report for {url}:" + Style.RESET_ALL)
        score = 0
        result = {}
        for h in checks:
            present = h in r.headers
            result[h] = r.headers.get(h, "Missing")
            status = (Fore.GREEN + "Present" + Style.RESET_ALL) if present else (Fore.RED + "Missing" + Style.RESET_ALL)
            print(f"  {h:30s}: {status}")
            if present:
                score += 1
        print(Fore.CYAN + f"\n  Security Score: {score}/{len(checks)}" + Style.RESET_ALL)
        add_history({"tool": "Security Header Report", "target": url, "result": result, "score": f"{score}/{len(checks)}"})
    except Exception as e:
        print(Fore.RED + f"Error: {e}" + Style.RESET_ALL)
    pause()


def redirect_checker():
    url = _get_url()
    if not url or not need(bool(requests), "requests"):
        return
    try:
        r = requests.get(url, timeout=10, allow_redirects=True)
        print(Fore.YELLOW + f"\nRedirect Chain for {url}:" + Style.RESET_ALL)
        chain = []
        for i, h in enumerate(r.history, 1):
            print(f"  {i}. {h.status_code} -> {h.url}")
            chain.append({"step": i, "status": h.status_code, "url": h.url})
        print(f"  Final -> {r.status_code} -> {r.url}")
        chain.append({"step": "final", "status": r.status_code, "url": r.url})
        add_history({"tool": "Redirect Checker", "target": url, "result": chain})
    except Exception as e:
        print(Fore.RED + f"Error: {e}" + Style.RESET_ALL)
    pause()


def cookie_inspector():
    url = _get_url()
    if not url or not need(bool(requests), "requests"):
        return
    try:
        r = requests.get(url, timeout=10)
        print(Fore.YELLOW + f"\nCookies set by {url}:" + Style.RESET_ALL)
        result = []
        if not r.cookies:
            print("  No cookies found.")
        for c in r.cookies:
            info = {"name": c.name, "value": c.value, "domain": c.domain, "path": c.path,
                     "expires": c.expires, "secure": c.secure}
            result.append(info)
            print(f"  {c.name} = {c.value}")
            print(f"    domain={c.domain} path={c.path} secure={c.secure} expires={c.expires}")
        add_history({"tool": "Cookie Inspector", "target": url, "result": result})
    except Exception as e:
        print(Fore.RED + f"Error: {e}" + Style.RESET_ALL)
    pause()


def robots_checker():
    domain = input("Enter domain (e.g. example.com): ").strip()
    if not domain or not need(bool(requests), "requests"):
        return
    url = f"https://{domain}/robots.txt"
    try:
        r = requests.get(url, timeout=10)
        print(Fore.YELLOW + f"\nrobots.txt for {domain}:" + Style.RESET_ALL)
        print(r.text[:3000] if r.status_code == 200 else f"  Not found (status {r.status_code})")
        add_history({"tool": "robots.txt Checker", "target": domain, "result": {"status": r.status_code}})
    except Exception as e:
        print(Fore.RED + f"Error: {e}" + Style.RESET_ALL)
    pause()


def sitemap_checker():
    domain = input("Enter domain (e.g. example.com): ").strip()
    if not domain or not need(bool(requests), "requests"):
        return
    url = f"https://{domain}/sitemap.xml"
    try:
        r = requests.get(url, timeout=10)
        print(Fore.YELLOW + f"\nsitemap.xml for {domain}:" + Style.RESET_ALL)
        print(r.text[:3000] if r.status_code == 200 else f"  Not found (status {r.status_code})")
        add_history({"tool": "sitemap.xml Checker", "target": domain, "result": {"status": r.status_code}})
    except Exception as e:
        print(Fore.RED + f"Error: {e}" + Style.RESET_ALL)
    pause()


# ---------------- Reports ----------------

def save_report(data, fmt="json", silent=False):
    os.makedirs(REPORT_DIR, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    fname = os.path.join(REPORT_DIR, f"report_{ts}.{fmt}")
    try:
        if fmt == "json":
            with open(fname, "w") as f:
                json.dump(data, f, indent=2)
        elif fmt == "txt":
            with open(fname, "w") as f:
                if isinstance(data, list):
                    for item in data:
                        f.write(json.dumps(item, indent=2) + "\n")
                else:
                    for k, v in data.items():
                        f.write(f"{k}: {v}\n")
        elif fmt == "html":
            with open(fname, "w") as f:
                f.write("<html><body><h2>GhostEye Report</h2><pre>")
                f.write(json.dumps(data, indent=2))
                f.write("</pre></body></html>")
        if not silent:
            print(Fore.GREEN + f"Report saved: {fname}" + Style.RESET_ALL)
    except Exception as e:
        if not silent:
            print(Fore.RED + f"Error saving report: {e}" + Style.RESET_ALL)


def report_menu():
    hist = load_history()
    if not hist:
        print(Fore.RED + "No scan history yet." + Style.RESET_ALL); pause(); return
    print("1. Export as HTML\n2. Export as TXT\n3. Export as JSON\n4. View Scan History\n0. Back")
    ch = input("Choose: ").strip()
    if ch == "1": save_report(hist, "html")
    elif ch == "2": save_report(hist, "txt")
    elif ch == "3": save_report(hist, "json")
    elif ch == "4":
        for i, h in enumerate(hist, 1):
            print(f"{i}. [{h.get('time')}] {h.get('tool')} -> {h.get('target')}")
    pause()


# ---------------- Utilities ----------------

def public_ip_finder():
    if not need(bool(requests), "requests"):
        return
    try:
        r = requests.get("https://api.ipify.org?format=json", timeout=8)
        ip = r.json().get("ip")
        print(Fore.GREEN + f"\nPublic IP: {ip}" + Style.RESET_ALL)
        add_history({"tool": "Public IP Finder", "target": "self", "result": ip})
    except Exception as e:
        print(Fore.RED + f"Error: {e}" + Style.RESET_ALL)
    pause()


def local_ip_finder():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        print(Fore.GREEN + f"\nLocal IP: {ip}" + Style.RESET_ALL)
    except Exception as e:
        print(Fore.RED + f"Error: {e}" + Style.RESET_ALL)
    pause()


def port_checker():
    print(Fore.RED + "\n[!] Only check ports on hosts you own or are explicitly authorized to test." + Style.RESET_ALL)
    host = input("Enter host (IP/domain): ").strip()
    confirm = input(f"Confirm you are authorized to test '{host}'? (yes/no): ").strip().lower()
    if confirm != "yes":
        print("Cancelled."); pause(); return
    try:
        port = int(input("Enter port number: ").strip())
    except ValueError:
        print(Fore.RED + "Invalid port." + Style.RESET_ALL); pause(); return
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        result = sock.connect_ex((host, port))
        state = "OPEN" if result == 0 else "CLOSED/FILTERED"
        color = Fore.GREEN if result == 0 else Fore.RED
        print(color + f"\nPort {port} on {host}: {state}" + Style.RESET_ALL)
        sock.close()
        add_history({"tool": "Port Availability Checker", "target": f"{host}:{port}", "result": state})
    except Exception as e:
        print(Fore.RED + f"Error: {e}" + Style.RESET_ALL)
    pause()


def timestamp_generator():
    now = datetime.datetime.now()
    utc_now = datetime.datetime.utcnow()
    print(Fore.YELLOW + "\nCurrent Timestamps:" + Style.RESET_ALL)
    print(f"  Local Time : {now.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  UTC Time   : {utc_now.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Epoch      : {int(time.time())}")
    conv = input("\nConvert an epoch timestamp? (number or blank): ").strip()
    if conv:
        try:
            dt = datetime.datetime.fromtimestamp(int(conv))
            print(f"  {conv} -> {dt.strftime('%Y-%m-%d %H:%M:%S')}")
        except Exception as e:
            print(Fore.RED + f"Error: {e}" + Style.RESET_ALL)
    pause()


def qr_generator():
    if not need(HAS_QRCODE, "qrcode[pil]"):
        return
    data = input("Enter text/URL to encode: ").strip()
    fname = input("Output filename (default qr.png): ").strip() or "qr.png"
    try:
        img = qrcode.make(data)
        img.save(fname)
        print(Fore.GREEN + f"\nQR code saved as {fname}" + Style.RESET_ALL)
    except Exception as e:
        print(Fore.RED + f"Error: {e}" + Style.RESET_ALL)
    pause()


def qr_reader():
    path = input("Enter QR image path: ").strip()
    if not os.path.isfile(path):
        print(Fore.RED + "File not found." + Style.RESET_ALL); pause(); return
    decoded_text = None
    try:
        import cv2
        img = cv2.imread(path)
        detector = cv2.QRCodeDetector()
        data, points, _ = detector.detectAndDecode(img)
        if data:
            decoded_text = data
    except Exception:
        pass
    if not decoded_text and HAS_PYZBAR and HAS_PIL:
        try:
            img = Image.open(path)
            results = qr_decode(img)
            if results:
                decoded_text = results[0].data.decode()
        except Exception:
            pass
    if decoded_text:
        print(Fore.GREEN + f"\nDecoded Data: {decoded_text}" + Style.RESET_ALL)
    else:
        print(Fore.RED + "\nCould not decode. Install opencv-python-headless or pyzbar+pillow." + Style.RESET_ALL)
    pause()


def internet_speed_check():
    try:
        import speedtest
    except ImportError:
        print(Fore.RED + "[!] 'speedtest-cli' not installed. Run: pip install speedtest-cli" + Style.RESET_ALL)
        pause(); return
    try:
        loading_animation("Testing internet speed (may take a while)")
        st = speedtest.Speedtest()
        st.get_best_server()
        down = st.download() / 1_000_000
        up = st.upload() / 1_000_000
        print(Fore.GREEN + "\nInternet Speed Test Results:" + Style.RESET_ALL)
        print(f"  Download: {down:.2f} Mbps")
        print(f"  Upload  : {up:.2f} Mbps")
        print(f"  Ping    : {st.results.ping:.2f} ms")
    except Exception as e:
        print(Fore.RED + f"Error: {e}" + Style.RESET_ALL)
    pause()


# ---------------- Settings ----------------

def settings_menu():
    while True:
        clear()
        print(Fore.CYAN + "== Settings ==" + Style.RESET_ALL)
        print(f"1. Theme: {CONFIG.get('theme')}")
        print(f"2. Auto Save Reports: {CONFIG.get('autosave')}")
        print("3. Update Checker")
        print("4. About")
        print("0. Back")
        ch = input("Choose: ").strip()
        if ch == "1":
            CONFIG["theme"] = "light" if CONFIG.get("theme") == "dark" else "dark"
            save_config(CONFIG)
        elif ch == "2":
            CONFIG["autosave"] = not CONFIG.get("autosave", True)
            save_config(CONFIG)
        elif ch == "3":
            print("You are running GhostEye v2.0 (latest known version).")
            pause()
        elif ch == "4":
            about()
        elif ch == "0":
            break


# ---------------- Menu system ----------------

MENUS = {
    "1": ("Information Gathering", [
        ("DNS Lookup", dns_lookup),
        ("WHOIS Lookup", whois_lookup),
        ("IP Information", ip_info),
        ("SSL Certificate Checker", ssl_checker),
        ("Website Status Checker", website_status),
        ("Reverse DNS Lookup", reverse_dns),
    ]),
    "2": ("Hash & Encoding", [
        ("MD5 Generator", md5_generator),
        ("SHA1 Generator", sha1_generator),
        ("SHA256 Generator", sha256_generator),
        ("SHA512 Generator", sha512_generator),
        ("Hash Verifier", hash_verifier),
        ("Base64 Encode", base64_encode),
        ("Base64 Decode", base64_decode),
        ("URL Encode", url_encode),
        ("URL Decode", url_decode),
    ]),
    "3": ("Password Tools", [
        ("Password Strength Checker", password_strength_checker),
        ("Random Password Generator", random_password_generator),
        ("Passphrase Generator", passphrase_generator),
    ]),
    "4": ("File Analysis", [
        ("File Hash Generator", file_hash_generator),
        ("File Integrity Checker", file_integrity_checker),
        ("File Metadata Viewer", file_metadata_viewer),
        ("EXIF Metadata Viewer", exif_viewer),
    ]),
    "5": ("Website Analysis", [
        ("HTTP Header Analyzer", http_header_analyzer),
        ("robots.txt Checker", robots_checker),
        ("sitemap.xml Checker", sitemap_checker),
        ("Redirect Checker", redirect_checker),
        ("Security Header Report", security_header_report),
        ("Cookie Inspector", cookie_inspector),
    ]),
    "6": ("Reports", [
        ("Generate / View Reports", report_menu),
    ]),
    "7": ("Utilities", [
        ("Internet Speed Check", internet_speed_check),
        ("Public IP Finder", public_ip_finder),
        ("Local IP Finder", local_ip_finder),
        ("Port Availability Checker", port_checker),
        ("Timestamp Generator", timestamp_generator),
        ("QR Code Generator", qr_generator),
        ("QR Code Reader", qr_reader),
    ]),
    "8": ("Settings", [
        ("Open Settings", settings_menu),
    ]),
}


def show_category(key):
    title, items = MENUS[key]
    while True:
        clear()
        banner()
        print(Fore.CYAN + f"\n== {title} ==" + Style.RESET_ALL)
        for i, (name, _) in enumerate(items, 1):
            print(f"  {i}. {name}")
        print("  0. Back to Main Menu")
        choice = input("\nSelect option: ").strip()
        if choice == "0":
            break
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(items):
                items[idx][1]()
            else:
                print(Fore.RED + "Invalid choice." + Style.RESET_ALL); time.sleep(1)
        except ValueError:
            print(Fore.RED + "Invalid input." + Style.RESET_ALL); time.sleep(1)


def main_menu():
    while True:
        clear()
        banner()
        print(Fore.CYAN + "\nMain Menu:" + Style.RESET_ALL)
        for key, (title, _) in MENUS.items():
            print(f"  {key}. {title}")
        print("  9. About")
        print("  0. Exit")
        choice = input("\nSelect category: ").strip()
        if choice == "0":
            print(Fore.MAGENTA + "\nThanks for using GhostEye v2.0. Goodbye!" + Style.RESET_ALL)
            sys.exit(0)
        elif choice == "9":
            about()
        elif choice in MENUS:
            show_category(choice)
        else:
            print(Fore.RED + "Invalid choice." + Style.RESET_ALL); time.sleep(1)


if __name__ == "__main__":
    try:
        os.makedirs(REPORT_DIR, exist_ok=True)
        main_menu()
    except KeyboardInterrupt:
        print(Fore.MAGENTA + "\n\nExiting GhostEye. Bye!" + Style.RESET_ALL)
        sys.exit(0)
