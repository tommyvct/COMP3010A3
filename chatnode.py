# from https://github.com/jstasiak/python-zeroconf/blob/master/examples/browser.py
import json
import sys

try:
    from zeroconf import ServiceBrowser, Zeroconf, ServiceListener, ServiceInfo
except ModuleNotFoundError:
    sys.path.append('/home/student/wus2/.local/lib/python3.6/site-packages')
    from zeroconf import ServiceBrowser, Zeroconf, ServiceListener, ServiceInfo

import select
import socket
from datetime import datetime

NODE_PORT = 25070
CLIENT_PORT = 26070
PING_EVERY = 5.0
FAIL_AFTER = 120.0
NODE_SELECT_TIMEOUT = 1
CLIENT_SELECT_TIMEOUT = 1
SERVICE_NAME = "Tommy's PROFESSIONAL trouble maker"
LAST_MESSAGE_SIZE = 5

node_list = {}  # { server_name : [ip_port_tuple, time_last_heard, socket_to_node] }
reverse_node_list = {}  # { str(ip_port_tuple) : servername }

zeroconf = Zeroconf()

telnet_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
telnet_server.setblocking(0)
telnet_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
telnet_server.bind((socket.gethostbyname(socket.gethostname()), CLIENT_PORT))
telnet_server.listen(5)
telnet_sockets_going_in = [telnet_server]
telnet_sockets_going_out = []


def send_ping(node: list, node_name: str = "") -> None:
    node[2].sendto(b'{"command": "PING"}', node[0])
    # print("I: ping " + node_name)


def send_message(name: str, message: str, node: list, node_name: str = "") -> None:
    message_json = f'{{"command": "MSG","message": "{message}","user": "{name}"}}'
    node[2].sendto(bytes(message_json.replace("\r\n", "\\n"), encoding='UTF-8'), node[0])
    print("I: send " + message_json.replace("\r\n", "\\n") + " to " + node_name)


def kick_client(s: socket) -> None:
    try:
        s.close()
        print("I: client kicked")
        telnet_sockets_going_out.remove(s)
        telnet_sockets_going_in.remove(s)
    except ValueError:
        pass


# maintain a list of active node
class ZeroconfListener:
    def remove_service(self, zeroconf, type, name):
        try:
            node_list[str(name)][2].close()

            ip_port_tuple_str = str(node_list[str(name)][0])
            del reverse_node_list[ip_port_tuple_str]

            del node_list[str(name)]
        except KeyError:
            # print(f"E: ZeroconfListener.remove_service() cannot find {name} in survivor list.")
            return
        print(f"I: Service {name} removed @ {ip_port_tuple_str}")

    def add_service(self, zeroconf, type, name):
        if name == (SERVICE_NAME + "._p2pchat._udp.local."):
            return
        service_info = zeroconf.get_service_info(type, name)
        ip_port_tuple = (socket.inet_ntoa(service_info.addresses[0]), service_info.port)
        socket_to_node = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        socket_to_node.setblocking(False)
        socket_to_node.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        socket_to_node.bind((socket.gethostbyname(socket.gethostname()), NODE_PORT))

        node_list[str(name)] = [ip_port_tuple, datetime.now(), socket_to_node]
        reverse_node_list[str(ip_port_tuple)] = str(name)
        print(f"I: Service {name} added @ {ip_port_tuple}")
        send_ping(node_list[str(name)], str(name))


#  discover via zeroconf
# browser =
# noinspection PyTypeChecker
ServiceBrowser(zeroconf, "_p2pchat._udp.local.", ZeroconfListener())

# publish over zeroconf
zeroconf.register_service(ServiceInfo(
    "_p2pchat._udp.local.",
    SERVICE_NAME + "._p2pchat._udp.local.",
    addresses=[socket.inet_aton(socket.gethostbyname(socket.gethostname()))],
    port=NODE_PORT,
    properties={},
))

ping_time = datetime.now()
last_messages = []
telnet_in_message_buffer = []

