import socket
import struct
from typing import Optional,Tuple


MSG_TEXT = 1
MSG_IMAGE = 2
MSG_CONTROL = 3
MSG_HISTORY = 4

def send_packet(sock: socket.socket, ptype: int, payload: bytes) -> None:
    if not isinstance(payload, (bytes, bytearray)):
        raise TypeError("payload must be bytes")
    length = 1 + len(payload)
    header = struct.pack("!I B", length, ptype)
    sock.sendall(header + payload)


def recv_all(sock: socket.socket, n: int) -> Optional[bytes]:
    data = bytearray()
    while len(data) < n:
        try:
            chunk = sock.recv(n - len(data))
        except OSError:
            return None
        if not chunk:
            return None
        data.extend(chunk)
    return bytes(data)

def recv_packet(sock: socket.socket) -> Tuple[Optional[int], Optional[bytes]]:
    header = recv_all(sock, 4)
    if not header:
        return None, None
    (length,) = struct.unpack("!I", header)
    type_b = recv_all(sock, 1)
    if not type_b:
        return None, None
    ptype = type_b[0]
    payload = b''
    if length - 1 > 0:
        payload = recv_all(sock, length - 1)
        if payload is None:
            return None, None
    return ptype, payload

