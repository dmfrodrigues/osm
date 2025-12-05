#!/usr/bin/env python3
import geopandas as gpd
import requests
from io import BytesIO

from impl.common import DiffDict, fetch_json_data, fetch_html_data, overpass_query, opening_weekdays, distance, write_diff, titleize

TITLEIZE_FIXES = {
    "Bp": "BP",
    "Oz Energia": "OZ Energia",
    "Auto Julio": "Auto Júlio",
    "Beq": "beq",
    "Bombagás": "BombaGás",
    "Dourogas Natural": "Dourogás",
    "Petroibérica": "PetroIbérica",
    "Leclerc": "E.Leclerc",
}

def fetch_data():
    url = "https://precoscombustiveis.dgeg.gov.pt/api/PrecoComb/PesquisarPostos?qtdPorPagina=100000"
    response = requests.get(url, verify=False).json()

    response = response["resultado"]

    """
    keys_values = {}
    
    for r in response:
        for k, v in r.items():
            if k not in keys_values:
                keys_values[k] = set()
            keys_values[k].add(v)

    for k, v in keys_values.items():
        print(f"{k}: {len(v)} unique values")
        
    print(f"TipoPosto values: {keys_values.get('TipoPosto', [])}")
    """

    gasolineiras = {}
    for r in response:
        if r["Id"] not in gasolineiras:
            gasolineiras[r["Id"]] = {
                k: (v if type(v) is not str else ' '.join(v.split())) for k, v in r.items() if k not in ["Combustivel", "Preco", "DataAtualizacao", "Quantidade"]
            }
            gasolineiras[r["Id"]]["Combustíveis"] = set()
        gasolineiras[r["Id"]]["Combustíveis"].add(
           r["Combustivel"]
        )

    return gasolineiras.values()

