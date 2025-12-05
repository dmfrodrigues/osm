#!/usr/bin/env python3
import requests

from impl.common import DiffDict, distance, write_diff, overpass_query, titleize

def fetch_data():
    url = "https://www.mbway.pt/wp-admin/admin-ajax.php?action=asl_load_stores"
    resp = requests.get(url)
    resp.raise_for_status()
    data = resp.json()
    return data

if __name__ == "__main__":
    new_data = fetch_data()
    
    print(len(new_data))

    old_data = [DiffDict(e) for e in overpass_query("""
(
nwr[amenity=atm](area.country);
);
""")]
    
    new_node_id = -10000
    
    for i,nd in enumerate(new_data):
        public_id = str(nd["id"])
        d = next((od for od in old_data if od["ref"] == public_id), None)
        if d is None:
            coord = [nd["latitude"], nd["longitude"]]
            ds = [x for x in old_data if not x["ref"] and distance([x.lat, x.lon], coord) < 100]
            if len(ds) == 1:
                d = ds[0]
        if d is None:
            d = DiffDict()
            d.data["type"] = "node"
            d.data["id"] = str(new_node_id)
            d.data["lat"] = nd["latitude"]
            d.data["lon"] = nd["longitude"]
            old_data.append(d)
            new_node_id -= 1

        d["amenity"] = "atm"
        d["ref"] = public_id
        d["ref_name"] = nd["title"]
        
        # TODO: Divide postcode into components
        d["addr:postcode"] = nd["postal_code"]
        d["addr:full"] = nd["street"]

    for d in old_data:
        if d.kind != "old":
            continue
        ref = d["ref"]
        if ref and any(nd for nd in new_data if ref == str(nd["id"])):
            continue
        d.kind = "del"

    old_data.sort(key=lambda d: d["ref"])

    write_diff("Multibanco", "ref", old_data)
