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
def build_ui(self):
        header = tk.Frame(self.root, bg="#075E54", height=64); header.pack(fill="x"); header.pack_propagate(False)
        avatar = tk.Canvas(header, width=44, height=44, bg="#075E54", highlightthickness=0); avatar.create_oval(2,2,42,42, fill="#cccccc", outline=""); avatar.pack(side="left", padx=10, pady=8)
        tk.Label(header, text=self.room, bg="#075E54", fg="white", font=("Helvetica", 14, "bold")).pack(side="top", anchor="w", padx=(4,0))
        tk.Label(header, text=f"me: {self.username}", bg="#075E54", fg="#d0ffd8", font=("Helvetica", 9)).pack(side="top", anchor="w", padx=(4,0))

        container = tk.Frame(self.root, bg="#d6e9cf"); container.pack(fill="both", expand=True)
        self.canvas = tk.Canvas(container, bg="#e6efdf", highlightthickness=0)
        vsb = ttk.Scrollbar(container, orient="vertical", command=self.canvas.yview); self.canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y"); self.canvas.pack(side="left", fill="both", expand=True)
        self.chat_frame = tk.Frame(self.canvas, bg="#e6efdf")
        self.canvas.create_window((0,0), window=self.chat_frame, anchor="nw", width=360)
        self.chat_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        bottom = tk.Frame(self.root, bg="#d6e9cf", pady=8); bottom.pack(fill="x")
        self.entry_var = tk.StringVar(); self.entry = tk.Entry(bottom, textvariable=self.entry_var, font=("Helvetica",13)); self.entry.pack(side="left", padx=(12,8), pady=6, expand=True, fill="x")
        self.entry.bind("<Return>", lambda e: self.on_send_text())
        img_btn = tk.Button(bottom, text="📷", bg="#25D366", fg="white", font=("Helvetica",12), command=self.on_send_image); img_btn.pack(side="right", padx=(6,12), pady=6)
        send_btn = tk.Button(bottom, text="Send", bg="#128C7E", fg="white", font=("Helvetica",12,"bold"), command=self.on_send_text); send_btn.pack(side="right", padx=(0,6), pady=6)

    def _on_mousewheel(self, event):
        if os.name == 'nt':
            self.canvas.yview_scroll(-1 * (event.delta // 120), "units")
        else:
            self.canvas.yview_scroll(-1 * (event.delta), "units")
            def add_text_bubble(self, text: str, sent_by_me: bool):
        row = tk.Frame(self.chat_frame, bg=self.chat_frame['bg']); row.pack(fill="x", pady=6, padx=8)
        bubble_bg = "#dcf8c6" if sent_by_me else "white"
        bubble = tk.Label(row, text=text, justify="left", bg=bubble_bg, wraplength=240, font=("Helvetica",12), padx=BUBBLE_PADX, pady=BUBBLE_PADY)
        if sent_by_me: bubble.pack(side="right", anchor="e")
        else: bubble.pack(side="left", anchor="w")
        self.canvas.update_idletasks(); self.canvas.yview_moveto(1.0)

    def add_image_bubble(self, image_bytes: bytes, filename: str, sent_by_me: bool):
        try:
            img = Image.open(io.BytesIO(image_bytes))
        except Exception:
            self.add_text_bubble("[Invalid image]", sent_by_me); return
        img.thumbnail((MAX_THUMB, MAX_THUMB)); tk_img = ImageTk.PhotoImage(img); key = f"{id(tk_img)}"; self.thumbs[key] = tk_img
        row = tk.Frame(self.chat_frame, bg=self.chat_frame['bg']); row.pack(fill="x", pady=6, padx=8)
        frame = tk.Frame(row, bg=("#dcf8c6" if sent_by_me else "white"), padx=6, pady=6)
        if sent_by_me: frame.pack(side="right", anchor="e")
        else: frame.pack(side="left", anchor="w")
        lbl = tk.Label(frame, image=tk_img, bd=0); lbl.image = tk_img; lbl.pack()
        def open_full():
            top = tk.Toplevel(self.root); top.title(filename); pil = Image.open(io.BytesIO(image_bytes))
            w,h = pil.size; screen_w = top.winfo_screenwidth() - 200; screen_h = top.winfo_screenheight() - 200
            ratio = min(screen_w/w, screen_h/h, 1.0); new_w, new_h = int(w*ratio), int(h*ratio)
            pil = pil.resize((new_w,new_h), Image.LANCZOS); tkfull = ImageTk.PhotoImage(pil); lblfull = tk.Label(top, image=tkfull); lblfull.image = tkfull; lblfull.pack()
        lbl.bind("<Button-1>", lambda e: open_full())
        self.canvas.update_idletasks(); self.canvas.yview_moveto(1.0)
    def on_send_text(self):
        text = self.entry_var.get().strip()
        if not text: return
        try:
            send_packet(self.sock, MSG_TEXT, text.encode("utf-8"))
            self.add_text_bubble(text, sent_by_me=True)
            self.entry_var.set("")
        except Exception as e:
            messagebox.showerror("Send error", str(e))

    def on_send_image(self):
        path = filedialog.askopenfilename(title="Choose image", filetypes=[("Images","*.png;*.jpg;*.jpeg;*.gif;*.bmp")])
        if not path: return
        try:
            with open(path, "rb") as f: data = f.read()
            fname = os.path.basename(path); fname_b = fname.encode('utf-8'); payload = pack_ushort(len(fname_b)) + fname_b + data
            send_packet(self.sock, MSG_IMAGE, payload); self.add_image_bubble(data, fname, sent_by_me=True)
        except Exception as e:
            messagebox.showerror("Send image error", str(e))