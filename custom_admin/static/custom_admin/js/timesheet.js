document.addEventListener('DOMContentLoaded', () => {
  const timesheetEntriesElement = document.getElementById('timesheet-entries');
  if (timesheetEntriesElement) {
    let timesheetEntries = [];
    try {
      timesheetEntries = JSON.parse(timesheetEntriesElement.textContent);
    } catch (e) {
      console.error('Failed to parse timesheet entries JSON:', e);
    }
    const tbody = document.getElementById('timesheet-entries-body');

    function createRow(entry = {}) {
      const tr = document.createElement('tr');

      // Date
      const dateTd = document.createElement('td');
      const dateInput = document.createElement('input');
      dateInput.type = 'date';
      dateInput.className = 'w-full border border-gray-300 rounded px-2 py-1 text-black';
      dateInput.value = entry.date || '';
      dateTd.appendChild(dateInput);
      tr.appendChild(dateTd);

      // Start Time
      const startTd = document.createElement('td');
      const startInput = document.createElement('input');
      startInput.type = 'time';
      startInput.className = 'w-full border border-gray-300 rounded px-2 py-1 text-black';
      startInput.value = entry.start_time || '';
      startTd.appendChild(startInput);
      tr.appendChild(startTd);

      // End Time
      const endTd = document.createElement('td');
      const endInput = document.createElement('input');
      endInput.type = 'time';
      endInput.className = 'w-full border border-gray-300 rounded px-2 py-1 text-black';
      endInput.value = entry.end_time || '';
      endTd.appendChild(endInput);
      tr.appendChild(endTd);

      // Project Name
      const projectTd = document.createElement('td');
      const projectInput = document.createElement('input');
      projectInput.type = 'text';
      projectInput.className = 'w-full border border-gray-300 rounded px-2 py-1 text-black';
      projectInput.value = entry.project_name || '';
      projectTd.appendChild(projectInput);
      tr.appendChild(projectTd);

      // Task Name
      const taskTd = document.createElement('td');
      const taskInput = document.createElement('input');
      taskInput.type = 'text';
      taskInput.className = 'w-full border border-gray-300 rounded px-2 py-1 text-black';
      taskInput.value = entry.task_name || '';
      taskTd.appendChild(taskInput);
      tr.appendChild(taskTd);

      // Actions
      const actionsTd = document.createElement('td');
      actionsTd.className = 'text-center';
      const delBtn = document.createElement('button');
      delBtn.type = 'button';
      delBtn.textContent = 'Delete';
      delBtn.className = 'bg-red-600 text-white px-2 py-1 rounded hover:bg-red-700';
      delBtn.addEventListener('click', () => {
        if (confirm('Are you sure you want to delete this row?')) {
          tr.remove();
        }
      });
      actionsTd.appendChild(delBtn);
      tr.appendChild(actionsTd);

      return tr;
    }

    function loadEntries() {
      tbody.innerHTML = '';
      if (timesheetEntries.length === 0) {
        // Add a default empty row if no data present
        const defaultRow = createRow();
        tbody.appendChild(defaultRow);
      } else {
        timesheetEntries.forEach(entry => {
          const row = createRow(entry);
          tbody.appendChild(row);
        });
      }
    }

    loadEntries();

    const addRowBtn = document.getElementById('add-row-button');
    const saveBtn = document.getElementById('save-entries-button');
    const saveFeedback = document.getElementById('save-feedback');
    const saveLoading = document.getElementById('save-loading');

    addRowBtn.addEventListener('click', () => {
      const newRow = createRow();
      tbody.appendChild(newRow);
    });

    saveBtn.addEventListener('click', async () => {
      saveFeedback.textContent = '';
      saveLoading.classList.remove('hidden');

      // Clear previous error highlights
      const rows = Array.from(tbody.querySelectorAll('tr'));
      rows.forEach(row => {
        row.style.border = '';
      });

      const entries = rows.map(row => {
        const inputs = row.querySelectorAll('input');
        return {
          date: inputs[0].value,
          start_time: inputs[1].value,
          end_time: inputs[2].value,
          project_name: inputs[4].value,
          task_name: inputs[3].value
        };
      });

      // Client-side validation
      for (let i = 0; i < entries.length; i++) {
        const error = validateEntry(entries[i]);
        if (error) {
          saveLoading.classList.add('hidden');
          saveFeedback.textContent = `Error in row ${i + 1}: ${error}`;
          saveFeedback.className = 'text-red-600 mt-2';

          // Highlight the error row
          rows[i].style.border = '2px solid red';

          // Scroll to the error row
          rows[i].scrollIntoView({ behavior: 'smooth', block: 'center' });

          return;
        }
      }

      try {
        const response = await fetch('/auth/save_timesheet_entries/', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
          },
          body: JSON.stringify({
            timesheet_id: saveBtn.getAttribute('data-timesheet-id'),
            entries: entries
          })
        });
        const data = await response.json();
        saveLoading.classList.add('hidden');
        if (data.success) {
          saveFeedback.textContent = 'Timesheet entries saved successfully.';
          saveFeedback.className = 'text-green-600 mt-2';
        } else {
          saveFeedback.textContent = 'Error saving timesheet entries: ' + (data.message || 'Unknown error.');
          saveFeedback.className = 'text-red-600 mt-2';
        }
      } catch (error) {
        saveLoading.classList.add('hidden');
        saveFeedback.textContent = 'Network error. Please try again.';
        saveFeedback.className = 'text-red-600 mt-2';
      }
    });

    function validateEntry(entry) {
      if (!entry.date) {
        return 'Date is required.';
      }
      if (!entry.start_time) {
        return 'Start Time is required.';
      }
      if (!entry.end_time) {
        return 'End Time is required.';
      }
      if (entry.start_time >= entry.end_time) {
        return 'Start Time must be before End Time.';
      }
      if (!entry.task_name || entry.task_name.trim() === '') {
        return 'Task Name is required.';
      }
      return null;
    }

    // CSRF helper
    function getCookie(name) {
      let cookieValue = null;
      if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
          const cookie = cookies[i].trim();
          if (cookie.substring(0, name.length + 1) === (name + '=')) {
            cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
            break;
          }
        }
      }
      return cookieValue;
    }
  };
});

