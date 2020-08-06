# from https://github.com/jstasiak/python-zeroconf/blob/master/examples/browser.py
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
SELECT_TIMEOUT = 1
SERVICE_NAME = "Tommy's PROFESSIONAL trouble maker._p2pchat._udp.local."

node_list = {}  # { server_name : [ip_port_tuple, time_last_heard, socket_to_node] }
reverse_node_list = {}  # { str(ip_port_tuple) : servername }

zeroconf = Zeroconf()


def send_ping(node: list, node_name: str = "") -> None:
    node[2].sendto(b'{"command": "PING"}', node[0])
    print("ping " + node_name)

def send_message(node: list, message_json: bytes, node_name: str = "") -> None:
    node[2].sendto(message_json, node[0])
    print("send " + message_json.decode("UTF-8") + " to " + node_name)


# maintain a list of active node
class ZeroconfListener:
    def remove_service(self, zeroconf, type, name):
        try:
            node_list[str(name)][2].close()

            ip_port_tuple_str = str(node_list[str(name)][0])
            del reverse_node_list[ip_port_tuple_str]

            del node_list[str(name)]
        except KeyError:
            print(f"fuck: ZeroconfListener.remove_service() cannot find {name} in survivor list.")
            return
        print(f"Service {name} removed @ {ip_port_tuple_str}")

    def add_service(self, zeroconf, type, name):
        service_info = zeroconf.get_service_info(type, name)
        ip_port_tuple = (socket.inet_ntoa(service_info.addresses[0]), service_info.port)
        socket_to_node = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        socket_to_node.setblocking(False)
        socket_to_node.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        socket_to_node.bind((socket.gethostbyname(socket.gethostname()), NODE_PORT))

        node_list[str(name)] = [ip_port_tuple, datetime.now(), socket_to_node]
        reverse_node_list[str(ip_port_tuple)] = str(name)
        send_ping(node_list[str(name)], str(name))
        print(f"Service {name} added @ {ip_port_tuple}")


#  discover via zeroconf
# browser =
# noinspection PyTypeChecker
ServiceBrowser(zeroconf, "_p2pchat._udp.local.", ZeroconfListener())


# publish over zeroconf
zeroconf.register_service(ServiceInfo(
    "_p2pchat._udp.local.",
    SERVICE_NAME,
    addresses=[socket.inet_aton(socket.gethostbyname(socket.gethostname()))],
    port=NODE_PORT,
    properties={},
))

ping_time = datetime.now()

try:
    while True:
        failed_node = []
        node_socket_list = []
        current_time = datetime.now()

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

        try:
            readable, writable, _ = select.select(node_socket_list, node_socket_list, node_socket_list, SELECT_TIMEOUT)

            if readable or writable:
                for source in readable:
                    # TODO here's data from other nodes, deal with it
                    # TODO Valid message detection
                    # TODO send message
                    # TODO frontend
                    # TODO filter out pingback
                    data, addr = source.recvfrom(1024)
                    data = data.decode('UTF-8')
                    print(reverse_node_list[str(addr)] + " > " + data)
                    try:
                        node_list[reverse_node_list[str(addr)]][1] = current_time
                        assert node_list[reverse_node_list[str(addr)]][1] == current_time
                    except KeyError:
                        print(f"fuck: cannot find {reverse_node_list[str(addr)]} when updating time_last_heard")
                for source in writable:
                    # TODO here's data to write, deal with it
                    pass

        except ValueError:
            print("fuck: ValueError")
        except OSError:
            print("fuck: OSError")

        # clean failed node
        if not len(failed_node) == 0:
            for node_name in failed_node:
                print(f"Node {node_name} failed.")
                node_list[node_name][2].close()
                del reverse_node_list[str(node_list[node_name][0])]
                del node_list[node_name]
                # print(node_list)

# except Exception as e:
#     zeroconf.unregister_all_services()
#     zeroconf.close()
#
#     for _, node in node_list.items():
#         node[2].close()
#
#     print(e)
#     exit(0)

except KeyboardInterrupt as e:
    print(e)
    exit(0)
finally:
    print("cleaning up")
    zeroconf.unregister_all_services()
    zeroconf.close()

    for _, node in node_list.items():
        node[2].close()