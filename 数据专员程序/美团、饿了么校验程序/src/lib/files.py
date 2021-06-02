import os
import re
import shutil
import pathlib
import random
import traceback
import pandas as pd
import datetime as dt
from enum import Enum
from src.lib.logger import debug, error


class FileErrorType(Enum):
    # 正确文件
    FileGood = 0
    # 文件匹配/名称校验错误
    FileNotMatch = 1
    # 文件为空
    FileIsEmpty = 2
    # 文件城市与目录城市不符
    FileCityNotMatch = 3


# 获取文件目录
# def folder_path(file):
#     path = pathlib.Path(file)
#     return str(path.parent)


# 饿了么 根据路径和匹配规则获取文件列表
def files_by_regex(file_info, rule_dict, unzip_files_list=None):
    """
    All files are checked this way,
    Correct files to copy and save to new directory for
    hierarchical categorization # error log TXT

    """
    # 文件列表
    files = []

    folder = file_info["folder"]
    city_name = file_info["cityName"]
    write_log = file_info['write_log']
    check_pack = file_info['check_pack']
    is_pack_file = file_info['is_pack_file']

    # 遍历目录中的文件
    files_list = unzip_files_list if unzip_files_list else os.listdir(folder)
    for file_name in files_list:
        # 如果是目录则跳过校验
        file_path = folder.joinpath(file_name)
        if os.path.isdir(file_path):
            continue

        # 压缩包的数据文件(带全路径)
        # windows
        if isinstance(file_name, pathlib.WindowsPath):
        # mac
        # if isinstance(file_name, pathlib.PosixPath):
            file_path = str(file_name)
            file_name = os.path.basename(file_path)
            split_path = os.path.split(os.path.dirname(file_path))
            file_info['pack_name'] = split_path[1]

        # 执行zip包数据不跑数据文件, 防止重复校验
        if check_pack and not str(file_name).endswith('.zip'):
            # 压缩包数据文件校验下， 取消数据文件限制
            if not is_pack_file:
                continue

        # 执行数据文件/非zip文件不跑zip的文件, 防止重复校验
        if not check_pack and str(file_name).endswith('.zip'):
            continue

        # 先获取business信息
        file_info['file_path'] = file_path
        match_verify_res = match_file_name_verify(file_name, rule_dict, file_info)

        # 判断文件名是否匹配
        if match_verify_res is False:
            err_info = f'文件匹配/名称校验错误, {file_path}'
            error(err_info)
            write_log('文件匹配/名称校验失败, 无法匹配到对应业务名', city_name, err_info)
            continue

        elif match_verify_res and isinstance(match_verify_res, dict):
            """这里非zip文件、表名匹配的文件成功的才执行校验城市和分层存储"""

            # 判断文件大小是否为0
            if is_file_empty(file_path):
                err_info = f'文件大小为0, {file_path}'
                error(err_info)
                write_log(match_verify_res['business'], city_name, err_info)
                continue

            match_verify_res.update(file_info)

            # 文件转df
            df = file_to_df(file_path)
            # if not df.empty: 校验城市时处理空文件
            # 如果是内容为空只有表头的文件 不执行城市校验
            # 校验文件城市和目录城市是否一致, 如果是多sheet的文件返回其business和file_name
            verify_city_result = verify_file_city(df, match_verify_res, file_path)
            if isinstance(verify_city_result, bool) and not verify_city_result:
                # 日志和存储文件在方法内输出
                continue

            # 执行存储
            excel_csv_file_store(match_verify_res, verify_city_result, file_name, file_path)

        files.append(file_name)

    # 获取匹配文件的结果数量，如果不等于零，则返回匹配到的文件列表
    return files


# 判断文件是否为空
def is_file_empty(path):
    size = os.stat(path).st_size
    if size == 0:
        return True
    else:
        return False


