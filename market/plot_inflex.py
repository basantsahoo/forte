import pandas as pd
from trend.tick_price_smoothing import PriceInflexDetectorForTrend
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from db.market_data import get_daily_tick_data, get_all_days
from trend.technical_patterns import pattern_engine
from matplotlib.backends.backend_pdf import PdfPages
import helper.utils as helper_utils
from settings import reports_dir
import traceback
from datetime import datetime
default_symbols =  ['NIFTY', 'BANKNIFTY']


def plot_fp_ext(report, dfsub,Symbol,day=None):
    total_infl = len(dfsub.index[dfsub['FPInflex']!=''])
    post_ib_df = dfsub.iloc[60:, :]
    post_ib_infl = post_ib_df[post_ib_df['FPInflex']!=''].shape[0]
    fig = plt.figure()
    ax = fig.add_subplot(111)
    plt.plot(dfsub.index,dfsub['Close'],dfsub.index[dfsub['FPInflex']!=''],dfsub.Close[dfsub['FPInflex']!=''])
    plt.ylabel(Symbol+" close price")
    plt.xlabel("Time")
    plt.title("First pass inflex")
    plt.text(0.01, 1.1, 'total infl = ' + str(total_infl), transform=ax.transAxes)
    plt.text(0.01, 1.05, 'post first hr infl = ' + str(post_ib_infl), transform=ax.transAxes)
    if day is not None:
        plt.text(0.9, 1.05, day, transform=ax.transAxes)
    report.savefig()
    plt.close()

def plot_sp_ext(report, dfsub,Symbol,day=None):
    total_infl = len(dfsub.index[dfsub['SPExt']!=''])
    post_ib_df = dfsub.iloc[60:, :]
    post_ib_infl = post_ib_df[post_ib_df['SPExt']!=''].shape[0]
    fig = plt.figure()
    ax = fig.add_subplot(111)
    plt.plot(dfsub.index, dfsub['Close'], dfsub.index[dfsub['SPExt']!=''], dfsub.Close[dfsub['SPExt']!=''])
    plt.ylabel(Symbol+" close price")
    plt.xlabel("Time")
    plt.title("Second pass inflex")
    plt.text(0.01, 1.1, 'total infl = ' + str(total_infl), transform=ax.transAxes)
    plt.text(0.01, 1.05, 'post first hr infl = ' + str(post_ib_infl), transform=ax.transAxes)
    if day is not None:
        plt.text(0.9, 1.05, day, transform=ax.transAxes)
    report.savefig()
    plt.close()
    #plt.show()

def plot_fourth_ext(report, dfsub,Symbol,day=None):
    total_infl = len(dfsub.index[dfsub['FourthExt']!=''])
    post_ib_df = dfsub.iloc[60:, :]
    post_ib_infl = post_ib_df[post_ib_df['FourthExt']!=''].shape[0]
    fig = plt.figure()
    ax = fig.add_subplot(111)
    plt.plot(dfsub.index, dfsub['Close'], dfsub.index[dfsub['FourthExt']!=''], dfsub.Close[dfsub['FourthExt']!=''])
    plt.ylabel(Symbol+" close price")
    plt.xlabel("Time")
    plt.title("Fourth pass inflex")
    plt.text(0.01, 1.1, 'total infl = ' + str(total_infl), transform=ax.transAxes)
    plt.text(0.01, 1.05, 'post first hr infl = ' + str(post_ib_infl), transform=ax.transAxes)
    if day is not None:
        plt.text(0.9, 1.05, day, transform=ax.transAxes)
    report.savefig()
    plt.close()
    #plt.show()

def plot_channel_sp(report, dfsub,Symbol,day=None):
    fig = plt.figure()
    ax = fig.add_subplot(111)
    plt.plot(dfsub.index,dfsub['Close'],dfsub.index[dfsub['SPExt'] =='SPH'],dfsub.Close[dfsub['SPExt'] =='SPH'],dfsub.index[dfsub['SPExt'] =='SPL'],dfsub.Close[dfsub['SPExt'] =='SPL'])
    plt.ylabel(Symbol+" close price")
    plt.xlabel("Time")
    plt.title("Second pass Channel")
    if day is not None:
        #plt.text(0.1, 1.05, 'Second Pass', transform=ax.transAxes)
        plt.text(0.9, 1.05, day, transform=ax.transAxes)
    report.savefig()
    plt.close()


