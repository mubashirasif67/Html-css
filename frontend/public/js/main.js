// Main JavaScript for Blessings Foundation Frontend

// API Base URL
const API_URL = 'http://localhost:8000/api';

// Utility Functions
function showLoading(element) {
    element.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Loading...';
}

function showError(message) {
    const alertDiv = document.createElement('div');
    alertDiv.className = 'alert alert-danger alert-dismissible fade show';
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    document.body.insertBefore(alertDiv, document.body.firstChild);
}

function showSuccess(message) {
    const alertDiv = document.createElement('div');
    alertDiv.className = 'alert alert-success alert-dismissible fade show';
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    document.body.insertBefore(alertDiv, document.body.firstChild);
}

// Format currency
function formatCurrency(amount) {
    return new Intl.NumberFormat('en-PK', {
        style: 'currency',
        currency: 'PKR',
        minimumFractionDigits: 0
    }).format(amount);
}

// Validate CNIC format
function validateCNIC(cnic) {
    const pattern = /^\d{5}-\d{7}-\d$/;
    return pattern.test(cnic);
}

// Format CNIC input
function formatCNICInput(input) {
    let value = input.value.replace(/[^\d]/g, '');
    
    if (value.length >= 5) {
        value = value.slice(0, 5) + '-' + value.slice(5);
    }
    if (value.length >= 13) {
        value = value.slice(0, 13) + '-' + value.slice(13);
    }
    
    input.value = value.slice(0, 15); // 13 digits + 2 hyphens
}

// Auto-format CNIC fields
document.addEventListener('DOMContentLoaded', function() {
    const cnicInputs = document.querySelectorAll('input[name="cnic"], input[name="donor_cnic"]');
    cnicInputs.forEach(input => {
        input.addEventListener('input', function() {
            formatCNICInput(this);
        });
    });
});

// Handle form validation
function validateForm(form) {
    const requiredFields = form.querySelectorAll('[required]');
    let isValid = true;
    
    requiredFields.forEach(field => {
        if (!field.value) {
            field.classList.add('is-invalid');
            isValid = false;
        } else {
            field.classList.remove('is-invalid');
        }
    });
    
    return isValid;
}

// API Calls
async function apiCall(endpoint, options = {}) {
    try {
        const response = await fetch(`${API_URL}${endpoint}`, {
            ...options,
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            }
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'API request failed');
        }
        
        return await response.json();
    } catch (error) {
        console.error('API Error:', error);
        throw error;
    }
}

// Load donation statistics for homepage
async function loadDonationStats() {
    const statsContainer = document.getElementById('donationStats');
    if (!statsContainer) return;
    
    try {
        showLoading(statsContainer);
        
        // In production, this would be a real API call
        // For now, using placeholder data
        statsContainer.innerHTML = `
            <div class="row text-center">
                <div class="col-md-3">
                    <h3>5,000+</h3>
                    <p>Families Supported</p>
                </div>
                <div class="col-md-3">
                    <h3>PKR 10M+</h3>
                    <p>Total Donations</p>
                </div>
                <div class="col-md-3">
                    <h3>500+</h3>
                    <p>Active Donors</p>
                </div>
                <div class="col-md-3">
                    <h3>98%</h3>
                    <p>Satisfaction Rate</p>
                </div>
            </div>
        `;
    } catch (error) {
        statsContainer.innerHTML = '<p class="text-danger">Failed to load statistics</p>';
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    // Load stats if on homepage
    loadDonationStats();
    
    // Add smooth scrolling
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({ behavior: 'smooth' });
            }
        });
    });
    
    // Add form validation
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            if (!validateForm(this)) {
                e.preventDefault();
                e.stopPropagation();
            }
        });
    });
});

// Export functions for use in other scripts
window.blessingsUtils = {
    showLoading,
    showError,
    showSuccess,
    formatCurrency,
    validateCNIC,
    apiCall
};