# coding=utf-8
# socket_client.py
# author: Lan_zhijiang
# mail: lanzhijiang@foxmail.com
# lastEditedDate: 2022/5/1
# description: socket client | socket通信客户端
import socket
import threading
import time
from universal.log import ParentLog
from universal.log import Log


class SocketClient:

    def __init__(self, ba):

        self.ba = ba
        self.parent_log = ba.parent_log
        self.log = Log(self.parent_log, "SocketClient")

        # self.server_url = self.setting["wsUrl"]
        # self.server_port = self.setting["wsPort"]
        self.server_url = ""
        self.server_port = 5025
        self.account = ""
        self.client_type = ""
        self.account_token = ""
        self.online = True

        self.socket_conn = None
        self.res_handler = {}
        self.req_handler = {}

    def send(self, string):

        """
        发送
        """
        try:
            self.socket_conn.send(string.encode("utf-8"))
        except OSError:
            self.online = False
            self.log.add_log("lost connection with server, try to reconnect", 1)
            self.connect_to_server(re_connect=True)

    def recv(self, length):

        """
        接收
        """
        try:
            return self.socket_conn.recv(length).decode("utf-8")
        except OSError:
            self.online = False
            self.log.add_log("lost connection with server, try to reconnect", 1)
            self.connect_to_server(re_connect=True)

    def parse_recv(self, recv):

        """
        解析接收的信息
        :param recv: 接收的信息
        :return:
        """
        if recv is None:
            self.log.add_log("error message, None Type", 3)
            return None, None, None
        try:
            a = recv.split("?")
            command, param_raw = a[0], a[1]
            b = command.split(":")
            command_type, command = b[0], b[1]
        except IndexError:
            return None, None, None
        param = {}
        param_raw = param_raw.split("&")
        try:
            for i in param_raw:
                i_split = i.split("=")
                param[i_split[0]] = i_split[1]
        except IndexError:
            pass
        return command, command_type, param

    def connect_to_server(self, re_connect=False):

        """
        连接到服务器
        :return:
        """
        self.log.add_log("start connect to the ws-server-%s" % self.server_url, 1)
        self.socket_conn = socket.socket()
        self.socket_conn.connect((self.server_url, self.server_port))

        # auth
        self.send("req:auth?account=%s&token=%s&userType=%s" % (self.account, self.account_token, self.client_type))
        recv = self.recv(1024)
        command, command_type, param = self.parse_recv(recv)
        if command_type == "res":
            if param["code"] == "0":
                self.log.add_log("auth success, socket connection with server-%s has established" % self.server_url, 1)
                if not re_connect:
                    heartbeat_thread = threading.Thread(target=self.heartbeat_start, args=())
                    communicate_thread = threading.Thread(target=self.communicate, args=())
                    heartbeat_thread.start()
                    communicate_thread.start()
            else:
                self.log.add_log("auth not pass, fail to establish the connection", 3)
        else:
            self.log.add_log("wrong response, it should be ", 3)

    def communicate(self):

        """
        開始交流（維持連接）
        :return
        """
        self.log.add_log("start communicate with server-%s" % self.server_url, 1)
        while True:
            # wait command
            recv = self.recv(1024)
            self.log.add_log("WsHandler: receive message from server, start handle", 0)
            # parse command
            command, command_type, param = self.parse_recv(recv)
            if command is None or command_type is None:
                self.send("res:res?code=1&msg=wrong format of message")
            else:
                self.last_heartbeat_time_stamp = self.parent_log.get_time_stamp()
                if command_type == "req":
                    handle_func = self.recv_command
                elif command_type == "res":
                    handle_func = self.recv_response
                else:
                    a = "res:%s?code=1&msg=wrong format of request" % command
                    self.send(a)
                    return
                handle_thread = threading.Thread(target=handle_func, args=(command, param))
                handle_thread.start()

    def recv_command(self, command, param):

        """
        处理接受到的指令
        :param command: 指令
        :param param: 参数
        """
        if command == "heartbeat":
            self.send("res:heartbeat?code=0&msg=done")
            return
        self.log.add_log("recv_command-%s" % command, 1)
        # command supported: pre_call call final_call result_publish
        self.req_handler[command](param, self)

    def recv_response(self, command, response):

        """
        处理响应
        :param command: 响应的指令
        :param response: 返回
        """
        self.log.add_log("recv_response-%s from server" % command, 1)
        try:
            self.res_handler[command](response, self)
        except KeyError:
            if command == "heartbeat":
                if response["code"] == 0:
                    self.log.add_log("heartbeat success", 0)
            else:
                # normal handle
                self.common_recv_response(response)

    def common_recv_response(self, response):

        """
        通用响应处理
        :param response: 响应
        """
        self.log.add_log("common_recv_response is now process response", 1)
        if response["code"] != "0":
            self.log.add_log("command execute not success, response is %s" % response["code"], 3)
        return

    def send_command(self, command, param, res_func=None):

        """
        发送指令
        :param command: 命令
        :param param: 参数
        :param res_func: 接受响应的函数
        :return
        """
        self.log.add_log("send_command-%s to server" % command, 1)
        if res_func is None:
            res_func = self.common_recv_response

        param_str = ""
        for i in list(param.keys()):
            param_str = param_str + "%s=%s" % (i, param[i]) + "&"
        param_str = param_str[0:-1]

        send_str = "req:%s?%s" % (command, param_str)
        self.send(send_str)
        if res_func is not None:
            self.res_handler[command] = res_func

    def send_response(self, command, param):

        """
        发送响应
        :param command: 响应的指令
        :param param: 参数
        :return
        """
        self.log.add_log("send_response for command-%s" % command, 1)
        param_str = ""
        for i in list(param.keys()):
            param_str = param_str + "%s=%s" % (i, param[i]) + "&"
        param_str = param_str[0:-1]

        send_str = "res:%s?%s" % (command, param_str)
        self.send(send_str)

    def heartbeat_start(self):

        """
        进行心跳
        :return
        """
        self.log.add_log("start heartbeat now", 1)
        while True:
            self.send("req:heartbeat?")
            time.sleep(5)
