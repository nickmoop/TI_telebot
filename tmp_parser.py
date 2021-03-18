import os
from datetime import datetime, timedelta

import requests

from tmp_utils import save_yaml, load_yaml

TOKEN = ""
BASE_URL = "https://api-invest.tinkoff.ru/openapi"
MARKET_STOCKS_URL = "{}/market/stocks".format(BASE_URL)
MARKET_CANDLES_URL = "{}/market/candles".format(BASE_URL)
NAME_FIGI_TICKER_MAP_PATH = "ticker_to_figi_map.yaml"
HEADERS = {
    "accept": "application/json",
    "Authorization": "Bearer {}".format(TOKEN),
}


def make_figi_ticker_dictionary():
    stocks = get_stocks()
    russian_stocks = load_yaml("russian_tickers.yaml")["russian_tickers"]

    ticker_to_figi_map = dict()
    for stock in stocks:
        if stock["ticker"] in russian_stocks:
            continue

        ticker_to_figi_map[stock["ticker"]] = {
            "figi": stock["figi"],
        }

    save_yaml(NAME_FIGI_TICKER_MAP_PATH, ticker_to_figi_map)


def get_stocks():
    return requests.get(
        MARKET_STOCKS_URL, headers=HEADERS
    ).json()["payload"]["instruments"]


def get_candles_by_figi(
        figi="BBG000BWJFZ4",
        candle_interval="1min",
        analysis_interval=None,
        **kwargs,
):
    now_ = datetime.now()
    now_iso = iso_now_datetime(now_)
    previous_iso = iso_now_datetime(
        now_ - timedelta(minutes=analysis_interval))

    params = (
        ("figi", figi),
        ("from", previous_iso),
        ("to", now_iso),
        ("interval", candle_interval),
    )

    return requests.get(
        MARKET_CANDLES_URL, headers=HEADERS, params=params,
    ).json()["payload"]["candles"]


def find_company_by_ticker(company_name):
    name_figi_ticker_map = load_yaml(NAME_FIGI_TICKER_MAP_PATH)

    return name_figi_ticker_map.get(
        company_name.upper(), dict()
    ).get("figi", None)


def iso_now_datetime(some_datetime):
    return some_datetime.astimezone().isoformat()


def to_local_time(some_datetime):
    local_datetime = datetime.strptime(some_datetime, "%Y-%m-%dT%H:%M:%SZ")
    local_datetime += timedelta(hours=2)

    return local_datetime


def add_company_to_monitoring(chat_id, company_figi, company_name):
    new_company_data = {
        company_name: {
            "figi": company_figi,
        }
    }

    file_path = "{}.yaml".format(chat_id)
    if os.path.isfile(file_path):
        file_data = load_yaml(file_path)
        if file_data is None:
            tmp_set_parameters(chat_id, "1min")
            file_data = load_yaml(file_path)
            file_data.update(new_company_data)
        else:
            file_data.update(new_company_data)
    else:
        tmp_set_parameters(chat_id, "1min")
        file_data = load_yaml(file_path)
        file_data.update(new_company_data)

    save_yaml(file_path, file_data)


def delete_company_from_monitoring(chat_id, company_figi):
    monitoring_list = load_yaml("{}.yaml".format(chat_id))
    is_company_monitoring = monitoring_list.pop(company_figi, False)
    if is_company_monitoring:
        save_yaml("{}.yaml".format(chat_id), monitoring_list)
        return True
    else:
        return False


def tmp_set_parameters(chat_id, candle_interval):
    if "monitor_other" in candle_interval:
        return set_other_companies_monitoring(chat_id, candle_interval)

    possible_candles_intervals = load_yaml("parameters_map.yaml")
    candle_interval = "1min" if candle_interval is None else candle_interval

    if candle_interval not in possible_candles_intervals.keys():
        return "Impossible candle_interval: {}. Please choose from: {}".format(
            candle_interval, possible_candles_intervals,
        )

    tmp_common_parameters = possible_candles_intervals[candle_interval]

    file_path = "{}.yaml".format(chat_id)
    if os.path.isfile(file_path):
        file_data = load_yaml(file_path)
        is_monitor_other_companies = file_data["common_parameters"]["is_monitor_other_companies"]
        file_data["common_parameters"] = tmp_common_parameters
        file_data["common_parameters"]["is_monitor_other_companies"] = is_monitor_other_companies
    else:
        file_data = {
            "common_parameters": tmp_common_parameters
        }

    save_yaml(file_path, file_data)

    return "New interval '{}' is set up.".format(candle_interval)


def set_other_companies_monitoring(chat_id, candle_interval):
    answer = "Something wrong with other companies monitoring flag setting."

    if "no_monitor_other" in candle_interval:
        answer = "No monitor other companies is set up."
        is_monitor_other_companies = False
    elif "monitor_other" in candle_interval:
        answer = "Monitor other companies is set up."
        is_monitor_other_companies = True
    else:
        return answer

    possible_candles_intervals = load_yaml("parameters_map.yaml")
    tmp_common_parameters = possible_candles_intervals["1min"]

    tmp_common_parameters["is_monitor_other_companies"] = is_monitor_other_companies

    file_path = "{}.yaml".format(chat_id)
    if os.path.isfile(file_path):
        file_data = load_yaml(file_path)

        common_parameters = file_data.get("common_parameters", None)
        if common_parameters is not None:
            file_data["common_parameters"]["is_monitor_other_companies"] = is_monitor_other_companies
        else:
            file_data["common_parameters"] = tmp_common_parameters
    else:
        file_data = {
            "common_parameters": tmp_common_parameters
        }

    save_yaml(file_path, file_data)

    return answer


def tmp_get_parameter(chat_id, parameter_name):
    file_path = "{}.yaml".format(chat_id)
    if os.path.isfile(file_path):
        file_data = load_yaml(file_path)
        if file_data is None:
            return None
        else:
            return file_data["common_parameters"].get(parameter_name, None)
    else:
        return None
