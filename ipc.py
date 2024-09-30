import multiprocessing as mp
from multiprocessing.connection import Listener, Client
import queue
import threading
import socket
import os



class PipeListener(threading.Thread):
    """
    this thread can be attached to a main process to create and listen to an inter-process 
    communication pipe.
    
    any messages will be forwarded to a thread-safe queue (for processing in some main thread)
    """
    
    def __init__(self, port: int, msg_queue: queue.SimpleQueue, 
                 stop_signal: threading.Event, auth: bytes = None, 
                 cycle_time: float = 5.0):
        super().__init__()
        self.address = ('localhost', port)
        self.msg_queue = msg_queue
        self.stop_signal = stop_signal
        self.cycle_time = cycle_time

        self.connection_list = []

        # get an 8-byte bitstring to use as the authkey for the pipe
        # this is meant more like a uid than a password
        if auth is None:
            self.auth = os.urandom(8)
        else:
            self.auth = auth

    def run(self):
        # define the listener and set a timeout so it doesn't
        # block forever while waiting for a connection
        listener = Listener(self.address, authkey=self.auth)
        listener._listener._socket.settimeout(self.cycle_time)

        try:
            while not self.stop_signal.is_set():
                # poll the listener and any active connections
                # TO DO: this may be done better with async, modify event loop
                # to do listener / connections_polling w/ asyncio
                connections_handler = threading.Thread(target=self.handle_connections)
                connections_handler.start()
                try:
                    connection = listener.accept()
                    self.connection_list.append(connection)
                    print('connected to client...')

                except socket.timeout:
                    pass

                finally:
                    connections_handler.join()
                
        finally:
            listener.close()
            for connection in self.connection_list:
                connection.close()

    def handle_connections(self):
        if len(self.connection_list) == 0:
            return
        for ready in mp.connection.wait(self.connection_list, self.cycle_time):
            try:
                msg = ready.recv()
                # if the client sent a stop signal (None)
                # remove it from the connection list
                if msg is None:
                    self.connection_list.remove(ready)
                    print('disconnecting client...')
                else:
                    self.msg_queue.put(msg)

            # the listener won't return an EOFError so we can only consider
            # the connection_list
            except EOFError:
                self.connection_list.remove(ready)
            else:
                print(msg)



class PipeClient(threading.Thread):
    """
    this thread can be attached to a main process to connect to the given localhost socket
    to send messages to another client.

    any messages will be forwarded to a thread-safe queue (for processing in some main thread)
    """
    
    def __init__(self, port: int, auth: bytes, msg_queue: queue.SimpleQueue, 
                 cycle_time: float = 5.0):
        super().__init__()
        self.address = ('localhost', port)
        self.msg_queue = msg_queue
        self.cycle_time = cycle_time
        self.auth = auth
        # instead of a separate stop signal we can just add a stop signal
        # to the msg_queue

    def run(self):
        connection_list = []
        with Client(self.address, authkey=self.auth) as client:
            while True:
                try:
                    # break if the queue receives a stop signal
                    # for now we'll treat a None as a stop signal
                    msg = self.msg_queue.get(block=True, timeout=self.cycle_time)
                    client.send(msg)
                    if msg is None:
                        break
                        
                except queue.Empty:
                    pass