from functools import partial
from queue import Queue
from time import sleep

import telebot

from tmp_logic import monitor_companies, tmp_monitor_other_companies
from tmp_parser import make_figi_ticker_dictionary, find_company_by_ticker, \
    add_company_to_monitoring, delete_company_from_monitoring, \
    tmp_set_parameters, tmp_get_parameter

BOT_ID = ""
BOT = telebot.TeleBot(BOT_ID)
STOP_QUEUES = dict()
SIGNALS_QUEUES = dict()
OTHER_SIGNALS_QUEUES = dict()


@BOT.message_handler(commands=["add"])
def add_ticker(message):
    company_name = message.text
    company_name = company_name.replace("/add ", "").upper()

    BOT.send_message(
        message.chat.id, "Try to find company: {}".format(company_name))

    company_figi = find_company_by_ticker(company_name)
    if company_figi is None:
        BOT.send_message(
            message.chat.id, "Company: {}, not found.".format(company_name))
    else:
        BOT.send_message(
            message.chat.id,
            "Company: {}, found. FIGI: {}.".format(company_name, company_figi),
        )

        add_company_to_monitoring(message.chat.id, company_figi, company_name)

        BOT.send_message(
            message.chat.id,
            "Company: {}, added to monitoring list.".format(company_name),
        )


@BOT.message_handler(commands=["delete"])
def add_ticker(message):
    company_name = message.text
    company_name = company_name.replace("/delete ", "")

    BOT.send_message(
        message.chat.id, "Try to find company: {}".format(company_name))

    company_figi = find_company_by_ticker(company_name)
    if company_figi is None:
        BOT.send_message(
            message.chat.id, "Company: {}, not found.".format(company_name))
    else:
        BOT.send_message(
            message.chat.id,
            "Company: {}, found. FIGI: {}.".format(company_name, company_figi),
        )

        is_company_deleted = delete_company_from_monitoring(
            message.chat.id, company_figi)
        if is_company_deleted:
            BOT.send_message(
                message.chat.id,
                "Company: {}, deleted from monitoring.".format(company_name),
            )
        else:
            BOT.send_message(
                message.chat.id,
                "Company: {}, not monitoring yet.".format(company_name),
            )


@BOT.message_handler(commands=["start"])
def start(message):
    stop_queue = Queue()
    signals_queue = Queue()
    other_companies_queue = Queue()

    STOP_QUEUES[message.chat.id] = stop_queue
    SIGNALS_QUEUES[message.chat.id] = signals_queue
    OTHER_SIGNALS_QUEUES[message.chat.id] = other_companies_queue
    BOT.send_message(message.chat.id, "Start monitoring.")

    request_interval = tmp_get_parameter(
        message.chat.id, "request_interval")
    is_monitor_other_companies = tmp_get_parameter(
        message.chat.id, "is_monitor_other_companies")
    tmp_minutes_counter = 0
    while True:
        if not stop_queue.empty():
            break

        if tmp_minutes_counter == 0:
            tmp_monitor_user_companies(message.chat.id, signals_queue)

        if is_monitor_other_companies:
            tmp_tmp_monitor_other_companies(
                message.chat.id, other_companies_queue)

        print("Go sleep")

        BOT.send_message(
            message.chat.id,
            text="Sleep 1 minute",
        )

        sleep(60)
        tmp_minutes_counter += 1
        if tmp_minutes_counter >= request_interval:
            tmp_minutes_counter = 0

    del SIGNALS_QUEUES[message.chat.id]
    del STOP_QUEUES[message.chat.id]
    BOT.send_message(message.chat.id, "Stop monitoring.")


def tmp_tmp_monitor_other_companies(chat_id, signals_queue):
    tmp_monitor_other_companies(chat_id, signals_queue)

    while not signals_queue.empty():
        company_name, monitor_signal = signals_queue.get()

        BOT.send_message(
            chat_id,
            text=monitor_signal,
            reply_markup=make_buy_sell_skip_keyboard(company_name),
        )

        signals_queue.task_done()


def tmp_monitor_user_companies(chat_id, signals_queue):
    monitor_companies(chat_id, signals_queue)

    while not signals_queue.empty():
        company_name, monitor_signal = signals_queue.get()

        BOT.send_message(
            chat_id,
            text=monitor_signal,
            reply_markup=make_buy_sell_skip_keyboard(company_name),
        )

        signals_queue.task_done()


