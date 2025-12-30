from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import whisper
import os
import time
import asyncio
import tempfile
from pydub import AudioSegment
from concurrent.futures import ThreadPoolExecutor
import uvicorn

app = FastAPI(title="Whisper AI API", version="2.0")

# CORS для Laravel
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Загружаем модель
model = whisper.load_model("tiny")
executor = ThreadPoolExecutor(max_workers=4)

async def transcribe_chunk_async(chunk_path: str, chunk_idx: int):
    """Параллельная транскрибация чанка"""
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        executor, lambda: model.transcribe(chunk_path)
    )
    return {
        "text": result["text"].strip(),
        "segments": len(result["segments"]) if result["segments"] else 0
    }

@app.post("/api/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    start = time.time()
    
    # Валидация
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file selected")
    
    if file.size > 100 * 1024 * 1024:  # 50MB
        raise HTTPException(status_code=400, detail="File too large (max 100MB)")
    
    original_filename = file.filename
    file_ext = original_filename.split('.')[-1]
    
    # Временные файлы
    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_ext}") as tmp:
        original_filepath = tmp.name
    
    chunk_paths = []
    
    try:
        # Сохраняем файл
        content = await file.read()
        with open(original_filepath, "wb") as f:
            f.write(content)
        
        file_size = os.path.getsize(original_filepath)
        audio = AudioSegment.from_file(original_filepath)
        chunk_length_ms = 30 * 1000  # 30 сек
        
        # Создаем чанки
        chunks = []
        for i in range(0, len(audio), chunk_length_ms):
            chunk = audio[i:i + chunk_length_ms]
            chunks.append(chunk)
        
        print(f"🎯 {len(chunks)} чанков по 30с")
        
        # Сохраняем чанки
        for idx, chunk in enumerate(chunks):
            chunk_path = f"/tmp/chunk_{int(time.time())}_{idx}.wav"
            chunk.export(chunk_path, format="wav")
            chunk_paths.append(chunk_path)
        
        # 🔥 ПАРАЛЛЕЛЬНАЯ ОБРАБОТКА
        tasks = [transcribe_chunk_async(path, idx) for idx, path in enumerate(chunk_paths)]
        all_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Результаты
        all_transcriptions = []
        total_segments = 0
        for result in all_results:
            if isinstance(result, Exception):
                print(f"⚠️ Ошибка чанка: {result}")
                continue
            all_transcriptions.append(result["text"])
            total_segments += result["segments"]
        
        full_transcription = " ".join([t for t in all_transcriptions if t])
        
        total_time = time.time() - start
        words = len(full_transcription.split())
        words_per_second = round(words / total_time, 2) if total_time > 0 else 0
        
        return {
            "success": True,
            "transcription": full_transcription.strip(),
            "stats": {
                "total_processing_time": round(total_time, 2),
                "words_per_second": words_per_second,
                "file_size_mb": round(file_size / (1024*1024), 1),
                "chunks_processed": len(chunks),
                "segments_count": total_segments,
                "total_words": words,
            },
            "filename": original_filename
        }
        
    finally:
        # Очистка
        for path in chunk_paths:
            if os.path.exists(path):
                os.remove(path)
        if os.path.exists(original_filepath):
            os.remove(original_filepath)

@app.get("/api/health")
async def health_check():
    return {
        "status": "ok",
        "model": "tiny",
        "framework": "FastAPI",
        "async": "native",
        "workers": executor._max_workers,
    }

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=5000)
