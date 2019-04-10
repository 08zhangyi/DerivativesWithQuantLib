import datetime
import QuantLib as ql
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator
from WindPy import w


class OptionAnalysisBase(object):
    def __init__(self, options, unit, eps_diff):
        # options为一个字典，标识每个期权的购买张数
        # options = {'10001124.SH': 1, '10001156.SH': 1}
        # 1为买，-1为卖
        # eps_diff为离散求斜率时的误差精度
        self.options = options  # 要计算的策略期权组成代码
        self.date_now = datetime.datetime.now().strftime('%Y-%m-%d')  # 计算日期为当日
        self.unit = float(unit)  # 计算策略的交易单位倍数
        self.eps_diff = eps_diff

    def _get_cost(self):
        # 获取构建策略组合时的成本，以一个unit为单位
        pass

    def _get_payoff(self, price):
        # 计算到期日期权的payoff函数，以一个unit为单位
        pass

    def _get_zeros(self, x_list, y_list):
        # 根据eps_zero的值计算y_list中的零点，以此计算x_list中的零点
        # 插值法
        zeros = []
        for i in range(len(y_list)-1):
            y = y_list[i]
            y_next = y_list[i+1]
            if y == 0.0:
                zeros.append(x_list[i])
            else:
                if y * y_next < 0:
                    alpha = y_next / (y_next - y)
                    zeros.append(alpha*x_list[i] + (1-alpha)*x_list[i+1])
        return np.array(zeros)

    def _get_max_min_return(self, x_list, y_list):
        # 根据return_list计算策略到期的最大收益和亏损
        min_value = np.min(y_list)
        max_value = np.max(y_list)
        left_diff = (y_list[1] - y_list[0]) / (x_list[1] - x_list[0])
        right_diff = (y_list[-1] - y_list[-2]) / (x_list[-1] - x_list[-2])
        if left_diff > self.eps_diff or right_diff < -self.eps_diff:
            min_value = None
        if left_diff < -self.eps_diff or right_diff > self.eps_diff:
            max_value = None
        return min_value, max_value

    def summary(self):
        # 对策略组合的收益进行总结
        pass


