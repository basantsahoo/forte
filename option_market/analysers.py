from collections import OrderedDict


class CellAnalyser:
    def __init__(self, cell):
        self.cell = cell

    def compute(self):
        if self.cell.elder_sibling is not None:
            self.cell.analytics['price_delta'] = self.cell.ion.price - self.cell.elder_sibling.ion.price
            self.cell.analytics['oi_delta'] = self.cell.ion.oi - self.cell.elder_sibling.ion.oi
            self.cell.analytics['volume'] = self.cell.ion.volume


class IntradayCrossAssetAnalyser:
    def __init__(self, capsule):
        self.capsule = capsule
        self.call_oi = OrderedDict()
        self.put_oi = OrderedDict()
        self.call_volume = OrderedDict()
        self.put_volume = OrderedDict()

    def compute(self, timestamp_list=[]):
        self.compute_oi_volume(timestamp_list)

    def compute_oi_volume(self, timestamp_list=[]):
        transposed_data = self.capsule.transposed_data
        #print('timestamp_list=====', timestamp_list)
        if not timestamp_list:
            timestamp_list = transposed_data.keys()
        #print(timestamp_list)
        for ts in timestamp_list:
            ts_data = transposed_data[ts]
            call_oi = sum([cell.ion.oi for cell in ts_data.values() if cell.instrument[-2::] == 'CE'])
            put_oi = sum([cell.ion.oi for cell in ts_data.values() if cell.instrument[-2::] == 'PE'])
            call_volume = sum([cell.ion.volume for cell in ts_data.values() if cell.instrument[-2::] == 'CE'])
            put_volume = sum([cell.ion.volume for cell in ts_data.values() if cell.instrument[-2::] == 'PE'])

            self.call_oi[ts] = call_oi
            self.put_oi[ts] = put_oi
            self.call_volume[ts] = call_volume
            self.put_volume[ts] = put_volume
            """
            if self.call_oi[ts] == 0:
                print([cell.ion for cell in ts_data.values() if cell.instrument[-2::] == 'CE'])
            """
            #print(self.call_oi[ts])

    def get_total_call_oi_series(self):
        return list(self.call_oi.values())

    def get_total_put_oi_series(self):
        return list(self.put_oi.values())

class OptionMatrixAnalyser:

    def __init__(self, option_matrix=None):
        self.option_matrix = option_matrix

    def analyse(self):
        if self.option_matrix is not None:
            self.analyse()

    def analyse(self):
        pass
