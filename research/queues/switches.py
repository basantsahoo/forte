def get_switch(switch_info):
    switch_type = switch_info['type']
    if switch_type in ['DistToSL']:
        return DistToSL(**switch_info)
    else:
        raise Exception("Switch is not defined")


class DistToSL:
    def __init__(self, **kwargs):
        self.id = kwargs['id']
        self.switch_eval = kwargs['switch_eval']
        self.thresholds = {'high': None, 'low': None, 'open': None, 'close': None, 'entry': None}

    def set_threshold(self, th_type, th):
        print('Switch id==', repr(self.id), "THRESHOLD  LOG", "Switch class==", self.__class__.__name__, "threshold type==", th_type, 'value ==', th, 'old value ', self.thresholds[th_type])
        self.thresholds[th_type] = th

    def evaluate(self):
        high = self.thresholds['high']
        low = self.thresholds['low']
        open = self.thresholds['open']
        close = self.thresholds['close']
        entry = self.thresholds['entry']
        res = eval(self.switch_eval)
        return res

    def flush(self):
        self.thresholds = {'high': None, 'low': None, 'open': None, 'close': None, 'entry': None}