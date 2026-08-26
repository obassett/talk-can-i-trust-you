"""Blocking-with-retries send/recv over a pyOpenSSL connection.

`spiffetls.listen()`/`dial()` return an `OpenSSL.SSL.Connection`. Even in
blocking mode, OpenSSL can raise WantReadError / WantWriteError while the TLS
state machine makes progress. These helpers mirror the retry pattern used by
py-spiffe's own smoke-test examples so the demo doesn't flake.
"""

from __future__ import annotations

import select
import time

from OpenSSL import SSL


def send_all(conn: SSL.Connection, data: bytes, timeout: float = 5.0) -> None:
    deadline = time.time() + timeout
    view = memoryview(data)
    while view:
        if time.time() >= deadline:
            raise TimeoutError("timeout sending data")
        try:
            sent = conn.send(view)
            view = view[sent:]
        except SSL.WantWriteError:
            select.select([], [conn], [], max(0.0, deadline - time.time()))
        except SSL.WantReadError:
            select.select([conn], [], [], max(0.0, deadline - time.time()))


def recv_line(conn: SSL.Connection, timeout: float = 5.0) -> bytes:
    """Read until a newline (or EOF). Returns the line without the trailing \\n."""
    deadline = time.time() + timeout
    data = b""
    while b"\n" not in data and len(data) < 64 * 1024:
        if time.time() >= deadline:
            raise TimeoutError("timeout reading response")
        try:
            chunk = conn.recv(4096)
            if not chunk:
                break
            data += chunk
        except SSL.WantReadError:
            select.select([conn], [], [], max(0.0, deadline - time.time()))
        except SSL.WantWriteError:
            select.select([], [conn], [], max(0.0, deadline - time.time()))
        except SSL.ZeroReturnError:
            break
    return data.split(b"\n", 1)[0]
