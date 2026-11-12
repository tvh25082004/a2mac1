#!/usr/bin/env python3
"""Check whether the 32 columns of hierarchies/{HID}/parts are missing compared to the 247 compare props."""
import json
from pathlib import Path

D = Path("/home/z/my-project/data")
files = sorted((D / "spec_batches").glob("batch_*.json"))
schema = {}
for f in files:
    for g in json.loads(f.read_text())["propertyGroups"]:
        for pr in g["properties"]:
            schema[pr["propertyId"]] = pr["propertyName"]

print("total compare props:", len(schema))
extra = {
    "product": "Product", "part-picture": "Picture",
    "0000000151FTDV01": "VIN", "0000000151FKDV01": "Mileage (Km)",
    "000000AUPWW1EU02": "GVWR (Kg)", "000000AVEUDIEU02": "Platform",
    "00000000TLGGDV01": "Body structure", "00000000TLEZDV01": "Doors",
    "00000000TLGFDV01": "Drive type", "00000000TLFMDV01": "Body style",
    "00000000TLGXDV01": "Vehicle Type", "00000000TLG5DV01": "Production Plant",
    "000000AVEUDLEU02": "Build Date", "A000000KD1C0EU02": "Available Studies",
    "000000AHJGG0EU02": "Program Year", "000000AHJGG1EU02": "Service Type",
    "000000AHJGG2EU02": "Package", "000000AUL513EU02": "Trim Level",
    "00000000TLG4DV01": "Destination Country", "00000000TLFIDV01": "Teardown type",
    "00000000TLF0DV01": "Fuel type",
}
missing = []
for pid, name in extra.items():
    if pid in schema:
        print(f"  ALREADY HAVE: {name:22} = {schema[pid]}")
    else:
        missing.append((pid, name))
print("\nMISSING (need more crawling):")
for pid, name in missing:
    print(f"  {pid} | {name}")
