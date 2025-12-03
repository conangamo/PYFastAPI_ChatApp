# Database Migrations

## Overview

This directory contains SQL migration scripts for the database schema changes.

Since this project uses SQLAlchemy's `Base.metadata.create_all()` instead of Alembic, migrations must be applied manually.

---

## How to Apply Migrations

### **Option 1: Fresh Start (Development Only)** 🔴

**WARNING**: This will DELETE all existing data!

```bash
# Stop backend
docker-compose down

# Remove database volume
docker volume rm chat_v4_postgres_data

# Restart (will recreate with new schema)
docker-compose up -d
```

---

### **Option 2: Manual Migration (Keep Data)** ✅

**Recommended for production or if you want to keep existing data.**

#### **Step 1: Connect to PostgreSQL**

```bash
# Access PostgreSQL container
docker-compose exec postgres psql -U postgres -d chat_app
```

#### **Step 2: Run Migration Script**

From inside PostgreSQL shell:

```sql
\i /path/to/migrations/001_add_read_receipts.sql
```

Or from host machine:

```bash
# Copy migration to container
docker cp backend/migrations/001_add_read_receipts.sql chat_v4_postgres_1:/tmp/

# Execute migration
docker-compose exec postgres psql -U postgres -d chat_app -f /tmp/001_add_read_receipts.sql
```

#### **Step 3: Verify Migration**

```sql
-- Check if columns exist
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'messages' 
AND column_name IN ('delivered_at', 'read_at', 'read_by_user_id');
```

Expected output:
```
    column_name     |           data_type           | is_nullable 
--------------------+-------------------------------+-------------
 delivered_at       | timestamp with time zone      | YES
 read_at            | timestamp with time zone      | YES
 read_by_user_id    | uuid                          | YES
```

---

## Available Migrations

| Migration | Description | Date |
|-----------|-------------|------|
| `001_add_read_receipts.sql` | Add read receipts columns to messages table | 2025-11-20 |

---

## Rollback Migrations

### **Rollback: 001_add_read_receipts**

```sql
-- Remove indexes
DROP INDEX IF EXISTS idx_messages_delivered_at;
DROP INDEX IF EXISTS idx_messages_read_at;
DROP INDEX IF EXISTS idx_messages_read_by_user_id;

-- Remove foreign key
ALTER TABLE messages
DROP CONSTRAINT IF EXISTS fk_messages_read_by_user;

-- Remove columns
ALTER TABLE messages 
DROP COLUMN IF EXISTS delivered_at,
DROP COLUMN IF EXISTS read_at,
DROP COLUMN IF EXISTS read_by_user_id;
```

---

## Future: Setup Alembic

For better migration management, consider setting up Alembic:

```bash
# Install Alembic
pip install alembic

# Initialize Alembic
alembic init alembic

# Generate migration from models
alembic revision --autogenerate -m "Add read receipts"

# Apply migration
alembic upgrade head
```

This will provide:
- Version control for migrations
- Auto-generate migrations from model changes
- Easy rollback
- Migration history

