// Donation form JavaScript

document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('donationForm');
    const imageInput = document.getElementById('receiptImage');
    const imagePreview = document.getElementById('imagePreview');
    const previewImg = document.getElementById('previewImg');

    // Image preview functionality
    imageInput.addEventListener('change', function(e) {
        const file = e.target.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onload = function(e) {
                previewImg.src = e.target.result;
                imagePreview.classList.remove('d-none');
            };
            reader.readAsDataURL(file);
        } else {
            imagePreview.classList.add('d-none');
        }
    });

    // Form submission
    form.addEventListener('submit', async function(e) {
        e.preventDefault();

        // Get form data
        const formData = new FormData();
        formData.append('donor_name', document.getElementById('donorName').value);
        formData.append('donor_email', document.getElementById('donorEmail').value);
        formData.append('donor_cnic', document.getElementById('donorCnic').value);
        formData.append('amount', document.getElementById('amount').value);
        formData.append('donation_type', document.getElementById('donationType').value);

        const receiptFile = document.getElementById('receiptImage').files[0];
        if (receiptFile) {
            formData.append('receipt_image', receiptFile);
        }

        // Show loading state
        const submitBtn = form.querySelector('button[type="submit"]');
        const originalText = submitBtn.textContent;
        submitBtn.textContent = 'Processing...';
        submitBtn.disabled = true;

        try {
            // Submit donation
            const response = await fetch('http://localhost:8000/api/donations/', {
                method: 'POST',
                body: formData,
                headers: {
                    // Don't set Content-Type for FormData - browser sets it automatically
                }
            });

            if (response.ok) {
                const result = await response.json();

                // Redirect to success page with details
                const successUrl = `donation_success.html?name=${encodeURIComponent(result.donor_name)}&amount=${result.amount}&type=${result.donation_type}&id=${result.id}`;
                window.location.href = successUrl;
            } else {
                const error = await response.json();
                alert('Error submitting donation: ' + (error.detail || 'Unknown error'));
            }
        } catch (error) {
            console.error('Error:', error);
            alert('Network error. Please try again.');
        } finally {
            // Restore button state
            submitBtn.textContent = originalText;
            submitBtn.disabled = false;
        }
    });

    // CNIC formatting
    const cnicInput = document.getElementById('donorCnic');
    cnicInput.addEventListener('input', function(e) {
        let value = e.target.value.replace(/\D/g, '');
        if (value.length > 13) value = value.slice(0, 13);

        let formatted = '';
        if (value.length > 0) formatted += value.slice(0, 5);
        if (value.length > 5) formatted += '-' + value.slice(5, 12);
        if (value.length > 12) formatted += '-' + value.slice(12, 13);

        e.target.value = formatted;
    });
});