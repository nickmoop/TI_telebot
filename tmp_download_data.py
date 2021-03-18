from time import sleep

import requests

from tmp_parser import TOKEN, MARKET_CANDLES_URL, iso_now_datetime
from datetime import timedelta, datetime
from tmp_utils import load_yaml


HEADERS = {
    "accept": "application/json",
    "Authorization": "Bearer {}".format(TOKEN),
}


def daterange(start_datetime, end_datetime):
    for n in range(int((end_datetime - start_datetime).days)):
        yield end_datetime - timedelta(n), end_datetime - timedelta(n) + timedelta(1)


if __name__ == "__main__":
    all_figi = [v["figi"] for v in load_yaml("ticker_to_figi_map.yaml").values()]

    for figi in all_figi:
        start_date = datetime(2000, 3, 15)
        end_date = datetime(2021, 3, 17)

        with open("{}_candles".format(figi), "w") as file_:
            file_.write("time  open  close  high  low  volume\n")

        counter = 0
        days_without_candles = 0
        for from_, to in daterange(start_date, end_date):
            if counter >= 200:
                sleep(60)
                counter = 0

            print(figi, iso_now_datetime(from_))
            counter += 1

            params = (
                ("figi", figi),
                ("from", iso_now_datetime(from_)),
                ("to", iso_now_datetime(to)),
                ("interval", "1min"),
            )

            try:
                day_candles = requests.get(
                    MARKET_CANDLES_URL, headers=HEADERS, params=params,
                ).json()["payload"]["candles"]
            except Exception as exception:
                print(exception)

                with open("{}_exceptions".format(figi), "a+") as file_:
                    file_.write("{}\n\n\n\n\n".format(exception))

                counter += 200
                continue

            if day_candles:
                days_without_candles = 0
            else:
                days_without_candles += 1

            if days_without_candles >= 15:
                sleep(60)
                break

            with open("{}_candles".format(figi), "a+") as file_:
                for candle in day_candles:
                    file_.write(
                        "{}  {}  {}  {}  {}  {}\n".format(
                            candle["time"], candle["o"], candle["c"],
                            candle["h"], candle["l"], candle["v"])
                    )
