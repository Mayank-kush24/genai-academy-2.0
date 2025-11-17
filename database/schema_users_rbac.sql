-- RBAC (Role-Based Access Control) User Management
-- Add this to your existing database

-- ============================================
-- Table: System Users (for authentication)
-- ============================================
CREATE TABLE IF NOT EXISTS system_users (
    user_id SERIAL PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    full_name VARCHAR(255),
    role VARCHAR(50) DEFAULT 'viewer',
    is_active BOOLEAN DEFAULT TRUE,
    
    -- Granular Permissions (JSON or individual columns)
    permissions JSONB DEFAULT '{}',
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_system_users_username ON system_users(username);
CREATE INDEX IF NOT EXISTS idx_system_users_email ON system_users(email);
CREATE INDEX IF NOT EXISTS idx_system_users_role ON system_users(role);
CREATE INDEX IF NOT EXISTS idx_system_users_active ON system_users(is_active);

-- ============================================
-- Default Roles and Permissions
-- ============================================
-- Roles:
--   - admin: Full access to everything
--   - manager: Can view data, manage imports, run verifications
--   - viewer: Read-only access
--   - custom: Custom permissions defined in permissions JSONB

-- Permissions structure (stored in JSONB):
-- {
--   "view_dashboard": true,
--   "view_profiles": true,
--   "view_data": true,
--   "import_data": false,
--   "export_data": false,
--   "manage_users": false,
--   "verification_queue": true
-- }

-- ============================================
-- Create default admin user
-- ============================================
-- After running this schema, run: python scripts/create_default_users.py
-- This will create default users with properly hashed passwords:
--   - admin / Admin@123
--   - manager / Manager@123
--   - viewer / Viewer@123

-- ============================================
-- Audit trigger for system_users
-- ============================================
CREATE OR REPLACE FUNCTION log_system_user_changes()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO master_log (table_name, record_identifier, action, changed_fields)
        VALUES ('system_users', NEW.username, 'INSERT', 
                jsonb_build_object('username', NEW.username, 'email', NEW.email, 'role', NEW.role));
    ELSIF TG_OP = 'UPDATE' THEN
        INSERT INTO master_log (table_name, record_identifier, action, changed_fields)
        VALUES ('system_users', NEW.username, 'UPDATE',
                jsonb_build_object(
                    'username', NEW.username,
                    'role', NEW.role,
                    'is_active', NEW.is_active,
                    'permissions', NEW.permissions
                ));
    ELSIF TG_OP = 'DELETE' THEN
        INSERT INTO master_log (table_name, record_identifier, action, changed_fields)
        VALUES ('system_users', OLD.username, 'DELETE',
                jsonb_build_object('username', OLD.username, 'email', OLD.email));
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger
DROP TRIGGER IF EXISTS system_users_audit_trigger ON system_users;
CREATE TRIGGER system_users_audit_trigger
AFTER INSERT OR UPDATE OR DELETE ON system_users
FOR EACH ROW EXECUTE FUNCTION log_system_user_changes();

-- ============================================
-- Update timestamp trigger
-- ============================================
CREATE OR REPLACE FUNCTION update_system_users_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS update_system_users_timestamp_trigger ON system_users;
CREATE TRIGGER update_system_users_timestamp_trigger
BEFORE UPDATE ON system_users
FOR EACH ROW EXECUTE FUNCTION update_system_users_timestamp();

-- ============================================
-- Views for user management
-- ============================================
CREATE OR REPLACE VIEW vw_system_users AS
SELECT 
    user_id,
    username,
    email,
    full_name,
    role,
    is_active,
    permissions,
    created_at,
    last_login,
    CASE 
        WHEN last_login > CURRENT_TIMESTAMP - INTERVAL '7 days' THEN 'Active'
        WHEN last_login IS NULL THEN 'Never Logged In'
        ELSE 'Inactive'
    END as login_status
FROM system_users
WHERE is_active = TRUE
ORDER BY created_at DESC;

-- ============================================
-- Helper functions
-- ============================================

-- Function to check if user has specific permission
CREATE OR REPLACE FUNCTION user_has_permission(p_username VARCHAR, p_permission VARCHAR)
RETURNS BOOLEAN AS $$
DECLARE
    v_has_permission BOOLEAN;
BEGIN
    SELECT 
        CASE 
            WHEN role = 'admin' THEN TRUE
            WHEN permissions ? p_permission THEN (permissions->p_permission)::boolean
            ELSE FALSE
        END INTO v_has_permission
    FROM system_users
    WHERE username = p_username AND is_active = TRUE;
    
    RETURN COALESCE(v_has_permission, FALSE);
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- Comments
-- ============================================
COMMENT ON TABLE system_users IS 'System users for RBAC authentication';
COMMENT ON COLUMN system_users.role IS 'User role: admin, manager, viewer, custom';
COMMENT ON COLUMN system_users.permissions IS 'Granular permissions in JSON format';
COMMENT ON COLUMN system_users.is_active IS 'Whether the user account is active';

