from collections import OrderedDict
from entities.trading_day import TradeDateTime
from config import oi_denomination
import numpy as np
from option_market.technical.cross_over import OptionVolumeIndicator

class OptionCellAnalyser:
    def __init__(self, cell):
        self.cell = cell

    def compute(self):
        self.compute_stats()
        self.compute_day_ledger()

    def compute_stats(self):
        #print(self.cell.__dict__)
        #print(self.cell.ion.__dict__)

        if self.cell.elder_sibling is not None:
            self.cell.analytics['price_delta'] = self.cell.ion.price - self.cell.elder_sibling.ion.price
            self.cell.analytics['oi_delta'] = self.cell.ion.oi - self.cell.elder_sibling.ion.oi
            self.cell.analytics['day_oi_delta'] = self.cell.ion.oi - self.cell.ion.past_closing_oi
            self.cell.analytics['day_oi_delta_pct'] = np.round(self.cell.analytics['day_oi_delta']/self.cell.ion.past_closing_oi, 2) if self.cell.ion.past_closing_oi else 0
            self.cell.analytics['max_oi'] = max(self.cell.ion.oi, self.cell.elder_sibling.analytics['max_oi'])
            self.cell.analytics['cumulative_volume'] = self.cell.ion.volume + self.cell.elder_sibling.analytics['cumulative_volume']

            #print(self.cell.instrument, self.cell.analytics['cumulative_volume'])
            if self.cell.elder_sibling.analytics['cumulative_volume']:
                """
                print("self.cell.elder_sibling.analytics['cumulative_volume']")
                print(self.cell.ion.volume)
                print(self.cell.elder_sibling.analytics['cumulative_volume'])
                """
                self.cell.analytics['vwap'] = (self.cell.ion.price * self.cell.ion.volume
                                               + self.cell.elder_sibling.analytics['vwap']
                                               * self.cell.elder_sibling.analytics['cumulative_volume'])/(self.cell.ion.volume + self.cell.elder_sibling.analytics['cumulative_volume'])
            else:
                self.cell.analytics['vwap'] = self.cell.ion.price
            self.cell.analytics['vwap_delta'] = self.cell.analytics['vwap'] - self.cell.elder_sibling.analytics['vwap']

            self.cell.ledger['price'] = (self.cell.ion.price + self.cell.elder_sibling.ion.price) * 0.5
            self.cell.ledger['qty'] = self.cell.ion.oi - self.cell.elder_sibling.ion.oi
            self.cell.ledger['net_qty'] = self.cell.ion.oi
            self.cell.ledger['prev_net_qty'] = self.cell.elder_sibling.ledger['net_qty']
            self.cell.ledger['prev_owap'] = self.cell.elder_sibling.ledger['owap']
            self.cell.ledger['prev_cum_investment'] = self.cell.elder_sibling.ledger['cum_investment']
            self.cell.ledger['prev_max_investment'] = self.cell.elder_sibling.ledger['max_investment']
            self.cell.ledger['prev_realized_pnl'] = self.cell.elder_sibling.ledger['realized_pnl']


        else:
            """
            if self.cell.instrument == '21700_PE':
                print('first item')
                print('self.cell.ion.oi==', self.cell.ion.oi)
            """
            #print(self.cell.__dict__)
            #print(self.cell.ion.__dict__)
            self.cell.analytics['price_delta'] = 0
            self.cell.analytics['oi_delta'] = 0
            self.cell.analytics['day_oi_delta'] = self.cell.ion.oi - self.cell.ion.past_closing_oi
            self.cell.analytics['day_oi_delta_pct'] = np.round(self.cell.analytics['day_oi_delta']/self.cell.ion.past_closing_oi, 2) if self.cell.ion.past_closing_oi else 0
            #self.cell.analytics['volume_scale'] = self.cell.ion.volume/self.cell.ion.past_avg_volume
            self.cell.analytics['max_oi'] = self.cell.ion.oi
            self.cell.analytics['cumulative_volume'] = self.cell.ion.volume
            self.cell.analytics['vwap'] = self.cell.ion.price
            self.cell.analytics['vwap_delta'] = 0

            self.cell.ledger['price'] = self.cell.ion.price
            self.cell.ledger['qty'] = self.cell.ion.oi
            self.cell.ledger['net_qty'] = self.cell.ion.oi
            self.cell.ledger['prev_net_qty'] = 0
            self.cell.ledger['prev_owap'] = 0
            self.cell.ledger['prev_cum_investment'] = 0
            self.cell.ledger['prev_max_investment'] = 0
            self.cell.ledger['prev_realized_pnl'] = 0
        """
        if self.cell.ion.oi < 0:
            print('\007')
        """
        #Trader P&L Calc

        self.cell.ledger['add_qty'] = self.cell.ledger['qty'] if self.cell.ledger['qty'] > 0 else 0
        self.cell.ledger['reduce_qty'] = abs(self.cell.ledger['qty']) if self.cell.ledger['qty'] < 0 else 0
        self.cell.ledger['owap'] = (self.cell.ledger['add_qty'] * self.cell.ledger['price'] + self.cell.ledger['prev_net_qty']*self.cell.ledger['prev_owap'])/(self.cell.ledger['prev_net_qty'] + self.cell.ledger['add_qty'])
        self.cell.ledger['investment'] = self.cell.ledger['qty'] * self.cell.ledger['price']
        self.cell.ledger['cum_investment'] = self.cell.ledger['prev_cum_investment'] + self.cell.ledger['investment']
        self.cell.ledger['max_investment'] = max(self.cell.ledger['cum_investment'], self.cell.ledger['prev_max_investment'])
        self.cell.ledger['realized_pnl'] = self.cell.ledger['prev_realized_pnl'] + self.cell.ledger['reduce_qty'] * (self.cell.ledger['prev_owap'] - self.cell.ledger['price'])
        self.cell.ledger['un_realized_pnl'] = self.cell.ledger['net_qty'] * (self.cell.ledger['owap'] - self.cell.ledger['price'])
        self.cell.ledger['total_pnl'] = self.cell.ledger['realized_pnl'] + self.cell.ledger['un_realized_pnl']
        self.cell.ledger['percent_pnl'] = np.round(self.cell.ledger['total_pnl'] / self.cell.ledger['max_investment'],2)
        """
        if self.cell.instrument == '21900_PE':
            print('*****************************')
            print('qty=====', self.cell.ledger['qty'])
            print('price=====', self.cell.ledger['price'])
            print('investment=====', self.cell.ledger['investment'])
            print('cum_investment=====', self.cell.ledger['cum_investment'])
            print('max_investment=====', self.cell.ledger['max_investment'])
            print('realized_pnl=====', self.cell.ledger['realized_pnl'])
            print('un_realized_pnl=====', self.cell.ledger['un_realized_pnl'])
            print('total_pnl=====', self.cell.ledger['total_pnl'])
            print('percent_pnl=====', self.cell.ledger['percent_pnl'])
        """

    def compute_day_ledger(self):
        if self.cell.elder_sibling is not None and self.cell.elder_sibling.trade_date == self.cell.trade_date:
            self.cell.day_ledger['price'] = (self.cell.ion.price + self.cell.elder_sibling.ion.price) * 0.5
            self.cell.day_ledger['qty'] = self.cell.ion.oi - self.cell.elder_sibling.ion.oi
            self.cell.day_ledger['net_qty'] = self.cell.ion.oi
            self.cell.day_ledger['prev_net_qty'] = self.cell.elder_sibling.day_ledger['net_qty']
            self.cell.day_ledger['prev_owap'] = self.cell.elder_sibling.day_ledger['owap']
            self.cell.day_ledger['prev_cum_investment'] = self.cell.elder_sibling.day_ledger['cum_investment']
            self.cell.day_ledger['prev_max_investment'] = self.cell.elder_sibling.day_ledger['max_investment']
            self.cell.day_ledger['prev_realized_pnl'] = self.cell.elder_sibling.day_ledger['realized_pnl']
        else:
            self.cell.day_ledger['price'] = self.cell.ion.price
            self.cell.day_ledger['qty'] = self.cell.ion.oi
            self.cell.day_ledger['net_qty'] = self.cell.ion.oi
            self.cell.day_ledger['prev_net_qty'] = 0
            self.cell.day_ledger['prev_owap'] = 0
            self.cell.day_ledger['prev_cum_investment'] = 0
            self.cell.day_ledger['prev_max_investment'] = 0
            self.cell.day_ledger['prev_realized_pnl'] = 0

        self.cell.day_ledger['add_qty'] = self.cell.day_ledger['qty'] if self.cell.day_ledger['qty'] > 0 else 0
        self.cell.day_ledger['reduce_qty'] = abs(self.cell.day_ledger['qty']) if self.cell.day_ledger['qty'] < 0 else 0
        self.cell.day_ledger['owap'] = (self.cell.day_ledger['add_qty'] * self.cell.day_ledger['price'] + self.cell.day_ledger['prev_net_qty']*self.cell.day_ledger['prev_owap'])/(self.cell.day_ledger['prev_net_qty'] + self.cell.day_ledger['add_qty'])
        self.cell.day_ledger['investment'] = self.cell.day_ledger['qty'] * self.cell.day_ledger['price']
        self.cell.day_ledger['cum_investment'] = self.cell.day_ledger['prev_cum_investment'] + self.cell.day_ledger['investment']
        self.cell.day_ledger['max_investment'] = max(self.cell.day_ledger['cum_investment'], self.cell.day_ledger['prev_max_investment'])
        self.cell.day_ledger['realized_pnl'] = self.cell.day_ledger['prev_realized_pnl'] + self.cell.day_ledger['reduce_qty'] * (self.cell.day_ledger['prev_owap'] - self.cell.day_ledger['price'])
        self.cell.day_ledger['un_realized_pnl'] = self.cell.day_ledger['net_qty'] * (self.cell.day_ledger['owap'] - self.cell.day_ledger['price'])
        self.cell.day_ledger['total_pnl'] = self.cell.day_ledger['realized_pnl'] + self.cell.day_ledger['un_realized_pnl']
        self.cell.day_ledger['percent_pnl'] = np.round(self.cell.day_ledger['total_pnl'] / self.cell.day_ledger['max_investment'], 2)
        """
        if self.cell.instrument == '21900_PE':
            print('*****************************')
            print('qty=====', self.cell.day_ledger['qty'])
            print('price=====', self.cell.day_ledger['price'])
            print('investment=====', self.cell.day_ledger['investment'])
            print('cum_investment=====', self.cell.day_ledger['cum_investment'])
            print('max_investment=====', self.cell.day_ledger['max_investment'])
            print('realized_pnl=====', self.cell.day_ledger['realized_pnl'])
            print('un_realized_pnl=====', self.cell.day_ledger['un_realized_pnl'])
            print('total_pnl=====', self.cell.day_ledger['total_pnl'])
            print('percent_pnl=====', self.cell.day_ledger['percent_pnl'])
        """
    def update_analytics(self, field, value):
        self.cell.analytics[field] = value


