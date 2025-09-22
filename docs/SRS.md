# Software Requirements Specification
# Blessings Distribution System

## 1. Introduction

### 1.1 Purpose
The Blessings Distribution System is a comprehensive web application designed to streamline the process of collecting donations, registering beneficiaries, and distributing aid efficiently and transparently.

### 1.2 Scope
- Public donation collection with OCR receipt processing
- Employee/beneficiary registration and management
- ML-powered eligibility determination
- Fraud detection and prevention
- Automated distribution list generation
- Pickup scheduling optimization
- Notification system (email/SMS)
- Admin dashboard for management
- Reporting and analytics

### 1.3 Definitions
- **Donor**: Individual or organization making donations
- **Employee/Beneficiary**: Person eligible for aid distribution
- **Admin**: System administrator managing the platform
- **Distribution Run**: Automated process of generating aid distribution lists
- **OCR**: Optical Character Recognition for receipt processing
- **ML**: Machine Learning for eligibility and fraud detection

## 2. System Requirements

### 2.1 Functional Requirements

#### 2.1.1 User Management
- FR-1.1: User registration with role assignment (donor, admin)
- FR-1.2: Secure login with JWT authentication
- FR-1.3: Password hashing and validation
- FR-1.4: Role-based access control

#### 2.1.2 Donation Management
- FR-2.1: Online donation form with amount and type selection
- FR-2.2: Receipt image upload and OCR processing
- FR-2.3: Automatic amount detection from receipts
- FR-2.4: Transaction hash generation for transparency
- FR-2.5: Donation history tracking

#### 2.1.3 Employee Management
- FR-3.1: Employee registration with CNIC validation
- FR-3.2: Family deduplication using CNIC family key
- FR-3.3: Employee eligibility status tracking
- FR-3.4: Employee search and filtering
- FR-3.5: Bulk employee import/export

#### 2.1.4 Distribution Management
- FR-4.1: Automated distribution list generation
- FR-4.2: ML-based eligibility scoring
- FR-4.3: Family deduplication in distribution
- FR-4.4: Fraud detection flagging
- FR-4.5: Pickup slot assignment using clustering
- FR-4.6: Distribution approval workflow

#### 2.1.5 Notification System
- FR-5.1: Email notifications for donation receipts
- FR-5.2: SMS notifications for pickup scheduling
- FR-5.3: Mock notification service for testing
- FR-5.4: Notification template management

#### 2.1.6 Reporting and Analytics
- FR-6.1: Dashboard with key metrics
- FR-6.2: Donation trends and analytics
- FR-6.3: Export functionality (CSV, Excel)
- FR-6.4: ML model performance metrics
- FR-6.5: Audit trail and transparency reports

### 2.2 Non-Functional Requirements

#### 2.2.1 Performance
- NFR-1.1: System should handle 1000+ concurrent users
- NFR-1.2: OCR processing should complete within 5 seconds
- NFR-1.3: Distribution generation should complete within 30 seconds
- NFR-1.4: API response time < 200ms for simple queries

#### 2.2.2 Security
- NFR-2.1: All passwords must be hashed using bcrypt
- NFR-2.2: CNIC numbers must be encrypted in database
- NFR-2.3: JWT tokens must expire within 30 minutes
- NFR-2.4: Rate limiting on sensitive endpoints
- NFR-2.5: Input validation and sanitization

#### 2.2.3 Usability
- NFR-3.1: Responsive design for mobile and desktop
- NFR-3.2: Intuitive user interface
- NFR-3.3: Clear error messages and feedback
- NFR-3.4: Accessibility compliance (WCAG 2.1)

#### 2.2.4 Reliability
- NFR-4.1: 99.9% uptime for production environment
- NFR-4.2: Automatic database backups
- NFR-4.3: Error logging and monitoring
- NFR-4.4: Graceful degradation for failed services

#### 2.2.5 Scalability
- NFR-5.1: Horizontal scaling support
- NFR-5.2: Database connection pooling
- NFR-5.3: Caching for frequently accessed data
- NFR-5.4: Background job processing with Celery

## 3. System Architecture

### 3.1 Technology Stack
- **Frontend**: React 18 + Vite, Bootstrap 5, Chart.js
- **Backend**: FastAPI + Python 3.11, SQLAlchemy, Alembic
- **Database**: MySQL 8.0
- **Cache/Broker**: Redis 7
- **ML**: Scikit-learn, Pandas, NumPy
- **OCR**: PyTesseract + OpenCV
- **Containerization**: Docker + Docker Compose

