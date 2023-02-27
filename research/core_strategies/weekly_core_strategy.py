from datetime import datetime
from helper.utils import get_broker_order_type
from research.strategies.signal_setup import get_target_fn
from research.queues.neuron_network import QNetwork
from research.queues.trade import Trade
import functools
known_spot_instruments = ['SPOT']
market_view_dict = {'SPOT_BUY': 'LONG',
                    'SPOT_SELL': 'SHORT',
                    'CE_BUY': 'LONG',
                    'CE_SELL': 'SHORT',
                    'PE_BUY': 'SHORT',
                    'PE_SELL': 'LONG'}

class BaseStrategy:
    def __init__(self,
                 insight_book=None,
                 id=None,
                 order_type="BUY",  # order type of the instrument, can take only one value
                 spot_instruments = [], # Instruments that should be traded as linear can include FUT in future
                 derivative_instruments=[], # Instruments that should be traded as non options
                 exit_time=[10],
                 carry_forward = False,
                 min_tpo=1,
                 max_tpo=13,
                 record_metric=True,
                 triggers_per_signal=1,
                 max_signal=1,
                 weekdays_allowed=[],
                 entry_signal_queues = [], #Used for signals to be evaluated to enter a trade
                 exit_criteria_list = [], #Used for signals to be evaluated to exit a trade
                 signal_filters=[], #Signals that should be filtered out before sending to queue
                 spot_long_targets = [], #[0.002,0.003, 0.004, 0.005],
                 spot_long_stop_losses=[], #[-0.001, -0.002, -0.002, -0.002],
                 spot_short_targets=[], #[-0.002, -0.003, -0.004, -0.005],
                 spot_short_stop_losses=[], #[0.001, 0.002, 0.002, 0.002],
                 instr_targets = [], #[0.002,0.003, 0.004, 0.005],
                 instr_stop_losses = [], #[-0.001,-0.002, -0.002,-0.002]
                 instr_to_trade=[],
                 trade_controllers=[],
                 entry_switch={},
                 risk_limits=[],
                 trade_cut_off_time=60
    ):
        self.id = self.__class__.__name__ + "_" + order_type + "_" + str(min(exit_time)) if id is None else id
        self.insight_book = insight_book
        self.order_type = order_type
        self.spot_instruments = spot_instruments if spot_instruments else []
        self.derivative_instruments = derivative_instruments if derivative_instruments else []
        self.exit_time = exit_time
        self.min_tpo = min_tpo
        self.max_tpo = max_tpo
        self.record_metric = record_metric
        self.triggers_per_signal = min(4, triggers_per_signal) #Dont go past 4
        self.max_signal = max_signal
        #self.entry_criteria = entry_criteria
        self.signal_filters = signal_filters
        self.exit_criteria_list = exit_criteria_list
        self.spot_long_targets = [abs(x) if isinstance(x, (int, float)) else x for x in spot_long_targets]
        self.spot_long_stop_losses = [-1 * abs(x) if isinstance(x, (int, float)) else x for x in spot_long_stop_losses]
        self.spot_short_targets = [-1 * abs(x) if isinstance(x, (int, float)) else x for x in spot_short_targets]
        self.spot_short_stop_losses = [abs(x) if isinstance(x, (int, float)) else x for x in spot_short_stop_losses]
        side = get_broker_order_type(self.order_type)
        self.instr_targets = [side * abs(x) for x in instr_targets]
        self.instr_stop_losses = [-1 * side * abs(x) for x in instr_stop_losses]
        self.instr_to_trade = instr_to_trade
        self.weekdays_allowed = weekdays_allowed
        self.activated = True
        self.is_aggregator = False
        self.params_repo = {}
        self.signal_params = {} #self.strategy_params = {}
        self.last_match = None
        self.pending_signals = {}
        self.tradable_signals ={}
        self.minimum_quantity = 1
        self.trade_controllers = trade_controllers
        self.risk_limits = risk_limits
        self.trade_cut_off_time = trade_cut_off_time
        self.carry_forward = carry_forward
        self.cover = 200 if self.derivative_instruments and self.order_type == 'SELL' else 0
        if (len(spot_long_targets) < self.triggers_per_signal) and (len(spot_short_targets) < self.triggers_per_signal) and (len(instr_targets) < self.triggers_per_signal):
            raise Exception("Triggers and targets of unequal size")
        #print('Add entry queue')
        self.entry_signal_pipeline = QNetwork(self, entry_signal_queues, entry_switch)
        #print('Add exit queue')
        self.exit_signal_pipeline = QNetwork(self, exit_criteria_list)

        #print('self.entry_signal_queues+++++++++++', self.entry_signal_pipeline)
        #print('self.exit_signal_queues+++++++++++', self.exit_signal_pipeline)
        """
        self.spot_targets = [('DT_HEIGHT_TARGET', {'ref_point':-2, 'factor':-1}),  ('LAST_N_CANDLE_BODY_TARGET_UP', {'period':5, 'n':3}), ('LAST_N_CANDLE_HIGH', {'period':5, 'n':3}), ('PREV_SPH', {})]
        self.spot_stop_loss = [('DT_HEIGHT_TARGET', {'ref_point':-2, 'factor':-1}),  ('LAST_N_CANDLE_BODY_TARGET_UP', {'period':5, 'n':3}), ('LAST_N_CANDLE_HIGH', {'period':5, 'n':3}), ('PREV_SPH', {})]
        self.instr_targets = [0.1, 0.2, 0.3, 0.4]
        self.instr_stop_loss = [-0.1, -0.2, -0.3, -0.4]
        """
        #self.prepare_targets()


    def get_market_view(self, instr):
        print('get_market_view', instr)
        view_dict = {'SPOT_BUY': 'LONG', 'SPOT_SELL': 'SHORT', 'CE_BUY': 'LONG', 'CE_SELL': 'SHORT', 'PE_BUY': 'SHORT', 'PE_SELL': 'LONG'}
        if not self.inst_is_option(instr):
            d_key = instr + "_" + self.order_type
        else:
            d_key = instr[-2::] + "_" + self.order_type
        return view_dict[d_key]

    def set_up(self):
        week_day_criterion = (not self.weekdays_allowed) or datetime.strptime(self.insight_book.trade_day, '%Y-%m-%d').strftime('%A') in self.weekdays_allowed
        activation_criterion = week_day_criterion
        if not activation_criterion:
            self.deactivate()

    def initiate_signal_trades(self):
        print('initiate_signal_trades+++++++++++++++++')
        print(self.spot_instruments)
        print(self.derivative_instruments)
        all_inst = self.spot_instruments + self.derivative_instruments
        for trade_inst in all_inst:
            print(trade_inst)
            trd_key = self.add_tradable_signal(trade_inst)
            curr_trade = self.tradable_signals[trd_key]
            curr_trade.trigger_entry()
            # legs = curr_trade.get_trade_legs()
            # Filter out triggers which doesn't contain data as a result of not enough time
            # triggers = [leg for leg in legs if leg]
            # At first signal we will add 2 positions with target 1 and target 2 with sl mentioned above
            # self.trigger_entry(trade_inst, self.order_type, trd_key, legs)
        self.entry_signal_pipeline.flush_queues()
        self.process_post_entry()

    def add_tradable_signal(self, trade_inst):
        existing_signals = len(self.tradable_signals.keys())
        sig_key = 'SIG_' + str(existing_signals + 1)
        self.tradable_signals[sig_key] = Trade(self, sig_key, trade_inst)
        return sig_key


    """Deactivate when not required to run in a particular day"""
    def deactivate(self):
        self.activated = False
        #self.insight_book.remove_strategy(self)
        print('############################################# Deactivated')

    """ Every strategy should run in valid tpo"""
    def valid_tpo(self):
        current_tpo = self.insight_book.curr_tpo
        min_tpo_met = self.min_tpo is None or current_tpo >= self.min_tpo
        max_tpo_met = self.max_tpo is None or current_tpo <= self.max_tpo
        return min_tpo_met and max_tpo_met

    def trade_limit_reached(self):
        return len(self.tradable_signals) >= self.max_signal

    def inst_is_option(self, inst):
        return inst not in known_spot_instruments

    def get_last_tick(self, instr='SPOT'):
        if self.inst_is_option(instr):
            last_candle = self.insight_book.option_processor.get_last_tick(instr)
        else:
            last_candle = self.insight_book.spot_processor.last_tick
        return last_candle

    def trigger_entry(self, trade_inst, order_type, sig_key, triggers):
        for trigger in triggers:
            if self.record_metric:
                mkt_parms = self.insight_book.activity_log.get_market_params()
                if self.signal_params:
                    mkt_parms = {**mkt_parms, **self.signal_params}
                self.params_repo[(sig_key, trigger['seq'])] = mkt_parms  # We are interested in signal features, trade features being stored separately
        self.signal_params = {}
        updated_symbol = self.insight_book.ticker + "_" + trade_inst if self.inst_is_option(trade_inst) else self.insight_book.ticker
        cover = triggers[0].get('cover', 0)
        signal_info = {'symbol': updated_symbol, 'cover': cover, 'strategy_id': self.id, 'signal_id': sig_key, 'order_type': order_type, 'legs': [{'seq': trigger['seq'], 'qty': trigger['quantity']} for trigger in triggers]}
        print('placing entry order at================', datetime.fromtimestamp(self.insight_book.spot_processor.last_tick['timestamp']))
        self.insight_book.pm.strategy_entry_signal(signal_info, option_signal=self.inst_is_option(trade_inst))

    def trigger_exit(self, signal_info):
        signal_info['strategy_id'] = self.id
        instrument = signal_info['symbol']
        updated_symbol = self.insight_book.ticker + "_" + instrument if self.inst_is_option(instrument) else self.insight_book.ticker
        signal_info['symbol'] = updated_symbol
        self.insight_book.pm.strategy_exit_signal(signal_info, option_signal=self.inst_is_option(instrument))

    def manage_risk(self):
        spot_movements = []
        for trade in self.tradable_signals.values():
            for leg in trade.legs.values():
                if leg['spot_exit_price'] is not None:
                    factor = -1 if leg['market_view'] == 'SHORT' else 1
                    spot_movements.append(factor * (leg['spot_exit_price'] - leg['spot_entry_price']))
        max_movement = max(spot_movements)
        total_losses = sum([x for x in spot_movements if x < 0])
        risk_limit_crossed = False
        for risk_limit in self.risk_limits:
            risk_limit_crossed = risk_limit_crossed or eval(risk_limit)
            if risk_limit_crossed:
                print("^^^^^^^^^^^Risk limit crossed", " max movement=====", max_movement, "total_losses", total_losses)
                for trade in self.tradable_signals.values():
                    trade.force_close()
                self.deactivate()
                break


    def register_instrument(self, signal):
        pass

    def process_post_entry(self):
        pass

    def while_active(function):
        @functools.wraps(function)
        def wrapper(self, *args, **kwargs):
            if self.activated:
                func = function(self, *args, **kwargs)
                return func
            else:
                return None
        return wrapper


    @while_active
    def register_signal(self, signal):
        self.entry_signal_pipeline.register_signal(signal)
        self.exit_signal_pipeline.register_signal(signal)
        for trade in self.tradable_signals.values():
            trade.register_signal(signal)

    def evaluate_entry_signals(self):
        return self.entry_signal_pipeline.evaluate_entry_signals()

    def look_for_trade(self):
        enough_time = self.insight_book.get_time_to_close() > self.trade_cut_off_time
        suitable_tpo = self.valid_tpo()
        signal_present = self.entry_signal_pipeline.all_entry_signal()
        trade_limit_not_reached = not self.trade_limit_reached()
        if trade_limit_not_reached and enough_time and suitable_tpo and signal_present: #and filter_criteria_met:
            signal_passed = self.evaluate_entry_signals() and self.custom_evaluation()
            if signal_passed:
                self.record_params()
                self.initiate_signal_trades()

    def custom_evaluation(self):
        return True

    def process_custom_signal(self):
        pass

    def evaluate_exit_signals(self):
        return self.exit_signal_pipeline.evaluate_exit_signals()

    def check_neuron_validity(self):
        self.entry_signal_pipeline.check_validity()
        self.exit_signal_pipeline.check_validity()

    @while_active
    def on_minute_data_pre(self):
        self.on_tick_data()
        self.check_neuron_validity()

    @while_active
    def on_minute_data_post(self):
        self.look_for_trade()

    @while_active
    def on_tick_data(self):
        self.monitor_existing_positions()

    def monitor_existing_positions(self):
        self.close_on_exit_signal()
        self.close_on_instr_tg_sl_tm()
        self.close_on_spot_tg_sl()

    def close_on_exit_signal(self):
        exit_criteria_met = self.evaluate_exit_signals()
        if exit_criteria_met:
            for trade_id, trade in self.tradable_signals.items():
                trade.close_on_exit_signal()

    def close_on_instr_tg_sl_tm(self):
        for trade_id, trade in self.tradable_signals.items():
            trade.close_on_instr_tg_sl_tm()

    def close_on_spot_tg_sl(self):
        for trade_id, trade in self.tradable_signals.items():
            trade.close_on_spot_tg_sl()

    def pre_signal_filter(self, signal={}):
        satisfied = not self.signal_filters
        if not satisfied:
            market_params = self.insight_book.activity_log.get_market_params()
            #print(market_params)
            d2_ad_resistance_pressure = market_params.get('d2_ad_resistance_pressure',0)

            five_min_trend = market_params.get('five_min_trend', 0)
            exp_b = market_params.get('exp_b', 0)
            d2_cd_new_business_pressure = market_params.get('d2_cd_new_business_pressure',0)
            category = (signal['category'] , signal['indicator'])
            week_day = datetime.strptime(self.insight_book.trade_day, '%Y-%m-%d').strftime('%A')
            open_type = market_params['open_type']
            tpo = market_params['tpo']
            strength = signal.get('strength', 0)
            kind = signal['info'].get('kind', "")
            money_ness = signal['info'].get('money_ness', "")
            week_open_type = self.insight_book.weekly_processor.get_market_params()['week_open_type']
            #print('inside +++++', open_type, tpo, strength, kind, money_ness)
            for condition in self.signal_filters:
                #print(condition['logical_test'])
                satisfied = satisfied or eval(condition['logical_test'])
            #print(satisfied)
        return satisfied


    def record_params(self):
        #print('inside record_params', matched_pattern)
        #print(self.insight_book.activity_log.locate_price_region())
        if self.record_metric:
            price_region = self.insight_book.activity_log.locate_price_region()
            for key, val in price_region.items():
                self.signal_params['pat_' + key] = val
            for pattern_queue_item in self.entry_signal_pipeline.neuron_dict.values():
                pattern_queue = pattern_queue_item['neuron']
                pattern_attr = pattern_queue.get_attributes()
                self.signal_params = {**self.signal_params, **pattern_attr}
