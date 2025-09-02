# client_gui.py

import socket, threading, struct, os, io, json, base64, time
import tkinter as tk
from tkinter import ttk, filedialog, simpledialog, messagebox
from PIL import Image, ImageTk
from protocol import send_packet, recv_packet, MSG_TEXT, MSG_IMAGE, MSG_CONTROL, MSG_HISTORY

SERVER_HOST = "192.168.1.250"
SERVER_PORT = 5000
DOWNLOADS = os.path.join(os.path.dirname(__file__), "downloads")
os.makedirs(DOWNLOADS, exist_ok=True)

MAX_THUMB = 220
BUBBLE_PADX = 12
BUBBLE_PADY = 8

def pack_ushort(n: int) -> bytes:
    return struct.pack("!H", n)

class ChatGUI:
    def __init__(self):
        # ask username & room
        root = tk.Tk(); root.withdraw()
        self.username = simpledialog.askstring("Tên", "Nhập username:", parent=root) or "Anon"
        self.room = simpledialog.askstring("Phòng", "Nhập tên room:", initialvalue="default", parent=root) or "default"
        root.destroy()

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.sock.connect((SERVER_HOST, SERVER_PORT))
        except Exception as e:
            messagebox.showerror("Kết nối thất bại", f"Không thể kết nối server: {e}")
            raise

        ctrl = {"action":"join","username":self.username,"room":self.room}
        send_packet(self.sock, MSG_CONTROL, json.dumps(ctrl, ensure_ascii=False).encode("utf-8"))

        self.root = tk.Tk()
        self.root.title(f"{self.username} @ {self.room}")
        self.root.geometry("380x700")
        self.root.configure(bg="#d6e9cf")
        self.thumbs = {}
        self.build_ui()
        t = threading.Thread(target=self.receive_loop, daemon=True)
        t.start()
        # handle closing cleanly
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

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

    def receive_loop(self):
        while True:
            try:
                ptype, payload = recv_packet(self.sock)
                if ptype is None: break
                if ptype == MSG_HISTORY:
                    try:
                        items = json.loads(payload.decode("utf-8", errors="ignore"))
                        for it in items:
                            if it.get("type") == "text":
                                text = f"{it.get('username','')}:\n{it.get('text','')}"
                                self.root.after(0, lambda t=text: self.add_text_bubble(t, sent_by_me=False))
                            elif it.get("type") == "image":
                                b64 = it.get("data_b64",""); img_bytes = base64.b64decode(b64) if b64 else b""; fname = it.get("filename","image")
                                self.root.after(0, lambda b=img_bytes,f=fname: self.add_image_bubble(b, f, sent_by_me=False))
                    except Exception as e:
                        print("[history] parse error", e)
                    continue
                if ptype == MSG_TEXT:
                    text = payload.decode("utf-8", errors="ignore"); self.root.after(0, lambda t=text: self.add_text_bubble(t, sent_by_me=False))
                elif ptype == MSG_IMAGE:
                    if len(payload) < 2: continue
                    fname_len = struct.unpack("!H", payload[:2])[0]; fname = payload[2:2+fname_len].decode('utf-8', errors='ignore'); img_bytes = payload[2+fname_len:]
                    self.root.after(0, lambda b=img_bytes,f=fname: self.add_image_bubble(b, f, sent_by_me=False))
            except Exception:
                break
        try: self.sock.close()
        except: pass

    def on_close(self):
        try: self.sock.shutdown(socket.SHUT_RDWR); self.sock.close()
        except: pass
        self.root.destroy()

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    import struct, io
    from PIL import Image
    app = ChatGUI(); app.run()
