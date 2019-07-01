"""
The Home Credit Default Risk competition did not provide labels for the application test
and the only way of getting the score is to send the submission file.
Here, we split the training data into train/test so we can compute the ROC curve without submission
"""

from sklearn.model_selection import train_test_split
import pandas as pd

RANDOM_STATE = 151789


def split_and_store(root_data, test_size=0.2):
    app_train = pd.read_csv(root_data + '/home-credit-default-risk/original_train_test/application_train.csv')
    # app_test = pd.read_csv(root_data + '/home-credit-default-risk/original_train_test/application_test.csv')
    train, test = train_test_split(app_train, test_size=test_size, random_state=RANDOM_STATE)

    test_labels = test[['SK_ID_CURR', 'TARGET']]
    test = test.drop(columns='TARGET', inplace=False)

    train.to_csv(root_data + '/home-credit-default-risk/application_train.csv')
    test.to_csv(root_data + '/home-credit-default-risk/application_test.csv')

    test_labels.to_csv(root_data + '/home-credit-default-risk/application_test_labels.csv')


if __name__ == "__main__":
    ROOT_PACKAGE_DIRECTORY = '/Users/bede01/Documents/work/phd-papers/ml-workload-optimization/code/jupyter'
    root_data = ROOT_PACKAGE_DIRECTORY + '/data'
    split_and_store(root_data)