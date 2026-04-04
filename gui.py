import tkinter as tk
from tkinter import messagebox
from tkinter import ttk, filedialog
#import style_gui as style

import hashlib
import socket
import os 
import uuid 
import threading
import queue

from protocol import send_json, recv_exact, recv_json
from server import CHUNK_SIZE

class FileTransferSystemGUI:
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("File Transfer System")
        self.root.geometry('800x600')
        
        self.selected_files = []
        self.sock = None
        
        self.root.grid_rowconfigure(0, weight=0) # connection frame
        self.root.grid_rowconfigure(1, weight=0) # files and clients frame
        self.root.grid_rowconfigure(2, weight=0, minsize=60) # progress frame
        
        self.root.grid_columnconfigure(0, weight=2)
        self.root.grid_columnconfigure(1, weight=1)
        
        self.connection_frame()
        self.files_frame()
        self.client_frame()
        self.progress_frame()
        # self.log_frame()
        
        self.fn_btns_state_change('disabled')
        
        self.root.mainloop()
        
## ------------------------ CONNECTION FRAME -----------------------------

    def connection_frame(self):
        
        conn_frame = tk.Frame(self.root)
        
        ## host
        self.lbl_host = tk.Label(conn_frame, text='Host:')
        self.lbl_host.pack(side='left', padx=5, pady=5)
        
        self.entry_host = tk.Entry(conn_frame)
        self.entry_host.insert('0', '127.0.0.1')
        self.entry_host.pack(side='left', padx=5, pady=5)
        
        ## port
        self.lbl_port = tk.Label(conn_frame, text='Port:')
        self.lbl_port.pack(side='left', padx=5, pady=5)
        
        self.entry_port = tk.Entry(conn_frame)
        self.entry_port.insert(0, '5001')
        self.entry_port.pack(side='left', padx=5, pady=5)
        
        ## connect button
        self.connect_btn = tk.Button(conn_frame, text='Connect', command=self.fn_connect)
        self.connect_btn.pack(side='left', padx=5, pady=5)
        
        # diconnect button
        self.disconnect_btn = tk.Button(conn_frame, text='Disconnect', command=self.fn_disconnect)
        self.disconnect_btn.pack(side='left', padx=5, pady=5)
        
        conn_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=10, pady=10)
  
## ------------------------ SERVER FILES FRAME -----------------------------
   
    def files_frame(self):
        file_frame = tk.Frame(self.root)
        
        file_frame.grid_rowconfigure(1, weight=0)
        file_frame.grid_columnconfigure(0, weight=1)

        lbl_serverFiles = tk.Label(file_frame, text='Files', font=('Arial', 16))
        lbl_serverFiles.grid(row=0, column=0, columnspan=2, pady=5)
        
        # frame for files
        child_frame = tk.Frame(file_frame)
        child_frame.grid(row=1, column=0, sticky='nsew')
        
        # list of files on server
        self.files_listBox = tk.Listbox(child_frame, height=5)
        self.files_listBox.pack(side='left', fill='both', expand=True)
        
        # scrollbar for files listbox
        scrollbar = ttk.Scrollbar(child_frame, orient='vertical', style='Custom.Vertical.TScrollbar')
        scrollbar.pack(side='right', fill='y') 
               
        scrollbar.config(command=self.files_listBox.yview)
        self.files_listBox.config(yscrollcommand=scrollbar.set)
        
        # btn frame for file actions
        btn_frame = tk.Frame(file_frame)
        btn_frame.grid(row=2, column=0, sticky="ew", pady=5)
        
        btn_frame.grid_columnconfigure(0, weight=1)
        btn_frame.grid_columnconfigure(1, weight=1)
        btn_frame.grid_columnconfigure(2, weight=1)
        
        # btn to refresh files list
        self.refresh_btn = tk.Button(btn_frame, text='Refresh', command=self.fn_refresh)
        self.refresh_btn.grid(row=0, column=0, padx=10, pady=10)
        
        #btn to upload files 
        self.upload_btn = tk.Button(btn_frame, text='Upload', command=self.fn_upload_file)
        self.upload_btn.grid(row=0, column=1, padx=10, pady=10)
        
        # btn to download files
        self.download_btn = tk.Button(btn_frame, text='Download', command=self.fn_download_file)
        self.download_btn.grid(row=0, column=2, padx=10, pady=10)
        
        file_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        
