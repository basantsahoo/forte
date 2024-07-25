from trade_master.controllers import get_controller_from_config, get_controller_from_store
import copy

from trade_master.leg_group import LegGroup
class Trade:
    def __init__(self, trade_set, trd_idx):
        self.trd_idx = trd_idx
        self.trade_set = trade_set
        self.pnl = 0
        durations = self.trade_set.trade_manager.durations
        carry_forward_days = self.trade_set.trade_manager.carry_forward_days
        targets = self.trade_set.trade_manager.trade_targets
        stop_losses = self.trade_set.trade_manager.trade_stop_losses
        spot_high_stop_losses = self.trade_set.trade_manager.spot_high_stop_losses
        spot_low_stop_losses = self.trade_set.trade_manager.spot_low_stop_losses
        spot_high_targets = self.trade_set.trade_manager.spot_high_targets
        spot_low_targets = self.trade_set.trade_manager.spot_low_targets
        self.durations = durations[min(trd_idx - 1, len(durations) - 1)] if durations else None
        self.carry_forward_days = carry_forward_days[min(trd_idx - 1, len(carry_forward_days) - 1)] if carry_forward_days else 0
        self.target = abs(targets[min(trd_idx - 1, len(targets) - 1)]) if targets else None
        self.stop_loss = -1 * abs(stop_losses[min(trd_idx - 1, len(stop_losses) - 1)]) if stop_losses else float('-inf')
        self.spot_high_stop_loss = abs(self.calculate_target(spot_high_stop_losses[min(trd_idx - 1, len(spot_high_stop_losses) - 1)], float('inf'))) if spot_high_stop_losses else float('inf')
        self.spot_low_stop_loss = -1 * abs(self.calculate_target(spot_low_stop_losses[min(trd_idx - 1, len(spot_low_stop_losses) - 1)], float('-inf'))) if spot_low_stop_losses else float('-inf')
        self.spot_high_target = abs(self.calculate_target(spot_high_targets[min(trd_idx - 1, len(spot_high_targets) - 1)])) if spot_high_targets else float('inf')
        self.spot_low_target = -1 * abs(self.calculate_target(spot_low_targets[min(trd_idx - 1, len(spot_low_targets) - 1)])) if spot_low_targets else float('-inf')

        self.leg_group_exits = {}
        for key, val in self.trade_set.trade_manager.leg_group_exits.items():
            if val:
                self.leg_group_exits[key] = val[trd_idx-1]
            else:
                self.leg_group_exits[key] = {}
        self.leg_groups = {}
        self.exit_orders = []
        self.entry_orders = []
        self.trigger_time = None
        self.exit_time = None
        self.spot_stop_loss_rolling = None
        self.force_exit_time = trade_set.trade_manager.trade_info.get('force_exit_time', None)
        if self.force_exit_time is None:
            self.force_exit_time = self.trade_set.trade_manager.market_book.get_force_exit_ts(trade_set.trade_manager.trade_info.get('force_exit_ts', None))
        print('trade force_exit_time======', self.force_exit_time)
        self.trade_duration = None
        self.spot_entry_price = None
        self.delta = None
        self.controller_list = []
        self.con_seq = 0


    @classmethod
    def from_config(cls, trade_set, trd_idx):
        obj = cls(trade_set, trd_idx)
        leg_groups = copy.deepcopy(trade_set.trade_manager.trade_info["leg_groups"])
        #print(leg_groups)
        for lg_index, leg_group_info in enumerate(leg_groups):
            lg_id = lg_index + 1
            obj.leg_groups[lg_id] = LegGroup.from_config(obj, lg_id, lg_index, leg_group_info)
        obj.other_init()
        return obj

    def set_controllers(self):
        if self.trade_set.trade_manager.trade_controllers:
            total_controllers = len(self.trade_set.trade_manager.trade_controllers)
            controller_info = self.trade_set.trade_manager.trade_controllers[min(self.trd_idx - 1, total_controllers - 1)]
            controller_id = self.con_seq
            self.con_seq += 1
            controller = get_controller_from_config(repr(self.trd_idx) + "_" + repr(controller_id), self.trd_idx, self.spot_entry_price,
                                        self.spot_stop_loss_rolling, self.calculate_delta(), controller_info)
            controller.activation_forward_channels.append(self.receive_communication)
            self.controller_list.append(controller)

    @classmethod
    def from_store(cls, trade_set, trade_info):
        obj = cls(trade_set, trade_info['trd_idx'])
        for leg_group_info in trade_info["leg_groups"]:
            obj.leg_groups[leg_group_info['lg_id']] = LegGroup.from_store(obj, leg_group_info)
        obj.other_init()
        obj.trigger_time = trade_info.get('trigger_time', None)
        obj.spot_high_target = trade_info.get('spot_high_target', None)
        obj.spot_high_stop_loss = trade_info.get('spot_high_stop_loss', None)
        obj.spot_low_target = trade_info.get('spot_low_target', None)
        obj.spot_low_stop_loss = trade_info.get('spot_low_stop_loss', None)
        obj.spot_stop_loss_rolling = trade_info.get('spot_stop_loss_rolling', None)
        obj.con_seq = trade_info['con_seq']
        obj.delta = trade_info['delta']
        obj.controller_list = [get_controller_from_store(stored_controller_info) for stored_controller_info in trade_info['controller_list']]
        print('from store controller list====', obj.controller_list)
        for controller in obj.controller_list:
            controller.activation_forward_channels.append(obj.receive_communication)

        return obj

    def to_dict(self):
        dct = {}
        for field in ['trd_idx', 'trigger_time', 'spot_stop_loss_rolling', 'spot_high_target', 'spot_high_stop_loss', 'spot_low_target', 'spot_low_stop_loss', 'delta', 'con_seq']:
            dct[field] = getattr(self, field)
        dct['leg_groups'] = [leg_group.to_dict() for leg_group in self.leg_groups.values()]
        dct['controller_list'] = [controller.to_dict() for controller in self.controller_list]

        return dct

    def to_partial_dict(self):
        dct = {}
        for field in ['trade_duration']:
            dct[field] = getattr(self, field)
        for field in ['trigger_time', 'exit_time', 'delta']:
            dct['trade_' + field] = getattr(self, field)
        return dct

    def other_init(self):

        self.trade_duration = max([leg_group.duration for leg_group in self.leg_groups.values()])
        self.spot_entry_price = self.leg_groups[list(self.leg_groups.keys())[0]].spot_entry_price
        print('trade  other_init duration===', self.trade_duration)
        print([leg_group.duration for leg_group in self.leg_groups.values()])


    def slide_leg_group(self, prior_lg_id, lg_index):
        """
        print('slide_leg_group ++++++++++++++++++++++++++++')
        lg_entries = [key for key in list(self.leg_groups.keys()) if lg_id in key]
        self.leg_groups[lg_id + '_' + repr(len(lg_entries))] = self.leg_groups[lg_id] #shift the entry to another key
        leg_groups = copy.deepcopy(self.trade_set.trade_manager.trade_info["leg_groups"])
        self.leg_groups[lg_id] = LegGroup.from_config(self, lg_index, leg_groups[lg_index])
        self.leg_groups[lg_id].trigger_entry()
        self.process_entry_orders()
        self.trade_set.process_entry_orders()
        print('slide_leg_group complete++++++++++++++++++++++++++++')
        """
        lg_id = len(self.leg_groups.keys()) + 1
        leg_groups = copy.deepcopy(self.trade_set.trade_manager.trade_info["leg_groups"])
        self.leg_groups[lg_id] = LegGroup.from_config(self, lg_id, lg_index, leg_groups[lg_index])
        self.leg_groups[lg_id].prior_lg_id = prior_lg_id
        self.leg_groups[lg_id].trigger_entry()
        self.process_entry_orders()
        self.trade_set.process_entry_orders()
        print('slide_leg_group complete++++++++++++++++++++++++++++')

    def process_entry_orders(self):
        if self.entry_orders:
            entry_orders = dict()
            entry_orders['trade_seq'] = self.trd_idx
            entry_orders['leg_groups'] = self.entry_orders
            for leg_group_orders in entry_orders['leg_groups']:
                for order in leg_group_orders['legs']:
                    order['trade_seq'] = self.trd_idx
            self.trade_set.entry_orders.append(entry_orders)
            self.entry_orders = []

    def finish_trade_setup_after_entry_order(self):
        self.trigger_time = self.leg_groups[list(self.leg_groups.keys())[0]].trigger_time
        self.spot_entry_price = self.leg_groups[list(self.leg_groups.keys())[0]].spot_entry_price

        spot_high_target_levels = self.trade_set.trade_manager.spot_high_target_levels
        spot_high_stop_loss_levels = self.trade_set.trade_manager.spot_high_stop_loss_levels
        spot_low_target_levels = self.trade_set.trade_manager.spot_low_target_levels
        spot_low_stop_loss_levels = self.trade_set.trade_manager.spot_low_stop_loss_levels

        spot_high_target_level = spot_high_target_levels[min(self.trd_idx - 1, len(spot_high_target_levels) - 1)] if spot_low_target_levels else float('inf')
        spot_high_stop_loss_level = spot_high_stop_loss_levels[min(self.trd_idx - 1, len(spot_high_stop_loss_levels) - 1)] if spot_high_stop_loss_levels else float('inf')
        spot_low_target_level = spot_low_target_levels[min(self.trd_idx - 1, len(spot_low_target_levels) - 1)] if spot_low_target_levels else float('-inf')
        spot_low_stop_loss_level = spot_low_stop_loss_levels[min(self.trd_idx - 1, len(spot_low_stop_loss_levels) - 1)] if spot_low_stop_loss_levels else float('-inf')

        self.spot_high_target = round(min(self.spot_high_target, spot_high_target_level / self.spot_entry_price - 1), 4)
        self.spot_high_stop_loss = round(min(self.spot_high_stop_loss, spot_high_stop_loss_level / self.spot_entry_price - 1), 4)
        self.spot_low_target = round(min(self.spot_low_target, spot_low_target_level / self.spot_entry_price - 1), 4)
        self.spot_low_stop_loss = round(min(self.spot_low_stop_loss, spot_low_stop_loss_level / self.spot_entry_price - 1), 4)
        self.delta = self.calculate_delta()
        self.spot_stop_loss_rolling = self.spot_low_stop_loss if self.delta >= 0 else self.spot_high_stop_loss #if self.delta < 0 else None
        #print('self.spot_stop_loss_rolling+++++++++', self.spot_stop_loss_rolling)
        self.set_controllers()

    def trigger_entry(self):
        for leg_group_id, leg_group in self.leg_groups.items():
            leg_group.trigger_entry()
        self.process_entry_orders()
        self.finish_trade_setup_after_entry_order()

    def calculate_target(self, target_level, default=None):
        #print('calculate_target+++++++++++++++++++++++++', target_level)
        rs = default
        if isinstance(target_level, (int, float)):
            rs = target_level
        else:
            mapped_fn = target_level['mapped_fn']
            kwargs = target_level.get('kwargs', {})
            if target_level['category'] == 'signal_queue':
                queue = self.trade_set.trade_manager.strategy.entry_signal_pipeline.get_neuron_by_id(target_level['mapped_object'])
                # print('queue.'+ mapped_fn + "()")

                rs = eval('queue.' + mapped_fn)(**kwargs)
                print('inside target fn +++++++++', rs)
                rs = default if rs is None else rs
            elif target_level['category'] == 'global':
                obj = target_level['mapped_object']
                fn_string = 'self.' + (obj + '.' if obj else '') + mapped_fn  # + '()'
                # print(fn_string)
                rs = eval(fn_string)(**kwargs)
        return rs

    def complete(self):
        all_leg_groups_complete = True
        for leg_group in self.leg_groups.values():
            all_leg_groups_complete = all_leg_groups_complete and leg_group.complete()
        return all_leg_groups_complete


    def process_exit_orders(self):
        #print('trade process_exit_orders =========', self.trd_idx)
        if self.exit_orders:
            exit_orders = dict()
            exit_orders['trade_seq'] = self.trd_idx
            exit_orders['leg_groups'] = self.exit_orders
            self.exit_orders = []
            self.trade_set.exit_orders.append(exit_orders)
            all_leg_group_exits = [lg.exit_time for lg in self.leg_groups.values()]
            self.exit_time = None if None in all_leg_group_exits else max(all_leg_group_exits)
        #print('total orders in trade set===', len(self.trade_set.exit_orders))


    def trigger_external_exit(self, exit_type):
        print('trade trigger_external_exit===', self.trd_idx)
        for leg_group_id, leg_group in self.leg_groups.items():
            if not leg_group.complete():
                leg_group.trigger_exit(exit_type)
        self.process_exit_orders()

    def trigger_exit(self, exit_type):
        print('trade trigger_exit===', self.trd_idx)
        for leg_group_id, leg_group in self.leg_groups.items():
            if not leg_group.complete():
                leg_group.trigger_exit(exit_type)

    def monitor_existing_positions_close(self):
        self.close_on_trade_tg()
        self.close_on_trade_sl_tm()
        self.close_on_spot_tg_sl()
        for leg_group_id, leg_group in self.leg_groups.items():
            if not leg_group.complete():
                leg_group.close_on_instr_tg() #Is this redundant?
                leg_group.close_on_instr_sl_tm()
        #for leg_group_id, leg_group in self.leg_groups.items():
            if not leg_group.complete():
                leg_group.close_on_spot_tg_sl()
        self.process_exit_orders()

    def monitor_existing_positions_target(self):
        print('trade monitor_existing_positions_target===', self.trd_idx)
        self.close_on_trade_tg()
        for leg_group_id, leg_group in self.leg_groups.items():
            if not leg_group.complete():
                leg_group.close_on_instr_tg()
        self.process_exit_orders()

    def calculate_pnl(self):
        capital_list = []
        pnl_list = []
        for leg_group_id, leg_group in self.leg_groups.items():
            capital, pnl, pnl_pct = leg_group.calculate_pnl()
            capital_list.append(capital)
            pnl_list.append(pnl)
        pnl_ratio = sum(pnl_list)/sum(capital_list)
        return sum(capital_list), sum(pnl_list), pnl_ratio

    def calculate_delta(self):
        trade_delta = []
        for leg_group_id, leg_group in self.leg_groups.items():
            if leg_group.prior_lg_id is None:
                delta = leg_group.delta
            trade_delta.append(delta)
        return sum(trade_delta)

    def close_on_trade_sl_tm(self):
        capital, pnl, pnl_pct = self.calculate_pnl()
        #print('trade p&l==========', capital, pnl, pnl_pct)
        #print('self.stop_loss=====', self.stop_loss)
        asset = list(self.leg_groups.values())[0].asset
        last_spot_candle = self.trade_set.trade_manager.get_last_tick(asset, 'SPOT')
        max_run_time = self.trigger_time + self.trade_duration * 60 if self.force_exit_time is None else min(
            self.trigger_time + self.trade_duration * 60, self.force_exit_time + 60)

        #print("trade trade_duration =", self.trade_duration)
        #print("trade self.trigger_time + self.trade_duration * 60 =", self.trigger_time + self.trade_duration*60)
        #print("trade self.force_exit_time + 60 =", self.force_exit_time + 60)
        #print("trade max_run_time =", max_run_time)

        if last_spot_candle['timestamp'] >= max_run_time:
            self.trigger_exit(exit_type='TRD_TC')
        elif self.force_exit_time and last_spot_candle['timestamp'] >= self.force_exit_time:
            self.trigger_exit(exit_type='TRD_TCFE')
        elif self.stop_loss and pnl_pct < self.stop_loss:
            self.trigger_exit(exit_type='TRD_TS')

    def close_on_trade_tg(self):
        capital, pnl, pnl_pct = self.calculate_pnl()
        if self.target and pnl_pct > self.target:
            self.trigger_exit(exit_type='TRD_TT')

    def close_on_spot_tg_sl(self):
        asset = list(self.leg_groups.values())[0].asset
        last_spot_candle = self.trade_set.trade_manager.get_last_tick(asset, 'SPOT')
        delta = self.calculate_delta()
        #print('self.spot_stop_loss_rolling=====', self.spot_stop_loss_rolling)
        if delta >= 0:
            if self.spot_high_target and last_spot_candle['close'] >= self.spot_entry_price * (1 + self.spot_high_target):
                self.trigger_exit(exit_type='TRD_ST')
            elif self.spot_low_stop_loss and last_spot_candle['close'] < self.spot_entry_price * (1 + self.spot_low_stop_loss):
                self.trigger_exit(exit_type='TRD_SS')

            elif self.spot_stop_loss_rolling and last_spot_candle['close'] < self.spot_entry_price * (1 + self.spot_stop_loss_rolling):
                #print('This loop+++++++++++++++')
                self.trigger_exit(exit_type='TRD_SRS')

        elif delta < 0:
            if self.spot_low_target and last_spot_candle['close'] <= self.spot_entry_price * (1 + self.spot_low_target):
                self.trigger_exit(exit_type='TRD_ST')
                # print(last_candle, trigger_details['target'])
            elif self.spot_high_stop_loss and last_spot_candle['close'] > self.spot_entry_price * (1 + self.spot_high_stop_loss):
                self.trigger_exit(exit_type='TRD_SS')
            elif self.spot_stop_loss_rolling and last_spot_candle['close'] > self.spot_entry_price * (1 + self.spot_stop_loss_rolling):
                self.trigger_exit(exit_type='TRD_SRS')

    # This is for trade controllers
    def register_signal(self, signal):
        for controller in self.controller_list:
            """
            print('controller++++++++++++++++++++++++++++++++++++++++++++++')
            print(signal.key())
            print(tuple(controller.signal_type))
            """
            if signal.key() == tuple(controller.signal_type):
                #print('signal', signal)
                controller.receive_signal(signal)


    def receive_communication(self, info={}):
        self.communication_log(info)
        if info['code'] == 'revise_stop_loss':
            if self.trd_idx == info['target_trade']:
                self.spot_stop_loss_rolling = info['new_threshold']
                print("Trade set", self.trade_set.id, "new stop loss for trade ", info['target_trade'], 'is ', self.spot_stop_loss_rolling)
        if info['code'] == 'trade_slide':
            if self.trd_idx == info['target_trade']:
                for leg_group_id, leg_group in self.leg_groups.copy().items():
                    if not leg_group.complete():
                        leg_group.check_slide_status()
                print("Trade set", self.trade_set.id, "Checking trade slides==============")

    def communication_log(self, info):
        #last_tick_time = self.manager.strategy.insight_book.spot_processor.last_tick['timestamp']
        print('Trade id==', repr(self.trd_idx), "COM  LOG", 'From Controller id==', info['n_id'], "sent code==", info['code'], "==")
