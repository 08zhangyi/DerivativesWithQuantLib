import numpy as np
import pandas as pd
import QuantLib as ql
from WindPy import w


class PathGenerator(object):
    # 仿真路径生成器基类
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


class SingleAssetPathGeneratorByErerydayReturn(PathGenerator):
    def __init__(self, asset, start_date, end_date, path_number):
        super().__init__(start_date, end_date, path_number)
        self.asset = asset

    def _get_return_everyday(self):
        # len(self.date_list)行，self.path_number)条路径
        # 收益率用每日对数收益率表示
        # 此函数为通过生成每日回报来生成路径的核心函数
        # 第一个结果用来仿真资产的价格走势，第二个结果用来对冲计算，默认两个结果相同
        return_everyday = np.zeros((len(self.date_list), self.path_number))  # 每日价格不变
        return return_everyday, return_everyday

    def _get_path_everyday(self):
        # 此函数为通过生成每日价格变动来生成路径的核心函数
        return_everyday, return_everyday_for_hedging = self._get_return_everyday()
        # 计算路径每日回报
        return_everyday = np.cumsum(return_everyday, axis=0)
        path_everyday = np.exp(return_everyday)
        path_everyday = pd.DataFrame(path_everyday, index=self.date_list)
        # 对冲路径每日回报
        return_everyday_for_hedging = np.cumsum(return_everyday_for_hedging, axis=0)
        path_everyday_for_hedging = np.exp(return_everyday_for_hedging)
        path_everyday_for_hedging = pd.DataFrame(path_everyday_for_hedging, index=self.date_list)
        return path_everyday, path_everyday_for_hedging

    def get_data(self):
        # 此函数返回结果
        # 第一个结果用来仿真资产的价格走势，第二个结果用来对冲计算
        path_everyday, path_everyday_for_hedging = self._get_path_everyday()
        return path_everyday, path_everyday_for_hedging


class HistoryReturnPathGeneratorByEverydayReturn(SingleAssetPathGeneratorByErerydayReturn):
    # 使用历史收益率数据构造仿真路径，初始价格为1.0
    def __init__(self, asset, start_date, end_date, path_number, history_end_date, history_frequrncy=0):
        self.history_end_date = history_end_date  # 历史路径的最后采样日
        self.history_frequency = history_frequrncy  # 历史路径的采样频率：0-收尾相接，1-年频率，2-月频率，3-季度频率，4-周频率
        super().__init__(asset, start_date, end_date, path_number)

    def _get_return_everyday_by_asset(self, asset):
        return_data_list = []
        calendar = ql.China()
        # 初始化end_date和start_date
        end_date = self._date_string_2_date_ql(self.history_end_date)
        start_date = calendar.advance(end_date, -len(self.date_list)+1, ql.Days)
        for pn in range(self.path_number):
            w.start()
            print('获取第'+str(pn+1)+'条历史路径，共计'+str(self.path_number)+'条，日期为从'+str(start_date)+'到'+str(end_date))
            return_data = np.array(w.wsd(asset, "pct_chg", self._date_ql_2_date_string(start_date), self._date_ql_2_date_string(end_date), "ShowBlank=0").Data[0])
            return_data = np.log((return_data / 100.0 + 1.0))[:, np.newaxis]
            return_data[0, :] = 0.0  # 第一天收盘为初始交易时刻
            return_data_list.append(return_data)
            if self.history_frequency == 1:  # 一年
                end_date = calendar.advance(end_date, -1, ql.Years)
            elif self.history_frequency == 2:  # 一个月
                end_date = calendar.advance(end_date, -1, ql.Months)
            elif self.history_frequency == 3:  # 一个季度
                end_date = calendar.advance(end_date, -3, ql.Months)
            elif self.history_frequency == 4:  # 一周
                end_date = calendar.advance(end_date, -1, ql.Weeks)
            else:  # 0为默认模式，收尾相接模式
                end_date = start_date
            start_date = calendar.advance(end_date, -len(self.date_list) + 1, ql.Days)
        return_everyday = np.concatenate(return_data_list, axis=1)  # 每日价格不变
        return return_everyday

    def _get_return_everyday(self):
        return_everyday = self._get_return_everyday_by_asset(self.asset)
        return return_everyday, return_everyday


class HistoryReturnPathGeneratorByEverydayReturnDiffHedging(HistoryReturnPathGeneratorByEverydayReturn):
    def __init__(self, asset, asset_for_hedging, start_date, end_date, path_number, history_end_date, history_frequrncy=0):
        # asset_for_hedging表示用于对冲回测的路径
        self.asset_for_hedging = asset_for_hedging
        super().__init__(asset, start_date, end_date, path_number, history_end_date, history_frequrncy)

    def _get_return_everyday(self):
        return_everyday = self._get_return_everyday_by_asset(self.asset)
        return_everyday_for_hedging = self._get_return_everyday_by_asset(self.asset_for_hedging)
        return return_everyday, return_everyday_for_hedging


class BrownianMCReturnPathGeneratorByEverydayReturn(SingleAssetPathGeneratorByErerydayReturn):
    def __init__(self, asset, start_date, end_date, path_number, drift, volatility):
        # 使用正态分布生成收益率数据，，初始价格为1.0
        # Brownian运动的参数，240天的年化
        self.volatility = volatility / np.sqrt(240)
        self.drift = drift / 240
        super().__init__(asset, start_date, end_date, path_number)

    def _get_return_everyday(self):
        return_everyday = np.random.normal(self.drift, self.volatility, size=(len(self.date_list), self.path_number))
        return_everyday[0, :] = 0.0
        return return_everyday, return_everyday


def 每日历史回报路径测试1():
    asset = '000300.SH'
    start_date = '2018-09-14'
    end_date = '2018-10-12'
    history_end_date = '2018-10-12'
    path_number = 10
    generator = HistoryReturnPathGeneratorByEverydayReturn(asset, start_date, end_date, path_number, history_end_date)
    sim_path, sim_path_for_hedging = generator.get_data()
    print(sim_path)
    print(sim_path_for_hedging)


def 每日历史回报路径测试2():
    # 计算路径与对冲路径不同
    asset = '000300.SH'
    asset_for_hedging = '000016.SH'
    start_date = '2018-09-14'
    end_date = '2018-10-12'
    history_end_date = '2018-10-12'
    path_number = 10
    generator = HistoryReturnPathGeneratorByEverydayReturnDiffHedging(asset, asset_for_hedging, start_date, end_date, path_number, history_end_date)
    sim_path, sim_path_for_hedging = generator.get_data()
    print(sim_path)
    print(sim_path_for_hedging)


if __name__ == '__main__':
    每日历史回报路径测试2()
