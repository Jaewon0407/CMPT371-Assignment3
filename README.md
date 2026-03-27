# CMPT371 Assignment 3 — File Transfer System (TCP + GUI)

## Project Plan

Fixed choices:
- Single shared server folder for all clients.
- Overwrite policy is **reject if filename exists**.

### 1) Requirements → Features Mapping

- **Networking functionality:** TCP client-server app that reliably connects, exchanges data, and terminates cleanly.
- **Data integrity:** SHA-256 verification for every upload and download.
- **Concurrency:** server supports multiple clients at once (thread-per-client is simplest in Python).
- **Interface:** GUI client with transfer progress + status log (bonus-friendly).
- **Run-ability:** clear, reproducible commands in README.md for a fresh environment.

### 2) Architecture

**Server**
- Listens on a host/port.
- Accepts multiple client connections and handles each in its own thread.
- Stores all files in one configured shared root folder (e.g., `shared`).

**Client**
- GUI application that connects to the server and performs `LIST` / `GET` / `PUT`.
- Runs all socket/file transfer work in a background thread so the UI never freezes.
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

### 5) GUI Plan (Tkinter)

Minimal UI that demos well and stays stable:
- Connection: host, port, Connect/Disconnect
- Remote files: Refresh/List button + list display
- Upload: Choose file → Upload button
- Download: select file → Download button + choose destination folder
- Progress bar + % label for current transfer
- Status log (scrollable text) for errors + events

Threading model:
- UI thread: all widget updates only
- Worker thread: networking + file I/O
- UI updates via `queue.Queue` + `root.after(...)` polling loop

### 6) Implementation Milestones (recommended order)

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

### 7) README Content Plan

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