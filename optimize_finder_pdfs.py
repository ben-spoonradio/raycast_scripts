#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Required parameters:
# @raycast.schemaVersion 1
# @raycast.title  Optimize pdf in Finder
# @raycast.mode fullOutput

# Optional parameters:
# @raycast.icon 📄
# @raycast.packageName PDF Tools
# @raycast.needsConfirmation false

# Documentation:
# @raycast.description Optimize pdf (uses Finder selection)
# @raycast.author moonbc
# @raycast.authorURL https://raycast.com/moonbc

"""
PDF 파일을 최적화하는 Raycast 스크립트
특징: PDF/A 생성, 이미지 최적화 및 JPEG 저장을 포함한 PDF 최적화
필요 조건: 
- Ghostscript가 설치되어 있어야 함 (brew install ghostscript)
- AppleScript를 사용하여 Finder에서 선택된 파일을 가져옵니다.
- PDF 파일만 처리합니다.
- 최적화된 파일은 원본 파일과 같은 디렉토리에 저장됩니다.
- 파일 이름에 특수 문자가 포함된 경우, 안전한 파일 이름으로 변경합니다.
- 최적화된 파일 이름은 원본 파일 이름에 "_optimized"가 추가됩니다.
- 최적화된 파일의 크기와 절감율을 출력합니다.
- 오류 발생 시 오류 메시지를 출력합니다.
- 사용법: 1) Finder에서 PDF 파일을 선택한 후 이 스크립트 실행
        2) 또는 명령줄에서 파일 경로 지정: python script.py /path/to/file.pdf
- 스크립트 실행 후 최적화된 PDF 파일이 생성됩니다.
"""

import subprocess
import os
from pathlib import Path
import sys
import shutil
import tempfile
import re

def get_selected_files_from_finder():
    """
    AppleScript를 사용하여 현재 Finder에서 선택된 파일 목록을 가져옵니다.
    개선된 버전: 다양한 특수문자를 포함한 파일 이름을 처리합니다.
    """
    apple_script = '''
    tell application "Finder"
        set sel_items to selection as alias list
        set output_text to ""
        repeat with i in sel_items
            set file_path to POSIX path of i
            set output_text to output_text & file_path & "\\n"
        end repeat
        return output_text
    end tell
    '''
    
    try:
        result = subprocess.run(['osascript', '-e', apple_script], 
                               capture_output=True, text=True, check=True)
        
        # 개행문자로 구분된 파일 경로를 리스트로 변환
        file_paths = [path.strip() for path in result.stdout.strip().split('\n') if path.strip()]
        return file_paths
    except subprocess.CalledProcessError as e:
        print(f"AppleScript 실행 중 오류 발생: {e}")
        if hasattr(e, 'stderr') and e.stderr:
            print(f"오류 내용: {e.stderr}")
        return []

def check_ghostscript_installation():
    """
    Ghostscript가 설치되어 있는지 확인하고, 경로를 반환합니다.
    """
    # 가능한 Ghostscript 실행 파일 경로들
    possible_paths = [
        'gs',  # 환경 변수 PATH에 있는 경우
        '/usr/local/bin/gs',  # Homebrew 일반 설치 경로
        '/opt/homebrew/bin/gs',  # Apple Silicon Mac의 Homebrew 경로
        '/usr/bin/gs',  # 일부 리눅스 시스템
        '/opt/local/bin/gs',  # MacPorts
    ]
    
    # 각 경로 확인
    for path in possible_paths:
        if shutil.which(path):
            return path
    
    # 설치되지 않은 경우 안내 메시지 출력
    print("❌ Ghostscript(gs)가 설치되어 있지 않습니다.")
    print("Homebrew를 사용하여 설치하려면 터미널에서 다음 명령을 실행하세요:")
    print("brew install ghostscript")
    print("\n설치 후 이 스크립트를 다시 실행해주세요.")
    return None

def sanitize_filename(filename):
    """
    파일 이름에서 시스템에 문제를 일으킬 수 있는 특수 문자를 제거합니다.
    """
    # 허용할 문자들: 영숫자, 점, 하이픈, 언더스코어, 공백
    sanitized = re.sub(r'[^\w\-\. ]', '_', filename)
    return sanitized