def find_literal_value(str_value):
    # 正则匹配出文件名称中的文字内容
    re_list = re.findall('[\u4e00-\u9fa5]+_[\u4e00-\u9fa5]+', str(str_value))
    if len(re_list) == 0:
        re_list = re.findall('骑手信息', str(str_value))
        if len(re_list) == 0:
            re_list = re.findall('K?P?I?[\u4e00-\u9fa5]+', str(str_value))
            if len(re_list) == 0:
                re_list = re.findall('data', str(str_value))
                if len(re_list) == 0:
                    return False

    return re_list[-1]


# 校验文件名称
def verify_name_by_business(file_name, file_info):
    fnv = file_info["fileNameVerify"]
    check_pack = file_info["check_pack"]
    file_name_match = find_literal_value(file_name)
    if not file_name_match:
        return False

    try:
        if not check_pack:
            file_dict = fnv.file_name_dict(file_name_match)
            if file_name_match == '骑手信息':
                have_city = set(os.path.splitext(file_name.strip())[0]) \
                            - set(str(file_name_match).strip())
                if len(have_city) == 0:
                    # 如果骑手信息  --->  改成 城市骑手信息
                    file_dict.update({'rider_file_name': ''.join([file_info['cityName'],
                                      file_name_match, '.xlsx'])})

            return file_dict

        else:
            if str(file_name).endswith('.zip'):
                # 检查包名，然后获取business再保存一份zip包
                file_dict = fnv.file_name_dict(file_name_match)
                save_to_path(file_name=file_name,
                             is_back=True,
                             file_path=file_info['file_path'],
                             business=file_dict['business'],
                             root_path=file_info['storePath'],
                             is_bus=file_dict['layer'] == 'business')
                return True

            # "校验压缩包名_文件名称 check_pack=True"
            pack = file_info['pack_name']
            pack_list = re.findall('[\u4e00-\u9fa5]+', str(pack))
            file_list = re.findall('[\u4e00-\u9fa5]+', str(file_name))
            pf_name = '_'.join([pack_list[0], file_list[0]])
            return fnv.file_name_dict(pf_name)

    except Exception as _:
        import traceback
        error(traceback.format_exc())
        return False


# 文件转df
def file_to_df(file_path):
    suffix = os.path.splitext(str(file_path))[1]
    try:
        if suffix == ".csv":
            try:
                df = pd.read_csv(file_path)
            except Exception as _:
                df = pd.read_excel(file_path)

        elif suffix == ".xls":
            try:
                df = pd.read_excel(file_path)
            except Exception as _:
                df = pd.read_csv(file_path)

        elif suffix == ".xlsx":
            df = pd.read_excel(file_path)

        else:
            df = None
    except Exception as _:
        df = None

    return df


def read_sheet(file_path):
    data_xls = pd.io.excel.ExcelFile(file_path)
    df_files = {}
    for sheet in data_xls.sheet_names:
        _df = pd.read_excel(file_path, sheet_name=sheet)
        df_files[sheet] = _df
    return df_files


def match_file_name_verify(file_name, rule_dict, file_info):
    # 找到文件对应的规则进行一对一匹配 不用重复匹配
    name = find_literal_value(file_name)
    regex = rule_dict[str(name).strip()]
    match = re.match(regex, str(file_name))
    # 按照文件命名规则匹配文件, 如果未匹配到文件，则false
    if match is None:
        return False

    # 校验文件名 返回业务名称等 否则False
    verify_res = verify_name_by_business(file_name, file_info)
    if not verify_res:
        return False

    return verify_res


def read_value_from_df(df, ver_data, file_path):
    # 防止df取值错误
    try:
        values = df[ver_data['field']]
    except Exception as _:
        try:
            df = pd.read_csv(file_path)
        except Exception as _:
            try:
                df = pd.read_excel(file_path)
            except Exception as _:
                return None

        values = df[ver_data['field']]

    # 清除空值行
    values = values.dropna()
    return values


