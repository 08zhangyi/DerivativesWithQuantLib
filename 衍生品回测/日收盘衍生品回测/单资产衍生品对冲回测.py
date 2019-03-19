import numpy as np
import QuantLib as ql
import pygal
# 导入模型的设定
import sys
sys.path.append('D:\\programs\\DerivativesWithQuantLib\\衍生品回测\\日收盘衍生品回测')
sys.path.append('D:\\programs\\DerivativesWithQuantLib\\衍生品定价模型')


class SingleAssetDerivativeBacktestDayBase(object):
    def __init__(self, asset, start_date, end_date, PathGenerator, coefsOfPathGenerator, Derivative, coefsOfDerivative, slippage=0.0, commission=0.0):
        self.asset = asset
        self.start_date = start_date  # 回测开始日期，此时刻的asset的价格为1
        self.end_date = end_date  # 回测到期日，也是期权的到期日
        # 生成仿真价格路径
        # self.simPaths表示计算标的的价格走势，self.simPathsHedging表示对冲标的的价格走势
        self.simPaths, self.simPathsHedging = PathGenerator(asset, start_date, end_date, **coefsOfPathGenerator).get_data()
        self.date_list = [self.date2str(d) for d in list(self.simPaths.index.values)]
        # 衍生品与其用到的其它参数
        self.Derivative = Derivative
        self.coefsOfDerivative = coefsOfDerivative
        # 滑点和手续费
        self.slippage = slippage
        self.commission = commission

    def get_hedging_profit_and_loss(self):
        # 计算对冲和行权造成的衍生品盈亏
        hedging_profit_and_loss = np.zeros((self.simPathsHedging.shape[0]-1, self.simPathsHedging.shape[1]))
        return hedging_profit_and_loss

    def summary(self):
        pass

    def str2date(self, string):
        # 2010-01-01格式的日期转化为ql.Date对象的函数
        string = [int(s) for s in string.split('-')]
        date = ql.Date(string[2], string[1], string[0])
        return date

    def date2str(self, date):
        # 2010-01-01格式的日期转化为ql.Date对象的函数
        date = date.to_date()
        date = date.strftime('%Y-%m-%d')
        return date


