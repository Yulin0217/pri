"""Frame-to-frame displacement client with permanent fallback after transport failure."""

import math
import pickle
import socket
from smarpod_pcle.config import get_settings
from smarpod_pcle.net import encode_frame, recv_message, send_message


def query_displacement(sock, frame):
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
    cfg = get_settings().mosaic
    return (cfg.sign_x * (current[0] - previous[0]) / cfg.meters_per_pixel,
            -cfg.sign_y * (current[1] - previous[1]) / cfg.meters_per_pixel)


class DisplacementSource:
    """Prime with the reference frame; never reuse a failed/fractured TCP stream."""

    def __init__(self):
        self.sock = None

    def connect(self):
        cfg = get_settings().server
        try:
            self.sock = socket.create_connection((cfg.host, cfg.port), timeout=cfg.timeout_s)
        except OSError as exc:
            print(f"Regression unavailable ({exc}); using commanded displacement.")

    def offset(self, frame, previous, current):
        if self.sock is not None:
            try:
                dx, dy = query_displacement(self.sock, frame)
                # First frame establishes the model's reference; consume its reply.
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
    from .scan import run_scan
    run_scan(regression=True)


if __name__ == "__main__":
    main()
