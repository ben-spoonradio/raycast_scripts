# AI 스터디 강의용 스크립트 실습 가이드

## 📋 실습 개요

이 실습 가이드는 다양한 Python 스크립트들을 통해 AI 도구 개발, 멀티미디어 처리, OCR, 유틸리티 개발 등을 학습하기 위한 자료입니다.

## 🛠️ 실습 환경 준비

### 1. Raycast 설치 및 설정

```bash
# Raycast 다운로드 및 설치
# https://www.raycast.com/ 에서 다운로드
```

**Raycast 스크립트 등록 방법**:
1. Raycast 실행 (⌘ + Space)
2. "Create Script Command" 검색 및 실행
3. 스크립트 경로 설정: 이 프로젝트 폴더 선택
4. 또는 Raycast 설정 → Extensions → Script Commands → Add Script Directory

### 2. 필수 도구 설치

```bash
# Homebrew 설치 (macOS)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Python 라이브러리 일괄 설치
pip install pandas openpyxl pyperclip openai-whisper anthropic pyaudio yt-dlp requests pytesseract pillow reportlab

# 시스템 도구 설치
brew install ffmpeg ghostscript bat tesseract tldr
```

### 3. Raycast 스크립트 헤더 이해

모든 Raycast 스크립트는 다음과 같은 헤더를 포함합니다:

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Required parameters:
# @raycast.schemaVersion 1
# @raycast.title [스크립트 제목]
# @raycast.mode fullOutput

# Optional parameters:
# @raycast.icon [이모지 아이콘]
# @raycast.packageName [패키지 그룹명]
# @raycast.needsConfirmation false

# Documentation:
# @raycast.description [상세 설명]
# @raycast.author [작성자]
# @raycast.authorURL [작성자 URL]
```

**헤더 파라미터 설명**:
- `schemaVersion`: Raycast API 버전 (현재 1)
- `title`: Raycast에서 표시될 명령어 이름
- `mode`: 출력 모드 (`fullOutput`, `compact`, `silent`)
- `icon`: 명령어 아이콘 (이모지)
- `packageName`: 그룹핑을 위한 패키지명
- `needsConfirmation`: 실행 전 확인 여부

## 📚 실습 모듈별 가이드

### 🎯 Module 1: Raycast 실기시험 도구 (raycast_exam_terminal_ui.py)

**학습 목표**: Python curses 라이브러리를 활용한 터미널 UI 개발

**주요 기능**:
- 5분 타이머 기반 실기시험 시뮬레이션
- 키보드 입력 처리 (화살표, Enter, Q)
- 실시간 진행 상황 추적
- JSON/Excel 데이터 처리

**실습 과정**:
```bash
# 1. 스크립트 실행
python raycast_exam_terminal_ui.py

# 2. 조작법 익히기
# ↑/↓: 문제 선택
# Enter: 완료 표시
# Q: 종료

# 3. 데이터 구조 이해
# questions.json 또는 questions.xlsx 파일 확인
```

**핵심 학습 포인트**:
- `curses` 라이브러리 사용법
- 실시간 타이머 구현
- 키보드 이벤트 처리
- JSON/Excel 데이터 읽기

---

### 📸 Module 2: 스크린 캡처 OCR (screen_capture_ocr.py) ⚡ Raycast 지원

**학습 목표**: 컴퓨터 비전과 OCR 기술 활용

**Raycast 헤더 정보**:
- **Title**: "Screen Capture OCR"
- **Icon**: 📸
- **Package**: "Screen Tools"
- **Mode**: fullOutput

**주요 기능**:
- 다양한 방식의 스크린 캡처 (전체/영역/윈도우/클립보드)
- Tesseract OCR을 통한 텍스트 추출
- PDF 자동 생성 및 미리보기

**실습 과정**:

**A. 터미널에서 직접 실행**:
```bash
# 1. 기본 전체 화면 캡처
python screen_capture_ocr.py

# 2. 영역 선택 캡처
python screen_capture_ocr.py --region

