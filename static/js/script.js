// Modal handling
function openModal(status) {
    document.getElementById('modal-status').value = status;
    document.getElementById('task-modal').style.display = 'block';
}

function closeModal() {
    document.getElementById('task-modal').style.display = 'none';
}

// Close modal when clicking outside
window.onclick = function(event) {
    const modal = document.getElementById('task-modal');
    if (event.target === modal) {
        closeModal();
    }
}

// Form submission
document.getElementById('task-form').addEventListener('submit', function(e) {
    e.preventDefault();

    // Validate form
    const title = this.elements['title'].value;
    const dueDate = this.elements['due_date'].value;

    if (!title || !dueDate) {
        alert('Please fill in all required fields');
        return;
    }

    // Submit the form
    this.submit();
});

document.addEventListener('DOMContentLoaded', function() {
    const calendarEl = document.getElementById('calendar');
    const eventModal = document.getElementById('event-modal');
    const eventForm = document.getElementById('event-form');
    const addEventBtn = document.getElementById('add-event-btn');

    // Initialize calendar
    const calendar = new FullCalendar.Calendar(calendarEl, {
        initialView: 'dayGridMonth',
        headerToolbar: {
            left: 'prev,next today',
            center: 'title',
            right: 'dayGridMonth,timeGridWeek,timeGridDay'
        },
        events: JSON.parse('{{ events | tojson | safe }}').map(event => ({
            title: event.title,
            start: event.start,
            className: event.status.toLowerCase().replace(' ', '-'),
            extendedProps: {
                status: event.status,
                id: event.id
            }
        })),
        eventClick: function(info) {
            // Handle event click (view/edit task)
            window.location.href = `/board#task-${info.event.extendedProps.id}`;
        }
    });

    calendar.render();

    // Add event button click handler
    addEventBtn.addEventListener('click', function() {
        eventModal.style.display = 'block';
    });

    // Event form submission
    eventForm.addEventListener('submit', function(e) {
        e.preventDefault();
        const title = document.getElementById('event-title').value;
        const date = document.getElementById('event-date').value;
        const status = document.getElementById('event-status').value;

        // Here you would typically make an AJAX call to save the task
        // For now, we'll just add it to the calendar
        calendar.addEvent({
            title: title,
            start: date,
            className: status.toLowerCase().replace(' ', '-'),
            allDay: true
        });

        closeModal();
        eventForm.reset();
    });
});

function closeModal() {
    document.getElementById('event-modal').style.display = 'none';
}
// Function to toggle task menu
function toggleTaskMenu(taskId) {
    const menu = document.getElementById(`menu-${taskId}`);
    const allMenus = document.querySelectorAll('.task-menu');

    // Close all other menus
    allMenus.forEach(m => {
        if (m.id !== `menu-${taskId}`) {
            m.classList.remove('show');
        }
    });

    // Toggle current menu
    menu.classList.toggle('show');
}

// Close menus when clicking elsewhere
document.addEventListener('click', function(event) {
    if (!event.target.closest('.task-menu') && !event.target.closest('.task-menu-btn')) {
        document.querySelectorAll('.task-menu').forEach(menu => {
            menu.classList.remove('show');
        });
    }
});