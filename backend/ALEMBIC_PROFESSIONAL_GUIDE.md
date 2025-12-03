# 🏆 Professional Database Migrations with Alembic

## ✅ **Setup Complete!**

Alembic đã được config theo chuẩn professional:
- ✅ Auto-detect model changes
- ✅ Version control migrations
- ✅ Rollback support
- ✅ Team-friendly
- ✅ Production-ready

---

## 🚀 **Professional Workflow**

### **1. Make Changes to Models**

Ví dụ: Thêm field mới vào User model:

```python
# app/models/user.py
class User(Base):
    # ... existing fields ...
    phone_number = Column(String(20), nullable=True)  # ← NEW FIELD
```

### **2. Auto-Generate Migration**

```bash
# Trong backend container:
docker-compose exec backend alembic revision --autogenerate -m "Add phone_number to users"
```

**Output:**
```
Generating /app/alembic/versions/a1b2c3d4e5f6_add_phone_number_to_users.py ... done
```

**Alembic tự động:**
- ✅ Detect thay đổi (new column)
- ✅ Generate migration file
- ✅ Add upgrade() and downgrade() functions

### **3. Review Migration**

```python
# alembic/versions/a1b2c3d4e5f6_add_phone_number_to_users.py

def upgrade() -> None:
    # Auto-generated
    op.add_column('users', sa.Column('phone_number', sa.String(20), nullable=True))

def downgrade() -> None:
    # Auto-generated
    op.drop_column('users', 'phone_number')
```

**Review checklist:**
- ✅ SQL correct?
- ✅ Downgrade works?
- ✅ Data migration needed?

### **4. Apply Migration**

```bash
# Apply migration
docker-compose exec backend alembic upgrade head

# Output:
INFO  [alembic.runtime.migration] Running upgrade  -> a1b2c3d4e5f6, Add phone_number to users
```

**Done!** ✅ Database updated!

### **5. Rollback (If Needed)**

```bash
# Rollback 1 version
docker-compose exec backend alembic downgrade -1

# Rollback to specific version
docker-compose exec backend alembic downgrade a1b2c3d4e5f6
```

---

## 📋 **Common Commands**

### **Check Current Version**
```bash
docker-compose exec backend alembic current
```

### **Show Migration History**
```bash
docker-compose exec backend alembic history
```

### **Upgrade to Latest**
```bash
docker-compose exec backend alembic upgrade head
```

### **Generate Migration (Auto-detect)**
```bash
docker-compose exec backend alembic revision --autogenerate -m "Description"
```

### **Generate Empty Migration (Manual)**
```bash
docker-compose exec backend alembic revision -m "Custom migration"
```

---

## 🎯 **Real Example: Migrate Existing Database**

### **Current Situation:**

Database có tables:
- ✅ users
- ✅ conversations
- ✅ messages
- ✅ friendships
- ✅ message_reactions

**Problem**: Tables được tạo manual, không có migration history!

### **Solution: Create Baseline Migration**

**Step 1: Create initial migration**
```bash
docker-compose exec backend alembic revision --autogenerate -m "Initial schema"
```

**Step 2: Mark as applied (without running)**
```bash
# Stamp database with this version (don't run upgrade)
docker-compose exec backend alembic stamp head
```

**Result:**
- ✅ Alembic knows current state
- ✅ Future migrations work normally
- ✅ No duplicate table errors

---

## 🔥 **Team Workflow Example**

### **Developer A: Add Feature**

```bash
# 1. Pull latest code
git pull

# 2. Apply any new migrations
docker-compose exec backend alembic upgrade head

# 3. Make changes to models
# ... edit app/models/user.py ...

# 4. Generate migration
docker-compose exec backend alembic revision --autogenerate -m "Add avatar_url"

# 5. Test migration
docker-compose exec backend alembic upgrade head
docker-compose exec backend alembic downgrade -1
docker-compose exec backend alembic upgrade head

# 6. Commit migration file
git add alembic/versions/xxx_add_avatar_url.py
git commit -m "Add avatar_url to users"
git push
```

