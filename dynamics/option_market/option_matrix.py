"""
OptionMatrix:
capsule (
    trading_data:{
        '2023-12-01':capsule(
                        trading_data:{
                            '42000_CE':capsule(
                                          trading_data:{
                                              epoc1: cell(
                                                        ion
                                                        analytics
                                                    )
                                          }
                                    )
                        },
                        transposed_data: {
                            epoc1: {
                                '42000_CE': cell
                            }
                        },
                        cross_analyser: None
                    )
    }
    analytics:{}
    )
"""

from entities.trading_day import NearExpiryWeek
from dynamics.option_market.building_blocks import Capsule
from dynamics.option_market.intraday_cross_analyser import IntradayCrossAssetAnalyser
#from option_market.analysers import OptionMatrixAnalyser
from dynamics.option_market.throttlers import OptionFeedThrottler, FeedThrottler, SpotFeedThrottler
from dynamics.option_market.signal_generator import OptionSignalGenerator
from dynamics.option_market.building_blocks import OptionCell, OptionIon
from entities.trading_day import TradeDateTime

volume_multiplier_dict = {'1min': 1, '5min': 5, '15min': 15}

class OptionMatrix:

    def __init__(self,  asset, feed_speed=1, throttle_speed=15, instant_compute=True, live_mode=False, volume_delta_mode=False, print_cross_stats=False, period="1min"):
        self.asset = asset
        self.capsule = Capsule()
        self.spot_capsule = Capsule()
        self.instant_compute = instant_compute
        #self.matrix_analyser = OptionMatrixAnalyser(self)
        self.current_date = None
        self.signal_generator = OptionSignalGenerator(self, live_mode)
        self.option_data_throttler = OptionFeedThrottler(self, feed_speed, throttle_speed)
        self.data_throttler = FeedThrottler(self, feed_speed, throttle_speed)
        self.spot_throttler = SpotFeedThrottler(self, feed_speed, throttle_speed)
        self.avg_volumes = {}
        self.closing_oi = {}
        self.hist_ltp = {}
        self.live_mode = live_mode
        self.counter = 0
        self.last_time_stamp = None
        self.volume_delta_mode = volume_delta_mode
        self.print_cross_stats = print_cross_stats
        self.period = period
        self.aggregation_factor = throttle_speed / feed_speed
        self.volume_multiplier = volume_multiplier_dict[self.period]
        self.live_ltps = {}


    def frame_change_action(self, current_frame, next_frame):
        #print('----------------frame_change_action', self.period)
        #print('----------------frame_change_action', TradeDateTime(current_frame).date_time_string)
        self.last_time_stamp = int(int(current_frame/(self.aggregation_factor * 60)) * self.aggregation_factor * 60)
        #print('option matrix, frame_change_action++++', next_frame)
        self.spot_throttler.check_time_to_push(next_frame)
        self.option_data_throttler.check_time_to_push(next_frame)
        self.data_throttler.check_time_to_push(next_frame)

    def process_avg_volume(self, trade_date, inst_vol_list):
        self.avg_volumes[trade_date] = {}
        for inst_vol in inst_vol_list:
            self.avg_volumes[trade_date][inst_vol['kind']] = inst_vol['avg_volume'] * self.volume_multiplier

    def process_closing_oi(self, trade_date, inst_oi_list):
        self.closing_oi[trade_date] = {}
        for inst_vol in inst_oi_list:
            self.closing_oi[trade_date][inst_vol['instrument']] = inst_vol['closing_oi']
        #print(self.closing_oi)

    def process_hist_ltp(self, trade_date, inst_ltp_list):
        self.hist_ltp[trade_date] = {}
        for inst in inst_ltp_list:
            #print(inst)
            self.hist_ltp[trade_date][inst['instrument']] = inst['ltp']

    def check_adjust_closing_oi(self, trade_date):
        """
        Reset closing oi to 0 when trade date is week begining
        closing oi will be set to first entry in price throttler
        """
        if self.current_date != trade_date:
            t_day = TradeDateTime(trade_date)
            near_week = NearExpiryWeek(t_day, self.asset)
            if t_day.date_string == near_week.start_date.date_string:
                for inst in self.closing_oi[trade_date].keys():
                    self.closing_oi[trade_date][inst] = 0

    def process_option_feed(self, instrument_data_list):
        #print('process_option_feed+++++++++++++++++', instrument_data_list)
        self.check_adjust_closing_oi(instrument_data_list[0]['trade_date'])
        self.current_date = instrument_data_list[0]['trade_date']
        self.option_data_throttler.throttle(instrument_data_list)
        for instrument_data in instrument_data_list:
            self.live_ltps[instrument_data['instrument']] = {'close': instrument_data['close'], 'timestamp':instrument_data['timestamp']}

    def process_spot_feed(self, instrument_data_list):
        #print('process_spot_feed+++++++++++++++++', instrument_data_list)
        self.current_date = instrument_data_list[0]['trade_date']
        self.spot_throttler.throttle(instrument_data_list)


    def process_feed_without_signal(self, instrument_data_list):
        self.check_adjust_closing_oi(instrument_data_list[0]['trade_date'])
        self.current_date = instrument_data_list[0]['trade_date']
        self.data_throttler.throttle(instrument_data_list)

    def get_day_capsule(self, trade_date):
        #print(self.capsule.trading_data)
        return self.capsule.trading_data.get(trade_date, None)

    def get_day_spot_capsule(self, trade_date):
        return self.spot_capsule.trading_data[trade_date]

    def get_instrument_capsule(self, trade_date, instrument):

        if instrument in ['spot']:
            return self.get_day_spot_capsule(trade_date).trading_data[instrument]
        else:
            return self.capsule.trading_data[trade_date].trading_data[instrument]

    def get_prev_day(self, trade_date):
        all_days = [TradeDateTime(day) for day in list(self.capsule.trading_data.keys())]
        filtered_days = [day for day in all_days if day.ordinal < TradeDateTime(trade_date).ordinal]
        filtered_days.sort()
        if filtered_days:
            return filtered_days[-1].date_string
        else:
            return None

    def get_prev_day_instrument_capsule(self, trade_date, instrument):
        prev_day = self.get_prev_day(trade_date)

        if prev_day is not None:
            instrument_capsule = self.get_instrument_capsule(prev_day, instrument)
            if instrument_capsule is None:
                instrument_capsule = self.get_prev_day_instrument_capsule(prev_day, instrument)
        else:
            instrument_capsule = None
        return instrument_capsule


    def get_prev_day_instrument_capsule_o(self, trade_date, instrument):
        all_days = [TradeDateTime(day) for day in list(self.capsule.trading_data.keys())]
        filtered_days = [day for day in all_days if day.ordinal < TradeDateTime(trade_date).ordinal]
        filtered_days.sort()
        if filtered_days:
            instrument_capsule = self.get_instrument_capsule(filtered_days[-1].date_string, instrument)
            return instrument_capsule
        else:
            instrument_capsule = self.get_prev_day_instrument_capsule(filtered_days[-1].date_string, instrument)

        return instrument_capsule

    def get_spot_instrument_capsule(self, trade_date, instrument):
        return self.spot_capsule.trading_data[trade_date].trading_data[instrument]

    def add_spot_cells(self, trade_date, cell_list):
        self.counter += 1
        timestamp_set = set()
        if not self.spot_capsule.in_trading_data(trade_date):
            capsule = Capsule()
            self.spot_capsule.insert_trading_data(trade_date, capsule)
        day_capsule = self.get_day_spot_capsule(trade_date)
        for cell in cell_list:
            if not day_capsule.in_trading_data(cell.instrument):
                day_capsule.insert_trading_data(cell.instrument, Capsule())
            instrument_capsule = self.get_spot_instrument_capsule(trade_date, cell.instrument)
            instrument_capsule.insert_trading_data(cell.timestamp, cell)
            cell.fresh_born(self, trade_date)
            cell.validate_ion_data()
            timestamp_set.add(cell.timestamp)

    def add_cells(self, trade_date, cell_list):
        self.counter += 1
        if cell_list:
            #self.last_time_stamp = cell_list[0].timestamp
            pass
            #print(self.counter)
            """
            if self.last_time_stamp == 1703843580:
                for cell in cell_list:
                    print(cell.instrument, " ", cell.timestamp, " ", cell.ion.oi)
            """
            #print(cell_list[0].instrument)
            #print("==========================================", self.counter)
        timestamp_set = set()
        if not self.capsule.in_trading_data(trade_date):
            capsule = Capsule()
            day_spot_capsule = self.get_day_spot_capsule(trade_date)
            cross_analyser = IntradayCrossAssetAnalyser(capsule, day_spot_capsule, self.avg_volumes[trade_date], self.closing_oi[trade_date])
            capsule.cross_analyser = cross_analyser
            self.capsule.insert_trading_data(trade_date, capsule)
        day_capsule = self.get_day_capsule(trade_date)

        for cell in cell_list:
            if not day_capsule.in_trading_data(cell.instrument):
                day_capsule.insert_trading_data(cell.instrument, Capsule())
            instrument_capsule = self.get_instrument_capsule(trade_date, cell.instrument)
            instrument_capsule.insert_trading_data(cell.timestamp, cell)
            day_capsule.insert_transposed_data(cell.timestamp, cell.instrument, cell)
            cell.fresh_born(self, trade_date)
            cell.validate_ion_data()
            cell.analyse()
            timestamp_set.add(cell.timestamp)
        ts_list = list(timestamp_set)
        ts_list.sort()
        #print('create dummy cells', ts_list)
        self.create_dummy_cells(ts_list)
        day_capsule.cross_analyser.compute(ts_list)

    def create_dummy_cells(self, ts_list):
        day_capsule = self.get_day_capsule(self.current_date)
        prev_day = self.get_prev_day(self.current_date)
        prev_day_capsule = self.get_day_capsule(prev_day)

        for ts in ts_list:
            curr_time_insts = list(day_capsule.transposed_data[ts].keys())
            ts_history = [x for x in list(day_capsule.transposed_data.keys()) if x < ts]
            missing_cells = []
            if ts_history:
                all_cells_in_prev_time = list(day_capsule.transposed_data[max(ts_history)].values())
                missing_cells = [cell for cell in all_cells_in_prev_time if cell.instrument not in curr_time_insts]
            elif prev_day_capsule is not None:
                ts_history = [x for x in list(prev_day_capsule.transposed_data.keys()) if x < ts]
                all_cells_in_prev_time = list(prev_day_capsule.transposed_data[max(ts_history)].values())
                missing_cells = [cell for cell in all_cells_in_prev_time if cell.instrument not in curr_time_insts]

            for m_cell in missing_cells:
                #print("missing_cells====", m_cell.instrument)
                cell = OptionCell(self.current_date, ts, m_cell.instrument, None, m_cell.volume_delta_mode)
                if not day_capsule.in_trading_data(cell.instrument):
                    day_capsule.insert_trading_data(cell.instrument, Capsule())
                cell.ion = OptionIon(None, None, None)
                cell.fresh_born(self, self.current_date)
                cell.validate_ion_data()
                cell.ion = self.option_data_throttler.apply_closing_oi(cell.ion, cell.instrument)
                cell.ion.volume = 0
                #print(cell.ion.__dict__)
                cell.analyse()
                instrument_capsule = self.get_instrument_capsule(self.current_date, m_cell.instrument)
                instrument_capsule.insert_trading_data(cell.timestamp, cell)
                day_capsule.insert_transposed_data(cell.timestamp, cell.instrument, cell)


    def generate_signal(self):
        if self.instant_compute:
            #self.matrix_analyser.analyse()
            self.signal_generator.generate()


    def get_last_tick(self, inst):
        #print('option market get last tick=======', inst)
        """
        print("self.current_date======", self.current_date, "inst====", inst)
        print('self.asset=====', self.asset)
        print('self.period========', self.period)
        print('self.capsule====', self.capsule.trading_data)
        """
        if inst in self.live_ltps:
            live_tick = self.live_ltps[inst]
            return live_tick

        day_capsule = self.get_day_capsule(self.current_date)
        trading_data = getattr(day_capsule, 'trading_data', {})
        instrument_capsule = trading_data.get(inst)
        if instrument_capsule:
            last_tick = instrument_capsule.last_tick
            candle = last_tick.ion.to_candle()
            candle['timestamp'] = last_tick.timestamp
            return candle
        else:
            hist_ltp = self.hist_ltp[self.current_date][inst]
            hist_tick = {'close': hist_ltp}
            return hist_tick
            #return None

    def get_closest_instrument(self, inst):
        #print('get_closest_instrument+++++++', inst)
        inst_strike = int(inst[:-3])
        day_capsule = self.get_day_capsule(self.current_date)
        instruments = day_capsule.transposed_data[self.last_time_stamp].keys()
        strikes = [int(tmp_inst[:-3]) for tmp_inst in instruments if tmp_inst[-2::] == inst[-2::]]
        desired_strike = [strike for strike in strikes if abs(inst_strike-strike) == min([abs(inst_strike)-strike for strike in strikes])][0]
        return str(desired_strike) + "_" + inst[-2::]

    def get_ts_volume(self,trade_day,ts):
        #print('++++++++++++++++++++++++++++++here 1 ++++++++++++++++')
        call_volume = self.capsule.trading_data[trade_day].cross_analyser.call_volume[ts]
        put_volume = self.capsule.trading_data[trade_day].cross_analyser.put_volume[ts]
        return put_volume, call_volume

    def subscribe_to_clock(self, clock):
        clock.subscribe_to_frame_change(self.frame_change_action)
