"""
TCP File Transfer Server

A multi-threaded server that allows multiple clients to:
- Upload/download files to/from a shared folder
- Send files to specific clients (peer-to-peer)
- List available files and connected clients

Each client connection is handled in a separate thread. Files are verified using SHA-256 hashing.
Uploads are atomic: failed transfers don't leave partial files.
"""

import argparse
import os
import socket
import threading
from typing import Dict, Any

from protocol import send_json, recv_json
import hashlib

CHUNK_SIZE = 65536  # Size of chunks for large file transfers (64 KB)
active_clients = set()  # Set of currently connected client IDs
lock = threading.Lock()  # Lock for thread-safe access to active_clients

def _sanitize_filename(name):
    """
    Validate and sanitize a filename to prevent directory traversal attacks.
    
    Checks that:
    - name is a non-empty string
    - name doesn't contain null bytes
    - name doesn't contain path separators (/ or \)
    - name is not "." or ".."
    - name doesn't end with ".part" (reserved for temporary uploads)
    """
    if not isinstance(name, str) or not name:
        raise ValueError("Missing file name")
    if "\x00" in name:
        raise ValueError("Invalid file name")
    if "/" in name or "\\" in name:
        raise ValueError("File name must not contain path separators")
    if name in {".", ".."}:
        raise ValueError("Invalid file name")
    if name.endswith(".part"):
        raise ValueError("Invalid file name")
    return name

def _sanitize_client_id(client_id):
    """
    Validate a client ID to prevent directory traversal attacks.
    
    Checks that:
    - client_id is a non-empty string
    - length is 64 characters or less
    - only contains alphanumeric, underscore, or hyphen characters
    """
    if not isinstance(client_id, str) or not client_id:
        raise ValueError("Missing client_id")
    if len(client_id) > 64:
        raise ValueError("client_id too long")
    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" )
    if any(ch not in allowed for ch in client_id):
        raise ValueError("client_id may only contain letters, digits, '_' or '-'")
    return client_id

def _client_root(clients_root, client_id):
    """
    Get the folder path for a specific client, with validation to prevent directory traversal.
    
    Args:
        clients_root: The base directory containing all client folders
        client_id: The client ID (must be already sanitized)
    
    Returns:
        The absolute path to the client's folder
    
    Raises:
        ValueError if the resolved path attempts to escape clients_root
    """
    # client_id is already sanitized to forbid separators.
    path = os.path.join(clients_root, client_id)
    abs_root = os.path.abspath(clients_root)
    abs_path = os.path.abspath(path)
    if os.path.commonpath([abs_root, abs_path]) != abs_root:
        raise ValueError("Invalid client_id")
    return path

def _sha256_file(path):
    """
    Compute the SHA-256 hash of a file to verify data integrity.
    
    Reads the file in chunks to handle large files efficiently
    without loading the entire file into memory.
    """
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            ch = f.read(CHUNK_SIZE)
            if not ch:
                break
            h.update(ch)
    return h.hexdigest()

def _send_file_bytes(conn, path):
    """
    Send a file's contents over the socket connection in chunks.
    
    Args:
        conn: Socket connection to send data through
        path: Path to the file to send
    """
    with open(path, "rb") as f:
        while True:
            ch = f.read(CHUNK_SIZE)
            if not ch:
                break
            conn.sendall(ch)

def _recv_file_bytes(conn, dest_path, total_bytes):
    """
    Receive file data over the socket and save it to a file.
    
    Computes SHA-256 hash while receiving data for integrity verification.
    
    Args:
        conn: Socket connection to receive data from
        dest_path: Path where to save the received file
        total_bytes: Expected number of bytes to receive
    
    Returns:
        The SHA-256 hash of the received file
    
    Raises:
        ConnectionError if the socket closes before all bytes are received
    """
    h = hashlib.sha256()
    remaining = total_bytes
    with open(dest_path, "wb") as f:
        while remaining > 0:
            ch = conn.recv(min(CHUNK_SIZE, remaining))
            if not ch:
                raise ConnectionError("Socket closed while receiving file bytes")
            remaining -= len(ch)
            f.write(ch)
            h.update(ch)
    return h.hexdigest()

def safe_list_files(root):
    """
    List all files in a directory (non-recursively).
    
    Excludes:
    - Directories
    - Files ending with ".part" (temporary/incomplete uploads)
    
    Returns:
        List of dictionaries with "name" and "size" keys, sorted by filename
    """
    files = []
    with os.scandir(root) as it:
        for entry in it:
            if not entry.is_file():
                continue
            if entry.name.endswith(".part"):
                continue
            st = entry.stat()
            files.append({"name": entry.name, "size": st.st_size})
    files.sort(key=lambda x: x["name"].lower())
    return files

