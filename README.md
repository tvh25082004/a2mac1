# A2MAC1 IBP Crawler & Benchmark Data

Complete crawler for the **A2MAC1 IBP** platform (ibp.a2mac1.com) built for vehicle benchmarking: 621 cars × 247 technical specifications, 621/621 car images, a catalog of **923,551 3D/CAD part files** (578 cars) and teardown status for 420 cars — consolidated into a single 108-sheet Excel workbook.

## Download real CAD STL files (GitHub Release — public, free)

**https://github.com/tvh25082004/a2mac1/releases/tag/cad-v1**

| Bundle | Size | Contents |
|---|---|---|
| `CAD-bundle-01.zip` | 1.86GB | 621 STL |
| `CAD-bundle-02.zip` | 1.89GB | 663 STL |
| `CAD-bundle-03.zip` | 1.37GB | 455 STL |

- Download all 3 bundles → **extract everything into the same folder** → you get **1,739 STL files** (`VinFast VF6 Plus 2024/` complete with all 1,670 parts = 100%, plus the first 69 files of `VinFast VF8 Plus 2023/`)
- Each `.stl` is one individual part (source: A2MAC1 IBP, 3D AutoReverse set, hierarchy `00000003LSK4EU01`)
- Full catalog (part names, partIds, sizes): see `CAD-INDEX.md` in this repo
- The remaining 1,934 VF8 files and the Chinese EVs (BYD/Aion/AITO/Chery/Geely) will be added to the Release once A2MAC1 lifts the current 403 block

## Final deliverables (download/)

| File | Description |
|---|---|
| `A2MAC1_benchmark_full_621_xe.xlsx` (8.3 MB) | Final Excel workbook: brand catalog + 104 brand sheets (247 specs × N cars, **car image embedded above each column**) + `3D & Teardown` sheet (621 rows: 3D file count, top 3 materials, teardown/3D status) + `CAD & 3D` sheet (endpoint summary) + Review sheet (105/105 PASS) |
| `A2MAC1_anh_xe/` | 518 car images 300×200 (public images) |
| `A2MAC1_anh_xe_fullHD/` | 103 fullHD images up to 4496×3000 (2025–2026 models, downloaded via file tokens) |
| `A2MAC1_raw_products_621xe.json` | Raw list of all 621 cars |

## How the crawler works

Full details in **[CRAWLER_GUIDE.md](CRAWLER_GUIDE.md)** — endpoints, request bodies, token handling and 403 anti-block lessons:

1. `POST /api/products/compare/data/by-products` — 247 specs (25 cars per request)
2. `GET /files/downloads/files?token=...&api-version=1.1` — private image downloads
3. `POST /api/visual/files/get-files?api-version=2.0` — 3D/CAD files per part
4. `POST /api/hierarchies/A000005AE6M1EU01/parts` — teardown/3D status per car

## Repository layout

```
scripts/     # all crawler code (Python) + Excel builder
data/        # raw JSON: products_all, spec_batches/ (25 batches × 621 cars), visual_files_summary,
             # teardown_state, packages_all, harvest/, frontend JS bundles (used for endpoint discovery)
download/    # final deliverables
```

## Running it again

```bash
pip install requests python-dotenv openpyxl pillow
cp .env.example .env   # paste your access_token
python3 scripts/crawl_specs.py      # 247 specs × 621 cars (resumable)
python3 scripts/crawl_all2.py all   # packages + 3D/CAD files + teardown (throttled, anti-403)
python3 scripts/build_excel_final.py
```

## Token configuration

Copy `.env.example` → `.env` and paste the full cookie string (F12 → Application → Cookies → `access_token`). Tokens last ~24 minutes; every crawler stores state and resumes when a fresh token is provided.

## Notes

- `.env` holds JWT credentials and is **never committed** — only `.env.example` is tracked.
- Data belongs to A2MAC1 (commercial license) — internal benchmark use only.