# 3. 특정 윈도우 캡처
python screen_capture_ocr.py --window

# 4. 클립보드 이미지 처리
python screen_capture_ocr.py --clipboard
```

**B. Raycast에서 실행**:
1. Raycast 실행 (⌘ + Space)
2. "Screen Capture OCR" 검색 및 실행
3. 자동으로 전체 화면 캡처 → OCR → PDF 생성

**핵심 학습 포인트**:
- PIL (Python Imaging Library) 사용법
- Tesseract OCR 연동
- AppleScript/osascript 활용
- PDF 생성 (reportlab)
- Raycast 통합 워크플로우

---

### 🎵 Module 3: 오디오 처리 도구들

#### A. Whisper 음성 인식 (whisper_with_speaker_diarization.py)

**학습 목표**: AI 음성 인식 기술 활용

```bash
# 오디오 파일 전사
python whisper_with_speaker_diarization.py audio_file.wav

# 다양한 모델 크기 테스트
# tiny, base, small, medium, large
```

#### B. TTS 변환 (KittenTTS.py) ⚡ Raycast 지원

**학습 목표**: 텍스트-음성 변환 기술

**Raycast 헤더 정보**:
- **Title**: "play clipboard text by kitten_tts"
- **Icon**: 🎵
- **Package**: "Audio Tools"

**실습 방법**:

**터미널 실행**:
```bash
# 클립보드 텍스트를 음성으로 변환
python KittenTTS.py
```

**Raycast 실행**:
1. 텍스트를 클립보드에 복사 (⌘ + C)
2. Raycast 실행 (⌘ + Space)
3. "play clipboard text" 검색 및 실행
4. 자동으로 클립보드 텍스트를 음성으로 재생

#### C. 오디오 형식 변환 (convert_wav_to_mp3.py) ⚡ Raycast 지원

**Raycast 헤더 정보**:
- **Title**: "Convert WAV to MP3 in Finder"
- **Icon**: 🎵
- **Package**: "Audio Tools"

**실습 방법**:

**터미널 실행**:
```bash
# WAV 파일을 MP3로 변환
python convert_wav_to_mp3.py
```

**Raycast 실행**:
1. Finder에서 WAV 파일 선택
2. Raycast 실행 (⌘ + Space)
3. "Convert WAV to MP3" 검색 및 실행
4. 선택한 파일들이 자동으로 MP3로 변환

**핵심 학습 포인트**:
- OpenAI Whisper API 사용
- 오디오 파일 처리 (pyaudio, wave)
- FFmpeg 연동
- 클립보드 활용 (pyperclip)
- Finder 통합 (AppleScript)

---

### 📺 Module 4: YouTube 다운로더 시리즈

**학습 목표**: 웹 스크래핑과 멀티미디어 다운로드

#### 실습 스크립트들:
- `youtube_all_downloader.py`: 비디오+오디오 통합 다운로드
- `youtube_audio_downloader.py`: 오디오만 추출
- `youtube_video_downloader.py`: 비디오만 다운로드

**실습 과정**:
```bash
# 1. 전체 다운로드 (비디오+오디오)
python youtube_all_downloader.py
# URL 입력 후 엔터

# 2. 오디오만 다운로드
python youtube_audio_downloader.py

# 3. 비디오만 다운로드  
python youtube_video_downloader.py
```

**핵심 학습 포인트**:
- yt-dlp 라이브러리 활용
- 동영상 포맷 변환
- FFmpeg 후처리
- 파일 시스템 조작

---

### ⌨️ Module 5: 타이핑 분석기 (typing_analyser.py)

**학습 목표**: 실시간 입력 처리와 성능 분석

**실습 과정**:
```bash
# 쉘 히스토리 기반 타이핑 연습
python typing_analyser.py
```

**주요 기능**:
- 쉘 히스토리에서 명령어 추출
- tldr 연동으로 명령어 설명 표시
- 실시간 타이핑 정확도 측정
- 색상 코딩된 피드백

**핵심 학습 포인트**:
- 터미널 원시 모드 (tty) 처리
- 실시간 키보드 입력 감지
- 문자열 비교 알고리즘
- ANSI 색상 코드 활용

---

### 📊 Module 6: 데이터 처리 도구들

#### A. Excel 유틸리티 (excel_utils.py)

```bash
# JSON을 Excel로 변환
python -c "from excel_utils import json_to_excel; json_to_excel()"

