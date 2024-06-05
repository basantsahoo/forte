from strat_machine.core_strategies.signal_setup import get_trade_manager_args
from helper.utils import inst_is_option, get_market_view
import itertools
from helper.utils import get_option_strike
import copy


class TradeManager:
    def __init__(self, market_book, strategy, **kwargs):
        args = get_trade_manager_args(**kwargs)
        self.initialize(market_book=market_book, strategy=strategy, **args)
        self.registered_signal = None

    def initialize(self,
             market_book=None,
             strategy=None,
             asset=None,
             exit_time=[10],
             exit_at=None,
             carry_forward_days=[0],
             triggers_per_signal=1,
             spot_high_targets=[],  # [0.002,0.003, 0.004, 0.005],
             spot_high_stop_losses=[],  # [-0.001, -0.002, -0.002, -0.002],
             spot_low_targets=[],  # [-0.002, -0.003, -0.004, -0.005],
             spot_low_stop_losses=[],  # [0.001, 0.002, 0.002, 0.002],
             spot_high_target_levels=[],
             spot_high_stop_loss_levels=[],
             spot_low_target_levels=[],
             spot_low_stop_loss_levels=[],
             trade_targets=[],  # [0.002,0.003, 0.004, 0.005],
             trade_stop_losses=[],  # [-0.001,-0.002, -0.002,-0.002]
             leg_group_exits={},
             trade_info = {},
            force_exit_ts=None,
            trade_controllers=[],
            risk_limits = 0
        ):
        # print('entry_signal_queues====',entry_signal_queues)
        self.strategy = strategy
        self.asset = asset
        self.exit_time = exit_time
        self.exit_at = exit_at
        self.triggers_per_signal = min(4, triggers_per_signal)  # Dont go past 4
        self.spot_high_targets = [abs(x) if isinstance(x, (int, float)) else x for x in spot_high_targets]
        self.spot_high_stop_losses = [-1 * abs(x) if isinstance(x, (int, float)) else x for x in
                                      spot_high_stop_losses]
        self.spot_low_targets = [-1 * abs(x) if isinstance(x, (int, float)) else x for x in spot_low_targets]
        self.spot_low_stop_losses = [abs(x) if isinstance(x, (int, float)) else x for x in spot_low_stop_losses]
        self.spot_high_target_levels = spot_high_target_levels
        self.spot_high_stop_loss_levels = spot_high_stop_loss_levels
        self.spot_low_target_levels = spot_low_target_levels
        self.spot_low_stop_loss_levels = spot_low_stop_loss_levels
        self.carry_forward_days = carry_forward_days
        side = 1#get_broker_order_type(self.order_type)
        self.trade_targets = [side * abs(x) for x in trade_targets]
        self.trade_stop_losses = [-1 * side * abs(x) for x in trade_stop_losses]
        self.leg_group_exits = leg_group_exits
        self.trade_info = trade_info
        self.force_exit_ts = force_exit_ts
        self.trade_controllers = trade_controllers
        self.risk_limits = risk_limits
        self.tradable_signals = {}
        self.asset_book = market_book.get_asset_book(self.asset) if market_book is not None else None
        self.restore_variables = {}

    def initiate_signal_trades(self):
        print('TradeManager initiate_signal_trades+++++++++++++++++')
        existing_signals = len(self.tradable_signals.keys())
        sig_key = 'SIG_' + str(existing_signals + 1)
        self.tradable_signals[sig_key] = TradeSet(self, sig_key)
        return sig_key

    def trigger_entry(self, sig_key):
        trade_set = self.tradable_signals[sig_key]
        for trade_idx, trade in trade_set.trades.items():
            all_orders = trade.get_entry_orders()
            print(all_orders)
            self.strategy.trigger_entry(sig_key, all_orders)


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

    def register_signal(self, signal):
        if signal.key_levels:
            for key, val in signal.key_levels.items():
                print(key, val)
                self.restore_variables[key] = getattr(self, key)
                setattr(self, key, val)
                print(getattr(self, key))
            print('spot_stop_loss_levels+++++++++', self.spot_short_stop_loss_levels)

    def process_post_entry(self):
        restore_variables_cp = self.restore_variables.copy()
        for key, val in restore_variables_cp.items():
            setattr(self, key, val)
            del self.restore_variables[key]



