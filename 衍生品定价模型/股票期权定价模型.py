import QuantLib as ql
import random
import numpy as np
from abc import abstractmethod, ABCMeta


# 定义全局变量
MC_SAMPLE_NUMBER = 10000
EPS = 0.001


# 股票期权定价的基类
class Option(object):
    __metaclass__ = ABCMeta  # 抽象类声明

    def __init__(self, stockPrice, evaluationDate):
        # evaluationDate，格式'YYYY-MM-DD'，期权的合约签订日
        self.stockPrice = ql.SimpleQuote(stockPrice)
        self.evaluationDate = self.str2date(evaluationDate)
        self.calendar = ql.China()
        ql.Settings.instance().evaluationDate = self.evaluationDate

    @abstractmethod
    def NPV(self):
        pass

    @abstractmethod
    def value(self):
        pass

    @abstractmethod
    def delta(self):
        pass

    def str2date(self, string):
        # 2010-01-01格式的日期转化为ql.Date对象的函数
        string = [int(s) for s in string.split('-')]
        date = ql.Date(string[2], string[1], string[0])
        return date


# 欧式股票期权的基类
class EuropeanOption(Option):
    __metaclass__ = ABCMeta  # 抽象类声明

    def __init__(self, stockPrice, strikePrice, evaluationDate, exerciseDate, optionType):
        # 输入参数为期权条款本身
        # optionType为ql.Option.Call或ql.Option.Put
        super().__init__(stockPrice, evaluationDate)
        self.strikePrice = strikePrice  # 敲定价不用ql.SimpleQuote包装，Payoff不支持
        self.exerciseDate = self.str2date(exerciseDate)
        self.optionType = optionType
        # 构造期权
        self.option = ql.EuropeanOption(ql.PlainVanillaPayoff(self.optionType, self.strikePrice),
                                        ql.EuropeanExercise(self.exerciseDate))


# 无分红股票欧式期权的BS解析定价模型
class EuropeanOptionBSAnalytic(EuropeanOption):
    def __init__(self, stockPrice, strikePrice, evaluationDate, exerciseDate, optionType, riskFree, volatility):
        # 无风险利率的计算方式为ActualActual
        # 波动率的计算方式为Actual365Fixed
        super().__init__(stockPrice, strikePrice, evaluationDate, exerciseDate, optionType)
        self.riskFree = ql.SimpleQuote(riskFree)
        self.volatility = ql.SimpleQuote(volatility)
        self.process = self.getPricingProcess()
        # 定义价格引擎
        engine = self.getPricingEngine()
        self.option.setPricingEngine(engine)

    def getPricingProcess(self):
        # 构造无风险利率和波动率曲线
        riskFreeCurve = ql.FlatForward(self.evaluationDate, ql.QuoteHandle(self.riskFree), ql.ActualActual())
        volatility = ql.BlackConstantVol(self.evaluationDate, self.calendar, ql.QuoteHandle(self.volatility),
                                         ql.Actual365Fixed())
        # 定义价格发展过程
        process = ql.BlackScholesProcess(ql.QuoteHandle(self.stockPrice),
                                         ql.YieldTermStructureHandle(riskFreeCurve),
                                         ql.BlackVolTermStructureHandle(volatility))
        return process

    def getPricingEngine(self):
        engine = ql.AnalyticEuropeanEngine(self.process)
        return engine

    def NPV(self, stockPrice, riskFree, volatility):
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
        value = self.NPV(self.stockPrice.value(), self.riskFree.value(), self.volatility.value())
        return value

    def delta(self):
        delta = self.option.delta()
        return delta


# 连续分红股票欧式期权的BSM解析定价模型
class EuropeanOptionBSMAnalytic(EuropeanOptionBSAnalytic):
    def __init__(self, stockPrice, strikePrice, evaluationDate, exerciseDate, optionType, dividendRate, riskFree, volatility):
        self.dividendRate = ql.SimpleQuote(dividendRate)
        super().__init__(stockPrice, strikePrice, evaluationDate, exerciseDate, optionType, riskFree, volatility)

    def getPricingProcess(self):
        # 构造无风险利率、分红和波动率曲线
        dividendRateCurve = ql.FlatForward(self.evaluationDate, ql.QuoteHandle(self.dividendRate), ql.Actual365Fixed())
        riskFreeCurve = ql.FlatForward(self.evaluationDate, ql.QuoteHandle(self.riskFree), ql.ActualActual())
        volatility = ql.BlackConstantVol(self.evaluationDate, self.calendar, ql.QuoteHandle(self.volatility),
                                         ql.Actual365Fixed())
        # 定义价格发展过程
        process = ql.BlackScholesMertonProcess(ql.QuoteHandle(self.stockPrice),
                                               ql.YieldTermStructureHandle(dividendRateCurve),
                                               ql.YieldTermStructureHandle(riskFreeCurve),
                                               ql.BlackVolTermStructureHandle(volatility))
        return process

    def NPV(self, stockPrice, dividendRate, riskFree, volatility):
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
        value = self.NPV(self.stockPrice.value(), self.dividendRate.value(), self.riskFree.value(), self.volatility.value())
        return value


