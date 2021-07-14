# -*- coding:utf-8 -*-
import logging.config
import os
from functools import partial
from time import sleep
import fire as _fire
from dapp_youshu.blitz.cookbook_player import BlitzCookBookPlayer
from datahub_biz.qplus_dataset_biz import QPlusFinanceDatasetBiz
from datahub_biz.salaryflow_biz import SalaryFlowBiz, SalarySheetBiz
from datahub_biz.dataset_biz import StdDatasetBiz
from yoda import datetime as datetime_util
from datahub.boostrap.shell_boostrap import bootstrap_shell
from datahub_biz.qlife_worker_biz import QLifeWorkerProfileChecker
from dask.distributed import Client
from loky import get_reusable_executor

_DIR = os.path.dirname(__file__)
_path_join = partial(os.path.join, _DIR)

_dask_cfg = {
    'dask_address': 'dask-scheduler-service.databus:8786'
}


def restart_workers(address=None):
    if not address:
        address = _dask_cfg.get('dask_address')
    client = Client(address)
    client.restart()
    sleep(2)
    print(u'workers restarted.')


def play_book(args):
    book_path, month, env = args
    bootstrap_shell()
    player = BlitzCookBookPlayer()
    dask_address = _dask_cfg.get('dask_address')
    return player.play_book(book_yaml=book_path, month=month, env=env, dask_address=dask_address)


def play_all_jobs(jobs):
    executor = get_reusable_executor(timeout=10)
    results = executor.map(play_book, jobs)
    for result in results:
        print(u'---> Play book result <%s> DONE.' % result)


def run_phase_1_jobs(month):
    jobs = [
        (_path_join(u'dapp_youshu/cookbook/00_datakit_dataset_ele.yml'), month, u'ele_daily_env'),
        # (_path_join(u'dapp_youshu/cookbook/00_datakit_dataset_mt.yml'), month, u'mt_daily_env'),
    ]
    play_all_jobs(jobs)

    restart_workers()

    jobs = [
        # (_path_join(u'dapp_youshu/cookbook/00_datakit_dataset_ele.yml'), month, u'ele_daily_env'),
        (_path_join(u'dapp_youshu/cookbook/00_datakit_dataset_mt.yml'), month, u'mt_daily_env'),
    ]
    play_all_jobs(jobs)


def run_phase_2_jobs(month):
    jobs = [
        (_path_join(u'dapp_youshu/cookbook/salarykit_dataset_ele.yml'), month, u'ele_daily_env'),
    ]
    play_all_jobs(jobs)

    jobs = [
        (_path_join(u'dapp_youshu/cookbook/salarykit_dataset_mt.yml'), month, u'mt_daily_env'),
    ]
    play_all_jobs(jobs)

    restart_workers()


def run_pre_phase(month):
    biz = QPlusFinanceDatasetBiz.instance()
    biz.cook_finance_biz_dataset(month)


def run_qlife_worker_phase(month):
    biz = QPlusFinanceDatasetBiz.instance()
    biz.cook_qlife_workers_dataset(month)


def play_jobs(month=None, run_pre=True, run_x_1=True, run_x_2=True, run_x_3=False, run_x_4=True, run_x_5=False,
              run_x_worker=False, dask_address=None):
    if not month:
        month = int(datetime_util.prcnow().format('YYYYMM'))
    else:
        month = int(month)
    if dask_address:
        _dask_cfg['dask_address'] = dask_address

    if run_pre:
        run_pre_phase(month)
    if run_x_worker:
        run_qlife_worker_phase(month)

    restart_workers()

    if run_x_1:
        run_phase_1_jobs(month)
        restart_workers()

    if run_x_2:
        run_phase_2_jobs(month)
        restart_workers()


