# 🚀 Chạy Frontend App

## Cách đơn giản nhất (Khuyến nghị)

```powershell
cd frontend
.\run.ps1
```

Script sẽ tự động:
- ✅ Activate virtual environment
- ✅ Kiểm tra backend có chạy không
- ✅ Khởi động desktop app

---

## Hoặc chạy thủ công

# Tổng quan chạy
cd frontend; .\venv\Scripts\Activate.ps1; python clear_storage.py

```powershell
cd frontend

# 1. Activate venv
.\venv\Scripts\Activate.ps1

# 2. Chạy app
python -m app.main
```

---

## Trước khi chạy

**Đảm bảo backend đang chạy:**

```powershell
# Kiểm tra
docker-compose ps

# Nếu chưa chạy, khởi động:
docker-compose up -d postgres backend

# Đợi 10 giây, sau đó kiểm tra:
curl http://localhost:8000/health
```

---

## Nếu cần logout/xóa session

```powershell
cd frontend
.\venv\Scripts\Activate.ps1
python clear_storage.py
```

---

## Troubleshooting

### Lỗi: `No module named 'flet'`
**Nguyên nhân:** Chưa activate venv  
**Fix:** Chạy `.\venv\Scripts\Activate.ps1` trước

### Giao diện trắng/không tương tác được
**Fix:**
1. Xóa storage: `python clear_storage.py`
2. Chạy lại app: `.\run.ps1`

### Backend không chạy
**Fix:**
```powershell
docker-compose restart backend
docker-compose logs backend
```

---

**Chúc bạn coding vui vẻ!** 🎉

