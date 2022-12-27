import numpy as np
import numpy.linalg as nl
import scipy.stats as ss
from itertools import product
from collections import OrderedDict
from graphviz import Digraph
from typing import Union, Tuple, Optional
open_type_codes = ['GAP_UP', 'GAP_DOWN', 'ABOVE_VA', 'BELOW_VA', 'INSIDE_VA']
intermediate_steps = ['D99', 'D29', 'D28', 'D27', 'D26', 'D25', 'D24', 'D23', 'D22', 'D21', 'D20', 'D19', 'D18', 'D17', 'D16', 'D15', 'D14', 'D13', 'D12', 'D11', 'D10', 'D9', 'D8', 'D7', 'D6', 'D5', 'D4', 'D3', 'D2', 'D1', 'POC', 'U1', 'U2', 'U3', 'U4', 'U5', 'U6', 'U7', 'U8', 'U9', 'U10', 'U11', 'U12', 'U13', 'U14', 'U15', 'U16', 'U17', 'U18', 'U19', 'U20', 'U21', 'U22', 'U23', 'U24', 'U25', 'U26', 'U27', 'U28', 'U29', 'U99']
#https://github.com/maximtrp/mchmm
class MarkovChain:

    def __init__(self, prev_state="BEGIN"):
        self.states = []
        self.observed_matrix = [[]]
        self.observed_p_matrix = [[]]
        self.model = OrderedDict()
        self.prev_state = prev_state

    def build_transition_model(self, data, transitions):
        model = OrderedDict()
        model[self.prev_state] = {}
        for open_type_code in open_type_codes:
            model[open_type_code] = {}
            model[self.prev_state][open_type_code] = 0

        for (day, features) in data.items():
            model[self.prev_state][features['open_type']] += 1
            transition_list = features[transitions]
            for idx in range(len(transition_list) - 1):
                state = transition_list[idx]
                follow = transition_list[idx + 1]
                if not idx:
                    if state not in model[features['open_type']]:
                        model[features['open_type']][state] = 0
                    model[features['open_type']][state] += 1
                if state not in model:
                    model[state] = {}
                if follow not in model[state]:
                    model[state][follow] = 0
                model[state][follow] += 1
        self.model = model

    def calc_transition_freq(self):
        self.states = np.array(list(self.model.keys()))
        matrix = np.zeros((len(self.states), len(self.states)))
        for x in range(len(self.states)):
            xid = np.argwhere(self.states == self.states[x]).flatten()
            transitions = self.model[self.states[x]]
            for to_state in list(transitions.keys()):
                yid = np.argwhere(self.states == to_state).flatten()
                cnt = transitions[to_state]
                matrix[xid, yid] = cnt
        return matrix

    def n_order_matrix(self,order):
        return nl.matrix_power(self.observed_p_matrix, order)

    def prob_to_freq_matrix(self):
        _mat = self.observed_p_matrix
        _rt = self._obs_row_totals
        _rt = _rt[:, None] if _rt.ndim == 1 else _rt
        return _mat * _rt

    def from_data(self, data, transitions='transitions'):
        # states list
        self.build_transition_model(data, transitions)
        self.observed_matrix = self.calc_transition_freq()
        self._obs_row_totals = np.sum(self.observed_matrix, axis=1)
        # observed transition probability matrix
        self.observed_p_matrix = np.nan_to_num(
            self.observed_matrix / self._obs_row_totals[:, None]
        )
        # filling in a row containing zeros with uniform p values
        uniform_p = 1 / len(self.states)
        zero_row = np.argwhere(self.observed_p_matrix.sum(1) == 0).ravel()
        #self.observed_p_matrix[zero_row, :] = uniform_p
        # expected transition frequency matrix
        self.expected_matrix = ss.contingency.expected_freq(self.observed_matrix)

    def chisquare(self,**kwargs):
        _obs = self.observed_matrix
        _exp = self.expected_matrix
        return ss.chisquare(f_obs=_obs, f_exp=_exp, **kwargs)

    def graph_make(self, *args, **kwargs) -> Digraph:
        '''Make a directed graph of a Markov chain using `graphviz`.
        Parameters
        ----------
        args : optional
            Arguments passed to the underlying `graphviz.Digraph` method.
        kwargs : optional
            Keyword arguments passed to the underlying `graphviz.Digraph`
            method.
        Returns
        -------
        graph : graphviz.dot.Digraph
            Digraph object with its own methods.
        Note
        ----
        `graphviz.dot.Digraph.render` method should be used to output a file.
        '''
        self.graph = Digraph(*args, **kwargs)

        ids = range(len(self.states))
        edges = product(ids, ids)

        for edge in edges:
            v1 = edge[0]
            v2 = edge[1]
            s1 = self.states[v1]
            s2 = self.states[v2]
            p = np.round(self.observed_p_matrix[v1, v2], 2)
            if p > 0:
                self.graph.edge(s1, s2, label=str(p), weight=str(p))

        return self.graph

    def simulate(
            self,
            n: int,
            tf: np.ndarray = None,
            states: Optional[Union[np.ndarray, list]] = None,
            start: Optional[Union[str, int]] = None,
            ret: str = 'both',
            seed: Optional[Union[list, np.ndarray]] = None
            ) -> Union[np.ndarray, Tuple[np.ndarray, np.ndarray]]:
        '''Markov chain simulation based on `scipy.stats.multinomial`.
        Parameters
        ----------
        n : int
            Number of states to simulate.
        tf : numpy.ndarray, optional
            Transition frequency matrix.
            If None, `observed_matrix` instance attribute is used.
        states : Optional[Union[np.ndarray, list]]
            State names. If None, `states` instance attribute is used.
        start : Optional[str, int]
            Event to begin with.
            If integer is passed, the state is chosen by index.
            If string is passed, the state is chosen by name.
            If `random` string is passed, a random state is taken.
            If left unspecified (None), an event with maximum
            probability is chosen.
        ret : str, optional
            Return state indices if `indices` is passed.
            If `states` is passed, return state names.
            Return both if `both` is passed.
        seed : Optional[Union[list, numpy.ndarray]]
            Random states used to draw random variates (of size `n`).
            Passed to `scipy.stats.multinomial` method.
        Returns
        -------
        x : numpy.ndarray
            Sequence of state indices.
        y : numpy.ndarray, optional
            Sequence of state names.
            Returned if `return` arg is set to 'states' or 'both'.
        '''
        # matrices init
        if tf is None:
            tf = self.observed_matrix
            fp = self.observed_p_matrix
        else:
            fp = tf / tf.sum(axis=1)[:, None]

        # states init
        if states is None:
            states = self.states
        if not isinstance(states, np.ndarray):
            states = np.array(states)

        # choose a state to begin with
        # `_start` is always an index of state
        if start is None:
            row_totals = tf.sum(axis=1)
            _start = np.argmax(row_totals / tf.sum())
        elif isinstance(start, int):
            _start = start if start < len(states) else len(states)-1
        elif start == 'random':
            _start = np.random.randint(0, len(states))
        elif isinstance(start, str):
            _start = np.argwhere(states == start).item()

        # simulated sequence init
        seq = np.zeros(n, dtype=int)
        seq[0] = _start

        # random seeds
        r_states = np.random.randint(0, n, n) if seed is None else seed

        # simulation procedure
        for i in range(1, n):
            _ps = fp[seq[i-1]]
            _sample = np.argmax(
                ss.multinomial.rvs(1, _ps, 1, random_state=r_states[i])
            )
            seq[i] = _sample

        if ret == 'indices':
            return seq
        elif ret == 'states':
            return states[seq]
        else:
            return seq, states[seq]


