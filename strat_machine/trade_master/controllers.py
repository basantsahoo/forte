
def get_controller(controller_id, leg_seq, entry_price, spot_stop_loss_rolling, market_view, controller_info={}):
    watcher_type = controller_info['type']
    if watcher_type in ['DownController']:
        return DownController(controller_id, leg_seq, entry_price, spot_stop_loss_rolling,market_view, controller_info)
    else:
        raise Exception("Controller is not defined")


class DownController:
    def __init__(self, controller_id, leg_seq, entry_price, spot_stop_loss_rolling, market_view, controller_info):
        self.id = controller_id
        self.leg_seq = leg_seq
        self.entry_price = entry_price
        self.spot_stop_loss_rolling = spot_stop_loss_rolling
        self.market_view = market_view
        self.signal_type = controller_info['signal_type']
        self.roll_factor = controller_info['roll_factor']
        self.pnl_multiplier = controller_info.get('pnl_multiplier', 1)
        self.activation_forward_channels = []
        self.signals = []
        self.code = 'revise_stop_loss'
        #print('controller created for ', leg_seq)
    def receive_signal(self, signal):
        #self.pre_log()
        self.signals.append(signal.signal_info)
        self.check_activation()

    def get_next_high(self):
        highs = [signal_info['high'] for signal_info in self.signals if signal_info['high'] < self.spot_stop_loss_rolling]
        highs.sort()
        return highs[-1]

    def check_activation(self):
        ltp = self.signals[-1]['close']
        factor = -1 if self.market_view == 'SHORT' else 1
        pnl = factor * (ltp - self.entry_price)
        #print('pnl of controller', self.id,  '+++++++', pnl, self.roll_factor * self.entry_price, self.entry_price)
        if pnl > self.roll_factor * self.pnl_multiplier * self.entry_price:
            #print('rolling controller ++++++', self.id)
            self.forward_activation()

    def forward_activation(self):
        next_high = self.spot_stop_loss_rolling - self.roll_factor * self.entry_price #self.get_next_high()
        next_entry = self.entry_price - self.roll_factor * self.entry_price  # self.get_next_high()
        #print('Controller id==',  repr(self.id), "ROLL  LOG", "Controller class==", self.__class__.__name__, "prev sl==", self.spot_stop_loss_rolling, 'current sl ==', next_high)
        self.spot_stop_loss_rolling = next_high
        self.entry_price = next_entry
        info = {'code': self.code, 'n_id': self.id, 'target_leg': self.leg_seq, 'new_threshold':next_high}
        for channel in self.activation_forward_channels:
            channel(info)

    def pre_log(self):
        #last_tick_time = self.neuron.manager.strategy.insight_book.spot_processor.last_tick['timestamp']
        pass
        #print('Controller id==',  repr(self.id), "for leg===", self.leg_seq, "PRE  LOG", "Controller class==", self.__class__.__name__, "signal type==", self.signal_type, 'current count ==', len(self.signals))