try:
    while True:
        failed_node = []
        node_socket_list = []
        current_time = datetime.now()
        telnet_out_message_buffer = []

        if len(last_messages) >= LAST_MESSAGE_SIZE:
            last_messages.clear()

        for node_name, node in node_list.copy().items():
            node_ip_port_tuple = node[0]
            node_time_last_heard = node[1]

            # nothing heard in 120s, fail it
            if abs((current_time - node_time_last_heard).total_seconds()) > FAIL_AFTER:
                failed_node.append(node_name)
            else:
                # node[2].setblocking(False)
                node_socket_list.append(node[2])

            # ping back every 60s

        if abs((current_time - ping_time).total_seconds()) > PING_EVERY:
            ping_time = datetime.now()
            for node_name, node in node_list.copy().items():
                send_ping(node_list[node_name], node_name)

        for node_name, node in node_list.copy().items():
            for message in telnet_in_message_buffer:
                message = message.decode("UTF-8").split('>', 1)
                send_message(message[0], message[1], node_list[node_name], node_name)

        # for message in telnet_in_message_buffer:
        #     message = message.decode("UTF-8").split('>', 1)
        #     send_message(source, message[0], message[1])


        try:
            readable = select.select(node_socket_list, [], [], NODE_SELECT_TIMEOUT)[0]

            for source in readable:
                data, addr = source.recvfrom(1024)
                data = data.decode('UTF-8')
                print("I: " + reverse_node_list[str(addr)] + " > " + data)
                data = json.loads(data)

                try:
                    if data["command"] == "PING":
                        pass
                    elif data["command"] == "MSG":
                        data = data["user"] + "> " + data["message"]
                        if data not in last_messages:
                            last_messages.append(data)
                            telnet_out_message_buffer.append(bytes(data, encoding='UTF-8'))  # display to clients
                    else:
                        raise KeyError
                except KeyError:
                    print(f"E: invalid data")

                try:
                    node_list[reverse_node_list[str(addr)]][1] = current_time
                    assert node_list[reverse_node_list[str(addr)]][1] == current_time
                except KeyError:
                    print(f"E: cannot find {reverse_node_list[str(addr)]} when updating time_last_heard")

        except UnicodeDecodeError:
            # print("E: invalid request")
            pass
        except OSError:  # socket closed right after select
            # print("E: OSError")
            pass
        except KeyError:
            # print("E: A node went down right after it's last response")
            pass

        telnet_in_message_buffer.clear()

        readable, writable, execptional = select.select(telnet_sockets_going_in, telnet_sockets_going_out,
                                                        telnet_sockets_going_in, CLIENT_SELECT_TIMEOUT)

        for s in readable:
            if s is telnet_server:  # handle new client
                new_client_connection_socket, new_client_address = s.accept()
                new_client_connection_socket.setblocking(0)
                print(f"I: Client {new_client_address} connected")
                new_client_connection_socket.sendall(b"Welcome!\r\nExample usage:\r\nyour name>your message\r\nType \'exit\' to exit\r\n\r\n")
                telnet_sockets_going_in.append(new_client_connection_socket)
                telnet_sockets_going_out.append(new_client_connection_socket)
            else:
                data = s.recv(1024)
                if data:
                    try:
                        if data.decode("UTF-8") == "exit\r\n":
                            s.sendall(b"Bye!\r\n")
                            kick_client(s)
                        elif not data.decode("UTF-8").find('>') == -1:
                            telnet_out_message_buffer.append(data)  # echo back the message
                            telnet_in_message_buffer.append(data)
                        else:
                            s.sendall(b"You didn't write your name!\r\n")
                    except UnicodeDecodeError: # Ctrl-Z, Ctrl-C, I don't know how to handle it so just kick him out
                        kick_client(s)
                else:
                    print("I: someone crashed!")
                    kick_client(s)

        try:
            for s in writable:
                for message in telnet_out_message_buffer:
                    s.sendall(message)
        except OSError:  # socket closed right after select
            pass

        telnet_out_message_buffer.clear()

        for s in execptional:
            print("I: someone crashed!")
            kick_client(s)

        # clean failed node
        if not len(failed_node) == 0:
            for node_name in failed_node:
                print(f"I: Node {node_name} failed.")
                node_list[node_name][2].close()
                del reverse_node_list[str(node_list[node_name][0])]
                del node_list[node_name]
                # print(node_list)

except KeyboardInterrupt as e:
    print(e)
    exit(0)

finally:
    print("I: cleaning up")
    zeroconf.unregister_all_services()
    zeroconf.close()

    for _, node in node_list.items():
        node[2].close()

    for s in telnet_sockets_going_in:
        s.close()

    for s in telnet_sockets_going_out:
        s.close()

    telnet_server.close()
