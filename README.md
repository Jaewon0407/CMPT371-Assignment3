# CMPT371 Assignment 3 — File Transfer System (TCP + GUI)

## Team Members

- Name: Jaewon Han | ID: \***\*\_\*\*** | Email: jha334@sfu.ca
- Name: Kalpana Kalpana | ID: 301467039 | Email: kka119@sfu.ca

## Project Description

This project is a TCP-based file transfer system implemented using Python with a Tkinter GUI.

The GUI displays a list of available files on server to download, available clients to send files to, progress bar and logs for activity in current session.

This system allows multiple clients to connect to a server, upload and download files, and also send files to another client through the server. It uses thread-per-client model.

It uses SHA-256 verification to verify the data integrity of uploaded and downloaded files.

## Project Plan

Fixed choices:

- Single shared server folder for all clients.
- Overwrite policy is **reject if filename exists**.

### 1) Requirements → Features Mapping

- **Networking functionality:** TCP client-server app that reliably connects, exchanges data, and terminates cleanly.
- **Data integrity:** SHA-256 verification for every upload and download.
- **Concurrency:** server supports multiple clients at once (thread-per-client is simplest in Python).
- **Interface:** GUI client implemented with Tkinter with transfer progress + status log (bonus-friendly).
- **Run-ability:** clear, reproducible commands in README.md for a fresh environment.

### 2) Architecture

**Server**

- Listens on a host/port.
- Accepts multiple client connections and handles each in its own thread.
- Stores shared files in one configured shared root folder and client-to-client files in per-client folders.

**Client**

- GUI application that connects to the server and performs `LIST` / `GET` / `PUT`.
- Runs all socket/file transfer work in a background thread so the UI never freezes and updates progress with a progress bar.
- Reports progress/events back to the GUI via a thread-safe queue.

### 3) Protocol Design (Framing over TCP)

Goal: avoid TCP “message boundary” bugs by explicitly framing control messages.

**Control messages (JSON frames)**

- Format: 4-byte big-endian length `N` + `N` bytes of UTF-8 JSON.
- Every message includes:
  - `type`: `"LIST" | "GET" | "PUT" | "BYE" | "OK" | "ERROR"`
  - `request_id`: unique string to match responses to GUI actions

**File bytes (raw stream)**

- After metadata says `size`, sender streams exactly `size` bytes.
- Receiver reads until it has exactly `size` bytes (looped `recv`), not “until close”.

**Core requests/responses**

- `LIST` → `OK {files:[{name,size}, ...]}`
- `GET {name}` → `OK {size, sha256}` then file bytes; or `ERROR {message}`
- `PUT {name, size, sha256}` → server replies `OK` or `ERROR`; if `OK`, client sends file bytes
- `BYE` → close

### 4) Storage + Safety Rules (based on your decisions)

- **Single shared folder:** all clients see the same remote file list.
- **Reject overwrite:** if `name` already exists on the server, `PUT` returns `ERROR` and no bytes are accepted (or the server immediately discards/doesn’t enter receive mode).
- **Filename sanitization:** reject path traversal and separators so clients cannot escape the server root (e.g., disallow `..`, `/`, `\`).
- **Atomic upload:**
  - Receive into a temporary file first.
  - If SHA-256 matches and the final filename does not exist, rename temp → final.
  - If hash mismatch or disconnect, delete the temp file.
- **Chunked transfer:** fixed-size chunks (e.g., 64 KiB) to support large files without high memory use.

### 5) GUI Implementation (Tkinter)

- Connection: host, port, Client ID, Connect/Disconnect
- Remote files: Refresh/List button + list display
- Upload: Upload button → Choose file
- Download: select file → Download button + choose destination folder
- Progress bar + % label for current transfer
- Status log (scrollable text) for errors + events
<!-- 
Threading model:


- UI thread: all widget updates only
- Worker thread: networking + file I/O
- UI updates via `queue.Queue` + `root.after(...)` polling loop -->

### 6) Limitations

- File transfer does not resume if it is interrupted; the file must be re-uploaded or re-downloaded
- Authentication is not implemented - any client can connect to the server with any client ID
- No encryption added - files sent over plain TCP
- Single file can be uploaded at a time
- This system is designed for local network use only
- Since the GUI file selection dialog cannot be fully blocked, so the clients can browse outside of their own client folder (GUI limitation - currently implemented by showing error and not proceeding with the request)

### 7) Requirements

This project uses standard Python libraries:

- socket
- os
- tkinter
- hashlib
- threading
- uuid

Tested on Python 3.11.5

### 8) How to Run:

1. Clone the repository:
   git clone https://github.com/Jaewon0407/CMPT371-Assignment3.git

   Switch to CMPT371-Assignment3 folder directory

2. Make sure requirements are met.

3. Start the server
   python server.py

4. Run client GUI
   python gui.py

5. In the GUI,
   Client ID: any unique name

### 9) Video Demo

Video link:

The demo video includes:

- Starting server
- Client connecting to server
- Uploading and downloading to the server
- Sending file to a client
- Disconnecting from the server

### 10) Implementation Summary

- **Networking primitives:** implement `recv_exact`, `send_json_frame`, `recv_json_frame` - Done
- **Server skeleton:** listen/accept loop, per-client handler thread, clean shutdown behavior - Done
- **GET:** send metadata (size + sha256), then stream bytes; client verifies hash
- **PUT (with overwrite rejection):**
  - If filename exists: respond `ERROR` immediately
  - Else accept upload to temp file, stream-hash while receiving, verify, then rename
- **Hardening:** disconnect mid-transfer cleanup, filename checks, clear error messages
- **GUI integration:** connect + list; add upload + download with progress and logs
- **Polish for grading:** extensive comments (protocol framing, read loops, concurrency, GUI threading); “Limitations” section written clearly
- **Demo readiness:** predictable 2-minute script: start server → connect → list → upload → list → download → verify → disconnect

### 11) README Content Plan

Expand README.md to include:

- Project title + description
- How TCP framing works at a high level (so graders understand your design)
- Step-by-step run guide (fresh environment assumptions)
- Limitations/issues (explicit):
  - No resume support
  - No encryption/authentication
  - Single shared folder (no per-user isolation)
  - Upload overwrite is rejected (user must rename)
  - Filename restrictions (no paths)
- Video demo link + team member names/IDs/emails
