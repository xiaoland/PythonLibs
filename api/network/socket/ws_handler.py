# coding=utf-8
# author: Lan_zhijiang
# description: ws handler(实际上是socket)
# date: 2022/4/22

import time
import threading


class OIISBackendWsHandler:

    def __init__(self, ba, addr):

        self.ba = ba
        self.log = ba.log
        self.setting = ba.setting
        self.main = ba.main
        
        self.addr = addr
        # self.log.add_log("WsHandler: new connections from addr-%s" % addr)

        self.mongodb_manipulator = self.ba.mongodb_manipulator

        self.ws = ""
        self.client_code = ""
        self.client_type = ""
        self.status = "inactive"
        self.last_heartbeat_time_stamp = ""

        self.wait_res_command = {}

    def send(self, string):

        """
        发送
        """
        try:
            self.ws.send(string.encode("utf-8"))
        except OSError:
            self.status = "inactive"
            self.log.add_log("WsHandler: connection with %s_client-%s has closed by accident" % (self.client_type, self.client_code), 3)
            try:
                client_status_list = \
                    list(self.mongodb_manipulator.get_document("interview", "calling", {"_id": "client_status"}, 1))[0][
                        self.client_code]
                client_status_list[self.client_code] = "offline"
                self.mongodb_manipulator.update_many_documents("interview", "calling", {"_id": "client_status"},
                                                               {self.client_code: client_status_list})
                del self.ba.ws_conn_list[self.client_type][self.client_code]
            except KeyError:

                self.log.add_log("WsHandler: not connected?! can't find %s in list" % self.client_code, 3)

    def recv(self, length):

        """
        接收
        """
        try:
            return self.ws.recv(length).decode("utf-8")
        except OSError:
            self.status = "inactive"
            self.log.add_log("WsHandler: connection with %s_client-%s has closed by accident" % (self.client_type, self.client_code), 3)
            try:
                del self.ba.ws_conn_list[self.client_type][self.client_code]
                client_status_list = \
                list(self.mongodb_manipulator.get_document("interview", "calling", {"_id": "client_status"}, 1))[0][
                    self.client_code]
                client_status_list[self.client_code] = "offline"
                self.mongodb_manipulator.update_many_documents("interview", "calling", {"_id": "client_status"},
                                                               {self.client_code: client_status_list})
            except KeyError:
                self.log.add_log("WsHandler: not connected?! can't find %s in list" % self.client_code, 3)

    def auth(self, account, user_type, token):

        """
        进行认证
        :param account: 賬戶
        :param user_type: 用戶類型
        :param token: token
        :return bool
        """
        if user_type == "waiting_room":
            return True, "success"

        if self.mongodb_manipulator.is_collection_exist(user_type, account) is False:
            self.log.add_log("WsHandler: account not exists or format error, auth fail", 1)
            return False, "account not exist"

        is_online = self.mongodb_manipulator.parse_document_result(
            self.mongodb_manipulator.get_document(user_type, account, {"isOnline": 1}, 2),
            ["isOnline"]
        )[0]["isOnline"]
        if not is_online:
            self.log.add_log("HttpHandler: user-%s" % account + " haven't login yet", 1)
            return False, "user haven't login yet"

        # is token same
        real_token = self.mongodb_manipulator.parse_document_result(
            self.mongodb_manipulator.get_document(user_type, account, {"token": 1}, 2),
            ["token"]
        )[0]["token"]
        if real_token == token:
            # auth pass
            return True, "success"
        else:
            # auth fail, wrong token
            self.log.add_log("HttpHandler: wrong token, auth fail", 1)
            return False, "wrong token"

    def handle_conn(self, ws):

        """
        處理連接
        :param ws
        :return
        """
        self.log.add_log("WsHandler: receive new websocket conn", 1)
        self.last_heartbeat_time_stamp = self.log.get_time_stamp()
        recv = ws.recv(1024).decode("utf-8")
        self.log.add_log("WsHandler: receive command, start handle", 1)

        try:
            a = recv.split("?")
            command, param_raw = a[0], a[1]
            b = command.split(":")
            command_type, command = b[0], b[1]
            param = {}
            param_raw = param_raw.split("&")
            for i in param_raw:
                i_split = i.split("=")
                param[i_split[0]] = i_split[1]
        except IndexError:
            self.log.add_log("WsHandler: wrong format of message, close", 3)
            return
        else:
            if command == "auth":
                self.last_heartbeat_time_stamp = self.log.get_time_stamp()
                try:
                    account, token, user_type = param["account"], param["token"], param["userType"]
                except KeyError:
                    self.log.add_log("WsHandler: param not complete, close", 3)
                    return
                res, err = self.auth(account, user_type, token)
                if res:
                    # auth success, join self into list, can start communicate
                    self.log.add_log("WsHandler: auth success", 1)
                    a = "res:auth?code=0&msg=%s" % err
                    ws.send(a.encode("utf-8"))
                    if account in self.ba.lost_conn_list[user_type]:
                        self.ba.lost_conn_list[user_type].remove(account)

                    if user_type == "waiting_room":
                        if account == "5":
                            for i in range(1, 61):
                                self.ba.ws_conn_list[user_type]["com%s" % str(i)] = self
                        elif account == "6":
                            for i in range(61, 112):
                                self.ba.ws_conn_list[user_type]["com%s" % str(i)] = self
                    self.ba.ws_conn_list[user_type][account] = self
                    self.ws = ws

                    self.client_code = account
                    self.client_type = user_type
                    self.status = "active"

                    # database status update
                    client_status_list = list(self.mongodb_manipulator.get_document("interview", "calling", {"_id": "client_status"}, 1))[0]
                    client_status_list = client_status_list[user_type]
                    client_status_list[account] = "online"
                    self.mongodb_manipulator.update_many_documents("interview", "calling", {"_id": "client_status"}, {user_type: client_status_list})

                    self.log.add_log("WsHandler: %s_client-%s establish connection with server success" % (self.client_type, self.client_code), 1)
                    self.send("auth?code=0&msg=success")
                    # if user_type != "a_client":
                    #     self.ba.ws_conn_list["a_client"]["root"].send_command("client_online", {"clientType": user_type, "account": account})
                    auto_close_thread = threading.Thread(target=self.auto_close_conn, args=())
                    auto_close_thread.start()
                    self.communicate()
                else:
                    # auth failed
                    self.log.add_log("WsHandler: auth failed", 1)
                    a = "res:auth?code=1&msg=%s" % err
                    ws.send(a.encode("utf-8"))
            else:
                self.log.add_log("WsHandler: client don't send an auth, close", 2)
                ws.send("You fucking fool, you should tell me who you are first!".encode("utf-8"))

            return

    def communicate(self):

        """
        開始交流（維持連接）
        :return
        """
        self.log.add_log("WsHandler: start communicate with client-%s" % self.client_code, 0)
        while True:
            # wait command
            recv = self.recv(1024)
            # parse command
            self.log.add_log("WsHandler: receive message from client-%s, start handle" % self.client_code, 0)
            try:
                if recv is None:
                    self.log.add_log("WsHandler: error message, None Type", 3)
                    self.send("res:res?code=1&msg=wrong_req")
                    return
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
                    self.log.add_log("WsHandler: empty param", 0)
            except IndexError:
                self.log.add_log("WsHandler: wrong format of message", 3)
                self.send("res:res?code=1&msg=wrong_format_of_message")
            else:
                self.last_heartbeat_time_stamp = self.log.get_time_stamp()
                if command_type == "req":
                    self.recv_command(command, param)
                elif command_type == "res":
                    self.recv_response(command, param)
                else:
                    self.send("res:%s?code=1&msg=wrong format of request" % command)

    def recv_command(self, command, param):

        """
        处理接受到的指令
        :param command: 指令
        :param param: 参数
        """
        if command == "heartbeat":
            self.log.add_log("WsHandler: client-%s heartbeat success" % self.client_code, 0)
            self.send("res:heartbeat?code=0&msg=done")
            return

        self.log.add_log("WsHandler: recv_command-%s from client-%s" % (command, self.client_code), 1)
        if command == "interviewer_start_interview":
            self.main.interviewer_start_interview(param["candidateCode"], param["comCode"])
        elif command == "interviewer_end_interview":
            self.main.interviewer_end_interview(param["candidateCode"], param["comCode"])
        elif command == "start_waiting":
            self.main.l3_waiting_start_handle(param["comCode"], param["candidateCode"])
        elif command == "end_waiting":
            self.main.l3_waiting_end_handle(param["comCode"], param["candidateCode"])
        elif command == "overtime_for_next_to_come":
            self.main.l3_overtime_for_next_to_come_handle(param["comCode"], param["candidateCode"])
        elif command == "init_waiting":
            self.main.l3_init_waiting_handle(param["comCode"])

    def recv_response(self, command, response):

        """
        处理响应
        :param command: 响应的指令
        :param response: 返回
        """
        self.log.add_log("WsHandler: recv_response-%s from client-%s" % (command, self.client_code), 1)
        try:
            self.wait_res_command[command](response)
        except KeyError:
            pass
            # normal handle
        else:
            self.log.add_log("WsHandler: receive sent command-%s's response" % command, 1)

    def common_recv_response(self, response):

        """
        通用响应处理
        :param response: 响应
        """
        self.log.add_log("WsHandler: common_recv_response is now process response", 1)
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
        self.log.add_log("WsHandler: send_command-%s to client-%s" % (command, self.client_code), 1)
        if res_func is None:
            res_func = self.common_recv_response
        param_str = ""
        for i in list(param.keys()):
            param_str = param_str + "%s=%s" % (i, param[i]) + "&"
        param_str = param_str[0:-1]

        send_str = "req:%s?%s" % (command, param_str)
        self.send(send_str)
        self.wait_res_command[command] = res_func

    def send_response(self, command, param):

        """
        发送响应
        :param command: 响应的指令
        :param param: 参数
        :return
        """
        self.log.add_log("WsHandler: send_response to client-%s" % self.client_code, 1)
        param_str = ""
        for i in list(param.keys()):
            param_str = param_str + "%s=%s" % (i, param[i]) + "&"
        param_str = param_str[0:-1]

        send_str = "res:%s?%s" % (command, param_str)
        self.send(send_str)

    def auto_close_conn(self):

        """
        检验心跳时间，超时则断开
        :return
        """
        self.log.add_log("WsHandler: start auto_close_conn", 1)
        while True:
            now_time_stamp = self.log.get_time_stamp()
            time_loss = int(now_time_stamp) - int(self.last_heartbeat_time_stamp)
            if time_loss > 10:
                self.log.add_log("WsHandler: auto_close_conn: heartbeat has stopped for too long, close connection", 2)
                self.ws.close()
                self.status = "inactive"
                break
            time.sleep(30)

        try:
            self.ba.lost_conn_list[self.client_type].append(self.client_code)
            del self.ba.ws_conn_list[self.client_type][self.client_code]
        except KeyError:
            self.log.add_log("WsHandler: client-%s has already down and closed socket connection" % self.client_code, 1)

    def start_count(self, com_code):

        """
        开始面试计时（仅interviewer）
        :param com_code: 面试终端编号
        :return
        """
        self.log.add_log("WsHandler: start interviewer_client-%s's interview count" % self.client_code, 1)

        in_queue_candidate_list = self.mongodb_manipulator.parse_document_result(
            self.mongodb_manipulator.get_document("interview", "now", {"_id": com_code}, 1),
            ["interviewQueue"]
        )[0]["interviewQueue"]["wait"]
        now_interview_phase = self.ba.get_interview_phase()
        next_candidate_code = None
        for i in list(in_queue_candidate_list.keys()):
            j = in_queue_candidate_list[i]
            next_candidate_code = j["candidateCode"]
            if j["interviewPhase"] == now_interview_phase:
                next_candidate_code = j["candidateCode"]
            if next_candidate_code is None:
                next_candidate_code = j["candidateCode"]

        time.sleep(180)
        # pre call the next candidate
        if next_candidate_code is not None:
            self.main.pre_call(next_candidate_code)
        else:
            self.log.add_log("WsHandler: next_candidate is None, maybe there are no more candidates", 1)
            if not list(in_queue_candidate_list.keys()):
                self.log.add_log("WsHandler: no more candidates, all has been done", 1)
                self.send_command("final_end_interview", {})
            else:
                self.log.add_log("WsHandler: interviewQueue-wait is not empty but no more candidates to interview, "
                                 "database may meet error!", 3)