@BOT.message_handler(commands=["stop"])
def stop(message):
    if message.chat.id in STOP_QUEUES:
        STOP_QUEUES[message.chat.id].put(1, block=False)
        BOT.send_message(message.chat.id, "Send stop message.")
    else:
        BOT.send_message(message.chat.id, "Monitoring already stopped.")


@BOT.message_handler(commands=["set"])
def set_ticker(message):
    BOT.send_message(
        message.chat.id,
        text="Choose candle interval",
        reply_markup=make_set_keyboard(),
    )


@BOT.message_handler(commands=["help"])
def help(message):
    BOT.send_message(
        message.chat.id,
        text="Commands list:\n"
             "/add <ticker> - will add company to companies monitoringlist\n"
             "/set - open menu with monitoring settings\n"
             "    user can set candles intervals and set 'other' companies to monitoring or not\n"
             "/start - start monitoring companies list by using given settings (or default setttings)\n"
             "/stop - stop monitoring companies",
    )


@BOT.callback_query_handler(func=lambda call: True)
def query_handler(call):
    answer = str()
    operation = call.data.split("__")[0]
    argument = call.data.split("__")[1]

    if operation == "buy":
        answer = "How much buy {}?".format(argument)
        BOT.register_next_step_handler(
            call.message,
            partial(process_buy, call=call, company_name=argument),
        )
    elif operation == "sell":
        answer = "How much sell {}?".format(argument)
        BOT.register_next_step_handler(
            call.message,
            partial(process_sell, call=call, company_name=argument),
        )
    elif operation == "skip":
        answer = "Skipped {}".format(argument)
        BOT.edit_message_reply_markup(
            call.message.chat.id, call.message.message_id)

    elif operation == "set":
        answer = tmp_set_parameters(call.message.chat.id, argument)
        BOT.edit_message_reply_markup(
            call.message.chat.id, call.message.message_id)
    else:
        print("Else. {}".format(call.data))

    BOT.send_message(call.message.chat.id, answer)


def process_buy(message, call=None, company_name=None):
    count_to_buy = int(message.text)
    answer = "I will buy {} of {}".format(count_to_buy, company_name)

    BOT.send_message(message.chat.id, answer)

    BOT.edit_message_reply_markup(
        call.message.chat.id, call.message.message_id)


def process_sell(message, call=None, company_name=None):
    count_to_sell = int(message.text)
    answer = "I will sell {} of {}".format(count_to_sell, company_name)

    BOT.send_message(message.chat.id, answer)

    BOT.edit_message_reply_markup(
        call.message.chat.id, call.message.message_id)


@BOT.message_handler()
def echo(message):
    BOT.send_message(
        message.chat.id,
        text="Echo: {}".format(message.text),
    )


def make_buy_sell_skip_keyboard(company_name):
    keyboard = telebot.types.InlineKeyboardMarkup()
    keyboard.row(
        telebot.types.InlineKeyboardButton(
            text="Buy {}".format(company_name),
            callback_data="buy__{}".format(company_name),
        ),
        telebot.types.InlineKeyboardButton(
            text="Sell {}".format(company_name),
            callback_data="sell__{}".format(company_name),
        ),
    )

    keyboard.row(
        telebot.types.InlineKeyboardButton(
            text="Skip {}".format(company_name),
            callback_data="skip__{}".format(company_name)
        ),
    )

    return keyboard


def make_set_keyboard():
    keyboard = telebot.types.InlineKeyboardMarkup()
    keyboard.row(
        telebot.types.InlineKeyboardButton(
            text="1min",
            callback_data="set__1min",
        ),
        telebot.types.InlineKeyboardButton(
            text="5min",
            callback_data="set__5min",
        ),
        telebot.types.InlineKeyboardButton(
            text="10min",
            callback_data="set__10min",
        ),
    )

    keyboard.row(
        telebot.types.InlineKeyboardButton(
            text="1hour",
            callback_data="set__hour",
        ),
        telebot.types.InlineKeyboardButton(
            text="4hour",
            callback_data="set__4hour",
        ),
        telebot.types.InlineKeyboardButton(
            text="1day",
            callback_data="set__day",
        ),
    )

    keyboard.row(
        telebot.types.InlineKeyboardButton(
            text="no monitor other companies",
            callback_data="set__no_monitor_other",
        ),
        telebot.types.InlineKeyboardButton(
            text="monitor other companies",
            callback_data="set__monitor_other",
        ),
    )

    return keyboard


if __name__ == "__main__":
    make_figi_ticker_dictionary()
    BOT.polling()  # look at kwargs!
