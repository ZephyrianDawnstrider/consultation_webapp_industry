from django.core.management.base import BaseCommand
from custom_admin.models import Invoice
import os

class Command(BaseCommand):
    help = 'Find and fix or remove invoice records with missing file references'

    def add_arguments(self, parser):
        parser.add_argument(
            '--delete-missing',
            action='store_true',
            help='Delete invoice records with missing files',
        )

    def handle(self, *args, **options):
        delete_missing = options['delete_missing']
        missing_files = []
        invoices = Invoice.objects.all()
        media_root = os.path.abspath('media')  # Adjust if needed

        for invoice in invoices:
            if invoice.file:
                file_path = os.path.join(media_root, invoice.file.name)
                if not os.path.exists(file_path):
                    missing_files.append((invoice.id, invoice.file.name))
                    self.stdout.write(f"Missing file for Invoice ID {invoice.id}: {invoice.file.name}")
                    if delete_missing:
                        invoice.delete()
                        self.stdout.write(f"Deleted Invoice ID {invoice.id} due to missing file.")
        
        if not missing_files:
            self.stdout.write("No missing invoice files found.")
        else:
            self.stdout.write(f"Total missing invoice files: {len(missing_files)}")
            if not delete_missing:
                self.stdout.write("Please review and take necessary action.")
            else:
                self.stdout.write("Deleted all invoice records with missing files.")
