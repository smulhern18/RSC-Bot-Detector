import json
import math
import os
import threading
from concurrent.futures.thread import ThreadPoolExecutor

import strconv
from sklearn.naive_bayes import GaussianNB
from scipy.optimize import least_squares

from spotter import extract_dissimilarity


def train(training_file_name: str, testing_file_name: str):
    user_map = get_bot_file()
    print("done reading in the botfile")

    training_timestamps = read_json_file(training_file_name, user_map)
    training_target = []
    training_features = []
    to_remove = []
    for username in training_timestamps:
        timestamps = training_timestamps[username]
        if len(timestamps) == 0:
            to_remove.append(username)
        else:
            is_bot = user_map[username]
            training_target.append(is_bot)

    print("done sorting training file")

    # optimizer Portion
    # function to use: spotter.extract_dissimilarity
    # needs timestamps, rsc parameters, and num of bins
    param_guess = [0.4, 0.4, 0.6, 0.5, 1.1, 2.5, 5, 8 / 24]
    result = optimizer_function(rsc_parameters=param_guess, timestamps=training_timestamps.values(), num_bins=10)

    print("done with optimizer")

    testing_timestamps = read_json_file(testing_file_name, user_map)
    testing_target = []
    testing_features = []
    to_remove = []
    for username in testing_timestamps:
        timestamps = testing_timestamps[username]
        if len(timestamps) == 0:
            to_remove.append(username)
        else:
            is_bot = user_map[username]
            testing_target.append(is_bot)

    print("done sorting testing file")

    for username, timestamps in training_timestamps:
        training_features.append(extract_dissimilarity(result, timestamps, 30))

    for username, timestamps in testing_timestamps:
        testing_features.append(extract_dissimilarity(result, timestamps, 30))

    # classifier portion
    classifier = GaussianNB()
    classifier.fit(training_features, training_target)

    print("done fitting classifier")

    score = classifier.score(testing_features, testing_target)

    print("The accuracy of the Classifier is:", score)

    print("Params of the classifer:")

    print(classifier.get_params())

    print("Result of the Optimizer:")
    print(result)


def get_bot_file():
    bot_map = {}

    with open("botAccountList.csv", 'r') as f:
        bots = f.readlines()
        f.close()
        for i in range(len(bots)):
            bot_map[bots[i]] = 1
    return bot_map


def read_json_file(filename: str, user_map: dict):
    input_file = open(filename, 'r')
    lines = input_file.readlines()
    store_list = dict()

    for line in lines:
        item = json.loads(line)
        username: str = item["author"]
        created_utc: int = strconv.convert_int(item["created_utc"])
        if username in store_list:
            store_list[username].append(created_utc)
        else:
            store_list[username] = list()
            store_list[username].append(created_utc)

        if username not in user_map.keys():
            user_map[username] = 0

    to_remove = []

    input_file.close()

    for username in store_list:
        if len(store_list[username]) < 3:
            to_remove.append(username)

    for username in to_remove:
        store_list.pop(username)



    return store_list


def optimizer_function(rsc_parameters, timestamps, num_bins):

    average_parameters = [0.0] * 8
    all_parameters = [average_parameters] * len(timestamps)
    i = 0
    futures = []
    with ThreadPoolExecutor(max_workers=64) as e:
        for timestamp in timestamps:
            futures.append(e.submit(threading_function, rsc_parameters, timestamp, num_bins))

    print("Processing futures")
    for future in futures:
        all_parameters[i] = future.result()
        i += 1

    total_parameters = [sum(x) for x in zip(*all_parameters)]
    for i in range(len(total_parameters)):
        average_parameters[i] = total_parameters[i] / len(timestamps)

    return average_parameters


def threading_function(rsc_parameters, timestamp, num_bins):

    bounds = ([0.01, 0.01, 0.01, 0.2, 0.2, math.log10(1), math.log10(100), 0],
              [0.99, 0.99, 0.99, 10.0, 10.0, math.log10(3600), math.log10(3600 * 24 * 30), 12 / 24])

    popt = least_squares(extract_dissimilarity,
                         args=(timestamp, num_bins),
                         x0=rsc_parameters,
                         method='trf',
                         bounds=bounds,
                         verbose=0,
                         max_nfev=100)
    x: list[float] = popt.x.tolist()
    return x

if __name__ == "__main__":
    os.chdir("F:\\MQP Data\\jsonFiles")
    train("RC_2015-10.json", "RC_2015-11.json")
