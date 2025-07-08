function submitEditInvoiceForm(invoiceId) {
    const form = document.getElementById(`edit-invoice-form-${invoiceId}`);
    if (!form) return;

    const formData = new FormData(form);

    fetch(form.action, {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie('csrftoken'),
            'Accept': 'application/json',
        },
        body: formData,
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert('Invoice updated successfully.');
            location.reload();
        } else {
            alert('Failed to update invoice: ' + data.message);
        }
    })
    .catch(error => {
        alert('Error updating invoice: ' + error);
    });
}

function deleteInvoice(invoiceId) {
    if (!confirm("Are you sure you want to delete this invoice? This action cannot be undone.")) {
        return;
    }

    fetch(`/consultation/invoice/delete/${invoiceId}/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie('csrftoken'),
            'Accept': 'application/json',
        },
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert('Invoice deleted successfully.');
            location.reload();
        } else {
            alert('Failed to delete invoice: ' + data.message);
        }
    })
    .catch(error => {
        alert('Error deleting invoice: ' + error);
    });
}

// Helper function to get CSRF token from cookies
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i=0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            // Does this cookie string begin with the name we want?
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}
