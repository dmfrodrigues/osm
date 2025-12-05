#!/usr/bin/env python3
import requests
from impl.common import DiffDict, distance, write_diff, overpass_query

def fetch_data():
    url = "https://services1.arcgis.com/zeazWQcjIo4rOOAP/arcgis/rest/services/03_merge_2/FeatureServer/0/query?where=1=1&outFields=*&f=geojson"
    subestaciones = requests.get(url).json()
    
    return subestaciones["features"]

if __name__ == "__main__":
    new_data = fetch_data()
    
    print(len(new_data))

    old_data = [DiffDict(e) for e in overpass_query("""
(
nwr[power=substation](area.country);
);
""", country="ES")]

    new_node_id = -10000
    
    for i,nd in enumerate(new_data):
        public_id = str(nd["properties"]["Name"])
        d = next((od for od in old_data if od["ref_name"] == public_id), None)
        if d is None:
            coord = [nd["geometry"]["coordinates"][1], nd["geometry"]["coordinates"][0]]
            ds = [x for x in old_data if not x["ref_name"] and distance([x.lat, x.lon], coord) < 200]
            if len(ds) == 1:
                d = ds[0]
        if d is None:
            d = DiffDict()
            d.data["type"] = "node"
            d.data["id"] = str(new_node_id)
            d.data["lat"] = nd["geometry"]["coordinates"][1]
            d.data["lon"] = nd["geometry"]["coordinates"][0]
            old_data.append(d)
            new_node_id -= 1

        d["power"] = "substation"
        d["operator"] = "Red Eléctrica de España"
        d["ref_name"] = nd["properties"]["Name"]
        if d["name"] is None:
            d["name"] = "Subestación " + nd["properties"]["Name"].title()

    for d in old_data:
        if d.kind != "old":
            continue
        ref = d["ref_name"]
        if ref and any(nd for nd in new_data if ref == str(nd["properties"]["Name"])):
            continue
        d.kind = "del"

    old_data.sort(key=lambda d: d["ref_name"])

    write_diff("Subestaciones", "ref_name", old_data)