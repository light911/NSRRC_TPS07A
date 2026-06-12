#!/usr/bin/env python3
"""
Smoke test for the DCSDHS connection skeleton (serve_forever/connect_dcss).

Runs a fake DCSS on localhost and checks that the DHS:
  1. connects and answers the handshake (htos_client_is_hardware, 200 bytes)
  2. reconnects after the server drops the connection

No EPICS, no hardware, no subprocess is touched: DCSDHS.__init__ is skipped
and run_session is replaced by a stub.

usage: uv run python tests/smoke_connection.py
"""
import socket
import threading
import time
import sys
import os
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from EpicsDHS import DCSDHS

PORT = 14299
N_SESSIONS = 2
results = {'connections': 0, 'handshakes': []}


def fake_dcss(server):
    for _ in range(N_SESSIONS):
        client, addr = server.accept()
        results['connections'] += 1
        client.sendall(b'stoc_send_client_type\x00')
        data = client.recv(400)
        results['handshakes'].append(data)
        time.sleep(0.3)
        client.close()  # simulate DCSS dropping the connection


def fake_session():
    # real run_session blocks until the connection dies; just pretend
    time.sleep(0.6)


def main():
    logging.basicConfig(level=logging.INFO)

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(('127.0.0.1', PORT))
    server.listen(2)
    threading.Thread(target=fake_dcss, args=(server,), daemon=True).start()

    dhs = DCSDHS.__new__(DCSDHS)  # skip __init__: no EPICS, no subprocesses
    dhs.logger = logging.getLogger('smoke')
    dhs.host = '127.0.0.1'
    dhs.port = PORT
    dhs.tcptimeout = 1
    dhs.dhsname = 'detector'
    dhs.Par = {'operationRecord': []}
    dhs.run_session = fake_session

    threading.Thread(target=dhs.serve_forever, daemon=True).start()

    deadline = time.time() + 15
    while time.time() < deadline and results['connections'] < N_SESSIONS:
        time.sleep(0.1)

    assert results['connections'] >= N_SESSIONS, \
        f"expected {N_SESSIONS} connections, got {results['connections']}"
    for hs in results['handshakes']:
        assert hs.startswith(b'htos_client_is_hardware detector'), \
            f"bad handshake: {hs[:60]}"
        assert len(hs) == 200, f"handshake should be padded to 200 bytes, got {len(hs)}"

    print(f"PASS: {results['connections']} connections, handshake ok, reconnect ok")


if __name__ == "__main__":
    main()
