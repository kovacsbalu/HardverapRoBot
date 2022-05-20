import json
import sys
import urllib.request

import paho.mqtt.client as mqtt
from bs4 import BeautifulSoup
from tinydb import Query, TinyDB


class Item:
    def __init__(self, adid, name, price, link):
        self.adid = adid
        self.name = name
        self.price = price
        self.link = link

    def __str__(self):
        return self.adid + ": " + self.name + " Ára:" + self.price + " Link:" + self.link

    def __repr__(self):
        return str(self.__dict__)


class HardverapRoBot:

    SEARCH_URL = "https://hardverapro.hu/aprok/keres.php?stext={}"\
                 "&stcid_text=&stcid=&stmid_text=&stmid=&minprice=&maxprice=&"\
                 "cmpid_text=&cmpid=&usrid_text=&usrid=&buying%5B%5D=0&stext_none="

    def __init__(self, search):
        self.json_db = TinyDB('hardverapro.json')
        self.new_ads = []
        self.search = search
        self.site_data = ""

    def check_new_ads(self):
        self.open_site()
        self.process_ads()

    def open_site(self):
        site = urllib.request.urlopen(self.SEARCH_URL.format(self.search))
        self.site_data = site.read().decode("utf8")
        site.close()

    def process_ads(self):
        soup = BeautifulSoup(self.site_data, 'html.parser')
        for link in soup.find_all("li", {"class": "media"}):
            try:
                ad = Item(
                    str(link.get('data-uadid')),
                    link.find("div", {"class": "uad-title"}).h1.a.text,
                    link.find("div", {"class": "uad-info"}).find("div", {"class": "uad-price"}).text,
                    str(link.find("div", {"class": "uad-title"}).h1.a.get('href'))
                )
            except AttributeError:
                continue
            if self.not_in_db(ad.adid):
                print(ad)
                self.json_db.insert(ad.__dict__)
                self.new_ads.append(ad)

    def not_in_db(self, adid):
        saved_ads = Query()
        return not self.json_db.search(saved_ads.adid == adid)

    def show_stat(self):
        saved_ads = Query()
        print("New ads: %s" % len(self.new_ads))
        print("Ads in db: %s" % self.json_db.count(saved_ads.adid.exists()))


if __name__ == "__main__":
    search_key = sys.argv[1]
    hrb = HardverapRoBot(search_key)
    hrb.check_new_ads()
    hrb.show_stat()
    print(hrb.new_ads)

    if hrb.new_ads:
        broker = '127.0.0.1'
        client = mqtt.Client("hardverapro")
        client.connect(broker)
        payload = [ob.__dict__ for ob in hrb.new_ads]
        client.publish("hardverapro/"+search_key, payload=json.dumps(payload))
