import json
from sklearn.naive_bayes import GaussianNB


def train(training_file_name: str, testing_file_name: str):

    user_map = get_bot_file()
    target_names = ["human", "bot"]

    training_timestamps = read_json_file(training_file_name, user_map)
    training_target = []
    training_features = []
    for username, timestamps in training_timestamps:
        is_bot = user_map[username]
        training_features.append(timestamps)
        training_target.append(is_bot)

    testing_timestamps = read_json_file(testing_file_name, user_map)
    testing_target = []
    testing_features = []
    for username, timestamps in testing_timestamps:
        is_bot = user_map[username]
        testing_features.append(timestamps)
        testing_target.append(is_bot)

    clf = GaussianNB()
    clf.fit(training_features, training_target)

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