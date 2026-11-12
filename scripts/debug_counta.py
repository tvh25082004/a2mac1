#!/usr/bin/env python3
"""Debug: why COUNTA returns n+1 for each brand sheet."""
from pathlib import Path
from openpyxl import load_workbook

OUT = Path("/home/z/my-project/download/A2MAC1_thong_so_ky_thuat_621_xe.xlsx")
wbf = load_workbook(OUT)              # formulas
wbv = load_workbook(OUT, data_only=True)  # cached values

wsf, wsv = wbf["Acura"], wbv["Acura"]
print("formula D6 (Review):", wbf["Review"]["D6"].value)
print("cached  D6:", wbv["Review"]["D6"].value, "| E6:", wbv["Review"]["E6"].value)
for r in range(6, 12):
    print(f"Acura B{r}:", repr(wsv.cell(row=r, column=2).value))
print("max_row Acura:", wsv.max_row)
