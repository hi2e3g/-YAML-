
# 文件夹路径
path = '/Users/c/Develop/Web.Work/app-bot-script/datasource/赤峰/今日下载/'

# 文件的匹配规则
configs = [
    {"no": "2", "type": "xlsx", "rule": "2.骑手信息"},
    {"no": "5", "type": "csv", "rule": "5A.运单数据--\d\d\d\d-\d\d-\d\d_\d\d\d\d-\d\d-\d\d"},
    {"no": "12",  "type": "xls", "rule": "12A.服务中心_评价_\d\d\d\d-\d\d-\d\d"},
    {"no": "14A", "type": "csv", "rule": "14A.\d\d\d\d-\d\d-\d\d至\d\d\d\d-\d\d-\d\d出勤统计表"},
    {"no": "20A", "type": "xlsx", "rule": "20A.KPI问题单导出数据\d\d\d\d_\d\d_\d\d \d\d_\d\d_\d\d"},

    # 21A 和 22A的压缩包文件，命名是一样的，但是要全部解压缩之后去匹配规则才行，两条规则合并成一条，节省一次解压缩时间。
    # 21A，22A存在多个压缩包
    {
        "no": "21A, 22A",
        "type": "zip",
        "rule": "2\dA.\d*-代理商账单-\d\d-\d\d-\d\d-\d\d-\d*",
        "pack": [
            # 21A
            {"no": "21A", "type": "csv", "rule": "\d*-配送费-\d\d-\d\d-\d\d-\d\d"},
            # 22A
            {"no": "22A", "type": "csv", "rule": "\d*-违规扣款-\d\d-\d\d-\d\d-\d\d"},
            {"no": "22A", "type": "csv", "rule": "\d*-调整账-\d\d-\d\d-\d\d-\d\d"},
            {"no": "22A", "type": "csv", "rule": "\d*-服务费-\d\d-\d\d-\d\d-\d\d"},
            {"no": "22A", "type": "csv", "rule": "\d*-考核奖惩-\d\d-\d\d-\d\d-\d\d"},
            {"no": "22A", "type": "csv", "rule": "\d*-骑手活动-\d\d-\d\d-\d\d-\d\d"},
            {"no": "22A", "type": "csv", "rule": "\d*-日结配送费扣款-\d\d-\d\d-\d\d-\d\d"},
            {"no": "22A", "type": "csv", "rule": "\d*-申诉返款-\d\d-\d\d-\d\d-\d\d"},
        ]
    },
    # 22A的规则可以单独拆分，目前为了提高效率，减少一次解压缩文件遍历，与21A合并
    # {
    #     "no": "22A",
    #     "type": "zip",
    #     "rule": "2\dA.\d*-代理商账单-\d\d-\d\d-\d\d-\d\d-\d*",
    #     "pack": [
    #         {"type": "csv", "rule": "\d*-违规扣款-\d\d-\d\d-\d\d-\d\d"},
    #         {"type": "csv", "rule": "\d*-调整账-\d\d-\d\d-\d\d-\d\d"},
    #         {"type": "csv", "rule": "\d*-服务费-\d\d-\d\d-\d\d-\d\d"},
    #         {"type": "csv", "rule": "\d*-考核奖惩-\d\d-\d\d-\d\d-\d\d"},
    #         {"type": "csv", "rule": "\d*-骑手活动-\d\d-\d\d-\d\d-\d\d"},
    #         {"type": "csv", "rule": "\d*-日结配送费扣款-\d\d-\d\d-\d\d-\d\d"},
    #         {"type": "csv", "rule": "\d*-申诉返款-\d\d-\d\d-\d\d-\d\d"},
    #     ]
    # },
    # 23A, 24A 所有文件在一个压缩包里
    {
        "no": "23A, 24A",
        "type": "zip",
        "rule": "23A.24A.\d*-骑手账单-\d\d-\d\d-\d\d-\d\d-\d*",
        "pack": [
            # 23A
            {"no": "23A", "type": "csv", "rule": "\d*-配送费-\d\d-\d\d-\d\d-\d\d"},
            # 24A
            {"no": "24A", "type": "csv", "rule": "\d*-调整帐-\d\d-\d\d-\d\d-\d\d"},
            {"no": "24A", "type": "csv", "rule": "\d*-骑手活动-\d\d-\d\d-\d\d-\d\d"},
            {"no": "24A", "type": "csv", "rule": "\d*-申诉返款-\d\d-\d\d-\d\d-\d\d"},
            {"no": "24A", "type": "csv", "rule": "\d*-违规扣款-\d\d-\d\d-\d\d-\d\d"},
        ]
    },
    # 24A的规则可以单独拆分，目前为了提高效率，减少一次解压缩文件遍历，与23A合并
    # {
    #     "no": "24A",
    #     "type": "zip",
    #     "rule": "20006586-骑手账单-10-01-10-18-575675",
    #     "pack": [
    #         {"type": "csv", "rule": "20006586-调整帐-10-01-10-18"},
    #         {"type": "csv", "rule": "20006586-骑手活动-10-01-10-18"},
    #         {"type": "csv", "rule": "20006586-申诉返款-10-01-10-18"},
    #         {"type": "csv", "rule": "20006586-违规扣款-10-01-10-18"},
    #     ]
    # },
    {"no": "25A", "type": "csv", "rule": "25A.\d\d\d\d-\d\d-\d\d-\d\d\d\d-\d\d-\d\d-骑手数据明细"},
    {"no": "27A", "type": "xlsx", "rule": "27A.data"},
    {"no": "28A", "type": "csv", "rule": "28A.\d\d\d\d-\d\d-\d\d至\d\d\d\d-\d\d-\d\d出勤明细表"},
    # {"no": "29A", "type": "csv", "rule": ""},
    {"no": "30A", "type": "xlsx", "rule": "30A.KPI数据导出\d\d\d\d_\d\d_\d\d \d\d_\d\d_\d\d"},
    {"no": "31A", "type": "xlsx", "rule": "30A.KPI数据导出\d\d\d\d_\d\d_\d\d \d\d_\d\d_\d\d"},  # 拆分自30A文件
    {"no": "32A", "type": "xls", "rule": "32A.\d\d\d\d-\d\d-\d\d至\d\d\d\d-\d\d-\d\d奖励明细"},
]
