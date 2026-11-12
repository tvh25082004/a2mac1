# A2MAC1 IBP Crawler — Crawler Guide

All code lives in `scripts/`, raw data in `data/`, final deliverables in `download/`.

## 0. Authentication
- Log in at https://ibp.a2mac1.com → F12 → Application → Cookies → copy the `access_token` value (JWT, valid ~24 minutes).
- Every request carries two headers:
  ```
  Cookie: access_token=<JWT>
  Authorization: Bearer <JWT>
  ```
- Configuration lives in `scripts/.env` (NEVER commit the real token — only `.env.example` is tracked):
  ```
  A2MAC1_TOKEN='<full cookie string>'
  A2MAC1_DELAY=0.25
  ```

## 1. Car list (621 cars)
- Sources: quick-search + products filter v2 (`data/harvest/quicksearch_all.json`, `filters_products_v2.json`).
- Result: `data/products_all.json` — each car has `productId`, `resourceName`, `pictureFile` (cover image + dedicated file token).

## 2. 247 technical specs × 621 cars
- Endpoint: `POST https://ibp.a2mac1.com/api/products/compare/data/by-products?hideMappedProperties=true`
- Body: **array of productIds** (max 25 cars per request — platform limit `compare.max-products=25`).
- Code: `scripts/crawl_specs.py` — splits 621 cars into 25-car batches, saves `data/spec_batches/batch_NNNN.json`, resume state in `data/spec_state.json`.
- Response shape: `{propertyGroups: [...], items: [...], values: {productId: {propertyId: {scenario: [{formatedValue, originalValue, unitLabel}]}}}}`
- The 247 properties span 17 groups (Brand=`00000000TLEEDV01`, Model=`00000000TLEGDV01`, Model Year=`00000000TLDRDV01`).

## 3. Car images (621/621 — COMPLETE)
- 518 public images: blob URL `https://legacystorageeu.blob.core.windows.net/public/...` (from `pictureFile.details.publicUrls.small`) — `scripts/download_images.py`.
- 103 private images (mostly 2025–2026 models, fullHD up to 4496×3000):
  ```
  GET /files/downloads/files?token=<pictureFile.details.token>&api-version=1.1
  ```
  with the JWT attached — code: `scripts/crawl_final.py`. Results: `download/A2MAC1_anh_xe/` + `download/A2MAC1_anh_xe_fullHD/`.

## 4. 3D/CAD part-file catalog (923,551 files / 578 cars — COMPLETE)
- Per-car data package:
  ```
  GET /api/visual/files/packages?productIds=<id1>&productIds=<id2>...   (batches of 25 cars)
  ```
  → returns packageId, **package token**, packageBaseUrl, hierarchyIds (`00000003LSK4EU01` = 3D AutoReverse, `00000005ZT4GEU01` = Vehicle Occupant Packaging).
- 3D files per part:
  ```
  POST /api/visual/files/get-files?api-version=2.0
  body: {"productIds": ["<pid>"], "hierarchyId": "00000003LSK4EU01", "isBookmark": false}
  ```
  → each file: part number, material (Metal > Steel, Plastics > PP…), color, HD/SD, `isDownloadable`, **dedicated token**.
- Code: `scripts/crawl_all.py` / `crawl_all2.py` (throttled version, anti-403). Results: `data/visual_files_summary.json` (per car), `data/packages_all.json`, full sample in `data/visual_files_sample.json`.

## 5. Teardown / 3D Data status per car (420/621)
```
POST /api/hierarchies/A000005AE6M1EU01/parts
body: {"filters": ["product-id eq <productId>"], "sorter": null, "page": {"number": 1, "size": 50}}
params: allowDynamicColumns=true, hideMappedProperties=true
```
→ 12 attributes per record: Package, Status, Teardown Data - Status/Delivery Date, 3D Data - Status, Preliminary/Final Data Delivery. Result: `data/teardown_state.json`.

## 6. Downloading real 3D/CAD files
- Single file: `GET /files/downloads/files?token=<fileToken>&api-version=1.1` (+`filename=`, `applyWatermark=false`).
- Multi-file archive: `POST /downloads` with fileTokens — platform caps **250 visual downloads** (`visual.max-downloads`).
- Account permission: `data.export-download` (granted).

## 7. Final Excel assembly (scripts/build_excel_final.py)
- 108 sheets: brand catalog (hyperlinked) + 104 brand sheets (247 specs × N cars matrix, **image embedded above each car column**) + `3D & Teardown` (621 rows: 3D file count, top 3 materials, teardown status) + `CAD & 3D` (endpoint summary) + Review (COUNTA cross-check — 105/105 PASS).
- Style library: `skills/xlsx/templates/base.py`; QA: recalc → audit → validate.

## ⚠️ Anti-403 lessons learned
- A 403 is often a **temporary warm-up block**: wait 4–5s and retry — it usually clears.
- Scanning ~1,800 requests in 6 minutes (8 threads) triggers a **long 403 block** → use 5 threads + 0.25s delay + 4s backoff on errors.
- Bulk-downloading ~1,700 CAD files in ~11 minutes triggered an app-level block that lasted several hours — pace long download sessions and rotate tokens.
- JWT expires mid-run → every crawler **saves state + resumes** (implemented everywhere).

## Repository layout
```
scripts/          # all crawler + Excel builder code
data/             # raw JSON: products, spec_batches (25 files), visual_files_summary, teardown_state, packages, harvest
download/         # deliverables: A2MAC1_benchmark_full_621_xe.xlsx + image folders
```