# 连续分红股票欧式期权的BSM蒙特卡洛定价模型
class EuropeanOptionBSMMonteCarlo(EuropeanOptionBSMAnalytic):
    def __init__(self, stockPrice, strikePrice, evaluationDate, exerciseDate, optionType, dividendRate, riskFree, volatility, seed=None, requiredSamples=MC_SAMPLE_NUMBER):
        # MC参数设定
        if seed is None:
            self.seed = random.randint(0, 100000000)
        else:
            self.seed = seed
        self.requiredSamples = requiredSamples
        super().__init__(stockPrice, strikePrice, evaluationDate, exerciseDate, optionType, dividendRate, riskFree, volatility)

    def getPricingEngine(self):
        # PseudoRandom，LowDiscrepancy，随机数发生器可用
        engine = ql.MCEuropeanEngine(self.process, 'PseudoRandom', timeSteps=self.exerciseDate-self.evaluationDate, antitheticVariate=True,
                                     requiredSamples=self.requiredSamples, seed=self.seed)
        return engine

    def delta(self, eps=EPS):
        # eps为差分计算delta时价格的差分变动比例
        value_p = self.NPV(self.stockPrice.value()*(1 + eps), self.dividendRate.value(), self.riskFree.value(),
                           self.volatility.value())
        value_m = self.NPV(self.stockPrice.value() * (1 - eps), self.dividendRate.value(), self.riskFree.value(),
                           self.volatility.value())
        delta = (value_p - value_m) / (2 * eps * self.stockPrice.value())
        return delta


# 离散分红欧式股票期权的基类
class EuropeanOptionDiscreteDividends(Option):
    __metaclass__ = ABCMeta  # 抽象类声明

    def __init__(self, stockPrice, strikePrice, evaluationDate, exerciseDate, optionType, dividendDates, dividends):
        # 输入参数为期权条款本身
        # optionType为ql.Option.Call或ql.Option.Put
        super().__init__(stockPrice, evaluationDate)
        self.strikePrice = strikePrice  # 敲定价不用ql.SimpleQuote包装，Payoff不支持
        self.exerciseDate = self.str2date(exerciseDate)
        self.optionType = optionType
        self.dividendDates = [self.str2date(d) for d in dividendDates]
        self.dividends = dividends
        # 构造期权
        self.option = ql.DividendVanillaOption(ql.PlainVanillaPayoff(self.optionType, self.strikePrice),
                                               ql.EuropeanExercise(self.exerciseDate),
                                               self.dividendDates,
                                               self.dividends)


# 离散分红股票欧式期权的BS解析定价模型
class EuropeanOptionDiscreteDividendsBSAnalytic(EuropeanOptionDiscreteDividends):
    def __init__(self, stockPrice, strikePrice, evaluationDate, exerciseDate, optionType, dividendDates, dividends, riskFree, volatility):
        # 无风险利率的计算方式为ActualActual
        # 波动率的计算方式为Actual365Fixed
        # dividendDates格式为['2010-01-01', '2010-02-01']
        # dividends格式为[0.2, 0.5]
        super().__init__(stockPrice, strikePrice, evaluationDate, exerciseDate, optionType, dividendDates, dividends)
        self.riskFree = ql.SimpleQuote(riskFree)
        self.volatility = ql.SimpleQuote(volatility)
        self.process = self.getPricingProcess()
        # 定义价格引擎
        engine = self.getPricingEngine()
        self.option.setPricingEngine(engine)

    def getPricingProcess(self):
        # 构造无风险利率和波动率曲线
        riskFreeCurve = ql.FlatForward(self.evaluationDate, ql.QuoteHandle(self.riskFree), ql.ActualActual())
        volatility = ql.BlackConstantVol(self.evaluationDate, self.calendar, ql.QuoteHandle(self.volatility),
                                         ql.Actual365Fixed())
        # 定义价格发展过程
        process = ql.BlackScholesProcess(ql.QuoteHandle(self.stockPrice),
                                         ql.YieldTermStructureHandle(riskFreeCurve),
                                         ql.BlackVolTermStructureHandle(volatility))
        return process

    def getPricingEngine(self):
        engine = ql.AnalyticDividendEuropeanEngine(self.process)
        return engine

    def NPV(self, stockPrice, riskFree, volatility):
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
        value = self.NPV(self.stockPrice.value(), self.riskFree.value(), self.volatility.value())
        return value

    def delta(self):
        delta = self.option.delta()
        return delta


