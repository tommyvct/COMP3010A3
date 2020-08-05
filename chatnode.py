# from https://github.com/jstasiak/python-zeroconf/blob/master/examples/browser.py
import sys

try:
    from zeroconf import ServiceBrowser, Zeroconf, ServiceListener, ServiceInfo
except ModuleNotFoundError:
    sys.path.append('/home/student/wus2/.local/lib/python2.7/site-packages')
    from zeroconf import ServiceBrowser, Zeroconf, ServiceListener, ServiceInfo

import select
import socket
from datetime import datetime

NODE_PORT = 15070
CLIENT_PORT = 16070
PING_EVERY = 60.0
FAIL_AFTER = 120.0

node_list = {}  # { server_name : [ip_port_tuple, time_last_heard, socket_to_node] }

zeroconf = Zeroconf()


# maintain a list of active node
class ZeroconfListener:
    def remove_service(self, zeroconf, type, name):
        node_list[str(name)][3].close()
        del node_list[str(name)]
        print("Service %s removed" % name)
        # print(node_list)

    def add_service(self, zeroconf, type, name):
        service_info = zeroconf.get_service_info(type, name)
        ip_port_tuple = (socket.inet_ntoa(service_info.addresses[0]), service_info.port)

        print("Service %s added" % name)

        socket_to_node = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        socket_to_node.setblocking(False)
        node_list[str(name)] = [ip_port_tuple, datetime.now(), socket_to_node]
        send_ping(node_list[str(name)], str(name))

        # send_ping(ip_port_tuple, node_list[str(name)][3])
        # print(node_list)


#  discover via zeroconf
# browser =
# noinspection PyTypeChecker
ServiceBrowser(zeroconf, "_p2pchat._udp.local.", ZeroconfListener())


def send_ping(node: list, node_name: str = "") -> None:
    node[2].sendto(b'{"command": "PING"}', node[0])
    print("ping " + node_name)


# publish over zeroconf
zeroconf.register_service(ServiceInfo(
    "_p2pchat._udp.local.",
    "Tommy's ultimate trouble maker._p2pchat._udp.local.",
    addresses=[socket.inet_aton(socket.gethostbyname(socket.gethostname()))],
    port=NODE_PORT,
    properties={},
    server="something_unique.local."
))

ping_time = datetime.now()

while True:
    try:
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

        readable, writable, _ = select.select(node_socket_list, node_socket_list, node_socket_list, 1)

        if readable or writable:
            for source in readable:
                # TODO here's data from other nodes, deal with it
                # TODO FIX it
                data, addr = source.recvfrom(2048)
                print(str(addr) + " > " + data.decode('UTF-8'))
            for source in writable:
                # TODO here's data to write, deal with it
                pass

        # clean failed node
        if not len(failed_node) == 0:
            for node_name in failed_node:
                print(f"Node {node_name} failed.")
                node_list[node_name][3].close()
                del node_list[node_name]
                # print(node_list)

    except Exception as e:
        zeroconf.unregister_all_services()
        zeroconf.close()

        for _, node in node_list.items():
            node[2].close()

        print(e)
        exit(0)

    except KeyboardInterrupt as e:
        zeroconf.unregister_all_services()
        zeroconf.close()

        for _, node in node_list.items():
            node[2].close()

        print(e)
        exit(0)