class MarkovChainFirstLevel(MarkovChain):
    def build_transition_model(self, data, transitions):
        model = OrderedDict()
        model[self.prev_state] = {'count':0}
        for open_type_code in open_type_codes:
            model[open_type_code] = {'count':0}
            model[self.prev_state][open_type_code] = 0
        for tpo in range(1,14):
            for step in intermediate_steps:
                for mov in ['F', 'R']:
                    model[str(tpo) + "_" + step + "_" + mov] = {'count': 0}
        for (day, features) in data.items():
            model[self.prev_state]['count'] += 1
            model[features['open_type']]['count'] += 1
            model[self.prev_state][features['open_type']] += 1

            transition_list = features[transitions]
            for idx in range(len(transition_list) - 1):
                state = transition_list[idx]
                follow = transition_list[idx + 1]
                if not idx:
                    if state not in model[features['open_type']]:
                        model[features['open_type']][state] = 0
                    model[features['open_type']][state] += 1
                if state != follow:
                    if follow not in model[state]:
                        model[state][follow] = 0
                    model[state]['count'] += 1
                    model[state][follow] += 1
        self.model = model

    def calc_transition_freq(self):
        self.states = np.array(list(self.model.keys()))
        self.observed_matrix = np.zeros((len(self.states), len(self.states)))
        self.observed_p_matrix = np.zeros((len(self.states), len(self.states)))
        for x in range(len(self.states)):
            xid = np.argwhere(self.states == self.states[x]).flatten()
            transitions = self.model[self.states[x]]
            for to_state in list(transitions.keys()):
                yid = np.argwhere(self.states == to_state).flatten()
                cnt = transitions[to_state]
                self.observed_matrix[xid, yid] = cnt
                self.observed_p_matrix[xid, yid] = transitions['count'] and cnt/transitions['count'] or 0


    def from_data(self, data, transitions='transitions'):
        # states list
        self.build_transition_model(data, transitions)
        self.calc_transition_freq()
        #self.observed_matrix = self.calc_transition_freq()
        #self._obs_row_totals = np.sum(self.observed_matrix, axis=1)
        # observed transition probability matrix
        #self.observed_p_matrix = np.nan_to_num(self.observed_matrix / self._obs_row_totals[:, None])
        # filling in a row containing zeros with uniform p values
        uniform_p = 1 / len(self.states)
        zero_row = np.argwhere(self.observed_p_matrix.sum(1) == 0).ravel()
        #self.observed_p_matrix[zero_row, :] = uniform_p
        # expected transition frequency matrix
        self.expected_matrix = ss.contingency.expected_freq(self.observed_matrix)


