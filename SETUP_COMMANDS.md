# Blessings Donation System - Setup Commands

## Prerequisites
- Docker and Docker Compose installed
- Git installed
- At least 4GB RAM available
- Ports 80, 3000, 8000, 5555, 6379, 3306 available

## Quick Setup (5 commands)

```bash
# 1. Build all services
docker-compose build --no-cache

# 2. Start all services
docker-compose up -d

# 3. Wait for services to be ready (30 seconds)
sleep 30

# 4. Seed database with sample data
docker-compose exec backend python scripts/data_generator.py
docker-compose exec backend python scripts/seed_data.py
docker-compose exec backend python scripts/generate_synthetic_receipts.py

# 5. Train ML models
docker-compose exec backend python scripts/train_eligibility.py
docker-compose exec backend python scripts/train_fraud.py
```

## Verification Commands

### Check Service Status
```bash
# Check all containers are running
docker-compose ps

# Check logs
docker-compose logs backend
docker-compose logs worker
docker-compose logs admin

# Health check
curl http://localhost:8000/health
curl http://localhost:3000
curl http://localhost
```

### Test API Endpoints
```bash
# Test donation creation
curl -X POST "http://localhost:8000/api/v1/donations" \
  -H "Content-Type: application/json" \
  -d '{
    "donor_name": "Test Donor",
    "donor_email": "test@example.com",
    "amount": 1000.0,
    "donation_type": "general",
    "payment_method": "cash"
  }'

# Test OCR endpoint
curl -X POST "http://localhost:8000/api/v1/donations/upload_receipt" \
  -F "file=@data/synthetic_receipts/receipt_1000.png" \
  -F "donor_name=Test Donor"

# Test employee registration
curl -X POST "http://localhost:8000/api/v1/employees" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "employee_id": "EMP001",
    "name": "Test Employee",
    "cnic": "12345-1234567-1",
    "grade": 15,
    "designation": "Assistant"
  }'
```

### Test ML Models
```bash
# Test eligibility model
docker-compose exec backend python -c "
from app.ml.eligibility import eligibility_predictor
result = eligibility_predictor.predict_eligibility({
    'grade': 15,
    'family_size': 5,
    'income_estimate': 30000,
    'previous_aid_count': 1
})
print('Eligibility Result:', result)
"

# Test fraud detection model
docker-compose exec backend python -c "
from app.ml.fraud_detection import fraud_detector
result = fraud_detector.predict_fraud({
    'amount': 10000,
    'donor_age': 35,
    'submission_speed': 60
})
print('Fraud Detection Result:', result)
"
```

### Test OCR Pipeline
```bash
# Test OCR accuracy
docker-compose exec backend python -c "
from app.ocr.pipeline import OCRPipeline
pipeline = OCRPipeline()
metrics = pipeline.test_ocr_accuracy('data/synthetic_receipts')
print('OCR Accuracy:', metrics.get('accuracy_rate', 0))
"
```

## Access Points

After successful setup, access the system at:

- **Public Pages**: http://localhost
- **Admin Dashboard**: http://localhost:3000
- **API Documentation**: http://localhost:8000/docs
- **Celery Monitoring**: http://localhost:5555

## Default Credentials

Created during seeding:
- **Admin User**: admin@blessings.org / password: admin123
- **Staff User**: staff@blessings.org / password: staff123

## Sample Data Verification

```bash
# Check database records
docker-compose exec backend python -c "
from app.database import SessionLocal
from app.donations.models import Donation
from app.employees.models import Employee

db = SessionLocal()
print('Donations:', db.query(Donation).count())
print('Employees:', db.query(Employee).count())
db.close()
"

# Check synthetic receipts
ls -la data/synthetic_receipts/

# Check ML models
ls -la backend/app/ml/models/
```

## Performance Validation

```bash
# Test concurrent donations (requires apache-bench)
ab -n 100 -c 10 -T 'application/json' \
  -p donation_payload.json \
  http://localhost:8000/api/v1/donations

# Monitor resource usage
docker stats

# Check response times
curl -w "@curl-format.txt" -s -o /dev/null \
  http://localhost:8000/api/v1/donations
```

## Troubleshooting Commands

```bash
# Restart services
docker-compose restart

# View detailed logs
docker-compose logs -f backend
docker-compose logs -f worker

# Reset database
docker-compose exec backend alembic downgrade base
docker-compose exec backend alembic upgrade head

# Rebuild and restart
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

## Cleanup Commands

```bash
# Stop all services
docker-compose down

# Remove all data (WARNING: This deletes everything)
docker-compose down -v
docker system prune -f
docker volume prune -f
```

## Production Deployment

```bash
# Set production environment
cp .env.example .env.production
# Edit .env.production with production settings

# Build production images
docker-compose -f docker-compose.yml -f docker-compose.prod.yml build

# Deploy to production
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Setup SSL (example with Let's Encrypt)
docker run -it --rm -v /etc/letsencrypt:/etc/letsencrypt \
  certbot/certbot certonly --standalone -d yourdomain.com
```

## Acceptance Criteria Validation

### ✅ Criterion 1: Docker Compose starts all services
```bash
docker-compose up --build
# Should start: backend, db, redis, worker, admin, nginx, flower
```

### ✅ Criterion 2: Database seeded with sample data
```bash
make seed
# Should create: 200 employees, 500 donations, 100 synthetic receipts
```

### ✅ Criterion 3: OCR accuracy >85%
```bash
docker-compose exec backend python scripts/test_ocr_accuracy.py
# Expected: >85% accuracy on synthetic receipts
```

### ✅ Criterion 4: Admin can generate and approve distribution
```bash
# Login to admin dashboard at http://localhost:3000
# Navigate to Distribution -> Generate
# Should create distribution list and allow approval
```

### ✅ Criterion 5: Tests pass with >70% coverage
```bash
make test
make coverage
# Expected: All tests pass, coverage >70%
```

## System Health Check

```bash
#!/bin/bash
echo "=== Blessings Donation System Health Check ==="

# Check containers
echo "Checking containers..."
docker-compose ps

# Check API health
echo "Checking API health..."
curl -f http://localhost:8000/health || echo "API health check failed"

# Check database connection
echo "Checking database..."
docker-compose exec -T backend python -c "
from app.database import check_database_connection
print('Database OK' if check_database_connection() else 'Database FAILED')
"

# Check ML models
echo "Checking ML models..."
docker-compose exec -T backend python -c "
from app.ml.eligibility import eligibility_predictor
from app.ml.fraud_detection import fraud_detector
print('Eligibility Model:', 'OK' if eligibility_predictor.is_model_loaded() else 'FAILED')
print('Fraud Model:', 'OK' if fraud_detector.is_model_loaded() else 'FAILED')
"

# Check OCR
echo "Checking OCR..."
docker-compose exec -T backend python -c "
import pytesseract
try:
    version = pytesseract.get_tesseract_version()
    print('OCR OK - Tesseract', version)
except:
    print('OCR FAILED')
"

echo "=== Health Check Complete ==="
```

Save this as `health_check.sh`, make it executable, and run:
```bash
chmod +x health_check.sh
./health_check.sh
```