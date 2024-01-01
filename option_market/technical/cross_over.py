import numpy as np
class Signal:
    def __init__(self, name):
        self.name = name

class DownCrossOver:
    def __init__(self, name, threshold=0.05, call_back_fn=None):
        self.name = name
        self.call_back_fn = call_back_fn
        self.threshold = threshold
        self.last_signal_idx = 0

    def evaluate(self, series, relative_series):
        """
        series = [max(1, x) for x in series]
        relative_series = [max(1, x) for x in relative_series]
        """
        if series and relative_series:
            ratio = [x * 1.00 / y - 1 for x, y in zip(series, relative_series)]
            if ratio[-1] < (-1 * self.threshold):

                for idx in range(len(ratio)-2, 0, -1):
                    #print(idx, " ", len(ratio))
                    if ratio[idx] >= 0:
                        if self.last_signal_idx != idx + 1:
                            self.last_signal_idx = idx + 1
                            print('found', self.name)
                            self.call_back_fn(Signal(self.name))
                        break


class SpotMomentumDetector:
    @staticmethod
    def check_momentum(series, history_period=30):
        if not series:
            return
        recent_history = series[-history_period::]
        high = max(recent_history)
        low = min(recent_history)
        high_index = recent_history.index(high)
        low_index = recent_history.index(low)
        momentum = {'direction': "neutral", 'end_point': None}
        if high*1.00/low - 1 > 0.0012:
            if high_index < low_index:
                momentum = {'direction': "negative", 'end_point': low_index, 'recovery': np.round(series[-1] * 1.00/low - 1, 4)}
            else:
                momentum = {'direction': "positive", 'end_point': high_index, 'recovery': np.round(series[-1] * 1.00/high - 1, 4)}
        print('high', high, high_index)
        print('low', low, low_index)
        return momentum

class OptionBuildupDetector:
    @staticmethod
    def check_build_up(series):
        res = [series[i + 1] - series[i] for i in range(len(series) - 1)]
        buildups = [x for x in res if x > 0]
        coverings = [x for x in res if x < 0]
        indicator = {
            'build_up_period': np.round(len(buildups)* 1.00/len(res), 2),
            'covering_period': np.round(len(coverings) * 1.00 / len(res),2),
            'pct_change': np.round(series[-1] * 1.00 / series[0] -1, 2),
        }
        return indicator

class BuildUpFollowingMomentum:
    def __init__(self, name, momentum_type='positive', call_back_fn=None):
        self.name = name
        self.call_back_fn = call_back_fn
        self.momentum_type = momentum_type
        self.last_signal_idx = 0

    def evaluate(self, spot_series, call_series, put_series):
        if len(spot_series) < 5:
            return
        spot_momentum = SpotMomentumDetector.check_momentum(spot_series)
        call_build_up = OptionBuildupDetector.check_build_up(call_series)
        put_build_up = OptionBuildupDetector.check_build_up(put_series)
        print(spot_momentum)
        print('call == ', call_build_up)
        print('put == ', put_build_up)


class OptionVolumeIndicator:
    def __init__(self, name,  call_back_fn=None):
        self.name = name
        self.call_back_fn = call_back_fn
        self.last_signal_idx = 0

    @staticmethod
    def calc_scale(series):
        scale = 0
        if series:
            avg_volume = np.median(series[:-1][-30::])
            scale = np.round(series[-1] / avg_volume, 2)
        return scale

    def evaluate(self, call_volume, put_volume):
        if len(call_volume) < 3:
            return
        avg_call_volume = np.mean(call_volume[:-1][-10::])
        avg_put_volume = np.mean(put_volume[:-1][-10::])
        call_volume_scale = np.round(call_volume[-1]/avg_call_volume, 2)
        put_volume_scale = np.round(put_volume[-1] / avg_put_volume, 2)
        if call_volume_scale >= 1.6:
            print('call volume scale+++++', call_volume_scale)
        if put_volume_scale >= 1.6:
            print('Put volume scale++++++', put_volume_scale)
