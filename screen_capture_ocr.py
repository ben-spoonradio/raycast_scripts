#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Required parameters:
# @raycast.schemaVersion 1
# @raycast.title Screen Capture OCR
# @raycast.mode silent

# Optional parameters:
# @raycast.icon 📸
# @raycast.packageName Screen Tools
# @raycast.needsConfirmation false

# Documentation:
# @raycast.description Screen capture to PDF with OCR text extraction (uses screenshot or clipboard)
# @raycast.author moonbc
# @raycast.authorURL https://raycast.com/moonbc
"""
화면 캡쳐 → PDF 생성 → 미리보기 앱 실행 → OCR 텍스트 추출 자동화 스크립트

사용법:
    python3 screen_capture_ocr.py
    python3 screen_capture_ocr.py --region  # 영역 선택 캡쳐
    python3 screen_capture_ocr.py --window  # 윈도우 캡쳐
    python3 screen_capture_ocr.py --clipboard  # 클립보드에서 이미지 가져오기
"""

import os
import sys
import subprocess
import tempfile
import argparse
from datetime import datetime
import time
from pathlib import Path

# [확실] 필요한 라이브러리 설치 확인
try:
    from PIL import Image, ImageGrab
    import pytesseract
    import cv2
    import numpy as np
except ImportError as e:
    print(f"❌ 필요한 라이브러리가 설치되지 않았습니다: {e}")
    print("다음 명령으로 설치해주세요:")
    print("pip install pillow pytesseract opencv-python numpy")
    sys.exit(1)