# 美式股票期权的基类
class AmericanOption(Option):
    __metaclass__ = ABCMeta  # 抽象类声明

    def __init__(self, stockPrice, strikePrice, evaluationDate, maturityDate, optionType):
        # 输入参数为期权条款本身
        # optionType为ql.Option.Call或ql.Option.Put
        super().__init__(stockPrice, evaluationDate)
        self.strikePrice = strikePrice  # 敲定价不用ql.SimpleQuote包装，Payoff不支持
        self.maturityDate = self.str2date(maturityDate)  # 美式期权为到期日
        self.optionType = optionType
        # 构造期权
        self.option = ql.VanillaOption(ql.PlainVanillaPayoff(self.optionType, self.strikePrice),
                                       ql.AmericanExercise(self.evaluationDate, self.maturityDate))


# 连续分红股票美式期权的BSM二叉树定价模型
class AmericanOptionBSMBinomial(AmericanOption):
    def __init__(self, stockPrice, strikePrice, evaluationDate, maturityDate, optionType, dividendRate, riskFree, volatility):
        # 无风险利率的计算方式为ActualActual
        # 波动率的计算方式为Actual365Fixed
        super().__init__(stockPrice, strikePrice, evaluationDate, maturityDate, optionType)
        self.dividendRate = ql.SimpleQuote(dividendRate)
        self.riskFree = ql.SimpleQuote(riskFree)
        self.volatility = ql.SimpleQuote(volatility)
        self.process = self.getPricingProcess()
        # 定义价格引擎
        engine = self.getPricingEngine()
        self.option.setPricingEngine(engine)

    def getPricingProcess(self):
        # 构造无风险利率、分红和波动率曲线
        dividendRateCurve = ql.FlatForward(self.evaluationDate, ql.QuoteHandle(self.dividendRate), ql.Actual365Fixed())
        riskFreeCurve = ql.FlatForward(self.evaluationDate, ql.QuoteHandle(self.riskFree), ql.ActualActual())
        volatility = ql.BlackConstantVol(self.evaluationDate, self.calendar, ql.QuoteHandle(self.volatility),
                                         ql.Actual365Fixed())
        # 定义价格发展过程
        process = ql.BlackScholesMertonProcess(ql.QuoteHandle(self.stockPrice),
                                               ql.YieldTermStructureHandle(dividendRateCurve),
                                               ql.YieldTermStructureHandle(riskFreeCurve),
                                               ql.BlackVolTermStructureHandle(volatility))
        return process

    def getPricingEngine(self):
        # 二叉树的方法有crr（CoxRossRubinstein），jr（JarrowRudd），eqp（AdditiveEQPBinomialTree），tian（Tian），lr（LeisenReimer），joshi4（Joshi4），trigeorgis（Trigeorgis）
        engine = ql.BinomialVanillaEngine(self.process, "AdditiveEQPBinomialTree", steps=self.maturityDate-self.evaluationDate)
        return engine

    def NPV(self, stockPrice, dividendRate, riskFree, volatility):
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
        value = self.NPV(self.stockPrice.value(), self.dividendRate.value(), self.riskFree.value(), self.volatility.value())
        return value

    def delta(self):
        delta = self.option.delta()
        return delta


# 连续分红股票美式期权的BSM有限差分定价模型
class AmericanOptionBSMFD(AmericanOptionBSMBinomial):
    def getPricingEngine(self):
        engine = ql.FDAmericanEngine(self.process, timeSteps=self.maturityDate-self.evaluationDate, gridPoints=100)
        return engine

    def delta(self):
        delta = self.option.delta()
        return delta


