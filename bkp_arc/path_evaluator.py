from collections import defaultdict, deque
from pathlib import Path
from os import listdir
from os.path import isfile, join
import json
from entities.base import Signal
from datetime import datetime


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
                if state_info.get('active', False):
                    #print(state_info)
                    self.state_config[state_info['id']] = StateEvaluator.load_from_config(self, state_info)

    def frame_change_action(self, current_frame, next_frame):
        if self.last_ts is None or current_frame - self.last_ts >= self.time_period:
            self.last_ts = current_frame
            NodeEvaluator.initialize_data(self)
            for state in self.state_config.values():
                state.evaluate()
            NodeEvaluator.clean_data()


class StateEvaluator:
    def __init__(self, manager, time_criteria, market_criteria_groups, paths):
        self.manager = manager
        self.criteria_evaluator = CriteriaEvaluator(manager, self, time_criteria, market_criteria_groups)
        self.path_evaluator = PathEvaluator(manager, self, paths)
        self.signal_config = {}
        self.key_level_fields = []
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

                node_evaluator_data = NodeEvaluator.get_initialized_data()
                for key_level_field in self.key_level_fields:
                    pat.key_levels[key_level_field] = node_evaluator_data.get(key_level_field, None)
                self.manager.spot_book.asset_book.pattern_signal(pat)
                #print("StateEvaluator =   =    Dispatch Signal ========")

    @classmethod
    def load_from_config(cls, manager, config):
        obj = cls(manager, config["time_criteria"], config["market_criteria_groups"], config["paths"])
        obj.signal_config = config['signal']
        obj.key_level_fields = config.get('key_level_fields', [])
        return obj


class CriteriaEvaluator:
    def __init__(self, manager, state_evaluator, time_criteria, market_criteria_groups):
        self.manager = manager
        self.state_evaluator = state_evaluator
        self.time_criteria_node = [NodeEvaluator(manager, state_evaluator, 'time', criteria) for criteria in time_criteria]
        self.market_criteria_groups = market_criteria_groups  #One from each group should be True (OR). All groups should be successful (AND)
        self.market_criteria_group_nodes = [GroupEvaluator(manager, state_evaluator, group) for group in  market_criteria_groups]
        self.node_graph = {}

    def evaluate(self):

        time_status = all([node.evaluate() for node in self.time_criteria_node]) if self.time_criteria_node else True
        market_criteria_status = all([group.evaluate() for group in self.market_criteria_group_nodes])
        #print("CriteriaEvaluator =   =    evaluate", time_status and market_criteria_status)
        #print('time_status', time_status)
        #print('market_criteria_status', market_criteria_status)
        return time_status and market_criteria_status


class GroupEvaluator:
    def __init__(self, manager, state_evaluator, criteria_groups):
        self.manager = manager
        self.state_evaluator = state_evaluator
        self.group_nodes = [NodeEvaluator(manager, state_evaluator,  idx, criteria) for idx, criteria in enumerate(criteria_groups)]
        self.status = not len(self.group_nodes)

    def evaluate(self):
        if not self.status:
            for idx, node in enumerate(self.group_nodes):
                if not node.status:
                    if node.previous_node is None or node.previous_node.status:
                        node.evaluate()
            self.status = any([node.status for node in self.group_nodes])
            #print("GroupEvaluator =   =    evaluate", self.status)
        return self.status


class PathEvaluator:
    def __init__(self, manager, state_evaluator, paths):
        self.manager = manager
        self.state_evaluator = state_evaluator
        self.paths = paths
        self.node_graph = {}
        self.status = not len(self.paths)
        for idx, criteria in enumerate(paths):
            if idx == 0:
                self.node_graph[idx] = NodeEvaluator(manager, state_evaluator, idx, criteria)
            else:
                self.node_graph[idx] = NodeEvaluator(manager, state_evaluator, idx, criteria, self.node_graph[idx-1])

    def evaluate(self):
        for idx, node in self.node_graph.items():
            if not node.status:
                if node.previous_node is None or node.previous_node.status:
                    node.evaluate()
                    self.status = node.status and self.status
        """
        for node in self.node_graph.values():
            print(node.condition, "==", node.status)
        """
        self.status = all([node.status for node in self.node_graph.values()])
        #print("PathEvaluator =   =    evaluate", self.status)
        return self.status


