import pandas as pd
import zipfile
import os

from numpy import unicode

import city_check
import re
from tkinter import *
import hashlib


class MY_window():
    def __init__(self, init_window_name):
        self.init_window_name = init_window_name
        # 设置窗口

    def unzip(self,path_input):
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

    def key_to_dict(self,df, key_col, val_col):
        redict, _dict = {}, df.to_dict(orient='records')
        for _ in _dict:
            redict.update({str(_.get(key_col)): _.get(val_col)})
        return redict

    def get_city_name(self,file_path):
        _file_word = file_path.split('\\')
        return _file_word

    def special_suffix_check(self,path_input):
        mark_suffix = [".csv", ".xlsx", ".xls", ".xlsm", ".xlsb", ".xlt"]
        for root, dirs, files in os.walk(path_input):
            for file in files:
                path = os.path.join(root, file)
                suffix = os.path.splitext(path)[-1]
                if suffix in mark_suffix:
                    pass
                else:
                    print("文件格式有误，请查看该文件：", path)

    def add_city_column(self,path_input, team_id_dict, err_log):
        mark_csv = ".csv"
        for root, dirs, files in os.walk(path_input):
            for file in files:
                # print(files)

                path = os.path.join(root, file)
                res = path.split('\\')
                if os.path.splitext(path)[-1] == mark_csv:
                    df = pd.read_csv(path)
                    """ 调用 """
                    _path = self.get_city_name(os.path.splitext(path)[0])
                    check_work = city_check.MakingSamples(_path)
                    """ end """
                    if check_work.check_team_city_57(df, team_id_dict, '团队ID'):
                        df["下载城市"] = res[-2]
                        df.to_csv(path, index=False)
                        self.result_data_Text.insert(INSERT, "Right:")
                        self.result_data_Text.insert(INSERT, path)
                        self.result_data_Text.insert(INSERT, "\n")
                        self.result_data_Text.update()
                        # print(df.head(2))
                    else:
                        self.result_data_Text.insert(INSERT, "error:")
                        self.result_data_Text.insert(INSERT, res[-2])
                        self.result_data_Text.insert(INSERT, "\n")
                        self.result_data_Text.update()
                        err_log.write_log_to_excel(
                            {'business': '57', 'city': os.path.splitext(path)[0], 'err': '所在城市不在已有字典表格中'}
                        )

                else:
                    df = pd.read_excel(path)
                    """ 调用 """
                    _path = self.get_city_name(os.path.splitext(path)[0])
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
        self.result_data_Text.insert(INSERT, "Done")
    def set_init_window(self):
        self.init_window_name.title("新增【下载城市】列工具")
        self.init_window_name.geometry('1068x681+10+10')
        # 标签
        self.init_data_label = Label(self.init_window_name, text="粘贴数据路径在空白处")
        self.init_data_label.grid(row=2, column=0)
        self.result_data_label = Label(self.init_window_name, text="执行状态")
        self.result_data_label.grid(row=7, column=0)
        # 文本框
        self.init_data_Text = Text(self.init_window_name, width=120, height=3)  # 原始数据录入框
        self.init_data_Text.grid(row=3, column=0, rowspan=3, columnspan=10)
        self.result_data_Text = Text(self.init_window_name, width=120, height=35)  # 处理结果展示
        self.result_data_Text.grid(row=8, column=0, rowspan=10, columnspan=10)

        # 按钮
        self.add_city_button = Button(self.init_window_name, text="运行", bg="lightblue", width=10,
                                      command=self.window_main)  # 调用内部方法  加()为直接调用
        self.add_city_button.grid(row=6, column=0)

        # 功能函数


    def window_main(self):
        path_input = self.init_data_Text.get(1.0, END).strip().replace("\n", "").encode()
        path_input= unicode(path_input, "utf-8")
        if path_input:
            err = city_check.Makelog()
            err.open_excel()
            err_path = r".\5b_add_city_column_log.csv"
            path_teamid = r".\station_id-city.csv"
            df_city = pd.read_csv(path_teamid)
            df_city_dict = self.key_to_dict(df_city, '站点ID', '城市')
            self.unzip(path_input)
            self.add_city_column(path_input,df_city_dict, err)
        else:
            self.result_data_Text("ERROR:地址输入有误")
if __name__ == "__main__":

    init_window = Tk()  # 实例化出一个父窗口
    add_PORTAL = MY_window(init_window)
    # 设置根窗口默认属性
    add_PORTAL.set_init_window()
    init_window.mainloop()