# 饿了么的
def get_file_field_value(df, ver_data, file_path):
    values = read_value_from_df(df, ver_data, file_path)
    if values is None:
        return None, None

    for value in values:
        # 匹配整个值 如果为空继续从df列表中循环取下一个不为空的
        if not value:
            continue
        else:
            find_value = re.findall('[\u4e00-\u9fa5]+', str(value))
            if len(find_value) == 0:
                continue
            elif len(find_value) == 1:
                return find_value[0], None
            else:
                return find_value[0], find_value[1]


def verify_file_city(df, ver_data, file_path):
    # 只处理单个非zip文件
    bus_list = str(ver_data['business']).split('&')
    file_name = os.path.basename(file_path)
    write_log = ver_data['write_log']

    if df is None:
        err_info = f'文件内部数据格式不对, pandas无法打开读取, 跳过校验: {file_path}'
        error(err_info)
        write_log(str(bus_list), ver_data['cityName'], err_info)
        return False

    result = []

    if len(bus_list) == 1:
        if df.empty:
            # 表文件为空内容， 直接返回空的df 正常存储
            return df

        if ver_data['layer'] == 'site':
            _, site_name = get_file_field_value(df, ver_data, file_path)
            if site_name is None:
                err_info = f'文件通过pandas打开取值发生错误, 跳过校验: {file_path}'
                error(err_info)
                write_log(str(bus_list[0]), ver_data['cityName'], err_info)
                return False

            # 站点处理 返回站点名称
            return [
                {
                    # 'df': df,
                    'file_path': file_path,  # 直接拷贝
                    'site_name': site_name,
                    'is_site': True
                }
            ]
        else:
            return df

    elif len(bus_list) == 2:
        # 两个business的 有奖励明细多存一份和划线&强排处理
        if ver_data['other'] == '划线&强排':
            # assess_type 划线&强排  城市群 只有此处需要校验城市名称
            assess_type = random.choice(df['考核方式'])
            if assess_type == '划线':
                business = bus_list[0]
                result.append(
                    {
                        # 'df': df,
                        'file_path': file_path,
                        'business': business,
                    }
                )
            else:
                business = bus_list[1]
                result.append(
                    {
                        # 'df': df,
                        'file_path': file_path,
                        'business': business,
                    }
                )

            if not df.empty:
                # 内容为空 不校验城市 直接返回df和bus
                file_city_name, _ = get_file_field_value(df, ver_data, file_path)
                if file_city_name is None:
                    err_info = f'文件通过pandas打开取值发生错误, 跳过校验: {file_path}'
                    error(err_info)
                    write_log(business, ver_data['cityName'], err_info)
                    return False

                if not file_city_name.strip() == ver_data['cityName'].strip():
                    err_info = f'城市名称不匹配, {file_path}'
                    error(err_info)
                    write_log(business, ver_data['cityName'], err_info)
                    return False

        else:
            # other=save_two_addr 骑手奖励再保存原始文件一份 （文件名不用再校验, 已校验）
            save_to_path(file_name=file_name,
                         is_back=True,
                         city_name=ver_data['cityName'],
                         file_path=file_path,
                         business=bus_list[1],
                         root_path=ver_data['storePath'])

            # 返回df和对应的business, 后面会判断存储到分层路径
            result.append(
                    {
                        # 因为要转换成csv格式 不能直接拷贝 (清掉Unnamed的列)
                        'df': df.loc[:, ~df.columns.str.contains('^Unnamed')],
                        'is_back': False,  # 别的文件全都不该格式， 只有骑手奖励的奖励明细表改成csv
                        'business': bus_list[0]
                    }
                )

    else:
        # 出勤明细表 三个business
        # 拆分前， 先把源文件存储一份 （文件名不用再校验, 已校验）
        save_to_path(file_name=file_name,
                     is_back=True,
                     city_name=ver_data['cityName'],
                     file_path=file_path,
                     business=bus_list[2],  # 第三位为原文件的业务名称
                     root_path=ver_data['storePath'])

        # 拆分sheet 校验存储
        # if ver_data['other'] == 'sheet1&sheet2': 只有此一种情况
        # 需要拆分sheet 再判断 返回新business
        df_dict = read_sheet(file_path)

        # 循环sheet 处理每个sheet内容
        for sheet_name, df in df_dict.items():
            file_name = sheet_name + '.csv'

            ver_res = verify_name_by_business(sheet_name, ver_data)
            if ver_res is False and ver_res is not True:
                # ver_res里 已经包含了各sheet的业务名
                # sheet名称有问题
                err_info = f'sheet名称有问题, sheet名称: {sheet_name}, {file_path}'
                error(err_info)
                write_log(ver_res['business'], ver_data['cityName'], err_info)
                continue

            if df.empty:
                # 内容为空 不校验城市 直接分层存储保存sheet的内容成新表
                save_to_path(# 因为是sheet 需要通过df将其内容转成文件
                             df=df.loc[:, ~df.columns.str.contains('^Unnamed')],
                             file_name=file_name,
                             city_name=ver_data['cityName'],
                             root_path=str(ver_data['storePath']),
                             business=ver_res['business'])
                # 继续下一个sheet
                continue

            result.append(
                {
                    # 因为是sheet 需要通过df将其内容转成文件
                    'df': df.loc[:, ~df.columns.str.contains('^Unnamed')],
                    'business': ver_res['business'],
                    'file_name': file_name
                }
            )

        if len(result) == 0:
            return False

    return result


