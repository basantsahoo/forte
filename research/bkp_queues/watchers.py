from datetime import datetime
from research.queues.process_logger import ProcessLoggerMixin
from research.config import watcher_log

def get_watcher(neuron=None, watcher_id=0, watcher_info={}, threshold=0):
    watcher_type = watcher_info['type']
    if watcher_type in ['HighBreach']:
        return HighBreach(neuron, watcher_id, watcher_info, threshold)
    else:
        raise Exception("Watcher is not defined")


class HighBreach(ProcessLoggerMixin):
    def __init__(self, neuron, watcher_id, watcher_info, threshold):
        self.neuron = neuron
        self.id = watcher_id
        self.signal_type = watcher_info['signal_type']
        self.min_activation_strength = watcher_info['min_activation_strength']
        self.life_span = watcher_info['life_span']
        self.threshold = threshold
        self.threshold_type = 'high'
        self.activation_forward_channels = []
        self.active = False
        self.signals = []
        self.code = 'watcher_update_signal'
        self.creation_time = self.neuron.manager.strategy.insight_book.spot_processor.last_tick['timestamp']
        self.display_id = self.neuron.manager.strategy.id + ' Watcher id== ' + repr(self.id)
        self.log_enabled = watcher_log

    def receive_signal(self, signal):
        #self.pre_log()
        if signal['info']['high'] > self.threshold and not self.active:
            self.signals = [signal]
        self.check_activation()

    def check_activation(self):
        if len(self.signals) >= self.min_activation_strength:
            new_status = True
            self.active = new_status
            self.forward_activation(new_status)
            self.post_log()

    def life_span_complete(self):
        last_tick_time = self.neuron.manager.strategy.insight_book.spot_processor.last_tick['timestamp']
        return last_tick_time - self.creation_time > self.life_span * 60

    def forward_activation(self, status):
        threshold = self.signals[-1]['info']['high']
        info = {'code': self.code, 'n_id': self.id, 'status': status, 'threshold_type': self.threshold_type, 'new_threshold':threshold}
        for channel in self.activation_forward_channels:
            channel(info)

    def pre_log(self):
        last_tick_time = datetime.fromtimestamp(self.neuron.manager.strategy.insight_book.spot_processor.last_tick['timestamp'])
        self.log(' Watcher id==',  repr(self.id), "PRE  LOG", "Watcher class==", self.__class__.__name__, "signal type==", self.signal_type, 'current count ==', len(self.signals))

    def post_log(self):
        last_tick_time = self.neuron.manager.strategy.insight_book.spot_processor.last_tick['timestamp']
        self.log(' Watcher id==', repr(self.id), "POST LOG", "Watcher class==", self.__class__.__name__, "signal type==", self.signal_type,  'current count ==', len(self.signals))


