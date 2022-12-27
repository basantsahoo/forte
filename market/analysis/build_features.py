"""
This module contains classes and methods used in
preprocessing and vectorization
"""
import os
import sys
import inspect
import pickle
import gzip
import bisect
import pandas as pd
from sklearn.base import BaseEstimator
from sklearn.preprocessing import LabelEncoder

# Categorical variables with numerical label
#CAT_NUM_LABEL = ['tpo']
CAT_NUM_LABEL = []

# Categorical variables with text label
CAT_TXT_LABEL = ['week_day','open_type', 'strategy']

# High dimensional categorical variables
CAT_HIGH_DIM = []

# Continuous variables to be filled with 0 for missing data
NUM_VAR_ZERO_FILL = []

# Continuous variables to be filled with median for missing data

NUM_VAR_MEDIAN_FILL = []


class NumericProcessor(BaseEstimator):
    """
    Preprocessor class implementaion for sklearn.pipeline
    Used to preprocess structured data and format text data
    """

    def __init__(self):
        """
        init method of the estimator
        """
        self.feature_list = []
        self.train_df = pd.DataFrame()

    def get_feature_names_out(self, input_features):
        return self.get_feature_names()

    def get_feature_names(self):
        """
        Returns name of the features
        """
        return self.feature_list

    def get_median_dict(self):
        """
        Calculates the medians for variables NUM_VAR_MEDIAN_FILL
        and returns a dict contating the median values
        """
        median_dict = {}
        for var in NUM_VAR_MEDIAN_FILL:
            median_value = self.train_df[var].dropna().median()
            median_dict[var] = median_value
        return median_dict

    def convert_highdimensional_tonum(self, feat):
        """
        Converts high dimensional categorical variables to numeric values
        Creates numeric value for different labels using frequency
        returns a dictionary with label:frequency pair
        """

        train_df = self.train_df.copy()
        train_df['Count'] = 1
        temp_df = train_df[[feat, 'Count']].copy()
        temp_grp_df = temp_df.groupby([feat]).sum().stack()
        temp_grp_df = temp_grp_df.unstack()
        sorted_temp_grp_df = temp_grp_df.sort_values(['Count'],
                                                     ascending=[False])
        sorted_temp_grp_df = sorted_temp_grp_df.reset_index()
        sorted_temp_grp_df['Total'] = sorted_temp_grp_df['Count'].sum()
        sorted_temp_grp_df['Frequency'] = \
            sorted_temp_grp_df['Count'] / sorted_temp_grp_df['Total']
        feat_dict = dict(zip(sorted_temp_grp_df[feat],
                             sorted_temp_grp_df['Frequency']))
        return feat_dict

    def get_processed_data(self, raw_df_input):

        """
        Treat  missing data
        Create any derived variables from raw variables
        Format the data and create dummy variables
        Parameters : Dataframe containing raw variables
        Returns : Dataframe containing processed
                and text variables
        """
        raw_df = raw_df_input.copy()
        raw_df = raw_df.reset_index(drop=True)
        cat_vars = CAT_NUM_LABEL + CAT_TXT_LABEL
        cont_vars = [ x for x in raw_df.columns.tolist() if x not in cat_vars]
        raw_df[cont_vars] = raw_df[cont_vars].fillna(-100)
        selected_df = raw_df[cont_vars]
        self.feature_list = selected_df.columns.tolist()
        return selected_df

    def fit(self, X, y=None):
        """
        fit method of the estimator
        """
        return self

    def transform(self, X):
        """
        transform method of the estimator
        """
        return self.get_processed_data(X)


