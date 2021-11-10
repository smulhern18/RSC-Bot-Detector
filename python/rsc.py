from math import exp, log, ceil, floor
import random
import warnings

NONE = 0
ACTIVE = 1
REST = 2
SLEEP = 3
PREVIOUS_STATE = NONE
CURRENT_STATE = ACTIVE


def generate_timestamps(p_prob: float,
                        q_prob: float,
                        p_post: float,
                        sigma_rest: float,
                        sigma_active: float,
                        lambda_active: float,
                        lambda_rest: float,
                        total_sleep: float,
                        t_size: int):
    warnings.filterwarnings("error")

    global CURRENT_STATE
    global PREVIOUS_STATE

    lambda_active = 1 / (10 ** lambda_active)
    lambda_rest = 1 / (10 ** lambda_rest)

    day_start = 0
    day_end = 24 * 3600 * (1 - total_sleep)

    previous_active_delay = 1 / lambda_active
    previous_rest_delay = 1 / lambda_rest

    rand_numbers = []
    for i in range(ceil(t_size / 2)):
        rand_numbers.append(random.random())
    rand_numbers_idx = 0

    t = [0.0] * t_size
    mu = previous_active_delay + 1/(lambda_active * exp(1))
    rate = 1/mu
    delay = -log(rand_numbers[rand_numbers_idx])/rate

    previous_active_delay = delay
    t[0] = day_start + delay

    delay = 0
    t_count = 1
    while t_count < t_size:
        if CURRENT_STATE == ACTIVE:

            if rand_numbers_idx < len(rand_numbers)-1:
                rand_numbers_idx += 1
            else:
                rand_numbers_idx = 0
            active_delay = calcDelay(sigma_active, previous_active_delay, lambda_active, rand_numbers[rand_numbers_idx])

            previous_active_delay = active_delay
            delay = delay + active_delay

            if random.random() < p_post:
                t[t_count] = t[t_count - 1] + delay
                t_count += 1
                delay = 0

            current_time = t[t_count - 1] + delay
            if isSleeping(current_time, day_start, day_end):
                CURRENT_STATE = SLEEP
            elif random.random() < p_prob:
                CURRENT_STATE = REST
                previous_rest_delay = 0
            else:
                CURRENT_STATE = ACTIVE
            PREVIOUS_STATE = ACTIVE

        elif CURRENT_STATE == REST:

            if rand_numbers_idx < len(rand_numbers)-1:
                rand_numbers_idx += 1
            else:
                rand_numbers_idx = 0

            rest_delay = calcDelay(sigma_rest, previous_rest_delay, lambda_rest, rand_numbers[rand_numbers_idx])

            previous_rest_delay = rest_delay
            delay = delay + rest_delay

            current_time = t[t_count - 1] + delay
            if isSleeping(current_time, day_start, day_end):
                CURRENT_STATE = SLEEP
            elif random.random() < q_prob:
                CURRENT_STATE = ACTIVE
                previous_active_delay = 0
            else:
                CURRENT_STATE = REST

            PREVIOUS_STATE = REST

        else:
            current_time = t[t_count - 1] + delay
            sleep_delay = timeUntilWakeUp(current_time, day_start, day_end)
            delay = delay + sleep_delay

            CURRENT_STATE = REST

    return t


def calcDelay(sigma, previous_delay, lamb, rand_num):
    try:
        mu = sigma * previous_delay + 1 / (lamb * exp(1))
    except RuntimeError:
        mu = (sigma * previous_delay)/10e6 + 1 / (lamb * exp(1))
    rate = 1 / mu
    try:
        delay = -log(rand_num) / rate
    except RuntimeError:
        rate = rate * 10e6
        delay = -log(rand_num) / rate
    return delay


def isSleeping(current_time, day_start, day_end):
    second_of_day = (current_time % 24.0) * 3600.0
    if day_start < second_of_day < day_end:
        sleeping = False
    else:
        sleeping = True

    return sleeping


def timeUntilWakeUp(current_time: float, day_start: float, day_end: float):
    day_length = 24 * 3600
    second_of_day = current_time - day_length * floor(current_time / day_length)

    if second_of_day < day_start:
        total_time = day_start - second_of_day
    elif second_of_day >= day_end:
        total_time = day_start + (24 * 3600 - second_of_day)
    else:
        total_time = day_start + (24 * 3600 - second_of_day)

    return total_time
