# coding=utf-8
# author: Lan_zhijiang
# description Websocket Server(实际上是socket)
# date: 2022/4/21

import socket
import threading
from api.ws.ws_handler import OIISBackendWsHandler

log_class = {}
settings = {}


def run_server(b_a):

    """
    启动服务器
    :return:
    """
    setting = b_a.setting
    b_a.log.add_log("WsServer: Start websocket server...", 1)

    global base_abilities
    base_abilities = b_a

    b_a.log.add_log("WsServer: socket listening on: %s" % setting["bindIp"] + ":%s" % setting["wsPort"], 1)
    # websocket_server = websockets.serve(receive_new_conn, '0.0.0.0', setting["wsPort"])
    websocket_server = socket.socket()
    websocket_server.bind(('0.0.0.0', setting["wsPort"]))
    websocket_server.listen(5)
    b_a.log.add_log("WsServer: server start, wait for client connecting...", 1)
    while True:
        conn, addr = websocket_server.accept()
        thread = threading.Thread(target=receive_new_conn, args=(conn, addr))
        thread.setDaemon(True)
        thread.start()


def receive_new_conn(conn, addr):
    OIISBackendWsHandler(base_abilities, addr).handle_conn(conn)
    # await ws.send("end_conn?")
    # await ws.close(reason="normal close")


class WsServer:

    def __init__(self, ba):

        self.ba = ba

    def run_server(self):

        """
        启动服务器
        :return
        """
        run_server(self.ba)

