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
        try:
            # curses 초기화
            curses.curs_set(0)
            stdscr.clear()
            stdscr.refresh()
            
            # 터미널 크기 검사
            h, w = stdscr.getmaxyx()
            if h < 10 or w < 30:
                safe_addstr(stdscr, 0, 0, "터미널이 너무 작습니다.")
                stdscr.refresh()
                stdscr.getch()
                return False
        except curses.error:
            return False
        
        modes = [
            ("일반 모드", "개발자/비개발자 모든 문제 포함"),
            ("비개발자 모드", "비개발자에게 적합한 문제만 포함")
        ]
        
        current_idx = 0
        
        while True:
            try:
                stdscr.clear()
                h, w = stdscr.getmaxyx()
                
                # 터미널이 너무 작으면 경고 메시지
                if h < 12 or w < 40:
                    safe_addstr(stdscr, 0, 0, f"터미널이 너무 작습니다 ({w}x{h})")
                    safe_addstr(stdscr, 1, 0, "최소 40x12 필요")
                    stdscr.refresh()
                    time.sleep(0.5)
                    continue
                
                # 안전한 좌표 계산
                center_y = max(6, h // 2)
                title_y = max(2, center_y - 4)
                
                # 제목
                title = "⚡ Raycast 실기시험 모드 선택"
                title_display = title[:w-4]  # 텍스트 자르기
                x = max(2, (w - len(title_display)) // 2)
                safe_addstr(stdscr, title_y, x, title_display, curses.A_BOLD)
                
                # 모드 옵션들
                for idx, (mode_name, mode_desc) in enumerate(modes):
                    y_pos = max(title_y + 3 + idx * 3, 5 + idx * 3)
                    if y_pos + 1 >= h - 2:  # 화면을 벗어나면 스킵
                        break
                        
                    mode_text = f"{idx + 1}. {mode_name}"
                    desc_text = f"    {mode_desc}"
                    
                    # 텍스트 길이 제한
                    mode_text = mode_text[:w-8]
                    desc_text = desc_text[:w-8]
                    
                    try:
                        if idx == current_idx:
                            safe_addstr(stdscr, y_pos, 4, mode_text, curses.A_REVERSE)
                            safe_addstr(stdscr, y_pos + 1, 4, desc_text, curses.A_DIM)
                        else:
                            safe_addstr(stdscr, y_pos, 4, mode_text)
                            safe_addstr(stdscr, y_pos + 1, 4, desc_text, curses.A_DIM)
                    except curses.error:
                        pass
                
                # 안내 메시지
                info_text = "화살표 키로 선택, Enter로 확인"
                info_text = info_text[:w-4]
                x = max(2, (w - len(info_text)) // 2)
                info_y = min(h - 2, center_y + 6)
                safe_addstr(stdscr, info_y, x, info_text)
            except curses.error:
                return False
            
            try:
                stdscr.refresh()
                key = stdscr.getch()
            except curses.error:
                return False
            
            if key == curses.KEY_UP:
                current_idx = (current_idx - 1) % len(modes)
            elif key == curses.KEY_DOWN:
                current_idx = (current_idx + 1) % len(modes)
            elif key == ord('\n') or key == 10:
                return current_idx  # 0=일반모드, 1=비개발자모드
            elif key == ord('q') or key == ord('Q') or key == 27:  # ESC 키 추가
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
            if len(all_questions) == 0:
                print("⚠️  비개발자 모드에 적합한 문제가 엑셀 파일에 없습니다. JSON 파일을 시도합니다.")
            else:
                selected_questions = random.sample(all_questions, min(5, len(all_questions)))
                print(f"✓ 엑셀 파일에서 {len(selected_questions)}개 문제를 로드했습니다.")
                return selected_questions
        except Exception as e:
            print(f"⚠️  엑셀 파일 로드 실패: {e}")
            print("파일이 손상되었거나 호환되지 않는 형식일 수 있습니다. JSON 파일을 시도합니다.")
    
    # 2. JSON 파일 시도
    if os.path.exists('questions.json'):
        try:
            with open('questions.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                all_questions = data.get('raycast_questions', [])
                if not all_questions:
                    print("⚠️  JSON 파일에 'raycast_questions' 필드가 비어있거나 존재하지 않습니다.")
                else:
                    if non_developer_mode:
                        all_questions = [q for q in all_questions if is_non_developer_friendly(q)]
                    if len(all_questions) == 0:
                        print("⚠️  비개발자 모드에 적합한 문제가 JSON 파일에 없습니다. 기본 문제를 사용합니다.")
                    else:
                        selected_questions = random.sample(all_questions, min(5, len(all_questions)))
                        print(f"✓ JSON 파일에서 {len(selected_questions)}개 문제를 로드했습니다.")
                        return selected_questions
        except json.JSONDecodeError as e:
            print(f"⚠️  JSON 파일 파싱 오류: {e}")
            print("파일의 JSON 형식을 확인해주세요.")
        except Exception as e:
            print(f"⚠️  JSON 파일 로드 실패: {e}")
    else:
        print("파일을 찾을 수 없습니다: questions.xlsx, questions.json")
    
    # 3. 기본 문제들 (fallback)
    print("ℹ️  기본 예제 문제들을 사용합니다.")
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

def safe_addstr(stdscr, y, x, text, attr=0):
    """안전한 addstr 래퍼 함수"""
    try:
        h, w = stdscr.getmaxyx()
        if y < 0 or y >= h or x < 0 or x >= w:
            return False
        
        # 텍스트가 화면을 벗어나면 자르기
        max_len = w - x - 1
        if max_len > 0:
            display_text = text[:max_len]
            stdscr.addstr(y, x, display_text, attr)
        return True
    except curses.error:
        return False

def safe_move(stdscr, y, x):
    """안전한 move 래퍼 함수"""
    try:
        h, w = stdscr.getmaxyx()
        if y < 0 or y >= h or x < 0 or x >= w:
            return False
        stdscr.move(y, x)
        return True
    except curses.error:
        return False

def safe_clrtoeol(stdscr):
    """안전한 clrtoeol 래퍼 함수"""
    try:
        stdscr.clrtoeol()
        return True
    except curses.error:
        return False

def get_display_width(text):
    """한글과 영문을 고려한 실제 표시 폭 계산"""
    width = 0
    for char in text:
        if ord(char) > 0x1100:  # 한글 및 기타 전각 문자
            width += 2
        else:
            width += 1
    return width

def truncate_text(text, max_width):
    """텍스트를 최대 폭에 맞게 자르기"""
    if get_display_width(text) <= max_width:
        return text
    
    truncated = ""
    current_width = 0
    for char in text:
        char_width = 2 if ord(char) > 0x1100 else 1
        if current_width + char_width + 3 > max_width:  # "..." 공간 확보
            return truncated + "..."
        truncated += char
        current_width += char_width
    return truncated

def draw_centered(stdscr, text, y_offset=0, attr=0):
    try:
        h, w = stdscr.getmaxyx()
    except curses.error:
        return  # 터미널 정보를 가져올 수 없으면 반환
    
    # 터미널이 너무 작으면 그려지지 않음
    if h < 10 or w < 20:
        return
    
    # 텍스트가 화면보다 크면 자르기
    max_text_width = w - 4  # 양쪽 여백
    display_text = truncate_text(text, max_text_width)
    
    display_width = get_display_width(display_text)
    x = max(2, (w - display_width) // 2)
    y = h//2 + y_offset
    
    # 좌표 유효성 검사 강화
    if y < 0 or y >= h or x < 0 or x >= w:
        return
    if x + display_width > w:
        return
        
    try:
        stdscr.addstr(y, x, display_text, attr)
        return True
    except curses.error:
        return False  # 화면 경계를 벗어나면 무시

def format_time(seconds):
    minutes = seconds // 60
    seconds = seconds % 60
    return f"{minutes:02d}:{seconds:02d}"

def trigger_confetti():
    try:
        # 현재 실행 중인 터미널 앱 감지
        current_app = None
        try:
            # 현재 활성 앱 이름 가져오기
            get_current_app = '''
            tell application "System Events"
                return name of first application process whose frontmost is true
            end tell
            '''
            result = subprocess.run(['osascript', '-e', get_current_app], 
                                  capture_output=True, text=True, check=False)
            current_app = result.stdout.strip()
        except:
            pass
        
        # Raycast confetti 트리거
        subprocess.run(['open', 'raycast://confetti'], check=False)
        
        # 약간의 지연 후 원래 앱으로 포커스 복원
        time.sleep(0.5)  # confetti 효과가 시작될 시간 확보
        
        if current_app:
            # 원래 활성화된 앱으로 포커스 복원
            restore_focus = f'''
            tell application "{current_app}" to activate
            '''
            subprocess.run(['osascript', '-e', restore_focus], check=False)
        else:
            # 감지 실패 시 일반적인 터미널 앱들 시도
            terminal_apps = ['Terminal', 'iTerm2', 'iTerm', 'Warp', 'Kitty']
            for app in terminal_apps:
                try:
                    check_app = f'''
                    tell application "System Events"
                        return (name of processes) contains "{app}"
                    end tell
                    '''
                    result = subprocess.run(['osascript', '-e', check_app], 
                                          capture_output=True, text=True, check=False)
                    if result.stdout.strip() == 'true':
                        subprocess.run(['osascript', '-e', f'tell application "{app}" to activate'], 
                                     check=False)
                        break
                except:
                    continue
        
    except Exception:
        pass

def run_exam():
    try:
        # 모드 선택
        selected_mode = select_mode()
        
        if selected_mode is False:  # 사용자가 q를 눌러 종료
            return
        
        non_developer_mode = (selected_mode == 1)  # 1=비개발자모드, 0=일반모드
    except KeyboardInterrupt:
        print("\n프로그램이 사용자에 의해 종료되었습니다.")
        return
    except Exception as e:
        print(f"모드 선택 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return
    
    def exam_main(stdscr):
        try:
            h, w = stdscr.getmaxyx()
            
            if h < 15 or w < 50:
                safe_addstr(stdscr, 0, 0, f"터미널이 너무 작습니다. (현재: {w}x{h})")
                safe_addstr(stdscr, 1, 0, "최소 크기: 50x15")
                safe_addstr(stdscr, 2, 0, "터미널 크기를 늘리고 다시 시도해주세요.")
                safe_addstr(stdscr, 4, 0, "아무 키나 눌러서 종료...")
                stdscr.refresh()
                stdscr.getch()
                return
            
            curses.curs_set(0)
            stdscr.clear()
            stdscr.refresh()
        except curses.error as e:
            print(f"curses 초기화 오류: {e}")
            return

        # 문제 로딩
        questions = load_questions(non_developer_mode)
        
        if not questions:
            stdscr.clear()
            safe_addstr(stdscr, h//2-1, 2, "❌ 선택한 모드에 적합한 문제가 없습니다!", curses.A_BOLD)
            safe_addstr(stdscr, h//2, 2, "비개발자 모드에서 일반 모드로 전환하거나")
            safe_addstr(stdscr, h//2+1, 2, "questions.json 또는 questions.xlsx 파일을 추가해주세요.")
            safe_addstr(stdscr, h//2+3, 2, "아무 키나 눌러서 종료하세요.")
            stdscr.refresh()
            stdscr.getch()
            return

        # 타이틀 화메
        try:
            h, w = stdscr.getmaxyx()
            mode_text = "비개발자 모드" if non_developer_mode else "일반 모드"
            
            # 중앙 정렬된 타이틀 화면 표시
            title_y = max(2, h//4)
            
            # 각 텍스트를 중앙 정렬
            title_text = "⚡ Raycast 실기시험 (5분 제한)"
            mode_line = f"모드: {mode_text}"
            questions_line = f"랜덤 선택된 {len(questions)}개 문제"
            controls1 = "화살표 키로 항목을 이동하고 Enter로 확인"
            controls2 = "Q 키로 시험 종료"
            start_text = "아무 키나 눌러서 시작..."
            
            safe_addstr(stdscr, title_y, max(0, (w - len(title_text)) // 2), title_text, curses.A_BOLD)
            safe_addstr(stdscr, title_y + 1, max(0, (w - len(mode_line)) // 2), mode_line)
            safe_addstr(stdscr, title_y + 2, max(0, (w - len(questions_line)) // 2), questions_line)
            safe_addstr(stdscr, title_y + 4, max(0, (w - len(controls1)) // 2), controls1)
            safe_addstr(stdscr, title_y + 5, max(0, (w - len(controls2)) // 2), controls2)
            safe_addstr(stdscr, title_y + 7, max(0, (w - len(start_text)) // 2), start_text)
            stdscr.refresh()
            stdscr.getch()
        except curses.error:
            return  # 타이틀 화면에서 오류 발생 시 종료

        current_idx = 0
        completed = [False]*len(questions)
        completion_times = [0]*len(questions)
        start_time = time.time()
        exam_duration = 5 * 60
        last_remaining_time = -1
        last_completed_count = -1
        last_current_idx = -1
        need_full_redraw = True

        stdscr.nodelay(True)

        while True:
            try:
                h, w = stdscr.getmaxyx()
                
                # 터미널 크기가 다시 너무 작아진 경우 처리
                if h < 15 or w < 50:
                    stdscr.clear()
                    safe_addstr(stdscr, max(0, h//2), max(0, w//2-15), "터미널을 더 크게 해주세요")
                    stdscr.refresh()
                    time.sleep(0.5)
                    continue
                    
            except curses.error:
                break  # 터미널 정보를 가져올 수 없으면 종료
            
            # 초기화 또는 터미널 크기 변경 시에만 전체 다시 그리기
            if need_full_redraw:
                try:
                    stdscr.clear()
                    need_full_redraw = False
                except curses.error:
                    break

            elapsed_time = time.time() - start_time
            remaining_time = max(0, exam_duration - elapsed_time)
            completed_count = sum(completed)
            
            if remaining_time <= 0:
                break

            # 헤더 업데이트 (시간이나 진행상황이 변경되었을 때만)
            if int(remaining_time) != last_remaining_time or completed_count != last_completed_count or need_full_redraw:
                mode_text = "비개발자 모드" if non_developer_mode else "일반 모드"
                
                # 헤더 영역만 선택적으로 지우기 - 문제 영역은 보호
                # 헤더는 상단 5줄만 지우기 (y=0~4)
                for i in range(5):
                    if i >= 0 and i < h and i < 6:  # 문제 시작 지점(y=6) 전까지만
                        try:
                            stdscr.move(i, 0)
                            stdscr.clrtoeol()
                        except curses.error:
                            pass
                
                # 헤더 정보를 상단 고정 위치에 표시
                try:
                    stdscr.addstr(0, 2, f"⚡ Raycast 실기시험 ({mode_text})", curses.A_BOLD)
                    
                    time_color = curses.A_NORMAL
                    if remaining_time <= 60:
                        time_color = curses.A_BLINK
                    
                    time_text = f"남은 시간: {format_time(int(remaining_time))}"
                    progress_text = f"진행 상황: {completed_count} / {len(questions)}"
                    
                    stdscr.addstr(1, 2, time_text, time_color)
                    stdscr.addstr(2, 2, progress_text)
                    stdscr.addstr(3, 2, "─" * min(50, w-4))  # 구분선
                except curses.error:
                    pass  # 화면 경계 오류 무시
                
                last_remaining_time = int(remaining_time)
                last_completed_count = completed_count

            # 문제 리스트 업데이트 (현재 선택이나 완료 상태가 변경되었을 때만)
            if current_idx != last_current_idx or completed_count != last_completed_count or need_full_redraw:
                for idx, q in enumerate(questions):
                    prefix = "[✓] " if completed[idx] else "[ ] "
                    time_suffix = ""
                    if completed[idx]:
                        time_suffix = f" ({format_time(int(completion_times[idx]))})"
                    
                    # 화면 크기 확인
                    if h < 20:  # 터미널이 너무 작으면 스킵
                        continue
                        
                    # 첫 번째 줄: title, difficulty, estimated_time, category
                    title_line = f"{prefix}{idx+1}. {q['title']} [{q['difficulty']}] ({q['estimated_time']}) - {q['category']}{time_suffix}"
                    # 두 번째 줄: description
                    description_line = f"    {q['description']}"
                    
                    # 텍스트 길이 제한
                    max_line_width = w - 8  # 좌우 여백
                    title_line = truncate_text(title_line, max_line_width)
                    description_line = truncate_text(description_line, max_line_width)
                    
                    y_pos = 6 + idx * 3  # 각 문제마다 3줄 간격
                    
                    # 화면을 벗어나면 표시하지 않음
                    if y_pos >= h - 2:
                        break
                    
                    if idx == current_idx:
                        safe_addstr(stdscr, y_pos, 4, title_line, curses.A_REVERSE)
                        if y_pos + 1 < h - 1:
                            safe_addstr(stdscr, y_pos + 1, 4, description_line, curses.A_DIM)
                    else:
                        safe_addstr(stdscr, y_pos, 4, title_line)
                        if y_pos + 1 < h - 1:
                            safe_addstr(stdscr, y_pos + 1, 4, description_line, curses.A_DIM)
                
                last_current_idx = current_idx

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
            time.sleep(0.05)  # 반응성 개선을 위해 단축

        # 종료 메시지
        try:
            stdscr.clear()
            stdscr.nodelay(False)
        except curses.error:
            pass  # 종료 시 오류 무시
        
        final_time = time.time() - start_time
        completed_count = sum(completed)
        all_completed = all(completed)
        
        # 안전한 고정 위치에 결과 표시
        try:
            h, w = stdscr.getmaxyx()
            result_y = max(2, h//3)
            
            if remaining_time <= 0:
                safe_addstr(stdscr, result_y, 2, "⏰ 시간이 종료되었습니다!", curses.A_BOLD)
            elif all_completed:
                safe_addstr(stdscr, result_y, 2, "🎉 축하합니다! 모든 문제를 완료했습니다!", curses.A_BOLD)
                # Confetti 실행
                trigger_confetti()
            else:
                safe_addstr(stdscr, result_y, 2, "✅ 실기시험을 종료합니다!", curses.A_BOLD)
            
            safe_addstr(stdscr, result_y + 2, 2, f"완료한 문제: {completed_count} / {len(questions)}")
            safe_addstr(stdscr, result_y + 3, 2, f"소요 시간: {format_time(int(final_time))}")
            safe_addstr(stdscr, result_y + 5, 2, "아무 키나 눌러서 종료하세요.")
        except curses.error:
            pass
        
        stdscr.refresh()
        stdscr.getch()
    
    try:
        # curses wrapper를 사용하여 안전하게 실행
        curses.wrapper(exam_main)
    except KeyboardInterrupt:
        print("\n프로그램이 사용자에 의해 종료되었습니다.")
    except curses.error as e:
        print(f"curses 라이브러리 오류: {e}")
        print("터미널 크기를 확인하고 다시 시도해주세요. (최소: 50x15)")
        import traceback
        traceback.print_exc()
    except Exception as e:
        print(f"프로그램 실행 중 예상치 못한 오류: {e}")
        print("터미널 환경을 확인하거나 Python 버전을 확인해주세요.")
        import traceback
        traceback.print_exc()
    finally:
        # 프로그램 종료 시 정리
        try:
            curses.endwin()
        except:
            pass

if __name__ == '__main__':
    run_exam()