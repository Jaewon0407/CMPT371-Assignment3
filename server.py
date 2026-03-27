import argparse
import os
import socket
import threading
from typing import Dict, Any

from protocol import send_json, recv_json
import hashlib

def safe_list_files(root: str):
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

def client_thread(conn: socket.socket, addr, root: str):
    try:
        while True:
            req: Dict[str, Any] = recv_json(conn)
            req_type = req.get("type")
            request_id = req.get("request_id", "")

            if req_type == "LIST":
                files = safe_list_files(root)
                send_json(conn, {"type": "OK", "request_id": request_id, "files": files})

            elif req_type == "GET":
                try:
                    # GET code here
                    # get filename
                    filename = req.get("name")
                    path = os.path.join(root, filename)
    
                    # check if exists 
                    if not os.path.isfile(path):
                        send_json(conn, {"type": "ERROR", "request_id": request_id, "message": "File not found!"})
                        continue
                    
                    # --> calculate size 
                    filesize = os.path.getsize(path)
                
                    # --> calculate SHA256
                    calHash = hashlib.sha256()
                    with open (path, "rb") as f:
                        while True:
                            # read file in chunks
                            ch = f.read(65536)
                            if not ch:
                                break
                            calHash.update(ch)
                    
                    # send ok + size + SHA256 (client knows what to expect)
                    send_json(conn, {
                        "type": "OK",
                        "request_id": request_id,
                        "size": filesize,
                        "sha256": calHash.hexdigest()
                    })
                
                    # send file bytes
                    with open (path, "rb") as f:
                        while True:
                            # read file in chunks
                            ch = f.read(65536)
                            if not ch:
                                break
                            conn.sendall(ch)
                except Exception as e:
                    print("Error during GET request: ", e)
                    
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
        # In the real assignment you can log this to console.
        # Don't crash the whole server because one client misbehaved.
        print("Client error: ", e)
    finally:
        try:
            conn.close()
        except Exception:
            pass

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=5001)
    ap.add_argument("--root", default="./shared")
    args = ap.parse_args()

    os.makedirs(args.root, exist_ok=True)

    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((args.host, args.port))
    srv.listen()
    
    # print server info to console ensuring server connected
    print(f"Server listening on {args.host}:{args.port}")

    while True:
        conn, addr = srv.accept()
        t = threading.Thread(target=client_thread, args=(conn, addr, args.root), daemon=True)
        t.start()

if __name__ == "__main__":
    main()