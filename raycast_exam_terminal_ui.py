# Raycast 실기시험용 터미널 UI 프로그램 (Python)

import curses
import time
import json
import random
import os
import subprocess

def load_questions():
    try:
        with open('questions.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            all_questions = data['raycast_questions']
            selected_questions = random.sample(all_questions, min(5, len(all_questions)))
            return [f"{i+1}. {q}" for i, q in enumerate(selected_questions)]
    except FileNotFoundError:
        # 기본 문제들 (fallback)
        return [
            "1. Raycast 실행 후 'Raycast'를 Google에 검색하세요.",
            "2. Clipboard History에서 최근 복사 항목 3개 확인 후 붙여넣기.",
            "3. Chrome 새 창 열기 (New Window 커맨드 이용).",
            "4. Slack Extension 설치 및 채널에 메시지 전송.",
            "5. Confluence에서 최근 문서 1건 검색."
        ]

def draw_centered(stdscr, text, y_offset=0, attr=0):
    h, w = stdscr.getmaxyx()
    x = w//2 - len(text)//2
    y = h//2 + y_offset
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

def main(stdscr):
    curses.curs_set(0)
    stdscr.clear()
    stdscr.refresh()

    # 문제 로딩
    questions = load_questions()

    # 타이틀 화면
    draw_centered(stdscr, "⚡ Raycast 실기시험 (5분 제한)", -2, curses.A_BOLD)
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

        draw_centered(stdscr, "Raycast 실기시험", -h//2+2, curses.A_BOLD)
        
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
            
            question_text = prefix + q + time_suffix
            if idx == current_idx:
                stdscr.addstr(6 + idx, 4, question_text, curses.A_REVERSE)
            else:
                stdscr.addstr(6 + idx, 4, question_text)

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

if __name__ == '__main__':
    curses.wrapper(main)
