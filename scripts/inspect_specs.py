#!/usr/bin/env python3
"""Inspect spec_batches structure: propertyGroups, values shape, brand coverage."""
import json
from pathlib import Path
from collections import Counter

D = Path("/home/z/my-project/data/spec_batches")
files = sorted(D.glob("batch_*.json"))
print("batch count:", len(files))

b1 = json.loads(files[0].read_text())
pg = b1["propertyGroups"]
total_props = sum(len(g["properties"]) for g in pg)
print(f"propertyGroups: {len(pg)} | total properties: {total_props}")
for g in pg:
    print(f"  - {g['propertyGroupName']}: {len(g['properties'])} props")
    if g["propertyGroupName"] == "Overview":
        for pr in g["properties"][:12]:
            print(f"      {pr['propertyId']} | {pr['propertyName']} | {pr['propertyType']} | {pr['displayType']}")

pid = b1["items"][0]["productId"]
v = b1["values"][pid]
print("\nvalues[pid] keys sample:", list(v.keys())[:10])
k0 = list(v.keys())[0]
print("values[pid][propId] sample:", json.dumps(v[k0], ensure_ascii=False)[:500])
print("propId count with values for vehicle 1:", len(v))

# collect property names globally + brand
all_props = {}
for f in files:
    d = json.loads(f.read_text())
    for g in d["propertyGroups"]:
        for pr in g["properties"]:
            all_props[pr["propertyId"]] = (pr["propertyName"], g["propertyGroupName"])
print("\nTOTAL distinct properties:", len(all_props))

# count brands
brands = Counter()
brand_pid = "00000000TLEEDV01"
missing_brand = 0
n_veh = 0
for f in files:
    d = json.loads(f.read_text())
    for pid, vals in d["values"].items():
        n_veh += 1
        x = vals.get(brand_pid)
        if x:
            fv = x[0].get("formatedValue") if isinstance(x, list) and x else None
            brands[fv] += 1
        else:
            missing_brand += 1
print("vehicles:", n_veh, "| missing Brand:", missing_brand)
print("brands:", dict(sorted(brands.items())))
