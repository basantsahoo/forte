"""
This module contains all methods required to
train models and score claims
"""
import os
import sys
import inspect
import logging
import pickle
import gzip
import json
import numpy as np
from time import time
import pandas as pd
from sklearn.ensemble import (
    GradientBoostingClassifier,
    ExtraTreesClassifier,
    RandomForestClassifier
)
from sklearn.model_selection import (
    GridSearchCV,
    RandomizedSearchCV,
    StratifiedKFold)

from sklearn.pipeline import (
    Pipeline,
    FeatureUnion,
    make_pipeline
)
from sklearn.linear_model import LogisticRegression
from sklearn import tree
from sklearn.tree import DecisionTreeClassifier
from sklearn.inspection import DecisionBoundaryDisplay
import matplotlib.pyplot as plt

from research.analysis.build_features import (
    NumericProcessor,
    CategoricalProcessor,
    MultiColumnLabelEncoder
)
from research.analysis.utils import WeightedGBM
from settings import models_dir, reports_dir
from sklearn.metrics import accuracy_score,classification_report,confusion_matrix, plot_roc_curve, PrecisionRecallDisplay
from sklearn.model_selection import train_test_split
import graphviz
from sklearn.inspection import DecisionBoundaryDisplay
from sklearn.preprocessing import OrdinalEncoder, OneHotEncoder
from sklearn.compose import make_column_transformer
from sklearn.svm import SVC
import numpy

def plot_roc(clf, X_test, y_test):
    plot_roc_curve(clf, X_test, y_test)
    plt.show()


def plot_surface(x_input, y_input):
    pre_processed_x = pre_process(x_input)
    #print(pre_processed_x[pre_processed_x.columns[7]])
    feature_names = pre_processed_x.columns.tolist()
    # Parameters
    plot_colors = "rb"
    col_pairs = [[x, y]  for x in range(len(pre_processed_x.columns)) for y in range(len(pre_processed_x.columns))]
    col_pairs = [z for z in col_pairs if z[0] != z[1]]
    splits = []
    y = list(range(0, len(col_pairs), 12))
    for i in range(len(y) - 1):
        x = list(np.arange(y[i], y[i + 1]))
        splits.append(x)
    splits.append(list(np.arange(y[-1], len(y))))

    for split in splits:
        for pairidx, pair in enumerate([col_pairs[index] for index in split]):
            # We only take the two corresponding features

            # transform x input first
            #print(pair)
            X = pre_processed_x[pre_processed_x.columns[pair]]

            pipeline = Pipeline([('clf', DecisionTreeClassifier(criterion="gini", max_leaf_nodes=7))])
            clf = pipeline.fit(X, y_input)
            ax = plt.subplot(3, 4, pairidx + 1)
            plt.tight_layout(h_pad=0.5, w_pad=0.5, pad=2.5)
            DecisionBoundaryDisplay.from_estimator(
                clf,
                X,
                cmap=plt.cm.RdYlBu,
                response_method="predict",
                ax=ax,
                xlabel=feature_names[pair[0]],
                ylabel=feature_names[pair[1]],
            )
            y_s = list(set(y_input))
            # Plot the training points
            X_NP = X.to_numpy()
            for i, color in zip(range(len(y_s)), plot_colors):
                idx = np.where(y_input == i)
                plt.scatter(
                    X_NP[idx, 0],
                    X_NP[idx, 1],
                    c=color,
                    label=y_s[i],
                    cmap=plt.cm.RdYlBu,
                    edgecolor="black",
                    s=15,
                )

        plt.suptitle("Decision surface of decision trees trained on pairs of features")
        plt.legend(loc="lower right", borderpad=0, handletextpad=0)
        _ = plt.axis("tight")
        plt.show()


def print_measures(pipeline, X_test, y_test):
    pre_processed_x = pre_process(X_test)
    #score = pipeline.predict_proba(pre_processed_x)[:, 1]
    y_pred = pipeline.predict(pre_processed_x)
    accuracy = accuracy_score(np.array(y_test), y_pred)
    print('accuracy=====', accuracy)
    print('classification report=====')
    print(classification_report(np.array(y_test), y_pred))
    print('confusion matrix=====')
    print(confusion_matrix(np.array(y_test), y_pred, labels=[0,1]))
    plot_roc(pipeline, pre_processed_x, y_test)
    display = PrecisionRecallDisplay.from_estimator(
        pipeline, pre_processed_x, y_test, name="LinearSVC"
    )
    display.ax_.set_title("2-class Precision-Recall curve")
    plt.show()

