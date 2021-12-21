import datetime
from WindPy import w
w.start()


# 函数区
# 从Wind获取期权组合的历史价格，DATE日收盘后数据
def get_option_portfolio_value_from_Wind(option_portfolio, date):
    option_portfoio_b = w.wss(option_portfolio['B'], "close,exe_ratio,exe_price,exe_mode", "tradeDate="+date+";priceAdj=U;cycle=D").Data
    option_portfoio_s = w.wss(option_portfolio['S'], "close,exe_ratio,exe_price,exe_mode", "tradeDate="+date+";priceAdj=U;cycle=D").Data
    # print(option_portfoio_b, option_portfoio_s)
    value = option_portfoio_b[0][0] * option_portfoio_b[1][0] - option_portfoio_s[0][0] * option_portfoio_s[1][0]  # 单张期权组合价值
    number = option_portfoio_b[1][0]
    if option_portfoio_b[3][0] == '认购':
        spread_type = 'BULL'
        lower_price = option_portfoio_b[2][0]  # 价差组合下限
        higher_price = option_portfoio_s[2][0]  # 价差组合上限
    elif option_portfoio_b[3][0] == '认沽':
        spread_type = 'BEAR'
        value = option_portfoio_b[0][0] * option_portfoio_b[1][0] - option_portfoio_s[0][0] * option_portfoio_s[1][0]
        lower_price = option_portfoio_s[2][0]  # 价差组合下限
        higher_price = option_portfoio_b[2][0]  # 价差组合上限
    else:
        raise Exception("非法的期权类型")
    return value, number, lower_price, higher_price, spread_type


