import _thread
import argparse
import time
from socket import AF_INET, SOCK_STREAM
from threading import Thread
import socket
import random
import os
import packet
from timer import Timer

# utf-8 means ascii
FORMAT = "utf-8"
counter = 0
filecount = 0
clients = {}
addresses = {}
files = []

terminalArg = argparse.ArgumentParser(description="Chat Server")
terminalArg.add_argument(
    '--host',
    help='Host IP',
    # brings your local ip address
    default=socket.gethostbyname(socket.gethostname())

)
terminalArg.add_argument(
    '--port',
    help='Port Number',
    default=5050
)

server_args = terminalArg.parse_args()

HOST = server_args.host
PORT = int(server_args.port)
BUFSIZE = 2048
ADDR = (HOST, PORT)

stop_server = False

SocketSERVER = socket.socket(AF_INET, SOCK_STREAM)
SocketSERVER.bind(ADDR)

PACKET_SIZE = 512
SENDER_ADDR = (socket.gethostbyname(socket.gethostname()), 0)

socketUDP = socket.socket(AF_INET, socket.SOCK_DGRAM)
socketUDP.bind(SENDER_ADDR)

base = 0
receiveThread = _thread.allocate_lock()
max_waiting_time = Timer(0.5)


def send_files(sock, filename):
    global receiveThread
    global base
    global max_waiting_time

    # Open file
    try:
        file = open(filename, 'rb')
    except IOError:
        print('Error: cannot open', filename)
        return

    # Add packets to the buffer
    packets = []
    seq_num = 0
    while True:
        data = file.read(512)
        if not data:
            break
        # append after covert to bytes
        packets.append(packet.createPacket(seq_num, data))
        seq_num += 1

    num_packets = len(packets)
    # print("{} downloaded".format(num_packets))
    window_size = set_window_size(num_packets)
    next_packet_to_send = 0
    base = 0

    # Start the file receiver thread
    _thread.start_new_thread(receiveAck, (sock,))

    while base < num_packets:
        receiveThread.acquire()
        # Send the max size of packets which can be send
        while next_packet_to_send < base + window_size:
            print('Sending packet', next_packet_to_send)
            if random.randint(0, 8) > 0:
                sock.sendto(packets[next_packet_to_send], (socket.gethostbyname(socket.gethostname()), 8080))
            next_packet_to_send += 1

        # Start timer
        if not max_waiting_time.isRunning():
            print('Starting timer')
            max_waiting_time.startTimer()

        # Wait until the timer stops or until an ACK is received
        while max_waiting_time.isRunning() and not max_waiting_time.wasTimeout():
            receiveThread.release()
            # print('Sleeping')
            time.sleep(0.05)
            receiveThread.acquire()

        if max_waiting_time.wasTimeout():
            # print('Timeout')
            max_waiting_time.stopTimer()
            next_packet_to_send = base
        else:
            print('Updating window size')
            window_size = set_window_size(num_packets)
        receiveThread.release()

    # Send empty packet as sentinel
    sock.sendto(packet.createEmptyPacket(), (socket.gethostbyname(socket.gethostname()), 8080))
    print('Downloaded!')
    file.close()


def receiveAck(sock):
    global receiveThread
    global base
    global max_waiting_time

    while True:
        pkt, _ = sock.recvfrom(512)
        ack, _ = packet.extractPacket(pkt)

        # print('Got ACK', ack)
        if ack >= base:
            receiveThread.acquire()
            base = ack + 1
            print('Base updated', base)
            max_waiting_time.stopTimer()
            receiveThread.release()


def set_window_size(num_packets):
    global base
    return min(4, num_packets - base)


def accept_incoming_connections():
    while True:
        client, client_address = SocketSERVER.accept()
        print("%s:%s has connected." % client_address)
        addresses[client] = client_address
        Thread(target=handle_new_client, args=(client,)).start()


def handle_new_client(client):  # Takes client socket as argument.
    counter = 0
    name = ""
    headder = ""
    while True:
        if counter == 0 or counter == 1:
            send_files_names()
        counter += 1
        message = client.recv(BUFSIZE)
        if not message is None:
            message = message.decode(FORMAT)

        if message == "":
            message = "[QUIT]"

        # Avoid messages before registering
        if message.startswith("[ALL]") and name:
            new_msg = message.replace("[ALL]", "[MSG]" + headder)
            send_message(new_msg, broadcast=True)
            continue
        if message.startswith("[FILEA]"):
            filename = message.split("]")[1]
            if filename in files:
                send_files(socketUDP, filename)
        if message.startswith("[REGISTER]"):
            name = message.split("]")[1]
            welcome = '[MSG]Welcome %s!' % name
            send_message(welcome, destination=client)
            message = "[MSG]%s has joined the chat!" % name
            send_message(message, broadcast=True)
            clients[client] = name
            headder = name + ": "
            send_clients()
            time.sleep(0.5)

            continue

        if message == "[QUIT]":
            client.close()
            try:
                del clients[client]
            except KeyError:
                pass
            if name:
                send_message("[MSG]%s has left the chat." % name, broadcast=True)
                send_clients()
            break

        # Avoid messages before registering
        if not name:
            continue
        try:
            msg_params = message.split("]")
            dest_name = msg_params[0][1:]
            dest_sock = find_client_socket(dest_name)
            if dest_sock:
                send_message(msg_params[1], prefix=headder, destination=dest_sock)

        except:
            print("Error parsing the message: %s" % message)


def send_clients():
    send_message("[CLIENTS]" + get_clients_names(), broadcast=True)


def send_files_names():
    global filecount
    if filecount != 0:
        pass
    send_files_("[FILES]" + get_files_names())


def get_files_names(separator=","):
    names = []
    for name in files:
        names.append(name)
    return separator.join(files)


def get_clients_names(separator=","):
    names = []
    for _, name in clients.items():
        names.append(name)
    return separator.join(names)


def find_client_socket(name):
    for client_sock, client_name in clients.items():
        if client_name == name:
            return client_sock
    return None


def send_files_(msg, prefix=""):
    send_msg = bytes(prefix + msg, FORMAT)
    for sock in clients:
        sock.send(send_msg)


def send_message(msg, prefix="", destination=None, broadcast=False):
    send_msg = bytes(prefix + msg, FORMAT)
    if broadcast:
        for sock in clients:
            sock.send(send_msg)
    else:
        if destination is not None:
            destination.send(send_msg)


if __name__ == '__main__':

    for file in os.listdir():
        if file.endswith(".txt") or file.endswith(".png") or file.endswith(".jpg") or file.endswith(
                ".pdf") or file.endswith(".jpeg"):
            files.append(file)
    try:
        SocketSERVER.listen(50)
        print("Server Started at {}:{}".format(HOST, PORT))
        print("Waiting for connection...")
        currentThread = Thread(target=accept_incoming_connections)
        currentThread.start()
        currentThread.join()

        SocketSERVER.close()
    except KeyboardInterrupt:
        print("Closing...")
