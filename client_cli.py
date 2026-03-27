import socket
import uuid
from protocol import send_json, recv_json
import hashlib
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

    send_json(sock, {"type": "GET", "request_id": str(uuid.uuid4()), "name": "test1.txt"})
    resp = recv_json(sock)
    if(resp["type"] == "OK"):
        filesize = resp["size"]
        sha_expected = resp["sha256"]
        
        # read all the bits in the file
        downloaded_sha = hashlib.sha256()
        
        with open ("downloaded_test.txt", "wb") as f:
            total = filesize
            while total > 0:
                ch = sock.recv(min(65536, total))
                if not ch:
                    break
                total -= len(ch)
                f.write(ch)
                downloaded_sha.update(ch)
                
        # compare sha, if equal - transfer succesful
        if(sha_expected == downloaded_sha.hexdigest()):
            print("File download successfully completed")
        else:
            print("File download failed")
    else:
        print("Server error: ", resp.get("message")) # server error       

    send_json(sock, {"type": "BYE", "request_id": str(uuid.uuid4())})
    print(recv_json(sock))

    sock.close()

if __name__ == "__main__":
    main()