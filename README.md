# Blessings Foundation - Charity Management System

A comprehensive charity management system with OCR capabilities, ML-powered distribution, and transparent donation tracking.

## 🚀 Features

- **Donation Management**: Accept and track donations with multiple payment methods
- **OCR Receipt Processing**: Automatically extract amounts from uploaded receipts
- **ML-Powered Distribution**: Fair beneficiary selection using eligibility scoring and fraud detection
- **Family Deduplication**: Ensure one ration per household using CNIC-based deduplication
- **Pickup Scheduling**: Clustered scheduling to minimize crowding
- **Blockchain Receipts**: SHA256 hashed receipts for transparency
- **Real-time Notifications**: Email and SMS notifications for donors and beneficiaries
- **Admin Dashboard**: React-based admin panel with analytics

## 🛠️ Tech Stack

- **Frontend**: HTML + CSS + Bootstrap (public), React (admin dashboard)
- **Backend**: Python 3.11, FastAPI
- **Database**: MySQL 8.0
- **ORM**: SQLAlchemy + Alembic
- **Cache/Queue**: Redis + Celery
- **OCR**: pytesseract + OpenCV
- **ML**: scikit-learn (eligibility & fraud detection)
- **Notifications**: Email (SMTP) + SMS (Twilio mock)
- **Containerization**: Docker + docker-compose

## 📋 Prerequisites

- Docker & Docker Compose
- 8GB RAM minimum
- 10GB free disk space

## 🚀 Quick Start

### 1. Clone the repository
```bash
git clone https://github.com/yourusername/blessings-fyp.git
cd blessings-fyp
```

### 2. Set up environment variables
```bash
cp .env.example .env
# Edit .env with your configuration
```

### 3. Build and run with Docker Compose
```bash
# Build all containers
make build

# Start all services
make up

# Wait for services to be ready, then run migrations
make migrate

# Seed database with sample data
make seed

# Train ML models
make train
```

### 4. Access the applications

- **Public Website**: http://localhost:8080
- **Admin Dashboard**: http://localhost:3000
- **API Documentation**: http://localhost:8000/docs
- **Default Admin Credentials**:
  - Email: `admin@blessings.org`
  - Password: `Admin@123456`

## 📝 Step-by-Step Commands

### Build and Run
```bash
# Build Docker images
docker-compose build

# Start all services
docker-compose up -d

# Check service status
docker-compose ps

# View logs
docker-compose logs -f
```

### Database Setup
```bash
# Run migrations
docker-compose exec backend alembic upgrade head

# Seed with sample data (200 employees, 500 donations)
docker-compose exec backend python scripts/seed_data.py

# Generate synthetic receipts for OCR testing
docker-compose exec backend python scripts/generate_receipts.py
```

### ML Model Training
```bash
# Train eligibility model
docker-compose exec backend python app/ml/train_eligibility.py

# Train fraud detection model
docker-compose exec backend python app/ml/train_fraud.py
```

### Run Tests
```bash
# Run all tests with coverage
make test

# Run unit tests only
make test-unit

# Run integration tests
make test-integration

# Generate coverage report
docker-compose exec backend pytest tests/ --cov=app --cov-report=html
```

### Static Checks
```bash
# Run linting
make lint

# Format code
make format
```

## 🔧 Development Commands

### Access containers
```bash
# Backend shell
make shell

# MySQL shell
make shell-db

# View Celery worker logs
make logs-celery
```

### Clean up
```bash
# Stop all services
make down

# Clean everything (including volumes)
make clean
```

## 📚 API Documentation

### Key Endpoints

#### Authentication
```bash
# Register
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"SecurePass123!","name":"John Doe","role":"donor"}'

# Login
curl -X POST http://localhost:8000/api/auth/login/json \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@blessings.org","password":"Admin@123456"}'
```

#### Donations
```bash
# Create donation
curl -X POST http://localhost:8000/api/donations \
  -H "Content-Type: application/json" \
  -d '{"donor_name":"Ali Ahmed","donor_email":"ali@example.com","donation_type":"zakat","amount":5000,"payment_method":"cash"}'

# Upload receipt for OCR
curl -X POST http://localhost:8000/api/donations/upload_receipt \
  -F "file=@receipt.jpg"
```

#### Distribution
```bash
# Generate distribution (Admin only)
curl -X GET "http://localhost:8000/api/admin/distribution/run?distribution_date=2024-01-15&max_beneficiaries=100" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Approve distribution
curl -X POST http://localhost:8000/api/admin/distribution/approve \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"distribution_run_id":1,"send_notifications":true}'
```

