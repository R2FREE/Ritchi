# Ritchi
<img src="https://github.com/R2FREE/Ritchi/blob/master/img/logo.png" width="200">

Ritchi is a crypto trading bot based on Telegram bot, WebSocket API and REST API for BitMEX exchange.  

You can control your algorithmic trading script on serve to run or stop trading, sell(short) or buy(long) with Telegram.  

If you are interested in Cryptocurrency Quantitative Trading, especially trading BTC on BitMEX and your location is at any “Restricted Jurisdiction” under BitMEX's [Terms of Service](https://www.bitmex.com/app/terms). I think this project will help you or inspire you at least.

## Features
- Based on Python 3.7+: Only For Windows now.
- Design for BitMEX traders in the forbidden IP countries (China, United States, Cuba, Camilla, Sevastopol, Iran, Syria, North Korea and Sudan).
- Manageable via Telegram: Manage the bot with Telegram.
- Performance status report: Provide a performance status of your current trades.

## Getting Started
Ritchi requires the Python Packages (or higher version) as below :
- numpy==1.16.4
- pandas==0.24.2
- aiogram==2.3
- python_telegram_bot==12.0.0
- pyTelegramBotAPI==3.6.6
- requests==2.22.0
- CurrencyConverter==0.13.10
- bitmex-ws==0.3.1

## How to use
Depending on the location of  server you running your code, there are mainly two ways to use Ritchi.  

### Location in  the forbidden IP countries
The original bitmex_ws package file need to be replaced by the file named bitmex_ws_forbidden in folder replace. The difference betweent these two files is the alternative one  replace this line code
```Python
self.wst = threading.Thread(target=lambda: self.ws.run_forever())
```
with
```Python
self.wst = threading.Thread(target=lambda :self.ws.run_forever(http_proxy_host="127.0.0.1", http_proxy_port=7890))
```
the value of http_proxy_port could be different depending on your setting (it should be 7890 for clash on Windows).

### Other countries
Remain to be done.

## Rest parts will be updated after Octorber. 
### For now, I'm preparing for getting a job related to digital IC design. I will keep updating this project after getting a ideal job.
