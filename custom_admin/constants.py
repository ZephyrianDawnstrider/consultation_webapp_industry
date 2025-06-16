# Centralized status choices for timesheet, invoice, and consultant statuses

TIMESHEET_STATUS_CHOICES = (
    ('approved', 'Approved'),
    ('pending', 'Pending'),
    ('rejected', 'Rejected'),
    ('awaiting_review', 'Awaiting Review'),
)

INVOICE_STATUS_CHOICES =(
    ('awaiting_review', 'Awaiting Review'),
    ('approved', 'Approved'),
    ('rejected', 'Rejected'),
    ('paid', 'Paid'),
    ('partially_paid', 'Partially Paid'),
    ('sent_to_banking', 'Sent to Banking'),
    ('sent_to_consultant', 'Sent to Consultant'),
)

CONSULTANT_STATUS_CHOICES = (
    ('approved', 'Approved'),
    ('rejected', 'Rejected'),
    ('to_be_reviewed', 'To Be Reviewed'),
)