## 🧪 Testing

### Unit Tests
Tests for individual components:
- Authentication (`test_auth.py`)
- OCR processing (`test_ocr.py`)
- ML models (`test_ml.py`)
- Distribution logic (`test_distribution.py`)

### Integration Tests
End-to-end tests (`test_integration.py`):
- Complete donation flow
- Employee registration and eligibility
- OCR receipt upload
- Distribution generation

### Run Tests
```bash
# All tests
pytest tests/ -v

# With coverage
pytest tests/ --cov=app --cov-report=term-missing

# Specific test file
pytest tests/test_ocr.py -v
```

## 📊 ML Models

### Eligibility Model
- **Algorithm**: RandomForest Classifier
- **Features**: grade, family_size, income, previous_aid_count, days_since_last_aid
- **Metrics**: ROC-AUC > 0.85 on synthetic data

### Fraud Detection Model
- **Algorithm**: Isolation Forest
- **Features**: amount patterns, frequency, timing anomalies, duplication flags
- **Contamination Factor**: 0.1 (10% expected anomalies)

### Model Retraining
Models are automatically retrained weekly via Celery beat schedule.

## 🔐 Security Features

- **Password Security**: Bcrypt hashing with salt
- **JWT Authentication**: Access & refresh tokens
- **CNIC Masking**: Shows only last 4 digits in UI
- **Rate Limiting**: 60 requests/minute per IP
- **Input Validation**: Pydantic schemas
- **CORS Protection**: Configured origins only

## 📈 Performance Metrics

### OCR Accuracy
- **Target**: >85% on synthetic receipts
- **Confidence Threshold**: 0.8
- **Processing Time**: <2 seconds per image

### Distribution Efficiency
- **Deduplication Rate**: ~10-15% of applicants
- **Processing Time**: <5 seconds for 1000 beneficiaries
- **Clustering**: KMeans for location-based scheduling

## 🚢 Deployment

### Production Configuration
1. Update `.env` with production values
2. Enable real email/SMS providers
3. Use production database
4. Configure SSL certificates
5. Set up monitoring (optional)

### Docker Production Build
```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

## 📝 Documentation

### System Architecture
```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Frontend  │────▶│   FastAPI   │────▶│    MySQL    │
│  (Bootstrap)│     │   Backend   │     │   Database  │
└─────────────┘     └─────────────┘     └─────────────┘
                           │
                    ┌──────┴──────┐
                    │             │
              ┌─────▼─────┐ ┌────▼────┐
              │   Celery  │ │  Redis  │
              │  Workers  │ │  Cache  │
              └───────────┘ └─────────┘
                    │
            ┌───────┴────────┐
            │                │
      ┌─────▼─────┐   ┌─────▼─────┐
      │    OCR    │   │    ML     │
      │ Processing│   │  Models   │
      └───────────┘   └───────────┘
```

### Database Schema (ERD)
```sql
-- Core tables
users (id, email, password_hash, role, ...)
employees (id, cnic, name, grade, family_key, ...)
donations (id, donor_id, amount, type, blockchain_hash, ...)
distributions (id, date, status, total_beneficiaries, ...)
distribution_beneficiaries (id, distribution_id, employee_id, ...)
pickup_schedules (id, distribution_id, date, time, location, ...)
notifications (id, user_id, type, status, ...)
```

## 🎯 Acceptance Criteria

✅ Docker Compose starts all services successfully  
✅ Database migrations run automatically  
✅ Sample data seeds correctly (200 employees, 500 donations)  
✅ OCR detects amounts with >85% accuracy on synthetic receipts  
✅ ML models train and save successfully  
✅ Distribution generation works with deduplication  
✅ Admin can approve distributions and trigger notifications  
✅ Tests achieve >70% code coverage  
✅ API documentation accessible at /docs  

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License.

## 👥 Team

- **Project Lead**: Your Name
- **Backend Developer**: Team Member 1
- **Frontend Developer**: Team Member 2
- **ML Engineer**: Team Member 3

## 📞 Support

For issues or questions:
- Create an issue on GitHub
- Email: support@blessings.org
- Documentation: See `/docs` folder

---

**Note**: This is a Final Year Project (FYP) demonstration system. For production use, ensure proper security auditing, real payment gateway integration, and compliance with local regulations.