<?php

use Illuminate\Support\Facades\Route;
use App\Http\Controllers\WhisperController;

Route::get('/', [WhisperController::class, 'index'])->name('whisper.index');
Route::prefix('api')->group(function () {
    Route::post('/transcribe', [WhisperController::class, 'transcribe']);
    Route::get('/health', [WhisperController::class, 'health']);
});
