"""Legacy length-prefixed pickle protocol: use only with a trusted server."""

import pickle
import struct

MAX_MESSAGE_BYTES = 16 * 1024 * 1024


def recv_exact(sock, size):
    if size < 0:
        raise ValueError("size must be nonnegative")
    data = bytearray()
    while len(data) < size:
        packet = sock.recv(size - len(data))
        if not packet:
            raise ConnectionError("Server disconnected while receiving a message")
        data.extend(packet)
    return bytes(data)


def send_message(sock, obj):
    payload = pickle.dumps(obj)
    if not 0 < len(payload) <= MAX_MESSAGE_BYTES:
        raise ValueError("Message exceeds the 16 MiB protocol limit")
    sock.sendall(struct.pack("!I", len(payload)) + payload)


def recv_message(sock):
    size = struct.unpack("!I", recv_exact(sock, 4))[0]
    if not 0 < size <= MAX_MESSAGE_BYTES:
        raise ValueError(f"Invalid message length: {size}")
    return pickle.loads(recv_exact(sock, size))


def encode_frame(frame, signal=1):
    import cv2
    frame = cv2.resize(frame, (224, 224), interpolation=cv2.INTER_CUBIC)
    ok, encoded = cv2.imencode(".jpg", frame)
    if not ok:
        raise RuntimeError("Could not encode frame as JPEG")
    return {"image": encoded.tobytes(), "signal": signal}
