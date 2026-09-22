# GeniusKala Host Speed Monitor — CSV

فایل `urls.txt` شامل URLهای تست است. پارامتر `gk_timing=1` به‌صورت خودکار هنگام درخواست اضافه می‌شود و لازم نیست داخل فایل نوشته شود.

## ورودی‌های Workflow
- `total_hours`: مدت کل تست؛ مثال 24
- `file_hours`: طول هر فایل CSV؛ مثال 4
- `interval_minutes`: فاصله هر تست؛ مثال 10
- `url_order`:
  - `sequential`: URLها به ترتیب فایل و به‌صورت چرخشی
  - `random`: در هر نوبت یک URL تصادفی

## مثال 24 / 4 / 10
تست 24 ساعت ادامه دارد، هر 10 دقیقه یک URL درخواست می‌شود و هر 4 ساعت یک CSV مستقل ساخته می‌شود؛ در نتیجه 6 فایل CSV خواهیم داشت.

User-Agent درخواست‌ها:
`GeniusKala-Host-Monitor/1.0`

CSV شامل زمان تهران و UTC، URL اصلی، URL تست‌شده، HTTP status، DNS، Connect، TLS، TTFB، Total Time، حجم پاسخ، IP، وضعیت LiteSpeed Cache و خطا است.
