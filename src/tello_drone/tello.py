import threading
import socket
import time
import logging
from queue import Queue
from collections import namedtuple


state_fields = ["pitch", "roll", "yaw",
                "vgx", "vgy", "vgz", 
                "templ", "temph",
                "tof", "h" "bat",
                "baro", "time", 
                "agx", "agy", "agz"]

State = namedtuple("State", state_fields, defaults=(None, ) * len(state_fields))

class ThreadSafeState:
    def __init__(self):
        self._state = State()
        self._lock = threading.Lock()

    def set_state(self, state: State):
        with self._lock:
            self._state = state

    def get_state(self):
        with self._lock:
            return self._state

class Tello:
    # Network information about tello drone
    COMMAND_PORT = 8889
    STATE_PORT = 8890

    VIDEO_ADDR = "0.0.0.0"
    VIDEO_PORT = 11111

    INT_STATE_FIELDS = (
        'pitch', 'roll', 'yaw',
        'vgx', 'vgy', 'vgz',
        'templ', 'temph',
        'tof', 'h', 'bat', 'time'
    )

    FLOAT_STATE_FIELDS = ('baro', 'agx', 'agy', 'agz')

    # Create logger 
    HANDLER = logging.StreamHandler()
    FORMATER = logging.Formatter('[%(levelname)s] %(filename)s - %(lineno)d - %(message)s')
    HANDLER.setFormatter(FORMATER)

    LOGGER = logging.getLogger("djitello")
    LOGGER.addHandler(HANDLER)
    LOGGER.setLevel(logging.INFO)

    def __init__(self,
        TELLO_IP: str,
    ):
        self.client_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.client_sock.bind(("", Tello.COMMAND_PORT))

        self.drone_addr = (TELLO_IP, Tello.COMMAND_PORT)

        # Structures to store data returned by the drone
        self.results = Queue(maxsize=0)
        self.state = ThreadSafeState()

        # Start threads

        # For client now need to bound
        self.flying = False
        self.stream = False

    @staticmethod
    def _recv_upd_response(client_sock: socket.socket, results: Queue):
        while True:
            try:
                data, address = client_sock.recvfrom(1024)
                Queue.put(data.decode("utf-8"))
            except Exception as e:
                print(e)
                break

    @staticmethod
    def _recv_upd_state(state: ThreadSafeState):
        # Create state socket
        state_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        state_sock.bind(("", Tello.STATE_PORT))

        while True:
            try:
                data, address = client_sock.recvfrom(1024)
                state = Tello.parse_state(data.decode("utf-8"))
            except Exception as e:
                print(e)
                break


        state_sock.close()

    @staticmethod
    def parse_state(state: str) -> State:
        state = state.rstrip("\r\n")

        def convert(data_field):
            filed_name, value = data_field.split(":")

            if field_name in Tello.INT_STATE_FIELD:
                return int(value)
            elif field_name in Tello.FLOAT_STATE_FIELD:
                return float(value)
            else: 
                raise ValueError

        state_list = list(map(convert, state.split(";")))
        return State(*state_list)
