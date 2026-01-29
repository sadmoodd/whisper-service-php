from fastapi import FastAPI, File, UploadFile, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import whisper
import os
import time
import tempfile
import requests
import logging
from pydub import AudioSegment
from dotenv import load_dotenv
import uvicorn

logging.basicConfig(level=logging.INFO, filename="whisper.log",
                    format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

load_dotenv()

app = FastAPI(title="Whisper AI API", version="2.0")


API_URL = "https://router.huggingface.co/v1/chat/completions"
headers = {
    "Authorization": f"Bearer {os.getenv('HF_TOKEN')}",
}


def query(payload):
    """Безопасный запрос к LLM"""
    try:
        response = requests.post(API_URL, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]['content'].strip()
    except Exception as e:
        logger.error(f"LLM query failed: {e}")
        return "Ошибка суммаризации"

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Модель (fp16=False для стабильности)
model = whisper.load_model("base")

async def transcribe_chunk_async(chunk_path: str, chunk_idx: int):
    """Безопасная транскрибация чанка"""
    try:
        result = model.transcribe(chunk_path)
        return {
            "text": result["text"].strip(),
            "segments": len(result.get("segments", []))
        }
    except Exception as e:
        logger.error(f"Chunk {chunk_idx} error: {e}")
        return {"text": "", "segments": 0}

@app.post("/api/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    logger.info("Запрос получен - обработка начата...")
    start = time.time()
    
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file selected")
    
    if file.size > 250 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large (max 250MB)")
    
    original_filename = file.filename
    file_ext = original_filename.split('.')[-1].lower()
    
    # 🔥 TemporaryDirectory - автоочистка!
    with tempfile.TemporaryDirectory() as tmpdir:
        original_filepath = os.path.join(tmpdir, f"original.{file_ext}")
        
        # Сохраняем оригинал
        content = await file.read()
        with open(original_filepath, "wb") as f:
            f.write(content)
        
        file_size = os.path.getsize(original_filepath)
        
        # Чанки (60s для стабильности)
        try:
            audio = AudioSegment.from_file(original_filepath)
            chunk_length_ms = 60 * 1000
            chunks = [audio[i:i + chunk_length_ms] for i in range(0, len(audio), chunk_length_ms)]
            
            logger.info(f"🎯 {len(chunks)} чанков по 60s")
            
            # Сохраняем чанки в tmpdir
            chunk_paths = []
            for idx, chunk in enumerate(chunks):
                chunk_path = os.path.join(tmpdir, f"chunk_{idx}.wav")
                chunk.export(chunk_path, format="wav")
                chunk_paths.append(chunk_path)
            
            # 🔥 ПОСЛЕДОВАТЕЛЬНАЯ обработка (без крашей!)
            all_results = []
            for idx, path in enumerate(chunk_paths):
                result = await transcribe_chunk_async(path, idx)
                logger.info(f"Чанк {idx + 1} из {len(chunk_paths)} обработан")
                all_results.append(result)
            
            logger.info("Все чанки обработаны успешно")
            # Собираем
            all_transcriptions = [r["text"] for r in all_results if r["text"]]
            total_segments = sum(r["segments"] for r in all_results)
            
            full_transcription = " ".join(all_transcriptions).strip()
            logger.info("Транскрипция получена")
        except Exception as e:
            logger.error(f"Audio processing failed: {e}")
            raise HTTPException(status_code=500, detail="Audio processing error")
    
    # Stats
    total_time = time.time() - start
    words = len(full_transcription.split())
    words_per_second = round(words / total_time, 2) if total_time > 0 else 0
    
    # LLM summary
    if full_transcription:
        prompt = f"""Проанализируй текст из аудио разбитый на чанки по 60с. Верни summary и примерные таймкоды и попытайся выделить собеседников,
        если это возможно. Если ничего не смог найти верни Не удалось аннотировать текст

        Транскрипция: {full_transcription}

        Только текст:"""
                
        payload = {
            "model": os.getenv("MODEL_NAME", 'Qwen/Qwen3-8B'),
            "messages": [
                {"role": "system", "content": "Ты анализатор аудио-текстов. Дай summary + таймкоды."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.57
        }
        logger.info('Обратились к LLM за аннотацией')
        summary = query(payload)
        logger.info(f'SUMMARY - {summary}')
    else:
        logger.warning("Модель на распознала текст возвращаем 'Нет распознанного текста'")
        summary = "Нет распознанного текста"
    
    # FastAPI - в stats ДОБАВЬТЕ:
    return {
        "success": True,
        "transcription": full_transcription,
        "summary": summary,
        "stats": {
            "total_processing_time": round(total_time, 2),
            "words_per_second": words_per_second,      # ✅ ДОБАВИТЬ!
            "file_size_mb": round(file_size / (1024*1024), 1),
            "chunks_processed": len(chunk_paths),
            "segments_count": total_segments,          # ✅ JS ищет ЭТО
            "total_words": words,
        },
        "filename": original_filename,
        "processing_time": round(total_time, 2)    # ✅ Корневой уровень для JS
    }


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "model": "base", "version": "1.1"}


if __name__ == "__main__":
    logger.info("API Запущен ----------")
    uvicorn.run(app, host="127.0.0.1", port=5000, reload=False)
    