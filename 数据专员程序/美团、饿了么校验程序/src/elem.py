# -*- coding:utf-8 -*-
import io
import os
import re
import yaml
import pathlib
import logging
from openpyxl import Workbook
from datetime import datetime as dt
from src.lib.logger import error
from src.lib.yaml import SourceYaml, GlobalConfig, \
                        FileNameVerify, Platform, ExecFilesVerify
from src.lib.files import find_literal_value, layer_by_path, \
                        creat_store_file_path, match_city_name_from_str


class DataSource(object):
    def __init__(self, platform):
        """初始化各种规则和配置"""

        # 获取目录配置
        stream = io.open(GlobalConfig.pathConfig, "r", encoding='utf8')
        self.stream_data = yaml.load(stream, Loader=yaml.FullLoader)
        data_key = 'ele_data' if platform == Platform.ELEM else 'mt_data'
        store_key = 'ele_store' if platform == Platform.ELEM else 'mt_store'
        plat_name = '饿了么' if platform == Platform.ELEM else '美团'
        self.data = pathlib.Path(self.stream_data[data_key]["value"])
        self.store = pathlib.Path(self.stream_data[store_key]["value"])
        if str(self.data).strip() == str(self.store).strip():
            raise ValueError(f'{plat_name}数据路径和拆分结果路径不能一致！')

        # 日志路径
        self.log_dir = os.path.join(os.path.split(self.data)[0], f'{plat_name}问题日志')
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)

        # 根据文件名得到业务信息
        self.fileNameVerify = FileNameVerify(platform)


class EleDataVerify(DataSource):

    def __init__(self):
        super(EleDataVerify, self).__init__(Platform.ELEM)
        # 列出所有城市
        self.cityFolder = os.listdir(str(self.data))

        # 初始化excel日志保存器
        self.file_xlsx = Workbook()
        self.work_sheet = self.file_xlsx.active
        self.work_sheet.append(['时间', '业务', '城市', '错误描述'])
        log_name = ''.join([dt.now().strftime('%Y.%m.%d-%H.%M.%S'), '.error.xlsx'])
        self.log_path = os.path.join(self.log_dir, log_name)

        # 获取配置的所有文件规则，并整理成字典， 便于后续数据文件精准校验
        s_yaml = SourceYaml()
        self.configs = s_yaml.daily_templates_by_platform(Platform.ELEM)
        self.rule_dict = dict()
        for config in self.configs:
            rule_name = find_literal_value(config.rule)
            self.rule_dict[rule_name] = config.rule + '.' + config.type
            if len(config.pack) > 0:
                for pack in config.pack:
                    rule_name = find_literal_value(pack.rule)
                    self.rule_dict[rule_name] = '.*' + pack.rule + '.' + pack.type

        # 触发文件校验
        self.exec_verify = ExecFilesVerify(self.rule_dict)

    def verify_and_layer(self):
        """对每个城市数据一一进行匹配 校验 分层 最后放到对应目录"""
        # 为了提前创建空目录, 手动写个业务下的表集合, 除了压缩包的两个目录账单和骑手账单， 骑手信息
        file_name_split_list = ['KPI数据导出', '奖励明细', '出勤明细表']
        file_name_list = ['运单数据', '服务中心_评价', '出勤统计表', 'KPI问题单导出数据', '考勤明细', '修改考勤明细',
                          '骑手账单_配送费', '骑手账单_调整帐', '代理商账单_调整账', '代理商账单_配送费',
                          '骑手数据明细', 'data']

        for city in self.cityFolder:
            # 为每个业务每个城市先创建空目录
            for name in file_name_list:
                result = self.fileNameVerify.file_name_dict(name)
                creat_store_file_path(city_name=city, only_create=True,
                                      business=result['business'],
                                      root_path=self.store)
            for name in file_name_split_list:
                result = self.fileNameVerify.file_name_dict(name)
                for bus in result['business'].split('&'):
                    creat_store_file_path(city_name=city, only_create=True,
                                          business=bus,
                                          root_path=self.store)

            # 每个城市路径
            city_path = self.data.joinpath(city)
            if not city_path.is_dir():
                continue

            folder = city_path.joinpath('今日下载')
            file_info = {
                "cityName": city,
                "folder": folder,
                "write_log": self.write_log_to_excel,
                "fileNameVerify": self.fileNameVerify,
                "storePath": self.store,
                # 1, zip解压后, False: 设置不校验包内文件 2, 保证zip文件和非zip文件不能重复交叉校验
                "check_pack": False,
                # 代表执行到校验压缩包内数据文件，配合check_pack, 控制校验流程
                "is_pack_file": False
            }

            # 校验数据文件
            self.exec_verify.verify_file(file_info)

            # 校验压缩包文件及内部的数据文件
            self.exec_verify.verify_pack(file_info)

        # 校验文件是否缺失和不唯一
        self.check_result_file_by_recursion()

        # 保存日志成excel
        self.file_xlsx.save(self.log_path)

    def write_log_to_excel(self, business, city_name, log_info):
        self.work_sheet.append([str(dt.now()), business, city_name, log_info])

    def check_result_file_by_recursion(self):
        # 递归遍历目录 校验结果文件是否缺失及除了20 22 24外其他目录下的结果文件是否唯一
        def check_result_file(path):
            dir_files = os.listdir(path)
            if path.split(os.path.sep)[-2][0].isdigit():
                city_name = path.split(os.path.sep)[-1]
                business = path.split(os.path.sep)[-2]
                suffix_num = re.findall('^\\d+', business)[0]
                if len(dir_files) == 0:
                    error(f'文件/文件夹缺失: {path}')
                    self.write_log_to_excel(business, city_name, f'文件/文件夹缺失: {path}')
                elif len(dir_files) != 1 and int(suffix_num) not in [20, 22, 24]:
                    error(f'文件不唯一: {path}')
                    self.write_log_to_excel(business, city_name, f'文件不唯一: {path}')
            else:
                for elem in dir_files:
                    new_path = os.path.join(path, elem)
                    if os.path.isdir(new_path):
                        check_result_file(new_path)

        check_result_file(str(self.store))


