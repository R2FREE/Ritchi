import telebot
from bitmex_api import BitMEX_API

bot = telebot.TeleBot("746132186:AAFaInEvPk3iZGvzQIYMpGV4CsHRyqg8CwE")
user = bot.get_me()

chat_id = 768693322

bm = BitMEX_API()


def log_separate(func):
    def wrapper(*args, **kw):
        print('*-*-*-*-*-*-*-*-*-*-*-*-*-*-*')
        return func(*args, **kw)
    return wrapper

def send_start(restart):
    bot.send_chat_action(chat_id, 'typing')
    if restart == 0:
        bot.send_message(chat_id, 'START PRINTING' + '\n')
    if restart == 1:
        bot.send_message(chat_id, 'RESTART PRINTER' + '\n')

def send_pnl(pnl, price):
    message = "PNL: " + pnl + '\n' + 'PRICE: ' + price
    bot.send_chat_action(chat_id, 'typing')
    bot.send_message(chat_id, message)

def send_place_order(trend, execQty, avgPrice):
    message = "PLACED: " + trend + '\n' +\
              'QTY: ' + execQty + '\n' +\
              'PRICE: ' + avgPrice
    bot.send_chat_action(chat_id, 'typing')
    bot.send_message(chat_id, message)

def send_float_order(trend, execQty, avgPrice):
    message = "CONTINUE: " + trend + '\n' +\
              'TOTAL QTY: ' + execQty + '\n' + \
              'PRICE: ' + avgPrice
    bot.send_chat_action(chat_id, 'typing')
    bot.send_message(chat_id, message)

def send_any_msg(msg):
    message = msg
    bot.send_chat_action(chat_id, 'typing')
    bot.send_message(chat_id, message)

@bot.message_handler(commands=['wallet'])
def reply_wallet_balance(message):
    balance = "Wallet: " + str(bm.user_wallet_balance()) + ' XBT'
    bot.send_chat_action(chat_id, 'typing')
    bot.send_message(message.chat.id, balance)


if __name__ == '__main__':
    # import time

    # i = 0
    # # bot.infinity_polling(True)
    # while 1:
    #     i = i + 1
    #     send_any_msg(str(i))
    #     time.sleep(10)

    send_any_msg("8550.5%")