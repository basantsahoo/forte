import pandas as pd
trade_file = '../reports/Trade Book_Dec_21_Feb_22.csv'


def evaluate_direction(sym, typ):
    pos = ''
    if 'IO PE' in sym:
        if typ == 'Buy':
            pos = 'SHORT'
        elif typ == 'Sell':
            pos = 'LONG'

    elif 'IO CE' in sym:
        if typ == 'Buy':
            pos = 'LONG'
        elif typ == 'Sell':
            pos = 'SHORT'
    else:
        if typ == 'Buy':
            pos = 'LONG'
        elif typ == 'Sell':
            pos = 'SHORT'
    return pos

def calculate_position(quantity, direction):
    direction_dict = {'LONG': 1, 'SHORT' : -1}
    return direction_dict[direction] * quantity

df = pd.read_csv(trade_file)
df['Time'] = df['Date'] + " " + df['Time']
df['instrument'] = df['Symbol'].apply(lambda x: 'PUT' if 'IO PE' in x else 'CALL' if 'IO CE' in x else 'FUTURE')
df['underlying'] = df['Symbol'].apply(lambda x: 'BANKNIFTY' if 'BANKNIFTY' in x else 'NIFTY' if 'NIFTY' in x else 'OTHER')
df['index_direction'] = df.apply(lambda x: evaluate_direction(x['Symbol'], x['Trade Type']), axis=1)
df['position'] = df.apply(lambda x: calculate_position(x['Quantity'], x['index_direction']), axis=1)
df = df[['Date', 'Time','Symbol','Trade Type', 'underlying', 'position', 'index_direction',  'Order id']]

df['Time'] = pd.to_datetime(df['Time'])
df['Date'] = pd.to_datetime(df['Date'])
df = df.sort_values(by=['Date', 'Time'])
df['net_poistion'] = df.groupby(['underlying','Date'])['position'].cumsum()
df.to_csv('reports/trade_analysis_Dec_21_Feb_22.csv')
print(df.head())