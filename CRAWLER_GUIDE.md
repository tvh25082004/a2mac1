# A2MAC1 IBP Crawler — Hướng dẫn cách crawl (CRAWLER GUIDE)

Toàn bộ code nằm trong `scripts/`, dữ liệu thô trong `data/`, sản phẩm cuối trong `download/`.

## 0. Xác thực (Authentication)
- Đăng nhập https://ibp.a2mac1.com → F12 → Application → Cookies → copy giá trị `access_token` (JWT, hạn ~24 phút).
- Mọi request gửi kèm 2 header:
  ```
  Cookie: access_token=<JWT>
  Authorization: Bearer <JWT>
  ```
- Cấu hình trong `scripts/.env` (KHÔNG commit token thật — chỉ có `.env.example`):
  ```
  A2MAC1_TOKEN='<chuỗi cookie đầy đủ>'
  A2MAC1_DELAY=0.25
  ```

## 1. Lấy danh sách xe (621 xe)
- Nguồn: quick-search + filters products v2 (`data/harvest/quicksearch_all.json`, `filters_products_v2.json`).
- Kết quả: `data/products_all.json` — mỗi xe có `productId`, `resourceName`, `pictureFile` (ảnh đại diện + token file riêng).

## 2. Crawl 247 thông số kỹ thuật × 621 xe
- Endpoint: `POST https://ibp.a2mac1.com/api/products/compare/data/by-products?hideMappedProperties=true`
- Body: **mảng productId** (tối đa 25 xe/lượt — giới hạn `compare.max-products=25` của nền tảng).
- Code: `scripts/crawl_specs.py` — chia 621 xe thành 25 batch, lưu `data/spec_batches/batch_NNNN.json`, state resume ở `data/spec_state.json`.
- Response: `{propertyGroups: [...], items: [...], values: {productId: {propertyId: {scenario: [{formatedValue, originalValue, unitLabel}]}}}}`
- 247 thuộc tính thuộc 17 nhóm (Brand=`00000000TLEEDV01`, Model=`00000000TLEGDV01`, Model Year=`00000000TLDRDV01`).

## 3. Tải ảnh xe (621/621 — HOÀN THÀNH)
- 518 ảnh công khai: URL blob `https://legacystorageeu.blob.core.windows.net/public/...` (lấy từ `pictureFile.details.publicUrls.small`) — `scripts/download_images.py`.
- 103 ảnh riêng tư (đa số mẫu 2025-2026, fullHD tới 4496×3000):
  ```
  GET /files/downloads/files?token=<pictureFile.details.token>&api-version=1.1
  ```
  kèm JWT — code: `scripts/crawl_final.py`. Kết quả: `download/A2MAC1_anh_xe/` + `download/A2MAC1_anh_xe_fullHD/`.

## 4. Quét danh mục file 3D/CAD từng linh kiện (923.551 file / 578 xe — HOÀN THÀNH)
- Gói dữ liệu theo xe:
  ```
  GET /api/visual/files/packages?productIds=<id1>&productIds=<id2>...   (batch 25 xe/lượt)
  ```
  → trả về packageId, **token gói**, packageBaseUrl, hierarchyIds (`00000003LSK4EU01` = 3D AutoReverse, `00000005ZT4GEU01` = Vehicle Occupant Packaging).
- File 3D từng linh kiện:
  ```
  POST /api/visual/files/get-files?api-version=2.0
  body: {"productIds": ["<pid>"], "hierarchyId": "00000003LSK4EU01", "isBookmark": false}
  ```
  → mỗi file: part number, vật liệu (Metal > Steel, Plastics > PP...), màu, HD/SD, `isDownloadable`, **token riêng**.
- Code: `scripts/crawl_all.py` / `crawl_all2.py` (bản throttle chống 403). Kết quả: `data/visual_files_summary.json` (theo xe), `data/packages_all.json`, mẫu full trong `data/visual_files_sample.json`.

## 5. Trạng thái Teardown / 3D Data theo xe (420/621)
```
POST /api/hierarchies/A000005AE6M1EU01/parts
body: {"filters": ["product-id eq <productId>"], "sorter": null, "page": {"number": 1, "size": 50}}
params: allowDynamicColumns=true, hideMappedProperties=true
```
→ 12 thuộc tính/bản ghi: Package, Status, Teardown Data - Status/Delivery Date, 3D Data - Status, Preliminary/Final Data Delivery. Kết quả: `data/teardown_state.json`.

## 6. Tải file 3D/CAD thật
- Tải 1 file: `GET /files/downloads/files?token=<fileToken>&api-version=1.1` (+`filename=`, `applyWatermark=false`).
- Tải nhiều file (archive): `POST /downloads` với fileTokens — nền tảng giới hạn **250 lượt tải visual** (`visual.max-downloads`).
- Quyền tài khoản: `data.export-download` (đã có).

## 7. Ghép Excel cuối (scripts/build_excel_final.py)
- 108 sheets: Danh mục hãng (hyperlink) + 104 sheet hãng (ma trận 247 thông số × N xe, **ảnh nhúng phía trên cột mỗi xe**) + `3D & Teardown` (621 dòng: số file 3D, vật liệu top 3, trạng thái teardown) + `CAD & 3D` (tổng hợp endpoint) + Review (COUNTA đối chiếu — 105/105 PASS).
- Thư viện style: `skills/xlsx/templates/base.py`; QA: recalc → audit → validate.

## ⚠️ Kinh nghiệm chống 403
- 403 thường là **warm-up tạm thời**: chờ 4-5s rồi retry lại được.
- Quét ~1.800 request liên tục trong 6 phút (8 threads) sẽ bị chặn 403 kéo dài → dùng 5 threads + delay 0.25s + backoff 4s khi lỗi.
- JWT hết hạn giữa chừng → crawler phải **lưu state + resume** (đã làm trong mọi script).

## Tổ chức file
```
scripts/          # toàn bộ code crawl + build excel
data/             # JSON thô: products, spec_batches (25 file), visual_files_summary, teardown_state, packages, harvest
download/         # sản phẩm: A2MAC1_benchmark_full_621_xe.xlsx + thư mục ảnh
```
