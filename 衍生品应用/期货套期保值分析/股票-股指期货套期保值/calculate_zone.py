from utils import get_stock_portfolio, get_portfolio_PL, get_future_PD, get_portfolio_ratio_v1


def main_v1():
    start_date = '2016-12-12'  # 套保初始日
    end_date = '2017-01-19'  # 套保结束日
    base_date = start_date  # 复权价格基准日
    ratio_start_date = '2016-09-08'  # 理论最优数量计算采样初始日
    ratio_end_date = start_date  # 理论最优数量计算采样结束日
    future_index = 'IF'
    future_code = 'IF1701.CFE'

    portfolio_dict = get_stock_portfolio('套保测算模板v1.xlsx')
    # portfolio_dict = get_stock_portfolio('套保测算模板v1 - 使用.xlsx')
    get_portfolio_PL(portfolio_dict, start_date, end_date, base_date)
    get_future_PD(future_code, base_date)
    get_portfolio_ratio_v1(portfolio_dict, future_index, ratio_start_date, ratio_end_date, base_date)


if __name__ == '__main__':
    main_v1()