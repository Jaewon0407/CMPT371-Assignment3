import socket
import uuid
from protocol import send_json, recv_json

# This file is for testing protocols fast in cli before gui

def main():
    host = "127.0.0.1"
    port = 5001

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((host, port))

    request_id = str(uuid.uuid4())
    send_json(sock, {"type": "LIST", "request_id": request_id})
    resp = recv_json(sock)
    print(resp)

    send_json(sock, {"type": "BYE", "request_id": str(uuid.uuid4())})
    print(recv_json(sock))

    sock.close()

if __name__ == "__main__":
    main()