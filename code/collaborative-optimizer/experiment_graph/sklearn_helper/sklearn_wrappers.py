"""
Helper methods and classes to make conversion of scripts containing scikit learn models (or similar) to workload easier.
Current approach for fitting scikit learn models is to call 'fit_sk_model' method and pass the scikit learn model. This
creates overhead when modifying scripts. Here, we write some adapter codes, that make the APIs exactly the same as
scikit learn package and make the necessary changes inside.
"""

import lightgbm as lgb


class SimpleModel:
    def __init__(self, underlying_sk_model):
        self.underlying_sk_model = underlying_sk_model
        self.trained_node = None

    def fit(self, data):
        self.trained_node = data.fit_sk_model(self.underlying_sk_model)

    def transform(self, data):
        if self.trained_node is None:
            raise Exception('Model is not trained yet!!!')
        return self.trained_node.transform(data)

    def fit_transform(self, data):
        self.fit(data)
        return self.transform(data)


class PredictiveModel:
    def __init__(self, underlying_sk_model):
        self.underlying_sk_model = underlying_sk_model
        self.trained_node = None

    def fit(self, train, labels, custom_args=None):
        self.trained_node = train.fit_sk_model_with_labels(self.underlying_sk_model, labels, custom_args)

    def predict_proba(self, test, custom_args=None):
        return self.trained_node.predict_proba(test, custom_args)

    def score(self, test, true_labels, score_type='accuracy', custom_args=None):
        return self.trained_node.score(test, true_labels, score_type=score_type, custom_args=custom_args)

    def feature_importances(self, features):
        return self.trained_node.feature_importances(features)


class LGBMClassifier(PredictiveModel):
    def __init__(self, **args):
        PredictiveModel.__init__(self, lgb.LGBMClassifier(**args))

    def best_iteration(self):
        return self.trained_node.data().best_iteration_