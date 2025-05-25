# Raycast 실기시험 도구

Raycast 기능을 연습할 수 있는 터미널 기반 실기시험 도구입니다. 5분 제한시간 안에 랜덤하게 선택된 문제들을 해결하세요.

## 🚀 기능

- **타이머 기반 실기시험**: 5분 제한시간으로 실전 같은 연습
- **랜덤 문제 선택**: 매번 다른 문제 조합으로 연습
- **진행 상황 추적**: 실시간 완료 상태 및 소요 시간 표시
- **다양한 데이터 형식 지원**: JSON, Excel 파일 모두 지원
- **상세한 문제 정보**: 난이도, 예상 소요시간, 카테고리, 단계별 설명 포함

## 📋 문제 카테고리

- **기본 검색**: Google 검색, 파일 검색 등
- **클립보드 관리**: 히스토리 관리 및 활용
- **앱 통합**: Chrome, VS Code 등 앱 연동
- **Extension 활용**: Slack, Jira, Confluence 등
- **시스템 제어**: 환경설정, 네트워크 관리
- **개발 도구**: 터미널, 경로 복사 등
- **생산성**: Calendar, Notes 등
- **유틸리티**: 스크린샷, Color Picker 등
- **윈도우 관리**: 화면 분할 및 정렬
- **파일 관리**: Finder, Applications 폴더
- **시스템 모니터링**: CPU, 메모리 상태 확인
- **디자인 도구**: 색상 추출 등

## 🔧 설치 및 실행

### 필수 요구사항
```bash
# Python 3.6+ 필요
python --version

# 엑셀 지원을 위한 라이브러리 설치 (선택사항)
pip install pandas openpyxl
```

### 실행
```bash
# 터미널 UI 실행
python raycast_exam_terminal_ui.py

# 엑셀 유틸리티 실행 (JSON ↔ Excel 변환)
python excel_utils.py
```

## 📊 데이터 관리

### 지원 파일 형식
1. **questions.xlsx** (우선순위 1) - Excel 파일
2. **questions.json** (우선순위 2) - JSON 파일
3. **내장 기본 데이터** (fallback)

### 데이터 구조
```json
{
  "raycast_questions": [
    {
      "id": 1,
      "title": "문제 제목",
      "description": "상세 설명",
      "difficulty": "쉬움|보통|어려움",
      "estimated_time": "예상 소요시간",
      "category": "카테고리",
      "steps": ["단계1", "단계2", ...]
    }
  ]
}
```

### Excel ↔ JSON 변환
```bash
# JSON을 Excel로 변환
python -c "from excel_utils import json_to_excel; json_to_excel()"

# Excel을 JSON으로 변환
python -c "from excel_utils import excel_to_json; excel_to_json()"
```

## 🎮 사용 방법

### 터미널 UI 조작
- **↑/↓ 화살표**: 문제 선택
- **Enter**: 문제 완료 표시
- **Q**: 시험 종료

### 화면 구성
```
⚡ Raycast 실기시험 (5분 제한)
남은 시간: 04:32
진행 상황: 2 / 5

[ ] 1. 문제 제목 [난이도] (예상시간) - 카테고리
    상세 설명과 수행 방법

[✓] 2. 완료된 문제 [쉬움] (30초) - 기본 검색 (00:25)
    완료 시간이 괄호 안에 표시됩니다
```

## 📁 파일 구조

```
raycast_exam/
├── README.md                     # 이 파일
├── CLAUDE.md                     # Claude Code 지침서
├── raycast_exam_terminal_ui.py   # 메인 터미널 UI
├── excel_utils.py                # Excel 유틸리티
├── questions.json                # JSON 문제 데이터
├── questions.xlsx                # Excel 문제 데이터
├── show_review.sh                # 리뷰 관리 스크립트
└── reviews/                      # 리뷰 파일 저장소
```

## 🏆 완료 시 기능

- **전체 완료**: Raycast Confetti 효과 실행
- **완료 통계**: 완료한 문제 수 및 총 소요 시간 표시
- **개별 기록**: 각 문제별 완료 시간 기록

## 💡 팁

1. **Excel 편집**: `questions.xlsx`를 Excel에서 직접 편집하여 문제 추가/수정
2. **난이도 조절**: 어려운 문제를 제거하거나 쉬운 문제를 추가하여 맞춤 연습
3. **카테고리별 연습**: 특정 카테고리 문제만 필터링하여 집중 연습
4. **시간 조절**: 필요시 `exam_duration` 값을 수정하여 시간 변경

## 🔍 문제 해결

### 라이브러리 오류
```bash
# pandas/openpyxl 설치 오류 시
pip install --upgrade pip
pip install pandas openpyxl
```

### 파일 찾을 수 없음
- `questions.json` 또는 `questions.xlsx` 파일이 같은 디렉토리에 있는지 확인
- 파일이 없어도 내장 기본 문제로 실행 가능

### 터미널 크기 오류
- 터미널 창을 충분히 크게 조정
- 최소 권장 크기: 80x24

## 📄 라이선스

이 프로젝트는 개인 학습 및 연습 목적으로 만들어졌습니다.