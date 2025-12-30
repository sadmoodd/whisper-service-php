<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Транскрибация - Whisper</title>
    
    <!-- Bootstrap 5 CSS -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <!-- Bootstrap Icons -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.css" rel="stylesheet">
    
    <style>
        body {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }
        .main-container {
            min-height: 100vh;
            padding: 2rem 0;
        }
        .custom-file-upload {
            position: relative;
            overflow: hidden;
        }
        .custom-file-upload input[type=file] {
            padding-right: 50px;
        }
        .custom-file-upload::after {
            content: "📁 Выберите файл";
            position: absolute;
            right: 15px;
            top: 50%;
            transform: translateY(-50%);
            pointer-events: none;
            font-size: 1rem;
            color: #6c757d;
        }
        .bg-gradient {
            background: linear-gradient(45deg, #0d6efd, #6610f2) !important;
        }
        #transcriptionText {
            font-size: 1.1rem;
            line-height: 1.6;
            white-space: pre-wrap;
            word-wrap: break-word;
        }
    </style>
</head>
<body>
    <div class="main-container">
        <div class="container py-5">
            <div class="row justify-content-center">
                <div class="col-lg-10 col-xl-8">
                    <!-- Заголовок -->
                    <div class="text-center mb-5">
                        <div class="display-5 mb-3 text-white">
                            <i class="bi bi-mic-fill text-primary"></i>
                            AI Транскрибация
                        </div>
                        <p class="lead text-white-50">
                            Загрузите аудио файл и получите текст за секунды с помощью Whisper AI
                        </p>
                    </div>

                    <!-- Health статус сервиса -->
                    <div class="card border-0 shadow-sm mb-5">
                        <div class="card-body">
                            <div class="row align-items-center">
                                <div class="col-auto">
                                    <div class="spinner-border spinner-border-sm text-primary d-none" id="healthSpinner"></div>
                                </div>
                                <div class="col">
                                    <div class="d-flex align-items-center">
                                        <i class="bi bi-circle-fill text-success me-2 fs-5" id="healthIcon"></i>
                                        <span class="h6 mb-0 fw-bold" id="healthStatus">Проверяем сервис...</span>
                                    </div>
                                    <small class="text-muted" id="healthDetails"></small>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Форма загрузки -->
                    <form id="transcribeForm" enctype="multipart/form-data" class="card shadow-lg border-0">
                        @csrf
                        <div class="card-header bg-gradient text-white py-4">
                            <h3 class="card-title mb-0">
                                <i class="bi bi-upload me-2"></i>
                                Загрузить аудио
                            </h3>
                        </div>
                        
                        <div class="card-body p-5">
                            <!-- Прогресс-бар -->
                            <div class="progress mb-4 d-none" id="uploadProgress" style="height: 8px;">
                                <div class="progress-bar progress-bar-striped progress-bar-animated bg-primary" 
                                     role="progressbar" style="width: 0%" id="progressBar"></div>
                            </div>

                            <!-- File input -->
                            <div class="mb-4">
                                <label for="audioFile" class="form-label fw-bold fs-5">
                                    Выберите аудио файл
                                </label>
                                <div class="custom-file-upload">
                                    <input type="file" 
                                           class="form-control form-control-lg" 
                                           id="audioFile" 
                                           name="audio" 
                                           accept="audio/*,.mp3,.wav,.webm,.m4a,.flac"
                                           required>
                                </div>
                                <div class="form-text mt-2">
                                    Поддерживаемые форматы: MP3, WAV, WebM, M4A, FLAC. Максимум 50MB.
                                </div>
                            </div>

                            <!-- Предпросмотр файла -->
                            <div id="filePreview" class="border rounded p-4 bg-light d-none mb-4">
                                <div class="row align-items-center">
                                    <div class="col-auto">
                                        <i class="bi bi-file-earmark-music fs-1 text-primary"></i>
                                    </div>
                                    <div class="col">
                                        <h6 class="mb-1" id="fileName"></h6>
                                        <small class="text-muted" id="fileSize"></small>
                                    </div>
                                    <div class="col-auto">
                                        <button type="button" class="btn btn-outline-danger btn-sm" id="clearFile">
                                            <i class="bi bi-x"></i>
                                        </button>
                                    </div>
                                </div>
                            </div>

                            <!-- Кнопки -->
                            <div class="d-grid d-md-flex gap-3">
                                <button type="button" class="btn btn-outline-secondary btn-lg flex-fill" id="backBtn">
                                    <i class="bi bi-arrow-left me-2"></i>
                                    Назад
                                </button>
                                <button type="submit" class="btn btn-primary btn-lg flex-fill" id="submitBtn" disabled>
                                    <i class="bi bi-mic-fill me-2"></i>
                                    <span id="submitText">Транскрибировать</span>
                                </button>
                            </div>
                        </div>
                    </form>

                    <!-- Результат -->
                    <div id="resultSection" class="mt-5 d-none">
                        <div class="card shadow-lg border-0">
                            <div class="card-header bg-success text-white py-4">
                                <h3 class="card-title mb-0">
                                    <i class="bi bi-check-circle-fill me-2"></i>
                                    Транскрибация завершена!
                                </h3>
                            </div>
                            <div class="card-body p-5">
                                <div class="row">
                                    <div class="col-md-8">
                                        <label class="form-label fw-bold fs-5 mb-2">Распознанный текст:</label>
                                        <div class="border rounded-3 p-4 bg-light" 
                                             id="transcriptionText" 
                                             style="min-height: 120px;">
                                            Результат появится здесь...
                                        </div>
                                        <div class="mt-3">
                                            <button class="btn btn-outline-primary me-2" id="copyBtn">
                                                <i class="bi bi-copy me-1"></i>Скопировать
                                            </button>
                                            <button class="btn btn-outline-success" id="downloadBtn">
                                                <i class="bi bi-download me-1"></i>Скачать TXT
                                            </button>
                                        </div>
                                    </div>
                                    <div class="col-md-4">
                                        <div class="card bg-light h-100">
                                            <div class="card-body">
                                                <h6 class="card-title">Статистика</h6>
                                                <div class="row text-center mb-3">
                                                    <div class="col-6">
                                                        <div class="h5 text-primary mb-0" id="processingTime">-</div>
                                                        <small class="text-muted">Время обработки</small>
                                                    </div>
                                                    <div class="col-6">
                                                        <div class="h5 text-success mb-0" id="wordsPerSec">-</div>
                                                        <small class="text-muted">Слов/сек</small>
                                                    </div>
                                                </div>
                                                <hr>
                                                <div class="row text-center">
                                                    <div class="col-6">
                                                        <div class="h6 text-info mb-0" id="fileSegments">-</div>
                                                        <small>Сегментов</small>
                                                    </div>
                                                    <div class="col-6">
                                                        <div class="h6 text-dark mb-0" id="fileNameResult">-</div>
                                                        <small>Файл</small>
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- Bootstrap 5 JS -->
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
        <script>
            class WhisperTranscriber {
                constructor() {
                    this.init();
                }

                init() {
                    this.form = document.getElementById('transcribeForm');
                    this.audioInput = document.getElementById('audioFile');
                    this.submitBtn = document.getElementById('submitBtn');
                    this.submitText = document.getElementById('submitText');
                    this.filePreview = document.getElementById('filePreview');
                    this.healthStatus = document.getElementById('healthStatus');
                    this.healthIcon = document.getElementById('healthIcon');
                    this.healthDetails = document.getElementById('healthDetails');
                    this.resultSection = document.getElementById('resultSection');

                    this.bindEvents();
                    this.checkHealth();
                }

                bindEvents() {
                    this.form.addEventListener('submit', (e) => this.handleSubmit(e));
                    this.audioInput.addEventListener('change', (e) => this.handleFileSelect(e));
                    document.getElementById('clearFile').addEventListener('click', () => this.clearFile());
                    document.getElementById('copyBtn').addEventListener('click', () => this.copyText());
                    document.getElementById('downloadBtn').addEventListener('click', () => this.downloadText());
                    document.getElementById('backBtn').addEventListener('click', () => this.resetForm());
                }

                async checkHealth() {
                    try {
                        document.getElementById('healthSpinner').classList.remove('d-none');
                        const response = await fetch('/api/health');
                        const data = await response.json();
                        
                        console.log('Health data:', data); // F12 → Console
                        
                        // ✅ ИСПРАВЛЕНО: Python статус = data.status
                        if (data.laravel_status === 'healthy' && data.status === 'ok') {
                            this.healthIcon.className = 'bi bi-circle-fill text-success fs-5 me-2';
                            this.healthStatus.textContent = '✅ Полностью готов';
                            this.healthDetails.textContent = 'Laravel + Whisper AI онлайн';
                        } else if (data.laravel_status === 'healthy') {
                            this.healthIcon.className = 'bi bi-circle-fill text-warning fs-5 me-2';
                            this.healthStatus.textContent = '⚠️ Только Laravel';
                            this.healthDetails.textContent = `Python: ${data.status || 'unavailable'}`;
                        }
                    } catch (error) {
                        console.error('Health check failed:', error);
                        this.healthIcon.className = 'bi bi-circle-fill text-danger fs-5 me-2';
                        this.healthStatus.textContent = '❌ Laravel недоступен';
                        this.healthDetails.textContent = 'Проверьте сервер';
                    } finally {
                        document.getElementById('healthSpinner').classList.add('d-none');
                    }
                }


                handleFileSelect(e) {
                    const file = e.target.files[0];
                    if (!file) return;

                    if (file.size > 50 * 1024 * 1024) {
                        alert('Файл слишком большой! Максимум 50MB.');
                        this.audioInput.value = '';
                        return;
                    }

                    document.getElementById('fileName').textContent = file.name;
                    document.getElementById('fileSize').textContent = this.formatFileSize(file.size);
                    this.filePreview.classList.remove('d-none');
                    this.submitBtn.disabled = false;
                }

                formatFileSize(bytes) {
                    if (bytes === 0) return '0 Bytes';
                    const k = 1024;
                    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
                    const i = Math.floor(Math.log(bytes) / Math.log(k));
                    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
                }

                async handleSubmit(e) {
                    e.preventDefault();
                    const formData = new FormData(this.form);

                    this.submitBtn.disabled = true;
                    this.submitText.innerHTML = '<i class="bi bi-hourglass-split spinner-border spinner-border-sm me-2"></i>Обработка...';
                    document.getElementById('uploadProgress').classList.remove('d-none');

                    let progressInterval;
                    try {
                        // ✅ ИСПРАВЛЕНО: Laravel вместо Python напрямую!
                        const response = await fetch('/api/transcribe', {
                            method: 'POST',
                            body: formData
                        });

                        const progressBar = document.getElementById('progressBar');
                        const data = await response.json();

                        console.log('Transcribe response:', data); // Отладка

                        // Имитация прогресса
                        let progress = 0;
                        progressInterval = setInterval(() => {
                            progress += Math.random() * 15;
                            if (progress > 90) progress = 90;
                            progressBar.style.width = progress + '%';
                        }, 300);

                        if (data.success) {
                            clearInterval(progressInterval);
                            setTimeout(() => { progressBar.style.width = '100%'; }, 500);
                            
                            document.getElementById('transcriptionText').textContent = data.transcription;
                            document.getElementById('processingTime').textContent = data.processing_time + 'с';
                            document.getElementById('wordsPerSec').textContent = (data.stats?.words_per_second || 0).toFixed(1);
                            document.getElementById('fileSegments').textContent = data.stats?.segments_count || 1;
                            document.getElementById('fileNameResult').textContent = data.filename;
                            
                            this.resultSection.classList.remove('d-none');
                            this.form.classList.add('d-none');
                        } else {
                            throw new Error(data.message || data.error || 'Неизвестная ошибка');
                        }
                    } catch (error) {
                        console.error('Transcription error:', error);
                        alert('Ошибка: ' + (error.message || 'Не удалось обработать файл'));
                    } finally {
                        if (progressInterval) clearInterval(progressInterval);
                        document.getElementById('uploadProgress').classList.add('d-none');
                        this.submitBtn.disabled = false;
                        this.submitText.textContent = 'Транскрибировать';
                    }
                }

                clearFile() {
                    this.audioInput.value = '';
                    this.filePreview.classList.add('d-none');
                    this.submitBtn.disabled = true;
                }

                copyText() {
                    navigator.clipboard.writeText(document.getElementById('transcriptionText').textContent).then(() => {
                        const btn = document.getElementById('copyBtn');
                        const original = btn.innerHTML;
                        btn.innerHTML = '<i class="bi bi-check-lg me-1"></i>Скопировано!';
                        btn.classList.add('btn-success');
                        setTimeout(() => {
                            btn.innerHTML = original;
                            btn.classList.remove('btn-success');
                        }, 2000);
                    });
                }

                downloadText() {
                    const text = document.getElementById('transcriptionText').textContent;
                    const blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = 'transcription.txt';
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                    URL.revokeObjectURL(url);
                }

                resetForm() {
                    this.resultSection.classList.add('d-none');
                    this.form.classList.remove('d-none');
                    this.clearFile();
                }
            }

            document.addEventListener('DOMContentLoaded', () => {
                new WhisperTranscriber();
            });
            </script>

    </script>
</body>
</html>
