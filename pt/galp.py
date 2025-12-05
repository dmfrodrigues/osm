#!/usr/bin/env python3
import requests

from impl.common import DiffDict, overpass_query, distance, write_diff

def fetch_data():
    url = "https://www.galp.com/pt/pt/particulares/estrada/api/filtered-locations"
    response = requests.post(url, json={
        "features": {
            "TANGERINA": False,
        }
    })
    data = response.json()

    print(len(data))
    # print(data[1000])
    
    return data
    
if __name__ == "__main__":
    new_data = fetch_data()
    
    old_data = [DiffDict(e) for e in overpass_query("""
(
nwr[amenity=fuel][brand=Galp](area.country);
);
""", country="PT") + overpass_query("""
(
nwr[amenity=fuel][brand=Galp](area.country);
);
""", country="ES")
]
    
    new_node_id = -10000
    
    values = {}
    
    for nd in new_data:
        for k, v in nd.items():
            if k not in values:
                values[k] = set()
            values[k].add(v)
        
        d = next((od for od in old_data if nd["Id"] in str(od["ref"]).split(";")), None)
        if d is None:
            d = next((od for od in old_data if nd["Id"] in str(od["ref:PT:dgeg"]).split(";") and distance([float(od.lat), float(od.lon)], [float(nd["X_DEG"]), float(nd["Y_DEG"])]) < 200), None)
        if d is None:
            coord = [float(nd["X_DEG"]), float(nd["Y_DEG"])]
            ds = [x for x in old_data if not x["ref"] and distance([x.lat, x.lon], coord) < 50]
            if len(ds) == 1:
                d = ds[0]
        if d is None:
            d = DiffDict()
            d.data["type"] = "node"
            d.data["id"] = str(new_node_id)
            d.data["lat"] = float(nd["X_DEG"])
            d.data["lon"] = float(nd["Y_DEG"])
            old_data.append(d)
            new_node_id -= 1
            
        d["amenity"] = "fuel"
        d["name"] = "Galp"
        d["brand"] = "Galp"
                
        if nd["Id"] not in d["ref"].split(";"):
            if d["ref"]:
                d["ref"] += f";{nd['Id']}"
            else:
                d["ref"] = str(nd["Id"])
        
        d["ref_name"] = nd["Nome"]
        if not d["addr:street"] and not (d["addr:housenumber"] or d["nohousenumber"] or d["addr:housename"]):
            d["x-dld-addr"] = nd["Morada"]
            
        if not d["addr:city"]:
            d["addr:city"] = nd["Localidade"]
        
        if not d["addr:postcode"]:
            d["addr:postcode"] = nd["CodigoPostal"]
        
        if nd["Telefone"]:
            phone = nd["Telefone"]
            if len(phone) == 9:
                phone = "+351 " + phone
            d["contact:phone"] = phone
        if nd["Fax"]:
            d["contact:fax"] = nd["Fax"]
        
        if nd["HORAS24"]:
            d["opening_hours"] = "24/7"
        
        fuel_types = set()
        if nd["ADBLUE"] == "Y":
            fuel_types.add("fuel:adblue")
        if nd["ADBLUE_GARRAFA"] == "Y":
            fuel_types.add("fuel:adblue:canister")
        if nd["AGRICOLA"] == "Y":
            fuel_types.add("fuel:taxfree_diesel")
        if nd["EVOLOGIC_95"] == "Y":
            fuel_types.add("fuel:octane_95")
        if nd["EVOLOGIC_98"] == "Y":
            fuel_types.add("fuel:octane_98")
        if nd["EVOLOGIC_GASOLEO"] == "Y":
            fuel_types.add("fuel:diesel")
        if nd["G_SEMCHUMBO95"] == "Y":
            fuel_types.add("fuel:octane_95")
        if nd["G_SEMCHUMBO98"] == "Y":
            fuel_types.add("fuel:octane_98")
        if nd["GASAUTO"] == "Y":
            fuel_types.add("fuel:lpg")
        if nd["GASOLINASIMPLES95"] == "Y":
            fuel_types.add("fuel:octane_95")
        if nd["GASOLEO"] == "Y":
            fuel_types.add("fuel:diesel")
        if nd["GASOLEOAGRICOLA"] == "Y":
            fuel_types.add("fuel:taxfree_diesel")
        if nd["GASOLEOSIMPLES"] == "Y":
            fuel_types.add("fuel:diesel")
        if nd["GASOLEO_RENOVAVEL_100"] == "Y":
            fuel_types.add("fuel:biodiesel")
        if nd["GASOLEO_RENOVABLE_100"] == "Y":
            fuel_types.add("fuel:biodiesel")
        if nd["GNC"] == "Y":
            fuel_types.add("fuel:cng")
        if nd["GNL"] == "Y":
            fuel_types.add("fuel:lng")
        if nd["HIENERGYDIESEL"] == "Y":
            fuel_types.add("fuel:diesel")
        if nd["HIENERGYGASOLINASP95"] == "Y":
            fuel_types.add("fuel:octane_95")
        if nd["HIENERGYGASOLINASP98"] == "Y":
            fuel_types.add("fuel:octane_98")
        if nd["HVONE"] == "Y":
            fuel_types.add("fuel:biodiesel")
        if nd["LUBRIFICANTES"] == "Y":
            fuel_types.add("fuel:engine_oil")
            
        for ft in fuel_types:
            d[ft] = "yes"
            
        tags_to_reset = set()

        if "fuel:adblue" not in fuel_types:
            tags_to_reset.add("fuel:adblue")
        if "fuel:adblue:canister" not in fuel_types:
            tags_to_reset.add("fuel:adblue:canister")
        if "fuel:taxfree_diesel" not in fuel_types:
            tags_to_reset.add("fuel:taxfree_diesel")
        if "fuel:octane_95" not in fuel_types:
            tags_to_reset.add("fuel:octane_95")
        if "fuel:octane_98" not in fuel_types:
            tags_to_reset.add("fuel:octane_98")
        if "fuel:diesel" not in fuel_types:
            tags_to_reset.add("fuel:diesel")
        if "fuel:biodiesel" not in fuel_types:
            tags_to_reset.add("fuel:biodiesel")
        if "fuel:cng" not in fuel_types:
            tags_to_reset.add("fuel:cng")
        if "fuel:lng" not in fuel_types:
            tags_to_reset.add("fuel:lng")
        if "fuel:engine_oil" not in fuel_types:
            tags_to_reset.add("fuel:engine_oil")
        if "fuel:lpg" not in fuel_types:
            tags_to_reset.add("fuel:lpg")

        if nd["WIFI"] == "Y":
            d["internet_access"] = "wlan"
        
        
        website = f"https://www.galp.com/pt/pt/particulares/estrada/mapa/{nd['Id']}"
        if d["website"]:
            d["website"] = website
        else:
            d["contact:website"] = website
            
        for key in tags_to_reset:
            if d[key]:
                d[key] = ""

    for d in old_data:
        if d.kind != "old":
            continue
        if d["ref"] and any(nd for nd in new_data if nd["Id"] in d["ref"].split(";")):
            continue
        d.kind = "del"

    old_data.sort(key=lambda d: d["ref"])

    write_diff("Galp", "Id", old_data)
