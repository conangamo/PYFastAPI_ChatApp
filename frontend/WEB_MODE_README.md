# 🌐 Web Mode - Testing 2 Users

## 🚀 Cách Dùng

### **Chạy Web Server**
```bash
cd frontend
python run_web.py
```

### **Mở 2 Browser Tabs**

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

### **Test! 🧪**
- Alice gửi tin → Bob nhận ngay lập tức
- Bob xem tin → Alice thấy ✓✓ (blue)
- Alice gõ → Bob thấy "📝 Alice is typing..."

---

## 📋 So Sánh

| Mode | Command | Dùng Khi Nào |
|------|---------|--------------|
| **Desktop** | `python -m app.main` | Dùng bình thường |
| **Web** | `python run_web.py` | Test 2 users |

---

## ✅ **Tất cả chức năng đều work trong web mode!**

- ✅ Login/Register
- ✅ Chat realtime
- ✅ Read receipts (✓✓)
- ✅ Typing indicators (📝)
- ✅ Voice messages (🎤)
- ✅ File upload (📎)

**Done!** 🎉

