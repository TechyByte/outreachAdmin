document.addEventListener('DOMContentLoaded', () => {
    // Initialize FullCalendar
    const calendarEl = document.getElementById('calendar');
    const calendar = new FullCalendar.Calendar(calendarEl, {
        initialView: 'dayGridMonth',
        events: function(fetchInfo, successCallback, failureCallback) {
            // Build query parameters from filters
            const params = new URLSearchParams();
            document.querySelectorAll('#filters-form select').forEach(select => {
                Array.from(select.selectedOptions).forEach(option => {
                    params.append(select.name, option.value);
                });
            });
            params.append('n_days', 60); // Example: Pass n_days filter

            // Fetch events with filters
            fetch(`/schedule/events?${params.toString()}`)
                .then(response => response.json())
                .then(data => successCallback(data))
                .catch(error => failureCallback(error));
        },
        headerToolbar: {
            left: 'prev,next today',
            center: 'title',
            right: 'dayGridMonth,timeGridWeek,timeGridDay'
        },
        eventClick: function (info) {
            alert(`Event: ${info.event.title}`);
        }
    });
    calendar.render();

    // Ensure Bootstrap tabs are initialized
    $('#schedule-tabs a[data-toggle="tab"]').on('shown.bs.tab', function (e) {
        const target = $(e.target).attr("href"); // Get the target tab
        console.log(`Switched to tab: ${target}`);
    });

    // Re-render calendar when filters are applied
    document.getElementById('filters-form').addEventListener('submit', (e) => {
        e.preventDefault();
        calendar.refetchEvents();
    });
});
