# coding=utf-8
# author: Lan_zhijiang
# description: Log class
# date: 2022/4/9

import json
import time
import datetime
import os
import sys
from queue import Queue

setting_path = r"./data/json/log_setting.json"


class Log:

    def __init__(self):

        self.logLevelList = [
           "DEBUG", "INFO", "WARNING", "ERROR", "FATAL"
        ]
        self.log_setting = json.load(open(setting_path, "r", encoding="utf-8"))
        self.log_queue = Queue()

    def get_log_file_path(self):

        """
        获取log文件路径
        :return:
        """
        basic_path = self.log_setting["logPath"]
        log_file_name = self.get_date() + ".log"
        if os.path.exists(basic_path + log_file_name) is False:
            create_log_file = open(basic_path + log_file_name, "w")
            create_log_file.close()
        else:
            pass
        return basic_path + log_file_name

    def get_time_stamp(self):

        """
        获取当前时间戳，整数化字符化
        :return:
        """
        return str(int(time.time()))

    def get_date(self):

        """
        获取当前日期
        :return:
        """
        return str(datetime.date.today())

    def get_formatted_time(self, format_string=None):

        """
        获取格式化的时间
        :param format_string: 格式化要求
        :return:
        """
        if format_string is None:
            format_string = "%H:%M:%S"
        return time.strftime(format_string)

    def add_log(self, content, level, logger=None, is_print=True, add_period=True):

        """
        添加log
            先添加到队列里面，超过一定数量再写入
        :param level: log级别  0: DEBUG 1: INFO 2: WARNING 3: ERROR(当前任务可能停止) 4: FATAL: 主线程退出
        :param content: log内容
        :param logger: 记录者
        :param is_print: 是否打印(为False时优先级高于设置)
        :param is_period: 是否添加句号
        :return:
        """
        if logger is None:
            logger = "DefaultLogger"
        log = "[%s] %s %s: %s" % (self.logLevelList[level], self.get_formatted_time(), logger.name, content)

        if add_period:
            log = log + " ."
        if is_print:
            print(log)
        else:
            if level >= self.log_setting["displayLevel"]:
                print(log)

        if level > 3:
            self.write_log()
            sys.exit()
        if self.log_queue.qsize() >= self.log_setting["write"]:
            self.write_log()
        return

    def write_log(self):

        """
        读取log并进行写入
        :return:
        """
        for i in range(0, self.log_queue.qsize()):
            log = self.log_queue.get()
            try:
                log_file = open(self.get_log_file_path(), "a")
                log_file.write(log + '\r\n')
                log_file.close()
            except IOError:
                print("[WARNING] %s Log:"
                      "Can't write into the log file, please check the permission or is the path correct!"
                      % self.get_formatted_time())
                break


class Logger:

    def __init__(self, name):

        self.name = name

    def __str__(self):

        return self.name