## ------------------------ CLIENT NAME FRAME -----------------------------

    def client_frame(self):
        frame = tk.Frame(self.root)
        
        frame.grid_rowconfigure(1, weight=0)
        frame.grid_columnconfigure(0, weight=1)
        
        lbl_connected_clients = tk.Label(frame, text='Connected Clients', font=('Arial', 14))
        lbl_connected_clients.grid(row=0, column=0, pady=5)
        
        child_frame = tk.Frame(frame)
        child_frame.grid(row=1, column=0, sticky='nsew')
        
        # listbox of clients
        self.clients_listBox = tk.Listbox(child_frame, height=5)
        self.clients_listBox.pack(side='left', fill='both', expand=True)
        
        
        scrollbar = ttk.Scrollbar(child_frame, orient='vertical', style='Custom.Vertical.TScrollbar')
        scrollbar.pack(side='right', fill='y') 
        
        scrollbar.config(command=self.clients_listBox.yview)
        self.clients_listBox.config(yscrollcommand=scrollbar.set)
        
        btn_frame = tk.Frame(frame)
        btn_frame.grid(row=2, column=0, pady=5)
        
        self.send_file_to_client_btn = tk.Button(btn_frame, text='Send File', command=self.fn_send_client_file)
        self.send_file_to_client_btn.grid(row=0, column=0, padx=10, pady=10)
        
        frame.grid(row=1, column=1, sticky="nsew", padx=10, pady=10)
   
## ------------------------ PROGRESS FRAME -----------------------------
    def progress_frame(self):
        frame = tk.Frame(self.root)
         
        lbl_progress = tk.Label(frame, text="Progress", font=('Arial', 16))
        lbl_progress.pack(padx=10, pady=10)
        
        self.progress_bar = ttk.Progressbar(frame, length=600)
        self.progress_bar.pack(padx=5, pady=5)
        
        frame.grid(row=2, column=0, columnspan=2, sticky="ew", padx=10, pady=10)
        
## ------------------------ LOG FRAME -----------------------------

     
## ----------------------------------------------------------------
## ----------------------------------------------------------------
## =================== BUTTON FUNCTIONALITIES =====================

## ------------------- Connect to server --------------------------
    def fn_connect(self):
        host = self.entry_host.get()
        port = int(self.entry_port.get())
        
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((host, port))
            
            # send HELLO message
            request_id = str(uuid.uuid4())
            client_id = str(uuid.uuid4())
            send_json(self.sock, {"type": "HELLO", "request_id": request_id, "client_id": client_id})
            resp = recv_json(self.sock)
            
            if resp.get("type") != "OK":
                print(resp)
                messagebox.showerror("Connection Error", "HELO failed") 
                return
            
            messagebox.showinfo("Connection Status", "Connected to server successfully!")
            
            # Enable disabled buttons
            self.fn_btns_state_change("normal")
            
            ## refresh files and clients listbox
            self.fn_refresh()
            
            
        except Exception as e:
            messagebox.showerror("Connection Error") 
        
    
## ------------------- Disconnect from server --------------------------
   
    def fn_disconnect(self):
        if messagebox.askyesno("Disconnect from Server", "Do you want to disconnect"):
            # notify server
            try:
                if self.sock:
                    request_id = str(uuid.uuid4())
                    send_json(self.sock, {'type': 'BYE', 'request_id': request_id})
                    
                    response = recv_json(self.sock)
                    
                    self.sock.close()
                    self.sock = None
                    
                    self.fn_btns_state_change('disabled')
                    self.files_listBox.delete(0, tk.END)
                    self.clients_listBox.delete(0, tk.END)
                    self.progress_bar["value"] = 0
                    messagebox.showinfo("Disconnected from server")
                    
            except Exception as e:
                messagebox.showerror("Error", "Error diconnecting from server")
                    
            #self.root.destroy()

## ------------------- Refresh files and clients list --------------------------
## ------------------- TO-DO: refresh client lists
          
    def fn_refresh(self):
        # if not connected, show error and re-connect
        if not self.sock:
            messagebox.showerror("Error", "Not connected to server, re-connect")
            self.fn_btns_state_change('disabled')
            return
        
        # if connected
        try:
            # send LIST request
            request_id = str(uuid.uuid4())
            send_json(self.sock, {"type": "LIST", "request_id": request_id})
            
            resp = recv_json(self.sock)
            
            if(resp.get("type") == 'OK'):
                resp_files = resp.get("files")
                
                # clear files listbox and insert in listbox
                self.files_listBox.delete(0, tk.END)
                
                # insert files in files listbox
                for file in resp_files:
                    self.files_listBox.insert(tk.END, file["name"] + " " + str(file["size"]) + " bytes")
            
            else:
                messagebox.showerror("Error", "Failed to refresh files list")
            # -------------------------------------------------------------
            
            # refresh client list
            send_json(self.sock, {"type": "LIST_CLIENTS", "request_id": str(uuid.uuid4())})
            resp = recv_json(self.sock)
            
            if(resp.get("type") == 'OK'):
                resp_clients = resp.get("clients")
                
                # clear files listbox and insert in listbox
                self.clients_listBox.delete(0, tk.END)
                
                # insert files in files listbox
                for client in resp_clients:
                    self.clients_listBox.insert(tk.END, client)
            
            else:
                messagebox.showerror("Error", "Failed to refresh clients list")
            ####### =============================
            
        except Exception as e:
            messagebox.showerror("Error", "Could not refresh connected clients and files in server!")
            
