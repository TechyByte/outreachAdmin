document.addEventListener('DOMContentLoaded', () => {
    // Helper to collect filter params from all sources
    function collectFilterParams() {
        const params = new URLSearchParams();

        // Collect select fields from main filter form
        document.querySelectorAll('#filters-form select').forEach(select => {
            Array.from(select.selectedOptions).forEach(option => {
                params.append(select.name, option.value);
            });
        });

        // Collect selected schools from hidden input (set by modal)
        const schoolsInput = document.getElementById('selected_schools_input');
        if (schoolsInput && schoolsInput.value) {
            schoolsInput.value.split(',').forEach(id => {
                if (id) params.append('school', id);
            });
        }

        // Collect selected lecturer from hidden input (set by modal)
        const lecturerInput = document.getElementById('selected_lecturers_input');
        if (lecturerInput && lecturerInput.value) {
            params.append('lecturer', lecturerInput.value);
        }

        return params;
    }

    // Calendar view
    const calendarEl = document.getElementById('calendar');
    let calendar;
    if (calendarEl) {
        calendar = new FullCalendar.Calendar(calendarEl, {
            initialView: 'dayGridMonth',
            events: function(fetchInfo, successCallback, failureCallback) {
                fetchEvents(successCallback, failureCallback);
            },
            headerToolbar: {
                left: 'prev,next today',
                center: 'title',
                right: 'dayGridMonth,timeGridWeek,timeGridDay'
            },
            eventClick: function(info) {
                alert(`Event: ${info.event.title}`);
            }
        });
        calendar.render();
    }

    // Table view
    const tableBody = document.querySelector('#schedule-table tbody');

    // Unified filter handler
    function handleFilterSubmit(e) {
        if (e) e.preventDefault();
        fetchEvents((events) => {
            if (calendar) {
                calendar.removeAllEvents();
                calendar.addEventSource(events);
            }
            if (tableBody) {
                populateTable(events);
            }
        }, (error) => {
            console.error('Error fetching events:', error);
        });
    }

    // Attach handler to main filter form
    const filtersForm = document.getElementById('filters-form');
    if (filtersForm) {
        filtersForm.addEventListener('submit', handleFilterSubmit);
    }

    // Attach handler to "Apply Filters" button (for program, course, location)
    const applyFiltersBtn = document.querySelector('button[form="filters-form"]');
    if (applyFiltersBtn) {
        applyFiltersBtn.addEventListener('click', function(e) {
            e.preventDefault();
            handleFilterSubmit();
        });
    }

    // School modal triggers filtering independently
    const applySchoolBtn = document.getElementById('apply-school-filter');
    if (applySchoolBtn) {
        applySchoolBtn.addEventListener('click', () => {
            setTimeout(() => {
                handleFilterSubmit();
            }, 300);
        });
    }

    // Lecturer modal triggers filtering independently (if you have a button for this, use its ID)
    // Example: <button id="apply-lecturer-filter" ...>
    const applyLecturerBtn = document.getElementById('apply-lecturer-filter');
    if (applyLecturerBtn) {
        applyLecturerBtn.addEventListener('click', () => {
            setTimeout(() => {
                handleFilterSubmit();
            }, 300);
        });
    }

    // Fetch events and populate both calendar and table
    function fetchEvents(successCallback, failureCallback) {
        const params = collectFilterParams();
        fetch(`/schedule/events?${params.toString()}`)
            .then(response => response.json())
            .then(data => {
                successCallback(data);
            })
            .catch(error => failureCallback(error));
    }

    // Populate the table with event data
    function populateTable(events = []) {
        if (!tableBody) return;
        tableBody.innerHTML = '';

        // Group agenda items by event using eventId
        const eventMap = {};
        events.forEach(event => {
            if (event.id && event.id.startsWith('event-')) {
                eventMap[event.id] = {
                    event: event,
                    agenda_items: []
                };
            }
        });
        // Attach agenda items to their parent event using eventId
        events.forEach(item => {
            if (item.id && item.id.startsWith('agenda-') && item.eventId && eventMap[item.eventId]) {
                eventMap[item.eventId].agenda_items.push(item);
            }
        });

        // Render each event row with nested agenda items
        Object.values(eventMap).forEach(({ event, agenda_items }) => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td><a href="${event.url}">${event.title}</a></td>
                <td>${event.school || 'unknown'}</td>
                <td>${event.course || 'unknown'}</td>
                <td>${event.program || 'unknown'}</td>
                <td style="color: ${event.color}">${event.status || 'unknown'}</td>
                <td>${event.start ? new Date(event.start).toLocaleDateString() : 'N/A'}</td>
                <td>${event.start && event.end ? `${new Date(event.start).toLocaleTimeString()} - ${new Date(event.end).toLocaleTimeString()}` : 'N/A'}</td>
                <td>${event.location || 'unknown'}</td>
                <td>
                    <table class="table">
                        <thead>
                            <tr>
                                <th>Time</th>
                                <th>Title</th>
                                <th>Lecturer</th>
                                <th>Duration</th>
                                <th>Status</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${agenda_items.map(item => `
                                <tr>
                                    <td>${item.start ? new Date(item.start).toLocaleTimeString() : 'N/A'}</td>
                                    <td><a href="${item.url}">${item.title}</a></td>
                                    <td>${item.lecturer || 'unknown'}</td>
                                    <td>${item.duration || 'N/A'}</td>
                                    <td style="color: ${item.color}">${item.status || 'N/A'}</td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </td>
            `;
            tableBody.appendChild(row);
        });
    }
});
