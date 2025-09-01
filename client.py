import socket, threading, struct, os, io, json, base64, time
import tkinter as tk
from tkinter import ttk, filedialog, simpledialog, messagebox
from PIL import Image, ImageTk
from protocol import send_packet, recv_packet, MSG_TEXT, MSG_IMAGE, MSG_CONTROL, MSG_HISTORY

SERVER_HOST = "192.168.1.8"
SERVER_PORT = 5000
DOWNLOADS = os.path.join(os.path.dirname(__file__), "downloads")
os.makedirs(DOWNLOADS, exist_ok=True)

MAX_THUMB = 220
BUBBLE_PADX = 12
BUBBLE_PADY = 8

def pack_ushort(n: int) -> bytes:
    return struct.pack("!H", n)