def save_to_path(**kwargs):
    df = kwargs.pop('df', None)
    file_path = kwargs.pop('file_path', None)
    target_path = creat_store_file_path(**kwargs)
    # if file_type == FileErrorType.FileGood:
    # 保存到分层目录
    if df is not None:
        # 只有骑手奖励和 考勤明细用到df保存到csv文件
        df.to_csv(target_path, index=False)
    else:
        # 保存zip包/不动格式的数据文件到对应业务 （适用于备份原文件）
        shutil.copyfile(str(file_path), target_path)


# 获取要存储文件的路径
def creat_store_file_path(is_site=False,
                          is_bus=False,
                          is_back=True,
                          only_create=False,
                          site_name=None,
                          business=None,
                          city_name=None,
                          file_name=None,
                          root_path=None,
                          download_dir=None):
    """
    use file_type, business, city, file_name return the path
    if not have path: makedirs
    """

    # normal
    # if file_type == FileErrorType.FileGood:
    if not download_dir:
        if is_bus:
            # 骑手信息/压缩包另存一份
            _dir = f'{business}'
        elif not is_site:
            # 城市
            _dir = f'{business}/{city_name}'
        else:
            # 站点
            _dir = f'{business}/{city_name}/{site_name}'
    else:
        if is_site:
            # 美团分层
            _dir = f'{business}/{city_name}/{site_name}/{download_dir}/'
        elif city_name:
            # 城市目录
            _dir = f'{business}/{city_name}/{download_dir}'
        else:
            # 业务+每日下载
            _dir = f'{business}/{download_dir}'

    # else:
        # # 问题文件存储路径  废弃
        # root_path = os.path.dirname(root_path)
        # root_path = os.path.join(root_path, '问题文件')
        # if file_type == FileErrorType.FileNotMatch:
        #     _dir = '文件匹配&名称校验错误'
        # elif file_type == FileErrorType.FileIsEmpty:
        #     _dir = '空文件'
        # else:
        #     _dir = '文件城市与目录城市不符'

    store_dir = os.path.join(root_path, _dir)
    if not os.path.exists(store_dir):
        os.makedirs(store_dir)

    # 仅创建目录
    if only_create is True:
        return

    if not is_back:
        # 后缀换成csv
        name, suffix = os.path.splitext(str(file_name).strip())
        if suffix != '.csv':
            file_name = ''.join([name, '.csv'])
        file_path = os.path.join(store_dir, file_name)
    else:
        # 另存一份的不用改后缀 保留原文件格式
        file_path = os.path.join(store_dir, file_name)

    return file_path


