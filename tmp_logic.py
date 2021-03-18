from tmp_parser import get_candles_by_figi, to_local_time
from tmp_utils import load_yaml


TMP_OTHER_COMPANIES = dict()
GREEN_HEART = "\U0001F49A"
RED_HEART = "\U0001F494"


def tmp_monitor_other_companies(chat_id, other_companies_queue):
    global TMP_OTHER_COMPANIES

    make_other_companies(chat_id)
    other_companies_settings = load_yaml("parameters_map.yaml")["other_companies"]

    tmp_counter = 50
    while tmp_counter != 0:
        if not TMP_OTHER_COMPANIES:
            break

        company_name, settings = TMP_OTHER_COMPANIES.popitem()

        signal = monitor_company({**settings, **other_companies_settings})
        if signal is not None:
            other_companies_queue.put(
                (company_name, "{}. {}".format(company_name, signal)),
                block=False,
            )

        tmp_counter -= 1

    print("Other companies to check: {}".format(len(TMP_OTHER_COMPANIES)))


def make_other_companies(chat_id):
    global TMP_OTHER_COMPANIES

    if TMP_OTHER_COMPANIES:
        return

    user_companies = load_yaml("{}.yaml".format(chat_id))
    all_companies = load_yaml("ticker_to_figi_map.yaml")

    TMP_OTHER_COMPANIES = {name: s for name, s in all_companies.items() if name not in user_companies.keys()}


def monitor_companies(chat_id, user_queue):
    companies = load_yaml("{}.yaml".format(chat_id))
    common_parameters = companies.pop("common_parameters")

    for company_name, settings in companies.items():
        signal = monitor_company({**settings, **common_parameters})
        if signal is not None:
            user_queue.put(
                (company_name, "{}. {}".format(company_name, signal)),
                block=False,
            )


def monitor_company(settings):
    candles = get_candles_by_figi(**settings)

    messages = list()
    messages.append(find_local_min_max(candles, **settings))
    messages.append(tmp_find_local_grow(candles, **settings))
    messages.append(tmp_find_candle_grow(candles, **settings))

    tmp_overall_message = "\n".join([m for m in messages if m is not None])

    if tmp_overall_message:
        return tmp_overall_message
    else:
        return None


def find_local_min_max(candles, extremum_percent=None, **kwargs):
    if not candles:
        print("Empty candles")
        return None

    local_min = None
    local_min_time = None
    local_max = None
    local_max_time = None

    for candle in candles:
        if local_min is None:
            local_min = candle["l"]
            local_min_time = to_local_time(candle["time"])
        elif candle["l"] > local_min:
            local_min = candle["l"]
            local_min_time = to_local_time(candle["time"])

        if local_max is None:
            local_max = candle["h"]
            local_max_time = to_local_time(candle["time"])
        elif candle["h"] > local_max:
            local_max = candle["h"]
            local_max_time = to_local_time(candle["time"])

    if local_min is None or local_max is None:
        # TODO remove it!
        import ipdb;ipdb.set_trace()

    percent_delta = (local_max / local_min - 1) * 100

    print(
        "Local min: {}\n" \
        "Local max: {}\n" \
        "Percent delta: {:.03f}\n" \
        "Percent delta threshold: {:.03f}".format(
            local_min, local_max, percent_delta, extremum_percent,
        )
    )

    if percent_delta < extremum_percent:
        return None

    if local_max_time > local_min_time:
        tmp_up_or_down = GREEN_HEART
    else:
        tmp_up_or_down = RED_HEART

    return "Local maximum at: {}\n" \
           "Local minimum at: {}\n" \
           "Percent delta: {:.03f} {} ${}".format(
        local_max_time, local_min_time, percent_delta, tmp_up_or_down,
        candles[-1]["c"],
    )


def tmp_find_local_grow(candles, grow_percent=None, **kwargs):
    if not candles:
        print("Empty candles")
        return None

    open_price = candles[0]["o"]
    close_price = candles[-1]["c"]

    percent_delta = max(open_price, close_price) / min(open_price, close_price)
    percent_delta -= 1
    percent_delta *= 100

    print(
        "Open price: {}\n" \
        "Close price: {}\n" \
        "Percent delta: {:.03f}\n" \
        "Percent delta threshold: {:.03f}".format(
            open_price, close_price, percent_delta, grow_percent,
        )
    )

    if open_price > close_price and percent_delta > grow_percent:
        return "Decrease from {} to {}\n" \
               "Percent delta: {:.03f} {} ${}".format(
            to_local_time(candles[0]["time"]),
            to_local_time(candles[-1]["time"]),
            percent_delta, RED_HEART, candles[-1]["c"],
        )

    if close_price > open_price and percent_delta > grow_percent:
        return "Increase from {} to {}\n" \
               "Percent delta: {:.03f} {} ${}".format(
            to_local_time(candles[0]["time"]),
            to_local_time(candles[-1]["time"]),
            percent_delta, GREEN_HEART, candles[-1]["c"],
        )

    return None


def tmp_find_candle_grow(candles, grow_percent=None, **kwargs):
    if not candles:
        print("Empty candles")
        return None

    open_price = candles[-1]["o"]
    close_price = candles[-1]["c"]

    percent_delta = max(open_price, close_price) / min(open_price, close_price)
    percent_delta -= 1
    percent_delta *= 100

    print(
        "Candle open price: {}\n" \
        "Candle close price: {}\n" \
        "Candle percent delta: {:.03f}\n" \
        "Candle percent delta threshold: {}".format(
            open_price, close_price, percent_delta, grow_percent,
        )
    )

    if open_price > close_price and percent_delta > grow_percent:
        return "Candle decrease: {}\n" \
               "Candle percent delta: {:.03f} {} ${}".format(
            to_local_time(candles[-1]["time"]), percent_delta, RED_HEART,
            candles[-1]["c"],
        )

    if close_price > open_price and percent_delta > grow_percent:
        return "Candle increase: {}\n" \
               "Candle percent delta: {:.03f} {} ${}".format(
            to_local_time(candles[-1]["time"]), percent_delta, GREEN_HEART,
            candles[-1]["c"],
        )

    return None


def tmp_candle_shadow(candles, shadow_percent=None, **kwargs):
    max_percent_delta = 0
    max_percent_delta_time = None
    for candle in candles:
        open_closed_delta = abs(candle["o"] - candle["c"])
        if open_closed_delta == 0:
            continue

        percent_delta = (candle["h"] - candle["l"]) / open_closed_delta
        percent_delta -= 1
        percent_delta *= 100

        if (
            percent_delta > shadow_percent and
            percent_delta > max_percent_delta
        ):
            max_percent_delta_time = to_local_time(candle["time"])
            max_percent_delta = percent_delta

    print(
        "Candle shadow percent delta: {}\n" \
        "Candle shadow percent delta threshold: {}".format(
            max_percent_delta, shadow_percent,
        )
    )

    if max_percent_delta == 0:
        return None

    return "Candle shadow max percent delta: {}\n" \
           "At: {}".format(max_percent_delta, max_percent_delta_time)
