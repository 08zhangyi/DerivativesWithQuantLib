import QuantLib as ql
from WindPy import w
from tools import str_date_2_ql_date


def get_shanghai_repo(date):
    calc_date = str_date_2_ql_date(date)
    ql.Settings.instance().evaluationDate = calc_date
    calendar = ql.China()
    bussiness_convention = ql.Following
    dayCount = ql.Actual365Fixed()
    end_of_month = False
    # 设置回购的基本信息
    w.start()
    # 获取上交所1d，2d，3d，4d，7d，14d，28d，91d回购的数据
    repo_maturities = [ql.Period(1, ql.Days), ql.Period(2, ql.Days), ql.Period(3, ql.Days),
                       ql.Period(4, ql.Days), ql.Period(7, ql.Days), ql.Period(14, ql.Days),
                       ql.Period(28, ql.Days), ql.Period(91, ql.Days)]
    repo_rates = w.wss("204001.SH,204002.SH,204003.SH,204004.SH,204007.SH,204014.SH,204028.SH,204091.SH", "close",
                       "tradeDate=20190121;priceAdj=U;cycle=D").Data[0]
    # 获取上交所1d，7d，14d，28d，91d回购的数据
    # repo_maturities = [ql.Period(1, ql.Days), ql.Period(7, ql.Days), ql.Period(14, ql.Days),
    #                    ql.Period(28, ql.Days), ql.Period(91, ql.Days)]
    # repo_rates = w.wss("204001.SH,204007.SH,204014.SH,204028.SH,204091.SH", "close",
    #                    "tradeDate=20190121;priceAdj=U;cycle=D").Data[0]
    repo_rate_helpers = []
    for i, repo_maturity in enumerate(repo_maturities):
        repo_rate_helpers.append(ql.DepositRateHelper(ql.QuoteHandle(ql.SimpleQuote(repo_rates[i]/100.0)),
                                                      repo_maturity,
                                                      0, calendar,
                                                      bussiness_convention,
                                                      end_of_month,
                                                      dayCount))
    return repo_rate_helpers


def get_shanghai_repo_1m(date):
    calc_date = str_date_2_ql_date(date)
    ql.Settings.instance().evaluationDate = calc_date
    calendar = ql.China()
    bussiness_convention = ql.Following
    dayCount = ql.Actual365Fixed()
    end_of_month = False
    # 设置回购的基本信息
    w.start()
    # 获取上交所1d，2d，7d，14d，28d回购的数据，只取一个月期限内流动性好的品种
    repo_maturities = [ql.Period(1, ql.Days), ql.Period(2, ql.Days), ql.Period(7, ql.Days), ql.Period(14, ql.Days),
                       ql.Period(28, ql.Days)]
    repo_rates = w.wss("204001.SH,204002.SH,204003.SH,204004.SH,204007.SH,204014.SH,204028.SH,204091.SH", "close",
                       "tradeDate=20190121;priceAdj=U;cycle=D").Data[0]
    repo_rate_helpers = []
    for i, repo_maturity in enumerate(repo_maturities):
        repo_rate_helpers.append(ql.DepositRateHelper(ql.QuoteHandle(ql.SimpleQuote(repo_rates[i]/100.0)),
                                                      repo_maturity,
                                                      0, calendar,
                                                      bussiness_convention,
                                                      end_of_month,
                                                      dayCount))
    return repo_rate_helpers


get_shanghai_repo('2019-01-21')