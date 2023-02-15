from research.strategies.signal_setup import get_signal_key
from research.queues.controllers import get_controller

class Trade:
    def __init__(self, strategy, t_id, trade_inst):
        self.id = t_id
        self.strategy = strategy
        self.trade_completed = False
        self.max_legs = 1
        self.legs = {}
        self.trade_inst = trade_inst
        self.custom_features = {}
        self.controllers = self.strategy.trade_controllers
        self.controller_list = []
        self.con_seq = 0

    def trigger_entry(self):
        legs = self.get_trade_legs()
        if self.controllers:
            for leg_no in range(len(legs)):
                leg = legs[leg_no]
                total_controllers = len(self.strategy.trade_controllers)
                controller_info = self.strategy.trade_controllers[min(leg_no, total_controllers-1)]
                q_signal_key = get_signal_key(controller_info['signal_type'])
                controller_info['signal_type'] = q_signal_key
                controller_id = self.con_seq #len(self.controller_list)
                self.con_seq += 1
                controller = get_controller(self.id +"_"+ repr(controller_id), leg['seq'], leg['entry_price'], leg['spot_stop_loss_rolling'], leg['market_view'], controller_info)
                controller.activation_forward_channels.append(self.receive_communication)
                self.controller_list.append(controller)
        self.strategy.trigger_entry(self.trade_inst, self.strategy.order_type, self.id, legs)

    def get_trade_legs(self):
        next_trigger = len(self.legs) + 1
        legs = [self.get_trades(trd_idx) for trd_idx in range(next_trigger, next_trigger + self.max_legs)]
        for leg in legs:
            self.legs[leg['seq']] = leg
        return legs

    def get_trades(self, idx=1):
        instr = self.trade_inst
        market_view = self.strategy.get_market_view(instr)
        last_candle = self.strategy.get_last_tick(instr)
        last_spot_candle = self.strategy.get_last_tick('SPOT')
        spot_targets = self.calculate_target('SPOT', self.strategy.spot_long_targets) if market_view == 'LONG' else self.calculate_target('SPOT', self.strategy.spot_short_targets)
        spot_stop_losses = self.calculate_target('SPOT', self.strategy.spot_long_stop_losses) if market_view == 'LONG' else self.calculate_target('SPOT', self.strategy.spot_short_stop_losses)
        instr_targets = self.calculate_target(instr, self.strategy.instr_targets) if instr != 'SPOT' else spot_targets
        instr_stop_losses = self.calculate_target(instr, self.strategy.instr_stop_losses) if instr != 'SPOT' else spot_stop_losses
        trade_info = {
            'seq': idx,
            'instrument': instr,
            'cover': self.strategy.cover,
            'market_view': market_view,
            'spot_target': spot_targets[idx-1] if spot_targets else None,
            'spot_stop_loss': spot_stop_losses[idx-1] if spot_stop_losses else None,
            'spot_stop_loss_rolling': spot_stop_losses[idx - 1] if spot_stop_losses else None,
            'instr_target': instr_targets[idx-1] if instr_targets else None,
            'instr_stop_loss': instr_stop_losses[idx-1] if instr_stop_losses else None,
            'duration': min(self.strategy.exit_time[idx-1], self.strategy.insight_book.get_time_to_close()-2),
            'quantity': self.strategy.minimum_quantity,
            'exit_type':None,
            'entry_price':last_candle['close'],
            'exit_price':None,
            'spot_entry_price': last_spot_candle['close'],
            'spot_exit_price': None,
            'trigger_time':last_candle['timestamp']
        }
        return trade_info

    def calculate_target(self, instr, target_level_list):

        levels = []
        last_candle = self.strategy.get_last_tick(instr)
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
                    #print('inside target fn +++++++++', rs)
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
                if last_spot_candle['timestamp'] - trigger_details['trigger_time'] >= trigger_details['duration']*60:
                    self.trigger_exit(trigger_seq, exit_type='TC')
                elif self.strategy.order_type == 'BUY':
                    if trigger_details['instr_target'] and last_instr_candle['close'] >= trigger_details['instr_target']:
                        self.trigger_exit(trigger_seq, exit_type='IT')
                    elif trigger_details['instr_stop_loss'] and last_instr_candle['close'] < trigger_details['instr_stop_loss']:
                        self.trigger_exit(trigger_seq, exit_type='IS')
                elif self.strategy.order_type == 'SELL':
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
                    elif trigger_details['spot_stop_loss_rolling'] and last_spot_candle['close'] < trigger_details['spot_stop_loss']:
                        self.trigger_exit( trigger_seq, exit_type='SS')
                    elif trigger_details['spot_stop_loss_rolling'] and last_spot_candle['close'] < trigger_details['spot_stop_loss_rolling']:
                        self.trigger_exit( trigger_seq, exit_type='SRS')
                elif market_view == 'SHORT':
                    if trigger_details['spot_target'] and last_spot_candle['close'] <= trigger_details['spot_target']:
                        self.trigger_exit(trigger_seq, exit_type='ST')
                        # print(last_candle, trigger_details['target'])
                    elif trigger_details['spot_stop_loss_rolling'] and last_spot_candle['close'] > trigger_details['spot_stop_loss']:
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
            if (signal['category'], signal['indicator']) == controller.signal_type:
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
