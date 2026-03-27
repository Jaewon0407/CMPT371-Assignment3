import json
import socket
from typing import Any, Dict

MAX_FRAME_BYTES = 10 * 1024 * 1024  # 10 MB safety cap for JSON frames

def recv_exact(sock: socket.socket, n: int) -> bytes:
    """Receive exactly n bytes or raise ConnectionError if socket closes early."""
    chunks = []
    bytes_recd = 0
    while bytes_recd < n:
        chunk = sock.recv(n - bytes_recd)
        if not chunk:
            raise ConnectionError("Socket closed while receiving data")
        chunks.append(chunk)
        bytes_recd += len(chunk)
    return b"".join(chunks)

def send_json(sock: socket.socket, obj: Dict[str, Any]) -> None:
    """Send one length-prefixed JSON message."""
    data = json.dumps(obj).encode("utf-8")
    length = len(data).to_bytes(4, "big")
    sock.sendall(length + data)

def recv_json(sock: socket.socket) -> Dict[str, Any]:
    """Receive one length-prefixed JSON message."""
    length_bytes = recv_exact(sock, 4)
    length = int.from_bytes(length_bytes, "big")
    if length < 0 or length > MAX_FRAME_BYTES:
        raise ValueError(f"Invalid frame length: {length}")
    data = recv_exact(sock, length)
    return json.loads(data.decode("utf-8"))