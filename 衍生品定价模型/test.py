import QuantLib as ql

calendar = ql.China()

days = calendar.businessDaysBetween(ql.Date(7, 3, 2018), ql.Date(4, 4, 2018))
for i in range(days):
    print(calendar.advance(ql.Date(7, 3, 2018), i+1, ql.Days))