def get_watcher(manager=None, watcher_id=0, watcher_info={}, threshold=0):
    watcher_type = watcher_info['type']
    if watcher_type in ['HighBreach']:
        return HighBreach(manager, watcher_id, watcher_info, threshold)
    else:
        raise Exception("Wactcher is not defined")


class HighBreach:
    def __init__(self, manager, watcher_id, watcher_info, threshold):
        self.manager = manager
        self.id = watcher_id
        self.signal_type = watcher_info['signal_type']
        self.min_activation_strength = watcher_info['min_activation_strength']
        self.life_span = watcher_info['life_span']
        self.threshold = threshold
        self.activation_forward_channels = []
        self.active = False
        self.signals = []
        self.creation_time = self.manager.strategy.insight_book.spot_processor.last_tick['timestamp']

    def receive_signal(self, signal):
        self.pre_log()
        if signal['info']['high'] > self.threshold and not self.active:
            self.signals = [signal]
        self.check_activation()

    def destroy(self):
        self.manager.stop_watcher(self.id)

    def check_activation(self):
        if len(self.signals) >= self.min_activation_strength:
            new_status = True
            self.active = new_status
            self.forward_activation(new_status)
            self.post_log()
            self.destroy()

    def check_life(self):
        last_tick_time = self.manager.strategy.insight_book.spot_processor.last_tick['timestamp']
        if last_tick_time - self.creation_time < self.life_span * 60:
            self.destroy()

    def forward_activation(self, status):
        info = {'code': 'watcher_signal', 'n_id' : self.id, 'status':status}
        for channel in self.activation_forward_channels:
            channel(info)

    def pre_log(self):
        print('Watcher id==',  repr(self.id), "PRE  LOG", "Watcher class==", self.__class__.__name__, "signal type==", self.signal_type, 'current count ==', len(self.signals))

    def post_log(self):
        print('Watcher id==', repr(self.id), "POST LOG", "Watcher class==", self.__class__.__name__, "signal type==", self.signal_type,  'current count ==', len(self.signals))


