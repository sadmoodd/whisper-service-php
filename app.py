from flask import Flask, request, jsonify
import whisper
import os
import time
import pydub  # pip install pydub
import tempfile
from pydub import AudioSegment
import numpy as np

app = Flask(__name__)
from flask_cors import CORS
CORS(app)

# Load Whisper model
model = whisper.load_model("tiny")

@app.route('/api/transcribe', methods=['POST'])
def transcribe_audio():
    start = time.time()
    
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    # Save original file
    original_filename = file.filename
    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file.filename.split('.')[-1]}") as tmp:
        file.save(tmp.name)
        original_filepath = tmp.name

    try:
        file_size = os.path.getsize(original_filepath)
        
        # 🔧 НОВОЕ: Разбиваем аудио на чанки по 30 секунд
        audio = AudioSegment.from_file(original_filepath)
        chunk_length_ms = 30 * 1000  # 30 секунд
        chunks = []
        
        for i in range(0, len(audio), chunk_length_ms):
            chunk = audio[i:i + chunk_length_ms]
            chunks.append(chunk)
        
        print(f"Разбили на {len(chunks)} чанков по {chunk_length_ms/1000}с")
        
        # Обрабатываем каждый чанк отдельно
        all_transcriptions = []
        chunk_times = []
        
        transcribe_start = time.time()
        
        for idx, chunk in enumerate(chunks):
            print(f"Обрабатываем чанк {idx+1}/{len(chunks)}...")
            
            # Сохраняем чанк временно
            chunk_path = f"/tmp/chunk_{idx}_{original_filename}"
            chunk.export(chunk_path, format="wav")
            
            # Транскрибируем чанк
            chunk_result = model.transcribe(chunk_path)
            all_transcriptions.append(chunk_result["text"].strip())
            
            chunk_times.append(chunk_result["segments"][0]["end"] if chunk_result["segments"] else 0)
            
            os.remove(chunk_path)  # Удаляем чанк
        
        transcribe_end = time.time()
        
        # Собираем полный текст
        full_transcription = " ".join([t for t in all_transcriptions if t])
        
        # Статистика
        total_time = transcribe_end - transcribe_start
        words = len(full_transcription.split())
        words_per_second = round(words / total_time, 2) if total_time > 0 else 0
        
        result = {
            "transcription": full_transcription.strip(),
            "stats": {
                "total_processing_time": total_time,
                "words_per_second": words_per_second,
                "file_size_in_bytes": file_size,
                "chunks_processed": len(chunks),
                "chunk_duration_sec": chunk_length_ms / 1000,
                "total_words": words
            },
            "filename": original_filename,
            "chunks": len(chunks)  # Для отладки
        }
        
        return jsonify(result)
        
    finally:
        # Удаляем оригинальный файл
        if os.path.exists(original_filepath):
            os.remove(original_filepath)

@app.route('/api/health', methods=["GET"])
def health_check():
    return jsonify({"status": "ok", "message": "API is OK!"})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
