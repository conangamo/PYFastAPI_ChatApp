# ⚡ Alembic Quick Start

## 🚀 **Setup (One Time)**

### **1. Mark Current Database State**

```bash
# Tell Alembic: "This is the current state, don't try to create existing tables"
docker-compose exec backend alembic stamp head
```

---

## 💼 **Daily Workflow**

### **When You Change Models:**

```bash
# 1. Edit model (e.g., app/models/user.py)
# Add new field, change column, etc.

# 2. Generate migration (auto-detect changes)
docker-compose exec backend alembic revision --autogenerate -m "Add phone_number to users"

# 3. Apply migration
docker-compose exec backend alembic upgrade head
```

**Done!** ✅

---

## 📋 **Common Commands**

```bash
# Check current version
docker-compose exec backend alembic current

# Show history
docker-compose exec backend alembic history

# Upgrade to latest
docker-compose exec backend alembic upgrade head

# Rollback 1 version
docker-compose exec backend alembic downgrade -1
```

---

## 🎯 **Example: Add New Field**

### **Step 1: Edit Model**

```python
# app/models/user.py
class User(Base):
    # ... existing ...
    bio = Column(Text, nullable=True)  # ← NEW
```

### **Step 2: Generate Migration**

```bash
docker-compose exec backend alembic revision --autogenerate -m "Add bio to users"
```

**Output:**
```
Generating alembic/versions/abc123_add_bio_to_users.py ... done
```

### **Step 3: Apply**

```bash
docker-compose exec backend alembic upgrade head
```

**Output:**
```
INFO  [alembic.runtime.migration] Running upgrade -> abc123, Add bio to users
```

**Done!** ✅ Table updated!

---

## 🔄 **Team Workflow**

### **Pull Changes from Teammate:**

```bash
# 1. Pull code
git pull

# 2. Apply new migrations
docker-compose exec backend alembic upgrade head
```

That's it! Database automatically updated! 🎉

---

## 🆚 **Before vs After**

### **Before (Manual SQL):**
```bash
❌ "Ae ơi, nhớ chạy file SQL nha!"
❌ "Ơ sao database tôi lỗi?"
❌ Copy-paste SQL vào terminal...
```

### **After (Alembic):**
```bash
✅ git pull
✅ alembic upgrade head
✅ Done!
```

---

## 📚 **Full Guide**

See: `ALEMBIC_PROFESSIONAL_GUIDE.md`

---

**Professional! 🏆**

