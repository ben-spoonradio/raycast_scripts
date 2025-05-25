# Raycast 실기시험용 터미널 UI 프로그램 (Python)

import curses
import time

questions = [
    "1. Raycast 실행 후 'Raycast'를 Google에 검색하세요.",
    "2. Clipboard History에서 최근 복사 항목 3개 확인 후 붙여넣기.",
    "3. Chrome 새 창 열기 (New Window 커맨드 이용).",
    "4. Slack Extension 설치 및 채널에 메시지 전송.",
    "5. Confluence에서 최근 문서 1건 검색.",
    "6. Jira Extension으로 내 할당 이슈 1건 검색."
]

def draw_centered(stdscr, text, y_offset=0, attr=0):
    h, w = stdscr.getmaxyx()
    x = w//2 - len(text)//2
    y = h//2 + y_offset
    stdscr.addstr(y, x, text, attr)

def main(stdscr):
    curses.curs_set(0)
    stdscr.clear()
    stdscr.refresh()

    # 타이틀 화면
    draw_centered(stdscr, "⚡ Raycast 실기시험 (5분 제한)", -2, curses.A_BOLD)
    draw_centered(stdscr, "화살표 키로 항목을 이동하고 Enter로 확인", 0)
    draw_centered(stdscr, "Q 키로 시험 종료", 2)
    stdscr.getch()

    current_idx = 0
    completed = [False]*len(questions)

    while True:
        stdscr.clear()
        h, w = stdscr.getmaxyx()

        draw_centered(stdscr, "Raycast 실기시험", -h//2+2, curses.A_BOLD)
        draw_centered(stdscr, f"진행 상황: {sum(completed)} / {len(questions)}", -h//2+4)

        for idx, q in enumerate(questions):
            prefix = "[✓] " if completed[idx] else "[ ] "
            if idx == current_idx:
                stdscr.addstr(6 + idx, 4, prefix + q, curses.A_REVERSE)
            else:
                stdscr.addstr(6 + idx, 4, prefix + q)

        key = stdscr.getch()

        if key == curses.KEY_UP:
            current_idx = (current_idx - 1) % len(questions)
        elif key == curses.KEY_DOWN:
            current_idx = (current_idx + 1) % len(questions)
        elif key == ord('q') or key == ord('Q'):
            break
        elif key == ord('\n') or key == 10:
            completed[current_idx] = True

        stdscr.refresh()

    # 종료 메시지
    stdscr.clear()
    draw_centered(stdscr, "✅ 실기시험을 종료합니다. 수고하셨습니다!", 0, curses.A_BOLD)
    stdscr.refresh()
    time.sleep(2)

if __name__ == '__main__':
    curses.wrapper(main)