class MarkovChainTPO(MarkovChain):
    def build_transition_model(self, data, transitions):
        model = OrderedDict()
        model[self.prev_state] = {'count':0}
        for open_type_code in open_type_codes:
            model[open_type_code] = {'count':0}
            model[self.prev_state][open_type_code] = 0
        for tpo in range(1,14):
            for step in intermediate_steps:
                for mov in ['F', 'R']:
                    model[str(tpo) + "_" + step + "_" + mov] = {'count': 0}
        for (day, features) in data.items():
            model[self.prev_state]['count'] += 1
            model[features['open_type']]['count'] += 1
            model[self.prev_state][features['open_type']] += 1

            transition_list = features[transitions]
            for idx in range(len(transition_list) - 1):
                state = transition_list[idx]
                follow = transition_list[idx + 1]
                if not idx:
                    if state not in model[features['open_type']]:
                        model[features['open_type']][state] = 0
                    model[features['open_type']][state] += 1
                if state != follow:
                    if follow not in model[state]:
                        model[state][follow] = 0
                    model[state]['count'] += 1
                    model[state][follow] += 1
        self.model = model
    def build_transition_model(self, data, transitions):
        model = OrderedDict()
        model[self.prev_state] = {'count':0}
        for open_type_code in open_type_codes:
            model[open_type_code] = {'count':0}
            model[self.prev_state][open_type_code] = 0
        for (day, features) in data.items():
            model[self.prev_state]['count'] += 1
            model[features['open_type']]['count'] += 1
            model[self.prev_state][features['open_type']] += 1

            transition_list = features[transitions]
            for idx in range(len(transition_list) - 1):
                state = transition_list[idx]
                follow = transition_list[idx + 1]
                if state != follow:
                    if state not in model[features['open_type']]:
                        model[features['open_type']][state] = 0
                    model[features['open_type']][state] += 1
                    if state not in model:
                        model[state] = {}
                    if follow not in model[state]:
                        model[state][follow] = 0
                    model[state][follow] += 1
        self.model = model

    def calc_transition_freq(self):
        self.states = np.array(list(self.model.keys()))
        self.observed_matrix = np.zeros((len(self.states), len(self.states)))
        self.observed_p_matrix = np.zeros((len(self.states), len(self.states)))
        for x in range(len(self.states)):
            xid = np.argwhere(self.states == self.states[x]).flatten()
            transitions = self.model[self.states[x]]
            for to_state in list(transitions.keys()):
                yid = np.argwhere(self.states == to_state).flatten()
                cnt = transitions[to_state]
                self.observed_matrix[xid, yid] = cnt
                self.observed_p_matrix[xid, yid] = transitions['count'] and cnt/transitions['count'] or 0


    def from_data(self, data, transitions='transitions'):
        # states list
        self.build_first_level_model(data, transitions)
        self.calc_transition_freq()
        #self.observed_matrix = self.calc_transition_freq()
        #self._obs_row_totals = np.sum(self.observed_matrix, axis=1)
        # observed transition probability matrix
        #self.observed_p_matrix = np.nan_to_num(self.observed_matrix / self._obs_row_totals[:, None])
        # filling in a row containing zeros with uniform p values
        uniform_p = 1 / len(self.states)
        zero_row = np.argwhere(self.observed_p_matrix.sum(1) == 0).ravel()
        #self.observed_p_matrix[zero_row, :] = uniform_p
        # expected transition frequency matrix
        self.expected_matrix = ss.contingency.expected_freq(self.observed_matrix)