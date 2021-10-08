import json
import math

from sklearn.naive_bayes import GaussianNB
from scipy.optimize import least_squares

from spotter import extract_dissimilarity


def train(training_file_name: str, testing_file_name: str):

    user_map = get_bot_file()

    training_timestamps = read_json_file(training_file_name, user_map)
    training_target = []
    training_features = []
    for username, timestamps in training_timestamps:
        is_bot = user_map[username]
        training_target.append(is_bot)

    testing_timestamps = read_json_file(testing_file_name, user_map)
    testing_target = []
    testing_features = []
    for username, timestamps in testing_timestamps:
        is_bot = user_map[username]
        testing_target.append(is_bot)

    # optimizer Portion
    # function to use: spotter.extract_dissimilarity
    # needs timestamps, rsc parameters, and num of bins
    param_guess = [0.5, 0.5, 0.5, 1.1, 2.5, 5, 8/24]
    result = optimizer_function(rsc_parameters=param_guess, timestamps=training_timestamps, num_bins=30)

    for username, timestamps in training_timestamps:
        training_features.append(extract_dissimilarity(result, timestamps, 30))

    for username, timestamps in testing_timestamps:
        testing_features.append(extract_dissimilarity(result, timestamps, 30))

    # classifier portion
    classifier = GaussianNB()
    classifier.fit(training_features, training_target)

    score = classifier.score(testing_features, testing_target)

    print("The accuracy of the Classifier is:", score)


def get_bot_file():
    bot_map = {}

    with open("botAccountList.csv", 'r') as f:
        bots = f.readlines()
        f.close()
        for i in range(len(bots)):
            bot_map[bots[i]] = 1
    return bot_map


def read_json_file(filename: str, user_map: dict):

    input_file = open(filename)
    json_array = json.load(input_file)
    store_list = {}

    for item in json_array:
        username: str = item["author"]
        created_utc: int = item["created_utc"]
        if store_list[username] is not None:
            timestamps: list = store_list[username]
            timestamps.append(created_utc)
            store_list[username] = timestamps
        else:
            store_list[username] = [created_utc]

        if username not in user_map.keys():
            user_map[username] = 0

    return store_list


def optimizer_function(rsc_parameters, timestamps, num_bins):

    bounds = ([0.0, 1.0],
              [0.0, 1.0],
              [0.0, 1.0],
              [0.2, 10.0],
              [0.2, 10.0],
              [math.log10(1), math.log10(3600)],
              [math.log10(100), math.log10(3600 * 24 * 30)],
              [0, 12/24])

    average_parameters = [0] * 8
    all_parameters = [[0]*8]*len(timestamps)

    for i in range(len(timestamps)):
        result = least_squares(extract_dissimilarity,
                               args=(timestamps[i], num_bins),
                               x0=rsc_parameters,
                               method='trf',
                               bounds=bounds)
        all_parameters[i] = result.x

    total_parameters = [sum(x) for x in zip(*all_parameters)]

    for i in range(len(total_parameters)):
        average_parameters[i] = total_parameters[i]/len(timestamps)

    return average_parameters
