# coding=utf-8
# author: Lan_zhijiang
# description: http command finder
# date: 2022/4/9

from api.local.local_caller import LocalCaller


class CommandFinder:

    def __init__(self, base_abilities, caller, user_type, com_code=None):

        self.local_caller = LocalCaller(base_abilities, caller, user_type, com_code)

        self.all_command_list = {
            "user_login": self.local_caller.user_login,
            "user_logout": self.local_caller.user_logout,
            "user_sign_up": self.local_caller.user_sign_up,
            "user_info_update": self.local_caller.user_info_update,
            "user_info_get_all": self.local_caller.user_info_get_all,
            "user_info_get_one_multi": self.local_caller.user_info_get_one_multi,
            "user_info_get_multi_multi": self.local_caller.user_info_get_multi_multi,
            "get_com_info": self.local_caller.get_com_info,
            "get_enterprise_info": self.local_caller.get_enterprise_info,
            "get_candidate_info": self.local_caller.get_candidate_info,
            "set_apply_job": self.local_caller.set_apply_job,
            "candidate_is_interview_end": self.local_caller.candidate_is_interview_end,
            "candidate_is_interview_started": self.local_caller.candidate_is_interview_started
        }