class ETF50OptionAnalysis(OptionAnalysisBase):
    def __init__(self, options, etf=0, unit=10000, eps_diff=0.01):
        self.etf = float(etf)  # 是否买入ETF的标识，买入为正数，卖出为负数，单位为ETF的份数（100份为一手）
        super().__init__(options, unit, eps_diff)
        w.start()
        self.ql_options, self.date_end, self.strike_list = self._set_ql_option()
        self.etf_now = w.wsq('510050.SH', "rt_latest").Data[0][0]
        print(self.etf_now)

    def _set_ql_option(self):
        ql_options = {}
        date_end = datetime.datetime.strptime(self.date_now, '%Y-%m-%d')  # 记录期权的最后到期日，此类应该都是一个到期日
        strike_list = []
        # 将期权的payoff转化为ql中的对象
        for option in self.options:
            number = self.options[option]
            option_data = w.wss(option, "exe_mode,exe_price,exe_ratio,lasttradingdate", "tradeDate=" + self.date_now).Data
            option_type = option_data[0][0]
            option_strike = option_data[1][0]
            option_volume = option_data[2][0] * number
            option_last_day = option_data[3][0]
            option_type = ql.Option.Call if option_type == '认购' else ql.Option.Put
            option_payoff = ql.PlainVanillaPayoff(option_type, option_strike)
            if option_last_day > date_end:
                date_end = option_last_day
            ql_options[option] = (option_payoff, option_volume)  # 记录期权的payoff函数和对应的份数函数
            strike_list.append(option_strike)
        return ql_options, date_end.strftime('%Y-%m-%d'), np.array(strike_list)

    def _get_cost(self):
        cost = 0
        for option in self.ql_options:
            _, volume = self.ql_options[option]
            if volume >= 0:  # 表示买入
                ask_price = w.wsq(option, "rt_ask1").Data[0][0]
                cost += ask_price * volume
            else:  # 表示卖出
                bid_price = w.wsq(option, "rt_bid1").Data[0][0]
                cost += bid_price * volume
        if self.etf >= 0:
            ask_price = w.wsq('510050.SH', "rt_ask1").Data[0][0]
            cost += ask_price * self.etf
        else:
            bid_price = w.wsq('510050.SH', "rt_bid1").Data[0][0]
            cost += bid_price * self.etf
        cost /= self.unit
        return cost

    def _get_payoff(self, price):
        payoff = 0
        for option in self.ql_options:
            payoff_function, volume = self.ql_options[option]
            payoff += payoff_function(price) * volume
        payoff += self.etf * price
        payoff /= self.unit
        return payoff

    def summary(self, min_val=0.9, max_val=1.1):
        # min_val与max_val为计算区间用的参数
        price_space = np.linspace(np.min([np.min(self.strike_list), self.etf_now])*min_val, np.max([np.max(self.strike_list), self.etf_now])*max_val, 1001)
        payoff_space = np.array([self._get_payoff(p) for p in price_space])
        cost = self._get_cost()  # 策略构造成本的计算
        profit_space = payoff_space - cost  # 策略到期回报的计算
        # 零点和策略汇报极值的计算
        zeros = self._get_zeros(price_space, profit_space)
        min_value, max_value = self._get_max_min_return(price_space, profit_space)
        # 总结此策略组合的信息
        etf_option_string = '50ETF期权策略组合的组成为：\n'
        for option in self.options:
            etf_option_string += (option + '的份数，' + str(self.options[option]) + '\n')
        etf_option_string += ('其中，50ETF的份数为：\n50ETF的份数，' + str(int(self.etf)) + '\n')
        etf_option_string += ('计算单位为' + str(self.unit) + '份50ETF\n')
        etf_option_string += ('策略构造成本为：%.4f元每单位\n' % cost)
        etf_option_string += ('策略到期最大盈利为：' + (('%.4f\n' % max_value) if max_value is not None else '无穷\n'))
        etf_option_string += ('策略到期最大亏损为：' + (('%.4f\n' % min_value) if min_value is not None else '无穷\n'))
        etf_option_string += '策略到期盈亏平衡点为（每份50ETF）：\n'
        for zero in zeros:
            etf_option_string += ('%.4f元\n' % zero)
        etf_option_string += '策略中使用到的期权的行权价为（从小到大）：\n'
        strikes = sorted(self.strike_list)
        for strike in strikes:
            etf_option_string += '%.4f元（策略利润：%.4f元）\n' % (strike, self._get_payoff(strike)-cost)
        print(etf_option_string)
        # 画图的配置
        plt.figure(figsize=(12, 12))
        plt.rcParams['font.sans-serif'] = ['SimHei']  # 显示负号
        plt.rcParams['axes.unicode_minus'] = False  # 显示中文
        # 画收益图
        plt.axhline(0.0, color='b', ls='--')
        plt.axvline(self.etf_now, color='g', ls='--', label='ETF现价')  # 现货价格线
        plt.plot(price_space, profit_space, 'r-', label='策略到期利润')  # 利润图
        plt.plot(self.etf_now, self._get_payoff(self.etf_now)-cost, 'g*', label='平价到期利润')
        plt.plot(zeros, np.zeros_like(zeros), 'b*', label='盈亏平衡点')
        plt.axis('square')
        # 显示文字
        xmin, xmax, ymin, ymax = plt.axis()
        plt.text(xmax, ymin, etf_option_string, ha='right', bbox=dict(facecolor='white', alpha=0.5))
        plt.text(self.etf_now, np.min(profit_space), '即时50ETF价格为：%.4f元每份' % self.etf_now, ha='center', bbox=dict(facecolor='white', alpha=0.5))
        plt.legend()
        plt.show()


# 使用模板区
def 备兑开仓():
    options = {'10001755.SH': -1}
    etf = 10000
    unit = 10000
    tool = ETF50OptionAnalysis(options, etf=etf, unit=unit)
    tool.summary()


def 牛市价差_Call():
    options = {'10001755.SH': 1, '10001759.SH': -1}
    etf = 0
    unit = 10000
    tool = ETF50OptionAnalysis(options, etf=etf, unit=unit)
    tool.summary()


def 蝶式价差_Call():
    options = {'10001756.SH': 1, '10001758.SH': -2, '10001769.SH': 1}
    etf = 0
    unit = 10000
    tool = ETF50OptionAnalysis(options, etf=etf, unit=unit)
    tool.summary()


if __name__ == '__main__':
    蝶式价差_Call()