class ScreenCaptureOCR:
    def __init__(self, output_dir="/Users/moonbc/source/vscode_labs/03_utilities"):
        self.output_dir = Path(output_dir)
        self.temp_dir = Path(tempfile.gettempdir())
        
        # [확실] Tesseract 경로 설정 (Homebrew 기본 설치 경로)
        if os.path.exists("/opt/homebrew/bin/tesseract"):
            pytesseract.pytesseract.tesseract_cmd = "/opt/homebrew/bin/tesseract"
        elif os.path.exists("/usr/local/bin/tesseract"):
            pytesseract.pytesseract.tesseract_cmd = "/usr/local/bin/tesseract"
        else:
            print("⚠️  Tesseract가 설치되지 않았습니다. 'brew install tesseract' 명령으로 설치해주세요.")

    def capture_screen_full(self) -> str:
        """전체 화면 캡쳐"""
        print("📸 전체 화면을 캡쳐합니다...")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        screenshot_path = self.temp_dir / f"screenshot_{timestamp}.png"
        
        # [확실] screencapture 명령 사용 (macOS 내장)
        result = subprocess.run([
            "screencapture", "-x", str(screenshot_path)
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✅ 스크린샷 저장: {screenshot_path}")
            return str(screenshot_path)
        else:
            raise Exception(f"스크린샷 캡쳐 실패: {result.stderr}")

    def hide_raycast(self):
        """Raycast 창 숨기기"""
        applescript = '''
        tell application "System Events"
            tell process "Raycast"
                set visible to false
            end tell
        end tell
        '''
        subprocess.run(["osascript", "-e", applescript], capture_output=True)

    def capture_screen_region(self) -> str:
        """영역 선택 캡쳐"""
        print("📸 Raycast 창을 숨기고 캡쳐할 영역을 선택해주세요...")
        
        # Raycast 창 숨기기
        self.hide_raycast()
        time.sleep(1)  # 창이 숨겨질 시간
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        screenshot_path = self.temp_dir / f"screenshot_region_{timestamp}.png"
        
        # [확실] -s 옵션으로 영역 선택 가능
        result = subprocess.run([
            "screencapture", "-s", str(screenshot_path)
        ], capture_output=True, text=True)
        
        if result.returncode == 0 and screenshot_path.exists():
            print(f"✅ 영역 스크린샷 저장: {screenshot_path}")
            return str(screenshot_path)
        else:
            raise Exception("영역 선택이 취소되었거나 캡쳐에 실패했습니다.")

    def capture_screen_window(self) -> str:
        """윈도우 캡쳐"""
        print("📸 캡쳐할 윈도우를 클릭해주세요...")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        screenshot_path = self.temp_dir / f"screenshot_window_{timestamp}.png"
        
        # [확실] -w 옵션으로 윈도우 선택 가능
        result = subprocess.run([
            "screencapture", "-w", str(screenshot_path)
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✅ 윈도우 스크린샷 저장: {screenshot_path}")
            return str(screenshot_path)
        else:
            raise Exception(f"윈도우 캡쳐 실패: {result.stderr}")

    def get_clipboard_image(self) -> str:
        """클립보드에서 이미지 가져오기"""
        print("📋 클립보드에서 이미지를 가져옵니다...")
        try:
            # [확실] PIL로 클립보드 이미지 접근
            image = ImageGrab.grabclipboard()
            if image is None:
                raise Exception("클립보드에 이미지가 없습니다.")
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_path = self.temp_dir / f"clipboard_image_{timestamp}.png"
            image.save(screenshot_path)
            
            print(f"✅ 클립보드 이미지 저장: {screenshot_path}")
            return str(screenshot_path)
        except Exception as e:
            raise Exception(f"클립보드 이미지 가져오기 실패: {e}")

    def image_to_pdf(self, image_path: str) -> str:
        """이미지를 PDF로 변환"""
        print("📄 PDF로 변환합니다...")
        
        # [확실] PIL을 사용한 PDF 변환
        image = Image.open(image_path)
        
        # RGB 모드로 변환 (PDF 저장을 위해 필요)
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        pdf_path = str(Path(image_path).with_suffix('.pdf'))
        image.save(pdf_path, "PDF", quality=95)
        
        print(f"✅ PDF 생성 완료: {pdf_path}")
        return pdf_path

    def open_with_preview(self, pdf_path: str):
        """미리보기 앱으로 PDF 열기"""
        print("👀 미리보기 앱으로 PDF를 엽니다...")
        
        # [확실] open 명령으로 미리보기 앱 실행
        result = subprocess.run([
            "open", "-a", "Preview", pdf_path
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ 미리보기 앱에서 PDF를 열었습니다.")
        else:
            print(f"⚠️  미리보기 앱 실행 중 오류: {result.stderr}")

    def preprocess_image_for_ocr(self, image_path: str) -> str:
        """OCR 정확도 향상을 위한 이미지 전처리"""
        print("🔧 OCR을 위한 이미지 전처리...")
        
        # [확실] OpenCV를 사용한 이미지 전처리
        img = cv2.imread(image_path)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # 노이즈 제거
        denoised = cv2.medianBlur(gray, 3)
        
        # 대비 향상 (CLAHE)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        enhanced = clahe.apply(denoised)
        
        # 이진화
        _, binary = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # 전처리된 이미지 저장
        preprocessed_path = str(Path(image_path).with_suffix('.preprocessed.png'))
        cv2.imwrite(preprocessed_path, binary)
        
        return preprocessed_path

    def extract_text_from_image(self, image_path: str) -> str:
        """이미지에서 텍스트 추출"""
        print("🔤 이미지에서 텍스트를 추출합니다...")
        
        try:
            # 이미지 전처리
            preprocessed_path = self.preprocess_image_for_ocr(image_path)
            
            # [확실] Tesseract를 사용한 OCR
            # 한국어와 영어를 동시에 인식
            text = pytesseract.image_to_string(
                Image.open(preprocessed_path), 
                lang='kor+eng',  # 한국어 + 영어
                config='--oem 3 --psm 6'  # 최적화된 설정
            )
            
            # 전처리 파일 정리
            os.remove(preprocessed_path)
            
            if text.strip():
                print("✅ 텍스트 추출 완료")
                return text.strip()
            else:
                return "텍스트를 찾을 수 없습니다."
                
        except Exception as e:
            print(f"❌ OCR 처리 중 오류: {e}")
            return f"OCR 오류: {e}"

    def save_extracted_text(self, text: str, original_filename: str) -> str:
        """추출된 텍스트를 파일로 저장"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        text_filename = f"extracted_text_{timestamp}.txt"
        text_path = self.output_dir / text_filename
        
        with open(text_path, 'w', encoding='utf-8') as f:
            f.write(f"원본 파일: {original_filename}\n")
            f.write(f"추출 시간: {datetime.now()}\n")
            f.write("-" * 50 + "\n\n")
            f.write(text)
        
        print(f"💾 추출된 텍스트 저장: {text_path}")
        return str(text_path)

    def cleanup_temp_files(self, *file_paths):
        """임시 파일 정리"""
        print("🧹 임시 파일을 정리합니다...")
        for file_path in file_paths:
            try:
                if file_path and os.path.exists(file_path):
                    os.remove(file_path)
                    print(f"🗑️  삭제: {file_path}")
            except Exception as e:
                print(f"⚠️  파일 삭제 실패 {file_path}: {e}")

    def run_full_process(self, capture_method: str = "full"):
        """전체 프로세스 실행"""
        temp_files = []
        
        try:
            print("🚀 화면 캡쳐 → PDF → OCR 프로세스를 시작합니다.\n")
            
            # 1. 화면 캡쳐
            if capture_method == "region":
                image_path = self.capture_screen_region()
            elif capture_method == "window":
                image_path = self.capture_screen_window()
            elif capture_method == "clipboard":
                image_path = self.get_clipboard_image()
            else:
                image_path = self.capture_screen_full()
            
            temp_files.append(image_path)
            
            # 2. PDF 변환
            pdf_path = self.image_to_pdf(image_path)
            temp_files.append(pdf_path)
            
            # 3. 미리보기 앱으로 열기
            self.open_with_preview(pdf_path)
            
            # 4. OCR 텍스트 추출
            extracted_text = self.extract_text_from_image(image_path)
            
            # 5. 텍스트 저장
            # text_file_path = self.save_extracted_text(
            #     extracted_text, 
            #     os.path.basename(pdf_path)
            # )
            
            # print("\n" + "="*60)
            # print("📋 추출된 텍스트 미리보기:")
            # print("="*60)
            # # 처음 500자만 미리보기
            # preview_text = extracted_text[:500] + ("..." if len(extracted_text) > 500 else "")
            # print(preview_text)
            # print("="*60)
            # print(f"📁 전체 텍스트 파일: {text_file_path}")
            print(f"📄 PDF 파일: {pdf_path}")
            
        except Exception as e:
            print(f"❌ 프로세스 실행 중 오류: {e}")
        finally:
            # [참고] 사용자가 PDF를 확인할 시간을 주기 위해 정리하지 않음
            # self.cleanup_temp_files(*temp_files)
            pass


def main():
    parser = argparse.ArgumentParser(
        description="화면 캡쳐 → PDF 생성 → 미리보기 실행 → OCR 텍스트 추출"
    )
    parser.add_argument(
        "--region", 
        action="store_true", 
        help="영역 선택 캡쳐"
    )
    parser.add_argument(
        "--window", 
        action="store_true", 
        help="윈도우 캡쳐"
    )
    parser.add_argument(
        "--clipboard", 
        action="store_true", 
        help="클립보드에서 이미지 가져오기"
    )
    
    args = parser.parse_args()
    
    # 캡쳐 방법 결정
    if args.region:
        capture_method = "region"
    elif args.window:
        capture_method = "window"
    elif args.clipboard:
        capture_method = "clipboard"
    else:
        # Raycast에서 사용할 때는 기본적으로 영역 선택 캡쳐
        capture_method = "region"
    
    # OCR 인스턴스 생성 및 실행
    ocr = ScreenCaptureOCR()
    ocr.run_full_process(capture_method)


if __name__ == "__main__":
    main()
