import QuantLib as ql


# 辅助函数区
def str_date_2_ql_date(date):
    return ql.Date(int(date.split('-')[2]), int(date.split('-')[1]), int(date.split('-')[0]))