### **Developer B: Pull Changes**

```bash
# 1. Pull code (includes migration file)
git pull

# 2. Apply new migration
docker-compose exec backend alembic upgrade head
```

**Magic!** ✨ Database auto-updated!

---

## 💡 **Best Practices**

### **1. Always Review Auto-Generated Migrations**

```python
# BAD: Auto-generated might miss indexes
def upgrade():
    op.add_column('users', sa.Column('email', sa.String()))

# GOOD: Add indexes manually
def upgrade():
    op.add_column('users', sa.Column('email', sa.String()))
    op.create_index('idx_users_email', 'users', ['email'])
```

### **2. Test Rollback**

```bash
# Always test downgrade works
alembic upgrade head
alembic downgrade -1  # Should work!
alembic upgrade head
```

### **3. Descriptive Messages**

```bash
# BAD
alembic revision -m "update"

# GOOD
alembic revision -m "Add email verification to users"
```

### **4. One Logical Change Per Migration**

```bash
# BAD: Multiple unrelated changes
alembic revision -m "Add phone, remove age, create posts table"

# GOOD: Separate migrations
alembic revision -m "Add phone_number to users"
alembic revision -m "Remove age column from users"
alembic revision -m "Create posts table"
```

### **5. Data Migrations**

```python
# When renaming column with data
def upgrade():
    # 1. Add new column
    op.add_column('users', sa.Column('display_name', sa.String()))
    
    # 2. Copy data
    op.execute("UPDATE users SET display_name = username")
    
    # 3. Drop old column
    op.drop_column('users', 'username')
```

---

## 🆚 **Comparison**

| Feature | Manual SQL ❌ | Alembic ✅ |
|---------|--------------|-----------|
| **Version Control** | None | Full history |
| **Auto-detect Changes** | Manual | Automatic |
| **Rollback** | Write SQL manually | One command |
| **Team Sync** | Chaos | Smooth |
| **Production Deploy** | Risky | Safe |
| **Track Applied** | Excel sheet? 😅 | Built-in |

---

## 📚 **Advanced Topics**

### **Branching & Merging Migrations**

```bash
# If 2 developers create migrations simultaneously
alembic merge -m "Merge migrations" head1 head2
```

### **Custom Migration Templates**

Edit `alembic/script.py.mako` to add:
- Author name
- Jira ticket
- Review checklist

### **Multiple Databases**

```bash
# Different databases (e.g., main + analytics)
alembic -c alembic_main.ini upgrade head
alembic -c alembic_analytics.ini upgrade head
```

---

## 🎓 **Next Steps**

### **Immediate:**
1. ✅ Create baseline migration (mark current state)
2. ✅ Test workflow with dummy change
3. ✅ Commit alembic setup to git

### **Future:**
- Move from `init_db()` to alembic only
- Setup CI/CD to auto-run migrations
- Add migration tests

---

## 🚨 **Important Notes**

### **For Existing Database:**

**DON'T run `alembic upgrade head` immediately!**

First:
```bash
# Mark current state without running
alembic stamp head
```

Then test with new migrations.

### **Production Deployment:**

```bash
# 1. Backup database
pg_dump chatapp > backup.sql

# 2. Test migration on staging
alembic upgrade head

# 3. If OK, run on production
alembic upgrade head

# 4. If fail, rollback
alembic downgrade -1
```

---

## 📝 **Cheat Sheet**

```bash
# Setup (once)
alembic init alembic

# Daily workflow
alembic revision --autogenerate -m "message"
alembic upgrade head

# Check status
alembic current
alembic history

# Rollback
alembic downgrade -1

# Mark without running
alembic stamp head
```

---

## 🎉 **Conclusion**

**Before (Manual):**
```
😅 "Ai chạy SQL file chưa?"
😰 "Database prod khác staging!"
😱 "Rollback thế nào?"
```

**After (Alembic):**
```
✅ git pull → alembic upgrade head → Done!
✅ All databases same version
✅ Rollback: alembic downgrade -1
```

**Welcome to Professional Development!** 🏆

