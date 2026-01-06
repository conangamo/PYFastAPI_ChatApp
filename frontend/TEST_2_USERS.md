# 🧪 Hướng Dẫn Test 2 Users Trên 1 Máy

## ⚠️ Vấn Đề Camera Conflict

Khi test 2 cửa sổ trên cùng 1 máy, cả 2 instance đều cố mở camera. Có 2 cách xử lý:

---

## 🌐 Cách 1: Web Mode (Khuyến nghị)

**Ưu điểm:** 
- ✅ Không có camera conflict (browser tự xử lý)
- ✅ Dễ test (chỉ cần 2 browser tabs)
- ✅ Tất cả chức năng đều hoạt động

### Chạy Web Mode:

```powershell
cd frontend
.\venv312\Scripts\Activate.ps1
python run_web.py
```

### Mở 2 Browser Tabs:

**Tab 1 (Normal):**
```
http://localhost:8550
Login: alice / alice123  (User A)
```

**Tab 2 (Incognito - Ctrl+Shift+N):**
```
http://localhost:8550
Login: bob / bob123  (User B)
```

### Test Video Call:
1. Alice gọi video call cho Bob
2. Bob nhận call
3. Cả 2 đều thấy camera của nhau

---

## 🖥️ Cách 2: Desktop Mode (2 Cửa Sổ)

**Lưu ý:** 
- ⚠️ Cả 2 instance đều cố mở camera index 0
- ✅ Code đã được sửa để tự động thử camera index khác nếu conflict
- ✅ Nếu máy có nhiều camera, mỗi instance sẽ dùng camera khác nhau

### Chạy 2 Desktop Instances:

**Terminal 1:**
```powershell
cd frontend
.\venv312\Scripts\Activate.ps1
python -m app.main
```
→ Login User A (alice/alice123)

**Terminal 2:**
```powershell
cd frontend
.\venv312\Scripts\Activate.ps1
python -m app.main
```
→ Login User B (bob/bob123)

### Cách Code Xử Lý Camera Conflict:

1. **VideoCallPage** (local preview):
   - Thử camera index 0, 1, 2
   - Dùng camera đầu tiên mở được

2. **OpenCVVideoTrack** (WebRTC stream):
   - Thử camera index 0, 1, 2
   - Dùng camera đầu tiên có frame hợp lệ (không phải trắng/đen)

### Kết Quả:

- **Nếu máy có 1 camera:**
  - Instance 1: Dùng camera 0
  - Instance 2: Có thể dùng camera 0 (Windows thường cho phép) hoặc báo lỗi
  
- **Nếu máy có nhiều camera:**
  - Instance 1: Dùng camera 0
  - Instance 2: Tự động dùng camera 1 hoặc 2

---

## 🔍 Debug Camera Conflict

Nếu gặp vấn đề, xem log:

### Log từ VideoCallPage:
```
Trying camera index 0 with CAP_DSHOW...
✓ Camera 0 opened successfully!
   Frame shape: (720, 1280, 3)
   Frame stats: min=10, max=246, mean=131.59
```

### Log từ OpenCVVideoTrack:
```
OpenCVVideoTrack started: camera=0, 640x480@30fps, frame_shape=(480, 640, 3)
```

Nếu thấy:
- `Failed to open any camera` → Tất cả camera đã bị chiếm
- `Frame appears to be uniform (min=max=0)` → Frame trắng/đen, camera conflict

---

## 💡 Tips

1. **Web Mode là cách tốt nhất** để test 2 users trên 1 máy
2. **Desktop Mode:** Chỉ dùng nếu cần test desktop-specific features
3. **Nếu camera conflict:** Đóng 1 instance, test lại
4. **Kiểm tra camera:** Mở Camera app trên Windows để xem camera nào đang được dùng

---

## ✅ Verify Setup

Sau khi setup, verify:

```powershell
# Check camera devices
python -c "import cv2; [print(f'Camera {i}: {cv2.VideoCapture(i).isOpened()}') for i in range(3)]"
```

Nếu thấy `True` cho nhiều camera, máy có nhiều camera và code sẽ tự động phân bổ.

---

**Chúc bạn test vui vẻ!** 🎉

