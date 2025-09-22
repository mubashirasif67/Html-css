/**
 * Donation Form JavaScript
 * Handles form submission, receipt upload, and OCR processing
 */

// API Base URL
const API_BASE_URL = 'http://localhost:8000/api/v1';

// DOM Elements
const donationForm = document.getElementById('donationForm');
const receiptFile = document.getElementById('receiptFile');
const uploadArea = document.getElementById('uploadArea');
const receiptPreview = document.getElementById('receiptPreview');
const processingStatus = document.getElementById('processingStatus');
const submitBtn = document.getElementById('submitBtn');
const donationAmount = document.getElementById('donationAmount');

// Quick amount buttons
const quickAmountButtons = document.querySelectorAll('.quick-amount');

// Initialize form
document.addEventListener('DOMContentLoaded', function() {
    setupEventListeners();
    setupFormValidation();
});

/**
 * Set up event listeners
 */
function setupEventListeners() {
    // Form submission
    donationForm.addEventListener('submit', handleFormSubmit);
    
    // Receipt file upload
    receiptFile.addEventListener('change', handleReceiptUpload);
    
    // Quick amount buttons
    quickAmountButtons.forEach(button => {
        button.addEventListener('click', function() {
            const amount = this.dataset.amount;
            donationAmount.value = amount;
            
            // Update button states
            quickAmountButtons.forEach(btn => btn.classList.remove('active'));
            this.classList.add('active');
        });
    });
    
    // Drag and drop for receipt upload
    uploadArea.addEventListener('dragover', function(e) {
        e.preventDefault();
        this.classList.add('border-success');
    });
    
    uploadArea.addEventListener('dragleave', function(e) {
        e.preventDefault();
        this.classList.remove('border-success');
    });
    
    uploadArea.addEventListener('drop', function(e) {
        e.preventDefault();
        this.classList.remove('border-success');
        
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            receiptFile.files = files;
            handleReceiptUpload();
        }
    });
    
    // CNIC formatting
    const cnicInput = document.getElementById('donorCnic');
    cnicInput.addEventListener('input', function() {
        let value = this.value.replace(/\D/g, ''); // Remove non-digits
        
        // Format as XXXXX-XXXXXXX-X
        if (value.length > 5) {
            value = value.substring(0, 5) + '-' + value.substring(5);
        }
        if (value.length > 13) {
            value = value.substring(0, 13) + '-' + value.substring(13, 14);
        }
        
        this.value = value;
    });
    
    // Phone number formatting
    const phoneInput = document.getElementById('donorPhone');
    phoneInput.addEventListener('input', function() {
        let value = this.value.replace(/\D/g, ''); // Remove non-digits
        
        // Add +92 prefix if not present
        if (value.length > 0 && !value.startsWith('92')) {
            if (value.startsWith('0')) {
                value = '92' + value.substring(1);
            } else {
                value = '92' + value;
            }
        }
        
        // Format as +92 XXX XXXXXXX
        if (value.length > 2) {
            value = '+' + value.substring(0, 2) + ' ' + value.substring(2);
        }
        if (value.length > 7) {
            value = value.substring(0, 7) + ' ' + value.substring(7);
        }
        
        this.value = value;
    });
}

/**
 * Set up form validation
 */
function setupFormValidation() {
    // Custom validation messages
    const requiredFields = donationForm.querySelectorAll('[required]');
    
    requiredFields.forEach(field => {
        field.addEventListener('invalid', function() {
            if (this.validity.valueMissing) {
                this.setCustomValidity('This field is required');
            }
        });
        
        field.addEventListener('input', function() {
            this.setCustomValidity('');
        });
    });
}

/**
 * Handle form submission
 */
async function handleFormSubmit(e) {
    e.preventDefault();
    
    // Validate form
    if (!donationForm.checkValidity()) {
        donationForm.classList.add('was-validated');
        return;
    }
    
    // Check if amount is provided or receipt is uploaded
    const amount = donationAmount.value;
    const hasReceipt = receiptFile.files.length > 0;
    
    if (!amount && !hasReceipt) {
        showAlert('Please enter a donation amount or upload a receipt.', 'warning');
        return;
    }
    
    // Show processing status
    showProcessingStatus(true);
    
    try {
        let donationData = null;
        
        if (hasReceipt) {
            // Upload receipt first for OCR processing
            const ocrResult = await uploadReceiptForOCR();
            
            if (ocrResult.success) {
                // Create donation with OCR data
                donationData = await createDonationWithReceipt(ocrResult);
            } else {
                throw new Error('Receipt processing failed: ' + ocrResult.error);
            }
        } else {
            // Create donation with manual amount
            donationData = await createDonation();
        }
        
        if (donationData.success) {
            // Redirect to success page
            window.location.href = `success.html?donation_id=${donationData.donation.id}&receipt_number=${donationData.donation.receipt_number}`;
        } else {
            throw new Error(donationData.error || 'Failed to create donation');
        }
        
    } catch (error) {
        console.error('Form submission error:', error);
        showAlert('Failed to process donation: ' + error.message, 'danger');
    } finally {
        showProcessingStatus(false);
    }
}

/**
 * Handle receipt file upload
 */
async function handleReceiptUpload() {
    const file = receiptFile.files[0];
    
    if (!file) {
        hideReceiptPreview();
        return;
    }
    
    // Validate file type
    if (!file.type.startsWith('image/')) {
        showAlert('Please upload an image file (JPG, PNG, etc.)', 'warning');
        receiptFile.value = '';
        return;
    }
    
    // Validate file size (10MB limit)
    if (file.size > 10 * 1024 * 1024) {
        showAlert('File size too large. Please upload an image smaller than 10MB.', 'warning');
        receiptFile.value = '';
        return;
    }
    
    // Show preview
    showReceiptPreview(file);
    
    // Process with OCR (optional preview)
    try {
        const ocrResult = await processReceiptOCR(file);
        if (ocrResult.detected_amount) {
            showOCRResult(ocrResult);
            
            // Auto-fill amount if not manually entered
            if (!donationAmount.value) {
                donationAmount.value = ocrResult.detected_amount;
            }
        }
    } catch (error) {
        console.error('OCR processing error:', error);
        showOCRResult({ error: 'Failed to process receipt automatically' });
    }
}

