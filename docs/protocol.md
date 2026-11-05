# Client/server protocol

The repository implements the client side of an existing Python TCP protocol.
It does not include a server, trained model, authentication service, or TLS
termination. Configure the peer through `server.host`, `server.port`, and
`server.timeout_s` in [the machine configuration](../config/example.toml).

## Transport and trust

Each message contains:

1. A four-byte unsigned integer in network byte order (`struct` format `!I`),
   giving the payload length in bytes.
2. Exactly that many bytes containing one pickled Python object.

TCP is a byte stream: either the header or payload can arrive in multiple reads.
The receiver must read each part completely and treat an incomplete message or
disconnect as an error. The shared transport rejects empty payloads and payloads
larger than **16 MiB** (`16 * 1024 * 1024` bytes), as defined by
`smarpod_pcle.net.MAX_MESSAGE_BYTES`; the peer must stay within that bound. A
length bound limits message allocation, not pickle deserialization behavior.

Only connect to a trusted peer on a trusted connection. Unpickling a crafted
payload can execute arbitrary code before application-level key/type validation
occurs. This protocol provides no authentication, integrity protection, or
encryption. Do not expose it directly to an untrusted network. [Python pickle
security documentation](https://docs.python.org/3/library/pickle.html)

Both endpoints need compatible pickle protocol versions and should exchange
built-in dictionaries, bytes, integers, and floats. JPEG bytes avoid requiring
matching NumPy classes to decode the image payload. A successful TCP connection
alone says nothing about model compatibility. The sender uses Python's default
pickle protocol, so verify compatibility if changing the client/server Python
versions.

## Image request

The client converts the configured pCLE view to grayscale, resizes it to
`224 × 224`, and JPEG-encodes it. The pickled request has this shape:

```python
{
    "image": b"...JPEG-encoded image bytes...",
    "signal": 1,
}
```

`image` contains encoded bytes, not a NumPy array or a base64 string. `signal` is
the existing integer control flag (`0` or `1`). In servo operation, `1` requests
the next correction cycle; subsequent streamed frames can carry `0` until the
client requests another update. The spiral demo sends `1` for each waypoint.
The service must implement the flag semantics expected by the selected client
mode; there is no protocol handshake that negotiates them.

Stream-only client mode 2 continuously sends `signal = 1`. It drains any replies
without using their values and also supports a server that sends no replies.
Once a reply starts arriving, an incomplete frame must still finish within the
configured socket timeout; a partial/invalid reply or disconnect ends the run.

## Visual-servoing reply

The servo client expects a dictionary containing finite numeric values:

```python
{
    "distance": 10.0,
    "angle": 0.0,
    "axis": 0.0,
}
```

- `distance`: signed Z correction in **micrometres**. The client converts it to
  metres and adds it to the commanded Z coordinate. Confirm this sign convention
  against the assembled setup; dataset defocus distance and signed correction
  are different quantities.
- `angle`: signed tilt correction in **degrees**.
- `axis`: tilt-axis azimuth in **degrees**, used by the existing conversion to X/Y
  rotation components (`0` corresponds to X, `90` to Y).

The existing control convention applies distance when `distance != 0` and
`angle == 0`, or orientation when `angle != 0` and `distance == 0`. The clear-state
reply is `distance == 0` and `angle == 0`; it allows a mosaicking servo run to
advance its local trajectory. Simultaneously nonzero distance and angle values
are rejected by the client; the controller is not a combined six-axis optimizer.

The local controller generates the scan trajectory. The server supplies
corrections, not arbitrary poses. The existing orientation policy and coordinate
conventions still need physical calibration; transport validation does not
validate the inferred movement.

`demo` consumes a reply for each image to keep the socket synchronized, but
does not apply its values to motion. Its trajectory is local. Ensure the service
returns replies when using this command.

## Regression-mosaicking reply

`mosaic-regression` uses a different response schema:

```python
{
    "dx": 2.5,
    "dy": -1.0,
}
```

These are frame-to-frame displacements for image placement. By default, the
values are **mosaic pixels**: X increases rightward and Y increases downward.
The caller accumulates them into a mosaic position. If the regression workflow
sets `mosaic.regression_in_micrometers = true`, it converts the values using
`mosaic.meters_per_pixel`. Confirm whether the service's predictions refer to the
resized `224 × 224` image or the original captured field of view, and convert its
output to the mosaic coordinate scale before use.

The first frame is sent as the reference and its reply is consumed; its mosaic
offset is zero. The service must establish the previous-frame reference for that
connection and return a valid finite `dx`/`dy` reply even for the reference frame.
Subsequent replies must also contain finite offsets.

There are no sequence IDs, reference-reset fields, or retransmission identifiers
in the legacy schema. A reconnect, dropped frame, or timeout can therefore
invalidate a stateful model's displacement history. On an initial connection or
per-frame communication/response error, the client closes the socket and uses
commanded stage deltas for the remainder of that scan. It does not reuse a
potentially desynchronized stream. This fallback continues image placement from
the accumulated position; it does not repair earlier model drift.

Servo (`distance`, `angle`, `axis`) and regression (`dx`, `dy`) services are not
interchangeable just because they listen on the same port. Use the matching
service for the selected command. Regression results affect mosaic placement;
the physical scan trajectory remains locally commanded.

## Bring-up checks

Start with `smarpod-pcle --config config/local.toml doctor --server`. This performs
only a TCP connection check and closes the socket. It does not send a frame,
read a reply, or establish that a model follows this protocol.

Before a live servo run, verify request decoding and response fields against
known images, check units and signs, and confirm that the service handles a
client disconnect. Configure a timeout appropriate for inference latency.
Network and model failures must be handled before further corrections are
applied to the robot.
