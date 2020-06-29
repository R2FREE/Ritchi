import re
import json
import urllib.request

url = "http://webforex.hermes.hexun.com/forex/quotelist?code=FOREXUSDCNY&column=Code,Price"
req = urllib.request.Request(url)
f = urllib.request.urlopen(req)
html = f.read().decode("utf-8")


s = re.findall('{.*}', str(html))[0]
json = json.loads(s)

USDCNY = round(json["Data"][0][0][1] / 10000, 2)
print(USDCNY)
