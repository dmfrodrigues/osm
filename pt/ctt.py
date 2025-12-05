#!/usr/bin/env python3
import json
import itertools
import re
from multiprocessing import Pool
import requests
from bs4 import BeautifulSoup

from lxml import etree

from impl.common import DiffDict, fetch_json_data, fetch_html_data, overpass_query, opening_weekdays, distance, write_diff, titleize

def flatten(list_of_lists):
    return list(itertools.chain.from_iterable(list_of_lists))

def getAddress(article):
    addr = article.find("div", class_="posRelative").text
    pos = addr.find("(Ver no mapa)")
    if pos != -1:
        addr = addr[:pos]
    return addr.strip()

def getPostCodeAndCity(article):
    addr = article.find("div", class_="posRelative").text
    pos = addr.find("(Ver no mapa)")
    if pos != -1:
        addr = addr[(pos+13):]
    pos = addr.find("Telefone:")
    if pos != -1:
        addr = addr[:pos]
    return addr.strip()

def getPostCode(article):
    return getPostCodeAndCity(article).split(" ", 1)[0]
    
def getCity(article):
    return titleize(getPostCodeAndCity(article).split(" ", 1)[1])

def getOpeningHours(article):
    items = article.find("ul", class_="list-check").find_all("li")
    for i in range(len(items)):
        item = items[i].text.strip().replace("\t", "").replace("\n", "").replace("\r", "")
        if item.startswith("Dias úteis:"):
            item = item.replace("Dias úteis:", "Mo-Fr ")
        elif item.startswith("2ª:"):
            item = item.replace("2ª:", "Mo ")
        elif item.startswith("3ª:"):
            item = item.replace("3ª:", "Tu ")
        elif item.startswith("4ª:"):
            item = item.replace("4ª:", "We ")
        elif item.startswith("5ª:"):
            item = item.replace("5ª:", "Th ")
        elif item.startswith("6ª:"):
            item = item.replace("6ª:", "Fr ")
        elif item.startswith("2ªadomingoeferiados:"):
            item = item.replace("2ªadomingoeferiados:", "Mo-Su ")
        elif item.startswith("2ªadomingo:"):
            item = item.replace("2ªadomingo:", "Mo-Su ")
        elif item.startswith("2ªasábado:"):
            item = item.replace("2ªasábado:", "Mo-Sa ")
        elif item.startswith("2ªe3ª:"):
            item = item.replace("2ªe3ª:", "Mo-Tu ")
        elif item.startswith("2ªa5ª:"):
            item = item.replace("2ªa5ª:", "Mo-Th ")
        elif item.startswith("2ªa4ª:"):
            item = item.replace("2ªa4ª:", "Mo-We ")
        elif item.startswith("3ªasábado:"):
            item = item.replace("3ªasábado:", "Tu-Sa ")
        elif item.startswith("3ªadomingo:"):
            item = item.replace("3ªadomingo:", "Tu-Su ")
        elif item.startswith("3ªadomingoeferiados:"):
            item = item.replace("3ªadomingoeferiados:", "Tu-Su ")
        elif item.startswith("3ªa6ª:"):
            item = item.replace("3ªa6ª:", "Tu-Fr ")
        elif item.startswith("3ªe4ª:"):
            item = item.replace("3ªe4ª:", "Tu-We ")
        elif item.startswith("4ªa6ª:"):
            item = item.replace("4ªa6ª:", "We-Fr ")
        else:
            raise Exception(f"Unexpected opening hours format '{item}'")
        i1, i2 = item.split(" ", 1)
        i2 = i2.replace(" ", "")
        item = f"{i1} {i2}"
        items[i] = item
        
    return items

def getPhone(article):
    phones = [a for a in article.find_all("a") if a["href"].startswith("tel:")]
    if len(phones) == 0:
        return None
    return phones[0]["href"].replace("tel:00351", "+351 ").strip()

def getLatLon(article):
    r = re.findall(r"q=([0-9\.-]+),([0-9\.-]+)", article.find("a")["href"])
    if len(r) == 0:
        return (40.0, -8.0)
    return (float(r[0][0]), float(r[0][1]))

