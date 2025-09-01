import os

def save_file(data: bytes, filename: str, folder="downloads"):
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, filename)
    with open(path, "wb") as f:
        f.write(data)
    return path