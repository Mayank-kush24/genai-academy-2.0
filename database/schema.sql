-- GenAI Academy 2.0 Database Schema
-- PostgreSQL Schema with Automated Audit Logging

-- ============================================
-- Table 1: User PII (Personal Information)
-- ============================================
CREATE TABLE IF NOT EXISTS user_pii (
    email VARCHAR(255) PRIMARY KEY,
    name VARCHAR(255),
    phone_number VARCHAR(50),
    gender VARCHAR(50),
    country VARCHAR(100),
    state VARCHAR(100),
    city VARCHAR(100),
    date_of_birth DATE,
    designation VARCHAR(255),
    class_stream VARCHAR(100),
    degree_passout_year INTEGER,
    occupation VARCHAR(255),
    linkedin VARCHAR(500),
    participated_in_academy_1 BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index for faster searches
CREATE INDEX IF NOT EXISTS idx_user_pii_name ON user_pii(name);
CREATE INDEX IF NOT EXISTS idx_user_pii_phone ON user_pii(phone_number);

-- ============================================
-- Table 2: Courses (Badge Submissions)
-- ============================================
CREATE TABLE IF NOT EXISTS courses (
    email VARCHAR(255) NOT NULL,
    problem_statement TEXT NOT NULL,
    share_skill_badge_public_link TEXT,
    valid BOOLEAN DEFAULT NULL,
    remarks TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (email, problem_statement),
    FOREIGN KEY (email) REFERENCES user_pii(email) ON DELETE CASCADE ON UPDATE CASCADE
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_courses_email ON courses(email);
CREATE INDEX IF NOT EXISTS idx_courses_valid ON courses(valid);
CREATE INDEX IF NOT EXISTS idx_courses_problem_statement ON courses(problem_statement);

-- ============================================
-- Table 3: Skillboost Profile
-- ============================================
CREATE TABLE IF NOT EXISTS skillboost_profile (
    email VARCHAR(255) NOT NULL,
    google_cloud_skills_boost_profile_link TEXT NOT NULL,
    valid BOOLEAN DEFAULT NULL,
    remarks TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (email, google_cloud_skills_boost_profile_link),
    FOREIGN KEY (email) REFERENCES user_pii(email) ON DELETE CASCADE ON UPDATE CASCADE
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_skillboost_profile_email ON skillboost_profile(email);
CREATE INDEX IF NOT EXISTS idx_skillboost_profile_valid ON skillboost_profile(valid);

-- ============================================
-- Table 4: Master Classes (Attendance)
-- ============================================
CREATE TABLE IF NOT EXISTS master_classes (
    email VARCHAR(255) NOT NULL,
    master_class_name VARCHAR(255) NOT NULL,
    time_watched VARCHAR(50),
    valid BOOLEAN DEFAULT TRUE,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (email, master_class_name),
    FOREIGN KEY (email) REFERENCES user_pii(email) ON DELETE CASCADE ON UPDATE CASCADE
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_master_classes_email ON master_classes(email);
CREATE INDEX IF NOT EXISTS idx_master_classes_name ON master_classes(master_class_name);

-- ============================================
-- Table 5: Master Log (Audit Trail)
-- ============================================
CREATE TABLE IF NOT EXISTS master_log (
    log_id SERIAL PRIMARY KEY,
    table_name VARCHAR(100) NOT NULL,
    record_identifier TEXT NOT NULL,
    action VARCHAR(20) NOT NULL,
    changed_fields JSONB,
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    changed_by VARCHAR(100) DEFAULT 'system'
);

-- Index for faster log queries
CREATE INDEX IF NOT EXISTS idx_master_log_table_name ON master_log(table_name);
CREATE INDEX IF NOT EXISTS idx_master_log_changed_at ON master_log(changed_at);
CREATE INDEX IF NOT EXISTS idx_master_log_record_identifier ON master_log(record_identifier);

-- ============================================
-- AUTOMATED AUDIT LOGGING TRIGGERS
-- ============================================

-- Trigger Function for user_pii table
CREATE OR REPLACE FUNCTION log_user_pii_changes()
RETURNS TRIGGER AS $$
BEGIN
    IF (TG_OP = 'INSERT') THEN
        INSERT INTO master_log (table_name, record_identifier, action, changed_fields)
        VALUES ('user_pii', NEW.email, 'INSERT', row_to_json(NEW)::jsonb);
        RETURN NEW;
    ELSIF (TG_OP = 'UPDATE') THEN
        INSERT INTO master_log (table_name, record_identifier, action, changed_fields)
        VALUES ('user_pii', NEW.email, 'UPDATE', 
                jsonb_build_object('old', row_to_json(OLD)::jsonb, 'new', row_to_json(NEW)::jsonb));
        RETURN NEW;
    ELSIF (TG_OP = 'DELETE') THEN
        INSERT INTO master_log (table_name, record_identifier, action, changed_fields)
        VALUES ('user_pii', OLD.email, 'DELETE', row_to_json(OLD)::jsonb);
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_user_pii_audit
AFTER INSERT OR UPDATE OR DELETE ON user_pii
FOR EACH ROW EXECUTE FUNCTION log_user_pii_changes();

-- Trigger Function for courses table
CREATE OR REPLACE FUNCTION log_courses_changes()
RETURNS TRIGGER AS $$
BEGIN
    IF (TG_OP = 'INSERT') THEN
        INSERT INTO master_log (table_name, record_identifier, action, changed_fields)
        VALUES ('courses', NEW.email || ' - ' || NEW.problem_statement, 'INSERT', row_to_json(NEW)::jsonb);
        RETURN NEW;
    ELSIF (TG_OP = 'UPDATE') THEN
        INSERT INTO master_log (table_name, record_identifier, action, changed_fields)
        VALUES ('courses', NEW.email || ' - ' || NEW.problem_statement, 'UPDATE',
                jsonb_build_object('old', row_to_json(OLD)::jsonb, 'new', row_to_json(NEW)::jsonb));
        RETURN NEW;
    ELSIF (TG_OP = 'DELETE') THEN
        INSERT INTO master_log (table_name, record_identifier, action, changed_fields)
        VALUES ('courses', OLD.email || ' - ' || OLD.problem_statement, 'DELETE', row_to_json(OLD)::jsonb);
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_courses_audit
AFTER INSERT OR UPDATE OR DELETE ON courses
FOR EACH ROW EXECUTE FUNCTION log_courses_changes();

-- Trigger Function for skillboost_profile table
CREATE OR REPLACE FUNCTION log_skillboost_profile_changes()
RETURNS TRIGGER AS $$
BEGIN
    IF (TG_OP = 'INSERT') THEN
        INSERT INTO master_log (table_name, record_identifier, action, changed_fields)
        VALUES ('skillboost_profile', NEW.email, 'INSERT', row_to_json(NEW)::jsonb);
        RETURN NEW;
    ELSIF (TG_OP = 'UPDATE') THEN
        INSERT INTO master_log (table_name, record_identifier, action, changed_fields)
        VALUES ('skillboost_profile', NEW.email, 'UPDATE',
                jsonb_build_object('old', row_to_json(OLD)::jsonb, 'new', row_to_json(NEW)::jsonb));
        RETURN NEW;
    ELSIF (TG_OP = 'DELETE') THEN
        INSERT INTO master_log (table_name, record_identifier, action, changed_fields)
        VALUES ('skillboost_profile', OLD.email, 'DELETE', row_to_json(OLD)::jsonb);
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_skillboost_profile_audit
AFTER INSERT OR UPDATE OR DELETE ON skillboost_profile
FOR EACH ROW EXECUTE FUNCTION log_skillboost_profile_changes();

-- Trigger Function for master_classes table
CREATE OR REPLACE FUNCTION log_master_classes_changes()
RETURNS TRIGGER AS $$
BEGIN
    IF (TG_OP = 'INSERT') THEN
        INSERT INTO master_log (table_name, record_identifier, action, changed_fields)
        VALUES ('master_classes', NEW.email || ' - ' || NEW.master_class_name, 'INSERT', row_to_json(NEW)::jsonb);
        RETURN NEW;
    ELSIF (TG_OP = 'UPDATE') THEN
        INSERT INTO master_log (table_name, record_identifier, action, changed_fields)
        VALUES ('master_classes', NEW.email || ' - ' || NEW.master_class_name, 'UPDATE',
                jsonb_build_object('old', row_to_json(OLD)::jsonb, 'new', row_to_json(NEW)::jsonb));
        RETURN NEW;
    ELSIF (TG_OP = 'DELETE') THEN
        INSERT INTO master_log (table_name, record_identifier, action, changed_fields)
        VALUES ('master_classes', OLD.email || ' - ' || OLD.master_class_name, 'DELETE', row_to_json(OLD)::jsonb);
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_master_classes_audit
AFTER INSERT OR UPDATE OR DELETE ON master_classes
FOR EACH ROW EXECUTE FUNCTION log_master_classes_changes();

-- ============================================
-- Views for BI Dashboard Integration
-- ============================================

-- View: User Complete Profile with Course Count
CREATE OR REPLACE VIEW v_user_summary AS
SELECT 
    u.email,
    u.name,
    u.phone_number,
    u.country,
    u.state,
    u.city,
    u.designation,
    u.occupation,
    COUNT(DISTINCT c.problem_statement) as courses_completed,
    COUNT(DISTINCT CASE WHEN c.valid = TRUE THEN c.problem_statement END) as courses_verified,
    COUNT(DISTINCT mc.master_class_name) as masterclasses_attended,
    MAX(u.created_at) as registered_at
FROM user_pii u
LEFT JOIN courses c ON u.email = c.email
LEFT JOIN master_classes mc ON u.email = mc.email
GROUP BY u.email, u.name, u.phone_number, u.country, u.state, u.city, u.designation, u.occupation;

-- View: Course Verification Status
CREATE OR REPLACE VIEW v_course_verification_status AS
SELECT 
    problem_statement,
    COUNT(*) as total_submissions,
    COUNT(CASE WHEN valid = TRUE THEN 1 END) as verified,
    COUNT(CASE WHEN valid = FALSE THEN 1 END) as failed,
    COUNT(CASE WHEN valid IS NULL THEN 1 END) as pending
FROM courses
GROUP BY problem_statement;

-- View: Masterclass Attendance Summary
CREATE OR REPLACE VIEW v_masterclass_attendance AS
SELECT 
    master_class_name,
    COUNT(*) as total_attendees,
    COUNT(CASE WHEN time_watched = 'live' THEN 1 END) as live_attendees,
    COUNT(CASE WHEN time_watched = 'recorded' THEN 1 END) as recorded_attendees
FROM master_classes
GROUP BY master_class_name;

COMMENT ON TABLE user_pii IS 'Personal information of all academy participants';
COMMENT ON TABLE courses IS 'Course completion badge submissions with verification status';
COMMENT ON TABLE skillboost_profile IS 'Google Cloud Skills Boost profile links';
COMMENT ON TABLE master_classes IS 'Masterclass attendance records';
COMMENT ON TABLE master_log IS 'Automated audit trail for all data changes';