def requestCTT(district, page="1"):
    return requests.post("https://appserver2.ctt.pt/feapl_2/app/open/stationSearch/search.jspx", 
        data=f"stationType=EC%2CPC%2CPARC&district={district}&currentPage={page}&__checkbox_pointServiceCodes=0000.0000.0013&__checkbox_pointServiceCodes=0000.0000.0012&__checkbox_pointServiceCodes=0000.0000.0014&__checkbox_pointServiceCodes=0000.0000.0010&__checkbox_pointServiceCodes=0000.0000.0009&__checkbox_pointServiceCodes=0000.0000.0011&__checkbox_pointServiceCodes=0000.0000.0004&__checkbox_pointServiceCodes=0000.0000.0003&__checkbox_pointServiceCodes=0000.0000.0002&__checkbox_pointServiceCodes=0000.0000.0001&__checkbox_pointServiceCodes=0000.0000.0016&__checkbox_pointServiceCodes=0000.0000.0015&__checkbox_pointServiceCodes=0000.0000.0005&__checkbox_pointServiceCodes=0000.0000.0006&__checkbox_pointServiceCodes=0000.0000.0008&__checkbox_pointServiceCodes=0000.0000.0007&__checkbox_pointServiceCodes=0004.0001.0001&__checkbox_pointServiceCodes=0001.0011.0001&__checkbox_pointServiceCodes=0001.0010.0003&__checkbox_pointServiceCodes=0001.0010.0004&__checkbox_pointServiceCodes=0001.0009.0001&__checkbox_pointServiceCodes=0001.0009.0002&__checkbox_pointServiceCodes=0001.0009.0003&__checkbox_pointServiceCodes=0001.0012.0004&__checkbox_pointServiceCodes=0001.0014.0001&__checkbox_pointServiceCodes=0001.0012.0003&__checkbox_pointServiceCodes=0001.0002.0001&__checkbox_pointServiceCodes=0001.0002.0002&__checkbox_pointServiceCodes=0001.0006.0001&__checkbox_pointServiceCodes=0001.0001.0001&__checkbox_pointServiceCodes=0001.0004.0001&__checkbox_pointServiceCodes=0001.0004.0002&__checkbox_pointServiceCodes=0001.0003.0001&__checkbox_pointServiceCodes=0001.0012.0001&__checkbox_pointServiceCodes=0001.0007.0001&__checkbox_pointServiceCodes=0001.0005.0014&__checkbox_pointServiceCodes=0001.0005.0004&__checkbox_pointServiceCodes=0001.0005.0005&__checkbox_pointServiceCodes=0001.0005.0003&__checkbox_pointServiceCodes=0001.0005.0010&__checkbox_pointServiceCodes=0001.0013.0001&__checkbox_pointServiceCodes=0001.0010.0001&__checkbox_pointServiceCodes=0001.0010.0002&__checkbox_pointServiceCodes=0001.0012.0002&__checkbox_pointServiceCodes=0001.0008.0001&__checkbox_pointServiceCodes=0002.0004.0011&__checkbox_pointServiceCodes=0002.0004.0012&__checkbox_pointServiceCodes=0002.0007.0002&__checkbox_pointServiceCodes=0002.0007.0001&__checkbox_pointServiceCodes=0002.0001.0002&__checkbox_pointServiceCodes=0002.0001.0001&__checkbox_pointServiceCodes=0002.0004.0010&__checkbox_pointServiceCodes=0002.0004.0009&__checkbox_pointServiceCodes=0002.0006.0003&__checkbox_pointServiceCodes=0002.0006.0001&__checkbox_pointServiceCodes=0002.0006.0002&__checkbox_pointServiceCodes=0002.0006.0005&__checkbox_pointServiceCodes=0002.0002.0001&__checkbox_pointServiceCodes=0002.0004.0008&__checkbox_pointServiceCodes=0002.0005.0001&__checkbox_pointServiceCodes=0002.0003.0001&__checkbox_pointServiceCodes=0003.0002.0005&__checkbox_pointServiceCodes=0003.0015.0001&__checkbox_pointServiceCodes=0003.0001.0001&__checkbox_pointServiceCodes=0003.0011.0001&__checkbox_pointServiceCodes=0003.0013.0001&__checkbox_pointServiceCodes=0003.0003.0001&__checkbox_pointServiceCodes=0003.0007.0001&__checkbox_pointServiceCodes=0003.0019.0002&__checkbox_pointServiceCodes=0003.0003.0003&__checkbox_pointServiceCodes=0003.0004.0001&__checkbox_pointServiceCodes=0003.0002.0003&__checkbox_pointServiceCodes=0003.0019.0001&__checkbox_pointServiceCodes=0003.0009.0001&__checkbox_pointServiceCodes=0003.0012.0001&__checkbox_pointServiceCodes=0003.0017.0001&__checkbox_pointServiceCodes=0003.0017.0002&__checkbox_pointServiceCodes=0003.0015.0002&__checkbox_pointServiceCodes=0003.0010.0001&__checkbox_pointServiceCodes=0003.0003.0002&__checkbox_pointServiceCodes=0003.0018.0001&__checkbox_pointServiceCodes=0003.0002.0006&__checkbox_pointServiceCodes=0003.0005.0001&__checkbox_pointServiceCodes=0003.0014.0002&__checkbox_pointServiceCodes=0003.0003.0004&__checkbox_pointServiceCodes=0003.0002.0001&__checkbox_pointServiceCodes=0003.0002.0002&__checkbox_pointServiceCodes=0003.0006.0001",
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:145.0) Gecko/20100101 Firefox/145.0",
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.5",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "X-Requested-With": "XMLHttpRequest",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "Priority": "u=0",
            "Pragma": "no-cache",
            "Cache-Control": "no-cache"
        }
    )