# 连续分红股票美式期权的BSM蒙特卡洛定价模型
class AmericanOptionBSMMonteCarlo(AmericanOptionBSMBinomial):
    def __init__(self, stockPrice, strikePrice, evaluationDate, maturityDate, optionType, dividendRate, riskFree, volatility, seed=None, requiredSamples=MC_SAMPLE_NUMBER):
        # MC参数设定
        if seed is None:
            self.seed = random.randint(0, 100000000)
        else:
            self.seed = seed
        self.requiredSamples = requiredSamples
        super().__init__(stockPrice, strikePrice, evaluationDate, maturityDate, optionType, dividendRate, riskFree, volatility)

    def getPricingEngine(self):
        engine = ql.MCAmericanEngine(self.process, 'PseudoRandom', timeSteps=self.maturityDate-self.evaluationDate, antitheticVariate=True,
                                     requiredSamples=self.requiredSamples, seed=self.seed)
        return engine

    def delta(self, eps=EPS):
        # eps为差分计算delta时价格的差分变动比例
        value_p = self.NPV(self.stockPrice.value()*(1 + eps), self.dividendRate.value(), self.riskFree.value(),
                           self.volatility.value())
        value_m = self.NPV(self.stockPrice.value() * (1 - eps), self.dividendRate.value(), self.riskFree.value(),
                           self.volatility.value())
        delta = (value_p - value_m) / (2 * eps * self.stockPrice.value())
        return delta


# 离散平均亚式股票期权的基类
class DiscreteAveragingAsiannOption(Option):
    __metaclass__ = ABCMeta  # 抽象类声明

    def __init__(self, stockPrice, strikePrice, evaluationDate, exerciseDate, optionType, averageType, historyPrices):
        # 输入参数为期权条款本身
        # optionType为ql.Option.Call或ql.Option.Put
        # averageType为ql.Average.Arithmetic或ql.Average.Geometric
        # historyPrices为历史价格列表，可以为[]、[1, 1.2, 1.03, 0.97]等形式
        super().__init__(stockPrice, evaluationDate)
        self.strikePrice = strikePrice  # 敲定价不用ql.SimpleQuote包装，Payoff不支持
        self.exerciseDate = self.str2date(exerciseDate)
        self.optionType = optionType
        self.averageType = averageType
        self.historyPrices = historyPrices
        # 构造期权
        # evaluationDate如果是第一天盘中，则historyPrices为[]
        # 否则，historyPrices的最后一项应为evaluationDate的收盘价
        runningAccumulator, pastFixings = self._get_accumulator()
        fixingDates = self._get_fixing_dates()
        self.option = ql.DiscreteAveragingAsianOption(self.averageType,
                                                      runningAccumulator,
                                                      pastFixings,
                                                      fixingDates,
                                                      ql.PlainVanillaPayoff(self.optionType, self.strikePrice),
                                                      ql.EuropeanExercise(self.exerciseDate))

    def _get_accumulator(self):
        # 根据历史价格构造runningAccumulator和pastFixings
        pastFixings = len(self.historyPrices)
        if self.averageType == ql.Average.Geometric:
            runningAccumulator = np.exp(np.sum(np.log(self.historyPrices)))
        else:
            runningAccumulator = np.sum(self.historyPrices)
        return runningAccumulator, pastFixings

    def _get_fixing_dates(self):
        # 不包括self.evaluationDate
        # 包括self.exerciseDate
        # 中间的交易日全部包括
        fixingDates = []
        for i in range(self.calendar.businessDaysBetween(self.evaluationDate, self.exerciseDate)):
            fixingDates.append(self.calendar.advance(self.evaluationDate, i + 1, ql.Days))
        return fixingDates


