// Custom JavaScript for Customer Management System

// Initialize Socket.IO
const socket = io();

// Socket.IO event handlers
socket.on('connect', () => {
    console.log('Connected to server');
});

socket.on('connection_response', (data) => {
    console.log('Connection response:', data);
});

socket.on('customer_added', (customer) => {
    console.log('New customer added:', customer);
    updateCustomersTable(customer);
    showNotification('New customer added: ' + customer.name, 'success');
});

socket.on('customer_updated', (customer) => {
    console.log('Customer updated:', customer);
    updateCustomersTable(customer);
});

socket.on('transaction_added', (transaction) => {
    console.log('New transaction added:', transaction);
    updateTransactionsTable(transaction);
    showNotification('New transaction added', 'success');
});

socket.on('customers_data', (data) => {
    console.log('Received customers data:', data);
    updateCustomersTable(data.customers);
});

socket.on('transactions_data', (data) => {
    console.log('Received transactions data:', data);
    updateTransactionsTable(data.transactions);
});

// Update customers table with new data
function updateCustomersTable(customers) {
    const table = $('#customersTable').DataTable();
    if (Array.isArray(customers)) {
        table.clear();
        customers.forEach(customer => {
            table.row.add([
                customer.name,
                customer.email,
                customer.phone,
                customer.gstin || '-',
                formatCurrency(customer.credit_limit),
                formatCurrency(customer.outstanding_balance),
                createActionButtons(customer.id)
            ]);
        });
    } else {
        // Single customer update
        const row = table.row((idx, data) => data[0] === customers.name);
        if (row.length) {
            row.data([
                customers.name,
                customers.email,
                customers.phone,
                customers.gstin || '-',
                formatCurrency(customers.credit_limit),
                formatCurrency(customers.outstanding_balance),
                createActionButtons(customers.id)
            ]);
        }
    }
    table.draw();
}

// Update transactions table with new data
function updateTransactionsTable(transactions) {
    const table = $('#transactionsTable').DataTable();
    if (Array.isArray(transactions)) {
        table.clear();
        transactions.forEach(transaction => {
            table.row.add([
                transaction.date,
                transaction.type === 'credit' ? 
                    '<span class="badge bg-danger">Credit</span>' : 
                    '<span class="badge bg-success">Payment</span>',
                formatCurrency(transaction.amount),
                transaction.description
            ]);
        });
    } else {
        // Single transaction update
        table.row.add([
            transaction.date,
            transaction.type === 'credit' ? 
                '<span class="badge bg-danger">Credit</span>' : 
                '<span class="badge bg-success">Payment</span>',
            formatCurrency(transaction.amount),
            transaction.description
        ]);
    }
    table.draw();
}

// Create action buttons for customer table
function createActionButtons(customerId) {
    return `
        <a href="/view_customer/${customerId}" class="btn btn-info btn-sm">
            <i class="fas fa-eye"></i>
        </a>
        <a href="/edit_customer/${customerId}" class="btn btn-warning btn-sm">
            <i class="fas fa-edit"></i>
        </a>
    `;
}

// Initialize DataTables with common options
function initDataTable(tableId, options = {}) {
    const defaultOptions = {
        responsive: true,
        language: {
            search: "_INPUT_",
            searchPlaceholder: "Search...",
            lengthMenu: "Show _MENU_ entries",
            info: "Showing _START_ to _END_ of _TOTAL_ entries",
            infoEmpty: "No entries found",
            infoFiltered: "(filtered from _MAX_ total entries)",
            zeroRecords: "No matching records found",
            paginate: {
                first: "First",
                last: "Last",
                next: "Next",
                previous: "Previous"
            }
        },
        dom: '<"row"<"col-sm-12 col-md-6"l><"col-sm-12 col-md-6"f>>' +
             '<"row"<"col-sm-12"tr>>' +
             '<"row"<"col-sm-12 col-md-5"i><"col-sm-12 col-md-7"p>>',
        buttons: ['copy', 'csv', 'excel', 'pdf', 'print']
    };

    return $(tableId).DataTable({ ...defaultOptions, ...options });
}

// Format currency values
function formatCurrency(amount) {
    return new Intl.NumberFormat('en-IN', {
        style: 'currency',
        currency: 'INR',
        minimumFractionDigits: 2
    }).format(amount);
}

// Format date values
function formatDate(date) {
    return new Intl.DateTimeFormat('en-IN', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    }).format(new Date(date));
}

// Validate form inputs
function validateForm(formId) {
    const form = document.getElementById(formId);
    if (!form) return true;

    let isValid = true;
    const inputs = form.querySelectorAll('input[required], select[required], textarea[required]');

    inputs.forEach(input => {
        if (!input.value.trim()) {
            isValid = false;
            input.classList.add('is-invalid');
        } else {
            input.classList.remove('is-invalid');
        }
    });

    return isValid;
}

// Show confirmation dialog
function confirmAction(message) {
    return confirm(message || 'Are you sure you want to proceed?');
}

// Show notification
function showNotification(message, type = 'success') {
    const alert = `
        <div class="alert alert-${type} alert-dismissible fade show" role="alert">
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;
    
    const container = document.querySelector('.content');
    if (container) {
        container.insertAdjacentHTML('afterbegin', alert);
        
        // Auto-dismiss after 5 seconds
        setTimeout(() => {
            const alertElement = container.querySelector('.alert');
            if (alertElement) {
                const bsAlert = new bootstrap.Alert(alertElement);
                bsAlert.close();
            }
        }, 5000);
    }
}

// Handle form submission with AJAX
function handleFormSubmit(formId, successCallback) {
    const form = document.getElementById(formId);
    if (!form) return;

    form.addEventListener('submit', function(e) {
        e.preventDefault();

        if (!validateForm(formId)) {
            showNotification('Please fill in all required fields.', 'danger');
            return;
        }

        const formData = new FormData(form);
        const submitButton = form.querySelector('button[type="submit"]');
        const originalText = submitButton.innerHTML;

        // Disable submit button and show loading state
        submitButton.disabled = true;
        submitButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Processing...';

        fetch(form.action, {
            method: form.method,
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showNotification(data.message || 'Operation completed successfully.');
                if (typeof successCallback === 'function') {
                    successCallback(data);
                }
            } else {
                showNotification(data.message || 'An error occurred.', 'danger');
            }
        })
        .catch(error => {
            showNotification('An error occurred while processing your request.', 'danger');
            console.error('Error:', error);
        })
        .finally(() => {
            // Re-enable submit button and restore original text
            submitButton.disabled = false;
            submitButton.innerHTML = originalText;
        });
    });
}

// Initialize tooltips
function initTooltips() {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

// Initialize popovers
function initPopovers() {
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
}

// Document ready handler
document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips and popovers
    initTooltips();
    initPopovers();

    // Initialize DataTables
    const tables = document.querySelectorAll('.datatable');
    tables.forEach(table => {
        initDataTable('#' + table.id);
    });

    // Add fade-in animation to cards
    const cards = document.querySelectorAll('.card');
    cards.forEach(card => {
        card.classList.add('fade-in');
    });

    // Handle form validation
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            if (!validateForm(form.id)) {
                e.preventDefault();
                showNotification('Please fill in all required fields.', 'danger');
            }
        });
    });

    // Auto-dismiss alerts
    const alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
    alerts.forEach(alert => {
        setTimeout(() => {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });

    // Request initial data
    socket.emit('get_customers');
    if (window.location.pathname.includes('view_customer')) {
        const customerId = window.location.pathname.split('/').pop();
        socket.emit('get_transactions', { customer_id: customerId });
    }
}); 