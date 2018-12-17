import QuantLib as ql
from abc import abstractmethod, ABCMeta


# 股票期权定价的基类
class Option(object):
    __metaclass__ = ABCMeta  # 抽象类声明

    def __init__(self, stockPrice, evaluationDate):
        # evaluationDate，格式'YYYY-MM-DD'，期权的合约签订日
        self.stockPrice = ql.SimpleQuote(stockPrice)
        evaluationDate = [int(t) for t in evaluationDate.split('-')]
        self.evaluationDate = ql.Date(evaluationDate[2], evaluationDate[1], evaluationDate[0])
        self.calendar = ql.China()
        ql.Settings.instance().evaluationDate = self.evaluationDate

    @abstractmethod
    def _NPV(self):
        pass

    @abstractmethod
    def value(self):
        pass

    @abstractmethod
    def delta(self):
        pass


# 欧式期权的基类
class EuropeanOption(Option):
    __metaclass__ = ABCMeta  # 抽象类声明

    def __init__(self, stockPrice, strikePrice, evaluationDate, exerciseDate, optionType):
        # 输入参数为期权条款本身
        # optionType为ql.Option.Call或ql.Option.Put
        super().__init__(stockPrice, evaluationDate)
        self.strikePrice = strikePrice  # 敲定价不用ql.SimpleQuote包装，Payoff不支持
        exerciseDate = [int(t) for t in exerciseDate.split('-')]
        self.exerciseDate = ql.Date(exerciseDate[2], exerciseDate[1], exerciseDate[0])
        self.optionType = optionType


class EuropeanOptionBS(EuropeanOption):
    def __init__(self, stockPrice, strikePrice, evaluationDate, exerciseDate, optionType, riskFree, volatility):
        # 无风险利率的计算方式为ActualActual
        # 波动率的计算方式为Actual365Fixed
        super().__init__(stockPrice, strikePrice, evaluationDate, exerciseDate, optionType)
        self.riskFree = ql.SimpleQuote(riskFree)
        self.volatility = ql.SimpleQuote(volatility)
        # 构造期权
        self.option = ql.EuropeanOption(ql.PlainVanillaPayoff(self.optionType, self.strikePrice), ql.EuropeanExercise(self.exerciseDate))
        # 构造无风险利率和波动率曲线
        riskFreeCurve = ql.FlatForward(self.evaluationDate, ql.QuoteHandle(self.riskFree), ql.ActualActual())
        volatility = ql.BlackConstantVol(self.evaluationDate, self.calendar, ql.QuoteHandle(self.volatility), ql.Actual365Fixed())
        # 定义价格发展过程
        process = ql.BlackScholesProcess(ql.QuoteHandle(self.stockPrice),
                                         ql.YieldTermStructureHandle(riskFreeCurve),
                                         ql.BlackVolTermStructureHandle(volatility))
        # 定义价格引擎
        engine = ql.AnalyticEuropeanEngine(process)
        self.option.setPricingEngine(engine)

    def _NPV(self, stockPrice, riskFree, volatility):
        # 记录现在的价格
        stockPriceNow = self.stockPrice.value()
        riskFreeNow = self.riskFree.value()
        volatilityNow = self.volatility.value()
        # 更新相关的计算参数
        self.stockPrice.setValue(stockPrice)
        self.riskFree.setValue(riskFree)
        self.volatility.setValue(volatility)
        NPVValue = self.option.NPV()
        # 恢复原参数
        self.stockPrice.setValue(stockPriceNow)
        self.riskFree.setValue(riskFreeNow)
        self.volatility.setValue(volatilityNow)
        return NPVValue

    def value(self):
        value = self._NPV(self.stockPrice.value(), self.riskFree.value(), self.volatility.value())
        return value

    def delta(self):
        delta = self.option.delta()
        return delta


class EuropeanOptionBSM(EuropeanOption):
    def __init__(self, stockPrice, strikePrice, evaluationDate, exerciseDate, optionType, dividendRate, riskFree, volatility):
        # 无风险利率的计算方式为ActualActual
        # 波动率的计算方式为Actual365Fixed
        super().__init__(stockPrice, strikePrice, evaluationDate, exerciseDate, optionType)
        self.riskFree = ql.SimpleQuote(riskFree)
        self.dividendRate = ql.SimpleQuote(dividendRate)
        self.volatility = ql.SimpleQuote(volatility)
        # 构造期权
        self.option = ql.EuropeanOption(ql.PlainVanillaPayoff(self.optionType, self.strikePrice), ql.EuropeanExercise(self.exerciseDate))
        # 构造无风险利率、分红和波动率曲线
        dividendRateCurve = ql.FlatForward(self.evaluationDate, ql.QuoteHandle(self.dividendRate), ql.Actual365Fixed())
        riskFreeCurve = ql.FlatForward(self.evaluationDate, ql.QuoteHandle(self.riskFree), ql.ActualActual())
        volatility = ql.BlackConstantVol(self.evaluationDate, self.calendar, ql.QuoteHandle(self.volatility), ql.Actual365Fixed())
        # 定义价格发展过程
        process = ql.BlackScholesMertonProcess(ql.QuoteHandle(self.stockPrice),
                                               ql.YieldTermStructureHandle(dividendRateCurve),
                                               ql.YieldTermStructureHandle(riskFreeCurve),
                                               ql.BlackVolTermStructureHandle(volatility))
        # 定义价格引擎
        engine = ql.AnalyticEuropeanEngine(process)
        self.option.setPricingEngine(engine)

    def _NPV(self, stockPrice, dividendRate, riskFree, volatility):
        # 记录现在的价格
        stockPriceNow = self.stockPrice.value()
        dividendRateNow = self.dividendRate.value()
        riskFreeNow = self.riskFree.value()
        volatilityNow = self.volatility.value()
        # 更新相关的计算参数
        self.stockPrice.setValue(stockPrice)
        self.dividendRate.setValue(dividendRate)
        self.riskFree.setValue(riskFree)
        self.volatility.setValue(volatility)
        NPVValue = self.option.NPV()
        # 恢复原参数
        self.stockPrice.setValue(stockPriceNow)
        self.dividendRate.setValue(dividendRateNow)
        self.riskFree.setValue(riskFreeNow)
        self.volatility.setValue(volatilityNow)
        return NPVValue

    def value(self):
        value = self._NPV(self.stockPrice.value(), self.dividendRate.value(), self.riskFree.value(), self.volatility.value())
        return value

    def delta(self):
        delta = self.option.delta()
        return delta


if __name__ == '__main__':
    stockPrice = 100.0
    strikePrice = 100.0
    evaluationDate = '2014-03-07'
    exerciseDate = '2014-06-07'
    optionType = ql.Option.Call
    dividendRate = 0.0
    riskFree = 0.01
    volatility = 0.2
    model = EuropeanOptionBS(stockPrice, strikePrice, evaluationDate, exerciseDate, optionType, riskFree, volatility)
    print(model.value())
    print(model.delta())
    model = EuropeanOptionBSM(stockPrice, strikePrice, evaluationDate, exerciseDate, optionType, dividendRate, riskFree, volatility)
    print(model.value())
    print(model.delta())