class TradeSet:
    def __init__(self, trade_manager, ts_id):
        self.id = ts_id
        self.trade_manager = trade_manager
        self.trade_info = copy.deepcopy(self.trade_manager.trade_info)
        self.trades = {}
        next_trigger = len(self.trades) + 1
        #Can contain None because it's inside expander
        trades = [Trade(self, trd_idx) for trd_idx in range(next_trigger, next_trigger + self.trade_manager.triggers_per_signal)]
        #print('trades===============', trades)
        for trade in trades:
            #if leg is not None:
            self.trades[trade.trd_idx] = trade


class Trade:
    def __init__(self, trade_set, trd_idx):
        self.trd_idx = trd_idx
        self.trade_set = trade_set
        self.pnl = 0
        self.exit_time = self.trade_set.trade_manager.exit_time[trd_idx]
        self.carry_forward_days = self.trade_set.trade_manager.carry_forward_days[trd_idx]
        self.target = self.trade_set.trade_manager.trade_targets[trd_idx]
        self.stop_loss = self.trade_set.trade_manager.trade_stop_losses[trd_idx]
        self.spot_high_stop_loss = self.trade_set.trade_manager.spot_high_stop_losses[trd_idx]
        self.spot_low_stop_loss = self.trade_set.trade_manager.spot_low_stop_losses[trd_idx]
        self.spot_high_target = self.trade_set.trade_manager.spot_high_targets[trd_idx]
        self.spot_low_target = self.trade_set.trade_manager.spot_low_targets[trd_idx]
        self.leg_group_exits = {}
        for key, val in self.trade_set.trade_manager.leg_group_exits.items():
            self.leg_group_exits[key] = val[trd_idx]
        self.leg_groups = {}
        leg_groups = self.trade_set.trade_info["leg_groups"]
        #print(leg_groups)
        for leg_group_info in leg_groups:
            self.leg_groups[leg_group_info['id']] = LegGroup(self, leg_group_info)

    def get_entry_orders(self):
        entry_orders = {}
        entry_orders['trade_seq'] = self.trd_idx
        entry_orders['orders'] = []
        for leg_group in self.leg_groups.values():
            #print(leg_group.get_entry_orders())
            orders = leg_group.get_entry_orders()
            for order in orders:
                order['trade_seq'] = self.trd_idx
            entry_orders['orders'].append(orders)

        return entry_orders

    def close_on_exit_signal(self):
        for leg_seq, leg_details in self.legs.items():
            if leg_details['exit_type'] is None:  # Still active
                # self.strategy.trigger_exit(self.id, leg_seq, exit_type='EC')
                self.trigger_exit(leg_seq, exit_type='EC')

    def trigger_exit(self, leg_seq, exit_type=None, manage_risk=True):
        #print('trigger_exit+++++++++++++++++++++++++++++', signal_id, trigger_id, exit_type)
        quantity = self.legs[leg_seq]['quantity']
        instrument = self.legs[leg_seq]['instrument']
        #updated_symbol = self.strategy.insight_book.ticker + "_" + instrument if self.strategy.inst_is_option(instrument) else self.strategy.insight_book.ticker
        signal_info = {'symbol': instrument, 'signal_id': self.id,
                       'leg_seq': leg_seq,
                       'qty': quantity}
        last_candle = self.strategy.get_last_tick(instrument)
        last_spot_candle = self.strategy.get_last_tick('SPOT')
        self.legs[leg_seq]['exit_type'] = exit_type
        self.legs[leg_seq]['exit_price'] = last_candle['close']
        self.legs[leg_seq]['spot_exit_price'] = last_spot_candle['close']
        self.strategy.trigger_exit(signal_info)
        self.remove_controller(leg_seq)
        if self.trade_complete() and manage_risk:
            self.strategy.manage_risk()

