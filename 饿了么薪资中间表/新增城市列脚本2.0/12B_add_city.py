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
    mark_suffix = [".csv"]
    for root, dirs, files in os.walk(path_input):
        for file in files:
            path = os.path.join(root, file)
            suffix = os.path.splitext(path)[-1]
            if suffix in mark_suffix:
                continue
            else:
                print("文件格式有误，请查看该文件：", path)


# 数据清洗
def clear_data(df):
    df = df.applymap(lambda x: str(x).strip('"'))
    df = df.applymap(lambda x: str(x).strip('='))
    df = df.applymap(lambda x: str(x).strip('"'))
    df = df.applymap(lambda x: str(x).strip('——'))
    return df
def excel_merge(path_input):
    filename_excel = []
    frames = []
    df_all=pd.DataFrame()
    for root, dirs, files in os.walk(path_input):
        for file in files:
            filename_excel.append(os.path.join(root,file))
            df = pd.read_excel(os.path.join(root,file)) #excel转换成DataFrame
            df=df[["下载城市","运单号"]]
            frames.append(df)
#合并所有数据
    df_all = pd.concat(frames)
    return df_all

def csv_merge(path_input):
    filename_csv = []
    frames = []
    df_all=pd.DataFrame()
    for root, dirs, files in os.walk(path_input):
        for file in files:
            path=os.path.join(root,file)
            filename_csv.append(path)
            df = pd.read_csv(path) #excel转换成DataFrame
            df=df[["下载城市","运单号"]]
            frames.append(df)
#合并所有数据
    df_all = pd.concat(frames)
    return df_all
#团队ID和城市转为字典
def key_to_dict(df, key_col, val_col):
    redict, _dict = {}, df.to_dict(orient='records')
    for _ in _dict:
        redict.update({str(_.get(key_col)): _.get(val_col)})
    return redict



def get_city_name(file_path):
    _file_word = file_path.split('\\')
    return _file_word
# 新增城市列函数
def add_city_column(path_input,err_log):
    mark_csv = ".csv"
    for root, dirs, files in os.walk(path_input):
        for file in files:
            path = os.path.join(root, file)
            res = path.split('\\')
            if os.path.splitext(path)[-1] == mark_csv:
                df = pd.read_csv(path)
                df59_path=root.replace("12B申诉管理-服务奖惩-评价","5B数据分析-运单详情")
                # 注意运单详情的格式，可能需要调用excel函数
                df59=csv_merge(df59_path)
                df59 = clear_data(df59)
                """ 调用 """
                _path = get_city_name(os.path.splitext(path)[0])
                check_work = city_check.MakingSamples(_path)
                """ end """
                if check_work.check_team_city_59(df, df59, '运单号'):
                    df["下载城市"]=res[-2]
                    df["运单号"]=[str(i) for i in df["运单号"]]
                    df.to_csv(path, index=False)
                    # print(df.head(2))
                    print(path)
                else:
                    print("error:",res[-2])
                    err_log.write_log_to_excel(
                        {'business': '57', 'city': os.path.splitext(path)[0], 'err': '所在城市不在已有字典表格中'}
                    )
            else:
                df = pd.read_excel(path)
                # print(df)
                df59_path = root.replace("12B申诉管理-服务奖惩-评价", "5B数据分析-运单详情")
                special_suffix_check(df59_path)
                # print("59 path is :",df59_path)
                # 注意运单详情的格式，可能需要调用excel函数
                df59 = csv_merge(df59_path)
                df59=clear_data(df59)
                # print(df59)
                """ 调用 """
                _path = get_city_name(os.path.splitext(path)[0])
                check_work = city_check.MakingSamples(_path)
                """ end """
                if check_work.check_team_city_59(df, df59, '运单号'):

                    df["下载城市"] = res[-2]
                    df["运单号"] = [str(i) for i in df["运单号"]]
                    # print(df)
                    df.to_excel(path, index=False)
                    # print(df.head(2))
                    print(path)
                else:
                    print("error:", res[-2])
                    # print(df)
                    err_log.write_log_to_excel(
                        {'business': '59', 'city': os.path.splitext(path)[0], 'err': '所在城市不在已有字典表格中'}
                    )

if __name__ == "__main__":
    """ 实例化日志     """
    err = city_check.Makelog()
    err.open_excel()
    # 日志存储位置
    err_path=r".\12b_add_city_column_log.csv"
    """ 实例化日志 end """

    # 填写"12B申诉管理-服务奖惩-评价"文件夹的地址，复制到path后边
    path_service_comment = r"F:\test\12B申诉管理-服务奖惩-评价"
    # 解压操作
    unzip(path_service_comment)

    # 新增列操作
    add_city_column(path_service_comment, err)

    """ 都执行完成后保存日志    """
    err.save_log(err_path)
    """ 都执行完成后保存日志 end"""
    print("DONE")