def print_decision_rules(rf):
    for tree_idx, est in enumerate(rf.named_steps['clf'].estimators_):
        tree = est.tree_
        assert tree.value.shape[1] == 1 # no support for multi-output

        print('TREE: {}'.format(tree_idx))

        iterator = enumerate(zip(tree.children_left, tree.children_right, tree.feature, tree.threshold, tree.value))
        for node_idx, data in iterator:
            left, right, feature, th, value = data

            # left: index of left child (if any)
            # right: index of right child (if any)
            # feature: index of the feature to check
            # th: the threshold to compare against
            # value: values associated with classes

            # for classifier, value is 0 except the index of the class to return
            class_idx = numpy.argmax(value[0])

            if left == -1 and right == -1:
                print('{} LEAF: return class={}'.format(node_idx, class_idx))
            else:
                print('{} NODE: if feature[{}] < {} then next={} else next={}'.format(node_idx, feature, th, left, right))



def train_et_bs_model(x_input, y_input):
    pre_processed_x = pre_process(x_input)
    pipeline = Pipeline([('clf', ExtraTreesClassifier(random_state=398))])
    pipeline.set_params(clf__n_estimators=100, clf__criterion='gini',
                        clf__n_jobs=3,
                        clf__class_weight="balanced")
    pipeline.fit(pre_processed_x, y_input)

    imp = pd.DataFrame()
    imp['feature'] = pre_processed_x.columns.tolist()
    imp['importance'] = pipeline.named_steps['clf'].feature_importances_
    imp.to_csv(os.path.join(models_dir, "FeatImp_Model_et_bs.csv"))
    return pipeline

def train_svc_model(x_input, y_input):
    pre_processed_x = pre_process(x_input)
    pipeline = Pipeline([('clf', SVC(kernel="rbf", C=10))])
    pipeline.fit(pre_processed_x, y_input)

    return pipeline


def train_decission_tree(x_input, y_input):
    pre_processed_x = pre_process(x_input)
    pipeline = Pipeline([('clf', DecisionTreeClassifier(criterion="gini", max_leaf_nodes=20))])
    pipeline.fit(pre_processed_x, y_input)

    plt.figure()
    tree.plot_tree(pipeline.named_steps['clf'], filled=True)
    plt.title("Decision tree trained on all the iris features")
    plt.show()

    dot_data = tree.export_graphviz(pipeline.named_steps['clf'], feature_names=pre_processed_x.columns, out_file=None)
    graph = graphviz.Source(dot_data)
    graph.view()
    return pipeline

def pre_process(x_input):
    """
    If you get exception because of adding new categorical variable, check build feature that it's added as categorical
    other wise variable will be processed as bot cat and numeric
    :param x_input:
    :return:
    """
    open_type_order = ['GAP_UP','ABOVE_VA','INSIDE_VA','BELOW_VA','GAP_DOWN']
    money_ness_order = ['OTM7', 'OTM6', 'OTM5', 'OTM4', 'OTM3', 'OTM2', 'OTM1', 'ATM0', 'ITM1', 'ITM2', 'ITM3','ITM4']
    money_ness_order = ['OTM_10', 'OTM_9', 'OTM_8', 'OTM_7', 'OTM_6', 'OTM_5', 'OTM_4', 'OTM_3', 'OTM_2', 'OTM_1', 'ATM_0', 'ITM_1', 'ITM_2', 'ITM_3','ITM_4', 'ITM_5', 'ITM_6']

    #x_input['open_type'] = ordinal_encoder(categories=[open_type_order]).fit_transform(x_input['open_type'])
    cat_transformer = make_column_transformer(
        (OrdinalEncoder(categories=[open_type_order], handle_unknown="use_encoded_value", unknown_value=np.nan), ['open_type']),
        #(OrdinalEncoder(categories=[money_ness_order], handle_unknown="use_encoded_value", unknown_value=np.nan), ['money_ness']),
        (OneHotEncoder(), ['week_day']),
        (OneHotEncoder(), ['kind']),
        #(OneHotEncoder(), ['money_ness']),
        remainder="drop"
    )

    """
        feature_union = FeatureUnion(transformer_list=[
        ('open_type', make_pipeline(Columns(names==['open_type']),OrdinalEncoder(categories=[open_type_order], handle_unknown="use_encoded_value", unknown_value=np.nan))),
        ('numprocessor', NumericProcessor()),
    ])

    """
    feature_union = FeatureUnion(transformer_list=[
        ('numprocessor', NumericProcessor()),
        #('open_type', cat_transformer),
    ])
    preprocessor = Pipeline([('union', feature_union)])
    X = preprocessor.fit_transform(x_input)
    feature_names = preprocessor.named_steps['union'].get_feature_names_out()

    feature_names = [x.split('__')[-1] for x in feature_names]
    df = pd.DataFrame(X, columns=feature_names)
    return df


