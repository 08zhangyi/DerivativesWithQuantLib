from utils import get_stock_portfolio, get_portfolio_PL, get_future_PD, get_portfolio_ratio_v1


def main_v1():
    start_date = '2019-02-15'  # 套保初始日
    end_date = '2019-03-14'  # 套保结束日
    base_date = '2019-02-15'  # 复权价格基准日
    ratio_start_date = '2018-08-14'  # 理论最优数量计算采样初始日
    ratio_end_date = '2019-02-15'  # 理论最优数量计算采样结束日
    future_index = 'IF'
    future_code = 'IF1903.CFE'

    portfolio_dict = get_stock_portfolio('套保测算模板v1 - 使用.xlsx')
    get_portfolio_PL(portfolio_dict, start_date, end_date, base_date)
    get_future_PD(future_code, base_date)
    get_portfolio_ratio_v1(portfolio_dict, future_index, ratio_start_date, ratio_end_date, base_date)


if __name__ == '__main__':
    main_v1()