document.addEventListener('DOMContentLoaded', function() {
    // Подтверждение удаления
    const deleteForms = document.querySelectorAll('form[action^="/delete_"]');
    deleteForms.forEach(form => {
        form.addEventListener('submit', function(e) {
            if (!confirm('Вы уверены, что хотите удалить этот элемент?')) {
                e.preventDefault();
            }
        });
    });
    
    // Подсветка сегодняшней даты в календаре
    const todayCells = document.querySelectorAll('.calendar td.today');
    todayCells.forEach(cell => {
        cell.innerHTML = `<strong>${cell.textContent}</strong>`;
    });
    
    // Быстрое создание заметки на выбранную дату в календаре
    const noteDateInput = document.getElementById('note_date');
    if (noteDateInput) {
        const urlParams = new URLSearchParams(window.location.search);
        const dateParam = urlParams.get('date');
        if (dateParam) {
            noteDateInput.value = dateParam;
        }
    }
});