# COMP3010A3: Distributed Chat System

## Overview
This program is a node for a peer-to-peer chat system, akin to IRC. The chat nodes present themselves using ZeroConf to the other nodes, have TCP clients they maintain, and as they get messages from those clients the nodes get send share the messages across the network.

If a message has not been sent from a known peer has not been heard after 2 minutes, the program should assume it has crashed, and it will be removed from the known node list.

## How to run it
`python3 chatnode.py`

### Mandatory Modification Needed
In the beginning of ther file, there are a few predefined constants.

1. `NODE_PORT`: port used to communicate with other nodes
2. `CLIENT_PORT`: port used to communicate with telnel clients
3. `PING_EVERY`: frequency of pinging known working nodes, in seconds
4. `FAIL_AFTER`: if a node didn't send back anything within given time, it will be deemed as dead
5. `NODE_SELECT_TIMEOUT`: timeout value used in `socket.select()` function for polling data from known nodes
6. `CLIENT_SELECT_TIMEOUT`: timeout value used in `socket.select()` function for polling data from connected telnet clients
7. `SERVICE_NAME`: the service named used to annouce over the network, must bu unique
8. `LAST_MESSAGE_SIZE`: control the size of history chat list, used to eliminate possible duplication

## How to connect a client to the chat node
Once the program is configured, the program will list some important informations:
```
Zeroconf service name: Tommy's PROFESSIONAL trouble maker
Zeroconf port: 25070
Hostname: Mac-Pro.local -> 127.0.0.1
Telnet client port: 26070
To connect, run 'telnet Mac-Pro.local 26070'
```
Open another terminal and run `telnet Mac-Pro.local 26070`:
```
Trying 127.0.0.1...
Connected to localhost.
Escape character is '^]'.
Welcome!
Example usage:
your name>your message
Type 'exit' to exit
```
You are now connected to the node!

## How to cleanly exit your chat client
There are several ways to do it:
1. Recommended: by type `exit`
2. Press <kbd>Ctrl</kbd> + <kbd>C</kbd> or <kbd>Ctrl</kbd> + <kbd>Z</kbd> 
3. Escape to telnet shell then <kbd>Ctrl</kbd> + <kbd>C</kbd>

## How to cleanly shut down your chat node
<kbd>Ctrl</kbd> + <kbd>C</kbd>.

Note that there is a chance of <kbd>Ctrl</kbd> + <kbd>C</kbd> on `socket.select()`, which will give you a full screen off error messages. But it's fine. Sockets are set to non-blocking and addresses are set to reusable. There's a `finally` statement at the bottom of ther file, which covers most of the processing logic. If something did went wrong, it will handle the socket clean up work.