class NodeEvaluator:
    # Class-level cache for initialized data
    _initialized_data = None

    @classmethod
    def get_initialized_data(cls):
        return cls._initialized_data

    @classmethod
    def clean_data(cls):
        cls._initialized_data = None

    @classmethod
    def initialize_data(cls, manager):
        if cls._initialized_data is None:
            try:
                asset = manager.spot_book.asset_book.asset
                trade_day = manager.spot_book.asset_book.market_book.trade_day
                market_params = manager.spot_book.spot_processor.get_market_params()
                volume_profile = manager.spot_book.volume_profile.volume_profile
                market_profile = manager.spot_book.volume_profile.market_profile
                last_week_metric = manager.spot_book.weekly_processor.last_week_metric
                curr_week_metric = manager.spot_book.weekly_processor.get_curr_week_metric()
                hist_day_market_profile_stats = manager.spot_book.weekly_processor.current_week_processor.hist_day_market_profile_stats

                price_location = market_params.get('price_location', 50)
                week_day = datetime.strptime(trade_day, '%Y-%m-%d').strftime('%A')
                open_type = market_params['open_type']
                tpo = market_params['tpo']

                volume_poc = volume_profile.get('poc_price')
                market_poc = market_profile.get('poc_price')
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

                market_profile_vah = market_profile.get('vah')
                market_profile_val = market_profile.get('val')

                day_close = market_profile.get('close')
                day_open = market_profile.get('open')
                day_low = market_profile.get('low')
                day_high = market_profile.get('high')

                open_above_lw_poc = day_open > last_week_metric['poc_price']
                open_above_lw_va = day_open > last_week_metric['va_h_p']
                open_below_lw_va = day_open < last_week_metric['va_l_p']
                open_above_lw_high = day_open > last_week_metric['high']
                open_below_lw_low = day_open < last_week_metric['low']

                close_above_lw_poc = day_close > last_week_metric['poc_price']
                close_above_lw_va = day_close > last_week_metric['va_h_p']
                close_below_lw_va = day_close < last_week_metric['va_l_p']
                close_above_lw_high = day_close > last_week_metric['high']
                close_below_lw_low = day_close < last_week_metric['low']

                hist_close_above_lw_va = any([day_stats['close'] > last_week_metric['va_h_p'] for day_stats in hist_day_market_profile_stats.values()])
                hist_close_below_lw_va = any([day_stats['close'] < last_week_metric['va_l_p'] for day_stats in hist_day_market_profile_stats.values()])

                breach_lw_low = day_low < last_week_metric['low']
                breach_lw_high = day_high > last_week_metric['high']

                sustains_lw_low = market_poc < last_week_metric['low']
                sustains_lw_high = market_poc > last_week_metric['high']

                trade_in_upper_lw_va = market_profile_val > last_week_metric['poc_price']
                trade_in_lower_lw_va = market_profile_vah < last_week_metric['poc_price']

                trade_above_lw_va = market_profile_val > last_week_metric['va_h_p']
                trade_below_lw_va = market_profile_vah < last_week_metric['va_l_p']

                trade_in_lw_va = market_profile_vah > last_week_metric['va_l_p'] and market_profile_val < last_week_metric['va_h_p']

                first_day_of_week = not hist_day_market_profile_stats
                past_days_in_week = len(hist_day_market_profile_stats.keys())
                last_week_range_pct = (last_week_metric['high'] - last_week_metric['low']) / ((last_week_metric['high'] + last_week_metric['low']) / 2)
                last_week_range = [last_week_metric['low'], last_week_metric['high']]
                curr_week_high_pct = (curr_week_metric['high'] - last_week_metric['poc_price']) / ((last_week_metric['high'] + last_week_metric['low']) / 2)
                curr_week_low_pct = (curr_week_metric['high'] - last_week_metric['poc_price']) / ((last_week_metric['high'] + last_week_metric['low']) / 2)
                curr_week_range = [curr_week_metric['low'], curr_week_metric['high']]
                curr_week_range_in_last_week_range = (max(curr_week_range) <= max(last_week_range) * 1.001) and (min(curr_week_range) >= min(last_week_range) * 0.999)
                d2_ad_resistance_pressure = market_params.get('d2_ad_resistance_pressure', 0)
                price_location = market_params.get('price_location', 50)
                five_min_trend = market_params.get('five_min_trend', 0)
                exp_b = market_params.get('exp_b', 0)
                d2_cd_new_business_pressure = market_params.get('d2_cd_new_business_pressure', 0)

                cls._initialized_data = {
                    'asset': asset,
                    'trade_day': trade_day,
                    'market_params': market_params,
                    'volume_profile': volume_profile,
                    'market_profile': market_profile,
                    'last_week_metric': last_week_metric,
                    'curr_week_metric': curr_week_metric,
                    'hist_day_market_profile_stats': hist_day_market_profile_stats,
                    'price_location': price_location,
                    'week_day': week_day,
                    'open_type': open_type,
                    'tpo': tpo,
                    'volume_poc': volume_poc,
                    'market_poc': market_poc,
                    'volume_profile_above_poc': volume_profile_above_poc,
                    'volume_profile_below_poc': volume_profile_below_poc,
                    'volume_profile_vah': volume_profile_vah,
                    'third_tpo_high_extn': third_tpo_high_extn,
                    'third_tpo_low_extn': third_tpo_low_extn,
                    'h_a_l': h_a_l,
                    'ext_low': ext_low,
                    'ext_high': ext_high,
                    'sin_print': sin_print,
                    'p_shape': p_shape,
                    'market_profile_vah': market_profile_vah,
                    'market_profile_val': market_profile_val,
                    'day_close': day_close,
                    'day_open': day_open,
                    'day_low': day_low,
                    'day_high': day_high,
                    'open_above_lw_poc': open_above_lw_poc,
                    'open_above_lw_va': open_above_lw_va,
                    'open_below_lw_va': open_below_lw_va,
                    'open_above_lw_high': open_above_lw_high,
                    'open_below_lw_low': open_below_lw_low,
                    'close_above_lw_poc': close_above_lw_poc,
                    'close_above_lw_va': close_above_lw_va,
                    'close_below_lw_va': close_below_lw_va,
                    'close_above_lw_high': close_above_lw_high,
                    'close_below_lw_low': close_below_lw_low,
                    'hist_close_above_lw_va': hist_close_above_lw_va,
                    'hist_close_below_lw_va': hist_close_below_lw_va,
                    'breach_lw_low': breach_lw_low,
                    'breach_lw_high': breach_lw_high,
                    'sustains_lw_low': sustains_lw_low,
                    'sustains_lw_high': sustains_lw_high,
                    'trade_in_upper_lw_va': trade_in_upper_lw_va,
                    'trade_in_lower_lw_va': trade_in_lower_lw_va,
                    'trade_above_lw_va': trade_above_lw_va,
                    'trade_below_lw_va': trade_below_lw_va,
                    'trade_in_lw_va': trade_in_lw_va,
                    'first_day_of_week': first_day_of_week,
                    'past_days_in_week': past_days_in_week,
                    'last_week_range_pct': last_week_range_pct,
                    'last_week_range': last_week_range,
                    'curr_week_high_pct': curr_week_high_pct,
                    'curr_week_low_pct': curr_week_low_pct,
                    'curr_week_range': curr_week_range,
                    'curr_week_range_in_last_week_range': curr_week_range_in_last_week_range,
                    'predicted_high_level': max(curr_week_range),
                    'predicted_low_level': min(curr_week_range),
                    'd2_ad_resistance_pressure': d2_ad_resistance_pressure,
                    'five_min_trend': five_min_trend,
                    'exp_b': exp_b,
                    'd2_cd_new_business_pressure': d2_cd_new_business_pressure
                }
            except Exception as e:
                print(f"Error initializing NodeEvaluator data: {e}")

    def __init__(self, manager, state_evaluator, id, condition, previous_node=None):
        self.manager = manager
        self.state_evaluator = state_evaluator
        self.id = id
        self.condition = condition
        self.previous_node = previous_node
        self.status = False

    def evaluate(self):
        if not self.status:
            try:
                # Unpack cached data
                data = NodeEvaluator._initialized_data

                # Evaluate condition using cached data
                self.status = eval(self.condition, None, data)
            except Exception as e:
                print(f"Error evaluating condition: {e}")

        return self.status



