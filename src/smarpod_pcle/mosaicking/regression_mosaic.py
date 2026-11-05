"""Frame-to-frame displacement client with permanent fallback after transport failure."""

import math
import pickle
import socket
from smarpod_pcle.config import get_settings
from smarpod_pcle.tcp_protocol import encode_frame, recv_message, send_message


def query_displacement(sock, frame):
    """Return the model's inter-frame displacement in image pixels (+Y downward).

    A server configured to return micrometres is converted here once; the scan
    accumulator and canvas always receive pixel displacements.
    """
    settings = get_settings().mosaic
    send_message(sock, encode_frame(frame))
    reply = recv_message(sock)
    if not isinstance(reply, dict):
        raise ValueError("Regression reply must be a dictionary containing dx and dy")
    dx, dy = float(reply["dx"]), float(reply["dy"])
    if settings.regression_in_micrometers:
        dx *= 1e-6 / settings.meters_per_pixel
        dy *= 1e-6 / settings.meters_per_pixel
    if not all(math.isfinite(value) for value in (dx, dy)):
        raise ValueError("Regression displacement must be finite after unit conversion")
    return dx, dy


def commanded_delta_px(previous, current):
    """Convert a stage delta in metres to image pixels using calibrated axis signs."""
    cfg = get_settings().mosaic
    return (cfg.sign_x * (current[0] - previous[0]) / cfg.meters_per_pixel,
            -cfg.sign_y * (current[1] - previous[1]) / cfg.meters_per_pixel)


class DisplacementSource:
    """Prime with the reference frame; never reuse a failed/fractured TCP stream.

    The protocol has no frame IDs or reference-reset command. After a failed
    exchange, this run permanently uses stage deltas so an old model reference
    or delayed reply cannot be mixed into the accumulated displacement.
    """

    def __init__(self):
        self.sock = None

    def connect(self):
        cfg = get_settings().server
        try:
            self.sock = socket.create_connection((cfg.host, cfg.port), timeout=cfg.timeout_s)
        except OSError as exc:
            print(f"Regression unavailable ({exc}); using commanded displacement.")

    def offset(self, frame, previous, current):
        """Return a pixel delta and its source; the first captured frame is the origin."""
        if self.sock is not None:
            try:
                dx, dy = query_displacement(self.sock, frame)
                # Send the first frame to prime the model, consume its reply, but place at zero.
                return (0.0, 0.0, "reference") if previous is None else (dx, dy, "regression")
            except (OSError, ValueError, KeyError, TypeError, EOFError,
                    pickle.UnpicklingError, OverflowError, ImportError, AttributeError,
                    IndexError) as exc:
                print(f"Regression failed ({exc}); using commanded displacement for this run.")
                self.close()
        if previous is None:
            return 0.0, 0.0, "reference"
        return (*commanded_delta_px(previous, current), "fallback")

    def close(self):
        if self.sock is not None:
            self.sock.close()
            self.sock = None


def main():
    from .scan_runner import run_scan
    run_scan(regression=True)


if __name__ == "__main__":
    main()
