#!/usr/bin/env python3
"""Phân tích offline: head 32 cột của parts, tree hierarchy, cấu trúc part row."""
import json
from pathlib import Path

D = Path("/home/z/my-project/data")

# 1) parts sample: head + rows
p = D / "hier_parts_sample.json"
if p.exists():
    d = json.loads(p.read_text())
    print("=== HEAD 32 cột của parts ===")
    for h in d["head"]:
        print(f"   {h['id'][:26]:26} | {h['type']:12} | {h.get('value')}")
    print("\n=== 3 row mẫu ===")
    for row in d["rows"][:3]:
        data = row["data"]
        print(f"row id: {row['id']}")
        for k, v in data.items():
            if v and isinstance(v, list):
                fv = v[0].get("formatedValue")
                ov = v[0].get("originalValue")
                if fv is not None and str(fv) != str(ov):
                    print(f"   {k[:26]:26} -> {str(fv)[:60]} (orig {str(ov)[:30]})")
                elif fv is not None:
                    print(f"   {k[:26]:26} -> {str(fv)[:60]}")
    print("tổng rows trang 1:", len(d["rows"]))

# 2) tree hierarchy
p = D / "hierarchy_tree.json"
if p.exists():
    d = json.loads(p.read_text())
    nodes = d.get("hierarchyNodes", [])
    print(f"\n=== TREE hierarchy: {len(nodes)} nodes ===")
    for n in nodes[:12]:
        print(f"   {n['id']} | L{n['level']} | {n['name']} | hasChildren={n.get('hasChildren')}")
    lv = {}
    for n in nodes:
        lv[n["level"]] = lv.get(n["level"], 0) + 1
    print("   theo level:", lv)

# 3) hierarchies 3d
p = D / "hierarchies_3d.json"
if p.exists():
    d = json.loads(p.read_text())
    print(f"\n=== hierarchies-3d: {len(d)} mục ===")
    for x in d[:10]:
        print(f"   {x['id']} | {x['value']}")

# 4) parts theo product
p = D / "parts_by_product_sample.json"
if p.exists():
    d = json.loads(p.read_text())
    print(f"\n=== parts BY PRODUCT (Acura MDX 2022): {len(d['rows'])} rows ===")
    for row in d["rows"]:
        data = row["data"]
        interesting = {}
        for k, v in data.items():
            if v and isinstance(v, list) and v[0].get("formatedValue") is not None:
                interesting[k] = v[0]["formatedValue"]
        print(f"   id={row['id']}: {json.dumps(interesting, ensure_ascii=False)[:300]}")
    print("head:", [h.get('value') for h in d["head"]])
