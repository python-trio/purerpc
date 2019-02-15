# Immediate mode

The goal: make `send` / `recv` on a Stream actually send or receive a message to / from socket.

It is a little bit tricky for receive, because all the receives happen in single listening coroutine thread that is bound to the underlying connection:

```python
async def listen():
    ...
    while True:
        data = await sock.recv(BUFFER_SIZE)
        if not data:
            break

        events = h2_conn.receive_data(data)
        for event in events:
            # process events
            ...
        await sock.sendall(h2_conn.data_to_send())
```

In contrast, multiple HTTP/2 streams can be opened on a same connection, this streams are typically processed in separate coroutine threads. That means there is asymmetry in how `send` and `recv` are processed.

Because all the receives happen on a separate thread it seems resonable to buffer the incoming data, HTTP/2 gives us flow control for that after all. The buffer should be as simple as possible: ***we cannot block*** in `listen()` thread on any call other than `sock.recv()` / `sock.sendall()`, because that will increase latency. Backpressure should be applied by the means of flow control. The simplest solution is the following: set a `bytes` ring buffer with the maximum size equal-ish to the maximum GRPC message that is expected (the maximum size should really be set because otherwise someone can attack the unlimited buffer). Set the stream flow control window to this size. On receiving a message, just copy the data (or reject the message altogether because of size limits) to the internal buffer. Parse the message from buffer and acknowledge it via `WINDOW_UPDATE` only in `Stream.recv` (when it is actually needed by application). With this scheme, trying to send more data than the application consumes violates flow control, and all the buffers are bounded (and also there is overall bound as  `num_streams * max_message_size`)

The sending is implemented as follows: each access to `H2Connection.data_to_send` is protected by a FIFO lock:

```python
with global_connection_lock:
    data = h2_conn.data_to_send()
    await sock.sendall(data)
```

This is a simple primitive that flushes all the data that is ready to be sent to the socket. The flow control on the sending end is also respected:

```python
async def send_message(stream_id, msg):
    pos = 0
    while pos < len(msg):
        size = h2_conn.local_flow_control_window(stream_id)
        if size == 0:
            await flow_control_event[stream_id].wait()
            flow_control_event[stream_id].clear()
            continue
        else:
            h2_conn.send_data(stream_id, msg[pos:pos+size])
            pos += size
            with global_connection_lock:
                data = h2_conn.data_to_send()
                await sock.sendall(data)
```

The `flow_control_event` is local to the current stream and the `await flow_control_event[stream_id].set()` is executed each time `WINDOW_UPDATE` frame for that stream or the connection itself arrives in `listen()` thread. 

With this approach, there is seemingly no `Queue`s anywhere and each action does exactly what it says it does, without any buffers.

For both client and server, there is one listening thread for the connections, and also one sending thread per stream. In case of server, the sending threads are spawned by the listening threads itself on the arrival of requests.

The benefits also include:

* no more complicated logic in _writer_thread
* no _writer_thread at all
* no more complicated logic in GRPCConnection.data_to_send regarding flow control and buffering

The cons:

* need to rethink "sans IO" GRPCConnection to work with this case
* need to think how to cancel tasks in progress when too large message is received
* need to count `flow_controlled_length`s to acknowledge the correct size (also need to set flow controlled length larger than maximum message length in case of padding)
* need to design more random tests that test identity of the messages before implementing this
* make perf tests

**UPDATE (2019-02-15)**: Turns out we need `_writer_thread` after all, because we cannot send anything on
`_listener_thread` (or we would block when both ends try to send very large chunks of data). If we just exclude
 calls to send from `_listener_thread`, we won't be able to answer PING frames. So instead, we ping `_writer_thread`
 so it can do the sending for us.