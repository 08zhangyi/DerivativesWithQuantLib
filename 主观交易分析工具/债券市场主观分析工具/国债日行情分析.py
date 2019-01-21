import QuantLib as ql
import xlrd
from WindPy import w
import pandas as pd
import numpy as np
from scipy.optimize import minimize


# 辅助函数区
def str_date_2_ql_date(date):
    return ql.Date(int(date.split('-')[2]), int(date.split('-')[1]), int(date.split('-')[0]))


# 处理数据的日期，一些债券惯例的定义
date = '2019-01-17'
calc_date = str_date_2_ql_date(date)
ql.Settings.instance().evaluationDate = calc_date
calendar = ql.China()
bussiness_convention = ql.Following
# 读取excel文件，提取相关的国债行情数据
workbook = xlrd.open_workbook('data\\债券日行情'+date+'.xlsx')
main_sheet = workbook.sheet_by_name('万得')
nrows_range = range(2, main_sheet.nrows-2)  # 有效信息的行范围
locaotion_dict = {'交易代码': 0, '收盘全价': 3, '债券类型': 22, '特殊条款': 29, '利率类型': 30, '成交量': 4}  # 有效信息的列范围
debt_list = []  # 记录代码，全价信息
for i in nrows_range:
    # 按照国债、无特殊条款、固定利率的条件筛选债券品种
    if main_sheet.cell(i, locaotion_dict['债券类型']).value == '国债' and \
    main_sheet.cell(i, locaotion_dict['特殊条款']).value == '' and \
    main_sheet.cell(i, locaotion_dict['利率类型']).value == '固定利率':
        debt_list.append([main_sheet.cell(i, locaotion_dict['交易代码']).value,
                          main_sheet.cell(i, locaotion_dict['收盘全价']).value,
                          main_sheet.cell(i, locaotion_dict['成交量']).value])
# 从wind上获取债券的具体信息
debt_codes = [d[0] for d in debt_list]
w.start()
# 提取-名义票面利率，起息日，到期日，付息日说明，年付息次数，计息基准
debt_data = w.wss(debt_codes, 'couponrate, carrydate, maturitydate, coupondatetxt, interestfrequency, actualbenchmark').Data
debt_data = list(zip(*debt_data))

bond_helpers = []
for i in range(len(debt_codes)):
    debt_data_temp = debt_data[i]
    issue_date = str_date_2_ql_date(debt_data_temp[1].strftime('%Y-%m-%d'))
    maturity_date = str_date_2_ql_date(debt_data_temp[2].strftime('%Y-%m-%d'))
    # print(debt_data_temp)
    # 设定付息频率
    if debt_data_temp[4] == 4:
        tenor = ql.Period(ql.Seasonality)
    elif debt_data_temp[4] == 2:
        tenor = ql.Period(ql.Semiannual)
    elif debt_data_temp[4] == 1:
        tenor = ql.Period(ql.Annual)
    else:
        tenor = None
    # 设定计息算法
    if debt_data_temp[5] == 'A/365':
        day_count = ql.Actual360()
    elif debt_data_temp[5] == 'ACT/ACT':
        day_count = ql.ActualActual()
    else:
        day_count = ql.ActualActual()
    # 构造债券
    if tenor:
        schedule = ql.Schedule(issue_date, maturity_date, tenor, calendar, bussiness_convention, bussiness_convention,
                               ql.DateGeneration.Forward, False)
        bond = ql.FixedRateBond(0, 100.0, schedule, [debt_data_temp[0]/100.0], day_count)
    else:
        bond = ql.ZeroCouponBond(0, calendar, 100.0, maturity_date, bussiness_convention, 100.0, issue_date)
    dirty_price_handle = ql.QuoteHandle(ql.SimpleQuote(debt_list[i][1]))
    bond_helper = ql.BondHelper(dirty_price_handle, bond, useCleanPrice=False)
    bond_helpers.append(bond_helper)

# 拟合曲线法暂时无法得到有意义的解，拟采用人工方法求解
# bond_helpers = bond_helpers[10:13]
# dayCount = ql.ActualActual()  # 曲线用到的日数计算方法
# bond_fitted_curve = ql.FittedBondDiscountCurve(calc_date, bond_helpers, dayCount, ql.NelsonSiegelFitting(), 1e-4, 1000)
# print('start fitting')
# bond_fitted_curve.fitResults()
# print('end fitting')
# rate = bond_fitted_curve.zeroRate(ql.Date(17, 1, 2020), dayCount, ql.Compounded, ql.Annual).rate()
# print(rate)

# 构造虚拟的零息票债券，调整零息票债券报价，进而调整YTM曲线
dayCount = ql.ActualActual()
fictitious_bonds_term = [ql.Period(3, ql.Months), ql.Period(6, ql.Months), ql.Period(9, ql.Months), ql.Period(1, ql.Years),
                         ql.Period(2, ql.Years), ql.Period(3, ql.Years), ql.Period(4, ql.Years), ql.Period(5, ql.Years),
                         ql.Period(7, ql.Years), ql.Period(10, ql.Years), ql.Period(15, ql.Years),
                         ql.Period(20, ql.Years), ql.Period(30, ql.Years)]
fictitious_bonds = [ql.ZeroCouponBond(0, calendar, 100.0, calc_date + t, bussiness_convention, 100.0, calc_date) for t in fictitious_bonds_term]
# 用到的辅助函数
def calculate_diff(zero_prices):
    # zero_prices为虚拟的零息债券的报价
    # zero_prices的size与fictitious_bonds_term一致
    ficitious_ytm_curve = get_ytm_curve(zero_prices)
    ficitious_pricing_engine = ql.DiscountingBondEngine(ql.YieldTermStructureHandle(ficitious_ytm_curve))
    debt_volumes = np.array([v[2] for v in debt_list])
    debt_volumes = debt_volumes / np.sum(debt_volumes)  # 归一化权重
    diff = 0.0  # 测算误差
    for i, bond_helper in enumerate(bond_helpers):
        bond_temp = bond_helper.bond()
        bond_temp.setPricingEngine(ficitious_pricing_engine)
        bond_temp_dirty_price = bond_temp.dirtyPrice()
        diff += debt_volumes[i] * (debt_list[i][1] - bond_temp_dirty_price)**2
    print(diff)
    return diff
def get_ytm_curve(zero_prices):
    # zero_prices为虚拟的零息债券的报价
    fictitious_bonds_price_init = [ql.QuoteHandle(ql.SimpleQuote(zero_price)) for zero_price in zero_prices]
    ficitious_bonds_helper = [ql.BondHelper(p, b, useCleanPrice=False) for p, b in
                              zip(fictitious_bonds_price_init, fictitious_bonds)]
    ficitious_ytm_curve = ql.PiecewiseLogLinearDiscount(calc_date, ficitious_bonds_helper, dayCount)
    # ficitious_ytm_curve = ql.PiecewiseLogCubicDiscount(calc_date, ficitious_bonds_helper, dayCount)
    ficitious_ytm_curve.enableExtrapolation()
    return ficitious_ytm_curve
# 进行优化，需求最优的拟合曲线
res = minimize(calculate_diff, x0=np.array([100.0]*len(fictitious_bonds)), method='BFGS')
print(res.x)
optimize_ficitious_ytm_curve = get_ytm_curve(res.x)
zero_rates = [optimize_ficitious_ytm_curve.zeroRate(calc_date + t, dayCount, ql.Compounded).rate() for t in fictitious_bonds_term]
print(zero_rates)