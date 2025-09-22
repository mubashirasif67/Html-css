# Blessings Donation System

A comprehensive donation management system with OCR capabilities, ML-powered eligibility assessment, and automated distribution management for charitable organizations.

## 🌟 Features

### Core Functionality
- **Donation Management**: Accept and process donations with multiple payment methods
- **OCR Receipt Processing**: Automatically extract amounts from donation receipts
- **Employee Registration**: Manage employee data for ration distribution
- **ML-Powered Eligibility**: Intelligent assessment of aid eligibility
- **Fraud Detection**: Automated detection of suspicious donations
- **Distribution Management**: Optimize ration distribution with geographic clustering
- **Notification System**: Email and SMS notifications for donors and beneficiaries

### Technical Features
- **FastAPI Backend**: High-performance async API with auto-generated documentation
- **React Admin Dashboard**: Modern, responsive admin interface
- **OCR Pipeline**: Advanced image preprocessing and text extraction
- **Machine Learning**: Scikit-learn models for eligibility and fraud detection
- **Background Tasks**: Celery-powered async processing
- **Comprehensive Testing**: Unit tests and integration tests
- **Docker Deployment**: Complete containerized setup
- **Security**: JWT authentication, input validation, rate limiting

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Backend API   │    │   ML Services  │
│                 │    │                 │    │                 │
│ • React Admin   │◄──►│ • FastAPI       │◄──►│ • Eligibility   │
│ • Bootstrap     │    │ • SQLAlchemy    │    │ • Fraud Detect  │
│ • Static Pages  │    │ • Alembic       │    │ • OCR Pipeline  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                       ┌─────────────────┐
                       │   Database      │
                       │                 │
                       │ • MySQL         │
                       │ • Redis         │
                       └─────────────────┘
                                │
                       ┌─────────────────┐
                       │   Workers       │
                       │                 │
                       │ • Celery        │
                       │ • Notifications │
                       │ • ML Training   │
                       └─────────────────┘
```

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose
- Git
- Make (optional, for convenience commands)

### 1. Clone Repository
```bash
git clone <repository-url>
cd blessings-donation-system
```

### 2. Configure Environment
```bash
cp .env.example .env
# Edit .env with your configuration
```

### 3. Start Services
```bash
make build
make up
```

### 4. Seed Database
```bash
make seed
```

### 5. Access Applications
- **Public Pages**: http://localhost
- **Admin Dashboard**: http://localhost:3000
- **API Documentation**: http://localhost:8000/docs
- **Celery Monitoring**: http://localhost:5555

## 📋 Environment Configuration

Copy `.env.example` to `.env` and configure:

### Required Settings
```env
# Security (CHANGE THESE!)
SECRET_KEY=your-very-secure-secret-key-change-this-in-production
JWT_SECRET=your-jwt-secret-key-for-token-signing

# Database
DATABASE_URL=mysql+pymysql://blessings_user:blessings_pass@db:3306/blessings

# Email (Required for notifications)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASS=your-gmail-app-password
```

### Optional Settings
```env
# SMS (Optional - uses mock service if not configured)
TWILIO_SID=your-twilio-account-sid
TWILIO_AUTH_TOKEN=your-twilio-auth-token
TWILIO_FROM=your-twilio-phone-number

