"""Utility functions"""
import os
import numpy as np


SAVE_RESULTS = True
TRANSFER_COST = 3 * 60  # Default transfer time is 3 minutes
T3M = 3 * 60
T1H = 1 * 60 * 60
T6H = 6 * 60 * 60
T24H = 24 * 60 * 60


def mkdir_if_not_exists(name):
    """Create directory if not exists"""
    if not os.path.exists(name):
        os.makedirs(name)


def str2sec(time_str):
    """
    Convert hh:mm:ss to seconds since midnight
    :param time_str: String in format hh:mm:ss
    """
    split_time = time_str.strip().split(":")
    if len(split_time) == 3:
        # Has seconds
        hours, minutes, seconds = split_time
        return int(hours) * 3600 + int(minutes) * 60 + int(seconds)
    minutes, seconds = split_time
    return int(minutes) * 60 + int(seconds)


def sec2str(scnds, show_sec=False):
    """
    Convert hh:mm:ss to seconds since midnight

    :param show_sec: only show :ss if True
    :param scnds: Seconds to translate to hh:mm:ss
    """
    scnds = np.round(scnds)
    hours = int(scnds / 3600)
    minutes = int((scnds % 3600) / 60)
    seconds = int(scnds % 60)
    return (
        "{:02d}:{:02d}:{:02d}".format(hours, minutes, seconds)
        if show_sec
        else "{:02d}:{:02d}".format(hours, minutes)
    )
