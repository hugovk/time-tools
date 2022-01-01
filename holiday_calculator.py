import argparse
import calendar
# from pprint import pprint

import holidays
from termcolor import colored

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Calculate public holidays for different countries",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("-s", "--start", type=int, default=2022, help="Start year")
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Print all holidays"
    )
    args = parser.parse_args()

    years = range(args.start, args.start + 100)
    print(f"{years[0]}-{years[-1]}, {len(years)} years")

    for country in "Finland", "England/Wales", "Scotland", "Northern Ireland":

        weekday_total = 0
        weekend_total = 0
        if country == "Finland":
            h = holidays.Finland(years=years)
        elif country == "England/Wales":
            h = holidays.England(years=years)
        elif country == "Northern Ireland":
            h = holidays.NorthernIreland(years=years)

        print(f"{country}:")

        for date, name in sorted(h.items()):
            if date.weekday() in range(0, 5):
                colour = "green"
                weekday_total += 1
            else:
                colour = "red"
                weekend_total += 1
            if args.verbose:
                print(
                    colored(
                        f"{date} {calendar.day_name[date.weekday()]}\t{name}",
                        colour,
                    )
                )

        print(
            colored(f"Weekday: {weekday_total}", "green"),
            "\t",
            colored(f"Weekend: {weekend_total}", "red"),
            "\t",
            f"Total: {weekday_total + weekend_total}",
        )

# End of file
