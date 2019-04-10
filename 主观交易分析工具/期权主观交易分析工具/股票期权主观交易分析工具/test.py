import QuantLib as ql

payoff = ql.PlainVanillaPayoff(ql.Option.Call, 100)
print(payoff(95))

from WindPy import w
import datetime

w.start()
code = '10001755.SH'
# 获取最新成交价，买一价，卖一价
data = [temp[0] for temp in w.wsq(code, "rt_latest,rt_bid1,rt_ask1").Data]
print(data)
latest_price, bid1_price, ask1_price = data

date_now = datetime.datetime.now().strftime('%Y-%m-%d')  # 获取当日的时点
option_data = w.wss("10001546.SH", "exe_mode,exe_type,exe_price,exe_ratio,lasttradingdate,exe_enddate","tradeDate="+date_now).Data
print(option_data)
option_type = option_data[0][0]
option_strike = option_data[2][0]
option_volume = option_data[3][0]
option_last_day = option_data[4][0].strftime('%Y-%m-%d')

