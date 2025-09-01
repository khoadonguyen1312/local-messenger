rooms = {"default": []}

def join_room(room_name, client):
    if room_name not in rooms:
        rooms[room_name] = []
    rooms[room_name].append(client)

def broadcast(room_name, sender, data):
    for c in rooms.get(room_name, []):
        if c != sender:
            c.sendall(data)