def run_month_phase_jobs(month):
    jobs = [
        (_path_join(u'dapp_youshu/cookbook/00_datakit_dataset_ele.yml'), month, u'ele_month_env'),
        (_path_join(u'dapp_youshu/cookbook/00_datakit_dataset_mt.yml'), month, u'mt_month_env'),
    ]
    play_all_jobs(jobs)

    restart_workers()

    jobs = [
        (_path_join(u'dapp_youshu/cookbook/salarykit_dataset_ele.yml'), month, u'ele_month_env'),
        (_path_join(u'dapp_youshu/cookbook/salarykit_dataset_mt.yml'), month, u'mt_month_env'),
    ]
    play_all_jobs(jobs)

    restart_workers()


def play_month_jobs(month=None, override_finance=False):
    if not month:
        month = int(datetime_util.prcnow().format('YYYYMM'))
    else:
        month = int(month)
    restart_workers()
    run_month_phase_jobs(month)


# def play_act_jobs(month):
#     month = int(month)
#
#     biz = SalaryFlowBiz.instance()
#     biz.cook_salaryflow_month_dataset(month)
#
#     restart_workers()
#     jobs = [
#         (_path_join(u'dapp_youshu/cookbook/adjust_data_with_new_finacial_ele.yml'), month, u'ele_month_env'),
#         (_path_join(u'dapp_youshu/cookbook/adjust_data_with_new_finacial_mt.yml'), month, u'mt_month_env'),
#     ]
#     play_all_jobs(jobs)
#     # restart_workers()
#     # run_phase_4_jobs(month)
#     # restart_workers()
#     jobs2 = [
#         # (_path_join(u'dapp_youshu/cookbook/financial_to_compass_comparison.yml'), month, None),
#         (_path_join(u'dapp_youshu/cookbook/city_order_cost_actual_mt_ele.yml'), month, None),
#         (_path_join(u'dapp_youshu/cookbook/dc_order_cost_actual_mt_ele.yml'), month, None)
#     ]
#     play_all_jobs(jobs2)
#     restart_workers()


def play_worker_salarysheet_jobs(month, t2=True, update_worker_alive_tags=False):
    """更新一线花名册
    :param month:
    :type month:
    :param t2:
    :type t2:
    :return:
    :rtype:
    """
    biz = SalarySheetBiz.instance()
    biz.build_ele_worker_salary_sheet_data(month, './datastore/salary/data', t2_mode=True)
    biz.build_mt_worker_salary_sheet_data(month, './datastore/salary/data', t2_mode=t2)
    if update_worker_alive_tags:
        biz.update_worker_alive_tags(month, t2_mode=True)
        biz.update_worker_alive_tags(month, t2_mode=False)


def play_recommend_jobs(month, dump_dir='./'):
    """
    执行内荐费任务，将数据给到汇流
    :param month:
    :return:
    """
    # 1、create salarysheet dataset to s3
    month = int(month)
    biz = SalarySheetBiz.instance()
    biz.cook_salarysheet_month_dataset(month)

    # 2、play recommend yml
    restart_workers()
    jobs = [
        (_path_join(u'dapp_youshu/cookbook/mt_recommend_bonus_details.yml'), month, u'mt_daily_env'),
    ]
    play_book(jobs[0])
    restart_workers()

    # 3、load  s3 recommend dataset dump to excel
    biz = StdDatasetBiz.instance()
    biz.dump_huiliu_recommend_file(month, u'mt_recommend_bonus_details', dump_dir)


def play_qlife_worker_jobs(month, with_month_data=False):
    biz = QLifeWorkerProfileChecker().instance()
    biz.check_ele_pending_records(month)
    biz.validate_ele_worker_profile(month)
    biz.check_mt_pending_records(month, with_month_data)
    biz.validate_mt_worker_profile(month)
    biz.book_ok_records(month)


