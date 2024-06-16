
def get_controller_from_config(controller_id, trd_idx, entry_price, spot_stop_loss_rolling, delta, controller_info={}):
    watcher_type = controller_info['type']
    if watcher_type in ['DownController']:
        return DownController.from_config(controller_id=controller_id, trd_idx=trd_idx, entry_price=entry_price, spot_stop_loss_rolling=spot_stop_loss_rolling,delta=delta, controller_info=controller_info)
    else:
        raise Exception("Controller is not defined")

def get_controller_from_store(stored_controller_info):
    print("get_controller_from_store==========================", stored_controller_info)

    watcher_type = stored_controller_info['controller_info']['type']
    if watcher_type in ['DownController']:
        return DownController.from_store(**stored_controller_info)
    else:
        raise Exception("Controller is not defined")


class DownController:
    def __init__(self, controller_id, trd_idx, entry_price, spot_stop_loss_rolling, delta, controller_info):
        self.id = controller_id
        self.trd_idx = trd_idx
        self.entry_price = entry_price
        self.spot_stop_loss_rolling = spot_stop_loss_rolling
        self.delta = delta
        self.signal_type = controller_info['signal_type']
        self.roll_factor = controller_info['roll_factor']
        self.pnl_multiplier = controller_info.get('pnl_multiplier', 1)
        self.activation_forward_channels = []
        self.signals = []
        self.code = 'revise_stop_loss'
        #print('controller created for ', trd_idx)

    @classmethod
    def from_config(cls, **kwargs):
        return cls(**kwargs)

    @classmethod
    def from_store(cls, **kwargs):
        return cls(**kwargs)

    def to_dict(self):
        dct = {}
        for field in ['trd_idx', 'entry_price', 'spot_stop_loss_rolling', 'delta']:
            dct[field] = getattr(self, field)
        dct['controller_info'] = {}
        dct['controller_id'] = self.id

        for field in ['signal_type', 'roll_factor', 'pnl_multiplier']:
            dct['controller_info'][field] = getattr(self, field)
        dct['controller_info']['type'] = 'DownController'
        return dct

    def receive_signal(self, signal):
        self.pre_log()
        self.signals.append(signal.signal_info)
        self.check_activation()

    def check_activation(self):
        #print('check_activation===', self.signals[-1])
        ltp = self.signals[-1]['close']
        factor = -1 if self.delta < 0 else 1
        pnl = factor * (ltp - self.entry_price)
        #print('pnl=====', pnl)
        #print('pnl of controller', self.id,  '+++++++', pnl, self.roll_factor * self.entry_price, self.entry_price)
        if pnl > self.roll_factor * self.pnl_multiplier * self.entry_price:
            #print('rolling controller ++++++', self.id)
            self.forward_activation()

    def forward_activation(self):
        next_high = self.spot_stop_loss_rolling - self.roll_factor * self.entry_price #self.get_next_high()
        next_entry = self.entry_price - self.roll_factor * self.entry_price  # self.get_next_high()
        #print('Controller id==',  repr(self.id), "ROLL  LOG", "Controller class==", self.__class__.__name__, "prev sl==", self.spot_stop_loss_rolling, 'current sl ==', next_high)
        self.spot_stop_loss_rolling = next_high/self.entry_price-1
        self.entry_price = next_entry
        info = {'code': self.code, 'n_id': self.id, 'target_trade': self.trd_idx, 'new_threshold':next_high}
        for channel in self.activation_forward_channels:
            channel(info)

    def pre_log(self):
        #last_tick_time = self.neuron.manager.strategy.insight_book.spot_processor.last_tick['timestamp']
        pass
        print('Controller id==',  repr(self.id), "for trade===", self.trd_idx, "PRE  LOG", "Controller class==", self.__class__.__name__, "signal type==", self.signal_type, 'current count ==', len(self.signals))