if __name__ == "__main__":
    new_data = fetch_data()
    
    print(f"Fetched {len(new_data)} gasoline stations from Preço dos Combustíveis portal")

    old_data = [DiffDict(e) for e in overpass_query("""
(
nwr(36,-10,43,-6)[amenity=fuel](area.country);
);
""")]
    
    new_data_refs = set()
    for nd in new_data:
        new_data_refs.add(str(nd["Nome"]))
    
    for od in old_data:
        ref_name = od["ref_name:PT:dgeg:precos-combustiveis"]
        if ref_name:
            for r in ref_name.split(";"):
                if r not in new_data_refs:
                    print(f"Old ref_name not found in new data: {r} in {od}")
    
    """
    ref_names = {}
    for nd in new_data:
        ref_name = str(nd["Nome"])
        if ref_name in ref_names:
            print(f"Duplicate ref_name detected: {ref_names[ref_name]} and {nd} both have ref_name '{ref_name}'")
        ref_names[ref_name] = nd
    """

    new_node_id = -10000
    
    for nd in new_data:
        d = next((od for od in old_data if nd["Nome"] in str(od["ref_name:PT:dgeg:precos-combustiveis"]).split(";") and od["addr:postcode"] == nd["CodPostal"]), None)
        if d is None:
            coord = [nd["Latitude"], nd["Longitude"]]
            ds = [x for x in old_data if not x["ref_name:PT:dgeg:precos-combustiveis"] and distance([x.lat, x.lon], coord) < 50]
            if len(ds) == 1:
                d = ds[0]
        if d is None:
            d = DiffDict()
            d.data["type"] = "node"
            d.data["id"] = str(new_node_id)
            d.data["lat"] = nd["Latitude"]
            d.data["lon"] = nd["Longitude"]
            old_data.append(d)
            new_node_id -= 1

        d["amenity"] = "fuel"

        if nd["Nome"] not in d["ref_name:PT:dgeg:precos-combustiveis"]:
            if d["ref_name:PT:dgeg:precos-combustiveis"]:
                d["ref_name:PT:dgeg:precos-combustiveis"] += ";"+nd["Nome"]
            else:
                d["ref_name:PT:dgeg:precos-combustiveis"] = nd["Nome"]

        marca = titleize(nd["Marca"])
        if marca in TITLEIZE_FIXES:
            marca = TITLEIZE_FIXES[marca]
        if marca != "Genérico":
            d["name"] = marca
            if marca not in d["brand"].split(";"):
                if d["brand"]:
                    d["brand"] += ";"+marca
                else:
                    d["brand"] = marca
        
        d["addr:postcode"] = nd["CodPostal"]
        d["addr:city"] = nd["Localidade"]

        d["x-dld-ref"] = nd["Id"]

        if not d["addr:street"] and not (d["addr:housenumber"] or d["nohousenumber"] or d["addr:housename"]):
            d["x-dld-addr"] = nd["Morada"]
        
        fuel_types = set()
        for tipo in nd["Combustíveis"]:
            if tipo =='Gasóleo simples':
                fuel_types.add("fuel:diesel")
            elif tipo =='Gasóleo colorido':
                fuel_types.add("fuel:diesel")
            elif tipo =='Gasóleo (até setembro 2021)':
                fuel_types.add("fuel:diesel")
            elif tipo =='Gasóleo especial':
                fuel_types.add("fuel:diesel")
            elif tipo == 'Biodiesel B15':
                fuel_types.add("fuel:diesel_b15")
            elif tipo =='Gasolina simples 95':
                fuel_types.add("fuel:octane_95")
            elif tipo == 'Gasolina especial 95':
                fuel_types.add("fuel:octane_95")
            elif tipo =='Gasolina 95 (até setembro 2021)':
                fuel_types.add("fuel:octane_95")
            elif tipo =='Gasolina 98':
                fuel_types.add("fuel:octane_98")
            elif tipo =='Gasolina especial 98':
                fuel_types.add("fuel:octane_98")
            elif tipo =='Gasolina de mistura (motores a 2 tempos)':
                fuel_types.add("fuel:1_50")
            elif tipo == 'GNC (gás natural comprimido) - €/kg':
                fuel_types.add("fuel:cng")
            elif tipo =='GNC (gás natural comprimido) - €/m3':
                fuel_types.add("fuel:cng")
            elif tipo =='GPL Auto':
                fuel_types.add("fuel:lpg")
            elif tipo =='GNL (gás natural liquefeito) - €/kg':
                fuel_types.add("fuel:lng")
            elif tipo =='Gasóleo de aquecimento':
                fuel_types.add("fuel:heating_oil")
            else:
                raise Exception(f"Unknown fuel type: {tipo}")
        
        for ft in fuel_types:
            d[ft] = "yes"
        
        tags_to_reset = set()

        if "fuel:diesel" not in fuel_types:
            tags_to_reset.add("fuel:diesel")
        if "fuel:diesel_b15" not in fuel_types:
            tags_to_reset.add("fuel:diesel_b15")
        if "fuel:octane_95" not in fuel_types:
            tags_to_reset.add("fuel:octane_95")
        if "fuel:octane_98" not in fuel_types:
            tags_to_reset.add("fuel:octane_98")
        if "fuel:1_50" not in fuel_types:
            tags_to_reset.add("fuel:1_50")
        if "fuel:cng" not in fuel_types:
            tags_to_reset.add("fuel:cng")
        if "fuel:lpg" not in fuel_types:
            tags_to_reset.add("fuel:lpg")
        if "fuel:lng" not in fuel_types:
            tags_to_reset.add("fuel:lng")
        if "fuel:heating_oil" not in fuel_types:
            tags_to_reset.add("fuel:heating_oil")

        for key in tags_to_reset:
            if d[key]:
                d[key] = ""

    for d in old_data:
        if d.kind != "old":
            continue
        if (d["ref_name:PT:dgeg:precos-combustiveis"] and d["addr:postcode"]) and any(nd for nd in new_data if nd["Nome"] in d["ref_name:PT:dgeg:precos-combustiveis"].split(";") and d["addr:postcode"] == nd["CodPostal"]):
            continue
        d.kind = "del"

    old_data.sort(key=lambda d: d["ref_name:PT:dgeg:precos-combustiveis"])

    write_diff("Gasolineiras (Portal do Preço dos Combustíveis)", "Id", old_data)