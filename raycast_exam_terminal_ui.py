# Raycast 실기시험용 터미널 UI 프로그램 (Python)

import curses
import time
import json
import random
import os
import subprocess
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

def is_non_developer_friendly(question):
    developer_categories = [
        "개발 도구", "Extension 활용", "시스템 제어", "시스템 모니터링", 
        "시스템 관리", "시스템 디버깅", "시스템 분석", "시스템 최적화",
        "네트워크 도구", "보안 도구", "보안 설정", "설정 관리",
        "데이터 도구", "미디어 도구", "학습 도구", "AI 도구", "웹 도구"
    ]
    
    developer_keywords = [
        "extension", "api", "ssh", "docker", "git", "github", "xcode", "simulator",
        "database", "sql", "json", "regex", "hash", "uuid", "base64", "csv",
        "markdown", "code", "script", "terminal", "brew", "port", "dns",
        "firewall", "cpu", "memory", "disk", "network", "ip", "url", "http"
    ]
    
    # 카테고리 체크
    if question.get('category', '') in developer_categories:
        return False
    
    # 제목과 설명에서 개발자 키워드 체크  
    title = question.get('title', '').lower()
    description = question.get('description', '').lower()
    
    for keyword in developer_keywords:
        if keyword in title or keyword in description:
            return False
    
    return True

