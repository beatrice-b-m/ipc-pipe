import threading
import queue
from ipc import PipeListener

if __name__ == "__main__":
    stop_signal = threading.Event()
    msg_queue = queue.SimpleQueue()

    # instantiate the listener and start the thread
    listener = PipeListener(6003, msg_queue, stop_signal, auth=b'test_auth')
    listener.start()

    while not stop_signal.is_set():
        try:
            msg = msg_queue.get(block=True, timeout=5.0)
            print(msg)

        except queue.Empty:
            print("queue is empty...")
            pass

        except KeyboardInterrupt:
            print("interrupt received...")
            stop_signal.set()
            listener.join()
