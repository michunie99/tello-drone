import threading
import socket
import time
import logging
from queue import Queue
from collections import namedtuple

# TODO - move to separate file 
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
        self.threads = []

        self.threads.append(threading.Thread(
            target=self._recv_udp_response, 
            args=(self.client_sock, self.results)
        ))

        self.threads.append(threading.Thread(
            target=self._recv_udp_state, 
            args=(self.state, )
        ))

        for thread in self.threads:
            thread.daemon = True
            thread.start()

        # For client now need to bound
        self.flying = False
        self.stream = False

        # Initialize drone
        self.initailize_drone()

    def initailize_drone(self):
        self.send_command("command") 

    def send_command(self, command: str):
        self.client_sock.sendto(command.encode("utf-8"), self.drone_addr)

    def send_command_response(self, command: str):
        raise NotImplemented

    @property 
    def get_state(self):
        return self.state.get_state()

    @staticmethod
    def _recv_udp_response(client_sock: socket.socket, results: Queue):
        while True:
            try:
                data, address = client_sock.recvfrom(1024)
                results.put(data.decode("utf-8"))
            except Exception as e:
                print(e)
                break

    @staticmethod
    def _recv_udp_state(state: ThreadSafeState):
        # Create state socket
        state_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        state_sock.bind(("", Tello.STATE_PORT))

        while True:
            try:
                print("wating .. ")
                data, address = state_sock.recvfrom(1024)
                print(data)
                state.set_state(Tello.parse_state(data.decode("utf-8")))
            except Exception as e:
                # TODO - add exeption
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

