#!/usr/bin/env python

"""Baseline workload 3 for Home Credit Default Risk Competition
   The code here, is the original code posted as a notebook for the Kaggle competitiong.
   The notebook can be found here: https://www.kaggle.com/willkoehrsen/introduction-to-manual-feature-engineering-p2
"""

# pandas and numpy for data manipulation
from datetime import datetime
import lightgbm as lgb
import pandas as pd
import numpy as np

# matplotlib and seaborn for plotting
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import roc_auc_score
# Suppress warnings from pandas
import warnings

from sklearn.preprocessing import LabelEncoder

warnings.filterwarnings('ignore')

plt.style.use('fivethirtyeight')


def run(root_data):
    def agg_numeric(df, parent_var, df_name):
        """
        Groups and aggregates the numeric values in a child dataframe
        by the parent variable.

        Parameters
        --------
            df (dataframe):
                the child dataframe to calculate the statistics on
            parent_var (string):
                the parent variable used for grouping and aggregating
            df_name (string):
                the variable used to rename the columns

        Return
        --------
            agg (dataframe):
                a dataframe with the statistics aggregated by the `parent_var` for
                all numeric columns. Each observation of the parent variable will have
                one row in the dataframe with the parent variable as the index.
                The columns are also renamed using the `df_name`. Columns with all duplicate
                values are removed.

        """

        # Remove id variables other than grouping variable
        for col in df:
            if col != parent_var and 'SK_ID' in col:
                df = df.drop(columns=col)

        # Only want the numeric variables
        parent_ids = df[parent_var].copy()
        numeric_df = df.select_dtypes('number').copy()
        numeric_df[parent_var] = parent_ids

        # Group by the specified variable and calculate the statistics
        agg = numeric_df.groupby(parent_var).agg(['count', 'mean', 'max', 'min', 'sum'])

        # Need to create new column names
        columns = []

        # Iterate through the variables names
        for var in agg.columns.levels[0]:
            if var != parent_var:
                # Iterate through the stat names
                for stat in agg.columns.levels[1]:
                    # Make a new column name for the variable and stat
                    columns.append('%s_%s_%s' % (df_name, var, stat))

        agg.columns = columns

        # Remove the columns with all redundant values
        _, idx = np.unique(agg, axis=1, return_index=True)
        agg = agg.iloc[:, idx]

        return agg

    def agg_categorical(df, parent_var, df_name):
        """
        Aggregates the categorical features in a child dataframe
        for each observation of the parent variable.

        Parameters
        --------
        df : dataframe
            The dataframe to calculate the value counts for.

        parent_var : string
            The variable by which to group and aggregate the dataframe. For each unique
            value of this variable, the final dataframe will have one row

        df_name : string
            Variable added to the front of column names to keep track of columns


        Return
        --------
        categorical : dataframe
            A dataframe with aggregated statistics for each observation of the parent_var
            The columns are also renamed and columns with duplicate values are removed.

        """

        # Select the categorical columns
        categorical = pd.get_dummies(df.select_dtypes('object'))

        # Make sure to put the identifying id on the column
        categorical[parent_var] = df[parent_var]

        # Groupby the group var and calculate the sum and mean
        categorical = categorical.groupby(parent_var).agg(['sum', 'count', 'mean'])

        column_names = []

        # Iterate through the columns in level 0
        for var in categorical.columns.levels[0]:
            # Iterate through the stats in level 1
            for stat in ['sum', 'count', 'mean']:
                # Make a new column name
                column_names.append('%s_%s_%s' % (df_name, var, stat))

        categorical.columns = column_names

        # Remove duplicate columns by values
        _, idx = np.unique(categorical, axis=1, return_index=True)
        categorical = categorical.iloc[:, idx]

        return categorical

    # Plots the disribution of a variable colored by value of the target
    def kde_target(var_name, df):

        # Calculate the correlation coefficient between the new variable and the target
        corr = df['TARGET'].corr(df[var_name])

        # Calculate medians for repaid vs not repaid
        avg_repaid = df.ix[df['TARGET'] == 0, var_name].median()
        avg_not_repaid = df.ix[df['TARGET'] == 1, var_name].median()

        plt.figure(figsize=(12, 6))

        # Plot the distribution for target == 0 and target == 1
        sns.kdeplot(df.ix[df['TARGET'] == 0, var_name], label='TARGET == 0')
        sns.kdeplot(df.ix[df['TARGET'] == 1, var_name], label='TARGET == 1')

        # label the plot
        plt.xlabel(var_name)
        plt.ylabel('Density')
        plt.title('%s Distribution' % var_name)
        plt.legend()

        # print out the correlation
        print('The correlation between %s and the TARGET is %0.4f' % (var_name, corr))
        # Print out average values
        print('Median value for loan that was not repaid = %0.4f' % avg_not_repaid)
        print('Median value for loan that was repaid =     %0.4f' % avg_repaid)

    import sys

    def return_size(df):
        """Return size of dataframe in gigabytes"""
        return round(sys.getsizeof(df) / 1e9, 2)

    previous = pd.read_csv(root_data + '/kaggle_home_credit/previous_application.csv')
    previous.head()

    # Calculate aggregate statistics for each numeric column
    previous_agg = agg_numeric(previous, 'SK_ID_CURR', 'previous')
    print('Previous aggregation shape: ', previous_agg.shape)
    previous_agg.head()

    # Calculate value counts for each categorical column
    previous_counts = agg_categorical(previous, 'SK_ID_CURR', 'previous')
    print('Previous counts shape: ', previous_counts.shape)
    previous_counts.head()

    train = pd.read_csv(root_data + '/kaggle_home_credit/application_train.csv')
    test = pd.read_csv(root_data + '/kaggle_home_credit/application_test.csv')

    test_labels = pd.read_csv(root_data + '/kaggle_home_credit/application_test_labels.csv')

    # Merge in the previous information
    train = train.merge(previous_counts, on='SK_ID_CURR', how='left')
    train = train.merge(previous_agg, on='SK_ID_CURR', how='left')

    test = test.merge(previous_counts, on='SK_ID_CURR', how='left')
    test = test.merge(previous_agg, on='SK_ID_CURR', how='left')

    # Function to calculate missing values by column# Funct
    def missing_values_table(df, print_info=False):
        # Total missing values
        mis_val = df.isnull().sum()

        # Percentage of missing values
        mis_val_percent = 100 * df.isnull().sum() / len(df)

        # Make a table with the results
        mis_val_table = pd.concat([mis_val, mis_val_percent], axis=1)

        # Rename the columns
        mis_val_table_ren_columns = mis_val_table.rename(
            columns={0: 'Missing Values', 1: '% of Total Values'})

        # Sort the table by percentage of missing descending
        mis_val_table_ren_columns = mis_val_table_ren_columns[
            mis_val_table_ren_columns.iloc[:, 1] != 0].sort_values(
            '% of Total Values', ascending=False).round(1)

        if print_info:
            # Print some summary information
            print ("Your selected dataframe has " + str(df.shape[1]) + " columns.\n"
                                                                       "There are " + str(
                mis_val_table_ren_columns.shape[0]) +
                   " columns that have missing values.")

        # Return the dataframe with missing information
        return mis_val_table_ren_columns

    def remove_missing_columns(train, test, threshold=90):
        # Calculate missing stats for train and test (remember to calculate a percent!)
        train_miss = pd.DataFrame(train.isnull().sum())
        train_miss['percent'] = 100 * train_miss[0] / len(train)

        test_miss = pd.DataFrame(test.isnull().sum())
        test_miss['percent'] = 100 * test_miss[0] / len(test)

        # list of missing columns for train and test
        missing_train_columns = list(train_miss.index[train_miss['percent'] > threshold])
        missing_test_columns = list(test_miss.index[test_miss['percent'] > threshold])

        # Combine the two lists together
        missing_columns = list(set(missing_train_columns + missing_test_columns))

        # Print information
        print('There are %d columns with greater than %d%% missing values.' % (len(missing_columns), threshold))

        # Drop the missing columns and return
        train = train.drop(columns=missing_columns)
        test = test.drop(columns=missing_columns)

        return train, test

    train, test = remove_missing_columns(train, test)

    def aggregate_client(df, group_vars, df_names):
        """Aggregate a dataframe with data at the loan level
        at the client level

        Args:
            df (dataframe): data at the loan level
            group_vars (list of two strings): grouping variables for the loan
            and then the client (example ['SK_ID_PREV', 'SK_ID_CURR'])
            names (list of two strings): names to call the resulting columns
            (example ['cash', 'client'])

        Returns:
            df_client (dataframe): aggregated numeric stats at the client level.
            Each client will have a single row with all the numeric data aggregated
        """

        # Aggregate the numeric columns
        df_agg = agg_numeric(df, parent_var=group_vars[0], df_name=df_names[0])

        # If there are categorical variables
        if any(df.dtypes == 'object'):

            # Count the categorical columns
            df_counts = agg_categorical(df, parent_var=group_vars[0], df_name=df_names[0])

            # Merge the numeric and categorical
            df_by_loan = df_counts.merge(df_agg, on=group_vars[0], how='outer')

            # Merge to get the client id in dataframe
            df_by_loan = df_by_loan.merge(df[[group_vars[0], group_vars[1]]], on=group_vars[0], how='left')

            # Remove the loan id
            df_by_loan = df_by_loan.drop(columns=[group_vars[0]])

            # Aggregate numeric stats by column
            df_by_client = agg_numeric(df_by_loan, parent_var=group_vars[1], df_name=df_names[1])

        # No categorical variables
        else:
            # Merge to get the client id in dataframe
            df_by_loan = df_agg.merge(df[[group_vars[0], group_vars[1]]], on=group_vars[0], how='left')

            # Remove the loan id
            df_by_loan = df_by_loan.drop(columns=[group_vars[0]])

            # Aggregate numeric stats by column
            df_by_client = agg_numeric(df_by_loan, parent_var=group_vars[1], df_name=df_names[1])

        return df_by_client

    cash = pd.read_csv(root_data + '/kaggle_home_credit/POS_CASH_balance.csv')
    cash.head()

    cash_by_client = aggregate_client(cash, group_vars=['SK_ID_PREV', 'SK_ID_CURR'], df_names=['cash', 'client'])
    cash_by_client.head()

    print 'Cash by Client Shape: '.format(cash_by_client.shape)
    train = train.merge(cash_by_client, on='SK_ID_CURR', how='left')
    test = test.merge(cash_by_client, on='SK_ID_CURR', how='left')

    train, test = remove_missing_columns(train, test)

    credit = pd.read_csv(root_data + '/kaggle_home_credit/credit_card_balance.csv')
    credit.head()

    credit_by_client = aggregate_client(credit, group_vars=['SK_ID_PREV', 'SK_ID_CURR'], df_names=['credit', 'client'])
    credit_by_client.head()

    print 'Credit by client shape: '.format(credit_by_client.shape)

    train = train.merge(credit_by_client, on='SK_ID_CURR', how='left')
    test = test.merge(credit_by_client, on='SK_ID_CURR', how='left')

    train, test = remove_missing_columns(train, test)

    installments = pd.read_csv(root_data + '/kaggle_home_credit/installments_payments.csv')
    installments.head()

    installments_by_client = aggregate_client(installments, group_vars=['SK_ID_PREV', 'SK_ID_CURR'],
                                              df_names=['installments', 'client'])
    installments_by_client.head()

    print 'Installments by client shape: '.format(installments_by_client.shape)

    train = train.merge(installments_by_client, on='SK_ID_CURR', how='left')
    test = test.merge(installments_by_client, on='SK_ID_CURR', how='left')

    train, test = remove_missing_columns(train, test)

    print 'Final Training Shape: {}'.format(train.shape)
    print 'Final Testing Shape: {}'.format(test.shape)

    print 'Final training size: {}'.format(return_size(train))
    print 'Final testing size: {}'.format(return_size(test))

    def model(features, test_features, encoding='ohe'):

        """Train and test a light gradient boosting model using
        cross validation.

        Parameters
        --------
            features (pd.DataFrame):
                dataframe of training features to use
                for training a model. Must include the TARGET column.
            test_features (pd.DataFrame):
                dataframe of testing features to use
                for making predictions with the model.
            encoding (str, default = 'ohe'):
                method for encoding categorical variables. Either 'ohe' for one-hot encoding or 'le' for integer label encoding
                n_folds (int, default = 5): number of folds to use for cross validation

        Return
        --------
            submission (pd.DataFrame):
                dataframe with `SK_ID_CURR` and `TARGET` probabilities
                predicted by the model.
            feature_importances (pd.DataFrame):
                dataframe with the feature importances from the model.
            valid_metrics (pd.DataFrame):
                dataframe with training and validation metrics (ROC AUC) for each fold and overall.

        """

        # Extract the ids
        train_ids = features['SK_ID_CURR']
        test_ids = test_features['SK_ID_CURR']

        # Extract the labels for training
        labels = features['TARGET']

        # Remove the ids and target
        features = features.drop(columns=['SK_ID_CURR', 'TARGET'])
        test_features = test_features.drop(columns=['SK_ID_CURR'])

        # One Hot Encoding
        if encoding == 'ohe':
            features = pd.get_dummies(features)
            test_features = pd.get_dummies(test_features)

            # Align the dataframes by the columns
            features, test_features = features.align(test_features, join='inner', axis=1)

            # No categorical indices to record
            cat_indices = 'auto'

        # Integer label encoding
        elif encoding == 'le':

            # Create a label encoder
            label_encoder = LabelEncoder()

            # List for storing categorical indices
            cat_indices = []

            # Iterate through each column
            for i, col in enumerate(features):
                if features[col].dtype == 'object':
                    # Map the categorical features to integers
                    features[col] = label_encoder.fit_transform(np.array(features[col].astype(str)).reshape((-1,)))
                    test_features[col] = label_encoder.transform(
                        np.array(test_features[col].astype(str)).reshape((-1,)))

                    # Record the categorical indices
                    cat_indices.append(i)

        # Catch error if label encoding scheme is not valid
        else:
            raise ValueError("Encoding must be either 'ohe' or 'le'")

        print('Training Data Shape: ', features.shape)
        print('Testing Data Shape: ', test_features.shape)

        # Extract feature names
        feature_names = list(features.columns)

        # TODO change n_estimators to 10000, he original number from the script
        model = lgb.LGBMClassifier(n_estimators=10, objective='binary',
                                   class_weight='balanced', learning_rate=0.05,
                                   reg_alpha=0.1, reg_lambda=0.1,
                                   subsample=0.8, n_jobs=-1, random_state=50)

        # Train the model
        model.fit(features, labels, eval_metric='auc',
                  categorical_feature=cat_indices,
                  verbose=200)

        # Record the best iteration
        best_iteration = model.best_iteration_
        predictions = model.predict_proba(test_features, num_iteration=best_iteration)[:, 1]
        score = roc_auc_score(test_labels['TARGET'], predictions)
        print 'LGBMClassifier with AUC score: {}'.format(score)

        feature_importance_values = model.feature_importances_

        feature_importances = pd.DataFrame({'feature': feature_names, 'importance': feature_importance_values})

        return feature_importances

    fi = model(train, test)


if __name__ == "__main__":
    execution_start = datetime.now()

    ROOT_PACKAGE_DIRECTORY = '/Users/bede01/Documents/work/phd-papers/ml-workload-optimization/code/collaborative-optimizer'
    root_data = ROOT_PACKAGE_DIRECTORY + '/data'
    run(root_data)

    execution_end = datetime.now()
    elapsed = (execution_end - execution_start).total_seconds()

    print('finished execution in {} seconds'.format(elapsed))