def evaluate_features(x_input, y_input):
    print('feature evaluation=========================')
    pre_processed_x = pre_process(x_input)
    print('raw data shape ', pre_processed_x.shape)
    pipeline = Pipeline([('clf', DecisionTreeClassifier(criterion="gini", max_leaf_nodes=20))])
    pipeline.fit(pre_processed_x, y_input)

    from sklearn.feature_selection import SequentialFeatureSelector
    from sklearn.neighbors import KNeighborsClassifier
    #knn = KNeighborsClassifier(n_neighbors=3)
    pipeline = Pipeline([('clf', ExtraTreesClassifier(random_state=398))])
    pipeline.set_params(clf__n_estimators=8, clf__criterion='gini',
                        clf__n_jobs=3,
                        )
    #pipeline.fit(pre_processed_x, y_input)

    classifier = ExtraTreesClassifier(random_state=398, n_estimators=8)
    #classifier.fit(pre_processed_x, y_input)

    sfs = SequentialFeatureSelector(classifier, n_features_to_select=20, direction="backward")
    sfs.fit(pre_processed_x, y_input)
    feature_selection_ = sfs.get_support(True)
    print(feature_selection_)
    features = np.array(pre_processed_x.columns.tolist())
    #selected_features = [features[idx] for idx, val in enumerate(feature_selection_) if val]
    selected_features = [features[sfs.get_support()]]
    print('important features ======', selected_features)


def train(data_set, target, exclude_variables=[]):
    if 'tpo' in data_set.columns.to_list():
        data_set = data_set.dropna(subset=['tpo'])

    data_set[target] = data_set[target].apply(lambda x : int(x > 0))
    y_input = data_set[target]
    x_input = data_set.drop(target, axis=1)
    other_variables = ['money_ness']
    cols =  [x for x in x_input.columns if x not in exclude_variables and x not in other_variables]
    x_input = x_input[cols]
    train_size = int(x_input.shape[0] * 0.66)
    X_train, X_test = x_input[0:train_size], x_input[train_size:x_input.shape[0]]
    y_train, y_test = y_input[0:train_size], y_input[train_size:len(y_input)]
    #print(list(X_train['money_ness'].unique()).sort())
    #print(list(X_test['money_ness'].unique()).sort())
    #X_train.fillna(X_train.mean(), inplace=True)
    #X_test.fillna(X_train.mean(), inplace=True)
    #X_train.to_csv('X_train.csv')

    #print(X_train)
    #X_train, X_test, y_train, y_test = train_test_split(x_input, y_input, test_size=0.33, random_state=42)

    #print(X_train.columns[X_train.isna().any()].tolist())
    #print(X_train.columns[X_train.isnull().any()])
    #print(X_train[X_train == np.inf])

    #print(X_train.shape)
    #evaluate_features(X_train, y_train)
    #model = train_svc_model(X_train, y_train)

    print(X_test.tail())
    model = train_et_bs_model(X_train, y_train)
    #model = train_et_bs_model(X_test, y_test)

    print_measures(model,X_test, y_test)

    #model = train_decission_tree(X_train, y_train)
    #print_decision_rules(model)
    #plot_surface(X_train, y_train)
