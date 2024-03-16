import numpy as np
import time
from entities.trading_day import TradeDateTime
from tabulate import tabulate
from dynamics.option_market.technical.cross_over import DownCrossOver, BuildUpFollowingMomentum, OptionVolumeIndicator, \
    OptionMomentumIndicator, PutBuyIndicator
from entities.base import Signal

class OptionSignalGenerator:
    def __init__(self, matrix, live_mode=False):
        self.option_matrix = matrix
        self.trade_hold_period = 30
        self.roll_period = 30
        self.max_oi = 0
        self.attention_oi = 1
        self.minutes_past = 0
        self.live_mode = live_mode
        self.inform_hour = 15
        self.call_down_cross_over = DownCrossOver('CALL_DOWN_CROSS', 0.05, call_back_fn=self.dispatch_signal)
        self.put_down_cross_over = DownCrossOver('PUT_DOWN_CROSS', 0.05, call_back_fn=self.dispatch_signal)
        self.build_up_calculator = BuildUpFollowingMomentum('BUILDUP', call_back_fn=self.dispatch_signal)
        self.option_volume_indicator = OptionVolumeIndicator('OPTION_VOLUME', call_back_fn=self.dispatch_signal)
        self.bullish_option_momentum_indicator = OptionMomentumIndicator('BULLISH_MOMENTUM', info_fn=self.get_info, call_back_fn=self.dispatch_signal)
        self.bearish_option_momentum_indicator = OptionMomentumIndicator('BEARISH_MOMENTUM', info_fn=self.get_info, call_back_fn=self.dispatch_signal)
        self.put_buy_indicator = PutBuyIndicator('BEARISH_MOMENTUM', info_fn=self.get_info, call_back_fn=self.dispatch_signal)
        self.signal_dispatcher = None

    def get_info(self):
        day_capsule = self.option_matrix.get_day_capsule(self.option_matrix.current_date)
        aggregate_stats = day_capsule.cross_analyser.get_aggregate_stats(self.option_matrix.last_time_stamp)

        call_oi_series = day_capsule.cross_analyser.get_total_call_oi_series()
        put_oi_series = day_capsule.cross_analyser.get_total_put_oi_series()
        call_volume_series = day_capsule.cross_analyser.get_total_call_volume_series()
        put_volume_series = day_capsule.cross_analyser.get_total_put_volume_series()
        cross_stats = day_capsule.cross_analyser.get_cross_instrument_stats(self.option_matrix.last_time_stamp)

        put_vwap = {inst: inst_data['vwap_delta'] for inst, inst_data in cross_stats.items() if inst[-2::] == 'PE'}
        call_vwap = {inst: inst_data['vwap_delta'] for inst, inst_data in cross_stats.items() if inst[-2::] == 'CE'}

        put_price_delta = {inst: inst_data['price_delta'] for inst, inst_data in cross_stats.items() if
                           inst[-2::] == 'PE'}
        call_price_delta = {inst: inst_data['price_delta'] for inst, inst_data in cross_stats.items() if
                            inst[-2::] == 'CE'}

        put_pos_change_list = [x for x in list(put_price_delta.values()) if x > 0]
        call_pos_change_list = [x for x in list(call_price_delta.values()) if x > 0]

        put_pos_price_pct = float(len(put_pos_change_list) / len(list(put_price_delta.values())))
        call_pos_price_pct = float(len(call_pos_change_list) / len(list(call_price_delta.values())))
        day_spot_capsule = self.option_matrix.get_spot_instrument_capsule(self.option_matrix.current_date, 'spot')
        print(day_spot_capsule.last_tick.ion.to_candle())
        info =  {'timestamp': self.option_matrix.last_time_stamp,
                'asset': self.option_matrix.asset,
                'call_volume_scale':aggregate_stats['call_volume_scale'],
                'put_volume_scale': aggregate_stats['put_volume_scale'],
                'sum_call_volume': aggregate_stats['sum_call_volume'],
                'sum_put_volume': aggregate_stats['sum_put_volume'],
                'call_volume_scale_day': aggregate_stats['call_volume_scale_day'],
                'put_volume_scale_day': aggregate_stats['put_volume_scale_day'],
                'median_call_volume': aggregate_stats['median_call_volume'],
                'median_put_volume': aggregate_stats['median_put_volume'],
                'pcr_minus_1': aggregate_stats['pcr_minus_1'],
                'call_volume_scale_day_2': aggregate_stats['call_volume_scale_day_2'],
                'put_volume_scale_day_2': aggregate_stats['put_volume_scale_day_2'],
                'regime': aggregate_stats['regime'],
                'market_entrant': aggregate_stats['market_entrant'],
                'call_entrant': aggregate_stats['call_entrant'],
                'put_entrant': aggregate_stats['put_entrant'],
                'transition': aggregate_stats['transition'],
                'roll_near_vol_pcr': aggregate_stats['roll_near_vol_pcr'],
                'roll_far_vol_pcr': aggregate_stats['roll_far_vol_pcr'],
                'roll_vol_spread_pcr': aggregate_stats['roll_vol_spread_pcr'],
                'put_pos_price_pct': put_pos_price_pct,
                'call_pos_price_pct': call_pos_price_pct,
                'call_vol_spread': aggregate_stats['call_vol_spread'],
                'put_vol_spread': aggregate_stats['put_vol_spread'],
                'total_vol_spread': aggregate_stats['total_vol_spread'],
                'total_profit': aggregate_stats['ledger']['total_profit'],
                'call_profit': aggregate_stats['ledger']['call_profit'],
                'put_profit': aggregate_stats['ledger']['put_profit'],
                'day_total_profit': aggregate_stats['ledger']['day_total_profit'],
                'day_call_profit': aggregate_stats['ledger']['day_call_profit'],
                'day_put_profit': aggregate_stats['ledger']['day_put_profit'],
                'near_put_oi_share': aggregate_stats['near_put_oi_share'],
                'far_put_oi_share': aggregate_stats['far_put_oi_share'],
                'near_call_oi_share': aggregate_stats['near_call_oi_share'],
                'far_call_oi_share': aggregate_stats['far_call_oi_share'],

                'put_oi_spread': aggregate_stats['put_oi_spread'],
                'call_oi_spread': aggregate_stats['call_oi_spread'],
                'price_list': [day_spot_capsule.last_tick.ion.to_candle()['close']],
                'near_call_volume_share_per_oi': aggregate_stats['near_call_volume_share_per_oi'],
                'near_put_volume_share_per_oi': aggregate_stats['near_put_volume_share_per_oi'],
                'far_call_volume_share_per_oi': aggregate_stats['far_call_volume_share_per_oi'],
                'far_put_volume_share_per_oi': aggregate_stats['far_put_volume_share_per_oi'],

        }

        return info


    def generate(self):
        #self.print_instant_info()
        self.print_stats()
        self.run_external_generators()
        #self.generate_intra_day_call_oi_drop_signal()
        #self.run_dynamic_analysis()
        pass

    def print_instant_info(self):
        day_capsule = self.option_matrix.get_day_capsule(self.option_matrix.current_date)
        if self.option_matrix.last_time_stamp == 1703843700:
            for key, cell in day_capsule.transposed_data[1703843700].items():
                info = cell.ion.oi if cell.ion.category == 'option' else cell.ion.close
                print(key, " ", cell.instrument, " ", cell.timestamp, " ", info)


    def print_stats(self):
        day_capsule = self.option_matrix.get_day_capsule(self.option_matrix.current_date)
        call_oi_series = day_capsule.cross_analyser.get_total_call_oi_series()

        if self.live_mode and self.option_matrix.last_time_stamp and call_oi_series:
            aggregate_stats = day_capsule.cross_analyser.get_aggregate_stats(self.option_matrix.last_time_stamp)
            aggregate_stat_table = self.get_aggregate_stats_table(aggregate_stats)
            print(tabulate(aggregate_stat_table, headers='firstrow', tablefmt='fancy_grid'))
            cross_stats = day_capsule.cross_analyser.get_cross_instrument_stats(self.option_matrix.last_time_stamp)
            call_cross_stats = {key: val for key, val in cross_stats.items() if key[-2::] == 'CE'}
            put_cross_stats = {key: val for key, val in cross_stats.items() if key[-2::] == 'PE'}
            """
            if aggregate_stats['call_volume_scale'] > 2 and aggregate_stats['put_volume_scale'] > 2:
                self.play_both_sound()
            else:
                if aggregate_stats['put_volume_scale'] > 2:
                    self.play_put_sound()

                elif aggregate_stats['call_volume_scale'] > 2:
                    self.play_call_sound()
            """
            #print('spot===', day_capsule.cross_analyser.get_instrument_ion_field_series()[-1])
            if self.option_matrix.print_cross_stats:
                print('Call stats==')
                call_cross_stats_table = self.get_cross_stats_table(call_cross_stats)
                print(tabulate(call_cross_stats_table, headers='firstrow', tablefmt='fancy_grid'))

                print('put stats==')
                put_cross_stats_table = self.get_cross_stats_table(put_cross_stats)
                print(tabulate(put_cross_stats_table, headers='firstrow', tablefmt='fancy_grid'))

    def play_call_sound(self):
        #beep(sound='coin')
        #os.system('afplay /System/Library/Sounds/Sosumi.aiff')
        #os.system('say "Call time."')
        #call(["afplay", "/System/Library/Sounds/Sosumi.aiff'"])
        print('\007')
        time.sleep(0.5)
    def play_put_sound(self):
        #beep(sound='robot_error')
        #os.system('afplay /System/Library/Sounds/Glass.aiff')
        #os.system('say "No Call time."')
        #call(["aplay", "/System/Library/Sounds/Glass.aiff'"])
        print('\007')
        time.sleep(0.5)
    def play_both_sound(self):
        #beep(sound='success')
        #os.system('afplay /System/Library/Sounds/Hero.aiff')
        #os.system('say "Draw time."')
        #call(["aplay", "/System/Library/Sounds/Hero.aiff'"])
        print('\007')
        time.sleep(0.5)

    def get_cross_stats_table(self, cross_stats):
        cross_stats_table = []
        inst_keys = [key[:-3] for key in list(cross_stats.keys())]
        cross_stats_table.append([""] + inst_keys)
        first_item = list(cross_stats.values())[0]
        for key in first_item.keys():
            lst = [key]
            for inst_data in cross_stats.values():
                lst.append(inst_data[key])
            cross_stats_table.append(lst)
        return cross_stats_table

    def get_aggregate_stats_table(self, aggregate_stats):
        table = [
            ['', 'Call', 'Put', 'Total'],
            ['Max', aggregate_stats['max_call_oi'], aggregate_stats['max_put_oi'], aggregate_stats['max_total_oi']],
            ['POI', aggregate_stats['poi_call_oi'], aggregate_stats['poi_put_oi'], aggregate_stats['poi_total_oi']],
            ['Drop% (Max)', aggregate_stats['call_drop'], aggregate_stats['put_drop'], aggregate_stats['total_drop']],
            ['Buildup% (Day)', aggregate_stats['call_build_up'], aggregate_stats['put_build_up'], aggregate_stats['total_build_up']],
            ['Addition(T-1)', aggregate_stats['call_addition'], aggregate_stats['put_addition'], aggregate_stats['total_addition']],
            ['pcr_minus_1', '', '', aggregate_stats['pcr_minus_1']],
            ['regime', '', '', aggregate_stats['regime']],
            ['Volume Scale', aggregate_stats['call_volume_scale'], aggregate_stats['put_volume_scale'], aggregate_stats['total_volume_scale']],
            ['Vol Spread', aggregate_stats['call_vol_spread'], aggregate_stats['put_vol_spread'], aggregate_stats['total_vol_spread']],
            ['Vol Share/unit (near)', aggregate_stats['near_call_volume_share_per_oi'], aggregate_stats['near_put_volume_share_per_oi'], ''],
            ['Vol Share/unit (far)', aggregate_stats['far_call_volume_share_per_oi'], aggregate_stats['far_put_volume_share_per_oi'], ''],
            ['OI Share (near)', aggregate_stats['near_call_oi_share'], aggregate_stats['near_put_oi_share'], ''],
            ['OI Share (far)', aggregate_stats['far_call_oi_share'], aggregate_stats['far_put_oi_share'], ''],
            ['near strike vol rat', '', '', aggregate_stats['roll_near_vol_pcr']],
            ['far strike vol rat', '', '', aggregate_stats['roll_far_vol_pcr']],
            ['vol spread rat', '', '', aggregate_stats['roll_vol_spread_pcr']],
            ['Profitability', aggregate_stats['ledger']['call_profit'], aggregate_stats['ledger']['put_profit'], aggregate_stats['ledger']['total_profit']],
            ['Profitability (Day)', aggregate_stats['ledger']['day_call_profit'], aggregate_stats['ledger']['day_put_profit'], aggregate_stats['ledger']['day_total_profit']],
        ]
        return table


    def run_external_generators(self):
        if self.option_matrix.last_time_stamp is not None:
            #print('run_external_generators, ', TradeDateTime(self.option_matrix.last_time_stamp).date_time_string)
            pass
        day_capsule = self.option_matrix.get_day_capsule(self.option_matrix.current_date)
        call_oi_series = day_capsule.cross_analyser.get_total_call_oi_series()
        put_oi_series = day_capsule.cross_analyser.get_total_put_oi_series()
        call_volume_series = day_capsule.cross_analyser.get_total_call_volume_series()
        put_volume_series = day_capsule.cross_analyser.get_total_put_volume_series()
        aggregate_stats = day_capsule.cross_analyser.get_aggregate_stats(self.option_matrix.last_time_stamp)
        cross_stats = day_capsule.cross_analyser.get_cross_instrument_stats(self.option_matrix.last_time_stamp)

        put_vwap = {inst: inst_data['vwap_delta'] for inst, inst_data in cross_stats.items() if inst[-2::] == 'PE'}
        call_vwap = {inst: inst_data['vwap_delta'] for inst, inst_data in cross_stats.items() if inst[-2::] == 'CE'}
        put_price_delta = {inst: inst_data['price_delta'] for inst, inst_data in cross_stats.items() if inst[-2::] == 'PE'}
        call_price_delta = {inst: inst_data['price_delta'] for inst, inst_data in cross_stats.items() if inst[-2::] == 'CE'}

        #self.bullish_option_momentum_indicator.evaluate(aggregate_stats['call_volume_scale'], call_price_delta, put_price_delta)
        self.bearish_option_momentum_indicator.evaluate(aggregate_stats['put_volume_scale'], put_price_delta, call_price_delta)
        #self.put_buy_indicator.evaluate(aggregate_stats['put_volume_scale'], aggregate_stats['call_volume_scale'], put_price_delta, call_price_delta)
        info = self.get_info()
        signal = Signal(asset=info['asset'], category='OPTION_MARKET', instrument="OPTION",
                        indicator="PCR_MINUS_1", strength=info['pcr_minus_1'], signal_time=info['timestamp'],
                        notice_time=info['timestamp'], info=info)
        self.dispatch_signal(signal)

    def run_external_generators_old(self):
        if self.option_matrix.last_time_stamp is not None:
            print(TradeDateTime(self.option_matrix.last_time_stamp).date_time_string)
        day_capsule = self.option_matrix.get_day_capsule(self.option_matrix.current_date)
        call_oi_series = day_capsule.cross_analyser.get_total_call_oi_series()
        put_oi_series = day_capsule.cross_analyser.get_total_put_oi_series()
        call_volume_series = day_capsule.cross_analyser.get_total_call_volume_series()
        put_volume_series = day_capsule.cross_analyser.get_total_put_volume_series()

        spot_series = day_capsule.cross_analyser.get_instrument_ion_field_series()
        vol_series = day_capsule.cross_analyser.get_instrument_ion_field_series('22200_CE')
        #print(vol_series)
        """"""
        self.call_down_cross_over.evaluate(call_oi_series, put_oi_series)
        self.put_down_cross_over.evaluate(put_oi_series, call_oi_series)
        self.build_up_calculator.evaluate(spot_series, call_oi_series, put_oi_series)
        self.option_volume_indicator.evaluate(call_volume_series, put_volume_series)

    def dispatch_signal(self, signal):
        #print(signal.name, TradeDateTime(self.option_matrix.last_time_stamp).date_time_string)
        if signal.indicator != 'PCR_MINUS_1':
            print('------------------------------------', signal.indicator)
        if self.signal_dispatcher:
            self.signal_dispatcher(signal)

    def generate_intra_day_call_oi_drop_signal(self):
        day_capsule = self.option_matrix.get_day_capsule(self.option_matrix.current_date)
        call_oi_series = day_capsule.cross_analyser.get_total_call_oi_series()
        put_oi_series = day_capsule.cross_analyser.get_total_put_oi_series()
        total_oi = [x + y for x, y in zip(call_oi_series, put_oi_series)]
        last_oi = call_oi_series[-1] if call_oi_series else 1
        if last_oi > self.max_oi:
            self.max_oi = last_oi
        if last_oi > self.attention_oi:
            self.attention_oi = last_oi
        signal = 0
        if len(call_oi_series) >= self.roll_period / self.option_matrix.option_data_throttler.aggregation_factor:
            #print(call_oi_series)
            mean_oi = np.mean(call_oi_series[-int(self.roll_period / self.option_matrix.option_data_throttler.aggregation_factor):-1])
            if (last_oi * 1.00 / mean_oi) - 1 > 0.01:
                # print('Buildup++++++')
                pass
            elif (last_oi * 1.00 / self.attention_oi) - 1 < -0.05:
                print('covering----', last_oi)
                print(self.option_matrix.option_data_throttler.last_frame_start)
                if last_oi == 0:
                    for ts, cross in day_capsule.transposed_data.items():
                        for inst, cell in cross.items():
                            if inst != 'spot':
                                print(ts," ", inst," ", cell.ion.oi)

                # print((last_oi * 1.00 / self.attention_oi) - 1)
                self.attention_oi = last_oi
                #self.attention_oi = max(last_oi,1) #Hack for divisible by 0
                signal = 1

            else:
                # print('balance====')
                pass

        return signal
