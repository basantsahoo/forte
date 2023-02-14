class ReceiverNeuron:
    def receive_watcher_action(self, info):
        if info['code'] == 'watcher_update_signal':
            self.watcher_thresholds[info['threshold_type']] = info['new_threshold']
            self.forward_queue.append([self.notify_threshold_change, {}])
            self.remove_watchers()
            self.create_watchers()
            self.feed_forward()
        elif info['code'] == 'watcher_reset_signal':
            self.reset()
            self.feed_forward()

    def receive_activation_communication(self, info={}):
        self.communication_log(info)
        if info['code'] == 'activation':
            self.activation_dependency[info['n_id']] = info['status']
            self.check_activation_status_change()
            self.feed_forward()

    def receive_reset_communication(self, info={}):
        self.communication_log(info)
        if info['code'] == 'reset_signal':
            self.reset_neuron_signal()

    def receive_signal_communication(self, info={}):
        print('receive_signal_communication++++++++++++++++++++++++++++++++++++++++++', self.display_id)
        self.communication_log(info)
        high = info['signal']['info']['high']
        low = info['signal']['info']['low']
        close = info['signal']['info']['close']
        self.signal_queue.set_threshold('high', high)
        self.signal_queue.set_threshold('low', low)
        self.signal_queue.set_threshold('close', close)
        if info['code'] == 'queue_signal':
            #self.reset_neuron_signal()
            pass



