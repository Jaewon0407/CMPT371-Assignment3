import argparse
import os
import socket
import threading
from typing import Dict, Any

from protocol import send_json, recv_json
import hashlib

CHUNK_SIZE = 65536
active_clients = set()
lock = threading.Lock()

def _sanitize_filename(name):
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
    if not isinstance(client_id, str) or not client_id:
        raise ValueError("Missing client_id")
    if len(client_id) > 64:
        raise ValueError("client_id too long")
    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" )
    if any(ch not in allowed for ch in client_id):
        raise ValueError("client_id may only contain letters, digits, '_' or '-'")
    return client_id

def _client_root(clients_root, client_id):
    # client_id is already sanitized to forbid separators.
    path = os.path.join(clients_root, client_id)
    abs_root = os.path.abspath(clients_root)
    abs_path = os.path.abspath(path)
    if os.path.commonpath([abs_root, abs_path]) != abs_root:
        raise ValueError("Invalid client_id")
    return path

def _sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            ch = f.read(CHUNK_SIZE)
            if not ch:
                break
            h.update(ch)
    return h.hexdigest()

def _send_file_bytes(conn, path):
    with open(path, "rb") as f:
        while True:
            ch = f.read(CHUNK_SIZE)
            if not ch:
                break
            conn.sendall(ch)

def _recv_file_bytes(conn, dest_path, total_bytes):
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
    with lock:
        if client_id in active_clients:
            return False
        
        # add client
        active_clients.add(client_id)
        return True

def _remove_active_client(client_id):
    if not client_id:
        return
    
    # lock and remove client id
    with lock:
        active_clients.discard(client_id)
    print("")
    
def client_thread(conn, addr, shared_root, clients_root):
    conn_client_id = None
    try:
        while True:
            try:
                req: Dict[str, Any] = recv_json(conn)
            except ConnectionError:
                # Client closed the connection cleanly.
                break
            req_type = req.get("type")
            request_id = req.get("request_id", "")

            try:
                if req_type == "HELLO":
                    client_id = _sanitize_client_id(req.get("client_id"))
                    
                    if not _add_active_client(client_id):
                        send_json(conn, {
                            "type": "ERROR",
                            "request_id": request_id,
                            "message": "Client ID - " + client_id + " already in use",
                        })
                        continue
                    
                    conn_client_id = client_id
                    os.makedirs(_client_root(clients_root, client_id), exist_ok=True)
                    send_json(conn, {
                        "type": "OK",
                        "request_id": request_id,
                        "client_id": client_id,
                    })

                elif req_type == "LIST":
                    files = safe_list_files(shared_root)
                    send_json(conn, {"type": "OK", "request_id": request_id, "files": files})

                # list clients
                elif req_type == "LIST_CLIENTS":
                    lst = []
                    for client in os.listdir(clients_root):
                        if os.path.isdir(os.path.join(clients_root, client)):
                            lst.append(client)
                            
                    send_json(conn, {"type": "OK", "request_id": request_id, "clients": lst})

                elif req_type == "LIST_CLIENT":
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

                    filesize = os.path.getsize(path)
                    sha256 = _sha256_file(path)

                    send_json(conn, {
                        "type": "OK",
                        "request_id": request_id,
                        "size": filesize,
                        "sha256": sha256,
                    })
                    _send_file_bytes(conn, path)

                elif req_type in {"PUT", "PUT_CLIENT"}:
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

                    final_path = os.path.join(dest_root, filename)
                    if os.path.exists(final_path):
                        send_json(conn, {
                            "type": "ERROR",
                            "request_id": request_id,
                            "message": "File already exists (overwrite rejected)",
                        })
                        continue

                    tmp_path = final_path + f".{request_id}.part"
                    send_json(conn, {"type": "OK", "request_id": request_id})

                    try:
                        sha_actual = _recv_file_bytes(conn, tmp_path, size)
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
                    send_json(conn, {"type": "OK", "request_id": request_id})
                    break

                else:
                    send_json(conn, {
                        "type": "ERROR",
                        "request_id": request_id,
                        "message": f"Unknown request type: {req_type}",
                    })
            except Exception as e:
                send_json(conn, {
                    "type": "ERROR",
                    "request_id": request_id,
                    "message": str(e),
                })
    except Exception as e:
        # In the real assignment you can log this to console.
        # Don't crash the whole server because one client misbehaved.
        print("Client error: ", e)
    finally:
        _remove_active_client(conn_client_id)
        try:
            conn.close()
        except Exception:
            pass

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=5001)
    ap.add_argument("--root", default="./shared", help="Shared folder root")
    ap.add_argument("--clients-root", default="./clients", help="Per-client folder root")
    args = ap.parse_args()

    os.makedirs(args.root, exist_ok=True)
    os.makedirs(args.clients_root, exist_ok=True)

    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((args.host, args.port))
    srv.listen()
    
    # print server info to console ensuring server connected
    print(f"Server listening on {args.host}:{args.port}")

    while True:
        conn, addr = srv.accept()
        t = threading.Thread(target=client_thread, args=(conn, addr, args.root, args.clients_root), daemon=True)
        t.start()

if __name__ == "__main__":
    main()