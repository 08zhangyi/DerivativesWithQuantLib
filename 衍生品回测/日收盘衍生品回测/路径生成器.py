import numpy as np
import pandas as pd
import QuantLib as ql
from WindPy import w


class PathGenerator(object):
    def __init__(self, start_date, end_date, path_number):
        start_date = self._date_string_2_date_ql(start_date)  # 路径生成的初始时间
        end_date = self._date_string_2_date_ql(end_date)  # 路径生成的结束时间
        self.date_list = self._generate_date_list(start_date, end_date)
        self.path_number = path_number  # 生成路径的个数

    # 时间转换通用函数
    @staticmethod
    def _date_string_2_date_ql(date):
        date = date.split('-')
        date = ql.Date(int(date[2]), int(date[1]), int(date[0]))
        return date

    @staticmethod
    def _date_ql_2_date_string(date):
        date = date.to_date().strftime('%Y-%m-%d')
        return date

    # 日期列表的生成函数
    @staticmethod
    def _generate_date_list(start_date, end_date, includeFirst=True, includeLast=True):
        calendar = ql.China()
        start_date = calendar.advance(start_date, 0, ql.Days)  # 休息日取为下一个交易日
        end_date = calendar.advance(end_date, 0, ql.Days)
        date_list = [start_date]
        date_temp = start_date
        while True:
            date_temp = calendar.advance(date_temp, 1, ql.Days)
            date_list.append(date_temp)
            if date_temp == end_date:
                break
        if not includeFirst:
            date_list = date_list[1:]
        if not includeLast:
            date_list = date_list[:-1]
        return date_list


class SingleAssetPathGenerator(PathGenerator):
    def __init__(self, asset, start_date, end_date, path_number):
        super().__init__(start_date, end_date, path_number)
        self.asset = asset
        self._get_path_everyday()

    def _get_return_everyday(self):
        # len(self.date_list)行，self.path_number)条路径
        # 收益率用每日对数收益率表示
        # 此函数为通过生成每日汇报来生成路径的核心函数
        return_everyday = np.zeros((len(self.date_list), self.path_number))  # 每日价格不变
        return return_everyday

    def _get_path_everyday(self):
        return_everyday = self._get_return_everyday()
        return_everyday = np.cumsum(return_everyday, axis=0)
        path_everyday = np.exp(return_everyday)
        path_everyday = pd.DataFrame(path_everyday, index=self.date_list)
        return path_everyday

    def get_date(self):
        path_everyday = self._get_path_everyday()
        return path_everyday


if __name__ == '__main__':
    asset = '000001.SH'
    start_date = '2018-09-14'
    end_date = '2018-10-12'
    path_number = 10
    generator = SingleAssetPathGenerator(asset, start_date, end_date, path_number)