/**
 * Show receipt preview
 */
function showReceiptPreview(file) {
    const reader = new FileReader();
    
    reader.onload = function(e) {
        document.getElementById('previewImage').src = e.target.result;
        document.getElementById('fileName').textContent = file.name;
        document.getElementById('fileSize').textContent = formatFileSize(file.size);
        receiptPreview.classList.remove('d-none');
    };
    
    reader.readAsDataURL(file);
}

/**
 * Hide receipt preview
 */
function hideReceiptPreview() {
    receiptPreview.classList.add('d-none');
    document.getElementById('ocrResult').innerHTML = '';
}

/**
 * Remove receipt
 */
function removeReceipt() {
    receiptFile.value = '';
    hideReceiptPreview();
    
    // Clear auto-filled amount if it came from OCR
    const amount = donationAmount.value;
    if (amount && !quickAmountButtons.some(btn => btn.classList.contains('active'))) {
        donationAmount.value = '';
    }
}

/**
 * Process receipt with OCR
 */
async function processReceiptOCR(file) {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await fetch(`${API_BASE_URL}/donations/upload_receipt`, {
        method: 'POST',
        body: formData
    });
    
    if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    
    return await response.json();
}

/**
 * Show OCR result
 */
function showOCRResult(result) {
    const ocrResultDiv = document.getElementById('ocrResult');
    
    if (result.detected_amount) {
        ocrResultDiv.innerHTML = `
            <div class="alert alert-success alert-sm mb-0">
                <i class="fas fa-check-circle me-1"></i>
                Detected Amount: PKR ${result.detected_amount.toLocaleString()}
                <small class="d-block mt-1">Confidence: ${(result.confidence * 100).toFixed(1)}%</small>
            </div>
        `;
    } else if (result.error) {
        ocrResultDiv.innerHTML = `
            <div class="alert alert-warning alert-sm mb-0">
                <i class="fas fa-exclamation-triangle me-1"></i>
                ${result.error}
            </div>
        `;
    } else {
        ocrResultDiv.innerHTML = `
            <div class="alert alert-info alert-sm mb-0">
                <i class="fas fa-info-circle me-1"></i>
                Processing receipt...
            </div>
        `;
    }
}

/**
 * Upload receipt for OCR processing
 */
async function uploadReceiptForOCR() {
    const formData = new FormData();
    formData.append('file', receiptFile.files[0]);
    formData.append('donor_name', document.getElementById('donorName').value);
    formData.append('donor_email', document.getElementById('donorEmail').value);
    
    const response = await fetch(`${API_BASE_URL}/donations/upload_receipt`, {
        method: 'POST',
        body: formData
    });
    
    const result = await response.json();
    
    return {
        success: response.ok,
        ...result
    };
}

/**
 * Create donation with receipt
 */
async function createDonationWithReceipt(ocrResult) {
    const formData = getFormData();
    
    // Use OCR detected amount if manual amount is not provided
    if (!formData.amount && ocrResult.suggested_amount) {
        formData.amount = ocrResult.suggested_amount;
    }
    
    const response = await fetch(`${API_BASE_URL}/donations`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(formData)
    });
    
    const result = await response.json();
    
    return {
        success: response.ok,
        ...result
    };
}

/**
 * Create donation
 */
async function createDonation() {
    const formData = getFormData();
    
    const response = await fetch(`${API_BASE_URL}/donations`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(formData)
    });
    
    const result = await response.json();
    
    return {
        success: response.ok,
        donation: result,
        error: result.error || result.detail
    };
}

/**
 * Get form data
 */
function getFormData() {
    return {
        donor_name: document.getElementById('donorName').value,
        donor_email: document.getElementById('donorEmail').value || null,
        donor_phone: document.getElementById('donorPhone').value || null,
        donor_cnic: document.getElementById('donorCnic').value || null,
        donor_address: document.getElementById('donorAddress').value || null,
        amount: parseFloat(document.getElementById('donationAmount').value) || null,
        currency: 'PKR',
        donation_type: document.getElementById('donationType').value,
        payment_method: document.getElementById('paymentMethod').value,
        campaign: document.getElementById('campaign').value || null,
        reference_number: document.getElementById('referenceNumber').value || null,
        notes: document.getElementById('notes').value || null
    };
}

/**
 * Show processing status
 */
function showProcessingStatus(show) {
    if (show) {
        processingStatus.classList.remove('d-none');
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Processing...';
    } else {
        processingStatus.classList.add('d-none');
        submitBtn.disabled = false;
        submitBtn.innerHTML = '<i class="fas fa-heart me-2"></i>Submit Donation';
    }
}

/**
 * Show alert message
 */
function showAlert(message, type = 'info') {
    // Remove existing alerts
    const existingAlerts = document.querySelectorAll('.alert-custom');
    existingAlerts.forEach(alert => alert.remove());
    
    // Create new alert
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show alert-custom`;
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    // Insert before form
    donationForm.parentNode.insertBefore(alertDiv, donationForm);
    
    // Auto-dismiss after 5 seconds
    setTimeout(() => {
        if (alertDiv.parentNode) {
            alertDiv.remove();
        }
    }, 5000);
}

/**
 * Format file size
 */
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}