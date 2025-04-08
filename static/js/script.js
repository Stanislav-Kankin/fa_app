document.addEventListener('DOMContentLoaded', function() {
    // Можно добавить любую клиентскую логику здесь
    console.log('Приложение загружено');
    
    // Пример: обработка кликов по кнопкам
    const buttons = document.querySelectorAll('.btn, .dashboard-btn');
    buttons.forEach(button => {
        button.addEventListener('click', function() {
            console.log('Нажата кнопка:', this.textContent);
        });
    });
});