def plot_channel_fp(report, dfsub,Symbol,day=None):
    fig = plt.figure()
    ax = fig.add_subplot(111)
    plt.plot(dfsub.index,dfsub['Close'],dfsub.index[dfsub['FPInflex'] =='FPH'],dfsub.Close[dfsub['FPInflex'] =='FPH'],dfsub.index[dfsub['FPInflex'] =='FPL'],dfsub.Close[dfsub['FPInflex'] =='FPL'])
    plt.ylabel(Symbol+" close price")
    plt.xlabel("Time")
    plt.title("First pass channel")
    if day is not None:
        #plt.text(0.1, 1.05, 'First Pass', transform=ax.transAxes)
        plt.text(0.9, 1.05, day, transform=ax.transAxes)
    report.savefig()
    plt.close()

def plotseries_2(dfsub,Symbol):
    fig = plt.figure()
    ax = fig.add_subplot(111)


    ax.plot(dfsub.index,dfsub['Close'],dfsub.index[dfsub['SPExt']!=''],dfsub.Close[dfsub['SPExt']!=''])
    ax.set_ylabel(Symbol+" close price")
    ax.set_xlabel("Time")
    ax.text(0, 16300, 'Parabola $Y = x^2$', fontsize=5, style='italic', color="red")
    ax.text(3.5, 16300, 'Sine wave', fontsize=5, style='italic', color="red")
    ax.text(-10, 16300, 'Sine wave', fontsize=5, style='italic', color="red")
    ax.text(100, 16300, 'Sine wave', fontsize=5, style='italic', color="red")
    ax.text(0.5, 0.9, 'test', transform=ax.transAxes)
    ax.text(1, 13, 'Practice on GFG', style='italic', bbox={
        'facecolor': 'grey', 'alpha': 0.5, 'pad': 10})

    print('++++++++++++++')
    plt.show()

def plot_daily_chart(symbol, days, interim=False):
    with PdfPages(reports_dir + 'daily_chart_comp_fourp_' + symbol + '.pdf') as report:
        for day in days:
            try:
                price_list = get_daily_tick_data(symbol, day)
                price_list['symbol'] = symbol
                price_list = price_list.to_dict('records')
                # https://medium.com/automation-generation/algorithmically-detecting-and-trading-technical-chart-patterns-with-python-c577b3a396ed
                pattern_detector = PriceInflexDetectorForTrend(symbol, fpth=0.0005, spth = 0.001,  callback=None)
                try:
                    for i in range(len(price_list)):
                        price = price_list[i]
                        pattern_detector.on_price_update([price['timestamp'], price['close']])
                        if interim and pattern_detector.dfstock_3 is not None:
                            dfsub = pattern_detector.dfstock_3
                            #print(dfsub.tail().T)
                            #plot_sp_ext(report, dfsub, symbol, day)
                            plot_fourth_ext(report, dfsub, symbol, day)
                            #plot_fourth_ext(report, dfsub, symbol, day)
                except Exception as e:
                    print(traceback.format_exc())
                    print(e)
                #pattern_detector.create_sp_extremes()
                dfsub = pattern_detector.dfstock_3
                #print(dfsub.head().T)
                dfsub = dfsub.reset_index()

                #plot_fp_ext(report, dfsub, symbol, day)
                plot_sp_ext(report, dfsub, symbol, day)
                plot_fourth_ext(report, dfsub, symbol, day)
                #plot_channel_fp(report, dfsub, symbol, day)
                #plot_channel_sp(report, dfsub, symbol, day)
                dfsub = dfsub.set_index('Time')
                dstring = day if type(day) == str else day.strftime("%Y-%m-%d")
                dfsub.to_csv(reports_dir + dstring+".csv")
            except Exception as e:
                print(e)
                print(traceback.format_exc())
                pass


def plot_charts(symbols = [], days = ['2022-06-15'], for_past_days=30, interim=True):
    start_time = datetime.now()
    if len(symbols) == 0:
        symbols = default_symbols
    for symbol in symbols:
        if len(days) == 0:
            days = get_all_days(helper_utils.get_nse_index_symbol(symbol))[0:for_past_days]
        plot_daily_chart(symbol, days, interim)
    end_time = datetime.now()
    print('plot chart', (end_time - start_time).total_seconds())

if __name__ == '__main__':
    plot_charts(['NIFTY'], interim=True)

"""
data = RawData
tseries = pd.TimeSeries(pd.DatetimeIndex(data['Time']),data.Close)
AO = pd.Series(data['Close'],index=pd.DatetimeIndex(data['Time']))
plt.plot(data['Time'],data['Close'])
plt.ylabel(Symbol+" close price")
plt.xlabel("Time")
"""
#plt.show()
#dfstock = SI.getMultPassTrend(RawData.copy())


