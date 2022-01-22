from math import log10, ceil
from os import getpid

from numpy import logspace, unique
import rsc


def extract_dissimilarity(actual_timestamps, rsc_parameters, num_bins):

    synthetic_timestamps = rsc.generate_timestamps(rsc_parameters[0],
                                                   rsc_parameters[1],
                                                   rsc_parameters[2],
                                                   rsc_parameters[3],
                                                   rsc_parameters[4],
                                                   rsc_parameters[5],
                                                   rsc_parameters[6],
                                                   rsc_parameters[7],
                                                   len(actual_timestamps))

    synthetic_delays = calcDeltas(synthetic_timestamps)
    synthetic_counts, centers, bucket_lims = no_centers_log_bin_hist(synthetic_delays, num_bins)

    actual_delays = calcDeltas(actual_timestamps)
    actual_counts = log_bin_hist(actual_delays, centers, bucket_lims)

    synthetic_sum = sum(synthetic_counts)
    actual_sum = sum(actual_counts)
    dissimilarity = [0.0] * len(synthetic_counts)

    for i in range(len(synthetic_counts)):
        if actual_sum != 0:
            actual_counts[i] = actual_counts[i]/actual_sum
        if synthetic_sum != 0:
            synthetic_counts[i] = synthetic_counts[i]/synthetic_sum
        dissimilarity[i] = abs(actual_counts[i] - synthetic_counts[i])

    return sum(dissimilarity)


def no_centers_log_bin_hist(deltas, num_bins):
    minimum = min(deltas)
    if minimum <= 0:
        minimum: float = 1.0
    min_exp = log10(minimum)
    max_exp = log10(max(deltas))
    bucket_lim = logspace(min_exp, max_exp, num=num_bins, base=10, dtype=float)
    for bucket in bucket_lim:
        bucket = ceil(bucket)
    bucket_lim = unique(bucket_lim)
    centers = [0] * (len(bucket_lim) - 1)
    for i in range(len(bucket_lim) - 1):
        centers[i] = bucket_lim[i] + bucket_lim[i+1] - bucket_lim[i]/2

    counts = log_bin_hist(deltas, centers, bucket_lim)

    return counts, centers, bucket_lim


def log_bin_hist(deltas, centers, bucket_lim):
    counts = [0] * len(centers)
    for delta in deltas:
        if delta < bucket_lim[0]:
            continue
        elif delta > bucket_lim[-1]:
            continue
        found_bucket = False
        bucket = 0
        for bucket in range(len(centers)):
            bucket_upper_lim = bucket_lim[bucket + 1]
            bucket_lower_lim = bucket_lim[bucket]
            if bucket_upper_lim > delta > bucket_lower_lim:
                found_bucket = True
                break
        if found_bucket:
            counts[bucket] += 1
        else:
            continue
    return counts


def calcDeltas(timestamps):
    deltas = [0] * (len(timestamps)-1)

    for i in range(len(timestamps)-1):
        deltas[i] = timestamps[i+1] - timestamps[i]
    return deltas

if __name__ == "__main__":
    print(extract_dissimilarity(rsc_parameters = [0.4, 0.4, 0.6, 0.5, 1.1, 2.5, 5.0, 0.3333333333333333], actual_timestamps=[0,1,2,3,4,5,6,7,8,9,10], num_bins=30))
