"""Legacy TCP framing: four-byte big-endian length, then a pickled Python object.

Pickle can execute code during decoding. The size limit bounds message buffering;
it does not make an untrusted peer safe or authenticate the inference server.
"""

import pickle
import struct

MAX_MESSAGE_BYTES = 16 * 1024 * 1024


def recv_exact(sock, size):
    """Read across TCP packet boundaries, failing if the peer disconnects.

    A configured socket timeout applies to each recv call, not to the total
    duration of this function or the complete message exchange.
    """
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
    """Send one framed object; callers must serialize writes on a shared socket."""
    payload = pickle.dumps(obj)
    if not 0 < len(payload) <= MAX_MESSAGE_BYTES:
        raise ValueError("Message exceeds the 16 MiB protocol limit")
    sock.sendall(struct.pack("!I", len(payload)) + payload)


def recv_message(sock):
    """Decode one full frame from a trusted peer.

    Discard the connection after a failed header/payload read: the remaining
    bytes cannot safely be interpreted as a new length prefix.
    """
    size = struct.unpack("!I", recv_exact(sock, 4))[0]
    if not 0 < size <= MAX_MESSAGE_BYTES:
        raise ValueError(f"Invalid message length: {size}")
    return pickle.loads(recv_exact(sock, size))


def encode_frame(frame, signal=1):
    """Resize to the model's 224-by-224 JPEG input and retain the signal field.

    Capture callers supply grayscale images; this helper preserves the input's
    channel count rather than applying another color conversion.
    """
    import cv2
    frame = cv2.resize(frame, (224, 224), interpolation=cv2.INTER_CUBIC)
    ok, encoded = cv2.imencode(".jpg", frame)
    if not ok:
        raise RuntimeError("Could not encode frame as JPEG")
    return {"image": encoded.tobytes(), "signal": signal}
