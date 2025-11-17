# RBAC User Management Guide

## 🔐 Overview
The GenAI Academy 2.0 system now includes a complete **Role-Based Access Control (RBAC)** system with user authentication, authorization, and granular permissions.

**Key Features:**
- ✅ User authentication (login/logout)
- ✅ Role-based access control (Admin, Manager, Viewer, Custom)
- ✅ Granular page-level permissions
- ✅ Admin panel for user management
- ✅ Password hashing with werkzeug
- ✅ Session management
- ✅ Audit logging for user changes

---

## 📋 Table of Contents
1. [Setup Instructions](#setup-instructions)
2. [Default Users & Roles](#default-users--roles)
3. [Login System](#login-system)
4. [User Management](#user-management)
5. [Permissions Reference](#permissions-reference)
6. [Security Features](#security-features)
7. [Troubleshooting](#troubleshooting)

---

## 🚀 Setup Instructions

### **Step 1: Create the System Users Table**

Run the RBAC schema SQL script:

```powershell
# Connect to PostgreSQL
psql -h 192.168.1.60 -U your_username -d academy2_db

# Run the schema
\i database/schema_users_rbac.sql
```

Or copy-paste the contents of `database/schema_users_rbac.sql` into your PostgreSQL client.

### **Step 2: Create Default Users**

Run the Python script to create default users with hashed passwords:

```powershell
python scripts\create_default_users.py
```

**Output:**
```
============================================================
Creating Default System Users
============================================================

No users found. Creating default users...

1. Creating Admin user...
   ✓ Admin created successfully!
     Username: admin
     Password: Admin@123
     Email: admin@academy.local

2. Creating Manager user...
   ✓ Manager created successfully!
     Username: manager
     Password: Manager@123
     Email: manager@academy.local

3. Creating Viewer user...
   ✓ Viewer created successfully!
     Username: viewer
     Password: Viewer@123
     Email: viewer@academy.local

============================================================
Default Users Created Successfully!
============================================================

You can now login with:
  Admin:   admin / Admin@123
  Manager: manager / Manager@123
  Viewer:  viewer / Viewer@123

⚠️  IMPORTANT: Change these default passwords after first login!
============================================================
```

### **Step 3: Restart Flask Server**

```powershell
# Stop the current server (Ctrl+C)
# Restart
python app\main.py
```

### **Step 4: Access the Login Page**

```
http://192.168.1.60:5000/login
```

---

## 👥 Default Users & Roles

### **1. Admin** (Full Access)
```
Username: admin
Password: Admin@123
Email: admin@academy.local
```

**Permissions:**
- ✅ View Dashboard
- ✅ View Profiles
- ✅ View Data
- ✅ Import Data
- ✅ Export Data
- ✅ Manage Users (Admin Panel)
- ✅ Verification Queue

**Can Access:**
- All pages
- User management (/admin/users)
- Create/edit/delete users
- Change user permissions

---

### **2. Manager** (Data Management)
```
Username: manager
Password: Manager@123
Email: manager@academy.local
```

**Permissions:**
- ✅ View Dashboard
- ✅ View Profiles
- ✅ View Data
- ✅ Import Data
- ✅ Export Data
- ❌ Manage Users
- ✅ Verification Queue

**Can Access:**
- Dashboard, Profiles, View Data
- Import CSV data
- Export data
- Cannot create/manage users

---

### **3. Viewer** (Read Only)
```
Username: viewer
Password: Viewer@123
Email: viewer@academy.local
```

**Permissions:**
- ✅ View Dashboard
- ✅ View Profiles
- ✅ View Data
- ❌ Import Data
- ❌ Export Data
- ❌ Manage Users
- ❌ Verification Queue

**Can Access:**
- Dashboard (view only)
- Profiles (view only)
- Data tables (view only)
- Cannot import, export, or manage users

---

## 🔑 Login System

### **Login Page**
**URL:** `http://192.168.1.60:5000/login`

**Features:**
- Username & password authentication
- "Remember me" checkbox (extends session)
- Flash messages for errors/success
- Redirect to next page after login
- Gradient design with Academy branding

### **How to Login**
1. Navigate to `/login`
2. Enter your username and password
3. (Optional) Check "Remember me"
4. Click "Login"

### **After Login**
- Redirected to homepage (`/`)
- Navigation shows only permitted pages
- Username displayed in navbar with dropdown
- Can logout via dropdown menu

### **Logout**
**URL:** `/logout`
- Clears session
- Redirects to login page
- Shows "Logged out successfully" message

---

## 👨‍💼 User Management

### **Admin Panel**
**URL:** `/admin/users` (Admin only)

**Features:**
- View all system users
- Create new users
- Edit existing users
- Delete users (with safeguards)
- Change permissions
- Activate/deactivate accounts

---

### **Creating a New User**

1. **Access Admin Panel**: Navigate to `/admin/users`
2. **Click "Create New User"** button
3. **Fill in the form:**
   - Username *
   - Email *
   - Full Name
   - Password *
   - Role (Admin/Manager/Viewer/Custom)
   - Permissions (auto-filled based on role)

4. **Click "Create User"**

**Form Fields:**

| Field | Required | Description |
|-------|----------|-------------|
| Username | ✅ | Unique username for login |
| Email | ✅ | User's email address |
| Full Name | ❌ | Display name |
| Password | ✅ | Initial password (min 8 chars) |
| Role | ✅ | Predefined role or custom |
| Permissions | ✅ | Auto-set by role or manual |

**Roles:**
- **Admin**: Full access to everything
- **Manager**: Can manage data but not users
- **Viewer**: Read-only access
- **Custom**: Manually select permissions

---

### **Editing a User**

1. **Find the user** in the Admin Panel
2. **Click "Edit"** button on their card
3. **Modify fields:**
   - Email
   - Full Name
   - Password (leave blank to keep current)
   - Role
   - Permissions
   - Status (Active/Inactive)

4. **Click "Update User"**

**Notes:**
- Username cannot be changed
- Password field is optional (only if changing)
- Changing role auto-updates permissions
- Setting status to "Inactive" disables the account

---

### **Deleting a User**

1. **Find the user** in the Admin Panel
2. **Click "Delete"** button
3. **Confirm deletion** in the popup

**Safeguards:**
- Cannot delete your own account
- Cannot delete the last admin user
- Soft delete (sets `is_active = FALSE`)
- Logged in master_log for audit

---

### **User Card Display**

Each user card shows:
- **Name**: Full name or username
- **Role Badge**: Color-coded role
- **Email**: User's email address
- **Permissions**: Visual list of enabled/disabled permissions
- **Created Date**: When account was created
- **Last Login**: Last login timestamp
- **Status**: Active/Inactive badge
- **Actions**: Edit and Delete buttons

---

## 🔐 Permissions Reference

### **Available Permissions**

| Permission | Description | Default Roles |
|------------|-------------|---------------|
| `view_dashboard` | Access dashboard and reports | All |
| `view_profiles` | View user profiles | All |
| `view_data` | View data tables | All |
| `import_data` | Import CSV/Excel data | Admin, Manager |
| `export_data` | Export data to CSV | Admin, Manager |
| `manage_users` | Create/edit/delete system users | Admin |
| `verification_queue` | Access verification queue | Admin, Manager |

---

### **Permission Checking**

#### **Frontend (Navigation)**
Navigation links are hidden if user lacks permission:

```html
{% if session.get('permissions', {}).get('import_data', False) %}
<li class="nav-item">
    <a class="nav-link" href="/import">Import</a>
</li>
{% endif %}
```

#### **Backend (Route Protection)**
Routes are protected with decorators:

```python
@app.route('/import')
@login_required  # Must be logged in
@permission_required('import_data')  # Must have specific permission
def import_page():
    return render_template('import.html')
```

#### **Admin Routes**
Admin-only routes use `@admin_required`:

```python
@app.route('/admin/users')
@login_required
@admin_required  # Must be admin role
def manage_users():
    return render_template('admin_users.html')
```

---

## 🛡️ Security Features

### **1. Password Hashing**
- Uses `werkzeug.security` (scrypt algorithm)
- Salted and hashed passwords
- Never stored in plaintext

```python
from werkzeug.security import generate_password_hash, check_password_hash

# Hash password
password_hash = generate_password_hash('MyPassword123')

# Verify password
is_valid = check_password_hash(password_hash, 'MyPassword123')
```

### **2. Session Management**
- Flask sessions with secret key
- Session cookie contains user_id and permissions
- Sessions expire after period of inactivity
- "Remember me" extends session duration

### **3. Permission Checks**
- Every protected route checks permissions
- Decorators: `@login_required`, `@permission_required()`, `@admin_required`
- Both frontend and backend validation

### **4. Audit Logging**
- All user actions logged in `master_log` table
- Tracks create, update, delete operations
- Includes username, timestamp, changed fields

### **5. Protection Against**
- ✅ Unauthorized access (login required)
- ✅ Privilege escalation (permission checks)
- ✅ CSRF attacks (Flask CSRF tokens)
- ✅ Session hijacking (secure cookies)
- ✅ Password leaks (hashed storage)
- ✅ Self-deletion (safeguards)
- ✅ Last admin deletion (safeguards)

---

## 🔧 Technical Implementation

### **Database Schema**

**Table:** `system_users`

| Column | Type | Description |
|--------|------|-------------|
| user_id | SERIAL | Primary key |
| username | VARCHAR(100) | Unique username |
| password_hash | VARCHAR(255) | Hashed password |
| email | VARCHAR(255) | Email address |
| full_name | VARCHAR(255) | Display name |
| role | VARCHAR(50) | User role |
| is_active | BOOLEAN | Account status |
| permissions | JSONB | Permission JSON |
| created_at | TIMESTAMP | Creation time |
| updated_at | TIMESTAMP | Last update |
| last_login | TIMESTAMP | Last login time |

**Indexes:**
- username (unique)
- email (unique)
- role
- is_active

**Triggers:**
- Audit logging (INSERT/UPDATE/DELETE)
- Auto-update `updated_at` timestamp

---

### **File Structure**

```
app/
├─ auth.py                          # Authentication & authorization
│  ├─ SystemUser model              # User ORM model
│  ├─ get_current_user()            # Get logged-in user
│  ├─ login_required                # Decorator
│  ├─ permission_required()         # Decorator
│  ├─ admin_required                # Decorator
│  ├─ authenticate_user()           # Login logic
│  ├─ create_user()                 # Create user
│  ├─ update_user()                 # Update user
│  └─ delete_user()                 # Delete user
│
├─ main.py                          # Flask routes
│  ├─ /login                        # Login page
│  ├─ /logout                       # Logout
│  ├─ /admin/users                  # User management
│  ├─ /api/users/*                  # User CRUD APIs
│  └─ Protected routes with @decorators
│
└─ templates/
   ├─ login.html                    # Login page
   ├─ admin_users.html              # User management
   └─ base.html                     # Navigation (permission-based)

database/
└─ schema_users_rbac.sql            # Database schema

scripts/
└─ create_default_users.py         # Create default users
```

---

## 🐛 Troubleshooting

### **Can't Login**
**Problem:** "Invalid username or password"
- Check username is correct (case-sensitive)
- Verify password
- Ensure user is active (`is_active = TRUE`)
- Check `last_login` in database

**Solution:**
```sql
-- Check if user exists
SELECT * FROM system_users WHERE username = 'admin';

-- Reset password
UPDATE system_users
SET password_hash = 'new_hash_here'
WHERE username = 'admin';

-- Or recreate users
DELETE FROM system_users;
-- Then run: python scripts/create_default_users.py
```

---

### **"Permission Denied" Error**
**Problem:** Can't access a page even when logged in

**Check permissions:**
```sql
SELECT username, role, permissions
FROM system_users
WHERE username = 'your_username';
```

**Fix permissions:**
```sql
-- Grant specific permission
UPDATE system_users
SET permissions = jsonb_set(permissions, '{import_data}', 'true'::jsonb)
WHERE username = 'your_username';

-- Or reset to role defaults
UPDATE system_users
SET role = 'admin'
WHERE username = 'your_username';
```

---

### **Locked Out (No Admin Access)**
**Problem:** No admin users available

**Solution:** Manually create admin via SQL:
```sql
-- Create emergency admin (you need to generate hash first)
-- Run: python -c "from werkzeug.security import generate_password_hash; print(generate_password_hash('NewPassword123'))"

INSERT INTO system_users (username, password_hash, email, full_name, role, permissions, is_active)
VALUES (
    'emergency_admin',
    'paste_generated_hash_here',
    'emergency@academy.local',
    'Emergency Administrator',
    'admin',
    '{"view_dashboard": true, "view_profiles": true, "view_data": true, "import_data": true, "export_data": true, "manage_users": true, "verification_queue": true}'::jsonb,
    TRUE
);
```

---

### **Session Expired**
**Problem:** Constantly redirected to login

**Causes:**
- Session cookie expired
- Server restarted (sessions lost)
- SECRET_KEY changed

**Solution:**
1. Login again
2. Check "Remember me" for longer sessions
3. Verify `SECRET_KEY` in `config.py` is set

---

### **Can't Delete User**
**Problem:** "Cannot delete your own account" or "Cannot delete the last admin user"

**Explanation:** These are safeguards to prevent system lockout.

**Solution:**
1. To delete yourself: Login as another admin
2. To delete last admin: Create another admin first
3. Or use SQL (not recommended):
   ```sql
   UPDATE system_users
   SET is_active = FALSE
   WHERE user_id = 123;
   ```

---

## 📊 Usage Examples

### **Example 1: Creating a New Data Entry User**
```
Role: Viewer
Permissions:
  ✅ View Dashboard
  ✅ View Profiles
  ✅ View Data
  ❌ Import Data
  ❌ Export Data
  ❌ Manage Users
  ❌ Verification Queue

Use Case: Team member who only needs to view data
```

### **Example 2: Creating a Data Manager**
```
Role: Manager
Permissions:
  ✅ View Dashboard
  ✅ View Profiles
  ✅ View Data
  ✅ Import Data
  ✅ Export Data
  ❌ Manage Users
  ✅ Verification Queue

Use Case: Program coordinator who manages data imports
```

### **Example 3: Custom Role (Report Viewer)**
```
Role: Custom
Permissions:
  ✅ View Dashboard
  ❌ View Profiles
  ❌ View Data
  ❌ Import Data
  ✅ Export Data
  ❌ Manage Users
  ❌ Verification Queue

Use Case: Leadership who only needs dashboard reports and exports
```

---

## 🔄 Workflow

### **Typical Admin Workflow**

1. **Login** as admin
2. **Create users** for team members
3. **Assign roles** based on job function
4. **Monitor activity** via audit logs
5. **Adjust permissions** as needed
6. **Deactivate users** when no longer needed

### **Typical Manager Workflow**

1. **Login** as manager
2. **Import data** from CSV/Excel
3. **Run verification** scripts
4. **View results** in dashboard
5. **Export data** for reports

### **Typical Viewer Workflow**

1. **Login** as viewer
2. **View dashboard** stats
3. **Browse profiles** to find specific users
4. **View data tables** for details
5. **Logout** when done

---

## 🔐 Best Practices

1. **Change Default Passwords Immediately**
   - Don't use Admin@123 in production
   - Use strong passwords (8+ chars, mixed case, numbers, symbols)

2. **Principle of Least Privilege**
   - Grant only necessary permissions
   - Start with "Viewer" and add permissions as needed

3. **Regular Audits**
   - Review user list monthly
   - Deactivate unused accounts
   - Check audit logs for suspicious activity

4. **Session Security**
   - Use HTTPS in production
   - Set secure cookies
   - Configure session timeouts

5. **Password Policy**
   - Enforce password complexity
   - Require periodic password changes
   - Never share accounts

6. **Backup**
   - Regularly backup `system_users` table
   - Keep admin credentials secure
   - Document user list offline

---

## 📝 Notes

- **Development Mode**: Default passwords are acceptable
- **Production Mode**: Change all default passwords and use HTTPS
- **Multi-Admin**: Create multiple admin accounts for redundancy
- **Custom Roles**: Use "Custom" role for unique permission combinations
- **Inactive Users**: Soft-deleted users remain in database for audit trail

---

**Version:** 1.0  
**Last Updated:** November 2024  
**Author:** GenAI Academy 2.0 Development Team

