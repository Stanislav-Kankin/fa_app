document.addEventListener('DOMContentLoaded', function() {
    // Подтверждение удаления
    document.querySelectorAll('.delete-form').forEach(form => {
        form.addEventListener('submit', function(e) {
            if (!confirm('Вы уверены, что хотите удалить этот файл?')) {
                e.preventDefault();
            }
        });
    });

    // Drag and drop для загрузки файлов
    const fileUpload = document.getElementById('file-upload');
    const uploadLabel = document.querySelector('.file-upload-label');
    
    if (fileUpload && uploadLabel) {
        // Подсветка при наведении
        uploadLabel.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadLabel.style.backgroundColor = 'rgba(76, 175, 80, 0.1)';
            uploadLabel.style.borderColor = '#4CAF50';
        });

        // Сброс подсветки
        uploadLabel.addEventListener('dragleave', () => {
            uploadLabel.style.backgroundColor = '';
            uploadLabel.style.borderColor = '';
        });

        // Обработка drop
        uploadLabel.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadLabel.style.backgroundColor = '';
            uploadLabel.style.borderColor = '';
            
            if (e.dataTransfer.files.length) {
                fileUpload.files = e.dataTransfer.files;
                // Обновляем текст
                const fileName = e.dataTransfer.files[0].name;
                document.querySelector('.upload-text').textContent = fileName;
            }
        });

        // Обновление текста при выборе файла
        fileUpload.addEventListener('change', function() {
            if (this.files.length) {
                document.querySelector('.upload-text').textContent = this.files[0].name;
            }
        });
    }

    // Воспроизведение видео при наведении
    document.querySelectorAll('.video-preview video').forEach(video => {
        const parent = video.closest('.media-card');
        
        parent.addEventListener('mouseenter', () => {
            video.play().catch(e => console.log('Автовоспроизведение не разрешено'));
        });
        
        parent.addEventListener('mouseleave', () => {
            video.pause();
            video.currentTime = 0;
        });
    });
});