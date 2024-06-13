from datetime import datetime
from helper.utils import get_broker_order_type
from strat_machine.queues.neuron_network import QNetwork
from strat_machine.queues.trade import Trade
from entities.trading_day import TradeDateTime
import functools
from helper.utils import get_option_strike

from servers.server_settings import cache_dir
from diskcache import Cache
from helper.utils import inst_is_option, get_market_view
from strat_machine.trade_master.trade_manager import TradeManager
from strat_machine.trade_master.trade_set import TradeSet

known_spot_instruments = ['SPOT']
market_view_dict = {'SPOT_BUY': 'LONG',
                    'SPOT_SELL': 'SHORT',
                    'CE_BUY': 'LONG',
                    'CE_SELL': 'SHORT',
                    'PE_BUY': 'SHORT',
                    'PE_SELL': 'LONG'}

class BaseStrategy:
    def __init__(self,
                 market_book=None,
                 id=None,
                 min_tpo=1,
                 max_tpo=13,
                 record_metric=True,
                 triggers_per_signal=1,
                 max_signal=1,
                 weekdays_allowed=[],
                 entry_signal_queues = [],  #Used for signals to be evaluated to enter a trade
                 exit_criteria_list = [],  #Used for signals to be evaluated to exit a trade
                 signal_filters=[],  #Signals that should be filtered out before sending to queue
                 register_signal_category=None,
                 trade_controllers=[],
                 entry_switch={},
                 risk_limits=[],
                 trade_cut_off_time=60,
                 trade_manager_info = {}
                 ):
        #print('core strategy 3333333333333333333333333')
        #print('entry_signal_queues====',entry_signal_queues)
        self.id = self.__class__.__name__ if id is None else id
        self.min_tpo = min_tpo
        self.max_tpo = max_tpo
        self.record_metric = record_metric
        self.triggers_per_signal = min(4, triggers_per_signal) #Dont go past 4
        self.max_signal = max_signal
        #self.entry_criteria = entry_criteria
        self.signal_filters = signal_filters
        self.exit_criteria_list = exit_criteria_list
        self.register_signal_category = register_signal_category
        self.weekdays_allowed = weekdays_allowed
        self.activated = True
        self.is_aggregator = False
        self.params_repo = {}
        self.signal_params = {} #self.strategy_params = {}
        self.last_match = None
        self.pending_signals = {}
        self.minimum_quantity = 1
        self.trade_controllers = trade_controllers
        self.risk_limits = risk_limits
        self.trade_cut_off_time = trade_cut_off_time
        self.trade_manager_info = trade_manager_info
        if (len(trade_manager_info['spot_high_targets']) < self.triggers_per_signal) and (len(trade_manager_info['spot_low_targets']) < self.triggers_per_signal) and (len(trade_manager_info['trade_targets']) < self.triggers_per_signal) and len(trade_manager_info['leg_group_exits']['targets']) < self.triggers_per_signal:
            raise Exception("Triggers and targets of unequal size")
        #print('Add entry queue')
        self.entry_signal_pipeline = QNetwork(self, entry_signal_queues, entry_switch)
        #print('Add exit queue', exit_criteria_list)
        self.exit_signal_pipeline = QNetwork(self, exit_criteria_list)
        self.asset_book = market_book.get_asset_book(self.trade_manager_info['asset']) if market_book is not None else None
        self.restore_variables = {}
        self.trade_manager = TradeManager.from_config(market_book, self, **trade_manager_info)
        self.asset = self.asset_book.asset
        self.execute_trades = False
        #print('self.entry_signal_queues+++++++++++', self.entry_signal_pipeline)
        #print('self.exit_signal_queues+++++++++++', self.exit_signal_pipeline)
        """
        self.spot_targets = [('DT_HEIGHT_TARGET', {'ref_point':-2, 'factor':-1}),  ('LAST_N_CANDLE_BODY_TARGET_UP', {'period':5, 'n':3}), ('LAST_N_CANDLE_HIGH', {'period':5, 'n':3}), ('PREV_SPH', {})]
        self.spot_stop_loss = [('DT_HEIGHT_TARGET', {'ref_point':-2, 'factor':-1}),  ('LAST_N_CANDLE_BODY_TARGET_UP', {'period':5, 'n':3}), ('LAST_N_CANDLE_HIGH', {'period':5, 'n':3}), ('PREV_SPH', {})]
        self.instr_targets = [0.1, 0.2, 0.3, 0.4]
        self.instr_stop_loss = [-0.1, -0.2, -0.3, -0.4]
        """
        #self.prepare_targets()
        self.strategy_cache = Cache(cache_dir + 'strategy_cache')



    def set_up(self):
        week_day_criterion = (not self.weekdays_allowed) or TradeDateTime(self.asset_book.market_book.trade_day).weekday_name in self.weekdays_allowed
        activation_criterion = week_day_criterion
        if not activation_criterion:
            self.deactivate()
        carry_trades = self.strategy_cache.get(self.id, {})
        print('carry_trades===', carry_trades)

        params_repo = self.strategy_cache.get('params_repo_' + self.id, {})
        for sig_key, trade_set_info in carry_trades.items():
            #print(list(trade_set_info[0]['leg_groups'][0]['legs'].values())[0]['trigger_time'])
            if list(trade_set_info[0]['leg_groups'][0]['legs'].values())[0]['trigger_time'] < self.get_last_tick()['timestamp']:
                self.trade_manager.tradable_signals[sig_key] = TradeSet.from_store(self.trade_manager, sig_key, trade_set_info)
                for trade in self.trade_manager.tradable_signals[sig_key].trades.values():
                    self.params_repo[(sig_key, trade.trd_idx)] = params_repo[(sig_key, trade.trd_idx)]
                    trade.set_controllers()
        #self.strategy_cache.delete(self.id)
        #self.strategy_cache.delete('params_repo_' + self.id)


    def market_close_for_day(self):
        print('stragey market_close_for_day #################################')
        carry_trade_sets = {}
        params_repo = {}
        for (sig_key, trade_set) in self.trade_manager.tradable_signals.items():
            if not trade_set.complete():
                carry_trade_sets[trade_set.id] = []
                for trade in trade_set.trades.values():
                    if not trade.complete():
                        carry_trade_sets[trade_set.id].append(trade.to_dict())
                        params_repo[(sig_key, trade.trd_idx)] = self.params_repo[(sig_key, trade.trd_idx)]
        self.strategy_cache.set(self.id, carry_trade_sets)
        self.strategy_cache.set('params_repo_' + self.id, params_repo)


    def initiate_signal_trades(self):
        print('strategy initiate_signal_trades+++++++++++++++++')
        if self.execute_trades:
            curr_trade_set_id = self.trade_manager.initiate_signal_trades()
            self.trade_manager.trigger_entry(curr_trade_set_id)
        self.entry_signal_pipeline.flush_queues()
        self.process_post_entry()


    """Deactivate when not required to run in a particular day"""
    def deactivate(self):
        print('############################################# Deactivated')
        self.activated = False
        #self.market_book.remove_strategy(self)


    """ Every strategy should run in valid tpo"""
    def valid_tpo(self):
        current_tpo = self.asset_book.market_book.curr_tpo
        min_tpo_met = self.min_tpo is None or current_tpo >= self.min_tpo
        max_tpo_met = self.max_tpo is None or current_tpo <= self.max_tpo
        return min_tpo_met and max_tpo_met

    def trade_limit_reached(self):
        return len(self.trade_manager.tradable_signals) >= self.max_signal


    def get_last_tick(self, instr='SPOT'):
        if inst_is_option(instr):
            last_candle = self.asset_book.option_matrix.get_last_tick(instr)
        else:
            last_candle = self.asset_book.spot_book.spot_processor.last_tick
        return last_candle

    def get_closest_instrument(self, instr='SPOT'):
        if inst_is_option(instr):
            instr = self.asset_book.option_matrix.get_closest_instrument(instr)
        else:
            instr = instr
        return instr

    def trigger_entry(self,  sig_key, triggers):
        for trigger in triggers:
            if self.record_metric:
                mkt_parms = self.asset_book.spot_book.spot_processor.get_market_params()
                if self.signal_params:
                    mkt_parms = {**mkt_parms, **self.signal_params}
                self.params_repo[(sig_key, trigger['trade_seq'])] = mkt_parms  # We are interested in signal features, trade features being stored separately
        self.signal_params = {}
        signal_info = {'strategy_id': self.id, 'signal_id': sig_key, 'trade_set': triggers}
        print('placing entry order at================', datetime.fromtimestamp(self.asset_book.spot_book.spot_processor.last_tick['timestamp']))
        print('at Same time Option Matrix clock================',
              datetime.fromtimestamp(self.asset_book.option_matrix.last_time_stamp))
        self.asset_book.market_book.pm.strategy_entry_signal(signal_info)


    def trigger_exit(self, sig_key, triggers):
        signal_info = {'strategy_id': self.id, 'signal_id': sig_key, 'trade_set': triggers}
        self.asset_book.market_book.pm.strategy_exit_signal(signal_info, self.trade_manager.exit_at)

    def manage_risk(self):
        spot_movements = []
        for trade_set in self.trade_manager.tradable_signals.values():
            for trade in trade_set.trades.values():
                for leg_group in trade.leg_groups.values():
                    for leg in leg_group.legs.values():
                        if leg.spot_exit_price is not None:
                            factor = -1 if leg_group.delta < 0 else 1
                            spot_movements.append(factor * (leg.spot_exit_price - leg.spot_entry_price))
        max_movement = max(spot_movements)
        total_losses = sum([x for x in spot_movements if x < 0])
        risk_limit_crossed = False
        for risk_limit in self.risk_limits:
            risk_limit_crossed = risk_limit_crossed or eval(risk_limit)
            if risk_limit_crossed:
                print("^^^^^^^^^^^Risk limit crossed", " max movement=====", max_movement, "total_losses", total_losses)
                for trade_set in self.trade_manager.tradable_signals.values():
                    trade_set.force_close()
                self.deactivate()
                break

    def register_instrument(self, signal):
        print('register_instrument++++++++++++++++++++++++++++++++++++++')
        self.trade_manager.register_signal(signal)


    def process_post_entry(self):
        self.execute_trades = False
        self.trade_manager.process_post_entry()

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
        # This is for trade controllers
        for trade_set in self.trade_manager.tradable_signals.values():
            trade_set.register_signal(signal)

    def evaluate_entry_signals(self):
        print('core strategy evaluate_entry_signals')
        return self.entry_signal_pipeline.evaluate_entry_signals()

    def look_for_trade(self):
        print('time to close========', self.asset_book.market_book.get_time_to_close())
        #print('trade_cut_off_time========', self.trade_cut_off_time)
        #print('self.valid_tpo()========', self.valid_tpo())
        #print('signal_present========', self.entry_signal_pipeline.all_entry_signal())
        #print('trade_limit_not_reached========', not self.trade_limit_reached())
        enough_time = self.asset_book.market_book.get_time_to_close() > self.trade_cut_off_time
        #print('enough_time========', enough_time)
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
        print('on_minute_data_pre+++++++++++++++++++++++++')
        self.on_tick_data()
        self.check_neuron_validity()

    @while_active
    def on_minute_data_post(self):
        print('on_minute_data_post+++++++++++++++++++++++++')
        self.look_for_trade()

    @while_active
    def on_tick_data(self):
        self.monitor_existing_positions()

    def monitor_existing_positions(self):
        exit_criteria_met = self.evaluate_exit_signals()
        print('close_on_exit_signal++++++++++++++++++++', exit_criteria_met)
        if exit_criteria_met:
            self.trade_manager.close_on_exit_signal()
        self.trade_manager.monitor_existing_positions()


    def pre_signal_filter(self, signal):
        satisfied = not self.signal_filters
        if not satisfied:
            market_params = self.asset_book.spot_book.spot_processor.get_market_params()
            #print(market_params)
            d2_ad_resistance_pressure = market_params.get('d2_ad_resistance_pressure',0)
            price_location =  market_params.get('price_location', 50)
            print('price_location+++++++++++++++++++', price_location)
            five_min_trend = market_params.get('five_min_trend', 0)
            exp_b = market_params.get('exp_b', 0)
            d2_cd_new_business_pressure = market_params.get('d2_cd_new_business_pressure',0)
            category = signal.key()
            week_day = datetime.strptime(self.asset_book.market_book.trade_day, '%Y-%m-%d').strftime('%A')
            open_type = market_params['open_type']
            tpo = market_params['tpo']
            strength = signal.strength if hasattr(signal, 'strength') else 0
            kind = signal.signal_info.get('kind', "")
            money_ness = signal.signal_info.get('money_ness', "")
            #print('inside +++++', open_type, tpo, strength, kind, money_ness)
            for condition in self.signal_filters:
                #print(condition['logical_test'])
                satisfied = satisfied or eval(condition['logical_test'])
            #print(satisfied)
        return satisfied




    def record_params(self):
        #print('inside record_params', matched_pattern)
        #print(self.market_book.activity_log.locate_price_region())
        if self.record_metric:
            price_region = self.asset_book.spot_book.spot_processor.locate_price_region()
            for key, val in price_region.items():
                self.signal_params['pat_' + key] = val
            for pattern_queue_item in self.entry_signal_pipeline.neuron_dict.values():
                pattern_queue = pattern_queue_item['neuron']
                pattern_attr = pattern_queue.get_attributes()
                self.signal_params = {**self.signal_params, **pattern_attr}
