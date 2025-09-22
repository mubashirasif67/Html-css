// Employee registration JavaScript

document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('employeeForm');

    // Form submission
    form.addEventListener('submit', async function(e) {
        e.preventDefault();

        // Get form data
        const employeeData = {
            name: document.getElementById('name').value,
            father_name: document.getElementById('fatherName').value,
            cnic: document.getElementById('cnic').value,
            grade: document.getElementById('grade').value,
            designation: document.getElementById('designation').value,
            mobile: document.getElementById('mobile').value,
            family_size: document.getElementById('familySize').value,
            address: document.getElementById('address').value
        };

        // Show loading state
        const submitBtn = form.querySelector('button[type="submit"]');
        const originalText = submitBtn.textContent;
        submitBtn.textContent = 'Registering...';
        submitBtn.disabled = true;

        try {
            // Submit employee registration
            const response = await fetch('http://localhost:8000/api/employees/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(employeeData)
            });

            if (response.ok) {
                alert('Employee registered successfully!');
                form.reset();
            } else {
                const error = await response.json();
                alert('Error registering employee: ' + (error.detail || 'Unknown error'));
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
    const cnicInput = document.getElementById('cnic');
    cnicInput.addEventListener('input', function(e) {
        let value = e.target.value.replace(/\D/g, '');
        if (value.length > 13) value = value.slice(0, 13);

        let formatted = '';
        if (value.length > 0) formatted += value.slice(0, 5);
        if (value.length > 5) formatted += '-' + value.slice(5, 12);
        if (value.length > 12) formatted += '-' + value.slice(12, 13);

        e.target.value = formatted;
    });

    // Mobile number formatting
    const mobileInput = document.getElementById('mobile');
    mobileInput.addEventListener('input', function(e) {
        let value = e.target.value.replace(/\D/g, '');
        if (value.length > 11) value = value.slice(0, 11);
        e.target.value = value;
    });
});