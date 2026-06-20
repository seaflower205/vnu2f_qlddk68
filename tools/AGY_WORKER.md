# Antigravity worker bridge

`run_agy_worker.py` gọi binary `agy` chính thức mà không đọc hoặc thay đổi OAuth.
Mọi lời gọi dùng `--sandbox`; output JSON có trạng thái riêng cho quota (`exit 75`).

## Thiết lập tài khoản

1. Người dùng chạy `agy` và hoàn tất OAuth trong trình duyệt Google.
2. Nếu có nhiều tài khoản, người dùng chọn tài khoản hoạt động trong công cụ quản lý trước khi giao việc.
3. Không lưu refresh token, authorization code hay cookie trong repo.

Wrapper không tự đổi tài khoản khi hết quota. Khi nhận `quota_exhausted`, agent phải dừng,
fallback sang provider được phép hoặc yêu cầu người dùng kích hoạt profile khác.

## Thêm và kiểm tra nhiều tài khoản

`agy` hiện không có `--profile` và Cockpit Tools không quản lý Antigravity CLI.
Để tách OAuth đúng cách, đăng nhập `agy` trong Windows user/VM riêng. Trong phiên
đang hoạt động, đăng ký metadata của tài khoản bằng:

```powershell
python tools/run_agy_worker.py --register-current
python tools/run_agy_worker.py --list-accounts
```

Lặp lại trong từng môi trường đăng nhập. Registry chỉ lưu ID băm, email che mờ, `last_seen` và
trạng thái quota tại `scratch/agy_worker/accounts.json`; không lưu OAuth/token.
Khi hết quota, tài khoản hiện hành được đánh dấu để bạn chọn profile tiếp theo.
Agent phải giữ nguyên task/prompt đang chờ và yêu cầu người dùng đăng nhập tài khoản
khác; không được bỏ qua lỗi quota hoặc báo hoàn thành.

## Kiểm tra không tiêu quota

```powershell
python tools/run_agy_worker.py --dry-run --prompt "probe" --cwd .
```

## Giao việc read-only

```powershell
python tools/run_agy_worker.py --prompt-file scratch/agy_prompt.txt --cwd .
```

Có thể đặt `AGY_BIN` nếu binary không nằm trong PATH hoặc vị trí mặc định Windows.
