#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Required parameters:
# @raycast.schemaVersion 1
# @raycast.title Convert WAV to MP3 in Finder
# @raycast.mode fullOutput

# Optional parameters:
# @raycast.icon 🎵
# @raycast.packageName Audio Tools
# @raycast.needsConfirmation false

# Documentation:
# @raycast.description Convert WAV files to MP3 format using FFmpeg (uses Finder selection)
# @raycast.author ben
# @raycast.authorURL https://raycast.com/ben

"""
WAV 파일을 MP3로 변환하는 Raycast 스크립트
특징: Finder에서 선택한 WAV 파일을 자동으로 감지하여 변환합니다.
필요 조건: 
- FFmpeg가 설치되어 있어야 함 (brew install ffmpeg)
"""

import os
import sys
import subprocess
import time
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

def get_finder_selection():
    """
    Finder에서 현재 선택된 파일/폴더의 경로를 가져옵니다.
    
    Returns:
        list: 선택된 파일/폴더 경로 목록
    """
    script = '''
    osascript -e 'tell application "Finder"
        set selectedItems to selection as alias list
        set pathList to {}
        repeat with i from 1 to count of selectedItems
            set selectedItem to item i of selectedItems
            set pathList to pathList & (POSIX path of selectedItem)
        end repeat
        return pathList
    end tell'
    '''
    
    try:
        result = subprocess.run(script, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode == 0 and result.stdout.strip():
            paths = result.stdout.strip().split(", ")
            return [path.strip() for path in paths if path.strip()]
        return []
    except Exception:
        return []

def open_file_dialog(file_types=None):
    """
    파일 선택 대화상자를 열어 사용자가 파일을 선택하도록 합니다.
    
    Args:
        file_types (list): 허용할 파일 확장자 목록 (예: ['.wav'])
    
    Returns:
        str: 선택한 파일의 경로 또는 취소 시 None
    """
    if file_types is None:
        file_types = ['.wav']
    
    file_types_str = ' '.join(f'"{ext}"' for ext in file_types)
    
    # AppleScript를 사용하여 파일 선택 대화상자 표시
    script = f'''
    osascript -e 'tell application "System Events"
        set selectedFile to choose file with prompt "변환할 WAV 파일을 선택하세요:" of type {{"WAV"}}
        return POSIX path of selectedFile
    end tell'
    '''
    
    try:
        result = subprocess.run(script, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
        return None
    except Exception:
        return None

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
        raise ValueError(f"입력 파일이 WAV 형식이 아닙니다: {wav_path}")
    
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

def get_wav_files_from_directory(directory_path):
    """
    디렉토리에서 모든 WAV 파일을 찾습니다.
    
    Args:
        directory_path (str): 디렉토리 경로
    
    Returns:
        list: WAV 파일 경로 목록
    """
    directory_path = normalize_path(directory_path)
    if not os.path.isdir(directory_path):
        raise ValueError(f"유효한 디렉토리가 아닙니다: {directory_path}")
    
    wav_files = []
    for root, dirs, files in os.walk(directory_path):
        for file in files:
            if file.lower().endswith('.wav'):
                wav_files.append(os.path.join(root, file))
    
    return wav_files

def main():
    # FFmpeg 설치 확인
    if not check_ffmpeg_installed():
        print("오류: FFmpeg가 설치되어 있지 않습니다.", file=sys.stderr)
        print("FFmpeg를 설치하려면 터미널에서 'brew install ffmpeg' 명령어를 실행하세요.", file=sys.stderr)
        sys.exit(1)
    
    # Finder에서 선택한 항목 가져오기
    selected_paths = get_finder_selection()
    
    if selected_paths:
        # Finder에서 선택된 항목이 있는 경우
        print(f"Finder에서 {len(selected_paths)}개 항목이 선택되었습니다.")
        
        # WAV 파일과 디렉토리 분류
        wav_files = []
        directories = []
        
        for path in selected_paths:
            norm_path = normalize_path(path)
            if os.path.isdir(norm_path):
                directories.append(norm_path)
            elif norm_path.lower().endswith('.wav'):
                wav_files.append(norm_path)
        
        # 디렉토리에서 WAV 파일 추가
        for directory in directories:
            try:
                dir_wav_files = get_wav_files_from_directory(directory)
                if dir_wav_files:
                    print(f"디렉토리 '{os.path.basename(directory)}'에서 {len(dir_wav_files)}개의 WAV 파일을 찾았습니다.")
                    wav_files.extend(dir_wav_files)
                else:
                    print(f"디렉토리 '{os.path.basename(directory)}'에 WAV 파일이 없습니다.")
            except Exception as e:
                print(f"디렉토리 '{directory}' 처리 중 오류 발생: {e}", file=sys.stderr)
        
        if not wav_files:
            print("선택된 항목 중 WAV 파일이 없습니다.")
            # 파일 선택 대화상자 열기
            wav_path = open_file_dialog(['.wav'])
            if not wav_path:
                print("파일 선택이 취소되었습니다.")
                sys.exit(0)
            wav_files = [wav_path]
    else:
        # Finder에서 선택된 항목이 없는 경우
        print("Finder에서 선택된 항목이 없습니다.")
        # 파일 선택 대화상자 열기
        wav_path = open_file_dialog(['.wav'])
        if not wav_path:
            print("파일 선택이 취소되었습니다.")
            sys.exit(0)
        wav_files = [wav_path]
    
    # 중복 제거 및 정렬
    wav_files = sorted(list(set(wav_files)))
    
    try:
        # 파일 변환
        if len(wav_files) == 1:
            print("\n단일 파일 변환 시작...")
            mp3_path = convert_wav_to_mp3(wav_files[0])
            print(f"\nMP3 파일이 성공적으로 생성되었습니다: {mp3_path}")
        else:
            print(f"\n총 {len(wav_files)}개의 WAV 파일 변환 시작...")
            
            # 진행 상황 표시를 위한 카운터
            success_count = 0
            error_count = 0
            errors = []
            
            for i, wav_file in enumerate(wav_files, 1):
                try:
                    print(f"\n[{i}/{len(wav_files)}] 변환 중...")
                    mp3_path = convert_wav_to_mp3(wav_file)
                    success_count += 1
                except Exception as e:
                    error_count += 1
                    errors.append((wav_file, str(e)))
                    print(f"오류: {e}", file=sys.stderr)
            
            # 최종 결과 요약
            print("\n=== 변환 결과 요약 ===")
            print(f"총 파일 수: {len(wav_files)}")
            print(f"성공: {success_count}")
            print(f"실패: {error_count}")
            
            if error_count > 0:
                print("\n=== 오류 목록 ===")
                for wav_file, error in errors:
                    print(f"- {os.path.basename(wav_file)}: {error}")
    
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
