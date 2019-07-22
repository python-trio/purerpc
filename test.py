from bindings import H2Connection, RequestReceived, ConnectionTerminated, SettingCodes, ErrorCodes
import json
import gc
import sys
import time
import socket
import traceback
import threading

conn = H2Connection(client_side=True)
conn.initiate_connection(settings_overrides=[(SettingCodes.MAX_CONCURRENT_STREAMS, 1400)])
conn.send_headers(1, [
    (":authority", "google.com"),
    (":path", "/"),
    (":method", "GET"),
    (":scheme", "https")
])
conn.send_data(1, b'\xff\xfa\xaf' * 100, end_stream=True)
conn.close_connection(error_code=ErrorCodes.ENHANCE_YOUR_CALM, additional_data='hey', last_stream_id=0)

data = conn.data_to_send()

conn = H2Connection(client_side=False)
print(conn.receive_data(data))



def handler(sock, addr):
    print("Calling handler")
    conn = H2Connection(client_side=False)
    try:
        conn.initiate_connection()
        sock.sendall(conn.data_to_send())
        while True:
            print("Receiving")
            data = sock.recv(1024)
            if not data:
                break
            events = conn.receive_data(data)
            print("\n".join(map(str, events)))
            for event in events:
                if isinstance(event, RequestReceived):
                    headers = [
                        (':status', '200')
                    ]
                    try:
                        conn.send_headers(event.stream_id, headers)
                        conn.send_data(event.stream_id, b"", end_stream=True)
                    except:
                        traceback.print_exc()
                elif isinstance(event, ConnectionTerminated):
                    return
            sock.sendall(conn.data_to_send())
    finally:
        sock.sendall(conn.data_to_send())
        sock.shutdown(socket.SHUT_RDWR)
        assert len(sock.recv(65536)) == 0
        sock.close()


sock = socket.socket(socket.AF_INET)
sock.bind(('0.0.0.0', 0))
sock.listen(100)

print(sock.getsockname()[1])

# def count_threads():
#     while True:
#         time.sleep(1)
#         print("ACTIVE COUNT", threading.active_count())

threads = []
# threads.append(threading.Thread(target=count_threads))
# threads[-1].start()
cnt = 0
while cnt < 149:
    conn, addr = sock.accept()
    cnt += 1
    print(cnt)
    thread = threading.Thread(target=handler, args=(conn, addr))
    thread.start()
    threads.append(thread)

for t in threads:
    t.join()
