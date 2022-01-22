import json
import math
from pebble import ProcessPool
from multiprocessing import Lock
import os
import random
from concurrent.futures.thread import ThreadPoolExecutor
from functools import partial
from concurrent.futures import TimeoutError

import numpy
import strconv
from sklearn.naive_bayes import GaussianNB
from scipy.optimize import minimize

from python import rsc
from spotter import extract_dissimilarity

mutex = Lock()

def train(training_file_name: str, testing_file_name: str):

    user_map = get_bot_file()

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

    # optimizer Portion
    param_guess = [0.4, 0.4, 0.6, 0.5, 1.1, 2.5, 5, 8 / 24]
    # result = optimizer_function(rsc_parameters=param_guess, timestamps=list(training_timestamps.values()), num_bins=30)

    result = [0.4, 0.4, 0.6, 0.5, 1.1, 2.5, 5.0, 0.3333333333333333]

    print("done with pre-classifier")

    trainingClassifier(result,
                       training_target,
                       testing_target,
                       training_timestamps,
                       testing_timestamps,
                       user_map)


def trainingClassifier(result,
                       training_target,
                       testing_target,
                       training_timestamps,
                       testing_timestamps,
                       user_map):

    rsc_parameters = result

    training_target = training_target[0:99000]
    training_timestamps = dict(list(training_timestamps.items())[:99000])
    testing_target = testing_target[0:99000]
    testing_timestamps = dict(list(testing_timestamps.items())[:99000])

    sample_timestamps = rsc.generate_timestamps(result[0],
                                                result[1],
                                                result[2],
                                                result[3],
                                                result[4],
                                                result[5],
                                                result[6],
                                                result[7],
                                                50)

    i = 0
    while i < 1000:
        i += 1
        username = "" + str(i) + " iterations of noise"
        user_map[username] = 1
        noised_timestamps = noise(timestamps=sample_timestamps, iterations=i)
        training_timestamps[username] = noised_timestamps
        testing_timestamps[username] = noised_timestamps
        training_target.append(1)
        testing_target.append(1)

    training_features = []
    testing_features = []

    partial_diss = partial(extract_dissimilarity, rsc_parameters=rsc_parameters, num_bins=30)

    with ProcessPool(max_workers=32, max_tasks=10) as pool:

        training_futures = pool.map(partial_diss, training_timestamps.values(), chunksize=5, timeout=10)
        pool.close()
        pool.join()

        training_futures = training_futures.result()
        i = 0
        while True:
            try:
                training_features.append([next(training_futures)])
                i += 1
            except StopIteration:
                break
            except TimeoutError:
                training_target.pop(i)
    while len(training_features) != len(training_target):
        training_target.pop(0)

    with ProcessPool(max_workers=32, max_tasks=10) as pool:

        testing_futures = pool.map(partial_diss, testing_timestamps.values(), chunksize=5, timeout=10)
        pool.close()
        pool.join()

        testing_futures = testing_futures.result()
        i = 0
        while True:
            try:
                testing_features.append([next(testing_futures)])
                i += 1
            except StopIteration:
                break
            except TimeoutError:
                testing_target.pop(i)
    while len(testing_features) != len(testing_target):
        testing_target.pop(0)
    
    print("done processing dissimilarity")

    training_target = numpy.array(training_target, dtype=float)
    testing_target = numpy.array(testing_target, dtype=float)
    training_features = numpy.array(training_features, dtype=float)
    testing_features = numpy.array(testing_features, dtype=float)

    classifier = GaussianNB()

    classifier.fit(training_features, training_target)

    print("done fitting classifier")

    score = classifier.score(X=testing_features, y=testing_target)

    print("The accuracy of the Classifier is:", score)

    true_positive = 0
    true_negative = 0
    false_positive = 0
    false_negative = 0

    for key in training_timestamps.keys():

        result = classifier_prediction_function(key, training_timestamps, user_map, classifier, rsc_parameters)

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

    max_values = 64

    average_parameters = [0.0] * 8
    all_parameters = [average_parameters] * max_values
    i = 0
    futures = []

    with ThreadPoolExecutor(max_workers=max_values) as e:
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

    bounds = ((0.01, 0.99), (0.01, 0.99), (0.01, 0.99), (0.2, 10.0), (0.2, 10.0), (math.log10(1), math.log10(3600)), (math.log10(100), math.log10(3600 * 24 * 30)), (0, 12/24))

    popt = minimize(extract_dissimilarity,
                    args=(timestamp, num_bins),
                    x0=rsc_parameters,
                    method='SLSQP',
                    bounds=bounds,
                    options={"disp": False})
    x: list[float] = popt.x.tolist()
    print(x)
    return x


def classifier_prediction_function(username, timestampList, usermap, classifier, rsc_parameters):

    timestamps = timestampList[username]
    truth = usermap[username]

    # run through the classification
    partial_diss = partial(extract_dissimilarity, rsc_parameters=rsc_parameters, num_bins=30)

    # Making sure if it hangs, it timeouts
    with ProcessPool(max_workers=1, max_tasks=1) as pool:

        futures = pool.map(partial_diss, [timestamps], timeout=10)
        pool.close()
        pool.join()

        futures = futures.result()
        while True:
            try:
                prediction = classifier.predict([[next(futures)]])
            except StopIteration:
                break
            except TimeoutError:
                prediction = 2
            result = "TN"

            # Determine truth
            if prediction != truth and truth == 1 and prediction != 2:
                tprint(username, "was a bot and not detected")
                result = "FN"
            elif prediction != truth and truth == 0 and prediction != 2:
                tprint(username, "was not a bot and detected")
                result = "FP"
            elif truth == 1 and prediction != 2:
                result = "TP"
            elif prediction == 2:
                tprint(username, "timed out when determining dissimilarity")
                result = prediction

    return result


def noise(timestamps, iterations):
    new_timestamps = timestamps.copy()

    for i in range(iterations):
        for timestamp in new_timestamps:
            noise_value = random.randrange(-5, 5, 1)
            timestamp += noise_value

    return new_timestamps


def tprint(str1, str2):
    with mutex:
        print(str1, str2)


if __name__ == "__main__":
    os.chdir("F:\\MQP Data\\jsonFiles")
    train("RC_2015-09.json", "RC_2015-10.json")
    train("RC_2020-06.json", "RC_2021-06.json")
