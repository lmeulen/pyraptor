"""Save results from RAPTOR algorithm"""
import os
from datetime import datetime

import pandas as pd
from loguru import logger

from pyraptor.util import sec2str, mkdir_if_not_exists


def write_results(output_folder, timetable, bag_k, evaluations) -> None:
    """
    Export results to a CSV file with stations and traveltimes per iteration.
    """

    mkdir_if_not_exists(output_folder)
    now = datetime.now()

    # Traveltime per round
    rows = []

    for round_k in list(bag_k.keys()):
        legs = bag_k[round_k]
        destination = 0

        for tt in legs:
            stop = timetable.stops.set_index.get(destination, None)

            if stop:
                name = stop.station.name
                platform = stop.platform_code

                rows.append(
                    dict(
                        round=str(round_k),
                        stop_id=str(destination),
                        stop_name=str(name),
                        platform_code=str(platform),
                        travel_time=str(tt[0]),
                    )
                )
            destination = destination + 1
    df = pd.DataFrame(rows)

    df = (
        df[["round", "stop_name", "travel_time"]]
        .groupby(["round", "stop_name"])
        .min()
        .sort_values(by=["stop_name", "round"])
    )
    df.travel_time = df.travel_time.apply(lambda x: sec2str(int(x)))

    filename1 = os.path.join(
        output_folder, "{date:%Y%m%d_%H%M%S}_traveltime.csv".format(date=now)
    )
    logger.debug("Write results to {}".format(filename1))
    df.to_csv(filename1)

    # Last legs
    rounds = sorted(list(bag_k.keys()))
    bag = bag_k[rounds[-1]]

    rows = []
    for b in bag:
        frm = b[0]
        via = b[1]
        to = b[2]
        rows.append(
            dict(
                from_id=str(frm),
                trip_id=str(via),
                stop_id=str(to),
            )
        )
    df2 = pd.DataFrame(rows)

    filename2 = os.path.join(
        output_folder, "{date:%Y%m%d_%H%M%S}_last_legs.csv".format(date=now)
    )
    logger.debug("Write results to {}".format(filename2))
    df2.to_csv(filename2, index=False)

    # Evaluations
    # (k, start_stop, trip, arrival_trip_stop_time)
    rows = []

    for val in evaluations:
        k = val[0]
        start_stop = val[1]
        trip = val[2]
        arrival_stop_time = val[3]

        rows.append(
            dict(
                k=k,
                start_stop=start_stop.id,
                trip=trip.id,
                to=arrival_stop_time.stop.id,
                trip_id=trip.id,
                trip_number=trip.hint,
                arrival=arrival_stop_time.dts_arr,
                from_name=start_stop.station.name,
                from_platform=start_stop.platform_code,
                to_name=arrival_stop_time.stop.station.name,
                to_platform=arrival_stop_time.stop.platform_code,
            )
        )
    df3 = pd.DataFrame(rows)
    df3.arrival = df3.arrival.apply(sec2str)

    filename3 = os.path.join(
        output_folder,
        "{date:%Y%m%d_%H%M%S}_evaluations.csv".format(date=now),
    )
    logger.debug("Write results to {}".format(filename3))
    df3.to_csv(filename3, index=False)
