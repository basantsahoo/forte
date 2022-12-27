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
from sklearn.tree import DecisionTreeClassifier, DecisionTreeRegressor
from sklearn.inspection import DecisionBoundaryDisplay
import matplotlib.pyplot as plt

from analysis.build_features import (
    NumericProcessor,
    CategoricalProcessor,
    MultiColumnLabelEncoder
)
from analysis.utils import WeightedGBM
from settings import models_dir, reports_dir
from sklearn.metrics import accuracy_score,classification_report,confusion_matrix, plot_roc_curve, PrecisionRecallDisplay
from sklearn.model_selection import train_test_split
import graphviz
from sklearn.inspection import DecisionBoundaryDisplay,permutation_importance
from sklearn.preprocessing import OrdinalEncoder, OneHotEncoder
from sklearn.compose import make_column_transformer
from sklearn.ensemble import  GradientBoostingRegressor
from sklearn.svm import SVR
from sklearn.metrics import mean_squared_error, mean_absolute_error, explained_variance_score, r2_score
from sklearn.metrics import mean_poisson_deviance, mean_gamma_deviance, accuracy_score
from sklearn.preprocessing import MinMaxScaler
import math

def pre_process(x_input):
    open_type_order = ['GAP_UP','ABOVE_VA','INSIDE_VA','BELOW_VA','GAP_DOWN']
    #x_input['open_type'] = ordinal_encoder(categories=[open_type_order]).fit_transform(x_input['open_type'])
    cat_transformer = make_column_transformer(
        (OrdinalEncoder(categories=[open_type_order], handle_unknown="use_encoded_value", unknown_value=np.nan), ['open_type']),
        (OneHotEncoder(), ['week_day']),
        (OneHotEncoder(), ['strategy']),
        remainder="drop"
    ) if 'strategy' in x_input.columns.tolist() else make_column_transformer(
        (OrdinalEncoder(categories=[open_type_order], handle_unknown="use_encoded_value", unknown_value=np.nan), ['open_type']),
        (OneHotEncoder(), ['week_day']),
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
        ('open_type', cat_transformer),

    ])
    preprocessor = Pipeline([('union', feature_union)])
    X = preprocessor.fit_transform(x_input)
    feature_names = preprocessor.named_steps['union'].get_feature_names_out()

    feature_names = [x.split('__')[-1] for x in feature_names]
    #print(feature_names)
    #print(len(list(set(feature_names))))
    #print(X.T)
    df = pd.DataFrame(X, columns=feature_names)

    """
    if 'strategy' in df.columns.tolist():
        del df['strategy']
    """
    return df

n_estimators = 100
def train_gbm_model(x_input, y_input):
    pre_processed_x = pre_process(x_input)
    #print(pre_processed_x.T)
    pipeline = Pipeline([('clf', GradientBoostingRegressor(random_state=398))])
    pipeline.set_params(clf__n_estimators=n_estimators, clf__max_depth=2,
                        clf__min_samples_split=10,
                        clf__learning_rate = 0.05,
                        clf__loss = "quantile")
    pipeline.fit(pre_processed_x, y_input)

    imp = pd.DataFrame()
    imp['feature'] = pre_processed_x.columns.tolist()
    imp['importance'] = pipeline.named_steps['clf'].feature_importances_
    imp.to_csv(os.path.join(models_dir, "FeatImp_Model_gbm.csv"))
    return pipeline

def train_svr_model(x_input, y_input):
    pre_processed_x = pre_process(x_input)
    pipeline = Pipeline([('clf', SVR(kernel="rbf", C=100, gamma=0.1, epsilon=0.1))])
    pipeline.fit(pre_processed_x, y_input)

    return pipeline


def train_decission_tree(x_input, y_input):
    pre_processed_x = pre_process(x_input)
    pipeline = Pipeline([('clf', DecisionTreeRegressor(random_state=0, max_depth=10))])
    pipeline.fit(pre_processed_x, y_input)

    plt.figure()
    tree.plot_tree(pipeline.named_steps['clf'], filled=True)
    plt.title("Decision tree trained on all the iris features")
    plt.show()

    dot_data = tree.export_graphviz(pipeline.named_steps['clf'], feature_names=pre_processed_x.columns, out_file=None)
    graph = graphviz.Source(dot_data)
    graph.view()
    return pipeline