def excel_csv_file_store(verify_name_info, verify_city_result, file_name, file_path):

    # 正确的文件
    if isinstance(verify_city_result, pd.DataFrame):
        rf_name = verify_name_info.get('rider_file_name', None)
        save_to_path(# df=verify_cty_result,
                     file_path=file_path,
                     file_name=rf_name or file_name,
                     city_name=verify_name_info['cityName'],
                     root_path=str(verify_name_info['storePath']),
                     is_bus=verify_name_info.get('layer') == 'business',
                     business=verify_name_info['business'])
    else:
        # 拆分sheet出来的n个文件 或者  不同考核方式(划线&强排)处理
        for ver_dict in verify_city_result:
            save_to_path(file_path=file_path,
                         df=ver_dict.get('df', None),  # 兼顾骑手奖励和考勤明细的df转文件
                         city_name=verify_name_info['cityName'],
                         root_path=str(verify_name_info['storePath']),
                         is_site=ver_dict.get('is_site') or False,
                         is_back=ver_dict.get('is_back', True),
                         site_name=ver_dict.get('site_name') or None,
                         file_name=ver_dict.get('file_name') or file_name,
                         business=ver_dict.get('business') or verify_name_info['business'])


# 美团校验
def layer_by_path(bus_info):
    bus_name = bus_info['business']
    bus_path = bus_info['bus_path']
    store_path = bus_info['store_path']
    logger = bus_info['logger']
    filename_verify = bus_info['fileNameVerify']
    bus_dict = filename_verify.file_name_dict(bus_name)
    if bus_dict is False:
        # 找不到对应业务直接return
        return
    business_num = int(bus_dict['number'])

    # 14
    # 1  业务-文件
    # 2  业务-城市-文件
    # 19  30  31  32  41  业务-城市-今日下载-文件
    # 26  28  29  38  39 40 14 业务-今日下载-文件  14不做校验
    # 4  5  10  18  业务-城市+站点-今日下载-文件 ---> 业务-城市-站点-今日下载-文件（需要拆分到站点 其他只校验）

    def verify_file_by_recursion(business_num, file_path):
        if os.path.isfile(file_path):
            # 美团只有满足这是那个后缀才处理
            if os.path.splitext(file_path)[-1] in ['.csv', '.xls', '.xlsx']:
                file_name = os.path.basename(file_path)

                if business_num == 1:
                    bus_type = get_full_name_from_field(bus_dict, file_path)
                    if str(bus_type).strip() == '海葵' or bus_type is True:
                        # 正确记录
                        debug(f'匹配到{file_path}')
                        save_to_path(file_name=file_name,
                                     file_path=file_path,
                                     is_back=True,
                                     is_bus=True,
                                     business=bus_name,
                                     root_path=store_path)
                    else:
                        # 错误记录
                        logger.error(f'业务类型值不匹配, 业务类型值: {bus_type}, 正确值: 海葵, 文件路径: {file_path}')

                elif business_num == 2:
                    # 美团数据/T-2/2数据中心-订单详情查询-订单来源-美团/广州/订单详情_20201123_094800_8.xls
                    dir_city_name = os.path.split(os.path.dirname(file_path))[-1]
                    file_city_name = get_full_name_from_field(bus_dict, file_path)
                    if str(file_city_name).strip() == str(dir_city_name.strip()) or file_city_name is True:
                        # 正确记录
                        debug(f'匹配到{file_path}')
                        save_to_path(file_name=file_name,
                                     file_path=file_path,
                                     is_back=True,
                                     city_name=dir_city_name,
                                     business=bus_name,
                                     root_path=store_path)
                    else:
                        # 错误记录 存储
                        logger.error(f'文件夹城市名称不匹配, 目录城市: {dir_city_name}, 文件城市: '
                                     f'{file_city_name}, 文件路径: {file_path}')

                elif business_num in [19, 30, 31, 32, 41]:
                    # 美团数据 / T - 1 / 19A结算对账 - 配送员薪资工具 - 配送数据 - 考勤数据
                    # / 上海易即达网络科技有限公司【北京】 / 今日下载/考勤列表导出20年11月23日13时57分20秒.xlsx
                    dir_name = str(file_path).split(os.path.sep)[-3]
                    mid_down_name = str(file_path).split(os.path.sep)[-2]

                    if business_num == 19:
                        file_bus_name = get_full_name_from_field(bus_dict, file_path)
                        if str(file_bus_name).strip() == str(dir_name.strip()) or file_bus_name is True:
                            # 正确记录
                            debug(f'匹配到{file_path}')
                            save_to_path(file_name=file_name,
                                         file_path=file_path,
                                         is_back=True,
                                         city_name=dir_name,
                                         download_dir=mid_down_name,
                                         business=bus_name,
                                         root_path=store_path)
                        else:
                            # 错误记录
                            logger.error(f'加盟商名称不匹配, 文件夹名称: {dir_name}, 文件加盟商: '
                                         f'{file_bus_name}, 文件路径: {file_path}')
                    else:
                        # 30, 31, 32, 41,
                        if business_num == 41:
                            # 校验日期  单元格A2=当前日T-1
                            file_day = get_date_from_field(bus_dict, file_path)
                            right_day = day_reduce_one_day()
                            if str(file_day).strip() == str(right_day).strip() or file_day is True:
                                # 校验正确记录
                                debug(f'匹配到{file_path}')
                                save_to_path(file_name=file_name,
                                             file_path=file_path,
                                             is_back=True,
                                             city_name=dir_name,
                                             download_dir=mid_down_name,
                                             business=bus_name,
                                             root_path=store_path)
                            else:
                                # 错误记录 存储
                                logger.error(f'T-1日期不匹配, 正确值: {right_day}, 文件日期: '
                                             f'{file_day}, 文件路径: {file_path}')

                        else:
                            # 30 31 32
                            split_field = bus_dict['field'].split('&')
                            bus_dict1 = {'field': split_field[0]}
                            # 单元格C2/E2中【】里面的城市=文件夹中【】的城市
                            file_site_name = get_full_name_from_field(bus_dict1, file_path)
                            file_city_name = match_city_name_from_str(file_site_name)
                            city_dir_name = match_city_name_from_str(dir_name)

                            if str(file_city_name).strip() != str(city_dir_name).strip() and file_city_name is not True:
                                # 错误记录
                                logger.error(f'文件夹城市名称不匹配, 文件夹城市: {city_dir_name}, 文件城市:'
                                             f'{file_city_name}, 文件路径: {file_path}')
                            else:
                                # 正确记录 继续校验日期
                                # 校验日期  单元格A2=当前日T-1
                                bus_dict2 = {'field': split_field[1]}
                                file_day = get_date_from_field(bus_dict2, file_path)
                                right_day = day_reduce_one_day()
                                if str(file_day).strip() == str(right_day).strip() or file_day is True:
                                    # 都通过校验 才保存
                                    debug(f'匹配到{file_path}')
                                    save_to_path(file_name=file_name,
                                                 file_path=file_path,
                                                 is_back=True,
                                                 city_name=dir_name,
                                                 download_dir=mid_down_name,
                                                 business=bus_name,
                                                 root_path=store_path)
                                else:
                                    # 错误记录
                                    logger.error(f'T-1日期不匹配, 正确值: {right_day}, 文件日期: '
                                                 f'{file_day}, 文件路径: {file_path}')

                elif business_num in [26, 28, 29, 38, 39, 40, 14]:
                    # business + 每日下载
                    # 美团数据/T-1/26A业务管理-站点早会管理/今日下载/早会管理_姜雪_2020-11-23+10_09_35.xls
                    mid_down_name = str(file_path).split(os.path.sep)[-2]
                    if business_num == 14:
                        # 不校验直接保存
                        debug(f'匹配到{file_path}')
                        save_to_path(file_name=file_name,
                                     file_path=file_path,
                                     is_back=True,
                                     download_dir=mid_down_name,
                                     business=bus_name,
                                     root_path=store_path)

                    elif business_num == 29:
                        right_date = month_reduce_one_day()
                        file_date = match_file_name_date(file_name)
                        if str(file_date).strip() == str(right_date).strip():
                            # 正确记录
                            debug(f'匹配到{file_path}')
                            save_to_path(file_name=file_name,
                                         file_path=file_path,
                                         is_back=True,
                                         download_dir=mid_down_name,
                                         business=bus_name,
                                         root_path=store_path)
                        else:
                            # 错误记录
                            logger.error(f'当前月1日-T-1日期不匹配, 正确值: {right_date}, 文件名日期: '
                                         f'{file_date}, 文件路径: {file_path}')
                    else:
                        # 校验日期  单元格A2/J2=当前日T-1
                        file_day = get_date_from_field(bus_dict, file_path)
                        if file_day and bus_dict['field'] == '开始时间' and file_day is not True:
                            # 早会管理表 特殊处理
                            file_day = file_day.replace('-', '').split(' ')[0]

                        right_day = day_reduce_one_day()
                        if str(file_day).strip() == str(right_day).strip() or file_day is True:
                            # 正确记录
                            debug(f'匹配到{file_path}')
                            save_to_path(file_name=file_name,
                                         file_path=file_path,
                                         is_back=True,
                                         download_dir=mid_down_name,
                                         business=bus_name,
                                         root_path=store_path)
                        else:
                            # 错误记录
                            logger.error(f'T-1日期不匹配, 正确值: {right_day}, 文件日期: '
                                         f'{file_day}, 文件路径: {file_path}')
                else:
                    # [4，5 10  18]
                    # 美团数据 / T - 1 / 4业务管理 - 考勤管理（新）-考勤明细 - 导出骑手考勤明细数据 / 上海易即达【郑州】
                    # 总部企业基地站 / 今日下载 / 骑手考勤明细数据_19872144_20201123_151351.xlsx
                    # 5里是压缩包
                    site_dir_name = str(file_path).split(os.path.sep)[-3]
                    mid_down_name = str(file_path).split(os.path.sep)[-2]
                    # 上海易即达【郑州】总部企业基地站
                    city_name = match_city_name_from_str(str(site_dir_name))

                    if business_num in [5, 10]:
                        # 不校验 直接分城市分站点保存
                        debug(f'匹配到{file_path}')
                        save_to_path(file_name=file_name,
                                     file_path=file_path,
                                     is_back=True,
                                     is_site=True,
                                     city_name=city_name,
                                     site_name=site_dir_name,
                                     download_dir=mid_down_name,
                                     business=bus_name,
                                     root_path=store_path)

                    else:
                        # 先校验 单元格G2=对应的文件夹站点
                        split_field = bus_dict['field'].split('&')
                        bus_dict1 = {'field': split_field[0]}
                        site_name = get_full_name_from_field(bus_dict1, file_path)
                        if str(site_name).strip() != str(site_dir_name).strip() and site_name is not True:
                            # 错误记录 存储
                            logger.error(f'站点不匹配, 文件夹站点: {site_dir_name}, 文件站点: '
                                         f'{site_name}, 文件路径: {file_path}')
                        else:
                            # 再校验单元格（4）B2或（18）C2 = 日期当期天 - 1
                            bus_dict2 = {'field': split_field[1]}
                            file_day = get_date_from_field(bus_dict2, file_path)
                            right_day = day_reduce_one_day()
                            if file_day is True or str(file_day).strip() == str(right_day).strip():
                                # 正确记录 分层保存
                                debug(f'匹配到{file_path}')
                                save_to_path(file_name=file_name,
                                             file_path=file_path,
                                             is_back=True,
                                             is_site=True,
                                             city_name=city_name,
                                             site_name=site_dir_name,
                                             download_dir=mid_down_name,
                                             business=bus_name,
                                             root_path=store_path)
                            else:
                                # 错误记录
                                logger.error(f'T-1日期不匹配, 正确值: {right_day}, 文件日期: '
                                             f'{file_day}, 文件路径: {file_path}')

        else:
            # 递归每个文件
            for file in os.listdir(file_path):
                verify_file_by_recursion(business_num, os.path.join(file_path, file))

    # 递归触发
    verify_file_by_recursion(business_num, bus_path)


