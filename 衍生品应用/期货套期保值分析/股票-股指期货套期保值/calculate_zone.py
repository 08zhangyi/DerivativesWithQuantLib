from utils import get_stock_portfolio, get_portfolio_PL, get_future_PD, get_portfolio_ratio_v1


def main_v1():
    start_date = '2019-02-15'
    end_date = '2019-03-14'
    base_date = '2019-02-15'
    future_index = 'IF'
    future_code = 'IF1903.CFE'

    portfolio_dict = get_stock_portfolio('套保测算模板v1 - 使用.xlsx')
    get_portfolio_PL(portfolio_dict, start_date, end_date, base_date)
    get_future_PD(future_code, base_date)
    get_portfolio_ratio_v1(portfolio_dict, future_index, start_date, end_date, base_date)


if __name__ == '__main__':
    main_v1()