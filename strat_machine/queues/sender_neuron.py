from entities.base import Signal
class SenderNeuron:
    def forward_signal(self, signal={}):
        print('forward_signal++++++++', signal)
        reset_info = {'code': 'reset_signal', 'n_id': self.id}
        for channel in self.reset_on_new_signal_channels:
            print(channel)
            channel(reset_info)
        signal_info = {'code': 'queue_signal', 'n_id': self.id, "signal": signal}
        for channel in self.signal_forward_channels:
            print(channel)
            channel(signal_info)

    def forward_activation_status_change(self, status):
        info = {'code': 'activation', 'n_id': self.id, 'status':status}
        for channel in self.activation_forward_channels:
            channel(info)

    def notify_threshold_change(self):
        for channel in self.threshold_forward_channels:
            th_type = channel['th_type']
            comm_fn = channel['comm_fn']
            th = self.get_watcher_threshold(th_type)
            last_informed = self.last_informed_thresholds[th_type]
            if th != last_informed:
                self.last_informed_thresholds[th_type] = th
                comm_fn(th_type, th)

    def feed_forward(self, msg=None):
        if self.forward_queue:
            #print(self.forward_queue)
            self.feed_forward_log(msg)
        for fwd in self.forward_queue:
            #print(fwd)
            fn = fwd[0]
            args = fwd[1]
            if type(args) == bool or type(args) == Signal:
                fn(args)
            else:
                fn()
        self.forward_queue = []

