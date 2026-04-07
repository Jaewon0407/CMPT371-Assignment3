import hashlib
import os
import socket
import tkinter as tk
import uuid
from tkinter import filedialog, messagebox, ttk

from protocol import recv_json, send_json


CHUNK_SIZE = 65536
SYNC_INTERVAL_MS = 3000


class FileTransferSystemGUI:
    def __init__(self):
        
        self.root = tk.Tk()
        self.root.title("File Transfer System")
        self.root.geometry("800x600")

        self.sock = None
        self.client_id = ""
        self.shared_files = []
        self.clients = []
        self.sync_after_id = None
        self.local_db_base = os.path.join(os.getcwd(), "client_db")

        self.root.grid_rowconfigure(0, weight=0)
        self.root.grid_rowconfigure(1, weight=0)
        self.root.grid_rowconfigure(2, weight=0, minsize=60)

        self.root.grid_columnconfigure(0, weight=2)
        self.root.grid_columnconfigure(1, weight=1)

        self.connection_frame()
        self.files_frame()
        self.client_frame()

        self.fn_btns_state_change("disabled")
        self.root.protocol("WM_DELETE_WINDOW", self.fn_close_window)
        self.root.mainloop()

    ## ------------------------ CONNECTION FRAME -----------------------------

    def connection_frame(self):
        conn_frame = tk.Frame(self.root, bd=2, relief="groove")

        self.lbl_host = tk.Label(conn_frame, text="Host:", font=("", 14, "bold"))
        self.lbl_host.pack(side="left", padx=5, pady=5)
        self.entry_host = tk.Entry(conn_frame, font=("", 14), width=10)
        self.entry_host.insert(0, "127.0.0.1")
        self.entry_host.pack(side="left", padx=5, pady=5)

        self.lbl_port = tk.Label(conn_frame, text="Port:", font=("", 14, "bold"))
        self.lbl_port.pack(side="left", padx=5, pady=5)
        self.entry_port = tk.Entry(conn_frame, font=("", 14), width=10)
        self.entry_port.insert(0, "5001")
        self.entry_port.pack(side="left", padx=5, pady=5)

        self.lbl_client_id = tk.Label(conn_frame, text="Client ID:", font=("", 14, "bold"))
        self.lbl_client_id.pack(side="left", padx=5, pady=5)
        self.entry_client_id = tk.Entry(conn_frame, font=("", 14), width=10)
        self.entry_client_id.insert(0, "ClientA")
        self.entry_client_id.pack(side="left", padx=5, pady=5)

        self.connect_btn = tk.Button(conn_frame, text="Connect", command=self.fn_connect)
        self.connect_btn.pack(side="left", padx=5, pady=5)

        self.disconnect_btn = tk.Button(conn_frame, text="Disconnect", command=self.fn_disconnect)
        self.disconnect_btn.pack(side="left", padx=5, pady=5)

        conn_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=10, pady=10)

    ## ------------------------ SERVER FILES FRAME -----------------------------

    def files_frame(self):
        file_frame = tk.Frame(self.root, bd=2, relief="groove")

        file_frame.grid_rowconfigure(1, weight=0)
        file_frame.grid_columnconfigure(0, weight=1)

        lbl_serverFiles = tk.Label(file_frame, text="Server Files", font=("Segoe UI", 14, "bold"))
        lbl_serverFiles.grid(row=0, column=0, columnspan=2, pady=5)

        child_frame = tk.Frame(file_frame)
        child_frame.grid(row=1, column=0, sticky="nsew")

        self.files_listBox = tk.Listbox(child_frame, height=7, selectmode=tk.SINGLE, selectborderwidth=2)
        self.files_listBox.pack(side="left", fill="both", expand=True, padx=(10, 0))

        scrollbar = ttk.Scrollbar(child_frame, orient="vertical", style="Custom.Vertical.TScrollbar")
        scrollbar.pack(side="right", fill="y", padx=(0, 10))

        scrollbar.config(command=self.files_listBox.yview)
        self.files_listBox.config(yscrollcommand=scrollbar.set)

        btn_frame = tk.Frame(file_frame)
        btn_frame.grid(row=2, column=0, sticky="ew", pady=5)

        btn_frame.grid_columnconfigure(0, weight=1)
        btn_frame.grid_columnconfigure(1, weight=1)
        btn_frame.grid_columnconfigure(2, weight=1)

        self.refresh_btn = tk.Button(btn_frame, text="Refresh", command=self.fn_refresh)
        self.refresh_btn.grid(row=0, column=0, padx=10, pady=10)

        self.upload_btn = tk.Button(btn_frame, text="Upload", command=self.fn_upload_file)
        self.upload_btn.grid(row=0, column=1, padx=10, pady=10)

        self.download_btn = tk.Button(btn_frame, text="Download", command=self.fn_download_file)
        self.download_btn.grid(row=0, column=2, padx=10, pady=10)

        file_frame.grid(row=1, column=0, sticky="nsew", padx=15, pady=15)

    ## ------------------------ CLIENT NAME FRAME -----------------------------

    def client_frame(self):
        frame = tk.Frame(self.root, bd=2, relief="groove")

        frame.grid_rowconfigure(1, weight=0)
        frame.grid_columnconfigure(0, weight=1)

        lbl_connected_clients = tk.Label(frame, text="Connected Clients", font=("", 14, "bold"))
        lbl_connected_clients.grid(row=0, column=0, pady=5)

        child_frame = tk.Frame(frame)
        child_frame.grid(row=1, column=0, sticky="nsew")

        self.clients_listBox = tk.Listbox(child_frame, height=7, selectmode=tk.SINGLE, selectborderwidth=2)
        self.clients_listBox.pack(side="left", fill="both", expand=True, padx=(10, 0))

        scrollbar = ttk.Scrollbar(child_frame, orient="vertical", style="Custom.Vertical.TScrollbar")
        scrollbar.pack(side="right", fill="y", padx=(0, 10))

        scrollbar.config(command=self.clients_listBox.yview)
        self.clients_listBox.config(yscrollcommand=scrollbar.set)

        btn_frame = tk.Frame(frame)
        btn_frame.grid(row=2, column=0, pady=5)

        self.send_file_to_client_btn = tk.Button(btn_frame, text="Send File", command=self.fn_send_client_file)
        self.send_file_to_client_btn.grid(row=0, column=0, padx=10, pady=10)

        frame.grid(row=1, column=1, sticky="nsew", padx=15, pady=15)

    ## ========================= Helpers ==============================

    def _new_request_id(self):
        return str(uuid.uuid4())

    def _local_db_dir(self):
        return os.path.join(self.local_db_base, self.client_id)

    def _local_download_dir(self):
        return self._local_db_dir()

    def _compute_sha_and_size(self, path):
        h = hashlib.sha256()
        total = 0
        with open(path, "rb") as f:
            while True:
                ch = f.read(CHUNK_SIZE)
                if not ch:
                    break
                total += len(ch)
                h.update(ch)
        return total, h.hexdigest()

    def _recv_file_to_path(self, out_path, total_bytes):
        remaining = total_bytes
        downloaded = 0
        h = hashlib.sha256()

        with open(out_path, "wb") as f:
            while remaining > 0:
                ch = self.sock.recv(min(CHUNK_SIZE, remaining))
                if not ch:
                    raise ConnectionError("Socket closed while receiving file bytes")
                f.write(ch)
                h.update(ch)
                downloaded += len(ch)
                remaining -= len(ch)
                

        return h.hexdigest()

    def _send_file_from_path(self, path, total_bytes):
        sent = 0
        with open(path, "rb") as f:
            while sent < total_bytes:
                ch = f.read(CHUNK_SIZE)
                if not ch:
                    break
                self.sock.sendall(ch)
                sent += len(ch)
                

    def _start_sync_loop(self):
        self._stop_sync_loop()
        self.sync_after_id = self.root.after(1500, self._sync_inbox_loop)

    def _stop_sync_loop(self):
        if self.sync_after_id is not None:
            self.root.after_cancel(self.sync_after_id)
            self.sync_after_id = None

    def _sync_inbox_loop(self):
        try:
            if self.sock and self.client_id:
                self._sync_inbox_once()
                
        except Exception:
            # Keep GUI responsive even if one sync tick fails.
            pass
        finally:
            if self.sock and self.client_id:
                self.sync_after_id = self.root.after(SYNC_INTERVAL_MS, self._sync_inbox_loop)
            else:
                self.sync_after_id = None

    def _sync_inbox_once(self):
        send_json(
            self.sock,
            {
                "type": "LIST_CLIENT",
                "request_id": self._new_request_id(),
                "client_id": self.client_id,
            },
        )
        resp = recv_json(self.sock)
        if resp.get("type") != "OK":
            return

        os.makedirs(self._local_db_dir(), exist_ok=True)

        new_downloads = 0
        files = resp.get("files", [])
        for item in files:
            name = item.get("name")
            if not isinstance(name, str) or not name:
                continue

            local_path = os.path.join(self._local_db_dir(), name)
            if os.path.exists(local_path):
                continue

            send_json(
                self.sock,
                {
                    "type": "GET_CLIENT",
                    "request_id": self._new_request_id(),
                    "client_id": self.client_id,
                    "name": name,
                },
            )
            meta = recv_json(self.sock)
            if meta.get("type") != "OK":
                continue

            size = int(meta.get("size", 0))
            sha_expected = meta.get("sha256", "")

            tmp_path = local_path + ".part"
            try:
                sha_actual = self._recv_file_to_path(tmp_path, size)
                if sha_actual != sha_expected:
                    raise RuntimeError("SHA-256 mismatch while syncing inbox file")
                os.replace(tmp_path, local_path)
                new_downloads += 1
            except Exception:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)

        if new_downloads > 0:
            messagebox.showinfo(
                "Incoming Files",
                f"{new_downloads} new file(s) saved to {self._local_db_dir()}",
            )

    ## =================== BUTTON FUNCTIONALITIES =====================

    ## ------------------- Connect to server --------------------------
    def fn_connect(self):
        host = self.entry_host.get().strip()
        client_id = self.entry_client_id.get().strip()

        try:
            port = int(self.entry_port.get().strip())
        except ValueError:
            messagebox.showerror("Connection Error", "Port must be a valid integer")
            return

        if not host:
            messagebox.showerror("Connection Error", "Host is required")
            return
        if not client_id:
            messagebox.showerror("Connection Error", "Client ID is required")
            return

        if self.sock:
            messagebox.showinfo("Connection Status", f"Already connected as {self.client_id}")
            return

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((host, port))

            send_json(
                sock,
                {
                    "type": "HELLO",
                    "request_id": self._new_request_id(),
                    "client_id": client_id,
                },
            )
            response = recv_json(sock)

            if response.get("type") != "OK":
                sock.close()
                messagebox.showerror("Connection Error", response.get("message", "HELLO failed"))
                return

            self.sock = sock
            self.client_id = client_id
            os.makedirs(self._local_db_dir(), exist_ok=True)

            self.fn_btns_state_change("normal")
            self.fn_refresh(show_popup=False)
            self._start_sync_loop()

            messagebox.showinfo(
                "Connection Status",
                f"Connected as client '{client_id}'. Local DB folder: {self._local_db_dir()}",
            )
        except Exception as e:
            messagebox.showerror("Connection Error", str(e))

    ## ------------------- Disconnect from server --------------------------

    def fn_disconnect(self, ask_confirmation=True, show_message=True):
        if ask_confirmation and not messagebox.askyesno("Disconnect from Server", "Do you want to disconnect?"):
            return

        self._stop_sync_loop()

        try:
            if self.sock:
                try:
                    send_json(self.sock, {"type": "BYE", "request_id": self._new_request_id()})
                    recv_json(self.sock)
                except Exception:
                    pass
                self.sock.close()
        finally:
            self.sock = None
            self.client_id = ""
            self.shared_files = []
            self.clients = []

            self.fn_btns_state_change("disabled")
            self.files_listBox.delete(0, tk.END)
            self.clients_listBox.delete(0, tk.END)

            if show_message:
                messagebox.showinfo("Disconnected", "Disconnected from server")

    def fn_close_window(self):
        self.fn_disconnect(ask_confirmation=False, show_message=False)
        self.root.destroy()

    ## ------------------- Refresh files and clients list --------------------------

    def fn_refresh(self, show_popup=True):
        if not self.sock:
            messagebox.showerror("Error", "Not connected to server, reconnect first")
            self.fn_btns_state_change("disabled")
            return

        try:
            send_json(self.sock, {"type": "LIST", "request_id": self._new_request_id()})
            resp = recv_json(self.sock)

            if resp.get("type") != "OK":
                messagebox.showerror("Error", resp.get("message", "Failed to refresh files list"))
                return

            self.shared_files = resp.get("files", [])
            self.files_listBox.delete(0, tk.END)
            for file_item in self.shared_files:
                self.files_listBox.insert(tk.END, f"{file_item['name']} ({file_item['size']} bytes)")

            send_json(self.sock, {"type": "LIST_CLIENTS", "request_id": self._new_request_id()})
            resp = recv_json(self.sock)
            if resp.get("type") != "OK":
                messagebox.showerror("Error", resp.get("message", "Failed to refresh clients list"))
                return

            self.clients = sorted(resp.get("clients", []), key=lambda x: x.lower())
            
            self.clients_listBox.delete(0, tk.END)
            for client in self.clients:
                self.clients_listBox.insert(tk.END, client)

            if show_popup:
                messagebox.showinfo("Refresh", "Files and clients list updated")
        except Exception as e:
            messagebox.showerror("Error", f"Could not refresh lists: {e}")

    ## ------------------- Upload file to server --------------------------

    def fn_upload_file(self):
        if not self.sock:
            messagebox.showerror("Error", "Not connected to server, reconnect first")
            return

        chosen_file = filedialog.askopenfilename()
        if not chosen_file:
            return

        try:
            name = os.path.basename(chosen_file)
            size, h_hex = self._compute_sha_and_size(chosen_file)

            send_json(
                self.sock,
                {
                    "type": "PUT",
                    "request_id": self._new_request_id(),
                    "name": name,
                    "size": size,
                    "sha256": h_hex,
                },
            )
            resp = recv_json(self.sock)

            if resp.get("type") != "OK":
                messagebox.showerror("Error", resp.get("message", "Failed to upload file"))
                return

            self._send_file_from_path(chosen_file, size)
            final_resp = recv_json(self.sock)

            if final_resp.get("type") == "OK":
                messagebox.showinfo("Upload", "File upload successful")
                self.fn_refresh(show_popup=False)
            else:
                messagebox.showerror("Error", final_resp.get("message", "Failed to upload file"))
        except Exception as e:
            messagebox.showerror("Error", f"Failed to upload file: {e}")

    ## ------------------- Download file from server --------------------------

    def fn_download_file(self):
        if not self.sock:
            messagebox.showerror("Error", "Not connected to server, reconnect first")
            return

        selected_file = self.files_listBox.curselection()
        if not selected_file:
            messagebox.showerror("Error", "No shared file selected")
            return

        selected_idx = selected_file[0]
        selected_filename = self.shared_files[selected_idx]["name"]
        out_dir = self._local_download_dir()
        os.makedirs(out_dir, exist_ok=True)

        try:
            send_json(
                self.sock,
                {
                    "type": "GET",
                    "request_id": self._new_request_id(),
                    "name": selected_filename,
                },
            )
            resp = recv_json(self.sock)

            if resp.get("type") != "OK":
                messagebox.showerror("Server Error", resp.get("message", "GET failed"))
                return

            filesize = int(resp["size"])
            sha_expected = resp["sha256"]

            downloaded_filepath = os.path.join(out_dir, selected_filename)
            tmp_path = downloaded_filepath + ".part"

            sha_actual = self._recv_file_to_path(tmp_path, filesize)

            if sha_expected != sha_actual:
                os.remove(tmp_path)
                messagebox.showerror("Error", "Failed to download file (SHA-256 mismatch)")
                return

            os.replace(tmp_path, downloaded_filepath)
            messagebox.showinfo("Download", f"File saved to {downloaded_filepath}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to download file: {e}")

    ## ------------------- Send file to client --------------------------

    def fn_send_client_file(self):
        if not self.sock:
            messagebox.showerror("Error", "Not connected to server, reconnect first")
            return

        selected = self.clients_listBox.curselection()
        if not selected:
            messagebox.showerror("Error", "Select a destination client first")
            return

        target_client = self.clients[selected[0]]
        if target_client == self.client_id:
            messagebox.showerror("Error", "Select another client (not yourself)")
            return

        source_dir = os.path.abspath(self._local_db_dir())
        os.makedirs(source_dir, exist_ok=True)

        chosen_file = filedialog.askopenfilename(
            title="Select file from your client folder",
            initialdir=source_dir,
        )
        if not chosen_file:
            return

        chosen_file = os.path.abspath(chosen_file)
        try:
            within_source_dir = os.path.commonpath([source_dir, chosen_file]) == source_dir
        except ValueError:
            within_source_dir = False
        if not within_source_dir:
            messagebox.showerror("Error", f"You can only send files from {source_dir}")
            return
        if not os.path.isfile(chosen_file):
            messagebox.showerror("Error", "Selected path is not a file")
            return

        try:
            name = os.path.basename(chosen_file)
            size, h_hex = self._compute_sha_and_size(chosen_file)

            send_json(
                self.sock,
                {
                    "type": "PUT_CLIENT",
                    "request_id": self._new_request_id(),
                    "client_id": target_client,
                    "name": name,
                    "size": size,
                    "sha256": h_hex,
                },
            )
            resp = recv_json(self.sock)

            if resp.get("type") != "OK":
                messagebox.showerror("Error", resp.get("message", "Failed to send file to client"))
                return

            self._send_file_from_path(chosen_file, size)
            final_resp = recv_json(self.sock)

            if final_resp.get("type") != "OK":
                messagebox.showerror("Error", final_resp.get("message", "Failed to send file to client"))
                return

            messagebox.showinfo(
                "Send Complete",
                f"File sent to {target_client}. It will sync into that client's local DB folder when connected.",
            )
            self.fn_refresh(show_popup=False)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to send file to client: {e}")

    # disable/enable buttons until connected
    def fn_btns_state_change(self, st):
        self.refresh_btn.config(state=st)
        self.upload_btn.config(state=st)
        self.download_btn.config(state=st)
        self.send_file_to_client_btn.config(state=st)
        self.disconnect_btn.config(state=st)

        if st == "disabled":
            connect_btn_state = "normal"
        else:
            connect_btn_state = "disabled"
        self.connect_btn.config(state=connect_btn_state)


FileTransferSystemGUI()