# 部分名称 城市名校验
def match_city_name_from_str(value):
    try:
        if not value:
            return ''

        if value is True:
            # 空表
            return True
        # '上海易即达【开封】苹果园站'  从目录中获取城市
        find_value_list = re.findall('【[\u4e00-\u9fa5]+】', str(value))
        value = re.findall('[\u4e00-\u9fa5]+', find_value_list[0])[0]
        return value
    except Exception as _:
        error(traceback.format_exc())
        return ''


# 获取全名称  城市字段/业务类型字段/站点字段/加盟商名称字段/日期字段
def get_full_name_from_field(bus_dict, file_path):
    try:
        # 从文件内容中获取指定字段的值
        df = file_to_df(file_path)
        if df is None:
            return ''

        if df.empty:
            return True

        values = read_value_from_df(df, bus_dict, file_path)
        if values is None:
            return ''

        for value in values:
            # 匹配整个值 如果为空继续从df列表中循环取下一个不为空的
            if not value:
                continue
            else:
                value = re.findall('.+', str(value))[0]
                return value
    except Exception as _:
        error(traceback.format_exc())
        return ''


# 获取全名称 日期字段 兼容日期值为汉字情况
def get_date_from_field(bus_dict, file_path):
    try:
        # 从文件内容中获取指定字段的值
        df = file_to_df(file_path)
        if df is None:
            return ''

        if df.empty:
            return True

        values = read_value_from_df(df, bus_dict, file_path)
        if values is None:
            return ''

        for value in values:
            # 匹配整个值 如果为空继续从df列表中循环取下一个不为空的
            if not value:
                continue
            else:
                value_f = re.findall('.+', str(value))[0]
                value = re.findall('[\u4e00-\u9fa5]+', value_f)
                if len(value) > 0:
                    continue

                return value_f
    except Exception as _:
        error(traceback.format_exc())
        return ''


# 表格名时间M-1-T-1校验
def match_file_name_date(file_name):
    try:
        # 'bm_jiangxue06_运营指标监测(新)_加盟站点_20201101_20201122_1606097339816.xlsx'
        # 从文件名称中获取日期  20201101_20201122
        file_date = re.findall('\\d{8}_\\d{8}', str(file_name))[0]
        return file_date
    except:
        error(traceback.format_exc())
        return ''


# 动态生成 20201101_20201122
def month_reduce_one_day():
    _day = dt.datetime.now() + dt.timedelta(days=-1)
    # _month = str(_day.month)
    # _day = str(_day)
    # tmonth_tday = '{}{}01_{}{}{}'.format(_day[:4], _month, _day[:4], _month, _day[8:10])
    tmonth_tday = '{}01_{}'.format(_day.strftime('%Y%m'), _day.strftime('%Y%m%d'))
    return tmonth_tday


# 动态生成 当前日T-1  20201122
def day_reduce_one_day():
    _day = dt.datetime.now() + dt.timedelta(days=-1)
    # _month = str(_day.month)
    # _day = str(_day)
    # tday = '{}{}{}'.format(_day[:4], _month, _day[8:10])
    tday = _day.strftime('%Y%m%d')
    return tday
