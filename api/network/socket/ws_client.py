# coding=utf-8
# ws_client.py
# author: Lan_zhijiang
# mail: lanzhijiang@foxmail.com
# date: 2022/04/27
# description: socket client | socket通信客户端
import socket
import threading
import time
from universal.log import Logger


class WsClient:

    def __init__(self, ba):

        self.ba = ba
        self.log = ba.log
        self.logger = Logger("SocketClient")

        # self.server_url = self.setting["wsUrl"]
        # self.server_port = self.setting["wsPort"]
        self.server_url = ""
        self.server_port = 5025
        self.account = ""
        self.client_type = ""
        self.account_token = ""

        self.socket_conn = None
        self.res_handler = {}
        self.req_handler = {}

    def send(self, string):

        """
        发送
        """
        try:
            self.ws.send(string.encode("utf-8"))
        except OSError:
            self.log.add_log("lost connection with server, try reconnect", 1, logger=self.logger)
            self.connect_to_server()

    def recv(self, length):

        """
        接收
        """
        try:
            return self.ws.recv(length).decode("utf-8")
        except OSError:
            self.log.add_log("lost connection with server, try reconnect", 1, logger=self.logger)
            self.connect_to_server()

    def connect_to_server(self, re_connect=False):

        """
        连接到服务器
        :return:
        """
        self.log.add_log("start connect to the ws-server-%s" % self.server_url, 1, logger=self.logger)
        self.ws = socket.socket()
        self.ws.connect((self.server_url, self.server_port))

        # auth
        self.send("req:auth?account=%s&token=%s&userType=%s" % (self.account, self.account_token, self.client_type))
        recv = self.recv(1024)
        a = recv.split("?")
        command, param_raw = a[0], a[1]
        b = command.split(":")
        command_type, command = b[0], b[1]
        param = {}
        param_raw = param_raw.split("&")
        for i in param_raw:
            i_split = i.split("=")
            param[i_split[0]] = i_split[1]
        if command_type == "res":
            if param["code"] == "0":
                self.log.add_log("auth success, websocket connection has established", 1, logger=self.logger)
                if not re_connect:
                    heartbeat_thread = threading.Thread(target=self.heartbeat_start, args=())
                    communicate_thread = threading.Thread(target=self.communicate, args=())
                    heartbeat_thread.start()
                    communicate_thread.start()
            else:
                self.log.add_log("auth not pass, fail to establish the connection", 3)

    def communicate(self):

        """
        開始交流（維持連接）
        :return
        """
        self.log.add_log("start communicate with server-%s" % self.server_url, 0)
        while True:
            # wait command
            recv = self.recv(1024)
            self.log.add_log("WsHandler: receive message from server, start handle", 0)
            # parse command
            try:
                a = recv.split("?")
                command, param_raw = a[0], a[1]
                b = command.split(":")
                command_type, command = b[0], b[1]
                param = {}
                param_raw = param_raw.split("&")
                try:
                    for i in param_raw:
                        i_split = i.split("=")
                        param[i_split[0]] = i_split[1]
                except IndexError:
                    self.log.add_log("WsHandler: param is empty", 1, logger=self.logger)
            except IndexError:
                self.send("res:res?code=1&msg=wrong format of request")
            else:
                self.last_heartbeat_time_stamp = self.log.get_time_stamp()
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
        self.log.add_log("recv_command-%s" % command, 1, logger=self.logger)
        # command supported: pre_call call final_call result_publish
        if command == "final_end_interview":
            pass
        elif command == "skip":
            self.main.event_skip_handle(param["nextCandidateCode"])

    def recv_response(self, command, response):

        """
        处理响应
        :param command: 响应的指令
        :param response: 返回
        """
        self.log.add_log("recv_response-%s from server" % command, 1, logger=self.logger)
        try:
            self.wait_res_command[command](response)
        except KeyError:
            pass
            # normal handle
            if command == "heartbeat":
                if response["code"] == 0:
                    self.log.add_log("heartbeat success", 0)
            elif command == "waiting_end":
                self.main.next_candidate = response["nextCandidateCode"]
                self.main.refresh_called_list()
            elif command == "init_waiting":
                self.main.next_candidate = response["nextCandidateCode"]
                self.main.refresh_called_list()
        else:
            self.common_recv_response(response)

    def common_recv_response(self, response):

        """
        通用响应处理
        :param response: 响应
        """
        self.log.add_log("WsHandler: common_recv_response is now process response", 1, logger=self.logger)
        if response["code"] != "0":
            self.log.add_log("WsHandler: command execute not success, response is %s" % response["code"], 3)
        return

    def send_command(self, command, param, res_func=None):

        """
        发送指令
        :param command: 命令
        :param param: 参数
        :param res_func: 接受响应的函数
        :return
        """
        self.log.add_log("send_command-%s to server" % command, 1, logger=self.logger)

        param_str = ""
        for i in list(param.keys()):
            param_str = param_str + "%s=%s" % (i, param[i]) + "&"
        param_str = param_str[0:-1]

        send_str = "req:%s?%s" % (command, param_str)
        self.send(send_str)
        if res_func is not None:
            self.wait_res_command[command] = res_func

    def send_response(self, command, param):

        """
        发送响应
        :param command: 响应的指令
        :param param: 参数
        :return
        """
        self.log.add_log("send_response for command-%s" % command, 1, logger=self.logger)
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
        self.log.add_log("start heartbeat now", 1, logger=self.logger)
        while True:
            self.send("req:heartbeat?")
            time.sleep(5)
