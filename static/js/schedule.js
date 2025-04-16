document.addEventListener('DOMContentLoaded', () => {
    // Initialize FullCalendar
    const calendarEl = document.getElementById('calendar');
    const calendar = new FullCalendar.Calendar(calendarEl, {
        initialView: 'dayGridMonth',
        events: '/schedule/events', // Fetch events from the backend
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

    // Toggle agenda items visibility
    document.querySelectorAll('.toggle-agenda').forEach(button => {
        button.addEventListener('click', () => {
            const eventId = button.getAttribute('data-event-id');
            const agendaItems = document.getElementById(`agenda-items-${eventId}`);
            if (agendaItems.style.display === 'none') {
                agendaItems.style.display = 'block';
            } else {
                agendaItems.style.display = 'none';
            }
        });
    });
});