# Excel을 JSON으로 변환  
python -c "from excel_utils import excel_to_json; excel_to_json()"
```

#### B. PDF 최적화 도구들 ⚡ Raycast 지원

**B-1. PDF 최적화 (optimize_finder_pdfs.py)**

**Raycast 헤더 정보**:
- **Title**: "Optimize pdf in Finder"
- **Icon**: 📄
- **Package**: "PDF Tools"

**B-2. PDF 최대 압축 (max_compress_finder_pdfs.py)**

**Raycast 헤더 정보**:
- **Title**: "PDF Max Compression"
- **Icon**: 📄
- **Package**: "PDF Tools"

**실습 방법**:

**터미널 실행**:
```bash
# PDF 최적화
python optimize_finder_pdfs.py

# PDF 최대 압축
python max_compress_finder_pdfs.py
```

**Raycast 실행**:
1. Finder에서 PDF 파일(들) 선택
2. Raycast 실행 (⌘ + Space)
3. "Optimize pdf" 또는 "PDF Max Compression" 검색
4. 선택한 PDF 파일들이 자동으로 최적화됨
5. 원본 파일은 백업되고 최적화된 파일로 교체

**핵심 학습 포인트**:
- pandas DataFrame 조작
- Excel 파일 읽기/쓰기 (openpyxl)
- Ghostscript 연동
- AppleScript로 Finder 연동
- 파일 백업 및 교체 로직

---

### 🔧 Module 7: 시스템 유틸리티

#### 코드 리뷰 관리 (show_review.sh)

```bash
# 코드 리뷰 생성 및 표시
./show_review.sh
```

**주요 기능**:
- Git 정보 추출
- 타임스탬프 기반 파일명 생성
- bat을 통한 구문 강조
- Markdown 파일 관리

---

## 🎯 실습 시나리오

### 시나리오 1: 멀티미디어 처리 파이프라인 (Raycast 통합)

1. YouTube에서 강의 영상 다운로드
2. 오디오 추출 후 Whisper로 전사
3. 전사 결과를 TTS로 재생성 (⚡ Raycast)
4. 스크린 캡처로 시각 자료 OCR 처리 (⚡ Raycast)

**터미널 기반**:
```bash
# 1단계: 영상 다운로드
python youtube_audio_downloader.py

# 2단계: 음성 인식
python whisper_with_speaker_diarization.py downloaded_audio.mp3

# 3단계: 화면 캡처 및 OCR
python screen_capture_ocr.py --region

# 4단계: 텍스트 음성 변환
# 클립보드에 텍스트 복사 후
python KittenTTS.py
```

**Raycast 통합 워크플로우**:
1. 1-2단계는 터미널에서 실행
2. 전사 결과를 클립보드에 복사
3. Raycast → "play clipboard text" (TTS 실행)
4. Raycast → "Screen Capture OCR" (화면 캡처 및 OCR)

### 시나리오 2: 생산성 도구 개발 (Raycast 통합)

1. Raycast 시험 문제를 Excel로 관리
2. 타이핑 연습으로 실력 향상
3. PDF 문서 최적화로 저장공간 관리 (⚡ Raycast)

**터미널 기반**:
```bash
# 1단계: 데이터 변환
python excel_utils.py

# 2단계: 실기 연습
python raycast_exam_terminal_ui.py

# 3단계: 타이핑 연습
python typing_analyser.py

