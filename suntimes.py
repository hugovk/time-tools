#!/usr/bin/env python
"""
Dawn, sunrise, noon, sunset and dusk times for the given years.
"""
import argparse
import datetime
import json
import os

from astral import Astral  # pip install astral

# from pprint import pprint


def mkdir(directory):
    if not os.path.isdir(directory):
        os.mkdir(directory)


def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""
    if isinstance(obj, datetime.datetime) or isinstance(obj, datetime.date):
        serial = obj.isoformat()
        return serial
    raise TypeError("Type not serializable")


def sunyears(start_year, end_year):
    city_name = "London"
    a = Astral()
    a.solar_depression = "civil"
    city = a[city_name]

    sun_times = {}

    print(f"Information for {city_name}/{city.region}\n")

    timezone = city.timezone
    print(f"Timezone: {timezone}")

    print(f" Latitude: {city.latitude:.02f}; Longitude: {city.longitude:.02f}\n")

    delta = datetime.timedelta(days=1)

    for year in range(start_year, end_year + 1):
        # Loop through all days in year
        start_date = datetime.date(year, 1, 1)
        end_date = datetime.date(year, 12, 31)
        d = start_date
        while d <= end_date:

            sun = city.sun(d, local=True)
            # print('Dawn:    %s' % str(sun['dawn']))
            # print('Sunrise: %s' % str(sun['sunrise']))
            # print('Noon:    %s' % str(sun['noon']))
            # print('Sunset:  %s' % str(sun['sunset']))
            # print('Dusk:    %s' % str(sun['dusk']))
            # pprint(sun)

            sun_times[json_serial(d)] = sun
            # print(json.dumps(sun_times, default=json_serial,
            #      indent=4, sort_keys=True))

            d += delta

    # print(json.dumps(sun_times, default=json_serial))
    outfilename = f"suntimes-{start_year}-{end_year}"
    outfilename = os.path.join("data", outfilename)
    mkdir("data")

    with open(outfilename + ".json", "w") as outfile:
        json.dump(
            sun_times,
            outfile,
            default=json_serial,
            indent=4,
            separators=(",", ": "),
            sort_keys=True,
        )

    with open(outfilename + ".min.json", "w") as outfile:
        json.dump(sun_times, outfile, default=json_serial)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Dawn, sunrise, noon, sunset and dusk times",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("-s", "--start", type=int, default=1660, help="Start year")
    parser.add_argument("-e", "--end", type=int, default=1669, help="End year")
    args = parser.parse_args()

    sunyears(args.start, args.end)

# End of file
