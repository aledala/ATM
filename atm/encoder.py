from __future__ import division, unicode_literals

from builtins import object

import numpy as np
import pandas as pd
from sklearn.preprocessing import LabelEncoder, OneHotEncoder


class MetaData(object):
    def __init__(self, class_column, train_path, test_path=None):
        """
        Compute a bunch of metadata about the dataset.

        class_column: name of dataframe column containing labels
        data_paths: paths to csvs with the same columns
        """
        data = pd.read_csv(train_path)
        if test_path is not None:
            data = data.append(pd.read_csv(test_path))

        # compute the portion of labels that are the most common value
        counts = data[class_column].value_counts()
        total_features = data.shape[1] - 1
        for c in data.columns:
            if data[c].dtype == 'object':
                total_features += len(np.unique(data[c])) - 1

        majority_percentage = float(max(counts)) / float(sum(counts))

        self.n_examples = data.shape[0]
        self.d_features = total_features
        self.k_classes = len(np.unique(data[class_column]))
        self.majority = majority_percentage
        self.size = int(np.array(data).nbytes / 1000)


class DataEncoder(object):
    def __init__(self, class_column='class', feature_columns=None):
        self.class_column = class_column
        self.feature_columns = feature_columns

        # these will be trained with fit_encoders()
        self.column_encoders = {}
        self.feature_encoder = None
        self.label_encoder = None

    def fit(self, data):
        """
        Fit one-hot encoders for categorical features and an integer encoder for
        the label. These can be used later to transform raw data into a form
        that ATM can work with.

        data: pd.DataFrame of unprocessed data
        """
        if self.class_column not in data.columns:
            raise KeyError('Class column "%s" not found in dataset!' %
                           self.class_column)

        self.categorical_columns = []
        if self.feature_columns is None:
            X = data.drop([self.class_column], axis=1)
            self.feature_columns = X.columns
        else:
            X = data[self.feature_columns]

        # encode categorical columns, leave ordinal values alone
        for column in X.columns:
            if X[column].dtype == 'object':
                # save the indices of categorical columns for one-hot encoding
                self.categorical_columns.append(X.columns.get_loc(column))

                # encode each feature as an integer in range(unique_vals)
                le = LabelEncoder()
                X[column] = le.fit_transform(X[column])
                self.column_encoders[column] = le

        # One-hot encode the whole feature matrix.
        # Set sparse to False so that we can test for NaNs in the output
        if self.categorical_columns:
            self.feature_encoder = OneHotEncoder(
                categorical_features=self.categorical_columns,
                sparse=False
            )
            self.feature_encoder.fit(X)

        # Train an encoder for the label as well
        labels = np.array(data[[self.class_column]])
        self.label_encoder = LabelEncoder()
        self.label_encoder.fit(labels)

    def transform(self, data):
        """
        Convert a DataFrame of labeled data to a feature matrix in the form
        that ATM can use.
        """
        if self.class_column in data:
            # pull labels into a separate series and transform them to integers
            labels = np.array(data[[self.class_column]])
            y = self.label_encoder.transform(labels)
            # drop the label column and transform the remaining features
        else:
            y = None

        X = data[self.feature_columns]

        # one-hot encode the categorical X
        if self.categorical_columns:

            # encode each categorical feature as an integer
            for column, encoder in list(self.column_encoders.items()):
                X[column] = encoder.transform(X[column])

            X = self.feature_encoder.transform(X)

        else:
            X = X.values

        return X, y

    def fit_transform(self, data):
        """ Process data into a form that ATM can use. """
        self.fit(data)
        return self.transform(data)