# 4단계: PDF 최적화
python optimize_finder_pdfs.py
```

**Raycast 통합 워크플로우**:
1. 1-3단계는 터미널에서 실행
2. Finder에서 PDF 파일 선택
3. Raycast → "Optimize pdf" (자동 최적화)

### 시나리오 3: Raycast 전용 워크플로우

**일반적인 업무 흐름에서 Raycast 활용**:

1. **문서 작업**: 
   - 화면 캡처 → OCR → 텍스트 추출
   - Raycast → "Screen Capture OCR"

2. **오디오 작업**:
   - 클립보드 텍스트 → 음성 변환
   - Raycast → "play clipboard text"
   
3. **파일 관리**:
   - PDF 최적화로 용량 절약
   - Raycast → "Optimize pdf" 또는 "PDF Max Compression"
   
4. **미디어 변환**:
   - WAV → MP3 변환
   - Raycast → "Convert WAV to MP3"

## 💡 실습 팁

### 1. 의존성 관리
```bash
# 가상환경 생성 권장
python -m venv venv
source venv/bin/activate

# 필요한 패키지만 선택 설치
pip install -r requirements.txt
```

### 2. Raycast 스크립트 관리
- **스크립트 경로**: Raycast 설정에서 스크립트 디렉토리 등록
- **권한 설정**: 스크립트 실행 권한 확인 (`chmod +x *.py`)
- **디버깅**: Raycast 로그 확인 (⌘ + K → "View Extension Logs")
- **새로고침**: 스크립트 수정 후 Raycast Extension 새로고침

### 3. 오류 처리
- **API 키 설정**: Anthropic, OpenAI 환경변수 설정
- **권한 문제**: macOS 보안 설정에서 접근성 권한 허용
- **패키지 충돌**: 가상환경 활용
- **Finder 통합**: AppleScript 실행 권한 확인

### 4. 성능 최적화
- **Whisper 모델 크기 조절**: tiny → base → small 순으로 테스트
- **PDF 압축 레벨 설정**: 용도에 따라 최적화/최대압축 선택
- **캐시 활용**: Whisper 모델 캐시로 중복 다운로드 방지
- **배치 처리**: 여러 파일 동시 처리로 효율성 증대

### 5. Raycast 활용 팁
- **키워드 검색**: 명령어 일부만 입력해도 검색 가능
- **즐겨찾기**: 자주 사용하는 스크립트는 ⌘ + K로 즐겨찾기 등록
- **단축키 설정**: 자주 사용하는 스크립트에 개별 단축키 할당
- **패키지 그룹핑**: packageName으로 관련 스크립트 그룹화

## 📈 학습 성과 측정

### 체크리스트
- [ ] curses UI 개발 이해
- [ ] OCR 파이프라인 구축
- [ ] 멀티미디어 처리 자동화
- [ ] API 연동 (Whisper, Anthropic)
- [ ] 파일 시스템 조작
- [ ] 실시간 입력 처리
- [ ] 데이터 형식 변환
- [ ] 시스템 스크립팅

### 추가 도전 과제

1. **커스텀 기능 추가**
   - Raycast 시험 문제 난이도별 필터링
   - OCR 결과 자동 번역 기능
   - YouTube 자막과 음성 인식 비교

2. **통합 워크플로우 개발**
   - 여러 스크립트를 연결하는 마스터 스크립트
   - 설정 파일 기반 자동화
   - 로그 및 결과 저장 시스템

3. **UI/UX 개선**
   - 웹 인터페이스 개발
   - 진행률 표시기 개선
   - 설정 관리 GUI

## 🔗 참고 자료

- **Raycast API**: https://developers.raycast.com/
- **OpenAI Whisper**: https://github.com/openai/whisper
- **Python Curses**: https://docs.python.org/3/library/curses.html
- **Tesseract OCR**: https://github.com/tesseract-ocr/tesseract
- **yt-dlp**: https://github.com/yt-dlp/yt-dlp

이 실습 가이드를 통해 Python을 활용한 다양한 도구 개발 경험을 쌓고, AI 기술을 실무에 적용하는 능력을 기를 수 있습니다.