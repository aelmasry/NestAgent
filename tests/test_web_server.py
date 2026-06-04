import socket

from web.server import choose_port


def test_choose_port_falls_back_when_requested_port_busy():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        busy_port = int(sock.getsockname()[1])

        chosen = choose_port("127.0.0.1", busy_port)

    assert chosen != busy_port
    assert chosen > 0


def test_choose_port_zero_returns_available_port():
    chosen = choose_port("127.0.0.1", 0)
    assert chosen > 0
