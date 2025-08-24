#!/usr/bin/env python3

import json
import itertools
import re
from multiprocessing import Pool

from lxml import etree

from impl.common import DiffDict, fetch_json_data, fetch_html_data, overpass_query, opening_weekdays, distance, write_diff, titleize


DATA_URL = "https://lbp.pt/associacoes"

REF = "ref"

CITY_FIXES = {
    "Lisbonenses": "Lisboa",
}

COORD = [40, -8]

def fix_city(city):
    city = titleize(city.strip())
    if city in CITY_FIXES:
        return CITY_FIXES[city]
    return city

def fetch_data():
    result = fetch_html_data(DATA_URL)
    result = result.xpath("/html/body/div/div/div/div/div/div/span/a")
    return result

if __name__ == "__main__":
    new_data = fetch_data()
    
    old_data = [DiffDict(e) for e in overpass_query(
"""
(
    nwr[amenity=fire_station](area.country);
);
"""
)]
    
    new_node_id = -10000
    
    for nd in new_data:
        nd = nd.attrib
        public_id = nd["id"]

        d = next((
            od
            for od in old_data
            if od[REF] == public_id
            or od["name"] == nd["mktv_associacoes_title"]
            or od["official_name"] == nd["mktv_associacoes_title"]
        ), None)

        if d is None:
            d = DiffDict()
            d.data["type"] = "node"
            d.data["id"] = str(new_node_id)
            d.data["lat"] = COORD[0]
            d.data["lon"] = COORD[1]
            old_data.append(d)
            new_node_id -= 1
        
        d["amenity"] = "fire_station"

        d["official_name"] = nd["mktv_associacoes_title"]
        d["short_name"] = nd["mktv_associacoes_abreviado"]
        d["start_date"] = nd["mktv_associacoes_fundacao"]
        
        phone = "+351 " + nd["mktv_associacoes_telefone"].strip()
        if phone not in d["contact:phone"].split(";"):
            if d["contact:phone"]:
                d["contact:phone"] += ";"
            d["contact:phone"] += phone

        if d.kind == "new" and not d["addr:street"] and not (d["addr:housenumber"] or d["nohousenumber"] or d["addr:housename"]):
            d["x-dld-addr"] =nd["mktv_associacoes_endereco"]
        
        d["addr:postcode"] = nd["mktv_associacoes_codigo_postal"]
        d["addr:city"] = fix_city(nd["mktv_associacoes_localidade"])
        
        email = nd["mktv_associacoe_emails"].strip()
        if email not in d["contact:email"].split(";"):
            if d["contact:email"]:
                d["contact:email"] += ";"
            d["contact:email"] += nd["mktv_associacoe_emails"]
        
        d["contact:website"] = nd["mktv_associacoes_url"]
        d["contact:facebook"] = nd["mktv_associacoes_facebook"]

    for d in old_data:
        if d.kind != "old":
            continue
        ref = d[REF]
        if ref and any(nd for nd in new_data if ref == nd["id"]):
            continue
        d.kind = "del"
        
    old_data.sort(key=lambda d: d["addr:postcode"])

    write_diff("Firefighters", REF, old_data)

    