def _add_active_client(client_id):
    """
    Register a client as active (connected).
    
    Thread-safe operation using a lock.
    
    Returns:
        True if the client was successfully added
        False if the client ID was already in use
    """
    with lock:
        if client_id in active_clients:
            return False
        
        # add client
        active_clients.add(client_id)
        return True

def _remove_active_client(client_id):
    """
    Unregister a client as active (disconnected).
    
    Thread-safe operation using a lock.
    """
    if not client_id:
        return
    
    # lock and remove client id
    with lock:
        active_clients.discard(client_id)
    print("")
    
def client_thread(conn, addr, shared_root, clients_root):
    """
    Handle a single client connection in a dedicated thread.
    
    This function:
    1. Receives JSON messages from the client
    2. Processes requests (HELLO, LIST, GET, PUT, etc.)
    3. Sends JSON responses back
    4. Handles file transfers with SHA-256 verification
    5. Manages client lifecycle (registration, deregistration)
    
    Request types:
    - HELLO: Register a client ID and start a session
    - LIST: List files in the shared folder
    - LIST_CLIENTS: List all other connected clients
    - LIST_CLIENT: List files in a specific client's folder
    - GET: Download a file from the shared folder
    - GET_CLIENT: Download a file from another client's folder
    - PUT: Upload a file to the shared folder
    - PUT_CLIENT: Send a file to another client's folder
    - BYE: Disconnect gracefully
    """
    conn_client_id = None
    try:
        while True:
            try:
                # Receive the next request from the client
                req: Dict[str, Any] = recv_json(conn)
            except ConnectionError:
                # Client closed the connection cleanly.
                break
            req_type = req.get("type")
            request_id = req.get("request_id", "")

            try:
                if req_type == "HELLO":
                    # Client wants to register with a client ID
                    client_id = _sanitize_client_id(req.get("client_id"))
                    
                    # Check if this ID is already in use by another client
                    if not _add_active_client(client_id):
                        send_json(conn, {
                            "type": "ERROR",
                            "request_id": request_id,
                            "message": "Client ID - " + client_id + " already in use",
                        })
                        continue
                    
                    # Create a folder for this client and send success response
                    conn_client_id = client_id
                    os.makedirs(_client_root(clients_root, client_id), exist_ok=True)
                    send_json(conn, {
                        "type": "OK",
                        "request_id": request_id,
                        "client_id": client_id,
                    })

                elif req_type == "LIST":
                    # Client wants to see files in the shared folder
                    files = safe_list_files(shared_root)
                    send_json(conn, {"type": "OK", "request_id": request_id, "files": files})

                # LIST_CLIENTS: Get list of all other connected clients
                elif req_type == "LIST_CLIENTS":
                    lst = []
                    for client in os.listdir(clients_root):
                        if os.path.isdir(os.path.join(clients_root, client)) and conn_client_id != client:
                            lst.append(client)
                            
                    send_json(conn, {"type": "OK", "request_id": request_id, "clients": lst})

                elif req_type == "LIST_CLIENT":
                    # Client wants to see files in another specific client's folder
                    target_id = _sanitize_client_id(req.get("client_id"))
                    target_root = _client_root(clients_root, target_id)
                    if not os.path.isdir(target_root):
                        send_json(conn, {
                            "type": "ERROR",
                            "request_id": request_id,
                            "message": f"Unknown client_id: {target_id}",
                        })
                        continue
                    files = safe_list_files(target_root)
                    send_json(conn, {
                        "type": "OK",
                        "request_id": request_id,
                        "client_id": target_id,
                        "files": files,
                    })

                elif req_type in {"GET", "GET_CLIENT"}:
                    # Client wants to download a file
                    # GET = from shared folder, GET_CLIENT = from another client's folder
                    filename = _sanitize_filename(req.get("name"))
                    if req_type == "GET":
                        root = shared_root
                    else:
                        target_id = _sanitize_client_id(req.get("client_id"))
                        root = _client_root(clients_root, target_id)

                    path = os.path.join(root, filename)
                    if not os.path.isfile(path):
                        send_json(conn, {
                            "type": "ERROR",
                            "request_id": request_id,
                            "message": "File not found!",
                        })
                        continue

                    # Compute file size and SHA-256 hash for verification
                    filesize = os.path.getsize(path)
                    sha256 = _sha256_file(path)

                    # Send metadata, then the file bytes
                    send_json(conn, {
                        "type": "OK",
                        "request_id": request_id,
                        "size": filesize,
                        "sha256": sha256,
                    })
                    _send_file_bytes(conn, path)

                elif req_type in {"PUT", "PUT_CLIENT"}:
                    # Client wants to upload a file
                    # PUT = to shared folder, PUT_CLIENT = to another client's folder
                    filename = _sanitize_filename(req.get("name"))
                    size = req.get("size")
                    sha_expected = req.get("sha256")
                    if not isinstance(size, int) or size < 0:
                        raise ValueError("Invalid size")
                    if not isinstance(sha_expected, str) or len(sha_expected) != 64:
                        raise ValueError("Invalid sha256")

                    if req_type == "PUT":
                        dest_root = shared_root
                    else:
                        target_id = _sanitize_client_id(req.get("client_id"))
                        dest_root = _client_root(clients_root, target_id)
                        os.makedirs(dest_root, exist_ok=True)

                    # Check if file already exists - we reject overwrites
                    final_path = os.path.join(dest_root, filename)
                    if os.path.exists(final_path):
                        send_json(conn, {
                            "type": "ERROR",
                            "request_id": request_id,
                            "message": "File already exists (overwrite rejected)",
                        })
                        continue

                    # Use a temporary .part file during upload for atomicity
                    # This way, incomplete uploads don't leave behind broken files
                    tmp_path = final_path + f".{request_id}.part"
                    send_json(conn, {"type": "OK", "request_id": request_id})

                    try:
                        # Receive the file bytes and compute SHA-256 hash
                        sha_actual = _recv_file_bytes(conn, tmp_path, size)
                        
                        # Verify the received file matches the expected hash
                        if sha_actual != sha_expected:
                            try:
                                os.remove(tmp_path)
                            except Exception:
                                pass
                            send_json(conn, {
                                "type": "ERROR",
                                "request_id": request_id,
                                "message": "SHA-256 mismatch; upload discarded",
                            })
                            continue

                        # Double-check that file doesn't already exist (race condition protection)
                        if os.path.exists(final_path):
                            try:
                                os.remove(tmp_path)
                            except Exception:
                                pass
                            send_json(conn, {
                                "type": "ERROR",
                                "request_id": request_id,
                                "message": "File already exists (overwrite rejected)",
                            })
                            continue

                        # Atomically move the temporary file to its final location
                        os.rename(tmp_path, final_path)
                        send_json(conn, {"type": "OK", "request_id": request_id})
                    finally:
                        # Best-effort cleanup if client disconnects mid-transfer.
                        if os.path.exists(tmp_path):
                            try:
                                os.remove(tmp_path)
                            except Exception:
                                pass
                    
                elif req_type == "BYE":
                    # Client wants to disconnect gracefully
                    send_json(conn, {"type": "OK", "request_id": request_id})
                    break

                else:
                    # Unknown request type
                    send_json(conn, {
                        "type": "ERROR",
                        "request_id": request_id,
                        "message": f"Unknown request type: {req_type}",
                    })
            except Exception as e:
                # Send error response to client for request-level exceptions
                send_json(conn, {
                    "type": "ERROR",
                    "request_id": request_id,
                    "message": str(e),
                })
    except Exception as e:
        # Log connection-level errors but don't crash the entire server
        # One misbehaving client shouldn't take down all other clients
        print("Client error: ", e)
    finally:
        # Clean up: unregister the client and close the socket
        _remove_active_client(conn_client_id)
        try:
            conn.close()
        except Exception:
            pass

def main():
    """
    Start the TCP file transfer server.
    
    Parses command-line arguments for host, port, and folder paths,
    then accepts incoming client connections and spawns a thread for each.
    """
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="0.0.0.0", help="Host address to bind to")
    ap.add_argument("--port", type=int, default=5001, help="Port to listen on")
    ap.add_argument("--root", default="./shared", help="Shared folder root")
    ap.add_argument("--clients-root", default="./clients", help="Per-client folder root")
    args = ap.parse_args()

    # Create necessary directories if they don't exist
    os.makedirs(args.root, exist_ok=True)
    os.makedirs(args.clients_root, exist_ok=True)

    # Create server socket and prepare to listen
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((args.host, args.port))
    srv.listen()
    
    # Print server info to console to confirm it's running
    print(f"Server listening on {args.host}:{args.port}")

    # Main server loop: accept connections and spawn handler threads
    while True:
        conn, addr = srv.accept()
        t = threading.Thread(target=client_thread, args=(conn, addr, args.root, args.clients_root), daemon=True)
        t.start()

if __name__ == "__main__":
    main()