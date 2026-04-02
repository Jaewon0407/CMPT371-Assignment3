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
        
        # disable all buttons until connected
        self.refresh_btn.config(state='disabled')
        self.upload_btn.config(state='disabled')
        self.download_btn.config(state='disabled')
        self.send_file_to_client_btn.config(state='disabled')
        self.disconnect_btn.config(state='disabled')
        
        self.root.mainloop()
        
## ------------------------ CONNECTION FRAME -----------------------------

    def connection_frame(self):
        
        conn_frame = tk.Frame(self.root)
        
        ## host
        self.lbl_host = tk.Label(conn_frame, text='Host:', font=('Arial', 16))
        self.lbl_host.pack(side='left', padx=5, pady=5)
        
        self.entry_host = tk.Entry(conn_frame, font=('Arial', 16))
        self.entry_host.insert('0', '127.0.0.1')
        self.entry_host.pack(side='left', padx=5, pady=5)
        
        ## port
        self.lbl_port = tk.Label(conn_frame, text='Port:', font=('Arial', 16))
        self.lbl_port.pack(side='left', padx=5, pady=5)
        
        self.entry_port = tk.Entry(conn_frame, font=('Arial', 16))
        self.entry_port.insert(0, '5001')
        self.entry_port.pack(side='left', padx=5, pady=5)
        
        ## connect button
        self.connect_btn = tk.Button(conn_frame, text='Connect', font=('Arial', 18), command=self.fn_connect)
        self.connect_btn.pack(side='left', padx=5, pady=5)
        
        # diconnect button
        self.disconnect_btn = tk.Button(conn_frame, text='Disconnect', font=('Arial', 18), command=self.fn_disconnect)
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

        
    def fn_connect(self):
        
        print('')
    
    
    def fn_disconnect(self):
        print('')
           
    def fn_refresh(self):
        print('')
        
    def fn_upload_file(self):
        print('')
        
    def fn_download_file(self):
        print('')
        
    def fn_send_client_file(self):
        print('')
        

    # disable buttons until connected    
    
    
FileTransferSystemGUI()     
             