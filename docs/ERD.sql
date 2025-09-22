-- Entity Relationship Diagram SQL
-- Blessings Distribution System

-- Users Table
CREATE TABLE users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('admin', 'donor', 'employee') NOT NULL DEFAULT 'donor',
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_users_email (email),
    INDEX idx_users_role (role)
);

-- Employees Table
CREATE TABLE employees (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT,
    cnic VARCHAR(15) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    father_name VARCHAR(100) NOT NULL,
    grade ENUM('1','2','3','4','5','10','15','20') NOT NULL,
    designation VARCHAR(100),
    mobile VARCHAR(15) NOT NULL,
    address TEXT,
    family_key VARCHAR(10) NOT NULL,
    family_size INT DEFAULT 1,
    latitude DECIMAL(10,8),
    longitude DECIMAL(11,8),
    is_eligible BOOLEAN DEFAULT TRUE,
    eligibility_score DECIMAL(3,2) DEFAULT 0.50,
    fraud_flag BOOLEAN DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
    INDEX idx_employees_cnic (cnic),
    INDEX idx_employees_family_key (family_key),
    INDEX idx_employees_grade (grade),
    INDEX idx_employees_eligibility (is_eligible)
);

-- Donations Table
CREATE TABLE donations (
    id INT PRIMARY KEY AUTO_INCREMENT,
    donor_id INT NOT NULL,
    donor_name VARCHAR(100) NOT NULL,
    donor_email VARCHAR(100),
    donor_cnic VARCHAR(15),
    amount DECIMAL(12,2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'PKR',
    donation_type ENUM('zakat', 'sadaqah', 'general') NOT NULL,
    receipt_image_path VARCHAR(255),
    detected_amount DECIMAL(12,2),
    confidence DECIMAL(3,2),
    ocr_text TEXT,
    transaction_hash VARCHAR(64),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (donor_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_donations_donor (donor_id),
    INDEX idx_donations_hash (transaction_hash),
    INDEX idx_donations_date (created_at)
);

-- Distribution Runs Table
CREATE TABLE distribution_runs (
    id INT PRIMARY KEY AUTO_INCREMENT,
    admin_id INT NOT NULL,
    run_date DATETIME NOT NULL,
    status ENUM('pending', 'approved', 'completed') DEFAULT 'pending',
    total_beneficiaries INT DEFAULT 0,
    total_amount DECIMAL(12,2) DEFAULT 0.00,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (admin_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_distribution_runs_admin (admin_id),
    INDEX idx_distribution_runs_date (run_date),
    INDEX idx_distribution_runs_status (status)
);

-- Distributions Table
CREATE TABLE distributions (
    id INT PRIMARY KEY AUTO_INCREMENT,
    employee_id INT NOT NULL,
    run_id INT NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    pickup_slot VARCHAR(50),
    notification_sent BOOLEAN DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE,
    FOREIGN KEY (run_id) REFERENCES distribution_runs(id) ON DELETE CASCADE,
    INDEX idx_distributions_employee (employee_id),
    INDEX idx_distributions_run (run_id),
    INDEX idx_distributions_slot (pickup_slot)
);

-- Feedback Table
CREATE TABLE feedback (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    feedback_text TEXT NOT NULL,
    sentiment ENUM('positive', 'negative', 'neutral'),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_feedback_user (user_id),
    INDEX idx_feedback_sentiment (sentiment)
);

-- Relationships:
-- 1. User -> Donations (One-to-Many)
-- 2. User -> Employees (One-to-Many, Admin creates employees)
-- 3. User -> DistributionRuns (One-to-Many, Admin creates runs)
-- 4. Employee -> Distributions (One-to-Many)
-- 5. DistributionRun -> Distributions (One-to-Many)
-- 6. User -> Feedback (One-to-Many)

-- Sample Data for Testing
INSERT INTO users (name, email, password_hash, role) VALUES
('Admin User', 'admin@blessings.org', '$2b$12$hashedpassword', 'admin'),
('Donor One', 'donor1@test.com', '$2b$12$hashedpassword', 'donor');

INSERT INTO employees (user_id, name, father_name, cnic, family_key, grade, mobile, family_size, is_eligible, eligibility_score) VALUES
(1, 'John Doe', 'Jane Doe', '12345-1234567-1', '1234567', '5', '03123456789', 4, TRUE, 0.85),
(1, 'Alice Smith', 'Bob Smith', '54321-7654321-2', '7654321', '3', '03219876543', 3, TRUE, 0.95);

INSERT INTO donations (donor_id, donor_name, amount, donation_type) VALUES
(2, 'Donor One', 10000.00, 'zakat'),
(2, 'Donor One', 5000.00, 'sadaqah');

-- Views for Common Queries
CREATE VIEW eligible_employees AS
SELECT e.*, u.name as created_by_name
FROM employees e
LEFT JOIN users u ON e.user_id = u.id
WHERE e.is_eligible = TRUE
ORDER BY e.eligibility_score DESC;

CREATE VIEW donation_summary AS
SELECT
    DATE(created_at) as donation_date,
    donation_type,
    COUNT(*) as count,
    SUM(amount) as total_amount,
    AVG(amount) as avg_amount
FROM donations
GROUP BY DATE(created_at), donation_type;

CREATE VIEW distribution_summary AS
SELECT
    dr.run_date,
    dr.status,
    dr.total_beneficiaries,
    dr.total_amount,
    COUNT(d.id) as assigned_distributions
FROM distribution_runs dr
LEFT JOIN distributions d ON dr.id = d.run_id
GROUP BY dr.id, dr.run_date, dr.status, dr.total_beneficiaries, dr.total_amount;