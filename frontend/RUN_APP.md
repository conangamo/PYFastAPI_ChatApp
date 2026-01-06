# 🚀 Hướng Dẫn Chạy Frontend App

## ⚠️ QUAN TRỌNG: Python 3.12 Required

**Video call cần Python 3.12** để cài đặt `aiortc` và `av` (có pre-built wheels, không cần Visual C++ Build Tools).

---

## 📋 Setup Python 3.12 (Chỉ cần làm 1 lần)

### Bước 1: Cài Python 3.12.7

1. **Tải Python 3.12.7:**
   - Link: https://www.python.org/downloads/release/python-3127/
   - Chọn: **Windows installer (64-bit)**
   - ⚠️ **Quan trọng:** Tick "Add python.exe to PATH" khi cài đặt

2. **Verify cài đặt:**
   ```powershell
   py -3.12 --version
   ```
   Nếu thấy `Python 3.12.7` là đã cài đúng.

### Bước 2: Chạy Setup Script

```powershell
cd frontend
.\setup_python312.ps1
```

Script sẽ tự động:
- ✅ Tạo virtual environment mới `venv312` với Python 3.12
- ✅ Upgrade pip
- ✅ Cài đặt tất cả packages từ `requirements.txt`
- ✅ Cài `av 12.0.0` (pre-built wheel)
- ✅ Cài `aiortc 1.6.0` và dependencies
- ✅ Verify OpenCV, aiortc, Flet

**Lưu ý:** Script sẽ tự động xử lý dependency conflicts (av 12.0.0 với aiortc 1.6.0 vẫn hoạt động tốt).

---

## 🎮 Chạy App

### Cách 1: Dùng Script (Khuyến nghị)

```powershell
cd frontend
.\run_python312.ps1
```

Script sẽ tự động:
- ✅ Activate Python 3.12 virtual environment (`venv312`)
- ✅ Kiểm tra backend có chạy không
- ✅ Khởi động desktop app

### Cách 2: Chạy Thủ Công

```powershell
cd frontend

# Activate venv312
.\venv312\Scripts\Activate.ps1

# Chạy app
python -m app.main
```

---

## 🔧 Trước Khi Chạy

### Đảm bảo Backend đang chạy:

```powershell
# Kiểm tra
docker-compose ps

# Nếu chưa chạy, khởi động:
docker-compose up -d postgres backend

# Đợi 10 giây, sau đó kiểm tra:
curl http://localhost:8000/health
```

---

## 🧹 Nếu Cần Logout/Xóa Session

```powershell
cd frontend
.\venv312\Scripts\Activate.ps1
python clear_storage.py
```

---

## 🐛 Troubleshooting

### Lỗi: `No module named 'flet'` hoặc `No module named 'cv2'`
**Nguyên nhân:** Chưa activate venv hoặc đang dùng venv cũ (Python 3.13)  
**Fix:** 
```powershell
cd frontend
.\venv312\Scripts\Activate.ps1  # Đảm bảo dùng venv312
python -m pip list | Select-String -Pattern "flet|cv2|aiortc"
```

### Lỗi: `Python 3.12 not found!`
**Nguyên nhân:** Python 3.12 chưa được cài hoặc chưa thêm vào PATH  
**Fix:**
1. Cài lại Python 3.12.7 và đảm bảo tick "Add python.exe to PATH"
2. Đóng và mở lại PowerShell
3. Verify: `py -3.12 --version`

### Lỗi: `WebRTC handler not available`
**Nguyên nhân:** `aiortc` hoặc `av` chưa được cài đặt  
**Fix:**
```powershell
cd frontend
.\venv312\Scripts\Activate.ps1
python -m pip install --only-binary :all: av==12.0.0
python -m pip install aiortc==1.6.0 --no-deps
python -m pip install aioice cryptography google-crc32c pyee pylibsrtp pyopenssl dnspython ifaddr
```

### Lỗi: `OpenCV not available`
**Nguyên nhân:** `opencv-python` chưa được cài đặt  
**Fix:**
```powershell
cd frontend
.\venv312\Scripts\Activate.ps1
python -m pip install opencv-python==4.12.0.88
```

### Giao diện trắng/không tương tác được
**Fix:**
1. Xóa storage: `python clear_storage.py`
2. Chạy lại app: `.\run_python312.ps1`

### Backend không chạy
**Fix:**
```powershell
docker-compose restart backend
docker-compose logs backend
```

### Camera không hoạt động / Frame trắng
**Nguyên nhân:** Camera backend MSMF trên Windows có thể trả frame trắng  
**Fix:** Code đã được sửa để dùng DirectShow backend (`cv2.CAP_DSHOW`). Nếu vẫn lỗi:
1. Kiểm tra camera permissions
2. Thử camera index khác (0, 1, 2)
3. Xem console log để debug

---

## 📝 Lưu Ý

### Python 3.13 vs Python 3.12

- **Python 3.13:** Không có pre-built wheels cho `av 11.0.0`, cần Visual C++ Build Tools để build từ source
- **Python 3.12:** Có pre-built wheels cho `av 12.0.0`, cài đặt nhanh và dễ dàng

### Virtual Environment

- **venv312:** Python 3.12 environment (dùng cho video call)
- **venv:** Python 3.13 environment (cũ, không hỗ trợ video call)

Luôn dùng `venv312` khi cần video call.

---

## ✅ Verify Setup

Sau khi setup, verify các packages quan trọng:

```powershell
cd frontend
.\venv312\Scripts\Activate.ps1
python -c "import cv2; import aiortc; import av; import flet; print('All packages OK!')"
python -c "from app.pages.video_call_page import CV2_AVAILABLE, WEBRTC_AVAILABLE; print(f'CV2: {CV2_AVAILABLE}, WebRTC: {WEBRTC_AVAILABLE}')"
```

Nếu cả 2 đều `True`, setup đã thành công!

---

**Chúc bạn coding vui vẻ!** 🎉
