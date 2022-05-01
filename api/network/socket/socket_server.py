# coding=utf-8
# author: Lan_zhijiang
# description Websocket Server(实际上是socket)
# date: 2022/4/21

import socket
import threading
import json
from universal.log import Log
from api.network.socket.socket_handler import SocketHandler

parent_log = None
settings = json.load(open("./data/json/setting.json", "r", encoding="utf-8"))


def run_server(p_l):

    """
    启动Socket服务器
    :return:
    """
    log = Log(p_l, "SocketServer")
    log.add_log("Start socket server...", 1)

    global parent_log
    parent_log = p_l

    log.add_log("socket listening on: %s" % setting["socketBindIp"] + ":%s" % setting["socketPort"], 1)
    websocket_server = socket.socket()
    websocket_server.bind(('0.0.0.0', setting["socketPort"]))
    websocket_server.listen(5)
    log.add_log("server start, wait for client connecting...", 1)
    while True:
        conn, addr = websocket_server.accept()
        thread = threading.Thread(target=receive_new_conn, args=(conn, addr))
        thread.setDaemon(True)
        thread.start()


def receive_new_conn(conn, addr):
    SocketHandler(parent_log, addr).handle_conn(conn)


class SocketServer:

    def __init__(self, parent_log):

        self.parent_log = parent_log

    def run_server(self):

        """
        启动服务器
        :return
        """
        run_server(self.parent_log)

