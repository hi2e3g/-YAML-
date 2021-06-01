import pandas as pd
import zipfile
import os
import city_check
import re

def unzip(path_input):
    mark_zip = ".zip"
    for root, dirs, files in os.walk(path_input):
        for file in files:
            zip_path = os.path.join(root, file)
            res = zip_path.split('\\')
            if os.path.splitext(zip_path)[-1] == mark_zip:
                # print("解压并删除压缩包:",zip_path)
                z = zipfile.ZipFile(zip_path, 'r')
                z.extractall(root)
                z.close()
                os.remove(zip_path)
            else:
                pass


# 检查是否有异常格式的文件
def special_suffix_check(path_input):
    mark_suffix = [".csv", ".xlsx", ".xls", ".xlsm", ".xlsb", ".xlt"]
    for root, dirs, files in os.walk(path_input):
        for file in files:
            path = os.path.join(root, file)
            suffix = os.path.splitext(path)[-1]
            if suffix in mark_suffix:
                pass
            else:
                print("文件格式有误，请查看该文件：", path)


# 新增城市列函数
def add_city_column(path_input, team_id_dict, err_log):
    mark_csv = ".csv"
    for root, dirs, files in os.walk(path_input):
        for file in files:
            path = os.path.join(root, file)
            res = path.split('\\')
            if os.path.splitext(path)[-1] == mark_csv:
                df = pd.read_csv(path)
                """ 调用 """
                _path = get_city_name(os.path.splitext(path)[0])
                check_work = city_check.MakingSamples(_path)
                """ end """
                if check_work.check_team_city_57(df, team_id_dict, '团队ID'):
                    df["下载城市"] = res[-2]

                    df.to_csv(path, index=False)
                    print("Right:", res[-2])
                    # print(df.head(2))
                else:
                    print("error:", res[-2])
                    err_log.write_log_to_excel(
                        {'business': '57', 'city': os.path.splitext(path)[0], 'err': '所在城市不在已有字典表格中'}
                    )

            else:
                df = pd.read_excel(path)
                """ 调用 """
                _path = get_city_name(os.path.splitext(path)[0])
                check_work = city_check.MakingSamples(_path)
                """ end """
                if check_work.check_team_city_57(df, team_id_dict, '团队ID'):
                    df["下载城市"] = res[-2]
                    df.to_excel(path, index=False)
                    print("right:", res[-2])
                else:
                    print("error:", res[-2])
                    err_log.write_log_to_excel(
                        {'business': '57', 'city': os.path.splitext(path)[0], 'err': '所在城市不在已有字典表格中'}
                    )


def key_to_dict(df, key_col, val_col):
    redict, _dict = {}, df.to_dict(orient='records')
    for _ in _dict:
        redict.update({str(_.get(key_col)): _.get(val_col)})
    return redict


def get_city_name(file_path):
    _file_word = file_path.split('\\')
    return _file_word


if __name__ == "__main__":
    """ 实例化日志 """
    err = city_check.Makelog()
    err.open_excel()
    err_path=r".\5b_add_city_column_log.csv"
    path_teamid = r".\station_id-city.csv"
    df_city = pd.read_csv(path_teamid)
    df_city_dict = key_to_dict(df_city, '站点ID', '城市')
    # 填写"5B数据分析-运单详情"文件夹的地址，复制到path后边
    path_delivery_details=r"F:\饿了么1月23日测试数据\5B数据分析-运单详情\上海"
    # 解压
    unzip(path_delivery_details)
    # 文件后缀检查
    special_suffix_check(path_delivery_details)
    # 新增列操作
    add_city_column(path_delivery_details,df_city_dict, err)
    # add_city_column(path_service_comment)
    """ 都执行完成后保存日志 """
    err.save_log(err_path)
    print("DONE")
