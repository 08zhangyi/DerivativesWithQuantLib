import pandas as pd
import sys
sys.path.append('D:\\programs\\DerivativesWithQuantLib\\衍生品应用\\嵌入场内期权收益凭证定价分析')
from 嵌入价差期权收益凭证定价分析 import spread_option_income_certificate


FILE_PATH = 'D:\\programs\\DerivativesWithQuantLib\\衍生品应用\\嵌入场内期权收益凭证定价分析\\嵌入价差期权收益凭证定价分析测算表.xlsx'
SHEET_NAME = '测算使用'

df_excel = pd.read_excel(FILE_PATH, sheet_name='测算使用').dropna()
result_list = []
for row in df_excel.iterrows():
    row = row[1]
    START_DATE = row['产品起始日'].strftime("%Y-%m-%d")
    END_DATE = row['产品到期日'].strftime("%Y-%m-%d")
    UNDERLYING_INDEX = row['挂钩标的指数']
    UNDERLYING_ASSET = row['标的指数对应可投资资产资产']
    BASIC_RATE_RATE = float(row['产品保底利率'])
    BULL_SPREADS = {'B': row['价差组合买入期权（B)'], 'S': row['价差组合卖出期权（S)']}
    PRINCIPLE = float(row['本金（元）'])
    FIXED_RETURN_RATE = float(row['相同期限固定收益可比利率'])
    floating_bottom_point, floating_bottom_ratio, floating_ceiling_point, floating_ceiling_ratio, \
    bottom_return, ceiling_return, participate_ratio, underlying_index_end, return_rate_end, hedge_value = \
    spread_option_income_certificate(START_DATE, END_DATE, UNDERLYING_INDEX, UNDERLYING_ASSET, BASIC_RATE_RATE,
                                     BULL_SPREADS, PRINCIPLE, FIXED_RETURN_RATE)
    result_list.append([floating_bottom_point, floating_bottom_ratio, floating_ceiling_point, floating_ceiling_ratio,
                        bottom_return, ceiling_return, participate_ratio, underlying_index_end, return_rate_end, hedge_value])

df_result = pd.DataFrame(result_list)
df_result.to_excel('D:\\programs\\DerivativesWithQuantLib\\衍生品应用\\嵌入场内期权收益凭证定价分析\\result.xlsx')