def numberEntries(district):
    response = requestCTT(district)
    soup = BeautifulSoup(response.text, 'html.parser')
    entriesEl = soup.find("strong")
    if entriesEl is not None:
        entriesText = entriesEl.text.strip().split(" ")[0]
        return int(entriesText)
    if soup.text.find("Foi encontrado 1 ponto CTT") != -1:
        return 1
    raise Exception("Could not find number of entries")

def entries(args):
    district, page = args
    print(f"    District {district}, page {page}")
    response = requestCTT(district, page)
    soup = BeautifulSoup(response.text, 'html.parser')
    return [
        {
            "name": article.find("h3").text.strip(),
            "latlon": getLatLon(article),
            "address": getAddress(article),
            "postCode": getPostCode(article),
            "city": getCity(article),
            "phone": getPhone(article),
            "id": article.find("a", class_="collapsible-open")["onclick"].split("(")[1].split(")")[0],
            "openingHours": getOpeningHours(article)
        }
        for article in soup.find_all("article")
    ]

PAGE_SIZE = 5

def fetch_data_district(district):
    numEntries = numberEntries(district)
    numPages = (numEntries // PAGE_SIZE) + (1 if (numEntries % PAGE_SIZE) > 0 else 0)
    print(f"  District {district} has {numEntries} entries ({numPages} pages)")
    pages = [(district, p) for p in range(1, numPages+1)]

    with Pool(8) as p:
        data = p.map(entries, pages)
    
    data = flatten(data)
    
    return data

def fetch_data():
    districts = {
        "Aveiro": "010000",
        "Beja": "020000",
        "Braga": "030000",
        "Bragança": "040000",
        "Castelo Branco": "050000",
        "Coimbra": "060000",
        "Évora": "070000",
        "Faro": "080000",
        "Guarda": "090000",
        "Leiria": "100000",
        "Lisboa": "110000",
        "Portalegre": "120000",
        "Porto": "130000",
        "Santarém": "140000",
        "Setúbal": "150000",
        "Viana do Castelo": "160000",
        "Vila Real": "170000",
        "Viseu": "180000",
        "Ilha da Madeira": "310000",
        "Ilha de Porto Santo": "320000",
        "Ilha de Santa Maria": "410000",
        "Ilha de São Miguel": "420000",
        "Ilha Terceira": "430000",
        "Ilha da Graciosa": "440000",
        "Ilha de São Jorge": "450000",
        "Ilha do Pico": "460000",
        "Ilha do Faial": "470000",
        "Ilha das Flores": "480000",
        "Ilha do Corvo": "490000",
    }
    stores = []
    for name, code in districts.items():
        print(name)
        new_stores = fetch_data_district(code)
        print(f"{name}: {len(new_stores)}")
        stores.extend(new_stores)
    return stores

if __name__ == "__main__":
    new_data = fetch_data()

    old_data = [DiffDict(e) for e in overpass_query(
"""
(
    nwr[amenity=post_office][name~CTT](area.country);
    nwr[amenity=post_office][operator~CTT](area.country);
    nwr[amenity=post_office][brand~CTT](area.country);

    nwr[amenity=post_office][!brand][!operator](area.country);
    
    nwr[amenity~payment_centre][brand=Payshop](area.country);
    
    nwr[post_office=post_partner]["post_office:brand"~CTT](area.country);
);
"""
)]

    new_node_id = -10000

    for nd in new_data:
        tags_to_reset = set()
        
        public_id = nd["id"]
        d = next((od for od in old_data if od["ref"] == public_id), None)
        if d is None:
            coord = nd["latlon"]
            ds = [x for x in old_data if not x["ref"] and distance([x.lat, x.lon], coord) < 50]
            if len(ds) == 1:
                d = ds[0]
        if d is None:
            d = DiffDict()
            d.data["type"] = "node"
            d.data["id"] = str(new_node_id)
            d.data["lat"] = nd["latlon"][0]
            d.data["lon"] = nd["latlon"][1]
            old_data.append(d)
            new_node_id -= 1

        if nd["name"].startswith("Loja CTT"):
            d["amenity"] = "post_office"
            d["name"] = "CTT"
            d["branch"] = nd["name"].replace("Loja CTT ", "")
            d["brand"] = "CTT"
            d["brand:wikidata"] = "Q1024518"
            d["operator"] = "CTT"
            d["operator:wikidata"] = "Q1024518"
            d["ref"] = public_id
            d["ref_name"] = nd["name"]
        elif nd["name"].startswith("Cacifo Locky"):
            d["amenity"] = "parcel_locker"
            d["name"] = "Locky"
            d["brand"] = "Locky"
            d["brand:wikidata"] = "Q127548459"
            d["operator"] = "CTT"
            d["operator:wikidata"] = "Q1024518"
            d["ref"] = public_id
            d["ref_name"] = nd["name"]
        elif nd["name"].startswith("Payshop"):
            if "payment_centre" not in d["amenity"].split(";"):
                d["amenity"] = "payment_centre"
            d["payment_centre:brand"] = "Payshop"
            d["payment_centre:ref"] = public_id
            d["payment_centre:ref_name"] = nd["name"]
        else:
            d["post_office"] = "post_partner"
            d["post_office:brand"] = "CTT"
            d["post_office:brand:wikidata"] = "Q1024518"
            d["post_office:ref"] = public_id
            d["post_office:ref_name"] = nd["name"]
        
        d["addr:postcode"] = nd["postCode"]
        d["addr:city"] = nd["city"]
        d["opening_hours"] = ";".join(nd["openingHours"])
        
        if not d["addr:street"] and not (d["addr:housenumber"] or d["nohousenumber"] or d["addr:housename"]):
            d["x-dld-addr"] = titleize(nd["address"])
            
        if d["phone"]:
            d["phone"] = nd["phone"]
        else:
            d["contact:phone"] = nd["phone"]

        for key in tags_to_reset:
            if d[key]:
                d[key] = ""

    for d in old_data:
        if d.kind != "old":
            continue
        ref = d["ref"]
        if ref and any(nd for nd in new_data if ref == nd["id"]):
            continue
        d.kind = "del"

    old_data.sort(key=lambda d: d["ref"])

    write_diff("CTT", "ref", old_data)
