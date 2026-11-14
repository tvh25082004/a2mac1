# A2MAC1 IBP Crawler & Benchmark Data

Crawl toàn bộ dữ liệu **A2MAC1 IBP** (ibp.a2mac1.com) phục vụ benchmark dòng xe: 621 xe × 247 thông số kỹ thuật, 621/621 ảnh xe, danh mục **923.551 file 3D/CAD linh kiện** (578 xe), trạng thái teardown 420 xe — tổng hợp thành 1 file Excel 108 sheets.

## Tải file CAD STL thật (GitHub Release — công khai, miễn phí)

**https://github.com/tvh25082004/a2mac1/releases/tag/cad-v1**

| Bundle | Dung lượng | Nội dung |
|---|---|---|
| `CAD-bundle-01.zip` | 1.86GB | 621 STL |
| `CAD-bundle-02.zip` | 1.89GB | 663 STL |
| `CAD-bundle-03.zip` | 1.37GB | 455 STL |

- Tải cả 3 bundle → **giải nén hết vào cùng 1 thư mục** → được **1.739 file STL** (`VinFast VF6 Plus 2024/` đầy đủ 1.670 linh kiện 100% + `VinFast VF8 Plus 2023/` 69 file đầu)
- Mỗi `.stl` là 1 linh kiện riêng (nguồn A2MAC1 IBP, bộ 3D AutoReverse, hierarchy `00000003LSK4EU01`)
- Danh mục đầy đủ (tên linh kiện, partId, kích thước) xem tại `data/cad_skip_list.json` trong repo
- VF8 còn lại 1.934 file + các xe Trung Quốc (BYD/Aion/AITO/Chery/Geely) sẽ được bổ sung vào Release sau khi A2MAC1 gỡ lượt chặn 403

## Sản phẩm cuối (download/)
| File | Mô tả |
|---|---|
| `A2MAC1_benchmark_full_621_xe.xlsx` (8.3 MB) | File Excel cuối: Danh mục hãng + 104 sheet hãng (247 thông số × N xe, **ảnh nhúng phía trên cột mỗi xe**) + sheet `3D & Teardown` (621 dòng: số file 3D, vật liệu top 3, trạng thái teardown/3D) + sheet `CAD & 3D` (tổng hợp endpoint) + Review (105/105 PASS) |
| `A2MAC1_anh_xe/` | 518 ảnh xe 300×200 (ảnh công khai) |
| `A2MAC1_anh_xe_fullHD/` | 103 ảnh fullHD tới 4496×3000 (xe 2025-2026, tải bằng file-token) |
| `A2MAC1_raw_products_621xe.json` | Danh sách gốc 621 xe |

## Cách crawler hoạt động
Xem chi tiết trong **[CRAWLER_GUIDE.md](CRAWLER_GUIDE.md)** — đầy đủ endpoint, body, cơ chế token, kinh nghiệm chống 403:
1. `POST /api/products/compare/data/by-products` — 247 thông số (25 xe/lượt)
2. `GET /files/downloads/files?token=...&api-version=1.1` — tải ảnh riêng tư
3. `POST /api/visual/files/get-files?api-version=2.0` — file 3D/CAD từng linh kiện
4. `POST /api/hierarchies/A000005AE6M1EU01/parts` — trạng thái teardown/3D theo xe

## Cấu trúc
```
scripts/     # toàn bộ code crawl (Python) + build Excel
data/        # JSON thô: products_all, spec_batches/ (25 batch × 621 xe), visual_files_summary,
             # teardown_state, packages_all, harvest/, JS bundle của frontend (dò endpoint)
download/    # sản phẩm cuối
```

## Chạy lại
```bash
pip install requests python-dotenv openpyxl pillow
cp .env.example .env   # dán access_token của bạn vào
python3 scripts/crawl_specs.py      # 247 thông số × 621 xe (resume được)
python3 scripts/crawl_all2.py all   # packages + file 3D/CAD + teardown (throttle chống 403)
python3 scripts/build_excel_final.py
```

## Cấu hình token
Copy `.env.example` → `.env`, dán chuỗi cookie đầy đủ (F12 → Application → Cookies → `access_token`) — token hạn ~24 phút, crawler tự resume khi cấp token mới.

## Ghi chú
- `.env` chứa JWT credential nên **không commit** — chỉ có `.env.example`.
- Dữ liệu thuộc A2MAC1 (license thương mại) — dùng nội bộ benchmark.
