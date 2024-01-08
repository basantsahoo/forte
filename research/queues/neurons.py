from helper.utils import locate_point
from research.queues.signal_queue import SignalQueue
from research.strategies.signal_setup import get_signal_key
from research.queues.watchers import get_watcher
from research.queues.sender_neuron import SenderNeuron
from research.queues.receiver_neuron import ReceiverNeuron
from research.queues.process_logger import ProcessLoggerMixin
from research.config import neuron_log

class Neuron(SenderNeuron, ReceiverNeuron, ProcessLoggerMixin):
    def __init__(self, manager, **kwargs):
        self.manager = manager
        self.id = kwargs['id']
        self.signal_type = get_signal_key(kwargs['signal_type'])
        self.min_activation_strength = kwargs['min_activation_strength']
        self.max_activation_strength = kwargs['max_activation_strength']
        self.trade_eval = kwargs['trade_eval']
        self.flush_hist = kwargs['flush_hist']
        self.register_instr = kwargs['register_instr']
        self.signal_queue = SignalQueue(**kwargs['signal_queue_info'])
        self.update_watcher_info = kwargs['update_watcher_info']
        self.reset_watcher_info = kwargs['reset_watcher_info']
        self.reset_on_new_signal_channels = []
        self.signal_forward_channels = []
        self.activation_forward_channels = []
        self.threshold_forward_channels = []
        self.active = False
        self.pending_trade_eval = False
        self.activation_dependency = {}
        self.watcher_list = []
        self.watcher_seq = 0
        self.watcher_thresholds = {'high': None, 'low': None, 'close': None}
        self.last_informed_thresholds = {'high': None, 'low': None, 'close': None}
        for back_neuron_id in kwargs['activation_subscriptions']:
            self.activation_dependency[back_neuron_id] = False
        self.forward_queue = []
        self.display_id = self.manager.strategy.id + " Neuron id ======== " + repr(self.id)
        self.log_enabled = kwargs.get('neuron_log', neuron_log)
        #print(self.display_id, self.log_enabled)

    # Q network will send filtered messages
    def test(self):
        # self.log(self.signal_queue.signals)
        pass

    def receive_signal(self, signal):
        if self.dependency_satisfied():
            self.log('receive_signal', signal)
            self.add_to_signal_queue(signal)


    # Check if all the dependent neurons are active
    def dependency_satisfied(self):
        status = True
        for st in self.activation_dependency.values():
            status = status and st
        return status

    #add new signal to queue, forward new signal to subscribers, notify thershold change and check activation status
    def add_to_signal_queue(self, signal):
        new_signal = self.signal_queue.new_signal(signal)
        if new_signal:
            #print('new signal')
            self.pending_trade_eval = True
            status_change = self.check_activation_status_change()
            self.register_instrument(status_change)
            self.forward_queue.append([self.forward_signal, signal])
            self.forward_queue.append([self.notify_threshold_change, {}])
            self.feed_forward('new signal')

    def register_instrument(self, status_change=False):

        if self.active:
            if status_change:
                if self.register_instr:
                    print('going to register_instrument +++++++')
                    self.manager.strategy.register_instrument(self.signal_queue.get_signal(-1))
            elif self.register_instr == 'always':
                self.manager.strategy.register_instrument(self.signal_queue.get_signal(-1))


    def check_activation_status_change(self):
        #print('check_activation_status_change')
        if (len(self.signal_queue.signals) >= self.min_activation_strength) and (len(self.signal_queue.signals) <= self.max_activation_strength):
            new_status = True
        else:
            new_status = False
        status_change = new_status != self.active
        if status_change:
            self.log("status changed. new activation stats=====", new_status)
            if new_status:
                self.create_watchers()
            else:
                self.remove_watchers()
            self.active = new_status
            self.forward_queue.append([self.forward_activation_status_change, new_status])
            self.post_log()
        return status_change


    def create_watchers(self):
        if self.update_watcher_info:
            self.new_watcher('watcher_update_signal')
        if self.reset_watcher_info:
            self.new_watcher('watcher_reset_signal')

    def new_watcher(self, code='watcher_update_signal'):
        watcher_info = self.update_watcher_info.copy() if code == 'watcher_update_signal' else self.reset_watcher_info.copy()
        q_signal_key = get_signal_key(watcher_info['signal_type'])
        watcher_info['signal_type'] = q_signal_key
        watcher_id = self.watcher_seq #len(self.watcher_list)
        self.watcher_seq += 1
        if watcher_info['type'] in ['HighBreach']:
            threshold = self.get_watcher_threshold('high')
        else:
            threshold = self.get_watcher_threshold('close')
        watcher = get_watcher(self, watcher_id, watcher_info, threshold)
        watcher.code = code
        watcher.activation_forward_channels.append(self.receive_watcher_action)
        self.watcher_list.append(watcher)
        self.log("Watcher id", watcher_id, " created")

    def get_watcher_threshold(self, th_type):
        th = self.watcher_thresholds[th_type]
        self.log('get_watcher_threshold in Neuron===== ', th_type, self.id)
        self.log('threshold', th)
        #print(self.signal_queue.signals)
        if th is None:
            th = self.signal_queue.get_signal(-1).info[th_type] if self.signal_queue.signals else None
            try:
                self.log(self.signal_queue.signals)
            except:
                pass
        return th

    def remove_watchers(self, watcher_id=None):
        if watcher_id is None:
            for watcher in self.watcher_list:
                self.log("Watcher id", watcher.id, " removed")
                watcher.activation_forward_channels = []
            self.watcher_list = []
        else:
            for w in range(len(self.watcher_list)):
                if self.watcher_list[w].id == watcher_id:
                    self.log("Watcher id", watcher_id, " removed")
                    del self.watcher_list[w]
                    break


    def flush(self):
        if self.flush_hist:
            self.reset()
            self.feed_forward()

    def reset_neuron_signal(self):
        if not self.active:
            self.reset()
            self.feed_forward()

    def reset(self):
        self.reset_log()
        self.signal_queue.reset()
        self.remove_watchers()
        self.watcher_thresholds = {'high': None, 'low': None, 'close': None}
        self.forward_queue.append([self.notify_threshold_change, {}])
        self.check_activation_status_change()


    def check_validity(self):
        last_tick_time = self.manager.strategy.asset_book.spot_book.spot_processor.last_tick['timestamp']
        self.signal_queue.check_validity(last_tick_time)
        self.check_activation_status_change()
        self.feed_forward()
        for watcher in self.watcher_list:
            if watcher.life_span_complete():
                del watcher

    def has_signal(self):
        return self.active

    def pre_log(self):
        last_tick_time = self.manager.strategy.asset_book.spot_processor.last_tick['timestamp']
        self.log(last_tick_time, "PRE  LOG", "Neuron class==", self.__class__.__name__, "signal type==", self.signal_type, 'dependency satisfied ==', self.dependency_satisfied(), 'current count ==', len(self.signal_queue.signals))

    def post_log(self):
        self.log("POST LOG", "Neuron class==", self.__class__.__name__, "signal type==", self.signal_type, 'dependency satisfied ==', self.dependency_satisfied(), 'current count ==', len(self.signal_queue.signals))

    def reset_log(self):
        self.log("RESET LOG")

    def feed_forward_log(self, msg):
        self.log("FEED FORWARD LOG", msg)

    def communication_log(self, info):
        last_tick_time = self.manager.strategy.asset_book.spot_processor.last_tick['timestamp']
        if info['code'] not in ['watcher_update_signal', 'watcher_reset_signal']:
            self.log(last_tick_time, "COM  LOG", 'From Neuron id==', info['n_id'], "sent code==", info['code'], "==" ,info.get('status', None))
        else:
            self.log(last_tick_time, "COM  LOG", 'From Watcher id==', info['n_id'], "sent code==", info['code'], "==" ,info.get('status', None))

    def get_attributes(self, pos=-1):
        res = {}
        pattern = self.signal_queue.get_signal(pos)
        if pattern.info.get('price_list', None) is not None:
            res['pattern_price'] = pattern.info['price_list']
        if pattern.info.get('time_list', None) is not None:
            res['pattern_time'] = pattern.info['time_list']
        if pattern.info.get('time', None) is not None:
            res['pattern_time'] = pattern.info['time']
        if pattern.info.get('candle', None) is not None:
            res['pattern_price'] = pattern.info['candle']
        if pattern.info.get('time_list', None) is not None:
            res['pattern_time'] = pattern.info['time_list']
        if pattern.info.get('call_volume_scale', None) is not None:
            res['call_volume_scale'] = pattern.info['call_volume_scale']
        if pattern.info.get('put_volume_scale', None) is not None:
            res['put_volume_scale'] = pattern.info['put_volume_scale']
        if pattern.info.get('sum_call_volume', None) is not None:
            res['sum_call_volume'] = pattern.info['sum_call_volume']
        if pattern.info.get('sum_put_volume', None) is not None:
            res['sum_put_volume'] = pattern.info['sum_put_volume']

        if hasattr(pattern, 'strike'):
            res['strike'] = pattern['strike']
        if hasattr(pattern, 'kind'):
            res['kind'] = pattern['kind']
        if hasattr(pattern, 'money_ness'):
            res['money_ness'] = pattern['money_ness']

        if res.get('pattern_price', None):
            pattern_df = self.manager.strategy.asset_book.get_inflex_pattern_df().dfstock_3
            pattern_location = locate_point(pattern_df, max(res['pattern_price']))
            res['pattern_location'] = pattern_location
        if pattern.info.get('price_list', None) is not None:
            res['pattern_height'] = self.get_pattern_height()
        res['strength'] = pattern.strength
        return res

    def get_pattern_height(self, pos=-1):
        return 0

    def eval_entry_criteria(self):
        test_criteria = self.trade_eval
        curr_ts = self.manager.strategy.asset_book.spot_book.spot_processor.last_tick['timestamp']
        if not test_criteria:
            return True
        #print(criteria)
        try:
            pattern = self.signals[test_criteria[0]]
        except:
            return False
        #print(pattern)
        strength = pattern['strength']
        signal = pattern.get('signal', "")
        time_lapsed = (curr_ts - pattern['notice_time'])/60
        all_waves = pattern['info'].get('all_waves', [])
        pattern_height = self.get_pattern_height(test_criteria[0])

        test = test_criteria[1] + test_criteria[2] + repr(test_criteria[3])
        """
        print(self.category)
        print(test)
        print(strength)
        """
        res = eval(test)
        self.pending_evaluation = False
        return res

    def eval_exit_criteria(self):
        criteria = self.trade_eval
        curr_ts = self.manager.strategy.asset_book.spot_processor.last_tick['timestamp']
        #print('eval_exit_criteria', criteria)
        if not criteria:
            return True
        #print(criteria)
        try:
            pattern = self.signals[criteria[0]]
        except:
            return False  # Different from entry

        #print(pattern)
        signal = pattern['signal']
        time_lapsed = (curr_ts - pattern['notice_time'])/60
        all_waves = pattern['info'].get('all_waves', [])
        pattern_height = self.get_pattern_height(criteria[0])

        test = criteria[1] + criteria[2] + repr(criteria[3])
        res = eval(test)
        return res

    def get_signal_high(self):
        return self.get_watcher_threshold('high')
        #signal = self.signal_queue.get_signal(-1)
        #return signal['info']['high']

    def get_signal_close(self):
        return self.get_watcher_threshold('close')