## ------------------- Upload file to server --------------------------       
        
    def fn_upload_file(self):
        if not self.sock:
            messagebox.showerror("Error", "Not connected to server, re-connect")
            self.fn_connect()
            return
        
        # if no error, choose file
        chosen_file = filedialog.askopenfilename()
        
        # if no chosen file, return
        if not chosen_file:
            return
        
        try:
            name = os.path.basename(chosen_file)
            size = os.path.getsize(chosen_file)
            
            # compute sha
            h = hashlib.sha256()
            with open(chosen_file, "rb") as f:
                while True:
                    ch = f.read(CHUNK_SIZE)
                    if not ch:
                        break
                    h.update(ch)
            h_hex = h.hexdigest()
            
            # send PUT request
            request_id = str(uuid.uuid4())
            
            send_json(self.sock, {"type": "PUT", "request_id": request_id, "name": name, "size": size, "sha256": h_hex})
            resp = recv_json(self.sock)
            
            if resp.get("type") != "OK":
                messagebox.showerror("Error", "Failed to upload file")
                return
            
            
            with open(chosen_file, "rb") as f:
                sent = 0
                while sent < size:
                    ch = f.read(CHUNK_SIZE)
                    if not ch:
                        break
                    self.sock.sendall(ch)
                    sent += len(ch)
                    
                    self.progress_bar["value"] = (sent/ size) * 100
                    self.root.update_idletasks()
                    
            resp = recv_json(self.sock)
            self.progress_bar["value"] = 0       
            
            if resp.get("type") == "OK":
                messagebox.showinfo("File upload successful")
                self.fn_refresh()
            else:
                messagebox.showerror("Error", "Failed to upload file")
            
            
            # upload file
            
        except Exception as e:
            messagebox.showerror("Error", "Failed to upload file" + str(e))

## ------------------- Download file from server --------------------------
        
    def fn_download_file(self):
        if not self.sock:
            messagebox.showerror("Error", "Not connected to server, re-connect")
            self.fn_connect()
            return
        
        selected_file = self.files_listBox.curselection()
        if not selected_file:
            messagebox.showerror("Error", "No file selected")
            return
        
        # 0-based index
        #print(self.files_listBox.get(selected_file[0]))
        selected_filename = self.files_listBox.get(selected_file[0]).rsplit(" ", 2)[0]
         
        ##
        try:
            send_json(self.sock, {"type": "GET", "request_id": str(uuid.uuid4()), "name": selected_filename})
            resp = recv_json(self.sock)
            if(resp["type"] == "OK"):
                filesize = resp["size"]
                sha_expected = resp["sha256"]
                
                # read all the bits in the file
                downloaded_sha = hashlib.sha256()
                
                os.makedirs("downloads", exist_ok=True)
                
                downloaded_filepath = os.path.join("downloads", selected_filename)
                with open (downloaded_filepath, "wb") as f:
                    total = filesize
                    while total > 0:
                        ch = self.sock.recv(min(65536, total))
                        if not ch:
                            break
                        total -= len(ch)
                        f.write(ch)
                        downloaded_sha.update(ch)
                        
                        # update progress bar
                        self.progress_bar["value"] = ((filesize - total)/ filesize) * 100
                        self.root.update_idletasks()
                
                # reset progress bar
                self.progress_bar["value"] = 0       
                # compare sha, if equal - transfer succesful
                if(sha_expected == downloaded_sha.hexdigest()):
                    messagebox.showinfo("File download successfully completed")
                else:
                    messagebox.showerror("Error", "Failed to download the file")
            else:
                messagebox.showerror("Server error: ", resp.get("message")) # server error  
                 
        except Exception as e:
            messagebox.showerror("Error", "Failed to download the file")
            return    
       

## ------------------- Send file to client --------------------------
      
    def fn_send_client_file(self):
        if not self.sock:
            messagebox.showerror("Error", "Not connected to server, re-connect")
            self.fn_connect()
            return
        
        
        print('')
        

    # disable/ enable buttons until connected
    def fn_btns_state_change(self, st):
        # disable all buttons until connected
        self.refresh_btn.config(state=st)
        self.upload_btn.config(state=st)
        self.download_btn.config(state=st)
        self.send_file_to_client_btn.config(state=st)
        self.disconnect_btn.config(state=st)
        
        connect_btn_state = ""
        if st == 'disabled':
            connect_btn_state = 'normal'
        else:
            connect_btn_state = 'disabled'
        self.connect_btn.config(state = connect_btn_state)
            
    
# max file size ?
# show all clients (not active ones only)  
FileTransferSystemGUI()     
             