def print_measures(pipeline, X_test, y_test, title=None):
    X_test = pre_process(X_test)
    test_score = np.zeros((n_estimators,), dtype=np.float64)
    for i, y_pred in enumerate(pipeline.named_steps['clf'].staged_predict(X_test)):
        test_score[i] = pipeline.named_steps['clf'].loss_(y_test, y_pred)

    fig = plt.figure(figsize=(6, 6))
    plt.subplot(1, 1, 1)
    plt.title("Deviance")
    plt.plot(
        np.arange(n_estimators) + 1,
        pipeline.named_steps['clf'].train_score_,
        "b-",
        label="Training Set Deviance",
    )
    plt.plot(
        np.arange(n_estimators) + 1, test_score, "r-", label="Test Set Deviance"
    )
    plt.legend(loc="upper right")
    plt.xlabel("Boosting Iterations")
    plt.ylabel("Deviance")
    if title is not None:
        plt.title(title)
    fig.tight_layout()
    plt.show()

    feature_importance = pipeline.named_steps['clf'].feature_importances_
    sorted_idx = np.argsort(feature_importance)
    pos = np.arange(sorted_idx.shape[0]) + 0.5
    fig = plt.figure(figsize=(12, 6))
    plt.subplot(1, 2, 1)
    plt.barh(pos, feature_importance[sorted_idx], align="center")
    plt.yticks(pos, np.array(X_test.columns.tolist())[sorted_idx])
    plt.title("Feature Importance (MDI)")

    result = permutation_importance(
        pipeline, X_test, y_test, n_repeats=10, random_state=42, n_jobs=2
    )
    sorted_idx = result.importances_mean.argsort()
    plt.subplot(1, 2, 2)
    plt.boxplot(
        result.importances[sorted_idx].T,
        vert=False,
        labels=np.array(X_test.columns.tolist())[sorted_idx],
    )
    plt.title("Permutation Importance (test set)")
    fig.tight_layout()
    plt.show()

def print_measures_2(pipeline, X_train, y_train, X_test, y_test):
    X_train = pre_process(X_train)
    X_test = pre_process(X_test)
    train_predict = pipeline.predict(X_train)
    test_predict = pipeline.predict(X_test)

    train_predict = train_predict.reshape(-1, 1)
    test_predict = test_predict.reshape(-1, 1)

    original_ytrain = y_train
    original_ytest = y_test

    print("Train data RMSE: ", math.sqrt(mean_squared_error(original_ytrain, train_predict)))
    print("Test data RMSE: ", math.sqrt(mean_squared_error(original_ytest, test_predict)))
    print("Train data MSE: ", mean_squared_error(original_ytrain, train_predict))
    print("Test data MSE: ", mean_squared_error(original_ytest, test_predict))
    print("Test data MAE: ", mean_absolute_error(original_ytrain, train_predict))
    print("Test data MAE: ", mean_absolute_error(original_ytest, test_predict))
    print("Train data explained variance regression score:", explained_variance_score(original_ytrain, train_predict))
    print("Test data explained variance regression score:", explained_variance_score(original_ytest, test_predict))
    print("Train data R2 score:", r2_score(original_ytrain, train_predict))
    print("Test data R2 score:", r2_score(original_ytest, test_predict))
    print("Train data MGD: ", mean_gamma_deviance(original_ytrain, train_predict))
    print("Test data MGD: ", mean_gamma_deviance(original_ytest, test_predict))
    print("----------------------------------------------------------------------")
    print("Train data MPD: ", mean_poisson_deviance(original_ytrain, train_predict))
    print("Test data MPD: ", mean_poisson_deviance(original_ytest, test_predict))
    #https://www.kaggle.com/code/ysthehurricane/advanced-stock-pred-using-svr-rfr-knn-lstm-gru/notebook#svrevalmat


def train(data_set, target, exclude_variables=[]):
    strategy = data_set['strategy'].tolist()[0]
    data_set = data_set.dropna(subset=['tpo'])
    data_set = data_set[data_set[target] > 0]
    y_input = data_set[target]
    x_input = data_set.drop(target, axis=1)
    cols = ['week_day','open_type','tpo','first_hour_trend','whole_day_trend','candles_in_range']
    cols =  [x for x in x_input.columns if x not in exclude_variables]
    x_input = x_input[cols]
    X_train, X_test, y_train, y_test = train_test_split(x_input, y_input, test_size=0.3, random_state=42)
    #model = train_decission_tree(X_train, y_train)
    #print(X_train.iloc[5:8,:].head().T)
    model = train_gbm_model(X_train, y_train)
    #model = train_svr_model(X_train, y_train)
    print_measures_2(model, X_train, y_train, X_test, y_test)
    print_measures(model,X_test, y_test, strategy)
    #plot_surface(X_train, y_train)

    # tier -1
    #CDL3OUTSIDE_5_BUY_15
    #CDL3OUTSIDE_5_BUY_20
    #CDL3OUTSIDE_5_BUY_30
    #CDL3OUTSIDE_5_SELL_20
    #CDL3OUTSIDE_15_SELL_30
    #CDLXSIDEGAP3METHODS_5_BUY_15
    #CDLXSIDEGAP3METHODS_5_BUY_30


    #tier -2
    #CDLENGULFING_15_BUY_15
    #CDLENGULFING_5_SELL_20
    #CDLENGULFING_5_SELL_30
    #CDL3OUTSIDE_5_SELL_30
    #CDL3OUTSIDE_15_SELL_15
    #CDL3OUTSIDE_15_BUY_10
