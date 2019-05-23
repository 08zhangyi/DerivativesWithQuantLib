import xlrd
import numpy as np
from WindPy import w
import statsmodels.api as sm


def get_stock_portfolio(file_path):
    portfolio_dict = {}
    workbook = xlrd.open_workbook(file_path)
    sheet_portfolio = workbook.sheet_by_name('投资组合')
    for i in range(1, sheet_portfolio.nrows):
        stock_name = sheet_portfolio.cell(i, 0).value
        stock_number = sheet_portfolio.cell(i, 1).value
        portfolio_dict[stock_name] = stock_number
    return portfolio_dict


def get_portfolio_PL(portfolio_dict, start_date, end_date, base_date):
    # 从start_date日收盘到end_date日收盘间计算投资组合价格变动
    # base_date为复权定点日
    w.start()
    stock_names = list(portfolio_dict.keys())
    data = w.wsd(stock_names, 'close2', start_date, end_date, 'adjDate='+''.join(base_date.split('-'))+';PriceAdj=T').Data
    data = np.array(data)
    price_start = data[:, 0]
    price_end = data[:, -1]
    stock_numbers = np.array(list(portfolio_dict.values()))
    market_value_start = np.sum(price_start * stock_numbers)
    market_value_end = np.sum(price_end * stock_numbers)
    print('投资组合的初期市值为：%.2f\n投资组合的到期市值为：%.2f' % (market_value_start, market_value_end))


def get_future_PD(future_code, date):
    # 以date日收盘计算期货合约的升贴水比例
    # future_code为股指期货代码，如IF1903.CFE
    # PD=premium&discount
    future_to_index = {'IF': '000300.SH', 'IH': '000016.SH', 'IC': '000905.SH'}
    index_code = future_to_index[future_code[0:2]]
    future_close = w.wss(future_code, "close", "tradeDate="+date+";priceAdj=U;cycle=D").Data[0][0]
    index_close = w.wss(index_code, "close", "tradeDate="+date+";priceAdj=U;cycle=D").Data[0][0]
    PD_ratio = np.max(((index_close - future_close) / index_close, 0))
    print('期货贴水比例为：%.4f%%' % (PD_ratio * 100.0))


def get_portfolio_ratio_v1(portfolio_dict, future_index_code, start_date, end_date, base_date):
    # 从start_date日收盘到end_date日收盘，计算每日组合净值变动与期货主力合约净值变动的相关系数
    # future_index_code，如IF
    # base_date为复权定点日
    # 计算方法采用普通最小二乘法
    data = w.wsd(list(portfolio_dict.keys()), 'close2', start_date, end_date, 'adjDate='+''.join(base_date.split('-'))+';PriceAdj=T').Data
    data = np.array(data)
    stock_numbers = np.array(list(portfolio_dict.values()))
    portfolio_values = np.matmul(stock_numbers, data)  # 投资组合价值序列
    future_index_values = w.wsd(future_index_code+'.CFE', 'close', start_date, end_date, '').Data[0]
    future_index_values = np.array(future_index_values)
    future_contract_multiplier = w.wss(future_index_code+'.CFE', 'contractmultiplier').Data[0][0]
    future_index_values = future_index_values * future_contract_multiplier  # 一手股指期货指数价值序列
    # 投资组合价值为因变量，一手股指期货指数价值为自变量，做线性回归
    future_index_values_diff = np.diff(future_index_values)
    portfolio_values_diff = np.diff(portfolio_values)
    X = sm.add_constant(future_index_values_diff.reshape(-1, 1))
    reg_model = sm.OLS(portfolio_values_diff, X)
    result = reg_model.fit()
    N_star = result.params[1]  # 理论最优手数
    R2 = result.rsquared
    print('理论最优套保手数为：%.4f\n回归拟合度R2值为：%.2f%%' % (N_star, R2*100.0))


if __name__ == '__main__':
    pass