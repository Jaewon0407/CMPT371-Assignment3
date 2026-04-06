# CMPT371 Assignment 3 — File Transfer System (TCP + GUI)

## Team Members

- Name: Jaewon Han | ID: 301465045 | Email: jha334@sfu.ca
- Name: Kalpana Kalpana | ID: 301467039 | Email: kka119@sfu.ca

### 1) Project Overview & Description

This project implements a functional TCP client-server application in Python: a **file transfer system** with a **Tkinter GUI client**. Multiple clients can connect to a central server, download/upload files to the shared server folder and also send files to other clients.

The server is responsible for:
- Handling multiple clients concurrently (thread-per-client)
- Validating requests and filenames
- Enforcing an **overwrite-rejected** policy (server refuses uploads if the filename already exists)
- Preserving data integrity using **SHA-256** checks for every transfer

### 2) Key Features

- **TCP client-server architecture** using Python’s Socket API
- **Multi-client concurrency** via `threading.Thread` on the server
- **Reliable message framing** for control messages (length-prefixed JSON)
- **File integrity verification** (SHA-256 on upload/download)
- **Atomic uploads** using temporary `.part` files and rename/replace semantics
- **GUI client** supports: Refresh/List, Upload, Download, and “Send File to Client”
- **Client inbox sync**: the GUI periodically checks for incoming files and downloads them automatically

### 3) Limitations

- File transfer does not resume if it is interrupted; the file must be re-uploaded or re-downloaded
- Authentication is not implemented - any client can connect to the server with any client ID
- Clients cannot be locked from viewing other client files (no per-client access control) which is a security limitation
- No encryption added - files sent over plain TCP
- Single file can be uploaded at a time
- This system is designed for local network use only
- Since the GUI file selection dialog cannot be fully blocked, so the clients can browse outside of their own client folder (GUI limitation - currently implemented by showing error and not proceeding with the request)

### 4) Requirements

This project uses standard Python libraries:

- socket
- os
- tkinter
- hashlib
- threading
- uuid
- argparse
- json

Tested on Python 3.11.5

### 5) How to Setup + Run

1. Clone the repository and enter the project folder:

   ```bash
   git clone https://github.com/Jaewon0407/CMPT371-Assignment3.git
   cd CMPT371-Assignment3
   ```

2. Verify Python is installed and Tkinter is available (tested on Python 3.11.5):

   ```bash
   python3 --version
   python3 -c "import tkinter; print('tkinter OK')"
   ```

   If `python3` is not found on your machine, use `python` instead (depends on OS setup).
   
   If the Tkinter import fails on Linux (common on fresh installs), install:

   ```bash
   sudo apt-get update
   sudo apt-get install -y python3-tk
   ```

3. Start the server (Terminal 1):

   ```bash
   python3 server.py
   ```

   Expected output:

   ```text
   Server listening on 0.0.0.0:5001
   ```

4. Start the GUI Client #1 (Terminal 2):

   ```bash
   python3 gui.py
   ```

   In the GUI, use:
   - Host: `127.0.0.1`
   - Port: `5001`
   - Client ID: `ClientA` (any unique ID)

   Client files are saved under: `client_db/<ClientID>/`

5. Start the GUI Client #2 (Terminal 3):

   ```bash
   python3 gui.py
   ```

   Use a different Client ID (e.g., `ClientB`) so the server can keep each client’s inbox separate.

#### Shared folder upload/download demo

From either client:
1. Click **Refresh** to update the shared file list.
2. Click **Upload** and choose a local file. (If the filename already exists on the server, the server rejects the upload.)
3. On the other client, click **Refresh**, select the uploaded file, then click **Download**.

#### Send a file to another client
1. Ensure both clients have connected at least once.
2. In the sender GUI, select the destination client in **Connected Clients**.
3. Click **Send File** and choose a file from the sender’s local folder `client_db/<SenderID>/`.

The receiver automatically syncs its inbox every few seconds and saves incoming files to:
- `client_db/<ReceiverID>/` 

#### Terminate Cleanly
Click **Disconnect** in the GUI(s), then close the window(s). Stop the server with `Ctrl+C` in its terminal.

### 6) Technical Protocol Details (Length-Prefixed JSON over TCP)

All communication uses TCP. We separate:

#### Control messages (JSON frames)
- Format: `LEN(4 bytes, big-endian)` + `LEN bytes of UTF-8 JSON`
- Each request includes:
  - `type`: request name (string)
  - `request_id`: unique string (UUID) so the client can match responses

The server replies with JSON frames:
- `{"type":"OK", ...}` on success
- `{"type":"ERROR", "message": "..."}` on failure

#### File bytes
After the server and client agree on a `size` (in bytes), the sender streams exactly `size` raw bytes. The receiver reads until it has received exactly `size` bytes.

#### Supported request types

Handshake:
- `HELLO {client_id}` → `OK {client_id}` or `ERROR`

Shared folder operations:
- `LIST` → `OK {files:[{name,size}, ...]}`
- `GET {name}` → `OK {size, sha256}` then file bytes
- `PUT {name, size, sha256}` → `OK` then file bytes then final `OK` / `ERROR`

Client inbox operations:
- `LIST_CLIENTS` → `OK {clients:[...]} `
- `LIST_CLIENT {client_id}` → `OK {files:[...]} `
- `GET_CLIENT {client_id, name}` → `OK {size, sha256}` then file bytes
- `PUT_CLIENT {client_id, name, size, sha256}` → `OK` then file bytes then final `OK` / `ERROR`

Termination:
- `BYE` → `OK` then close

### 7) Repository Layout

- `server.py`: multi-client TCP server, shared folder + per-client inbox folders
- `gui.py`: Tkinter GUI client (connect, refresh, upload/download, send-to-client, auto-sync)
- `protocol.py`: length-prefixed JSON framing helpers
- `shared/`: server’s shared folder (files visible to all clients)
- `clients/`: server’s per-client inbox folders (one folder per client ID)
- `client_db/`: local client storage (one folder per client ID)

### 8) Video Demo

Video link:

The demo video includes:

- Starting server
- Client connecting to server
- Uploading and downloading to the server
- Sending file to a client
- Disconnecting from the server

### 9) Implementation Summary

### Code origin
- All application code was written by our group. ChatGPT was used to create the interface/frontend.

### GenAI usage (if applicable)
- ChatGPT was used to assist in writing and polishing `README.md`
- GitHub Copilot was used for planning the workflow of the project.

### References
- Python documentation: sockets, threading, and Tkinter
- Python Socket Programming HOWTO (conceptual reference)