class MtDataVerify(DataSource):

    def __init__(self):
        super(MtDataVerify, self).__init__(Platform.MT)
        self.t_dirs = os.listdir(str(self.data))

        logging.basicConfig(filemode='w')
        self.logger = logging.getLogger('美团数据校验拆分_logger')
        self.logger.setLevel(level=logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s: %(message)s')
        log_name = ''.join([dt.now().strftime('%Y.%m.%d-%H.%M.%S'), '.error.txt'])
        file_handler = logging.FileHandler(os.path.join(self.log_dir, log_name))
        file_handler.setLevel(level=logging.INFO)
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)

    def verify_and_layer(self):
        """对T1 T2目录下文件夹处理"""

        # 创建空目录
        self.create_empty_dir_by_recursion()

        # 循环T-1 T-2目录
        for t_dir in self.t_dirs:
            t_path = self.data.joinpath(t_dir)
            if not t_path.is_dir():
                continue

            # 每个业务目录
            for business in os.listdir(t_path):
                bus_path = t_path.joinpath(business)
                if not bus_path.is_dir():
                    continue

                # 解析路径
                bus_info = {
                    "logger": self.logger,
                    "business": business,
                    "store_path": self.store,
                    "bus_path": os.path.join(t_path, business),
                    "fileNameVerify": self.fileNameVerify,
                }

                # 执行校验分层
                layer_by_path(bus_info)

        # 检查结果文件
        self.check_result_file_by_recursion()

    def create_empty_dir_by_recursion(self):
        def create_empty_dir(path):
            dir_files = os.listdir(path)
            dirs = path.split(os.path.sep)
            # 1  业务-文件
            if dirs[-1][0].isdigit():
                suffix_num = int(re.findall('^\\d+', dirs[-1])[0])
                if int(suffix_num) == 1:
                    creat_store_file_path(only_create=True,
                                          is_bus=True,
                                          business=dirs[-1],
                                          root_path=self.store)

            # 2  业务-城市-文件    /
            # 26  28  29  38  39 40 14 业务-今日下载-文件
            if dirs[-2][0].isdigit():
                suffix_num = int(re.findall('^\\d+', dirs[-2])[0])
                if int(suffix_num) == 2:
                    creat_store_file_path(only_create=True,
                                          city_name=dirs[-1],
                                          business=dirs[-2],
                                          root_path=self.store)

                if int(suffix_num) in [26, 28, 29, 38, 39, 40, 14]:
                    creat_store_file_path(only_create=True,
                                          download_dir=dirs[-1],
                                          business=dirs[-2],
                                          root_path=self.store)

            # 4  5  10  18  业务-城市+站点-今日下载-文件 --> 业务-城市-站点-今日下载-文件  /
            # 19  30  31  32  41  业务-城市-今日下载-文件
            if dirs[-3][0].isdigit():
                suffix_num = int(re.findall('^\\d+', dirs[-3])[0])
                if int(suffix_num) in [4, 5, 10, 18]:
                    # 按城市拆分站点
                    city_name = match_city_name_from_str(dirs[-2])
                    creat_store_file_path(only_create=True,
                                          is_site=True,
                                          city_name=city_name,
                                          site_name=dirs[-2],
                                          download_dir=dirs[-1],
                                          business=dirs[-3],
                                          root_path=self.store)

                if int(suffix_num) in [19, 30, 31, 32, 41]:
                    creat_store_file_path(only_create=True,
                                          city_name=dirs[-2],
                                          download_dir=dirs[-1],
                                          business=dirs[-3],
                                          root_path=self.store)
            # 递归循环
            for elem in dir_files:
                new_path = os.path.join(path, elem)
                if os.path.isdir(new_path):
                    create_empty_dir(new_path)

        create_empty_dir(str(self.data))

    def check_result_file_by_recursion(self):
        # 递归遍历目录 校验结果文件是否缺失及结果文件是否唯一
        # 前面怎么根据业务创建的空目录 这里就怎么根据业务进行校验文件缺失和唯一
        # 如果手动删除拆分结果下的目录(非文件), 那检测不到该目录缺失
        def check_result_file(path):
            dir_files = os.listdir(path)
            dirs = path.split(os.path.sep)
            # 1  业务-文件
            if dirs[-1][0].isdigit():
                suffix_num = int(re.findall('^\\d+', dirs[-1])[0])
                if int(suffix_num) == 1:
                    if len(dir_files) == 0:
                        self.logger.error(f'文件缺失: {path}')
                    elif len(dir_files) != 1:
                        self.logger.error(f'文件不唯一: {path}')

            # 2  业务-城市-文件    /
            # 26  28  29  38  39 40 14 业务-今日下载-文件
            if dirs[-2][0].isdigit():
                suffix_num = int(re.findall('^\\d+', dirs[-2])[0])
                if int(suffix_num) in [2, 26, 28, 29, 38, 39, 40, 14]:
                    if len(dir_files) == 0:
                        self.logger.error(f'文件缺失: {path}')
                    elif len(dir_files) != 1:
                        self.logger.error(f'文件不唯一: {path}')

            # 4  5  10  18  业务-城市+站点-今日下载-文件 --> 业务-城市-站点-今日下载-文件  /
            # 19  30  31  32  41  业务-城市-今日下载-文件
            if dirs[-3][0].isdigit():
                suffix_num = int(re.findall('^\\d+', dirs[-3])[0])
                if int(suffix_num) in [19, 30, 31, 32, 41]:
                    if len(dir_files) == 0:
                        self.logger.error(f'文件缺失: {path}')
                    elif len(dir_files) != 1:
                        self.logger.error(f'文件不唯一: {path}')

            # 4  5  10  18 拆分后 --> 业务-城市-站点-今日下载-文件
            if dirs[-4][0].isdigit():
                suffix_num = int(re.findall('^\\d+', dirs[-4])[0])
                # 拆分后的目录多一层
                if int(suffix_num) in [4, 5, 10, 18]:
                    if len(dir_files) == 0:
                        self.logger.error(f'文件缺失: {path}')
                    elif len(dir_files) != 1:
                        self.logger.error(f'文件不唯一: {path}')

            for elem in dir_files:
                new_path = os.path.join(path, elem)
                if os.path.isdir(new_path):
                    check_result_file(new_path)

        check_result_file(str(self.store))


ele = EleDataVerify()
mt = MtDataVerify()
