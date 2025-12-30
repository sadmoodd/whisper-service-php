from fastapi import FastAPI, File, UploadFile, HTTPException, Request
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
import torch
import gc


app = FastAPI(title="Whisper AI API", version="2.0")


# 🔥 БЕЗОПАСНАЯ ИНИЦИАЛИЗАЦИЯ GPU/CPU
def init_model():
    torch.cuda.empty_cache() if torch.cuda.is_available() else None
    
    if torch.cuda.is_available():
        capability = torch.cuda.get_device_capability(0)
        print(f"🎮 GPU: {torch.cuda.get_device_name(0)} (capability {capability[0]}.{capability[1]})")
        
        # GTX 1070 = 6.1, используем base + оптимизации
        device = "cuda"
        model_size = "base" 
        os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"
    else:
        device = "cpu"
        model_size = "base"
    
    print(f"🚀 Загружаем {model_size} на {device}")
    model = whisper.load_model(model_size, device=device)
    print("✅ Модель готова!")
    return model


# Инициализация модели
model = init_model()
executor = ThreadPoolExecutor(max_workers=1)  # 1 worker = нет OOM


# CORS для Laravel
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def check_request_size(request: Request, call_next):
    body = await request.body()
    max_size = 250 * 1024 * 1024
    if len(body) > max_size:
        raise HTTPException(status_code=413, detail="Request too large")
    return await call_next(request)


async def transcribe_chunk_async(chunk_path: str, chunk_idx: int):
    """🔥 СТАБИЛЬНАЯ транскрибация с очисткой памяти"""
    loop = asyncio.get_event_loop()
    
    def transcribe_safe():
        try:
            # Оптимизации для GTX 1070
            result = model.transcribe(
                chunk_path, 
                fp16=torch.cuda.is_available(),  # fp16 только на GPU
                language="ru",  
                temperature=0.0  # Детерминизм
            )
            return {
                "text": result["text"].strip(),
                "segments": len(result["segments"]) if result["segments"] else 0
            }
        except Exception as e:
            print(f"❌ Чанк {chunk_idx}: {e}")
            return {"text": "", "segments": 0}
        finally:
            # 🔥 КРИТИЧНО: очистка после каждого чанка
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            gc.collect()
    
    result = await loop.run_in_executor(executor, transcribe_safe)
    return result


@app.post("/api/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    start = time.time()
    
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file selected")
    
    if file.size > 250 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large (max 250MB)")
    
    original_filename = file.filename
    file_ext = original_filename.split('.')[-1].lower()
    
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
        
        # 🔥 БОЛЬШИЕ ЧАНКИ = МЕНЬШЕ OOM
        chunk_length_ms = 60 * 1000  # 60 сек вместо 30
        
        chunks = []
        for i in range(0, len(audio), chunk_length_ms):
            chunk = audio[i:i + chunk_length_ms]
            if len(chunk) > 1000:  # Минимум 1 сек
                chunks.append(chunk)
        
        print(f"🎯 {len(chunks)} чанков по 60с (файл: {round(file_size/1024/1024,1)}MB)")
        
        # Сохраняем чанки
        for idx, chunk in enumerate(chunks):
            chunk_path = f"/tmp/chunk_{int(time.time())}_{idx:02d}.wav"
            chunk.export(chunk_path, format="wav")
            chunk_paths.append(chunk_path)
        
        # 🔥 ПОСЛЕДОВАТЕЛЬНАЯ обработка (1 за раз)
        all_results = []
        for idx, path in enumerate(chunk_paths):
            print(f"🔄 Обрабатываем чанк {idx+1}/{len(chunk_paths)}")
            result = await transcribe_chunk_async(path, idx)
            all_results.append(result)
        
        # Результаты
        all_transcriptions = [r["text"] for r in all_results if r["text"].strip()]
        total_segments = sum(r["segments"] for r in all_results)
        
        full_transcription = " ".join(all_transcriptions).strip()
        
        total_time = time.time() - start
        words = len(full_transcription.split())
        words_per_second = round(words / total_time, 2) if total_time > 0 else 0
        
        print(f"✅ Готово! {words} слов за {total_time:.1f}с ({words_per_second} wps)")
        
        return {
            "success": True,
            "transcription": full_transcription,
            "stats": {
                "total_processing_time": round(total_time, 2),
                "words_per_second": words_per_second,
                "file_size_mb": round(file_size / (1024*1024), 1),
                "chunks_processed": len(chunks),
                "segments_count": total_segments,
                "total_words": words,
                "device": "cuda" if torch.cuda.is_available() else "cpu",
                "model_size": "base"
            },
            "filename": original_filename
        }
        
    finally:
        # Очистка
        for path in chunk_paths:
            try:
                if os.path.exists(path):
                    os.remove(path)
            except:
                pass
        try:
            if os.path.exists(original_filepath):
                os.remove(original_filepath)
        except:
            pass
        
        # Финальная очистка GPU
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        gc.collect()


@app.get("/api/health")
async def health_check():
    device = "cuda" if torch.cuda.is_available() else "cpu"
    return {
        "status": "ok",
        "model": "base",
        "device": device,
        "framework": "FastAPI",
        "workers": executor._max_workers,
        "memory": torch.cuda.memory_allocated()/1024**2 if torch.cuda.is_available() else 0
    }


if __name__ == "__main__":
    # Предзапуск очистка
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    
    uvicorn.run(
        "app:app",
        host="127.0.0.1",
        port=5000,
        limit_max_requests=250*1024*1024,
        timeout_keep_alive=600,
        log_level="info"
    )