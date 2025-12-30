<?php

namespace App\Http\Controllers;

use App\Http\Controllers\Controller;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Storage;
use Illuminate\Support\Str;

class WhisperController extends Controller
{
    private const WHISPER_API_URL = 'http://127.0.0.1:5000/api/transcribe';

    public function index(){
        return view('index');
    }

    public function transcribe(Request $request)
    {
        // Валидация аудио файла
        $request->validate([
            'audio' => 'required|file|mimes:mp3,wav,webm,m4a|max:1000000' // 10MB max
        ]);

        $audioFile = $request->file('audio');
        $originalName = $audioFile->getClientOriginalName();
        $fileName = Str::uuid() . '.' . $audioFile->getClientOriginalExtension();
        $filePath = 'whisper/' . $fileName;

        // Сохраняем файл временно
        $diskPath = $audioFile->storeAs('whisper', $fileName, 'local');

        try {
            // Отправляем в Python API
            $response = Http::timeout(120) // 2 минуты таймаут
                ->attach('file', file_get_contents(Storage::path($diskPath)), $originalName)
                ->post(self::WHISPER_API_URL);

            // Удаляем временный файл
            Storage::disk('local')->delete($diskPath);

            if ($response->successful()) {
                $data = $response->json();
                
                return response()->json([
                    'success' => true,
                    'transcription' => $data['transcription'] ?? '',
                    'filename' => $originalName,
                    'stats' => $data['stats'] ?? [],
                    'processing_time' => $data['stats']['total_processing_time'] ?? 0
                ]);
            }

            return response()->json([
                'success' => false,
                'error' => 'Whisper API error',
                'message' => $response->body()
            ], 502);

        } catch (\Exception $e) {
            // Удаляем файл при ошибке
            Storage::disk('local')->delete($diskPath);
            
            return response()->json([
                'success' => false,
                'error' => 'Service unavailable',
                'message' => $e->getMessage()
            ], 503);
        }
    }

    public function health()
    {
        $response = Http::timeout(5)->get('http://127.0.0.1:5000/api/health');
        $whisperData = $response->successful() ? $response->json() : ['status' => 'unavailable'];
        
        return response()->json([
            'status' => $whisperData['status'] ?? 'unavailable',
            'message' => $whisperData['message'] ?? null,
            'laravel_status' => 'healthy'
        ]);
    }

}