class LegGroup:
    def __init__(self, trade, leg_group_info):
        #print(leg_group_info["legs"])
        self.id = leg_group_info['id']
        self.trade = trade
        self.pnl = 0
        self.completed = False
        self.leg_group_info = leg_group_info
        self.target = self.trade.leg_group_exits['targets'][self.id]
        self.stop_loss = self.trade.leg_group_exits['stop_losses'][self.id]
        self.spot_high_stop_loss = self.trade.leg_group_exits['spot_high_stop_losses'][self.id]
        self.spot_low_stop_loss = self.trade.leg_group_exits['spot_low_stop_losses'][self.id]
        self.spot_high_target = self.trade.leg_group_exits['spot_high_targets'][self.id]
        self.spot_low_target = self.trade.leg_group_exits['spot_low_targets'][self.id]
        for leg_id, leg_info in self.leg_group_info["legs"].items():
            self.leg_group_info["legs"][leg_id] = self.expand_leg_info(int(leg_id), leg_info)

    def get_entry_orders(self):
        entry_orders = []
        for leg in self.leg_group_info["legs"].values():
            entry_orders.append(copy.deepcopy(leg))
        for order in entry_orders:
            order['leg_group_id'] = self.id
        entry_orders = sorted(entry_orders, key=lambda d: d['order_type'])
        return entry_orders

    """
    "0": {
          "instr_to_trade" : [["ITM", 1, "CE"]],
          "order_type":"SELL",
          "qty": 1
        },
    """
    def expand_leg_info(self, idx=1, leg_info={}):
        #print(leg_info)
        instr = leg_info['instr_to_trade']
        if instr != ['SPOT']:
            last_tick = self.trade.trade_set.trade_manager.get_last_tick('SPOT')
            ltp = last_tick['close']
            strike = get_option_strike(ltp, instr[0], instr[1], instr[2])
            instr = str(strike) + "_" + instr[2]

            market_view = self.leg_group_info['view']
            last_candle = self.trade.trade_set.trade_manager.get_last_tick(instr)
            if not last_candle:
                print('last_candle not found for', instr)
                instr = self.trade.trade_set.trade_manager.get_closest_instrument(instr)
                last_candle = self.trade.trade_set.trade_manager.get_last_tick(instr)
                print('Now instr is ', instr)

        last_spot_candle = self.trade.trade_set.trade_manager.get_last_tick('SPOT')
        leg_info['leg_id'] = idx
        leg_info['instrument'] = leg_info['instrument'] if 'instrument' in leg_info else instr
        leg_info['entry_price'] = leg_info['entry_price'] if 'entry_price' in leg_info else last_candle['close']
        leg_info['exit_price'] = leg_info['exit_price'] if 'exit_price' in leg_info else None
        leg_info['spot_entry_price'] = leg_info['spot_entry_price'] if 'spot_entry_price' in leg_info else last_spot_candle['close']
        leg_info['spot_exit_price'] = leg_info['spot_exit_price'] if 'spot_exit_price' in leg_info else None
        leg_info['trigger_time'] = leg_info['trigger_time'] if 'trigger_time' in leg_info else last_candle['timestamp']

        print('self.strategy.force_exit_ts++++++++++++++++++', self.trade.trade_set.trade_manager.force_exit_ts)
        #trade_info['max_run_time'] = trade_info['trigger_time'] + trade_info['duration'] * 60 if self.trade.trade_set.trade_manager.force_exit_ts is None else min(trade_info['trigger_time'] + trade_info['duration'] * 60, self.trade.trade_set.trade_manager.force_exit_ts + 60)
        return leg_info

    def expand_leg_info_2(self, idx=1, leg_info={}):
        instr = leg_info['instr_to_trade']
        if instr != ['SPOT']:
            last_tick = self.trade.trade_set.trade_manager.get_last_tick('SPOT')
            ltp = last_tick['close']
            strike = get_option_strike(ltp, instr[0], instr[1], instr[2])
            instr = str(strike) + "_" + instr[2]

            market_view = self.leg_group_info['view']
            last_candle = self.trade.trade_set.trade_manager.get_last_tick(instr)
            if not last_candle:
                print('last_candle not found for', instr)
                instr = self.trade.trade_set.trade_manager.get_closest_instrument(instr)
                last_candle = self.trade.trade_set.trade_manager.get_last_tick(instr)
                print('Now instr is ', instr)

        last_spot_candle = self.trade.trade_set.trade_manager.get_last_tick('SPOT')
        spot_targets = self.calculate_target('SPOT', self.trade.trade_set.trade_manager.spot_high_targets) if market_view == 'LONG' else self.calculate_target('SPOT', self.trade.trade_set.trade_manager.spot_low_targets)
        spot_stop_losses = self.calculate_target('SPOT', self.trade.trade_set.trade_manager.spot_high_stop_losses) if market_view == 'LONG' else self.calculate_target('SPOT', self.trade.trade_set.trade_manager.spot_low_stop_losses)
        print(spot_stop_losses)
        instr_targets = self.calculate_target(instr, self.trade.trade_set.trade_manager.instr_targets) if instr != 'SPOT' else spot_targets
        instr_stop_losses = self.calculate_target(instr, self.trade.trade_set.trade_manager.instr_stop_losses) if instr != 'SPOT' else spot_stop_losses
        spot_high_target_levels = self.trade.trade_set.trade_manager.spot_high_target_levels
        spot_high_stop_loss_levels = self.trade.trade_set.trade_manager.spot_high_stop_loss_levels
        print('spot_high_stop_loss_levels+++++++++', spot_high_stop_loss_levels)
        spot_low_target_levels = self.trade.trade_set.trade_manager.spot_low_target_levels
        spot_low_stop_loss_levels = self.trade.trade_set.trade_manager.spot_low_stop_loss_levels
        spot_target_levels = spot_high_target_levels if market_view == 'LONG' else spot_low_target_levels
        spot_stop_loss_levels = spot_low_stop_loss_levels if market_view == 'LONG' else spot_high_stop_loss_levels
        print('spot_stop_loss_levels+++++++++', spot_stop_loss_levels)
        if market_view == 'LONG':
            spot_targets = [min(i) for i in itertools.zip_longest(spot_targets, spot_target_levels, fillvalue=float('inf'))]
            spot_stop_losses = [max(i) for i in itertools.zip_longest(spot_stop_losses, spot_stop_loss_levels, fillvalue=float('-inf'))]
            """
            for t_idx in range(len(spot_targets)):
                spot_targets[t_idx] = min(spot_targets[t_idx], spot_target_levels[min(t_idx, len(spot_target_levels)-1)]) if spot_target_levels else spot_targets[t_idx]
            for s_idx in range(len(spot_stop_losses)):
                spot_stop_losses[s_idx] = max(spot_stop_losses[s_idx], spot_stop_loss_levels[min(s_idx, len(spot_stop_loss_levels) - 1)]) if spot_stop_loss_levels else spot_stop_losses[s_idx]
            """
        else:
            print(spot_targets, spot_target_levels)
            spot_targets = [max(i) for i in itertools.zip_longest(spot_targets, spot_target_levels, fillvalue=float('-inf'))]
            spot_stop_losses = [min(i) for i in itertools.zip_longest(spot_stop_losses, spot_stop_loss_levels, fillvalue=float('inf'))]
            print(spot_stop_losses)
            """
            for t_idx in range(len(spot_targets)):
                spot_targets[t_idx] = max(spot_targets[t_idx], spot_target_levels[min(t_idx, len(spot_target_levels)-1)]) if spot_target_levels else spot_targets[t_idx]
            for s_idx in range(len(spot_stop_losses)):
                spot_stop_losses[s_idx] = min(spot_stop_losses[s_idx], spot_stop_loss_levels[min(s_idx, len(spot_stop_loss_levels) - 1)]) if spot_stop_loss_levels else spot_stop_losses[s_idx]
            """
        trade_info = {
            'seq': idx,
            'instrument': instr,
            'cover': self.trade.trade_set.trade_manager.cover,
            'market_view': market_view,
            'spot_target': spot_targets[min(idx-1, len(spot_targets)-1)] if spot_targets else None,
            'spot_stop_loss': spot_stop_losses[min(idx-1, len(spot_stop_losses)-1)] if spot_stop_losses else None,
            'spot_stop_loss_rolling': spot_stop_losses[min(idx-1, len(spot_stop_losses)-1)] if spot_stop_losses else None,
            'instr_target': instr_targets[min(idx-1, len(instr_targets)-1)] if instr_targets else None,
            'instr_stop_loss': instr_stop_losses[min(idx-1, len(instr_stop_losses)-1)] if instr_stop_losses else None,
            'duration': min(self.trade.trade_set.trade_manager.exit_time[idx-1], self.trade.trade_set.trade_manager.asset_book.market_book.get_time_to_close()-2) if not self.trade.trade_set.trade_manager.carry_forward_days else 90000000,
            'quantity': self.trade.trade_set.trade_manager.minimum_quantity,
            'exit_type':None,
            'entry_price':last_candle['close'],
            'exit_price':None,
            'spot_entry_price': last_spot_candle['close'],
            'spot_exit_price': None,
            'trigger_time':last_candle['timestamp']
        }
        print('self.strategy.force_exit_ts++++++++++++++++++', self.trade.trade_set.trade_manager.force_exit_ts)
        trade_info['max_run_time'] = trade_info['trigger_time'] + trade_info['duration'] * 60 if self.trade.trade_set.trade_manager.force_exit_ts is None else min(trade_info['trigger_time'] + trade_info['duration'] * 60, self.trade.trade_set.trade_manager.force_exit_ts + 60)
        return trade_info

    def calculate_target(self, instr, target_level_list):

        levels = []
        last_candle = self.trade.trade_set.trade_manager.get_last_tick(instr)
        close_point = last_candle['close']

        for target_level in target_level_list:

            if isinstance(target_level, (int, float)):
                target = close_point * (1 + target_level)
                levels.append(target)
            else:
                #print('calculate_target+++++++++++++++++++++++++', target_level)
                #print(target_level[0])
                mapped_fn = target_level['mapped_fn']
                kwargs = target_level.get('kwargs', {})
                rs = 0
                if target_level['category'] == 'signal_queue':
                    #queue = self.strategy.entry_signal_pipeline.get_que_by_category(target_level['mapped_object'])#self.entry_signal_queues[target_level['mapped_object']]
                    queue = self.strategy.entry_signal_pipeline.get_neuron_by_id(target_level['mapped_object'])
                    # print('queue.'+ mapped_fn + "()")
                    rs = eval('queue.' + mapped_fn)(**kwargs)
                    print('inside target fn +++++++++', rs)
                elif target_level['category'] == 'global':
                    obj = target_level['mapped_object']
                    fn_string = 'self.' + (obj + '.' if obj else '') + mapped_fn  # + '()'
                    # print(fn_string)
                    rs = eval(fn_string)(**kwargs)
                if rs:
                    levels.append(rs)
        return levels

    def close_on_exit_signal(self):
        for leg_seq, leg_details in self.legs.items():
            if leg_details['exit_type'] is None:  #Still active
                #self.strategy.trigger_exit(self.id, leg_seq, exit_type='EC')
                self.trigger_exit(leg_seq, exit_type='EC')

    def force_close(self):
        for leg_seq, leg_details in self.legs.items():
            if leg_details['exit_type'] is None:  #Still active
                #self.strategy.trigger_exit(self.id, leg_seq, exit_type='EC')
                self.trigger_exit(leg_seq, exit_type='FC', manage_risk=False)

    def close_on_instr_tg_sl_tm(self):
        last_spot_candle = self.strategy.get_last_tick('SPOT')
        for trigger_seq, trigger_details in self.legs.items():
            if trigger_details['exit_type'] is None:  #Still active
                last_instr_candle = self.strategy.get_last_tick(trigger_details['instrument'])
                #print("self.strategy.force_exit_ts=====", self.strategy.force_exit_ts)
                if last_spot_candle['timestamp'] >= trigger_details['max_run_time']:
                    self.trigger_exit(trigger_seq, exit_type='TC')
                elif self.strategy.force_exit_ts and last_spot_candle['timestamp'] >= self.strategy.force_exit_ts:
                    self.trigger_exit(trigger_seq, exit_type='TSFE')
                elif self.strategy.order_type == 'BUY':
                    if trigger_details['instr_target'] and last_instr_candle['close'] >= trigger_details['instr_target']:
                        self.trigger_exit(trigger_seq, exit_type='IT')
                    elif trigger_details['instr_stop_loss'] and last_instr_candle['close'] < trigger_details['instr_stop_loss']:
                        self.trigger_exit(trigger_seq, exit_type='IS')
                elif self.strategy.order_type == 'SELL':
                    print('eveluating SL for sell order ++++++++++++++++++')
                    print('instr_stop_loss' , trigger_details['instr_stop_loss'])
                    print('last_instr_candle close' , last_instr_candle['close'])
                    if trigger_details['instr_target'] and last_instr_candle['close'] <= trigger_details['instr_target']:
                        self.trigger_exit(trigger_seq, exit_type='IT')
                        #print(last_candle, trigger_details['target'])
                    elif trigger_details['instr_stop_loss'] and last_instr_candle['close'] > trigger_details['instr_stop_loss']:
                        self.trigger_exit(trigger_seq, exit_type='IS')

    def close_on_spot_tg_sl(self):
        last_spot_candle = self.strategy.get_last_tick('SPOT')
        for trigger_seq, trigger_details in self.legs.items():
            if trigger_details['exit_type'] is None:  #Still active
                market_view = trigger_details['market_view']
                if market_view == 'LONG':
                    if trigger_details['spot_target'] and last_spot_candle['close'] >= trigger_details['spot_target']:
                        self.trigger_exit(trigger_seq, exit_type='ST')
                    elif trigger_details['spot_stop_loss'] and last_spot_candle['close'] < trigger_details['spot_stop_loss']:
                        self.trigger_exit( trigger_seq, exit_type='SS')
                    elif trigger_details['spot_stop_loss_rolling'] and last_spot_candle['close'] < trigger_details['spot_stop_loss_rolling']:
                        self.trigger_exit( trigger_seq, exit_type='SRS')
                elif market_view == 'SHORT':
                    if trigger_details['spot_target'] and last_spot_candle['close'] <= trigger_details['spot_target']:
                        self.trigger_exit(trigger_seq, exit_type='ST')
                        # print(last_candle, trigger_details['target'])
                    elif trigger_details['spot_stop_loss'] and last_spot_candle['close'] > trigger_details['spot_stop_loss']:
                        self.trigger_exit(trigger_seq, exit_type='SS')
                    elif trigger_details['spot_stop_loss_rolling'] and last_spot_candle['close'] > trigger_details['spot_stop_loss_rolling']:
                        self.trigger_exit(trigger_seq, exit_type='SRS')

    def trigger_exit(self, leg_seq, exit_type=None, manage_risk=True):
        #print('trigger_exit+++++++++++++++++++++++++++++', signal_id, trigger_id, exit_type)
        quantity = self.legs[leg_seq]['quantity']
        instrument = self.legs[leg_seq]['instrument']
        #updated_symbol = self.strategy.insight_book.ticker + "_" + instrument if self.strategy.inst_is_option(instrument) else self.strategy.insight_book.ticker
        signal_info = {'symbol': instrument, 'signal_id': self.id,
                       'leg_seq': leg_seq,
                       'qty': quantity}
        last_candle = self.strategy.get_last_tick(instrument)
        last_spot_candle = self.strategy.get_last_tick('SPOT')
        self.legs[leg_seq]['exit_type'] = exit_type
        self.legs[leg_seq]['exit_price'] = last_candle['close']
        self.legs[leg_seq]['spot_exit_price'] = last_spot_candle['close']
        self.strategy.trigger_exit(signal_info)
        self.remove_controller(leg_seq)
        if self.trade_complete() and manage_risk:
            self.strategy.manage_risk()

    def trade_complete(self):
        all_legs_complete = True
        for leg in self.legs.values():
            all_legs_complete = all_legs_complete and leg['exit_type'] is not None
        return all_legs_complete

    def remove_controller(self, leg_seq):
        print('remove_controller test for leg seq++++++++', leg_seq)
        for c_c in range(len(self.controller_list)):
            if self.controller_list[c_c].leg_seq == leg_seq:
                print('removing controller ', self.controller_list[c_c].id)
                self.controller_list[c_c].activation_forward_channels = []
                del self.controller_list[c_c]


    def register_signal(self, signal):
        for controller in self.controller_list:
            if signal.key() == controller.signal_type:
                #print('signal', signal)
                controller.receive_signal(signal)

    def receive_communication(self, info={}):
        self.communication_log(info)
        if info['code'] == 'revise_stop_loss':
            leg = self.legs[info['target_leg']]
            leg['spot_stop_loss_rolling'] = info['new_threshold']
            print(self.id, "new stop loss for leg ", info['target_leg'], 'is ', leg['spot_stop_loss_rolling'])

    def communication_log(self, info):
        #last_tick_time = self.manager.strategy.insight_book.spot_processor.last_tick['timestamp']
        print('Trade Manager id==', repr(self.id), "COM  LOG", 'From Controller id==', info['n_id'], "sent code==", info['code'], "==")
