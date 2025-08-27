#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Required parameters:
# @raycast.schemaVersion 1
# @raycast.title play clipboard text by kitten_tts
# @raycast.mode fullOutput

# Optional parameters:
# @raycast.icon 🎵
# @raycast.packageName Audio Tools
# @raycast.needsConfirmation false

# Documentation:
# @raycast.description play clipboard text by kitten_tts
# @raycast.author ben
# @raycast.authorURL https://raycast.com/ben


import subprocess
import tempfile
import os
import re
import threading
from queue import Queue
from kittentts import KittenTTS
import soundfile as sf

def get_clipboard_text():
    try:
        result = subprocess.run(['pbpaste'], capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return None

def play_audio_file(audio_file):
    try:
        subprocess.run(['afplay', audio_file], check=True)
    except subprocess.CalledProcessError:
        print("Error playing audio file")

def split_text(text, max_length=300):
    if len(text) <= max_length:
        return [text]
    
    sentences = re.split(r'(?<=[.!?])\s+', text)
    chunks = []
    current_chunk = ""
    
    for sentence in sentences:
        if len(current_chunk) + len(sentence) + 1 <= max_length:
            current_chunk += (sentence + " ")
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            if len(sentence) > max_length:
                words = sentence.split()
                temp_chunk = ""
                for word in words:
                    if len(temp_chunk) + len(word) + 1 <= max_length:
                        temp_chunk += (word + " ")
                    else:
                        if temp_chunk:
                            chunks.append(temp_chunk.strip())
                        temp_chunk = word + " "
                current_chunk = temp_chunk
            else:
                current_chunk = sentence + " "
    
    if current_chunk:
        chunks.append(current_chunk.strip())
    
    return chunks

def generate_audio_worker(tts_model, text_queue, audio_queue, chunk_index):
    while True:
        item = text_queue.get()
        if item is None:
            break
        
        i, chunk = item
        try:
            print(f"Generating audio for chunk {i}...")
            audio = tts_model.generate(chunk, voice='expr-voice-3-m')
            
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                sf.write(temp_file.name, audio, 24000)
                audio_queue.put((i, temp_file.name))
        except Exception as e:
            print(f"Error generating chunk {i}: {e}")
            audio_queue.put((i, None))
        finally:
            text_queue.task_done()

def main():
    clipboard_text = get_clipboard_text()
    
    if not clipboard_text:
        print("No text found in clipboard")
        return
    
    text_chunks = split_text(clipboard_text)
    total_chunks = len(text_chunks)
    
    print(f"Text length: {len(clipboard_text)} characters")
    print(f"Split into {total_chunks} chunks")
    print("Starting audio conversion and playback...")
    
    m = KittenTTS("KittenML/kitten-tts-nano-0.1")
    
    text_queue = Queue()
    audio_queue = Queue()
    
    # 첫 번째 청크를 먼저 생성
    if total_chunks > 0:
        print(f"Generating first chunk...")
        first_chunk = text_chunks[0]
        try:
            audio = m.generate(first_chunk, voice='expr-voice-3-m')
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                sf.write(temp_file.name, audio, 24000)
                first_audio_path = temp_file.name
        except Exception as e:
            print(f"Error generating first chunk: {e}")
            return
    
    # 백그라운드 생성 스레드 시작
    generator_thread = threading.Thread(
        target=generate_audio_worker, 
        args=(m, text_queue, audio_queue, total_chunks)
    )
    generator_thread.start()
    
    # 나머지 청크들을 큐에 추가
    for i in range(1, total_chunks):
        text_queue.put((i + 1, text_chunks[i]))
    
    # 첫 번째 청크 재생
    print(f"\nPlaying chunk 1/{total_chunks}...")
    print(f"Text: {first_chunk[:100]}{'...' if len(first_chunk) > 100 else ''}")
    play_audio_file(first_audio_path)
    os.unlink(first_audio_path)
    
    # 나머지 청크들을 순차적으로 재생
    for i in range(1, total_chunks):
        try:
            chunk_num, audio_path = audio_queue.get(timeout=30)
            
            if audio_path is None:
                print(f"Skipping chunk {chunk_num} due to generation error")
                continue
            
            print(f"\nPlaying chunk {chunk_num}/{total_chunks}...")
            chunk_text = text_chunks[chunk_num - 1]
            print(f"Text: {chunk_text[:100]}{'...' if len(chunk_text) > 100 else ''}")
            
            play_audio_file(audio_path)
            os.unlink(audio_path)
            
        except Exception as e:
            print(f"Error playing chunk: {e}")
    
    # 정리
    text_queue.put(None)
    generator_thread.join()
    
    print("\nAll audio playback completed")

if __name__ == "__main__":
    main()
 