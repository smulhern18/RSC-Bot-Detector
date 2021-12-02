import concurrent.futures
import json
import math
import os
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
    to_remove = []
    for username in training_timestamps:
        timestamps = training_timestamps[username]
        if len(timestamps) == 0:
            to_remove.append(username)
        else:
            is_bot = user_map[username]
            training_target.append(is_bot)

    print("done sorting training file")

    testing_timestamps = read_json_file(testing_file_name, user_map)
    testing_target = []
    to_remove = []
    for username in testing_timestamps:
        timestamps = testing_timestamps[username]
        if len(timestamps) == 0:
            to_remove.append(username)
        else:
            is_bot = user_map[username]
            testing_target.append(is_bot)

    print("done sorting testing file")

    # optimizer Portion
    # function to use: spotter.extract_dissimilarity
    # needs timestamps, rsc parameters, and num of bins
    param_guess = [0.4, 0.4, 0.6, 0.5, 1.1, 2.5, 5, 8 / 24]
    result = optimizer_function(rsc_parameters=param_guess, timestamps=list(training_timestamps.values()), num_bins=30)

    print("done with optimizer")

    trainingClassifier(result,
                       training_target,
                       testing_target,
                       training_timestamps,
                       testing_timestamps,
                       user_map)

    print(result)


def trainingClassifier(result,
                       training_target,
                       testing_target,
                       training_timestamps,
                       testing_timestamps,
                       user_map):

    training_features = []
    testing_features = []

    i = 0
    training_futures = []
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=32768)
    for username in training_timestamps:
        if i > 10000:
            break
        training_futures.append(executor.submit(extract_dissimilarity, result, training_timestamps[username], 30))
        i += 1

    for future in training_futures:
        training_features.append([future.result])

    print("done processing training dissimilarity")

    i = 0

    executor = concurrent.futures.ThreadPoolExecutor(max_workers=32768)
    testing_futures = []
    for username in testing_timestamps:
        if i > 10000:
            break
        testing_futures.append(executor.submit(extract_dissimilarity, result, testing_timestamps[username], 30))
        i += 1

    for future in testing_futures:
        testing_features.append([future.result])

    print("done processing testing dissimilarity")

    classifier = GaussianNB()
    classifier.fit(training_features, training_target)

    print("done fitting classifier")

    score = classifier.score(X=testing_features, y=testing_target)

    print("The accuracy of the Classifier is:", score)

    futures = []

    with ThreadPoolExecutor(max_workers=16384) as e:
        for i in range(len(testing_features)):
            username = testing_timestamps.keys()[i]
            dissimilarity = testing_features[i]
            is_bot = user_map[username]
            futures.append(e.submit(classifier_prediction_function, dissimilarity, is_bot, classifier))

    true_positive = 0
    true_negative = 0
    false_positive = 0
    false_negative = 0

    for future in futures:
        result = future.result()
        if result == "TP":
            true_positive += 1
        elif result == "TN":
            true_negative += 1
        elif result == "FP":
            false_positive += 1
        elif result == "FN":
            false_negative += 1
            
    print(true_positive, "true positives")
    print(true_negative, "true negatives")
    print(false_positive, "false positives")
    print(false_negative, "false negatives")

    print("Params of the classifer:")

    print(classifier.get_params())
    print(classifier.priors)

    return


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

    max_values = 256

    average_parameters = [0.0] * 8
    all_parameters = [average_parameters] * max_values
    i = 0
    futures = []
    with ThreadPoolExecutor(max_workers=256) as e:
        j = 0
        while j < max_values:
            futures.append(e.submit(threading_function, rsc_parameters, timestamps[j], num_bins))
            j += 1

    for future in futures:
        all_parameters[i] = future.result()
        i += 1

    total_parameters = [sum(x) for x in zip(*all_parameters)]
    for i in range(len(total_parameters)):
        average_parameters[i] = total_parameters[i] / max_values

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


def classifier_prediction_function(dissimilarity, truth, classifier):

    # run through the classification
    prediction = classifier.predict(dissimilarity)

    result = "TN"

    # Determine truth
    if prediction != truth and truth == 1:
        result = "FN"
    elif prediction != truth and truth == 0:
        result = "FP"
    elif truth == 1:
        result = "TP"

    return result


if __name__ == "__main__":
    os.chdir("F:\\MQP Data\\jsonFiles")
    train("RC_2015-10.json", "RC_2015-11.json")
    train("RC_2015-10.json", "RC_2015-11.json")
    train("RC_2015-10.json", "RC_2015-11.json")