class SpotCellAnalyser:
    def __init__(self, cell):
        self.cell = cell

    def compute(self):
        if self.cell.elder_sibling is not None:
            self.cell.analytics['price_delta'] = self.cell.ion.close - self.cell.elder_sibling.ion.close
        else:
            self.cell.analytics['price_delta'] = 0

    def update_analytics(self, field, value):
        self.cell.analytics[field] = value

"""
class OptionMatrixAnalyser:

    def __init__(self, option_matrix=None):
        self.option_matrix = option_matrix
        self.call_oi_delta_grid = {}
        self.put_oi_delta_grid = {}
        self.call_volume_grid = {}
        self.put_volume_grid = {}

    def analyse(self):
        if self.option_matrix is not None:
            self.analyse()

    def calculate_info(self):
        day_capsule = self.option_matrix.get_day_capsule(self.option_matrix.current_date)
        ts_list = day_capsule.cross_analyser.get_ts_series()
        for idx in range(1, len(ts_list)):
            for instrument, instrument_capsule in day_capsule.trading_data.items():
                curr_cell = instrument_capsule.trading_data[ts_list[idx]]
                prev_cell = instrument_capsule.trading_data[ts_list[idx-1]]
                print(curr_cell)
"""
"""
    def analyse(self):
        print('matrix analyse')
"""
"""
        self.calculate_info()
        if self.option_matrix.last_time_stamp is not None:
            print(TradeDateTime(self.option_matrix.last_time_stamp).date_time_string)
        day_capsule = self.option_matrix.get_day_capsule(self.option_matrix.current_date)
        print(day_capsule.trading_data)
        for instrument, capsule in day_capsule.trading_data.items():
            pass
"""