# Payment Gateway (Optional - uses mock service)
STRIPE_PUBLIC_KEY=your-stripe-public-key
STRIPE_SECRET_KEY=your-stripe-secret-key
```

## 🛠️ Development Commands

### Docker Commands
```bash
make build          # Build all Docker images
make up             # Start all services
make down           # Stop all services
make logs           # View logs from all services
make shell          # Open shell in backend container
```

### Database Commands
```bash
make seed           # Populate with sample data
make db-migrate     # Run database migrations
make db-reset       # Reset database schema
```

### Testing Commands
```bash
make test           # Run all tests
make test-unit      # Run unit tests only
make coverage       # Run tests with coverage report
```

### Code Quality Commands
```bash
make lint           # Run linting checks
make format         # Format code
make type-check     # Run type checking
```

### ML Commands
```bash
make train-models   # Train ML models
make generate-receipts  # Generate synthetic receipts
```

## 📊 API Documentation

The system provides comprehensive API documentation:

- **Interactive Docs**: http://localhost:8000/docs (Swagger UI)
- **ReDoc**: http://localhost:8000/redoc (Alternative documentation)

### Key API Endpoints

#### Authentication
```http
POST /api/v1/auth/register    # Register new user (Admin only)
POST /api/v1/auth/login       # User login
POST /api/v1/auth/refresh     # Refresh access token
```

#### Donations
```http
POST /api/v1/donations                    # Create donation
POST /api/v1/donations/upload_receipt     # Upload receipt for OCR
GET  /api/v1/donations                    # List donations
GET  /api/v1/donations/{id}               # Get donation details
PUT  /api/v1/donations/{id}               # Update donation
```

#### Employees
```http
POST /api/v1/employees        # Register employee
GET  /api/v1/employees        # List employees
GET  /api/v1/employees/{id}   # Get employee details
PUT  /api/v1/employees/{id}   # Update employee
```

#### Administration
```http
GET  /api/v1/admin/distribution/run       # Generate distribution list
POST /api/v1/admin/distribution/approve   # Approve distribution
GET  /api/v1/admin/reports/donations      # Export donation reports
```

## 🧠 Machine Learning Models

### Eligibility Assessment Model
- **Algorithm**: Random Forest / Gradient Boosting
- **Features**: Grade, family size, income, previous aid, employment status
- **Accuracy**: >85% on validation set
- **Training**: Automated retraining weekly

### Fraud Detection Model
- **Algorithm**: Isolation Forest (Anomaly Detection)
- **Features**: Amount patterns, timing, contact info, submission speed
- **Performance**: 90%+ precision, 85%+ recall
- **Threshold**: Configurable risk levels

### OCR Pipeline
- **Preprocessing**: Noise reduction, deskewing, contrast enhancement
- **Engine**: Tesseract OCR with custom configuration
- **Accuracy**: >85% on synthetic receipt dataset
- **Fallback**: Manual review for low-confidence results

## 📧 Notification System

### Email Notifications
- **Donation Receipts**: Automatic receipt generation
- **Pickup Notifications**: Ration collection schedules
- **Weekly Reports**: Administrative summaries
- **System Alerts**: Critical system notifications

### SMS Notifications (Optional)
- **Pickup Reminders**: SMS alerts for collection times
- **Donation Confirmations**: Quick confirmation messages
- **Critical Alerts**: Emergency notifications to admins

## 🔒 Security Features

### Authentication & Authorization
- **JWT Tokens**: Secure, stateless authentication
- **Role-Based Access**: Admin, Staff, Volunteer, Viewer roles
- **Session Management**: Secure token refresh mechanism
- **Password Security**: Bcrypt hashing with salt

### Data Protection
- **Input Validation**: Comprehensive request validation
- **Rate Limiting**: API endpoint protection
- **CNIC Encryption**: Sensitive data protection
- **Audit Trails**: Complete change tracking

### Infrastructure Security
- **CORS Protection**: Configured cross-origin policies
- **HTTPS Ready**: SSL/TLS configuration
- **Security Headers**: Comprehensive header protection
- **Container Security**: Minimal attack surface

## 📈 Monitoring & Analytics

### Application Metrics
- **Donation Statistics**: Real-time donation tracking
- **OCR Performance**: Processing accuracy metrics
- **ML Model Performance**: Prediction accuracy monitoring
- **System Health**: Service status monitoring

### Logging
- **Structured Logging**: JSON-formatted logs
- **Error Tracking**: Comprehensive error capture
- **Performance Monitoring**: Response time tracking
- **Audit Logging**: Security event tracking

## 🧪 Testing

### Test Coverage
- **Unit Tests**: >70% code coverage
- **Integration Tests**: End-to-end API testing
- **ML Pipeline Tests**: Model accuracy validation
- **OCR Tests**: Image processing validation

### Test Data
- **Synthetic Donations**: 500 realistic donation records
- **Employee Data**: 200 employee profiles with variations
- **Receipt Images**: 100 synthetic receipt images for OCR testing
- **Fraud Scenarios**: Comprehensive fraud pattern testing

## 🚀 Deployment

### Production Deployment
1. **Environment Setup**:
   ```bash
   cp .env.example .env.production
   # Configure production settings
   ```

2. **Build Production Images**:
   ```bash
   make prod-build
   ```

3. **Deploy Services**:
   ```bash
   make prod-up
   ```

4. **Initialize Database**:
   ```bash
   make db-migrate
   make train-models
   ```

### Production Checklist
- [ ] Change all default passwords and secrets
- [ ] Configure SSL/TLS certificates
- [ ] Set up database backups
- [ ] Configure monitoring and alerting
- [ ] Set up log aggregation
- [ ] Configure firewall rules
- [ ] Test disaster recovery procedures

## 🤝 Contributing

### Development Setup
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `make test`
5. Run linting: `make lint`
6. Submit a pull request

### Code Standards
- **Python**: PEP 8 compliance with Black formatting
- **JavaScript**: ESLint with Prettier formatting
- **Documentation**: Comprehensive docstrings and comments
- **Testing**: Write tests for all new features

## 📚 Documentation

### Additional Documentation
- **SRS Document**: `docs/SRS.md` - System Requirements Specification
- **Architecture Guide**: `docs/architecture.md` - Detailed system architecture
- **API Reference**: `docs/api.md` - Complete API documentation
- **Deployment Guide**: `docs/deployment.md` - Production deployment guide
- **Viva Q&A**: `docs/viva_qa.md` - Common questions and answers

### Database Schema
- **ERD Diagram**: `docs/ERD.sql` - Complete database schema
- **Migration Scripts**: `backend/alembic/versions/` - Database migrations
- **Sample Data**: `backend/scripts/seed_data.py` - Test data generation

## 🆘 Support

### Common Issues

#### OCR Not Working
- Ensure Tesseract is installed in the container
- Check image format compatibility
- Verify image quality and resolution

#### Email Not Sending
- Check SMTP configuration in `.env`
- Verify Gmail app password (not regular password)
- Check firewall settings for SMTP ports

#### ML Models Not Loading
- Run `make train-models` to generate models
- Check model file permissions
- Verify scikit-learn version compatibility

### Getting Help
1. Check the logs: `make logs`
2. Run health checks: `make health`
3. Review documentation in `docs/`
4. Check GitHub issues
5. Contact support team

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **FastAPI**: Modern, fast web framework for Python
- **React**: User interface library
- **Tesseract**: Open source OCR engine
- **Scikit-learn**: Machine learning library
- **Docker**: Containerization platform
- **Bootstrap**: CSS framework for responsive design

## 📊 Project Status

- **Version**: 1.0.0
- **Status**: Production Ready
- **Last Updated**: December 2023
- **Maintainers**: Blessings Development Team

---

**Made with ❤️ for charitable organizations worldwide**