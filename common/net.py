"""Length-prefixed pickle messaging over a TCP socket.

Wire format matches apps/client.py and apps/demo.py: a 4-byte big-endian uint32
length prefix followed by a pickled Python object.

Note: pickle payloads are only safe from a trusted server. This mirrors the
existing convention in this repository; do not point it at an untrusted host.
"""

import pickle
import struct


def recv_exact(sock, size):
    """Receive exactly `size` bytes or raise ConnectionError."""
    data = b""
    while len(data) < size:
        packet = sock.recv(size - len(data))
        if not packet:
            raise ConnectionError("server disconnected while receiving data")
        data += packet
    return data


def send_message(sock, obj):
    """Pickle `obj` and send it with a 4-byte length prefix."""
    payload = pickle.dumps(obj)
    sock.sendall(struct.pack("!I", len(payload)) + payload)


def recv_message(sock):
    """Receive one length-prefixed pickle message and return the object."""
    size = struct.unpack("!I", recv_exact(sock, 4))[0]
    return pickle.loads(recv_exact(sock, size))
