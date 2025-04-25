document.addEventListener('DOMContentLoaded', () => {
    // Initialize FullCalendar
    const calendarEl = document.getElementById('calendar');
    const calendar = new FullCalendar.Calendar(calendarEl, {
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

    // Re-render calendar and table when filters are applied
    document.getElementById('apply-school-filter').addEventListener('click', (e) => {
        e.preventDefault();
        fetchEvents((events) => {
            calendar.removeAllEvents();
            calendar.addEventSource(events);
            populateTable(events);
        }, (error) => {
            console.error('Error fetching events:', error);
        });
    });

    // Re-render calendar and table when filters are applied
    document.getElementById('filters-form').addEventListener('submit', (e) => {
        e.preventDefault();
        fetchEvents((events) => {
            calendar.removeAllEvents();
            calendar.addEventSource(events);
            populateTable(events);
        }, (error) => {
            console.error('Error fetching events:', error);
        });
    });

    // Fetch events and populate both calendar and table
    function fetchEvents(successCallback, failureCallback) {
        const params = new URLSearchParams();
        document.querySelectorAll('#filters-form select').forEach(select => {
            Array.from(select.selectedOptions).forEach(option => {
                params.append(select.name, option.value);
            });
        });

        document.querySelectorAll('input[name="selected_schools"]:checked').forEach(input => {
            params.append('school', input.value);
        });

        fetch(`/schedule/events?${params.toString()}`)
            .then(response => response.json())
            .then(data => {
                successCallback(data);
                populateTable(data);
            })
            .catch(error => failureCallback(error));
    }

    // Populate the table with event data
    function populateTable(events = []) {
        const tableBody = document.querySelector('#schedule-table tbody');
        tableBody.innerHTML = ''; // Clear existing rows

        events.forEach(event => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td><a href="#">${event.title}</a></td>
                <td>${event.school || 'unknown'}</td>
                <td>${event.course || 'unknown'}</td>
                <td>${event.program || 'unknown'}</td>
                <td>${event.status || 'unknown'}</td>
                <td>${event.start ? new Date(event.start).toLocaleDateString() : 'N/A'}</td>
                <td>${event.start && event.end ? `${new Date(event.start).toLocaleTimeString()} - ${new Date(event.end).toLocaleTimeString()}` : 'N/A'}</td>
                <td>${event.location || 'unknown'}</td>
                <td>
                    ${event.agenda_items ? event.agenda_items.map(item => `
                        <div>
                            <strong>${item.title}</strong> (${item.time || 'N/A'}) - ${item.status || 'N/A'}
                        </div>
                    `).join('') : 'N/A'}
                </td>
            `;
            tableBody.appendChild(row);
        });
    }
});
