#!/usr/bin/env python3
import json
import requests
from datetime import datetime, timezone

from impl.common import DiffDict, fetch_json_data, overpass_query, distance, write_diff

def fetch_data():
    now = datetime.now(timezone.utc)
    res = requests.get("https://locky.westeurope.cloudapp.azure.com//api/v2/locker/public/cache/getAll?countryCode=PT",
        headers={
            "sourceId": "10",
            "sourceName": "Frontend service",
            "sourceDate": now.isoformat(),
        }
    )
    data = res.json()
    return data
  
def processOpeningHours(schedule):
    hours2days_map = {}
    for item in schedule:
        day, openTime, closeTime = item["day"], item["openTime"], item["closeTime"]
        if day == "WEEKDAYS":
            day = [0, 1, 2, 3, 4]
        elif day == "SATURDAY":
            day = [5]
        elif day == "SUNDAY":
            day = [6]
        elif day == "HOLIDAYS":
            day = [7]
        else:
            raise Exception("Unknown days value: {}".format(day))
        
        
        if openTime is None and closeTime is None:
            hours = "off"
        else:
            openTime = openTime[0:5]
            closeTime = closeTime[0:5]
            hours = "{}-{}".format(openTime, closeTime)
            if hours == "00:00-00:00":
                hours = "00:00-24:00"
        
        if hours not in hours2days_map:
            hours2days_map[hours] = []
        hours2days_map[hours].extend(day)
    
    ret = []
    for hours, days in hours2days_map.items():
        if 0 in days and 1 in days and 2 in days and 3 in days and 4 in days and 5 in days and 6 in days:
            day_str = "Mo-Su"
            for d in [0, 1, 2, 3, 4, 5, 6]:
                days.remove(d)
        if 0 in days and 1 in days and 2 in days and 3 in days and 4 in days and 5 in days:
            day_str = "Mo-Sa"
            for d in [0, 1, 2, 3, 4, 5]:
                days.remove(d)
        if 0 in days and 1 in days and 2 in days and 3 in days and 4 in days and 6 in days:
            day_str = "Su-Fr"
            for d in [0, 1, 2, 3, 4, 6]:
                days.remove(d)
        if 0 in days and 1 in days and 2 in days and 3 in days and 4 in days:
            day_str = "Mo-Fr"
            for d in [0, 1, 2, 3, 4]:
                days.remove(d)
        
        if len(days) > 0:
            day_str += "," + ",".join(["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su", "PH"][d] for d in sorted(days))

        ret.append("{} {}".format(day_str, hours))
    
    ret = ";".join(ret)
    if ret == "Mo-Su,PH 00:00-24:00":
        return "24/7"
    
    return ret
        
if __name__ == "__main__":
    new_data = fetch_data()

    old_data = [DiffDict(e) for e in overpass_query(
"""
(
    nwr[amenity=parcel_locker][name~Locky](area.country);
);
"""
)]

    new_node_id = -10000

    for nd in new_data:
        tags_to_reset = set()
        
        public_id = nd["id"]
        d = next((od for od in old_data if od["ref"] == public_id), None)
        if d is None:
            ds = [x for x in old_data if not x["ref"] and distance([x.lat, x.lon], [float(nd["latitude"]), float(nd["longitude"])]) < 100]
            if len(ds) == 1:
                d = ds[0]
        if d is None:
            d = DiffDict()
            d.data["type"] = "node"
            d.data["id"] = str(new_node_id)
            d.data["lat"] = float(nd["latitude"])
            d.data["lon"] = float(nd["longitude"])
            old_data.append(d)
            new_node_id -= 1

        d["amenity"] = "parcel_locker"
        d["name"] = "Locky"
        d["ref_name"] = nd["name"]
        d["note"] = nd["locationInfo"]
        d["capacity"] = nd["totalDoors"]
        d["ref"] = nd["depositPointId"]
        
        assert nd["lockerType"] in ["LOCKER"]
        
        if "lockerDetails" in nd:
            d["addr:full"] = nd["lockerDetails"]["address"]
            d["addr:postcode"] = nd["lockerDetails"]["postalCode"]
            d["addr:city"] = nd["lockerDetails"]["city"]
            if "schedule" in nd["lockerDetails"]:
                d["opening_hours"] = processOpeningHours(nd["lockerDetails"]["schedule"])

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

    write_diff("Locky", "ref", old_data)
