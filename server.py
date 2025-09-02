import socket, threading, os, json, time, base64
from protocol import recv_packet, send_packet, MSG_TEXT, MSG_IMAGE, MSG_CONTROL, MSG_HISTORY

HOST = "0.0.0.0"
PORT = 5000
HISTORY_DIR = "history"
HISTORY_FILES_DIR = "history_files"
os.makedirs(HISTORY_DIR, exist_ok=True)
os.makedirs(HISTORY_FILES_DIR, exist_ok=True)

clients = set()
client_meta = {}  
lock = threading.Lock()
MAX_HISTORY_SEND = 50

def room_history_path(room: str) -> str:
    safe = room.replace("/", "_")
    return os.path.join(HISTORY_DIR, f"{safe}.jsonl")

def append_history(room: str, entry: dict):
    try:
        with open(room_history_path(room), "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception as e:
        print("[history] write error:", e)

def read_last_history(room: str, limit: int = MAX_HISTORY_SEND):
    path = room_history_path(room)
    if not os.path.exists(path):
        return []
    try:
        with open(path, "rb") as f:
            f.seek(0, os.SEEK_END)
            sz = f.tell()
            buff = bytearray()
            pointer = sz - 1
            lines = []
            while pointer >= 0 and len(lines) < limit:
                f.seek(pointer)
                ch = f.read(1)
                if ch == b'\n':
                    if buff:
                        lines.append(buff[::-1].decode("utf-8", errors="ignore"))
                        buff = bytearray()
                else:
                    buff.append(ch[0])
                pointer -= 1
            if buff:
                lines.append(buff[::-1].decode("utf-8", errors="ignore"))
            lines.reverse()
            return [json.loads(l) for l in lines if l.strip()]
    except Exception as e:
        print("[history] read error:", e)
        return []

def broadcast_in_room(sender_sock, ptype, payload, room):
    with lock:
        dead = []
        for c in list(clients):
            if c is sender_sock:
                continue
            meta = client_meta.get(c, {})
            if meta.get("room") != room:
                continue
            try:
                send_packet(c, ptype, payload)
            except Exception:
                dead.append(c)
        for d in dead:
            clients.discard(d)
            client_meta.pop(d, None)
            try: d.close()
            except: pass

def handle_client(conn: socket.socket, addr):
    print(f"[+] {addr} connected")
    with lock:
        clients.add(conn)
        client_meta[conn] = {"username": None, "room": None}
    try:
        while True:
            ptype, payload = recv_packet(conn)
            if ptype is None:
                break
            # Control: join
            if ptype == MSG_CONTROL:
                try:
                    obj = json.loads(payload.decode("utf-8", errors="ignore"))
                    if obj.get("action") == "join":
                        username = obj.get("username", "Anon")
                        room = obj.get("room", "default")
                        with lock:
                            client_meta[conn]["username"] = username
                            client_meta[conn]["room"] = room
                        # send history
                        items = read_last_history(room, MAX_HISTORY_SEND)
                        hist_payload = json.dumps(items, ensure_ascii=False).encode("utf-8")
                        send_packet(conn, MSG_HISTORY, hist_payload)
                        # announce
                        announce = f"[*] {username} joined {room}"
                        append_history(room, {"type":"text","username":"[system]","text":announce,"ts":int(time.time())})
                        broadcast_in_room(conn, MSG_TEXT, announce.encode("utf-8"), room)
                except Exception as e:
                    print("[control] parse error:", e)
                continue
            meta = client_meta.get(conn, {})
            username = meta.get("username") or "Anon"
            room = meta.get("room") or "default"
            if ptype == MSG_TEXT:
                try:
                    text = payload.decode("utf-8", errors="ignore")
                    entry = {"type":"text","username":username,"text":text,"ts":int(time.time())}
                    append_history(room, entry)
                    broadcast_in_room(conn, MSG_TEXT, payload, room)
                except Exception as e:
                    print("[text] error:", e)
                continue
            if ptype == MSG_IMAGE:
                try:
                    if len(payload) < 2:
                        continue
                    fname_len = int.from_bytes(payload[:2], byteorder="big")
                    fname = payload[2:2+fname_len].decode('utf-8', errors='ignore')
                    img_bytes = payload[2+fname_len:]
                    # save image file
                    safe_room = room.replace("/", "_")
                    room_dir = os.path.join(HISTORY_FILES_DIR, safe_room)
                    os.makedirs(room_dir, exist_ok=True)
                    ts = int(time.time())
                    safe_fname = f"{ts}_{os.path.basename(fname)}"
                    save_path = os.path.join(room_dir, safe_fname)
                    with open(save_path, "wb") as f:
                        f.write(img_bytes)
                    b64 = base64.b64encode(img_bytes).decode('ascii')
                    entry = {"type":"image","username":username,"filename":safe_fname,"data_b64":b64,"ts":ts}
                    append_history(room, entry)
                    broadcast_in_room(conn, MSG_IMAGE, payload, room)
                except Exception as e:
                    print("[image] error:", e)
                continue
            print("[WARN] Unknown packet type", ptype)
    except Exception as e:
        print("[-] error on client", addr, e)
    finally:
        with lock:
            clients.discard(conn)
            client_meta.pop(conn, None)
        try: conn.close()
        except: pass
        print(f"[-] {addr} disconnected")

def main():
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((HOST, PORT))
    srv.listen()
    print(f"Server listening on {HOST}:{PORT}")
    try:
        while True:
            c,a = srv.accept()
            threading.Thread(target=handle_client, args=(c,a), daemon=True).start()
    except KeyboardInterrupt:
        print("Shutting down")
    finally:
        srv.close()

if __name__ == "__main__":
    main()