def optimize_pdf(input_path: str, output_path: str, gs_path: str):
    """
    PDF/A 생성, 이미지 최적화 및 JPEG 저장을 포함한 PDF 최적화 함수
    """
    input_file = Path(input_path).expanduser()
    output_file = Path(output_path).expanduser()
    
    if not input_file.exists():
        raise FileNotFoundError(f"입력 PDF를 찾을 수 없습니다: {input_file}")
    
    # 출력 디렉토리가 없으면 생성
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    gs_command = [
        gs_path,
        "-sDEVICE=pdfwrite",
        "-dCompatibilityLevel=1.4",
        "-dPDFSETTINGS=/screen",  # 이미지 최적화
        "-dPDFA=2",               # PDF/A-2 모드 활성화
        "-dBATCH",
        "-dNOPAUSE",
        "-dQUIET",
        "-dNOOUTERSAVE",
        "-dUseCIEColor",
        "-dColorImageDownsampleType=/Bicubic",     # 해상도 감소
        "-dColorImageResolution=150",              # 이미지 DPI 조정
        "-dAutoFilterColorImages=false",
        "-dColorImageFilter=/DCTEncode",           # JPEG 압축
        "-sOutputFile=" + str(output_file),
        str(input_file)
    ]
    
    try:
        result = subprocess.run(gs_command, check=True, capture_output=True)
        
        # 원본 및 최적화된 파일 크기 비교
        original_size = os.path.getsize(input_file)
        optimized_size = os.path.getsize(output_file)
        
        reduction = 100 - (optimized_size / original_size * 100)
        
        print(f"✅ PDF 최적화 완료: {output_file}")
        print(f"   원본 크기: {original_size / 1024:.1f} KB")
        print(f"   최적화 크기: {optimized_size / 1024:.1f} KB")
        print(f"   절감율: {reduction:.1f}%")
        
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ PDF 최적화 실패: {e}")
        print(f"오류 메시지: {e.stderr.decode() if e.stderr else '알 수 없음'}")
        return False

def main():
    print("PDF 최적화 도구 시작...")
    
    # Ghostscript 설치 확인
    gs_path = check_ghostscript_installation()
    if not gs_path:
        return
    
    # Finder에서 선택된 파일 가져오기
    selected_files = get_selected_files_from_finder()
    
    # Finder에서 파일을 가져오지 못했다면 명령줄 인자 확인
    if not selected_files and len(sys.argv) > 1:
        print("Finder에서 파일을 가져오지 못했습니다. 명령줄 인자를 사용합니다.")
        selected_files = sys.argv[1:]
    
    if not selected_files:
        print("처리할 파일이 없습니다.")
        print("사용법: 1) Finder에서 PDF 파일을 선택한 후 이 스크립트 실행")
        print("      2) 또는 명령줄에서 파일 경로 지정: python script.py /path/to/file.pdf")
        return
    
    # 디버깅: 선택된 파일 출력
    print(f"선택된 파일 목록:")
    for idx, file_path in enumerate(selected_files, 1):
        print(f"  {idx}. {file_path}")
    
    # PDF 파일만 필터링
    pdf_files = [f for f in selected_files if f.lower().endswith('.pdf')]
    
    if not pdf_files:
        print("선택된 PDF 파일이 없습니다.")
        return
    
    # 각 PDF 파일을 처리
    successful = 0
    for pdf_file in pdf_files:
        # 원본 파일 경로에서 새 파일 이름 생성 (파일명_optimized.pdf)
        input_path = Path(pdf_file)
        output_dir = input_path.parent
        
        # 파일 이름 정리: 특수문자를 제거하여 안전한 파일명 생성
        sanitized_stem = sanitize_filename(input_path.stem)
        output_name = f"{sanitized_stem}_optimized.pdf"
        output_path = output_dir / output_name
        
        print(f"\n처리 중: {input_path}")
        print(f"출력 파일: {output_path}")
        
        if optimize_pdf(str(input_path), str(output_path), gs_path):
            successful += 1
    
    # 결과 요약
    print(f"\n총 {len(pdf_files)}개의 PDF 중 {successful}개 최적화 완료")

if __name__ == "__main__":
    main()
