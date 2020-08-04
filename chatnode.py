# from https://github.com/jstasiak/python-zeroconf/blob/master/examples/browser.py
from zeroconf import ServiceBrowser, Zeroconf, ServiceListener, ServiceInfo
import socket
from datetime import datetime

NODE_PORT = 15070
CLIENT_PORT = 16070

node_list = {}  # [ip_port_tuple, time_last_heard, time_last_ping, socket_to_node]
zeroconf = Zeroconf()
zeroconf.register_service(ServiceInfo(
    "_p2pchat._udp.local.",
    "Tommy's totally fake server._p2pchat._udp.local.",
    addresses=[socket.inet_aton(socket.gethostbyname(socket.gethostname()))],
    port=NODE_PORT,
    properties={},
    server="something_unique.local."
))


class ZeroconfListener(ServiceListener):
    def remove_service(self, zeroconf, type, name):
        node_list[type, name][3].close()
        del node_list[type, name]
        print("Service %s removed" % name)
        print(node_list)

    def add_service(self, zeroconf, type, name):
        service_info = zeroconf.get_service_info(type, name)
        ip_port_tuple = (socket.inet_ntoa(service_info.addresses[0]), service_info.port)

        print("Service %s added, service location: %s" % (name, ip_port_tuple))

        socket_to_node = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        node_list[type, name] = [ip_port_tuple, datetime.now(), datetime.now(), socket_to_node]

        send_ping(ip_port_tuple, node_list[type, name][3])
        print(node_list)


# browser =
ServiceBrowser(zeroconf, "_p2pchat._udp.local.", ZeroconfListener())


def send_ping(ip_port_tuple: tuple, socket_to_use: socket) -> None:
    socket_to_use.sendto(b'{"command": "PING"}', ip_port_tuple)


while True:
    try:
        failed_node = []

# TODO properly iteraate through dic
        for node_name, node in list(node_list):
            node_ip_port_tuple = node[0]
            node_time_last_heard = node[1]
            node_time_last_ping = node[2]
            node_socket_to_use = node[3]
            current_time = datetime.now()

            if abs((current_time - node_time_last_heard).total_seconds()) > 120.0:  # nothing heard in 120s
                failed_node.append(node)

            if abs((current_time - node_time_last_heard).total_seconds()) > 60.0:  # ping back every 60s
                send_ping(node_ip_port_tuple, node_socket_to_use)

        if not len(failed_node) == 0:
            for node_name, node in failed_node:
                print(f"Node {node_name} failed.")
                node[3].close()
                del node_list[node_name]
                print(node_list)

    except Exception as e:
        for _, node in node_list.items():
            node[3].close()

        zeroconf.unregister_all_services()
        zeroconf.close()
        exit(0)
