import io
import os
import yaml
import pathlib
import configparser
from enum import Enum
from src.lib.logger import debug, error
from src.lib.files import files_by_regex
from src.lib.zip import unzip

lib_path = os.path.dirname(os.path.abspath(__file__))


class GlobalConfig:
    # 资源目录 校验多个城市的目录的数据 要处理
    pathConfig = pathlib.Path(os.path.join(lib_path, "path_config.yml"))
    # 文件匹配规则
    config = pathlib.Path(os.path.join(lib_path, "config.yml"))
    # 业务匹配规则
    source = pathlib.Path(os.path.join(lib_path, "data_source.yml"))
    # 文件名称校验规则
    ele_file_dict = pathlib.Path(os.path.join(lib_path, "ele_file_dict.ini"))
    # 美团的校验控制
    mt_file_dict = pathlib.Path(os.path.join(lib_path, "mt_file_dict.ini"))

    # @staticmethod
    # def get_file_path(file):
    #     return folder.join(file)
    #
    # @staticmethod
    # def is_file_exist(file):
    #     return folder.join(file).is_file()
    #
    # @staticmethod
    # def is_file_exist_by_regex(folder, regex):
    #     files = GlobalConfig.match_files(folder, regex)
    #     if len(files) == 0:
    #         return False
    #     else:
    #         return True
    #
    # @staticmethod
    # def match_files(path, regex):
    #     # 文件列表
    #     files = []
    #     # 遍历目录中的文件，
    #     for file in os.listdir(str(path)):
    #         # 匹配规则
    #         match = re.match(regex, file)
    #         # 按照文件命名规则匹配文件, 如果未匹配到文件，则继续执行
    #         if match == None:
    #             continue
    #
    #         files.append(file_path)
    #
    #     # 获取匹配文件的结果数量，如果不等于零，则返回匹配到的文件列表
    #     return files


# 平台类型
class Platform(Enum):
    ELEM = 1
    MT = 2


# 模版对象
class Template:
    def __init__(self, code, name, rule=None, type=None, pack=[]):
        self.code = code    # 标示
        self.name = name    # 名称

        self.rule = rule    # 文件匹配规则
        self.type = type    # 文件类型, 'csv', 'zip', 'xls', 'xlsx'

        # 压缩包内容
        self.pack = self.load_pack(pack)
        # 文件列表
        self.files = []

    def load_config(self, rule, type, pack=[]):
        '''加载配置文件'''
        self.rule = rule
        self.type = type
        self.pack = self.load_pack(pack)

    def load_pack(self, pack=[]):
        '''加载压缩包文件'''
        if pack == None or len(pack) == 0:
            return []

        result = []
        for item in pack:
            info = item.get(self.code)
            result.append(
                Template(
                    info.get('code'),
                    info.get('name'),
                    info.get('rule'),
                    info.get('type')
                )
            )
        return result


class ConfigYaml:
    def __init__(self):
        stream = io.open(GlobalConfig.config, "r", encoding='utf8')
        self.data = yaml.load(stream, Loader=yaml.FullLoader)

    def config_by_code(self, code):
        return self.data[0].get(code, None)


class SourceYaml:
    def __init__(self):
        stream = io.open(GlobalConfig.source, "r", encoding='utf8')
        self.data = yaml.load(stream, Loader=yaml.FullLoader)

    def data_by_platform(self, platform: Platform):
        '''根据平台获取业务规则配置'''
        if platform == Platform.ELEM:
            return self.data[1]
        if platform == Platform.MT:
            return self.data[0]

    def daily_templates_by_platform(self, platform: Platform):
        '''根据平台，获取配置数据'''
        data = self.data_by_platform(platform)
        if len(data) <= 0:
            return []

        # 获取配置文件
        configs = ConfigYaml()
        result = []
        for item in data['daily_templates']:
            config = configs.config_by_code(str(item['code']))
            if config is not None:
                result.append(
                    Template(
                        item.get('code'),
                        item.get('name'),
                        config.get('rule'),
                        config.get('type'),
                        config.get('pack'),
                    )
                )
        return result


class FileNameVerify(object):

    def __init__(self, platform):
        self.is_ele = (platform == Platform.ELEM)
        if self.is_ele:
            file_dict = GlobalConfig.ele_file_dict
        else:
            file_dict = GlobalConfig.mt_file_dict
        self.cf = configparser.ConfigParser()
        self.cf.read(file_dict, encoding='utf8')

    def file_name_dict(self, file_name):
        if file_name in self.cf.sections():
            result = {
                'business': self.cf.get(file_name, "business"),
                'layer': self.cf.get(file_name, "layer"),
                'field': self.cf.get(file_name, "field"),
            }
            if self.is_ele:
                result['other'] = self.cf.get(file_name, "other")
            else:
                result['number'] = self.cf.get(file_name, "number")

            return result
        else:
            return False


class ExecFilesVerify(object):

    def __init__(self, rule_dict):
        self.rule_dict = rule_dict

    def verify_file(self, file_info):
        res_files = files_by_regex(file_info, self.rule_dict)
        if not res_files:
            error(f"数据文件有问题, 城市: {file_info['cityName']}")
        else:
            debug(f"匹配到数据文件, 城市: {file_info['cityName']}, 数据文件: {res_files}")

    def verify_pack(self, file_info):
        # 设置True, 校验压缩包
        file_info["check_pack"] = True
        # 获取压缩包的文件列表
        files = self.fetch_files_by_unzip(file_info)

        # 解压后, 设置True, 校验压缩包内数据文件
        file_info["is_pack_file"] = True
        res_files = files_by_regex(file_info, self.rule_dict, files)

        # 判断压缩内的文件是否匹配成功
        if not res_files:
            error(f"解压出来的数据文件都有问题, 城市: {file_info['cityName']}")
        else:
            debug(f"匹配到解压出来的数据文件, 城市: {file_info['cityName']}, 数据文件: {res_files}")

    # 根据压缩包规则，获取压缩包，解压缩，并获取解压缩后的文件列表
    def fetch_files_by_unzip(self, file_info):
        # 文件路径，解压zip包, 获取压缩包文件
        unzip_files = files_by_regex(file_info, self.rule_dict)
        if not unzip_files:
            error(f"解压前, zip压缩包文件不存在, 城市: {file_info['cityName']}")
            return False
        else:
            debug(f"解压前, 匹配到zip压缩包, 城市: {file_info['cityName']}, 压缩包: {unzip_files}")

        result = []

        # 遍历压缩包文件
        for file in unzip_files:
            # 解压缩文件，解压缩到目录中
            unzip_list = unzip(file_info['folder'].joinpath(file), file_info['folder'])
            if len(unzip_list) == 0:
                error('压缩包文件解压为空: ' + file)
                continue
            else:
                # 合并所有解压缩的文件   压缩包内文件
                result.extend(unzip_list)

        return result
