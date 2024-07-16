from collections import defaultdict, deque
from pathlib import Path
from os import listdir
from os.path import isfile, join
import json
from entities.base import Signal


class MarketStateManager:
    def __init__(self, spot_book):
        #print('=========PathManager============ init')
        self.spot_book = spot_book
        self.state_config = {}
        self.last_ts = None
        self.time_period = 5*60
        state_config_dir = str(Path(__file__).resolve().parent.parent) + "/deployments/paths/"
        state_files = [f for f in listdir(state_config_dir) if isfile(join(state_config_dir, f))]
        for fl in state_files:
            with open(state_config_dir + fl, 'r') as state_config:
                state_info = json.load(state_config)
                print(state_info)
                self.state_config[state_info['id']] = StateEvaluator.load_from_config(self, state_info)

    def frame_change_action(self, current_frame, next_frame):
        if self.last_ts is None or current_frame - self.last_ts >= self.time_period:
            self.last_ts = current_frame
            #print("MarketStateManager =   =    frame_change_action")
            for state in self.state_config.values():
                state.evaluate()


class StateEvaluator:
    def __init__(self, manager, time_criteria, market_criteria_groups, paths):
        self.manager = manager
        self.criteria_evaluator = CriteriaEvaluator(manager, time_criteria, market_criteria_groups)
        self.path_evaluator = PathEvaluator(manager, paths)
        self.signal_config = {}
        self.status = False

    def evaluate(self):
        if not self.status:
            #print("StateEvaluator =   =    evaluate")
            self.status = self.criteria_evaluator.evaluate() and self.path_evaluator.evaluate()
            if self.status:
                pat = Signal(asset=self.manager.spot_book.asset_book.asset, category=self.signal_config['category'], instrument=None,
                             indicator= self.signal_config['indicator'],
                             strength=1,
                             signal_time=self.manager.last_ts,
                             notice_time=self.manager.last_ts,
                             signal_info=self.manager.spot_book.asset_book.get_last_tick('SPOT'), key_levels={}, period="1min")

                self.manager.spot_book.asset_book.pattern_signal(pat)
                #print("StateEvaluator =   =    Dispatch Signal ========")

    @classmethod
    def load_from_config(cls, manager, config):
        obj = cls(manager, config["time_criteria"], config["market_criteria_groups"], config["paths"])
        obj.signal_config = config['signal']

        return obj


class CriteriaEvaluator:
    def __init__(self, manager, time_criteria, market_criteria_groups):
        self.manager = manager
        self.time_criteria_node = [NodeEvaluator(manager, 'time', criteria) for criteria in time_criteria]
        self.market_criteria_groups = market_criteria_groups  #One from each group should be True (OR). All groups should be successful (AND)
        self.market_criteria_group_nodes = [GroupEvaluator(manager, group) for group in  market_criteria_groups]
        self.node_graph = {}

    def evaluate(self):

        time_status = all([node.evaluate() for node in self.time_criteria_node]) if self.time_criteria_node else True
        market_criteria_status = all([group.evaluate() for group in self.market_criteria_group_nodes])
        print("CriteriaEvaluator =   =    evaluate", time_status and market_criteria_status)
        return time_status and market_criteria_status


class GroupEvaluator:
    def __init__(self, manager,  criteria_groups):
        self.manager = manager
        self.group_nodes = [NodeEvaluator(criteria) for criteria in criteria_groups]
        self.node_graph = {}
        self.status = not len(self.group_nodes)

    def evaluate(self):
        if not self.status:
            for idx, node in self.node_graph:
                if not node.status:
                    if node.previous_node is None or node.previous_node.status:
                        node.evaluate()
            self.status = any([node.status for node in self.group_nodes])
            #print("GroupEvaluator =   =    evaluate", self.status)
        return self.status



class PathEvaluator:
    def __init__(self, manager, paths):
        self.manager = manager
        self.paths = paths
        self.node_graph = {}
        self.status = not len(self.paths)
        for idx, criteria in enumerate(paths):
            if idx == 0:
                self.node_graph[idx] = NodeEvaluator(manager, idx, criteria)
            else:
                self.node_graph[idx] = NodeEvaluator(manager, idx, criteria, self.node_graph[idx-1])

    def evaluate(self):
        for idx, node in self.node_graph.items():
            if not node.status:
                if node.previous_node is None or node.previous_node.status:
                    node.evaluate()
                    self.status = node.status and self.status
        for node in self.node_graph.values():
            print(node.condition, "==", node.status)
        self.status = all([node.status for node in self.node_graph.values()])
        print("PathEvaluator =   =    evaluate", self.status)
        return self.status


class NodeEvaluator:
    def __init__(self, manager, id, condition, previous_node=None, satisfied=False):
        self.manager = manager
        self.id = id
        self.condition = condition
        self.previous_node = previous_node
        self.status = False

    def evaluate(self):

        if not self.status:
            asset = self.manager.spot_book.asset_book.asset
            trade_day = self.manager.spot_book.asset_book.market_book.trade_day
            market_params = self.manager.spot_book.spot_processor.get_market_params()
            volume_profile = self.manager.spot_book.volume_profile.volume_profile
            market_profile = self.manager.spot_book.volume_profile.market_profile
            #volume_profile = self.manager.spot_book.volume_profile.price_data[trade_day][asset]['volume_profile']
            #market_profile = self.manager.spot_book.volume_profile.price_data[trade_day][asset]['market_profile']

            #print('volume_profile=============', volume_profile)
            #print('market_profile=============', market_profile)
            volume_poc = volume_profile.get('poc_price')
            market_poc = market_profile.get('poc_price')
            #print('volume_poc====', volume_poc)
            #print('market_poc====', market_poc)
            volume_profile_above_poc = volume_profile.get('above_poc')
            volume_profile_below_poc = volume_profile.get('below_poc')
            volume_profile_vah = volume_profile.get('vah')
            third_tpo_high_extn = volume_profile.get('third_tpo_high_extn')
            third_tpo_low_extn = volume_profile.get('third_tpo_low_extn')
            h_a_l = volume_profile.get('h_a_l')
            ext_low = market_profile['profile_dist']['ext_low']
            ext_high = market_profile['profile_dist']['ext_high']
            sin_print = market_profile['profile_dist']['sin_print']
            p_shape = market_profile['profile_dist'].get('p_shape', "")
            close = market_profile.get('close')
            #print('volume_profile_vah======', volume_profile_vah)
            #print('close======', close)

            # print(market_params)
            d2_ad_resistance_pressure = market_params.get('d2_ad_resistance_pressure', 0)
            price_location = market_params.get('price_location', 50)
            # print('price_location+++++++++++++++++++', price_location)
            five_min_trend = market_params.get('five_min_trend', 0)
            exp_b = market_params.get('exp_b', 0)
            d2_cd_new_business_pressure = market_params.get('d2_cd_new_business_pressure', 0)
            open_type = market_params['open_type']
            tpo = market_params['tpo']

            self.status =  eval(self.condition)
            #print("NodeEvaluator =   =    evaluate", self.condition, self.status)
        return self.status

