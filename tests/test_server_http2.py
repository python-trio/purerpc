import time
import socket
import contextlib

import pytest
import h2.config
import h2.connection
import h2.events
import h2.settings

import purerpc
import purerpc.grpclib.connection

from purerpc.test_utils import run_purerpc_service_in_process


@pytest.fixture
def dummy_server_port():
    with run_purerpc_service_in_process(purerpc.Service("Greeter")) as port:
        # TODO: migrate to serve_async() to avoid timing problems
        time.sleep(0.1)
        yield port


@contextlib.contextmanager
def http2_client_connect(host, port):
    sock = socket.socket(socket.AF_INET)
    sock.connect((host, port))
    config = h2.config.H2Configuration(client_side=True, header_encoding="utf-8")
    conn = h2.connection.H2Connection(config=config)
    conn.initiate_connection()
    sock.send(conn.data_to_send())

    try:
        yield conn, sock
    finally:
        sock.close()


def http2_receive_events(conn, sock):
    try:
        sock.settimeout(0.1)
        events = []
        while True:
            try:
                data = sock.recv(4096)
            except socket.timeout:
                break
            if not data:
                break
            events.extend(conn.receive_data(data))
    finally:
        sock.settimeout(None)
    return events


def test_connection(dummy_server_port):
    ping_data = b"DEADBEEF"

    with http2_client_connect("localhost", dummy_server_port) as (conn, sock):
        conn.ping(ping_data)
        sock.send(conn.data_to_send())

        events_received = http2_receive_events(conn, sock)
        event_types_received = list(map(type, events_received))

        assert h2.events.RemoteSettingsChanged in event_types_received
        assert h2.events.WindowUpdated in event_types_received
        assert h2.events.SettingsAcknowledged in event_types_received
        assert h2.events.PingAckReceived in event_types_received

        for event in events_received:
            if isinstance(event, h2.events.RemoteSettingsChanged):
                assert (event.changed_settings[h2.settings.SettingCodes.MAX_FRAME_SIZE].new_value ==
                        purerpc.grpclib.connection.GRPCConnection.MAX_INBOUND_FRAME_SIZE)

                assert (event.changed_settings[h2.settings.SettingCodes.MAX_CONCURRENT_STREAMS].new_value ==
                        purerpc.grpclib.connection.GRPCConnection.MAX_CONCURRENT_STREAMS)

                assert (event.changed_settings[h2.settings.SettingCodes.MAX_HEADER_LIST_SIZE].new_value ==
                        purerpc.grpclib.connection.GRPCConnection.MAX_HEADER_LIST_SIZE)
            elif isinstance(event, h2.events.PingAckReceived):
                assert event.ping_data == ping_data

        time.sleep(0.2)

        conn.ping(ping_data)
        sock.send(conn.data_to_send())

        events_received = http2_receive_events(conn, sock)
        event_types_received = list(map(type, events_received))
        assert h2.events.PingAckReceived in event_types_received
        for event in events_received:
            if isinstance(event, h2.events.PingAckReceived):
                assert event.ping_data == ping_data
