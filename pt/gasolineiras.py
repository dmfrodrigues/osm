#!/usr/bin/env python3
import geopandas as gpd
import requests
from io import BytesIO

from impl.common import DiffDict, fetch_json_data, fetch_html_data, overpass_query, opening_weekdays, distance, write_diff, titleize

REF = "ref:PT:dgeg"

TITLEIZE_FIXES = {
    "Bp": "BP",
    "Oz Energia": "OZ Energia",
}

def fetch_data():
    WFS_URL = "https://servergeo.dgeg.gov.pt/arcgis/services/Visualizadores/PACVR/MapServer/WFSServer"
    typename = "PACVR:Postos_Abastecimento"
    url = f"WFS:{WFS_URL}?service=WFS&version=2.0.0&request=GetFeature&typeNames={typename}"

    gdf = gpd.read_file(url, driver="WFS")
    
    return gdf.to_dict(orient="records")

if __name__ == "__main__":
    new_data = fetch_data()

    old_data = [DiffDict(e) for e in overpass_query("""
(
nwr(36,-10,43,-6)[amenity=fuel](area.country);
);
""")]
    
    new_node_id = -10000
    
    for nd in new_data:
        public_id = nd["Código_Posto"]
        d = next((od for od in old_data if od[REF] == public_id), None)
        if d is None:
            coord = [nd["Latitude__Y_"], nd["Longitude__X_"]]
            ds = [x for x in old_data if not x[REF] and distance([x.lat, x.lon], coord) < 100]
            if len(ds) == 1:
                d = ds[0]
        if d is None:
            d = DiffDict()
            d.data["type"] = "node"
            d.data["id"] = str(new_node_id)
            d.data["lat"] = nd["Latitude__Y_"]
            d.data["lon"] = nd["Longitude__X_"]
            old_data.append(d)
            new_node_id -= 1

        d[REF] = public_id
        d["amenity"] = "fuel"
        
        marca = titleize(nd["Marca"])
        if marca in TITLEIZE_FIXES:
            marca = TITLEIZE_FIXES[marca]
        if marca != "Genérico":        
            d["name"] = marca
            if marca not in d["brand"].split(";"):
                if d["brand"]:
                    d["brand"] += ";" + marca
                else:
                    d["brand"] = marca
        d["ref:inspire"] = nd["Inspire_ID"]

    for d in old_data:
        if d.kind != "old":
            continue
        ref = d[REF]
        if ref and any(nd for nd in new_data if ref == nd["Código_Posto"]):
            continue
        d.kind = "del"

    old_data.sort(key=lambda d: d[REF])

    write_diff("Gasolineiras", REF, old_data)