### 3.2 System Components
1. **Web Server**: FastAPI application server
2. **Database Server**: MySQL with connection pooling
3. **Cache Server**: Redis for session and data caching
4. **Background Worker**: Celery for OCR and notifications
5. **ML Services**: Python services for eligibility and fraud detection
6. **Frontend Application**: React SPA for admin interface
7. **Static File Server**: Nginx for public pages

### 3.3 Data Flow
1. User submits donation form with optional receipt
2. OCR service processes receipt image
3. Donation record created with transaction hash
4. Admin generates distribution using ML models
5. Fraud detection flags suspicious records
6. Eligible employees clustered for pickup scheduling
7. Notifications sent to beneficiaries
8. Distribution approved and executed

## 4. Interface Requirements

### 4.1 User Interfaces
- **Public Donation Form**: HTML form with file upload
- **Employee Registration**: HTML form with validation
- **Admin Dashboard**: React application with multiple views
- **API Documentation**: Swagger UI at /api/docs

### 4.2 External Interfaces
- **Email Service**: SMTP integration (Gmail, Outlook, etc.)
- **SMS Service**: Twilio API (with mock fallback)
- **OCR Service**: PyTesseract with OpenCV preprocessing
- **ML Services**: Scikit-learn models with joblib persistence

## 5. Data Requirements

### 5.1 Data Models
- **Users**: Authentication and role information
- **Donations**: Donation records with OCR data
- **Employees**: Beneficiary information with eligibility
- **DistributionRuns**: Distribution generation records
- **Distributions**: Individual aid allocations
- **Feedback**: User feedback with sentiment analysis

### 5.2 Data Storage
- **Primary Database**: MySQL 8.0 with ACID compliance
- **File Storage**: Local filesystem for receipt images
- **Cache**: Redis for session and temporary data
- **ML Models**: Joblib files for model persistence

### 5.3 Data Security
- Passwords: bcrypt hashing with salt
- CNIC: AES encryption with key rotation
- PII: Masking in logs and displays
- Backups: Encrypted database backups

## 6. Implementation Constraints

### 6.1 Hardware Requirements
- Minimum: 4GB RAM, 2 CPU cores, 20GB storage
- Recommended: 8GB RAM, 4 CPU cores, 50GB storage
- Production: Load balanced with dedicated resources

### 6.2 Software Requirements
- Docker 20.10+
- Docker Compose 2.0+
- Python 3.11+
- Node.js 18+
- MySQL 8.0+
- Redis 7+

### 6.3 Development Tools
- Git for version control
- pytest for testing
- Black for code formatting
- Flake8 for linting
- MyPy for type checking

## 7. Testing Requirements

### 7.1 Unit Testing
- Backend API endpoints
- ML model functions
- OCR processing
- Utility functions

### 7.2 Integration Testing
- Database operations
- External service integrations
- File upload processing
- Background job execution

### 7.3 Performance Testing
- Load testing for 1000+ concurrent users
- OCR processing performance
- ML model inference speed
- Database query optimization

### 7.4 Security Testing
- Authentication and authorization
- Input validation
- SQL injection prevention
- XSS protection

## 8. Deployment Requirements

### 8.1 Environment Setup
- Docker containers for all services
- Environment variable configuration
- Database initialization and migration
- SSL certificate for production

### 8.2 Monitoring
- Application performance monitoring
- Error tracking and alerting
- Database performance metrics
- User activity logging

### 8.3 Backup and Recovery
- Daily database backups
- File system backups
- Configuration backups
- Disaster recovery plan

## 9. Maintenance Requirements

### 9.1 Regular Maintenance
- Security updates and patches
- Database optimization and cleanup
- Log rotation and archiving
- ML model retraining with new data

### 9.2 Monitoring
- System health checks
- Performance metrics collection
- Error rate monitoring
- User feedback analysis

## 10. Appendices

### 10.1 API Documentation
Available at `/api/docs` when system is running

### 10.2 Database Schema
See `/docs/ERD.sql` for complete schema

### 10.3 Test Cases
See `/backend/tests/` for comprehensive test suite

### 10.4 Deployment Guide
See `README.md` for detailed setup instructions