#!/usr/bin/env python3
from arcgis.gis import GIS
from arcgis.features import FeatureLayer

from impl.common import DiffDict, distance, write_diff, overpass_query, titleize

def fetch_data():
    gis = GIS()

    url = "https://services5.arcgis.com/j4eW900wJsR0Vv9G/arcgis/rest/services/PR26_FSTarefa/FeatureServer/0"
    layer = FeatureLayer(url)

    features = layer.query(
        where="1=1",
        out_fields="*",
        return_geometry=True,
        result_record_count=10000
    )
    
    return [f.attributes for f in features.features]

if __name__ == "__main__":
    new_data = fetch_data()
    
    print(len(new_data))

    old_data = [DiffDict(e) for e in overpass_query("""
(
nwr[polling_station=yes](area.country);
);
""")]
    
    new_node_id = -10000
    
    for i,nd in enumerate(new_data):
        public_id = str(nd["id"])
        d = next((od for od in old_data if od["polling_station:ref"] == public_id), None)
        if d is None:
            coord = [nd["latitude"], nd["longitude"]]
            ds = [x for x in old_data if not x["polling_station:ref"] and distance([x.lat, x.lon], coord) < 100]
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

        d["polling_station"] = "yes"
        d["polling_station:ref"] = public_id
        d["polling_station:ref_name"] = nd["nome"]
        d["polling_station:zone"] = nd["codigo"]
        
        if not d["addr:street"] and not (d["addr:housenumber"] or d["nohousenumber"] or d["addr:housename"]):
            d["addr:full"] = nd["morada"]
        
        d["addr:postcode"] = nd["codigoPostal"]
        d["addr:city"] = titleize(nd["localidadePostal"])
        d["polling_station:number_of_sections"] = nd["numMesas"]

    for d in old_data:
        if d.kind != "old":
            continue
        ref = d["polling_station:ref"]
        if ref and any(nd for nd in new_data if ref == str(nd["id"])):
            continue
        d.kind = "del"

    old_data.sort(key=lambda d: d["polling_station:ref"])

    write_diff("Locais de voto", "polling_station:ref", old_data)