def play_new_compass(current_month, last_month, day):
    restart_workers()
    jobs = [
        (_path_join(u'dapp_youshu/cookbook/new_compass/process_middle_table_ele.yml'), current_month, u'ele_daily_env'),
        # (_path_join(u'dapp_youshu/cookbook/new_compass/transfer_month_city_analysis_ele.yml'), last_month,
        #  u'ele_month_env'),
        (_path_join(u'dapp_youshu/cookbook/new_compass/process_middle_table_mt.yml'), current_month, u'mt_daily_env'),
        (_path_join(u'dapp_youshu/cookbook/new_compass/process_middle_table_yk.yml'), current_month, u'yk_daily_env'),
    ]
    if 1 <= day <= 10:
        jobs.append(
            (_path_join(u'dapp_youshu/cookbook/new_compass/process_middle_table_ele.yml'), last_month, u'ele_month_env')
        )
        jobs.append(
            (_path_join(u'dapp_youshu/cookbook/new_compass/process_middle_table_mt.yml'), last_month, u'mt_month_env')
        )
        jobs.append(
            (_path_join(u'dapp_youshu/cookbook/new_compass/process_middle_table_yk.yml'), last_month, u'yk_daily_env')
        )
    for job in jobs:
        play_book(job)


def play_mt_reports(current_month):
    jobs = [
        (_path_join(u'dapp_youshu/cookbook/final_accounts_report_form_mt.yml'), current_month,
         'mt_report_from_final_accounts_daily_env')
    ]
    for job in jobs:
        play_book(job)


def play_finance_week_reports(current_month):
    jobs = [
        (_path_join(u'dapp_youshu/cookbook/finance-week/finance_weekly_report_dataset.yml'), current_month, u'new_finance_weekly_report_env'),
        (_path_join(u'dapp_youshu/cookbook/finance-week/finance_weekly_financial_report_dataset.yml'), current_month, u'new_financial_form_snap_env'),
    ]
    for job in jobs:
        play_book(job)


def cron_daily(cook_first_day=2, cook_last_month_day=10, cook_month_jobs_day=(1, 10)):
    """每日定时任务, copied from datahub_job/compass_cooker.py

    :return:
    :rtype:
    """
    today = datetime_util.prcnow()
    currentday = today.datetime.day
    current_month = int(today.format('YYYYMM'))
    print(u'==== cron_daily START ===')
    if currentday > cook_first_day:
        try:
            print(u'cook-daily-jobs<%s> ...' % current_month)
            play_jobs(month=current_month, run_x_worker=True)
            print(U'======play_jobs<%s> OK=======' % current_month)
        except Exception as e:
            print(e)
            print(U'======play_jobs<%s> FAILED=======' % current_month)
        # try:
        #     play_worker_salarysheet_jobs(month=current_month, t2=True)
        #     print(U'======play_worker_salarysheet_jobs<%s> OK=======' % current_month)
        # except Exception as e:
        #     print(e)
        #     print(U'======play_worker_salarysheet_jobs<%s> FAILED=======' % current_month)
    # Redo last month dataset
    last_month = int(today.replace(months=-1).format('YYYYMM'))
    if currentday <= cook_last_month_day:
        print(u'==> Redo with Last month<%s> ' % last_month)
        try:
            play_jobs(month=last_month)
            print(U'======play_jobs<%s> OK=======' % last_month)
        except Exception as e:
            print(e)
            print(U'======play_jobs<%s> FAILED=======' % last_month)
    if cook_month_jobs_day[0] <= currentday <= cook_month_jobs_day[1]:
        print(u'cook-month-jobs<%s> ...' % last_month)
        try:
            play_month_jobs(month=last_month)
            print(U'======play_month_jobs<%s> OK=======' % last_month)
        except Exception as e:
            print(e)
            print(U'======play_month_jobs<%s> FAILED=======' % last_month)
        # print(u'cook-worker-salary-jobs ...')
        # try:
        #     play_worker_salarysheet_jobs(month=last_month, t2=False, update_worker_alive_tags=True)
        #     print(U'======play_worker_salarysheet_jobs<%s> OK=======' % last_month)
        # except Exception as e:
        #     print(e)
        #     print(U'======play_worker_salarysheet_jobs<%s> FAILED=======' % last_month)
    # 新罗盘
    print(u'CRON-NEW-COMPASS START---')
    play_new_compass(current_month, last_month, currentday)
    print(u'CRON-NEW-COMPASS END---')
    # 财务周报
    print('finance-week START ---')
    play_finance_week_reports(current_month)
    print('finance-week END ---')
    # 美团决算
    print('美团决算类报表 START --')
    play_mt_reports(current_month)
    print('美团决算类报表 END --')
    print(u'==== cron_daily DONE ===')


