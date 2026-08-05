#!/usr/bin/env python3
"""
GhostEye v2.1 - Modular Python CLI Security Toolkit
By Jolly (@laukii.i)
Designed for Termux / Linux environments.
"""

import os
import sys
import socket
import ssl
import json
import time
import datetime
import hashlib
import base64
import urllib.parse
import string
import secrets
import subprocess
import importlib.util

---------------- Optional dependency handling ----------------

try:
import requests
except ImportError:
requests = None

try:
from colorama import Fore, Style, init as colorama_init
colorama_init(autoreset=True)
HAS_COLOR = True
except ImportError:
HAS_COLOR = False
class _Dummy:
def getattr(self, name):
return ""
Fore = _Dummy()
Style = _Dummy()

try:
import qrcode
HAS_QRCODE = True
except ImportError:
HAS_QRCODE = False

try:
from PIL import Image
from PIL.ExifTags import TAGS
HAS_PIL = True
except ImportError:
HAS_PIL = False

try:
from pyzbar.pyzbar import decode as qr_decode
HAS_PYZBAR = True
except ImportError:
HAS_PYZBAR = False

---------------- Constants ----------------

VERSION = "2.1"
HOME_DIR = os.path.expanduser("~")
BASE_DIR = os.path.join(HOME_DIR, ".ghosteye")
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
HISTORY_FILE = os.path.join(BASE_DIR, "history.json")
REPORT_DIR = os.path.join(BASE_DIR, "reports")
PLUGIN_DIR = os.path.join(BASE_DIR, "plugins")

DEFAULT_CONFIG = {
"theme": "dark",
"autosave": True,
"version": VERSION,
}

---------------- Config ----------------

def ensure_dirs():
for d in (BASE_DIR, REPORT_DIR, PLUGIN_DIR):
os.makedirs(d, exist_ok=True)

def load_config():
ensure_dirs()
if not os.path.isfile(CONFIG_FILE):
save_config(DEFAULT_CONFIG)
return dict(DEFAULT_CONFIG)
try:
with open(CONFIG_FILE, "r") as f:
cfg = json.load(f)
merged = dict(DEFAULT_CONFIG)
merged.update(cfg)
return merged
except Exception:
return dict(DEFAULT_CONFIG)

def save_config(cfg):
ensure_dirs()
try:
with open(CONFIG_FILE, "w") as f:
json.dump(cfg, f, indent=2)
except Exception:
pass

CONFIG = load_config()

---------------- Theme system ----------------

def theme_colors():
"""Return a dict of semantic colors depending on active theme."""
if CONFIG.get("theme") == "light":
return {
"title": Fore.BLUE,
"ok": Fore.GREEN,
"warn": Fore.MAGENTA,
"err": Fore.RED,
"info": Fore.CYAN,
"reset": Style.RESET_ALL,
}
return {
"title": Fore.CYAN,
"ok": Fore.GREEN,
"warn": Fore.YELLOW,
"err": Fore.RED,
"info": Fore.YELLOW,
"reset": Style.RESET_ALL,
}

---------------- Basic helpers ----------------

def clear():
os.system("cls" if os.name == "nt" else "clear")

def pause():
input("\nPress Enter to continue...")

def need(condition, package_name):
if not condition:
c = theme_colors()
print(c["err"] + f"[!] Missing dependency: '{package_name}'. Install with: pip install {package_name}" + c["reset"])
pause()
return False
return True

