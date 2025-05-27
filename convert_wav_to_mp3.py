#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Required parameters:
# @raycast.schemaVersion 1
# @raycast.title Convert WAV to MP3
# @raycast.mode fullOutput

# Optional parameters:
# @raycast.icon 🎵
# @raycast.argument1 { "type": "text", "placeholder": "WAV file path" }
# @raycast.packageName Audio Tools
# @raycast.needsConfirmation false

# Documentation:
# @raycast.description Convert WAV file to MP3 format using FFmpeg
# @raycast.author yourname
# @raycast.authorURL https://github.com/yourusername

"""
WAV 파일을 MP3로 변환하는 Raycast 스크립트
필요 조건: 
- FFmpeg가 설치되어 있어야 함 (brew install ffmpeg)
"""

import os
import sys
import subprocess
import time
import re
import unicodedata

def check_ffmpeg_installed():
    """
    FFmpeg가 설치되어 있는지 확인합니다.
    
    Returns:
        bool: FFmpeg 설치 여부
    """
    try:
        result = subprocess.run(['which', 'ffmpeg'], 
                               stdout=subprocess.PIPE, 
                               stderr=subprocess.PIPE,
                               text=True)
        return result.returncode == 0
    except Exception:
        return False

def normalize_path(path):
    """
    입력된 경로를 정규화하고 절대 경로로 변환합니다.
    
    Args:
        path (str): 변환할 파일 경로
    
    Returns:
        str: 정규화된 절대 경로
    """
    # 유니코드 정규화
    path = unicodedata.normalize('NFC', path)
    
    # 경로가 따옴표로 감싸진 경우 제거
    path = path.strip('"\'')
    
    # 사용자 홈 디렉토리 (~) 확장
    if path.startswith('~'):
        path = os.path.expanduser(path)
    
    # 상대 경로를 절대 경로로 변환
    if not os.path.isabs(path):
        path = os.path.abspath(path)
    
    return path

def convert_wav_to_mp3(wav_path, bitrate='192k'):
    """
    WAV 파일을 MP3로 변환합니다.
    
    Args:
        wav_path (str): WAV 파일 경로
        bitrate (str): MP3 비트레이트 (기본값: 192k)
    
    Returns:
        str: 생성된 MP3 파일 경로
    """
    # 경로 정규화
    wav_path = normalize_path(wav_path)
    
    # 파일 존재 여부 확인
    if not os.path.exists(wav_path):
        raise FileNotFoundError(f"파일을 찾을 수 없습니다: {wav_path}")
    
    # 입력 파일이 WAV 형식인지 확인
    if not wav_path.lower().endswith('.wav'):
        raise ValueError("입력 파일이 WAV 형식이 아닙니다.")
    
    # 출력 파일 경로 생성
    mp3_path = os.path.splitext(wav_path)[0] + '.mp3'
    
    # FFmpeg 명령 구성
    command = [
        'ffmpeg',
        '-i', wav_path,
        '-codec:a', 'libmp3lame',
        '-b:a', bitrate,
        '-y',  # 기존 파일 덮어쓰기
        mp3_path
    ]
    
    print(f"변환 중: {os.path.basename(wav_path)} -> {os.path.basename(mp3_path)}")
    
    # FFmpeg 실행
    start_time = time.time()
    process = subprocess.run(command, 
                             stdout=subprocess.PIPE, 
                             stderr=subprocess.PIPE,
                             text=True)
    end_time = time.time()
    
    # 오류 확인
    if process.returncode != 0:
        raise RuntimeError(f"변환 실패: {process.stderr}")
    
    # 결과 확인
    if not os.path.exists(mp3_path):
        raise RuntimeError("MP3 파일이 생성되지 않았습니다.")
    
    duration = end_time - start_time
    
    # 파일 크기 정보
    wav_size = os.path.getsize(wav_path) / (1024 * 1024)  # MB 단위
    mp3_size = os.path.getsize(mp3_path) / (1024 * 1024)  # MB 단위
    
    print(f"변환 완료: {os.path.basename(mp3_path)}")
    print(f"소요 시간: {duration:.2f}초")
    print(f"WAV 크기: {wav_size:.2f} MB")
    print(f"MP3 크기: {mp3_size:.2f} MB")
    print(f"압축률: {(1 - mp3_size/wav_size) * 100:.2f}%")
    
    return mp3_path

def main():
    # FFmpeg 설치 확인
    if not check_ffmpeg_installed():
        print("오류: FFmpeg가 설치되어 있지 않습니다.", file=sys.stderr)
        print("FFmpeg를 설치하려면 터미널에서 'brew install ffmpeg' 명령어를 실행하세요.", file=sys.stderr)
        sys.exit(1)
    
    # 명령행 인자 처리
    if len(sys.argv) < 2:
        print("사용법: WAV 파일 경로를 입력하세요", file=sys.stderr)
        sys.exit(1)
    
    # 입력 파일 경로
    wav_path = sys.argv[1]
    
    try:
        # 단일 파일 변환
        if os.path.isfile(wav_path) or wav_path.lower().endswith('.wav'):
            mp3_path = convert_wav_to_mp3(wav_path)
            print(f"MP3 파일이 생성되었습니다: {mp3_path}")
        
        # 디렉토리 내 모든 WAV 파일 변환
        elif os.path.isdir(normalize_path(wav_path)):
            dir_path = normalize_path(wav_path)
            wav_files = [os.path.join(dir_path, f) for f in os.listdir(dir_path) 
                         if f.lower().endswith('.wav')]
            
            if not wav_files:
                print(f"디렉토리에 WAV 파일이 없습니다: {dir_path}")
                sys.exit(0)
            
            print(f"{len(wav_files)}개의 WAV 파일을 변환합니다...")
            
            for i, wav_file in enumerate(wav_files, 1):
                print(f"\n[{i}/{len(wav_files)}] 처리 중...")
                mp3_path = convert_wav_to_mp3(wav_file)
            
            print(f"\n총 {len(wav_files)}개의 WAV 파일이 MP3로 변환되었습니다.")
        
        else:
            print(f"오류: 유효하지 않은 입력입니다: {wav_path}", file=sys.stderr)
            sys.exit(1)
            
    except FileNotFoundError as e:
        print(f"오류: {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"오류: {e}", file=sys.stderr)
        sys.exit(1)
    except RuntimeError as e:
        print(f"오류: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"예상치 못한 오류: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()

