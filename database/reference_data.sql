-- Reference Data for GenAI Academy 2.0
-- This file contains reference data for courses, tracks, and masterclasses

-- ============================================
-- Track and Course Definitions
-- ============================================

-- Create a reference table for tracks
CREATE TABLE IF NOT EXISTS tracks (
    track_id SERIAL PRIMARY KEY,
    track_name VARCHAR(255) UNIQUE NOT NULL,
    track_description TEXT
);

-- Create a reference table for course definitions
CREATE TABLE IF NOT EXISTS course_definitions (
    course_id SERIAL PRIMARY KEY,
    problem_statement TEXT UNIQUE NOT NULL,
    course_name VARCHAR(500),
    track_id INTEGER REFERENCES tracks(track_id),
    skillboost_badge_pattern TEXT,
    display_order INTEGER
);

-- Create a reference table for masterclass definitions
CREATE TABLE IF NOT EXISTS masterclass_definitions (
    masterclass_id SERIAL PRIMARY KEY,
    master_class_name VARCHAR(255) UNIQUE NOT NULL,
    masterclass_description TEXT,
    scheduled_date DATE,
    display_order INTEGER
);

-- ============================================
-- Insert Track Data (5 tracks)
-- ============================================
INSERT INTO tracks (track_name, track_description) VALUES
('Generative AI Fundamentals', 'Foundation track covering basic concepts of Generative AI'),
('Machine Learning Engineering', 'Track focused on ML engineering and model deployment'),
('AI Application Development', 'Building AI-powered applications and solutions'),
('Data Analytics with AI', 'Leveraging AI for data analysis and insights'),
('Cloud AI Solutions', 'Google Cloud AI platform and services')
ON CONFLICT (track_name) DO NOTHING;

-- ============================================
-- Insert Course Definitions (14 courses)
-- ============================================
-- Note: Update these problem_statements to match your actual course names from the CSV

INSERT INTO course_definitions (problem_statement, course_name, track_id, display_order) VALUES
-- Track 1: Generative AI Fundamentals (3 courses)
('Introduction to Generative AI', 'Introduction to Generative AI', 1, 1),
('Introduction to Large Language Models', 'Introduction to Large Language Models', 1, 2),
('Introduction to Responsible AI', 'Introduction to Responsible AI', 1, 3),

-- Track 2: Machine Learning Engineering (3 courses)
('Introduction to Machine Learning', 'Introduction to Machine Learning', 2, 4),
('Machine Learning Operations (MLOps)', 'Machine Learning Operations (MLOps)', 2, 5),
('Feature Engineering', 'Feature Engineering', 2, 6),

-- Track 3: AI Application Development (3 courses)
('Generative AI with Vertex AI', 'Generative AI with Vertex AI', 3, 7),
('Building AI Applications', 'Building AI Applications', 3, 8),
('Prompt Design in Vertex AI', 'Prompt Design in Vertex AI', 3, 9),

-- Track 4: Data Analytics with AI (2 courses)
('BigQuery Machine Learning', 'BigQuery Machine Learning', 4, 10),
('Data Analysis with AI', 'Data Analysis with AI', 4, 11),

-- Track 5: Cloud AI Solutions (3 courses)
('Google Cloud AI Services', 'Google Cloud AI Services', 5, 12),
('Document AI', 'Document AI', 5, 13),
('Vision AI', 'Vision AI', 5, 14)
ON CONFLICT (problem_statement) DO NOTHING;

-- ============================================
-- Insert Masterclass Definitions (14 masterclasses)
-- ============================================
INSERT INTO masterclass_definitions (master_class_name, masterclass_description, display_order) VALUES
('Masterclass 1: Introduction to AI', 'Kickoff session introducing AI concepts', 1),
('Masterclass 2: Generative AI Deep Dive', 'Deep dive into generative AI technologies', 2),
('Masterclass 3: LLM Architectures', 'Understanding large language model architectures', 3),
('Masterclass 4: Prompt Engineering', 'Best practices for prompt engineering', 4),
('Masterclass 5: AI Ethics and Responsibility', 'Responsible AI development and deployment', 5),
('Masterclass 6: ML Model Training', 'Techniques for training machine learning models', 6),
('Masterclass 7: MLOps Best Practices', 'Operationalizing machine learning workflows', 7),
('Masterclass 8: Building with Vertex AI', 'Hands-on with Google Cloud Vertex AI', 8),
('Masterclass 9: BigQuery ML', 'Machine learning with BigQuery', 9),
('Masterclass 10: Document Processing with AI', 'Automating document workflows', 10),
('Masterclass 11: Computer Vision Applications', 'Building vision AI solutions', 11),
('Masterclass 12: AI Application Architecture', 'Designing scalable AI applications', 12),
('Masterclass 13: Real-world AI Case Studies', 'Industry applications of AI', 13),
('Masterclass 14: Future of AI', 'Emerging trends and future directions', 14)
ON CONFLICT (master_class_name) DO NOTHING;

-- ============================================
-- Create helper view for track completion
-- ============================================
CREATE OR REPLACE VIEW v_track_completion AS
SELECT 
    u.email,
    u.name,
    t.track_id,
    t.track_name,
    COUNT(DISTINCT cd.course_id) as total_courses_in_track,
    COUNT(DISTINCT CASE WHEN c.valid = TRUE THEN cd.course_id END) as completed_courses,
    CASE 
        WHEN COUNT(DISTINCT cd.course_id) = COUNT(DISTINCT CASE WHEN c.valid = TRUE THEN cd.course_id END)
        THEN TRUE 
        ELSE FALSE 
    END as track_completed
FROM user_pii u
CROSS JOIN tracks t
LEFT JOIN course_definitions cd ON cd.track_id = t.track_id
LEFT JOIN courses c ON c.email = u.email AND c.problem_statement = cd.problem_statement AND c.valid = TRUE
GROUP BY u.email, u.name, t.track_id, t.track_name;

-- ============================================
-- Create helper view for certificate eligibility
-- ============================================
CREATE OR REPLACE VIEW v_certificate_eligible AS
SELECT 
    email,
    name,
    track_id,
    track_name,
    completed_courses,
    total_courses_in_track
FROM v_track_completion
WHERE track_completed = TRUE;

COMMENT ON TABLE tracks IS 'Definition of learning tracks in the academy';
COMMENT ON TABLE course_definitions IS 'Master list of all available courses';
COMMENT ON TABLE masterclass_definitions IS 'Master list of all masterclass sessions';
COMMENT ON VIEW v_track_completion IS 'Track-wise completion status for all users';
COMMENT ON VIEW v_certificate_eligible IS 'Users eligible for track certificates';