def spread_option_income_certificate(start_date, end_date, underlying_index, underlying_asset, basic_return_rate, spread_options, principle, fixed_return_rate):
    '''
    # 产品基本特征
    :param start_date:
    :param end_date:
    :param underlying_index: 挂钩标的指数
    :param underlying_asset: 挂钩对应投资资产
    :param basic_return_rate: 产品基础收益率（最低收益率；年化，下同）
    :param spread_options: 价差期权构成，支持看涨牛市价差或看跌熊市价差
    :param principle:
    # 市场参数特征
    :param fix_return_rate: 相同期限固定收益产品收益率
    :return: floating_bottom_point: 浮动下限点位
             floating_bottom_ratio: 浮动下限比例
             floating_ceiling_point: 浮动上限点位
             floating_ceiling_ratio: 浮动上限比例
             bottom_return: 下限收益率
             ceiling_return: 上限收益率
             participate_ratio: 参与率
             underlying_index_end: 到期日指数
             return_rate_end: 到期日产品收益率
             hedge_value: 对冲收入（元）
    '''
    # 计算单利计息天数
    N = datetime.datetime.strptime(end_date, '%Y-%m-%d') - datetime.datetime.strptime(start_date, '%Y-%m-%d')
    N = N.days
    # 计算保证基础收益率时的可购买期权组合的资金量
    option_available = principle - principle * (1 + basic_return_rate * N / 365) / (1 + fixed_return_rate * N / 365)
    print('\n产品发行日为%s，产品到期日为%s，一共%i个自然日，产品发行规模为%.2f元，给定的同期固定收益产品利率为%.2f%%' % (start_date, end_date, N, principle, fixed_return_rate*100))
    print('可购买期权的资金为：%.2f元' % option_available)

    # 产品理论到期日收益情况
    # 计算价差期权组合单位价值和单位数量
    option_value, option_number, asset_lower, asset_higher, spread_type = get_option_portfolio_value_from_Wind(spread_options, start_date)
    option_portfolio_buy = option_available / option_value  # 购买价差组合的数量
    print('单位期权组合价值%.2f元' % option_value, '单位期权组合资产数量%.2f份' % option_number, '购买期权组合数量%.4f张' % option_portfolio_buy)
    # 标的指数和期权的相关价格
    underlying_index_start = w.wss(underlying_index, "close", "tradeDate="+start_date+";priceAdj=U;cycle=D").Data[0][0]
    underlying_asset_start = w.wss(underlying_asset, "close", "tradeDate="+start_date+";priceAdj=U;cycle=D").Data[0][0]
    index_lower = underlying_index_start * asset_lower / underlying_asset_start  # 指数浮动区间下限
    index_higher = underlying_index_start * asset_higher / underlying_asset_start  # 指数浮动区间上限
    if spread_type == 'BULL':
        print('\n挂钩指数：%s，%s日收盘点位：%.2f点（100%%）' % (underlying_index, start_date, underlying_index_start),
              '\n浮动下限对应指数：%.2f点（%.2f%%）' % (index_lower, index_lower/underlying_index_start*100),
              '\n浮动上限对应指数：%.2f点（%.2f%%）' % (index_higher, index_higher/underlying_index_start*100))
        floating_bottom_point = index_lower
        floating_bottom_ratio = index_lower/underlying_index_start
        floating_ceiling_point = index_higher
        floating_ceiling_ratio = index_higher/underlying_index_start
    elif spread_type == 'BEAR':
        print('\n挂钩指数：%s，%s日收盘点位：%.2f点（100%%）' % (underlying_index, start_date, underlying_index_start),
              '\n浮动下限对应指数：%.2f点（%.2f%%）' % (index_higher, index_higher/underlying_index_start*100),
              '\n浮动上限对应指数：%.2f点（%.2f%%）' % (index_lower, index_lower / underlying_index_start * 100))
        floating_bottom_point = index_higher
        floating_bottom_ratio = index_higher/underlying_index_start
        floating_ceiling_point = index_lower
        floating_ceiling_ratio = index_lower / underlying_index_start
    else:
        raise Exception("非法的期权类型")
    # 计算最佳情形期权投资的总盈亏
    spread_option_max = (asset_higher - asset_lower) * option_number * option_portfolio_buy  # 期权投资最大收益率
    return_max = (spread_option_max / principle) * 365 / N  # 年化期权投资最大收益率
    participate_ratio = return_max / ((index_higher - index_lower) / underlying_index_start)
    print('\n产品下限年化收益率为：%.4f%%\n产品上限年化收益率为：%.4f%%\n产品年化参与率为：%.4f%%' % (basic_return_rate*100, return_max*100+basic_return_rate*100, participate_ratio*100))

    # 产品到期日根据条款实际收益和对冲情况
    # 计算条款收益
    underlying_index_end = w.wss(underlying_index, "close", "tradeDate="+end_date+";priceAdj=U;cycle=D").Data[0][0]
    # underlying_index_end = 6000
    return_rate = min(max((underlying_index_end - index_lower) / (index_higher - index_lower), 0), 1) * return_max  # 年化到期超额收益率
    return_value = return_rate * principle * N /365  # 实际到期应付出的超额资金
    option_value, _, _, _, _ = get_option_portfolio_value_from_Wind(spread_options, end_date)
    option_return = option_portfolio_buy * option_value  # 期权投资到期盈亏
    hedge_value = option_return - return_value  # 对冲盈亏
    print('\n到期日%s挂钩指数为：%.2f点，产品到期年化收益率为：%.4f%%' % (end_date, underlying_index_end, return_rate*100+basic_return_rate*100))
    print('产品投资对冲收入为：%.2f元' % hedge_value)

    bottom_return = basic_return_rate
    ceiling_return = return_max+basic_return_rate
    return_rate_end = return_rate+basic_return_rate
    participate_ratio = participate_ratio
    return floating_bottom_point, floating_bottom_ratio, floating_ceiling_point, floating_ceiling_ratio, \
           bottom_return, ceiling_return, participate_ratio, underlying_index_end, return_rate_end, hedge_value


if __name__ == "__main__":
    # 产品基本特征
    START_DATE = '2021-09-24'
    END_DATE = '2021-10-25'
    UNDERLYING_INDEX = '000300.SH'  # 挂钩标的指数
    UNDERLYING_ASSET = '510300.SH'  # 挂钩对应投资资产
    BASIC_RATE_RATE = 0.015  # 产品基础收益率（最低收益率；年化，下同）
    BULL_SPREADS = {'B': '10003600.SH', 'S': '10003604.SH'}  # 牛市价差期权构成
    BEAR_SPREADS = {'B': '10003613.SH', 'S': '10003609.SH'}  # 熊市价差期权构成
    PRINCIPLE = 10000000
    # 市场参数特征
    FIXED_RETURN_RATE = 0.032  # 相同期限固定收益产品收益率

    print(spread_option_income_certificate(START_DATE, END_DATE, UNDERLYING_INDEX, UNDERLYING_ASSET, BASIC_RATE_RATE,
                                           BULL_SPREADS, PRINCIPLE, FIXED_RETURN_RATE))