# 离散平均价格亚式股票期权BSM定价模型-蒙特卡洛求解
class DiscreteArithmeticAveragingPriceAsiannOptionBSMMonteCarlo(DiscreteAveragingAsiannOption):
    def __init__(self, stockPrice, strikePrice, evaluationDate, exerciseDate, optionType, historyPrices, dividendRate, riskFree, volatility, seed=None, requiredSamples=MC_SAMPLE_NUMBER):
        averageType = ql.Average.Arithmetic
        # MC参数设定
        if seed is None:
            self.seed = random.randint(0, 100000000)
        else:
            self.seed = seed
        self.requiredSamples = requiredSamples
        super().__init__(stockPrice, strikePrice, evaluationDate, exerciseDate, optionType, averageType, historyPrices)
        self.riskFree = ql.SimpleQuote(riskFree)
        self.volatility = ql.SimpleQuote(volatility)
        self.dividendRate = ql.SimpleQuote(dividendRate)
        self.process = self.getPricingProcess()
        # 定义价格引擎
        engine = self.getPricingEngine()
        self.option.setPricingEngine(engine)

    def getPricingProcess(self):
        # 构造无风险利率、分红和波动率曲线
        dividendRateCurve = ql.FlatForward(self.evaluationDate, ql.QuoteHandle(self.dividendRate), ql.Actual365Fixed())
        riskFreeCurve = ql.FlatForward(self.evaluationDate, ql.QuoteHandle(self.riskFree), ql.ActualActual())
        volatility = ql.BlackConstantVol(self.evaluationDate, self.calendar, ql.QuoteHandle(self.volatility),
                                         ql.Actual365Fixed())
        # 定义价格发展过程
        process = ql.BlackScholesMertonProcess(ql.QuoteHandle(self.stockPrice),
                                               ql.YieldTermStructureHandle(dividendRateCurve),
                                               ql.YieldTermStructureHandle(riskFreeCurve),
                                               ql.BlackVolTermStructureHandle(volatility))
        return process

    def getPricingEngine(self):
        # 'pseudorandom'为具体的RNG类型
        engine = ql.MCDiscreteArithmeticAPEngine(self.process, 'pseudorandom', antitheticVariate=True,
                                                 requiredSamples=self.requiredSamples, seed=self.seed)
        return engine

    def NPV(self, stockPrice, dividendRate, riskFree, volatility):
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
        value = self.NPV(self.stockPrice.value(), self.dividendRate.value(), self.riskFree.value(), self.volatility.value())
        return value

    def delta(self, eps=EPS):
        # eps为差分计算delta时价格的差分变动比例
        value_p = self.NPV(self.stockPrice.value()*(1 + eps), self.dividendRate.value(), self.riskFree.value(),
                           self.volatility.value())
        value_m = self.NPV(self.stockPrice.value() * (1 - eps), self.dividendRate.value(), self.riskFree.value(),
                           self.volatility.value())
        delta = (value_p - value_m) / (2 * eps * self.stockPrice.value())
        return delta


# 此处开始写测试函数
# 也是使用说明

def 欧式期权测试1():
    # 盘中实时计算时，由于未到收盘时刻，evaluationDate为当天的前一个交易日
    # 收盘盯市计算时，evaluationDate为当天
    stockPrice = 1.0
    strikePrice = 0.0
    evaluationDate = '2019-02-27'
    exerciseDate = '2019-02-27'
    optionType = ql.Option.Call
    riskFree = 0.01
    volatility = 0.2
    model = EuropeanOptionBSAnalytic(stockPrice, strikePrice, evaluationDate, exerciseDate, optionType, riskFree, volatility)
    print(model.value())


def 美式期权测试1():
    stockPrice = 100.0
    strikePrice = 100.0
    evaluationDate = '2014-03-07'
    maturityDate = '2014-06-07'
    optionType = ql.Option.Call
    dividendRate = 0.0
    riskFree = 0.01
    volatility = 0.2
    model = AmericanOptionBSMMonteCarlo(stockPrice, strikePrice, evaluationDate, maturityDate, optionType, dividendRate, riskFree, volatility)
    print(model.value())
    print(model.delta())


def 亚式期权测试1():
    # historyPrices使用说明
    # 模型计算中，不包括evaluationDate作为均值采样日，但包括exerciseDate
    # 盘中实时报价时，由于即时的S价格不包含在计算的均值内，因此此时historyPrices=[]，且evaluationDate为当天的前一个交易日
    # 收盘时盯市价格，evaluationDate为当天，historyPrices=[当天收盘价,]
    # 其他日子计算时，以此类推，例如：
    # 当日盘中实时计算，S=100.0，历史收盘价为[99.0, 102.0, 101.0]，则historyPrices=[99.0, 102.0, 101.0]，evaluationDate为当天的前一个交易日
    # 当日收盘盯市价格，则historyPrices=[99.0, 102.0, 101.0, 当天收盘价]，evaluationDate为当天
    stockPrice = 100.0
    strikePrice = 100.0
    evaluationDate = '2014-03-07'
    exerciseDate = '2014-06-07'
    optionType = ql.Option.Call
    historyPrices = [99.0, 98.7, 101.5, 101.4]
    dividendRate = 0.0
    riskFree = 0.01
    volatility = 0.20
    model = DiscreteArithmeticAveragingPriceAsiannOptionBSMMonteCarlo(stockPrice, strikePrice, evaluationDate, exerciseDate, optionType, historyPrices, dividendRate, riskFree, volatility)
    print(model.value())
    print(model.delta())


if __name__ == '__main__':
    美式期权测试1()
    亚式期权测试1()