def select_mode():
    """모드 선택 함수"""
    import curses
    
    def mode_selection_screen(stdscr):
        curses.curs_set(0)
        stdscr.clear()
        
        modes = [
            ("일반 모드", "개발자/비개발자 모든 문제 포함"),
            ("비개발자 모드", "비개발자에게 적합한 문제만 포함")
        ]
        
        current_idx = 0
        
        while True:
            stdscr.clear()
            h, w = stdscr.getmaxyx()
            
            # 제목
            title = "⚡ Raycast 실기시험 모드 선택"
            x = max(0, (w - len(title)) // 2)
            stdscr.addstr(h//2 - 4, x, title, curses.A_BOLD)
            
            # 모드 옵션들
            for idx, (mode_name, mode_desc) in enumerate(modes):
                y_pos = h//2 - 1 + idx * 2
                mode_text = f"{idx + 1}. {mode_name}"
                desc_text = f"    {mode_desc}"
                
                if idx == current_idx:
                    stdscr.addstr(y_pos, 4, mode_text, curses.A_REVERSE)
                    stdscr.addstr(y_pos + 1, 4, desc_text, curses.A_DIM)
                else:
                    stdscr.addstr(y_pos, 4, mode_text)
                    stdscr.addstr(y_pos + 1, 4, desc_text, curses.A_DIM)
            
            # 안내 메시지
            info_text = "화살표 키로 선택, Enter로 확인"
            x = max(0, (w - len(info_text)) // 2)
            stdscr.addstr(h//2 + 4, x, info_text)
            
            stdscr.refresh()
            
            key = stdscr.getch()
            
            if key == curses.KEY_UP:
                current_idx = (current_idx - 1) % len(modes)
            elif key == curses.KEY_DOWN:
                current_idx = (current_idx + 1) % len(modes)
            elif key == ord('\n') or key == 10:
                return current_idx == 1  # True면 비개발자 모드
            elif key == ord('q') or key == ord('Q'):
                return False
    
    return curses.wrapper(mode_selection_screen)

def load_questions(non_developer_mode=False):
    # 1. 엑셀 파일 우선 시도
    if PANDAS_AVAILABLE and os.path.exists('questions.xlsx'):
        try:
            df = pd.read_excel('questions.xlsx', engine='openpyxl')
            all_questions = df.to_dict('records')
            if non_developer_mode:
                all_questions = [q for q in all_questions if is_non_developer_friendly(q)]
            selected_questions = random.sample(all_questions, min(5, len(all_questions)))
            return selected_questions
        except Exception as e:
            print(f"엑셀 파일 로드 실패: {e}")
    
    # 2. JSON 파일 시도
    try:
        with open('questions.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            all_questions = data['raycast_questions']
            if non_developer_mode:
                all_questions = [q for q in all_questions if is_non_developer_friendly(q)]
            selected_questions = random.sample(all_questions, min(5, len(all_questions)))
            return selected_questions
    except FileNotFoundError:
        pass
    
    # 3. 기본 문제들 (fallback)
    base_questions = [
            {
                "id": 1,
                "title": "Raycast 실행 후 'Raycast'를 Google에 검색하세요.",
                "description": "Raycast의 기본 검색 기능을 사용하여 Google에서 'Raycast'를 검색합니다.",
                "difficulty": "쉬움",
                "estimated_time": "30초",
                "category": "기본 검색"
            },
            {
                "id": 2,
                "title": "Clipboard History에서 최근 복사 항목 3개 확인 후 붙여넣기.",
                "description": "Raycast의 클립보드 히스토리 기능을 사용하여 최근에 복사한 항목들을 확인하고 선택하여 붙여넣습니다.",
                "difficulty": "쉬움",
                "estimated_time": "45초",
                "category": "클립보드 관리"
            },
            {
                "id": 3,
                "title": "Chrome 새 창 열기 (New Window 커맨드 이용).",
                "description": "Raycast를 통해 Google Chrome의 새 창을 열기 위한 커맨드를 사용합니다.",
                "difficulty": "쉬움",
                "estimated_time": "30초",
                "category": "앱 통합"
            },
            {
                "id": 4,
                "title": "Slack Extension 설치 및 채널에 메시지 전송.",
                "description": "Raycast Store에서 Slack Extension을 찾아 설치하고, 계정을 연동한 후 채널에 메시지를 전송합니다.",
                "difficulty": "어려움",
                "estimated_time": "2분",
                "category": "Extension 활용"
            },
            {
                "id": 5,
                "title": "Confluence에서 최근 문서 1건 검색.",
                "description": "Confluence Extension을 사용하여 최근 문서를 검색하고 열어봅니다.",
                "difficulty": "보통",
                "estimated_time": "1분",
                "category": "Extension 활용"
            }
        ]
    
    if non_developer_mode:
        base_questions = [q for q in base_questions if is_non_developer_friendly(q)]
    
    return base_questions

def draw_centered(stdscr, text, y_offset=0, attr=0):
    h, w = stdscr.getmaxyx()
    # 간단한 문자 길이 기반 중앙 정렬
    text_length = len(text)
    x = max(0, (w - text_length) // 2)
    y = h//2 + y_offset
    if y >= 0 and y < h and x + text_length <= w:
        stdscr.addstr(y, x, text, attr)

def format_time(seconds):
    minutes = seconds // 60
    seconds = seconds % 60
    return f"{minutes:02d}:{seconds:02d}"

def trigger_confetti():
    try:
        # Raycast confetti 트리거
        subprocess.run(['open', 'raycast://confetti'], check=False)
    except Exception:
        pass

def run_exam():
    # 모드 선택
    non_developer_mode = select_mode()
    
    def exam_main(stdscr):
        curses.curs_set(0)
        stdscr.clear()
        stdscr.refresh()

        # 문제 로딩
        questions = load_questions(non_developer_mode)
        
        if not questions:
            draw_centered(stdscr, "❌ 선택한 모드에 적합한 문제가 없습니다!", 0, curses.A_BOLD)
            draw_centered(stdscr, "아무 키나 눌러서 종료하세요.", 2)
            stdscr.refresh()
            stdscr.getch()
            return

        # 타이틀 화면
        mode_text = "비개발자 모드" if non_developer_mode else "일반 모드"
        draw_centered(stdscr, "⚡ Raycast 실기시험 (5분 제한)", -3, curses.A_BOLD)
        draw_centered(stdscr, f"모드: {mode_text}", -2)
        draw_centered(stdscr, f"랜덤 선택된 {len(questions)}개 문제", -1)
        draw_centered(stdscr, "화살표 키로 항목을 이동하고 Enter로 확인", 0)
        draw_centered(stdscr, "Q 키로 시험 종료", 2)
        stdscr.getch()

        current_idx = 0
        completed = [False]*len(questions)
        completion_times = [0]*len(questions)
        start_time = time.time()
        exam_duration = 5 * 60

        stdscr.nodelay(True)

        while True:
            stdscr.clear()
            h, w = stdscr.getmaxyx()

            elapsed_time = time.time() - start_time
            remaining_time = max(0, exam_duration - elapsed_time)
            
            if remaining_time <= 0:
                break

            mode_text = "비개발자 모드" if non_developer_mode else "일반 모드"
            draw_centered(stdscr, f"⚡ Raycast 실기시험 ({mode_text})", -h//2+2, curses.A_BOLD)
            
            time_color = curses.A_NORMAL
            if remaining_time <= 60:
                time_color = curses.A_BLINK
            
            draw_centered(stdscr, f"남은 시간: {format_time(int(remaining_time))}", -h//2+3, time_color)
            draw_centered(stdscr, f"진행 상황: {sum(completed)} / {len(questions)}", -h//2+4)

            for idx, q in enumerate(questions):
                prefix = "[✓] " if completed[idx] else "[ ] "
                time_suffix = ""
                if completed[idx]:
                    time_suffix = f" ({format_time(int(completion_times[idx]))})"
                
                # 첫 번째 줄: title, difficulty, estimated_time, category
                title_line = f"{prefix}{idx+1}. {q['title']} [{q['difficulty']}] ({q['estimated_time']}) - {q['category']}{time_suffix}"
                # 두 번째 줄: description
                description_line = f"    {q['description']}"
                
                y_pos = 6 + idx * 3  # 각 문제마다 3줄 간격
                
                if idx == current_idx:
                    stdscr.addstr(y_pos, 4, title_line, curses.A_REVERSE)
                    stdscr.addstr(y_pos + 1, 4, description_line, curses.A_DIM)
                else:
                    stdscr.addstr(y_pos, 4, title_line)
                    stdscr.addstr(y_pos + 1, 4, description_line, curses.A_DIM)

            try:
                key = stdscr.getch()
            except:
                key = -1

            if key == curses.KEY_UP:
                current_idx = (current_idx - 1) % len(questions)
            elif key == curses.KEY_DOWN:
                current_idx = (current_idx + 1) % len(questions)
            elif key == ord('q') or key == ord('Q'):
                break
            elif key == ord('\n') or key == 10:
                if not completed[current_idx]:
                    completed[current_idx] = True
                    completion_times[current_idx] = time.time() - start_time
                    if all(completed):
                        break
                    current_idx = (current_idx + 1) % len(questions)

            stdscr.refresh()
            time.sleep(0.1)

        # 종료 메시지
        stdscr.clear()
        stdscr.nodelay(False)
        
        final_time = time.time() - start_time
        completed_count = sum(completed)
        all_completed = all(completed)
        
        if remaining_time <= 0:
            draw_centered(stdscr, "⏰ 시간이 종료되었습니다!", -1, curses.A_BOLD)
        elif all_completed:
            draw_centered(stdscr, "🎉 축하합니다! 모든 문제를 완료했습니다!", -1, curses.A_BOLD)
            # Confetti 실행
            trigger_confetti()
        else:
            draw_centered(stdscr, "✅ 실기시험을 종료합니다!", -1, curses.A_BOLD)
        
        draw_centered(stdscr, f"완료한 문제: {completed_count} / {len(questions)}", 0)
        draw_centered(stdscr, f"소요 시간: {format_time(int(final_time))}", 1)
        draw_centered(stdscr, "아무 키나 눌러서 종료하세요.", 3)
        
        stdscr.refresh()
        stdscr.getch()
    
    curses.wrapper(exam_main)

if __name__ == '__main__':
    run_exam()