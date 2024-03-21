"""
This module contains utility functions to support
other asepects of project
"""
import os
import sys
import inspect
from string import punctuation
import re
import numpy as np
from sklearn.ensemble import GradientBoostingClassifier
import sklearn.utils.class_weight as cw


def report(results, n_top=3):
    """
    Shows top n models with their parameters
    """
    for i in range(1, n_top + 1):
        candidates = np.flatnonzero(results['rank_test_score'] == i)
        for candidate in candidates:
            print("Model with rank: {0}".format(i))
            print("Mean validation score: {0:.3f} (std: {1:.3f})".format(
                results['mean_test_score'][candidate],
                results['std_test_score'][candidate]))
            print("Parameters: {0}".format(results['params'][candidate]))


class WeightedGBM(GradientBoostingClassifier):
    """
    Provides  Calss implementation to assign
    class weight during GBM fit.
    """

    def fit(self, X, y, class_weight=None):
        #print(X[0:1].T)
        """
        method overridden fit method of
        GradientBoostingClassifier
        """
        if class_weight is None:
            weights = cw.compute_class_weight('balanced', [0, 1], y)
            wts = np.ones_like(y)
            wts_train = np.column_stack((y, wts))
            for i in range(len(wts_train[:, 0])):
                if wts_train[i, 0] == 1:
                    wts_train[i, 1] = round(weights[1] / weights[0])
            fin_wts = wts_train[:, 1]
        else:
            fin_wts = class_weight
        super(WeightedGBM, self).fit(X, y, fin_wts)
        return self

