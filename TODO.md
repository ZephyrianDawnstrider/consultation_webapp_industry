# TODO: Fix CSV Update Issue

## Tasks
- [x] Edit `save_timesheet_entries` function in `consultant/views.py` to overwrite existing CSV file instead of creating new one with timestamp.
- [x] Fixed file path inconsistency: Use existing file path for editing instead of generating new filename.
- [x] Changed `os.path.join` to f-string for consistent forward slashes.

## Details
- Added data-timesheet-id attribute to the save button in the template to pass the selected timesheet ID.
- Modified the save function to delete the existing file first and save with the same filename.
- Updated the JS to send the timesheet_id from the button attribute instead of hardcoded null.
- Fixed file path inconsistency: Changed `os.path.join('timesheets', file_name)` to `f"timesheets/{file_name}"` to use forward slashes consistently, preventing different paths on Windows vs. other systems.
- This ensures updates are made to the existing timesheet record and file is overwritten.

## Followup
- Test the timesheet update functionality to confirm it overwrites the existing CSV file.
- Verify that the file path and content remain consistent.