def loading_animation(message="Working", duration=1.2):
c = theme_colors()
frames = ["|", "/", "-", "\"]
steps = int(duration / 0.1)
for i in range(steps):
sys.stdout.write(f"\r{c['info']}{message}... {frames[i % len(frames)]}{c['reset']}")
sys.stdout.flush()
time.sleep(0.1)
sys.stdout.write("\r" + " " * (len(message) + 15) + "\r")

def banner():
c = theme_colors()
print(c["title"] + r"""


---

/ | |   ___  | || _|   _  ___
| |  | ' \ / _ / __| __|  || | | |/ _ \
| || | | | | () _ \ || || || |  /
_|| ||_/|/_|______, |_|
|_/
""" + c["reset"])
print(c["info"] + f"        GhostEye v{VERSION} - by Jolly (@laukii.i)" + c["reset"])

def about():
c = theme_colors()
clear()
banner()
print(c["title"] + "\n== About GhostEye ==" + c["reset"])
print(f"Version     : {VERSION}")
print("Author      : Jolly (@laukii.i)")
print("Description : Modular Python CLI security & OSINT toolkit")
print("Platform    : Termux / Linux")
print("License     : Personal / Educational use")
pause()

---------------- History ----------------

def load_history():
ensure_dirs()
if not os.path.isfile(HISTORY_FILE):
return []
try:
with open(HISTORY_FILE, "r") as f:
return json.load(f)
except Exception:
return []

def save_history(hist):
ensure_dirs()
try:
with open(HISTORY_FILE, "w") as f:
json.dump(hist, f, indent=2)
except Exception:
pass

def add_history(entry):
entry["time"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
hist = load_history()
hist.append(entry)
save_history(hist)
if CONFIG.get("autosave", True):
save_report(entry, "json", silent=True, single=True)

def search_history():
c = theme_colors()
hist = load_history()
if not hist:
print(c["err"] + "No scan history yet." + c["reset"])
pause()
return
term = input("Search term (tool name / target / blank for all): ").strip().lower()
matches = [
h for h in hist
if term in str(h.get("tool", "")).lower() or term in str(h.get("target", "")).lower()
] if term else hist
if not matches:
print(c["warn"] + "No matching entries." + c["reset"])
else:
print(c["title"] + f"\n{len(matches)} match(es):" + c["reset"])
for i, h in enumerate(matches, 1):
print(f"  {i}. [{h.get('time')}] {h.get('tool')} -> {h.get('target')}")
pause()

---------------- Plugin loader ----------------

PLUGIN_MENU_ITEMS = []

def load_plugins():
"""
Loads .py files from ~/.ghosteye/plugins/
Each plugin must define:
NAME = "My Plugin"
def run():
...
"""
ensure_dirs()
PLUGIN_MENU_ITEMS.clear()
if not os.path.isdir(PLUGIN_DIR):
return
for fname in sorted(os.listdir(PLUGIN_DIR)):
if not fname.endswith(".py"):
continue
path = os.path.join(PLUGIN_DIR, fname)
try:
spec = importlib.util.spec_from_file_location(fname[:-3], path)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
name = getattr(mod, "NAME", fname[:-3])
run_fn = getattr(mod, "run", None)
if callable(run_fn):
PLUGIN_MENU_ITEMS.append((name, run_fn))
except Exception as e:
print(Fore.RED + f"[!] Failed to load plugin {fname}: {e}" + Style.RESET_ALL)

def plugin_menu():
c = theme_colors()
if not PLUGIN_MENU_ITEMS:
print(c["warn"] + f"No plugins found in {PLUGIN_DIR}" + c["reset"])
print("Drop a .py file there with NAME and run() defined, then restart GhostEye.")
pause()
return
while True:
clear()
banner()
print(c["title"] + "\n== Plugins ==" + c["reset"])
for i, (name, _) in enumerate(PLUGIN_MENU_ITEMS, 1):
print(f"  {i}. {name}")
print("  0. Back")
ch = input("\nSelect plugin: ").strip()
if ch == "0":
break
try:
idx = int(ch) - 1
if 0 <= idx < len(PLUGIN_MENU_ITEMS):
PLUGIN_MENU_ITEMS[idx]1
else:
print(c["err"] + "Invalid choice." + c["reset"]); time.sleep(1)
except ValueError:
print(c["err"] + "Invalid input." + c["reset"]); time.sleep(1)

---------------- Update / Version checker ----------------

def update_checker():
c = theme_colors()
print(c["info"] + f"\nCurrent version: {VERSION}" + c["reset"])
if not need(bool(requests), "requests"):
return
repo_url = input("Enter GitHub raw version-file URL (blank to skip): ").strip()
if not repo_url:
print("Skipped online check.")
pause()
return
try:
r = requests.get(repo_url, timeout=8)
latest = r.text.strip()
if latest == VERSION:
print(c["ok"] + "You are running the latest version." + c["reset"])
else:
print(c["warn"] + f"A newer version is available: {latest}" + c["reset"])
except Exception as e:
print(c["err"] + f"Error checking for updates: {e}" + c["reset"])
pause()

def version_checker():
c = theme_colors()
print(c["info"] + f"\nGhostEye version: {VERSION}" + c["reset"])
pause()

---------------- Small input helper ----------------

def _get_target(prompt="Enter target (domain/IP): "):
val = input(prompt).strip()
return val

def _get_url(prompt="Enter URL (include http:// or https://): "):
val = input(prompt).strip()
if val and not val.startswith(("http://", "https://")):
val = "https://" + val
return val

---------------- Information Gathering ----------------

def dns_lookup():
c = theme_colors()
domain = _get_target("Enter domain: ")
if not domain:
return
try:
loading_animation("Resolving DNS")
infos = socket.getaddrinfo(domain, None)
ips = sorted(set(i[4][0] for i in infos))
print(c["ok"] + f"\nDNS results for {domain}:" + c["reset"])
for ip in ips:
print(f"  {ip}")
add_history({"tool": "DNS Lookup", "target": domain, "result": ips})
except Exception as e:
print(c["err"] + f"Error: {e}" + c["reset"])
pause()

def whois_lookup():
c = theme_colors()
domain = _get_target("Enter domain: ")
if not domain:
return
try:
out = subprocess.run(["whois", domain], capture_output=True, text=True, timeout=15)
if out.returncode == 0 and out.stdout.strip():
text = out.stdout.strip()
print(c["ok"] + f"\nWHOIS for {domain}:" + c["reset"])
print(text[:3000])
add_history({"tool": "WHOIS Lookup", "target": domain, "result": text[:3000]})
else:
print(c["err"] + "whois command not available or returned no data." + c["reset"])
print("On Termux install with: pkg install whois")
except FileNotFoundError:
print(c["err"] + "'whois' is not installed. Termux: pkg install whois" + c["reset"])
except Exception as e:
print(c["err"] + f"Error: {e}" + c["reset"])
pause()

def ip_info():
c = theme_colors()
if not need(bool(requests), "requests"):
return
target = _get_target("Enter IP (blank for your public IP): ")
url = f"https://ip-api.com/json/{target}" if target else "https://ip-api.com/json/"
try:
loading_animation("Fetching IP info")
r = requests.get(url, timeout=10)
data = r.json()
print(c["ok"] + "\nIP Information:" + c["reset"])
for k, v in data.items():
print(f"  {k}: {v}")
add_history({"tool": "IP Information", "target": target or "self", "result": data})
except Exception as e:
print(c["err"] + f"Error: {e}" + c["reset"])
pause()

def ssl_checker():
c = theme_colors()
domain = _get_target("Enter domain (no https://): ").replace("https://", "").replace("http://", "").strip("/")
if not domain:
return
try:
loading_animation("Checking SSL certificate")
ctx = ssl.create_default_context()
with socket.create_connection((domain, 443), timeout=8) as sock:
with ctx.wrap_socket(sock, server_hostname=domain) as ssock:
cert = ssock.getpeercert()
issuer = dict(x[0] for x in cert.get("issuer", []))
subject = dict(x[0] for x in cert.get("subject", []))
not_after = cert.get("notAfter")
expiry = datetime.datetime.strptime(not_after, "%b %d %H:%M:%S %Y %Z")
days_left = (expiry - datetime.datetime.utcnow()).days
print(c["ok"] + f"\nSSL Certificate for {domain}:" + c["reset"])
print(f"  Issued to  : {subject.get('commonName')}")
print(f"  Issued by  : {issuer.get('commonName')}")
print(f"  Expires    : {not_after} ({days_left} days left)")
if days_left < 30:
print(c["warn"] + "  Warning: certificate expiring soon!" + c["reset"])
add_history({"tool": "SSL Certificate Checker", "target": domain,
"result": {"issued_to": subject.get("commonName"),
"issued_by": issuer.get("commonName"),
"expires": not_after, "days_left": days_left}})
except Exception as e:
print(c["err"] + f"Error: {e}" + c["reset"])
pause()

def website_status():
c = theme_colors()
url = _get_url()
if not url or not need(bool(requests), "requests"):
return
try:
start = time.time()
r = requests.get(url, timeout=10)
elapsed = round((time.time() - start) * 1000, 2)
state = "UP" if r.status_code < 400 else "ISSUE"
color = c["ok"] if state == "UP" else c["err"]
print(color + f"\n{url} -> {state} (status {r.status_code}, {elapsed} ms)" + c["reset"])
add_history({"tool": "Website Status Checker", "target": url,
"result": {"status": r.status_code, "ms": elapsed}})
except Exception as e:
print(c["err"] + f"Error: {e}" + c["reset"])
pause()

def reverse_dns():
c = theme_colors()
ip = _get_target("Enter IP address: ")
if not ip:
return
try:
host = socket.gethostbyaddr(ip)
print(c["ok"] + f"\nReverse DNS for {ip}:" + c["reset"])
print(f"  Hostname: {host[0]}")
add_history({"tool": "Reverse DNS Lookup", "target": ip, "result": host[0]})
except Exception as e:
print(c["err"] + f"Error: {e}" + c["reset"])
pause()

def public_ip_finder():
c = theme_colors()
if not need(bool(requests), "requests"):
return
try:
r = requests.get("https://api.ipify.org?format=json", timeout=8)
ip = r.json().get("ip")
print(c["ok"] + f"\nPublic IP: {ip}" + c["reset"])
add_history({"tool": "Public IP Finder", "target": "self", "result": ip})
except Exception as e:
print(c["err"] + f"Error: {e}" + c["reset"])
pause()

def local_ip_finder():
c = theme_colors()
try:
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.connect(("8.8.8.8", 80))
ip = s.getsockname()[0]
s.close()
print(c["ok"] + f"\nLocal IP: {ip}" + c["reset"])
add_history({"tool": "Local IP Finder", "target": "self", "result": ip})
except Exception as e:
print(c["err"] + f"Error: {e}" + c["reset"])
pause()

---------------- Hash & Encoding ----------------

def _text_hash(algo_name, hasher):
c = theme_colors()
text = input("Enter text: ")
digest = hasher(text.encode()).hexdigest()
print(c["ok"] + f"\n{algo_name}: {digest}" + c["reset"])
add_history({"tool": f"{algo_name} Generator", "target": text[:50], "result": digest})
pause()

def md5_generator():
_text_hash("MD5", hashlib.md5)

def sha1_generator():
_text_hash("SHA1", hashlib.sha1)

def sha256_generator():
_text_hash("SHA256", hashlib.sha256)

def sha512_generator():
_text_hash("SHA512", hashlib.sha512)

def hash_verifier():
c = theme_colors()
text = input("Enter text: ")
expected = input("Enter expected hash: ").strip().lower()
algo = input("Algorithm (md5/sha1/sha256/sha512): ").strip().lower()
hashers = {"md5": hashlib.md5, "sha1": hashlib.sha1, "sha256": hashlib.sha256, "sha512": hashlib.sha512}
if algo not in hashers:
print(c["err"] + "Unknown algorithm." + c["reset"]); pause(); return
digest = hashersalgo.hexdigest()
match = digest == expected
color = c["ok"] if match else c["err"]
print(color + f"\n{'MATCH' if match else 'NO MATCH'} (computed: {digest})" + c["reset"])
add_history({"tool": "Hash Verifier", "target": algo, "result": {"match": match}})
pause()

def base64_encode():
c = theme_colors()
text = input("Enter text: ")
enc = base64.b64encode(text.encode()).decode()
print(c["ok"] + f"\nEncoded: {enc}" + c["reset"])
add_history({"tool": "Base64 Encode", "target": text[:50], "result": enc})
pause()

def base64_decode():
c = theme_colors()
text = input("Enter base64 text: ")
try:
dec = base64.b64decode(text).decode(errors="replace")
print(c["ok"] + f"\nDecoded: {dec}" + c["reset"])
add_history({"tool": "Base64 Decode", "target": text[:50], "result": dec})
except Exception as e:
print(c["err"] + f"Error: {e}" + c["reset"])
pause()

def url_encode():
c = theme_colors()
text = input("Enter text: ")
enc = urllib.parse.quote(text)
print(c["ok"] + f"\nEncoded: {enc}" + c["reset"])
add_history({"tool": "URL Encode", "target": text[:50], "result": enc})
pause()

def url_decode():
c = theme_colors()
text = input("Enter URL-encoded text: ")
dec = urllib.parse.unquote(text)
print(c["ok"] + f"\nDecoded: {dec}" + c["reset"])
add_history({"tool": "URL Decode", "target": text[:50], "result": dec})
pause()

---------------- Password Tools ----------------

def password_strength_checker():
c = theme_colors()
pw = input("Enter password to check: ")
length = len(pw)
has_lower = any(ch.islower() for ch in pw)
has_upper = any(ch.isupper() for ch in pw)
has_digit = any(ch.isdigit() for ch in pw)
has_symbol = any(ch in string.punctuation for ch in pw)
score = sum([length >= 8, length >= 12, has_lower, has_upper, has_digit, has_symbol])
labels = ["Very Weak", "Weak", "Fair", "Good", "Strong", "Very Strong"]
label = labels[min(score, len(labels) - 1)]
print(c["title"] + f"\nLength: {length}" + c["reset"])
print(f"  Lowercase: {'Yes' if has_lower else 'No'}")
print(f"  Uppercase: {'Yes' if has_upper else 'No'}")
print(f"  Digits   : {'Yes' if has_digit else 'No'}")
print(f"  Symbols  : {'Yes' if has_symbol else 'No'}")
print(c["ok"] + f"  Strength : {label}" + c["reset"])
add_history({"tool": "Password Strength Checker", "target": "*" * length, "result": label})
pause()

def random_password_generator():
c = theme_colors()
try:
length = int(input("Password length (default 16): ").strip() or "16")
except ValueError:
length = 16
alphabet = string.ascii_letters + string.digits + string.punctuation
pw = "".join(secrets.choice(alphabet) for _ in range(length))
print(c["ok"] + f"\nGenerated password: {pw}" + c["reset"])
add_history({"tool": "Random Password Generator", "target": f"length={length}", "result": "[hidden]"})
pause()

WORDLIST = ["ghost", "shadow", "nova", "cipher", "quantum", "raven", "delta", "phoenix",
"matrix", "vortex", "cobra", "tiger", "orbit", "falcon", "storm", "echo",
"cyber", "flux", "nomad", "onyx", "pixel", "rogue", "titan", "zenith"]

def passphrase_generator():
c = theme_colors()
try:
words = int(input("Number of words (default 4): ").strip() or "4")
except ValueError:
words = 4
chosen = [secrets.choice(WORDLIST) for _ in range(words)]
passphrase = "-".join(chosen) + "-" + str(secrets.randbelow(900) + 100)
print(c["ok"] + f"\nGenerated passphrase: {passphrase}" + c["reset"])
add_history({"tool": "Passphrase Generator", "target": f"words={words}", "result": "[hidden]"})
pause()

---------------- File Analysis ----------------

def _get_file_path():
path = input("Enter file path: ").strip()
if not os.path.isfile(path):
c = theme_colors()
print(def _get_file_path():
path = input("Enter file path: ").strip()
if not os.path.isfile(path):
c = theme_colors()
print(c["err"] + "File not found." + c["reset"])
pause()
return None
return path

def file_hash_generator():
c = theme_colors()
path = _get_file_path()
if not path:
return
algo = input("Algorithm (md5/sha1/sha256/sha512, default sha256): ").strip().lower() or "sha256"
hashers = {"md5": hashlib.md5, "sha1": hashlib.sha1, "sha256": hashlib.sha256, "sha512": hashlib.sha512}
if algo not in hashers:
print(c["err"] + "Unknown algorithm." + c["reset"]); pause(); return
h = hashersalgo
try:
loading_animation("Hashing file")
with open(path, "rb") as f:
for chunk in iter(lambda: f.read(1024 * 1024), b""):
h.update(chunk)
digest = h.hexdigest()
print(c["ok"] + f"\n{algo.upper()} of {path}:\n  {digest}" + c["reset"])
add_history({"tool": "File Hash Generator", "target": path, "result": digest})
except Exception as e:
print(c["err"] + f"Error: {e}" + c["reset"])
pause()

def file_integrity_checker():
c = theme_colors()
path = _get_file_path()
if not path:
return
expected = input("Enter expected SHA256 hash: ").strip().lower()
h = hashlib.sha256()
try:
with open(path, "rb") as f:
for chunk in iter(lambda: f.read(1024 * 1024), b""):
h.update(chunk)
digest = h.hexdigest()
match = digest == expected
color = c["ok"] if match else c["err"]
print(color + f"\n{'INTEGRITY OK' if match else 'INTEGRITY MISMATCH'} (computed: {digest})" + c["reset"])
add_history({"tool": "File Integrity Checker", "target": path, "result": {"match": match}})
except Exception as e:
print(c["err"] + f"Error: {e}" + c["reset"])
pause()

def file_metadata_viewer():
c = theme_colors()
path = _get_file_path()
if not path:
return
try:
st = os.stat(path)
info = {
"size_bytes": st.st_size,
"created": datetime.datetime.fromtimestamp(st.st_ctime).strftime("%Y-%m-%d %H:%M:%S"),
"modified": datetime.datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
"accessed": datetime.datetime.fromtimestamp(st.st_atime).strftime("%Y-%m-%d %H:%M:%S"),
}
print(c["ok"] + f"\nMetadata for {path}:" + c["reset"])
for k, v in info.items():
print(f"  {k}: {v}")
add_history({"tool": "File Metadata Viewer", "target": path, "result": info})
except Exception as e:
print(c["err"] + f"Error: {e}" + c["reset"])
pause()

def exif_viewer():
c = theme_colors()
if not need(HAS_PIL, "pillow"):
return
path = _get_file_path()
if not path:
return
try:
img = Image.open(path)
exif_data = img._getexif() if hasattr(img, "_getexif") else None
if not exif_data:
print(c["warn"] + "No EXIF data found." + c["reset"])
else:
result = {}
print(c["ok"] + f"\nEXIF data for {path}:" + c["reset"])
for tag_id, value in exif_data.items():
tag = TAGS.get(tag_id, tag_id)
print(f"  {tag}: {value}")
result[str(tag)] = str(value)
add_history({"tool": "EXIF Metadata Viewer", "target": path, "result": result})
except Exception as e:
print(c["err"] + f"Error: {e}" + c["reset"])
pause()

---------------- Website Analysis ----------------

def http_header_analyzer():
c = theme_colors()
url = _get_url()
if not url or not need(bool(requests), "requests"):
return
try:
r = requests.get(url, timeout=10)
print(c["ok"] + f"\nHTTP Headers for {url}:" + c["reset"])
for k, v in r.headers.items():
print(f"  {k}: {v}")
add_history({"tool": "HTTP Header Analyzer", "target": url, "result": dict(r.headers)})
except Exception as e:
print(c["err"] + f"Error: {e}" + c["reset"])
pause()

SECURITY_HEADERS = [
"Strict-Transport-Security", "Content-Security-Policy", "X-Frame-Options",
"X-Content-Type-Options", "Referrer-Policy", "Permissions-Policy",
]

def security_header_report():
c = theme_colors()
url = _get_url()
if not url or not need(bool(requests), "requests"):
return
try:
r = requests.get(url, timeout=10)
print(c["title"] + f"\nSecurity Header Report for {url}:" + c["reset"])
result = {}
for h in SECURITY_HEADERS:
present = h in r.headers
result[h] = present
color = c["ok"] if present else c["err"]
status = "Present" if present else "Missing"
print(color + f"  {h}: {status}" + c["reset"])
add_history({"tool": "Security Header Report", "target": url, "result": result})
except Exception as e:
print(c["err"] + f"Error: {e}" + c["reset"])
pause()

def redirect_checker():
c = theme_colors()
url = _get_url()
if not url or not need(bool(requests), "requests"):
return
try:
r = requests.get(url, timeout=10, allow_redirects=True)
print(c["title"] + f"\nRedirect Chain for {url}:" + c["reset"])
chain = []
for i, h in enumerate(r.history, 1):
print(f"  {i}. {h.status_code} -> {h.url}")
chain.append({"step": i, "status": h.status_code, "url": h.url})
print(f"  Final -> {r.status_code} -> {r.url}")
chain.append({"step": "final", "status": r.status_code, "url": r.url})
add_history({"tool": "Redirect Checker", "target": url, "result": chain})
except Exception as e:
print(c["err"] + f"Error: {e}" + c["reset"])
pause()

def cookie_inspector():
c = theme_colors()
url = _get_url()
if not url or not need(bool(requests), "requests"):
return
try:
r = requests.get(url, timeout=10)
print(c["title"] + f"\nCookies set by {url}:" + c["reset"])
result = []
if not r.cookies:
print("  No cookies found.")
for ck in r.cookies:
info = {"name": ck.name, "value": ck.value, "domain": ck.domain, "path": ck.path,
"expires": ck.expires, "secure": ck.secure}
result.append(info)
print(f"  {ck.name} = {ck.value}")
print(f"    domain={ck.domain} path={ck.path} secure={ck.secure} expires={ck.expires}")
add_history({"tool": "Cookie Inspector", "target": url, "result": result})
except Exception as e:
print(c["err"] + f"Error: {e}" + c["reset"])
pause()

def robots_checker():
c = theme_colors()
domain = input("Enter domain (e.g. example.com): ").strip()
if not domain or not need(bool(requests), "requests"):
return
url = f"https://{domain}/robots.txt"
try:
r = requests.get(url, timeout=10)
print(c["title"] + f"\nrobots.txt for {domain}:" + c["reset"])
print(r.text[:3000] if r.status_code == 200 else f"  Not found (status {r.status_code})")
add_history({"tool": "robots.txt Checker", "target": domain, "result": {"status": r.status_code}})
except Exception as e:
print(c["err"] + f"Error: {e}" + c["reset"])
pause()

def sitemap_checker():
c = theme_colors()
domain = input("Enter domain (e.g. example.com): ").strip()
if not domain or not need(bool(requests), "requests"):
return
url = f"https://{domain}/sitemap.xml"
try:
r = requests.get(url, timeout=10)
print(c["title"] + f"\nsitemap.xml for {domain}:" + c["reset"])
print(r.text[:3000] if r.status_code == 200 else f"  Not found (status {r.status_code})")
add_history({"tool": "sitemap.xml Checker", "target": domain, "result": {"status": r.status_code}})
except Exception as e:
print(c["err"] + f"Error: {e}" + c["reset"])
pause()

---------------- Reports ----------------

def save_report(data, fmt="json", silent=False, single=False):
ensure_dirs()
ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
prefix = "entry" if single else "report"
fname = os.path.join(REPORT_DIR, f"{prefix}_{ts}.{fmt}")
try:
if fmt == "json":
with open(fname, "w") as f:
json.dump(data, f, indent=2)
elif fmt == "txt":
with open(fname, "w") as f:
f.write(f"GhostEye v{VERSION} Report\n")
f.write("=" * 40 + "\n")
if isinstance(data, list):
for item in data:
f.write(json.dumps(item, indent=2) + "\n" + ("-" * 40) + "\n")
else:
for k, v in data.items():
f.write(f"{k}: {v}\n")
elif fmt == "html":
with open(fname, "w") as f:
f.write("<html><head><meta charset='utf-8'>")
f.write("<style>body{font-family:monospace;background:#111;color:#eee;padding:20px}")
f.write("h2{color:#0ff}pre{background:#1c1c1c;padding:12px;border-radius:6px;")
f.write("border:1px solid #333;white-space:pre-wrap}</style></head><body>")
f.write(f"<h2>GhostEye v{VERSION} Report</h2>")
f.write(f"<p>Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>")
f.write("<pre>")
f.write(json.dumps(data, indent=2))
f.write("</pre></body></html>")
if not silent:
print(theme_colors()["ok"] + f"Report saved: {fname}" + theme_colors()["reset"])
except Exception as e:
if not silent:
print(theme_colors()["err"] + f"Error saving report: {e}" + theme_colors()["reset"])

def report_menu():
c = theme_colors()
hist = load_history()
if not hist:
print(c["err"] + "No scan history yet." + c["reset"]); pause(); return
print("1. Export as HTML\n2. Export as TXT\n3. Export as JSON\n4. View Scan History\n5. Search History\n0. Back")
ch = input("Choose: ").strip()
if ch == "1":
save_report(hist, "html")
elif ch == "2":
save_report(hist, "txt")
elif ch == "3":
save_report(hist, "json")
elif ch == "4":
for i, h in enumerate(hist, 1):
print(f"{i}. [{h.get('time')}] {h.get('tool')} -> {h.get('target')}")
pause()
elif ch == "5":
search_history()

---------------- Utilities ----------------

def port_checker():
c = theme_colors()
print(c["err"] + "\n[!] Only check ports on hosts you own or are explicitly authorized to test." + c["reset"])
host = input("Enter host (IP/domain): ").strip()
confirm = input(f"Confirm you are authorized to test '{host}'? (yes/no): ").strip().lower()
if confirm != "yes":
print("Cancelled."); pause(); return
try:
port = int(input("Enter port number: ").strip())
except ValueError:
print(c["err"] + "Invalid port." + c["reset"]); pause(); return
try:
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.settimeout(3)
result = sock.connect_ex((host, port))
state = "OPEN" if result == 0 else "CLOSED/FILTERED"
color = c["ok"] if result == 0 else c["err"]
print(color + f"\nPort {port} on {host}: {state}" + c["reset"])
sock.close()
add_history({"tool": "Port Availability Checker", "target": f"{host}:{port}", "result": state})
except Exception as e:
print(c["err"] + f"Error: {e}" + c["reset"])
pause()

def timestamp_generator():
c = theme_colors()
now = datetime.datetime.now()
utc_now = datetime.datetime.utcnow()
print(c["title"] + "\nCurrent Timestamps:" + c["reset"])
print(f"  Local Time : {now.strftime('%Y-%m-%d %H:%M:%S')}")
print(f"  UTC Time   : {utc_now.strftime('%Y-%m-%d %H:%M:%S')}")
print(f"  Epoch      : {int(time.time())}")
conv = input("\nConvert an epoch timestamp? (number or blank): ").strip()
if conv:
try:
dt = datetime.datetime.fromtimestamp(int(conv))
print(f"  {conv} -> {dt.strftime('%Y-%m-%d %H:%M:%S')}")
except Exception as e:
print(c["err"] + f"Error: {e}" + c["reset"])
pause()

def qr_generator():
c = theme_colors()
if not need(HAS_QRCODE, "qrcode[pil]"):
return
data = input("Enter text/URL to encode: ").strip()
fname = input("Output filename (default qr.png): ").strip() or "qr.png"
try:
img = qrcode.make(data)
img.save(fname)
print(c["ok"] + f"\nQR code saved as {fname}" + c["reset"])
except Exception as e:
print(c["err"] + f"Error: {e}" + c["reset"])
pause()

def qr_reader():
c = theme_colors()
path = input("Enter QR image path: ").strip()
if not os.path.isfile(path):
print(c["err"] + "File not found." + c["reset"]); pause(); return
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
print(c["ok"] + f"\nDecoded Data: {decoded_text}" + c["reset"])
else:
print(c["err"] + "\nCould not decode. Install opencv-python-headless or pyzbar+pillow." + c["reset"])
pause()

def internet_speed_check():
c = theme_colors()
try:
import speedtest
except ImportError:
print(c["err"] + "[!] 'speedtest-cli' not installed. Run: pip install speedtest-cli" + c["reset"])
pause(); return
try:
loading_animation("Testing internet speed (may take a while)", duration=2.0)
st = speedtest.Speedtest()
st.get_best_server()
down = st.download() / 1_000_000
up = st.upload() / 1_000_000
print(c["ok"] + "\nInternet Speed Test Results:" + c["reset"])
print(f"  Download: {down:.2f} Mbps")
print(f"  Upload  : {up:.2f} Mbps")
print(f"  Ping    : {st.results.ping:.2f} ms")
except Exception as e:
print(c["err"] + f"Error: {e}" + c["reset"])
pause()

---------------- Settings ----------------

def settings_menu():
c = theme_colors()
while True:
clear()
print(c["title"] + "== Settings ==" + c["reset"])
print(f"1. Theme: {CONFIG.get('theme')}")
print(f"2. Auto Save Reports: {CONFIG.get('autosave')}")
print("3. Update Checker")
print("4. Version Checker")
print("5. Reload Plugins")
print("6. About")
print("0. Back")
ch = input("Choose: ").strip()
if ch == "1":
CONFIG["theme"] = "light" if CONFIG.get("theme") == "dark" else "dark"
save_config(CONFIG)
elif ch == "2":
CONFIG["autosave"] = not CONFIG.get("autosave", True)
save_config(CONFIG)
elif ch == "3":
update_checker()
elif ch == "4":
version_checker()
elif ch == "5":
load_plugins()
print(c["ok"] + f"Loaded {len(PLUGIN_MENU_ITEMS)} plugin(s)." + c["reset"])
pause()
elif ch == "6":
about()
elif ch == "0":
break

---------------- Menu system ----------------

MENUS = {
"1": ("Information Gathering", [
("DNS Lookup", dns_lookup),
("WHOIS Lookup", whois_lookup),
("IP Information", ip_info),
("SSL Certificate Checker", ssl_checker),
("Website Status Checker", website_status),
("Reverse DNS Lookup", reverse_dns),
("Public IP Finder", public_ip_finder),
("Local IP Finder", local_ip_finder),
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
("Port Availability Checker", port_checker),
("Timestamp Generator", timestamp_generator),
("QR Code Generator", qr_generator),
("QR Code Reader", qr_reader),
]),
"8": ("Plugins", [
("Open Plugin Menu", plugin_menu),
]),
"9": ("Settings", [
("Open Settings", settings_menu),
]),
}

def show_category(key):
c = theme_colors()
title, items = MENUS[key]
while True:
clear()
banner()
print(c["title"] + f"\n== {title} ==" + c["reset"])
for i, (name, _) in enumerate(items, 1):
print(f"  {i}. {name}")
print("  0. Back to Main Menu")
choice = input("\nSelect option: ").strip()
if choice == "0":
break
try:
idx = int(choice) - 1
if 0 <= idx < len(items):
items[idx]1
else:
print(c["err"] + "Invalid choice." + c["reset"]); time.sleep(1)
except ValueError:
print(c["err"] + "Invalid input." + c["reset"]); time.sleep(1)

def main_menu():
c = theme_colors()
while True:
clear()
banner()
print(c["title"] + "\nMain Menu:" + c["reset"])
for key, (title, _) in MENUS.items():
print(f"  {key}. {title}")
print("  0. Exit")
choice = input("\nSelect category: ").strip()
if choice == "0":
print(Fore.MAGENTA + f"\nThanks for using GhostEye v{VERSION}. Goodbye!" + Style.RESET_ALL)
sys.exit(0)
elif choice in MENUS:
show_category(choice)
else:
print(c["err"] + "Invalid choice." + c["reset"]); time.sleep(1)

if name == "main":
try:
ensure_dirs()
load_plugins()
main_menu()
except KeyboardInterrupt:
print(Fore.MAGENTA + "\n\nExiting GhostEye. Bye!" + Style.RESET_ALL)
sys.exit(0)