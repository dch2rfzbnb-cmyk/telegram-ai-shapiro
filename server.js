const express = require('express');
const path = require('path');
const app = express();
const PORT = process.env.PORT || 3000;

// Отдаем статику из папки public
app.use(express.static(path.join(__dirname, 'public')));

// Главный маршрут — отдаем index.html
app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, 'public', 'index-simple.html'));  // ← ИЗМЕНИ!
});

// Запуск сервера
app.listen(PORT, () => {
    console.log(`🚀 Сервер запущен: http://localhost:${PORT}`);
    console.log('Нажми Ctrl+C для остановки');
});
