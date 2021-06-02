#!/usr/bin/env python3
import time
import traceback
from src.elem import ele, mt


# 程序入口
def main():
    try:
        start = time.time()
        # print('*'*100, '开始饿了么数据检验和分层', '*'*100)
        # ele.verify_and_layer()
        # print('*'*100, '饿了么数据检验和分层结束', '*'*100)
        # time.sleep(2)
        print('*'*100, '开始美团数据检验和分层', '*'*100)
        mt.verify_and_layer()
        print('*'*100, '美团数据检验和分层结束', '*'*100)
        end = time.time()
        print(f'总耗时{end-start}秒')
    except Exception as _:
        raise Exception(traceback.format_exc())


if __name__ == '__main__':
    main()