def cron_daily_huiliu(cook_first_day=4, cook_month_jobs_day=(1, 10), dump_dir='/data/jfs-huiliu-data'):
    today = datetime_util.prcnow()
    currentday = today.datetime.day
    current_month = int(today.format('YYYYMM'))
    last_month = int(today.replace(months=-1).format('YYYYMM'))
    print(u'==== cron_daily_huiliu START ===')
    if currentday > cook_first_day:
        try:
            print(u'cook-worker-salary-jobs ...')
            play_worker_salarysheet_jobs(month=current_month, t2=True)
            print(U'======play_worker_salarysheet_jobs<%s> OK=======' % current_month)
        except Exception as e:
            print(e)
            print(U'======play_worker_salarysheet_jobs<%s> FAILED=======' % current_month)
    # Redo last month dataset
    if cook_month_jobs_day[0] <= currentday <= cook_month_jobs_day[1]:
        print(u'cook-worker-salary-jobs ...')
        try:
            play_worker_salarysheet_jobs(month=last_month, t2=False, update_worker_alive_tags=True)
            print(U'======play_worker_salarysheet_jobs<%s> OK=======' % last_month)
        except Exception as e:
            print(e)
            print(U'======play_worker_salarysheet_jobs<%s> FAILED=======' % last_month)

    # note
    # WHY?
    # play_recommend_jobs 使用了playbook, dask全局使用集群，激活后由于花名册部分代码仍依赖本地文件的cache，这会导致在本地文件在不同的
    # dask节点中无法找到。故临时方案是集中处理完花名册，再playbook
    if currentday > cook_first_day:
        try:
            print(U'======play_recommend_jobs<%s> ...' % current_month)
            play_recommend_jobs(month=current_month, dump_dir=dump_dir)
            print(U'======play_recommend_jobs<%s> OK=======' % current_month)
        except Exception as e:
            print(e)
            print(U'======play_recommend_jobs<%s> FAILED=======' % current_month)
    # Redo last month dataset
    if cook_month_jobs_day[0] <= currentday <= cook_month_jobs_day[1]:
        try:
            print(U'======play_recommend_jobs<%s> ...' % last_month)
            play_recommend_jobs(month=last_month, dump_dir=dump_dir)
            print(U'======play_recommend_jobs<%s> OK=======' % last_month)
        except Exception as e:
            print(e)
            print(U'======play_recommend_jobs<%s> FAILED=======' % last_month)

    print(u'==== cron_daily_huiliu DONE ===')


if __name__ == '__main__':
    logging.config.fileConfig('logging_shell.ini', disable_existing_loggers=False)
    bootstrap_shell()
    _fire.Fire({
        'play_jobs': play_jobs,
        'play_month_jobs': play_month_jobs,
        # 'play_act_jobs': play_act_jobs,
        'play_worker_stats': run_qlife_worker_phase,
        'play_worker_salarysheet': play_worker_salarysheet_jobs,
        'play_recommend_jobs': play_recommend_jobs,
        'cron_daily': cron_daily,
        'cron_daily_huiliu': cron_daily_huiliu,
        'play_mt_reports': play_mt_reports,
        'play_finance_week_reports': play_finance_week_reports,
    })
