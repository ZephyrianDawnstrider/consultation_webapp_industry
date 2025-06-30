import os
import time
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.conf import settings
from consultation.models import ConsultantProfile, Timesheet, Invoice

class Command(BaseCommand):
    help = 'Remove redundant files in media folders (agreements, timesheets, invoices) that are not stored in the database and older than 7 days.'

    def handle(self, *args, **kwargs):
        media_subdirs = {
            'agreements': ConsultantProfile.objects.exclude(agreement_document='').values_list('agreement_document', flat=True),
            'timesheets': Timesheet.objects.exclude(file='').values_list('file', flat=True),
            'invoices': Invoice.objects.exclude(file='').values_list('file', flat=True),
        }

        now = datetime.now()
        cutoff_time = now - timedelta(days=7)

        for subdir, db_files in media_subdirs.items():
            db_file_paths = set()
            for db_file in db_files:
                # db_file is a FileField path relative to media root
                db_file_paths.add(db_file)

            media_path = os.path.join(settings.MEDIA_ROOT, subdir)
            if not os.path.exists(media_path):
                self.stdout.write(f"Media subdirectory does not exist: {media_path}")
                continue

            for root, dirs, files in os.walk(media_path):
                for file in files:
                    if not (file.lower().endswith('.pdf') or file.lower().endswith('.csv')):
                        continue
                    file_path = os.path.relpath(os.path.join(root, file), settings.MEDIA_ROOT)
                    if file_path not in db_file_paths:
                        full_file_path = os.path.join(settings.MEDIA_ROOT, file_path)
                        try:
                            file_mtime = datetime.fromtimestamp(os.path.getmtime(full_file_path))
                            if file_mtime < cutoff_time:
                                os.remove(full_file_path)
                                self.stdout.write(f"Deleted redundant file: {full_file_path}")
                            else:
                                self.stdout.write(f"File {full_file_path} is redundant but not older than 7 days.")
                        except Exception as e:
                            self.stderr.write(f"Error processing file {full_file_path}: {e}")

        self.stdout.write("Cleanup of redundant files completed.")