class SingleAssetDerivativeBacktestDeltaHedging4EuropeanOption(SingleAssetDerivativeBacktestDayBase):
    # 适用于欧式期权
    # 计算期权的delta值，用delta值作为对冲比例
    def get_asset_delta(self):
        asset_delta = np.zeros(self.simPaths.shape)
        date_number = len(self.date_list)
        path_number = self.simPaths.shape[1]
        for date_index in range(date_number):
            date = self.date_list[date_index]
            if date_index == (date_number - 1):
                pass  # 最后一日全部平仓，delta值都是零
            else:
                for path_index in range(path_number):
                    stockPrice = self.simPaths.values[date_index, path_index]  # 获取虚拟时刻的股票头寸
                    evaluationDate = date  # 获取期权股指
                    exerciseDate = self.end_date
                    option = self.Derivative(stockPrice=stockPrice,
                                             evaluationDate=evaluationDate,
                                             exerciseDate=exerciseDate,
                                             **self.coefsOfDerivative)
                    delta_value = option.delta()
                    asset_delta[date_index, path_index] = delta_value
        return asset_delta

    def get_payoff(self):
        # payoff是到期的支出项，适用于欧式香草期权
        price_exercise_date = self.simPaths.values[-1]
        optionType = self.coefsOfDerivative['optionType']
        strikePrice = self.coefsOfDerivative['strikePrice']
        if optionType == ql.Option.Call:
            payoff = np.maximum(price_exercise_date-strikePrice, 0.0)
        elif optionType == ql.Option.Put:
            payoff = np.maximum(strikePrice-price_exercise_date, 0.0)
        else:
            payoff = np.ones_like(price_exercise_date)
        return payoff

    def get_hedging_profit_and_loss(self):
        asset_delta = self.get_asset_delta()
        payoff = self.get_payoff()
        hedging_profit_and_loss = np.zeros_like(self.simPathsHedging.values)
        hedging_profit_and_loss[1:] = np.diff(self.simPathsHedging.values, axis=0) * asset_delta[0:-1, :]  # delta对冲的盈亏
        asset_delta_delta = np.diff(np.r_[np.ones((1, asset_delta.shape[1])), asset_delta], axis=0)  # 每日调仓量
        hedging_profit_and_loss -= (np.abs(self.simPathsHedging.values * asset_delta_delta) * self.slippage * self.commission)  # delta对冲盈亏加入手续费影响
        hedging_profit_and_loss[-1] = hedging_profit_and_loss[-1] - payoff  # payoff的支出
        return asset_delta, hedging_profit_and_loss, payoff

    def summary(self):
        asset_delta, hedging_profit_and_loss, payoff = self.get_hedging_profit_and_loss()
        all_hedging_profit_and_loss = np.sum(hedging_profit_and_loss, axis=0)
        sim_path_values = self.simPaths.values
        path_number = self.simPaths.shape[1]
        # 画图
        # 仿真价格路径
        line_chart_sim_path_values = pygal.Line()
        line_chart_sim_path_values.title = '仿真价格路径'
        line_chart_sim_path_values.x_labels = self.date_list
        for index in range(path_number):
            line_chart_sim_path_values.add(str(index+1), sim_path_values[:, index])
        line_chart_sim_path_values.render_to_file('data\\仿真价格路径.svg')
        # Delta值
        line_chart_asset_delta = pygal.Line()
        line_chart_asset_delta.title = 'Delta值'
        line_chart_asset_delta.x_labels = self.date_list
        for index in range(path_number):
            line_chart_asset_delta.add(str(index+1), asset_delta[:, index])
        line_chart_asset_delta.render_to_file('data\\Delta值.svg')
        # 当日盯市与Payoff之和的盈亏图
        line_chart_hedging_profit_and_loss = pygal.Line()
        line_chart_hedging_profit_and_loss.title = '当日盯市与Payoff之和的盈亏图'
        line_chart_hedging_profit_and_loss.x_labels = self.date_list
        for index in range(path_number):
            line_chart_hedging_profit_and_loss.add(str(index+1), hedging_profit_and_loss[:, index])
        line_chart_hedging_profit_and_loss.render_to_file('data\\当日盯市与Payoff之和的盈亏图.svg')
        # 累积对冲和payoff盈亏图
        line_chart_all_hedging_profit_and_loss = pygal.Bar()
        line_chart_all_hedging_profit_and_loss.title = '累积对冲和payoff盈亏图'
        line_chart_all_hedging_profit_and_loss.x_labels = range(1, path_number+1)
        line_chart_all_hedging_profit_and_loss.add('', all_hedging_profit_and_loss)
        line_chart_all_hedging_profit_and_loss.render_to_file('data\\累积对冲和payoff盈亏图.svg')
        # payoff图
        line_chart_payoff = pygal.Bar()
        line_chart_payoff.title = 'payoff图'
        line_chart_payoff.x_labels = range(1, path_number+1)
        line_chart_payoff.add('', payoff)
        line_chart_payoff.render_to_file('data\\payoff图.svg')
        # 对冲和payoff盈亏图的分位数计算值
        print('对冲和payoff盈亏图的分位数计算值:')
        print(np.percentile(all_hedging_profit_and_loss, 10),
              np.percentile(all_hedging_profit_and_loss, 25),
              np.percentile(all_hedging_profit_and_loss, 50),
              np.percentile(all_hedging_profit_and_loss, 75),
              np.percentile(all_hedging_profit_and_loss, 90))


# 此处开始写测试函数
# 测试函数为各个回测类的使用模板
# 实际应用中参考此处测试函数的写法
# 全部为function形式
# 需要的模块全部在测试函数中导入

def 欧式回测测试1():
    from 路径生成器 import HistoryReturnPathGeneratorByEverydayReturn
    from 股票期权定价模型 import EuropeanOptionBSAnalytic

    asset = '000300.SH'
    start_date = '2018-03-08'
    end_date = '2018-03-23'
    PathGenerator = HistoryReturnPathGeneratorByEverydayReturn
    coefsOfPathGenerator = {'path_number': 20, 'history_end_date': '2018-03-28', 'history_frequrncy': 0}
    Derivative = EuropeanOptionBSAnalytic
    coefsOfDerivative = {'strikePrice': 1.0, 'optionType': ql.Option.Call, 'riskFree': 0.01, 'volatility': 0.4}
    backtest_model = SingleAssetDerivativeBacktestDeltaHedging4EuropeanOption(asset, start_date, end_date, PathGenerator, coefsOfPathGenerator, Derivative, coefsOfDerivative)
    backtest_model.summary()


if __name__ == '__main__':
    欧式回测测试1()
