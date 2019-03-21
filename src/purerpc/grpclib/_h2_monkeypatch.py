import h2.connection
import h2.stream


def new_h2_connection_data_to_send(self, amount=None):
    if amount is None:
        data = bytes(self._data_to_send)
        self._data_to_send = bytearray()
        return data
    else:
        data = bytes(self._data_to_send[:amount])
        self._data_to_send = self._data_to_send[amount:]
        return data


def new_h2_connection_clear_outbound_data_buffer(self):
    self._data_to_send = bytearray()


def monkey_patch_h2_data_to_send():
    h2.connection.H2Connection.data_to_send = new_h2_connection_data_to_send
    h2.connection.H2Connection.clear_outbound_data_buffer = new_h2_connection_clear_outbound_data_buffer


def monkey_patch_h2_reset_on_closed_stream_bug():
    """
    H2 raises h2.exceptions.StreamClosedError when receiving RST_STREAM on a closed stream that was
    not closed by endpoint, for example:

    -> HEADERS frame
    -> DATA frame with END_STREAM flag set  # stream is now half-closed (local)
    <- HEADERS frame
    <- DATA frame
    <- HEADERS frame with END_STREAM flag set  # stream is now closed
    <- RST_STREAM

    This is the case when calling unary-unary requests with purerpc client and grpcio server
    (it sends END_STREAM + RST_STREAM because the RPC call is unary-unary and it cannot receive
    any more data).

    To fix this, we use a workaround.
    """
    h2.stream._transitions[h2.stream.StreamState.CLOSED,
                           h2.stream.StreamInputs.RECV_RST_STREAM] = \
        (None, h2.stream.StreamState.CLOSED)

    h2.stream._transitions[h2.stream.StreamState.CLOSED,
                           h2.stream.StreamInputs.RECV_WINDOW_UPDATE] = \
        (None, h2.stream.StreamState.CLOSED)


def apply_patch():
    monkey_patch_h2_reset_on_closed_stream_bug()
    monkey_patch_h2_data_to_send()