class MultiColumnLabelEncoder(BaseEstimator):
    """
    CatPrepocessor class implementaion for sklearn.pipeline
    Used to process categorical variables
    """

    def __init__(self):
        """
        init method of the estimator
        """
        self.feature_list = []

    def get_feature_names(self):
        """
        Returns name of the features
        """
        return self.feature_list

    def fit(self, X, y=None):
        """
        fit method of the estimator
        """
        return self

    def transform(self, X):
        #print('MultiColumnLabelEncoder+++++++++++++++')
        """
        transform method of the estimator
        """
        final_cat_num_cols = list(X.columns.intersection(set(CAT_NUM_LABEL)))
        final_cat_txt_cols = list(X.columns.intersection(set(CAT_TXT_LABEL)))
        cat_df = X[final_cat_num_cols + final_cat_txt_cols].copy()
        cat_df.update(cat_df[final_cat_num_cols].fillna(-1))
        cat_df[final_cat_num_cols] = cat_df[final_cat_num_cols].astype(int)
        cat_df.update(cat_df[final_cat_txt_cols].fillna('UKN'))
        cat_df[final_cat_txt_cols] = cat_df[final_cat_txt_cols].astype(str)

        for colname in final_cat_num_cols:
            le = LabelEncoder().fit(X[colname])
            le_classes = le.classes_.tolist()
            print(le_classes)
            if -1 not in le.classes_:
                bisect.insort_left(le_classes, -1)
                le.classes_ = le_classes
            cat_df[colname] = cat_df[colname].map(lambda s: -1 if s not in le.classes_ else s)
            cat_df[colname] = le.transform(cat_df[colname])

        for colname in final_cat_txt_cols:
            le = LabelEncoder().fit(X[colname].astype(str))
            le_classes = le.classes_.tolist()
            print(le_classes)
            if 'UKN' not in le.classes_:
                bisect.insort_left(le_classes, 'UKN')
                le.classes_ = le_classes
            cat_df[colname] = cat_df[colname].map(lambda s: 'UKN' if s not in le.classes_ else s)
            cat_df[colname] = le.transform(cat_df[colname])
            #print(cat_df[colname].unique())
        self.feature_list = cat_df.columns.tolist()
        #print(cat_df.head())
        return cat_df


class CategoricalProcessor(BaseEstimator):
    """
    CatPrepocessor class implementaion for sklearn.pipeline
    Used to process categorical variables
    """

    def __init__(self):
        """
        init method of the estimator
        """
        self.train_df = pd.DataFrame()
        self.train_df.update(self.train_df[CAT_NUM_LABEL].fillna(-1))
        self.train_df.update(self.train_df[CAT_TXT_LABEL].fillna('-1'))
        self.feature_list = []

    def get_feature_names(self):
        """
        Returns name of the features
        """
        return self.feature_list

    def fit(self, X, y=None):
        """
        fit method of the estimator
        """
        return self

    def transform(self, X):
        """
        transform method of the estimator
        """
        cat_vars = CAT_NUM_LABEL + CAT_TXT_LABEL
        cat_df = X[cat_vars].copy()
        cat_df = cat_df.astype(object)
        cat_df_train = self.train_df[cat_vars].copy()
        cat_df_train = cat_df_train.astype(object)
        cat_df_train = pd.get_dummies(cat_df_train, prefix=cat_vars,
                                      columns=cat_vars, dummy_na=False)
        cat_df = pd.get_dummies(cat_df, prefix=cat_vars,
                                columns=cat_vars, dummy_na=False)
        # Remove trailing '.0 ' from variable names to handle any
        # unexpected data format in unseen data
        for col in cat_df_train.columns.values.tolist():
            if col[-2:] == '.0':
                cat_df_train = cat_df_train.rename(columns={col: col[:-2]})

        for col in cat_df.columns.values.tolist():
            if col[-2:] == '.0':
                cat_df = cat_df.rename(columns={col: col[:-2]})
        # final_var_list = cat_df_train.columns.tolist()
        missing_vars = list(set(FINAL_DUMMY_VAR_LIST) -
                            set(cat_df.columns.values.tolist()))
        if len(missing_vars) > 0:
            cat_df[missing_vars] = pd.DataFrame([[0 for var in missing_vars]],
                                                index=cat_df.index)
        self.feature_list = FINAL_DUMMY_VAR_LIST
        return cat_df[FINAL_DUMMY_VAR_LIST]
