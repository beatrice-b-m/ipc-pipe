import threading
import queue
from ipc import PipeClient
import time


if __name__ == "__main__":
    msg_queue = queue.SimpleQueue()

    # instantiate the listener and start the thread
    client = PipeClient(6003, b'test_auth', msg_queue)
    client.start()

    msg_list = [
        "varA",
        [0.0, 2.0],
        {"keyA": 0, "keyB": 8.6, "keyC": [0.0, 1.0, 2.0]}
    ]

    try:
        for msg in msg_list:
            print('sending', msg)
            msg_queue.put(msg)
            time.sleep(10)
        
    finally:
        msg_queue.put_nowait(None) # send stop signal
        client.join()
