import sys
import termios
import time
import tty
import random
import subprocess
import os
import re

def read_char():
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(sys.stdin.fileno())
        char = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return char

def get_shell_history():
    """shell history에서 명령어들을 가져오는 함수"""
    try:
        # zsh history 파일 경로
        history_file = os.path.expanduser("~/.zsh_history")
        
        # history 파일이 존재하는지 확인
        if os.path.exists(history_file):
            with open(history_file, 'r', encoding='utf-8', errors='ignore') as f:
                commands = f.readlines()
        else:
            # history 명령어를 직접 실행
            result = subprocess.run(['history'], shell=True, capture_output=True, text=True)
            commands = result.stdout.split('\n')
        
        # 빈 줄과 중복 제거, 적절한 길이의 명령어만 선택
        filtered_commands = []
        for cmd in commands:
            cmd = cmd.strip()
            
            # zsh history 형식에서 타임스탬프 제거
            # 형식: ": 1587750465:0;command" -> "command"
            if cmd.startswith(': '):
                # 정규식을 사용하여 타임스탬프 패턴 제거
                match = re.match(r'^: \d+:\d+;(.*)$', cmd)
                if match:
                    cmd = match.group(1)
            
            # history 명령어의 번호 제거 (예: "  123  ls -la" -> "ls -la")
            elif cmd and len(cmd.split()) > 1 and cmd.split()[0].isdigit():
                cmd = ' '.join(cmd.split()[1:])
            
            # 적절한 길이의 명령어만 선택
            if cmd and 10 <= len(cmd) <= 80:
                filtered_commands.append(cmd)
        
        # 중복 제거
        unique_commands = list(dict.fromkeys(filtered_commands))
        
        return unique_commands if unique_commands else get_fallback_commands()
        
    except Exception as e:
        print(f"History를 읽는 중 오류 발생: {e}")
        return get_fallback_commands()

def get_fallback_commands():
    """history를 읽을 수 없을 때 사용할 기본 명령어들"""
    return [
        "ls -la /home/user",
        "cd /var/log && tail -f syslog",
        "grep -r 'error' /var/log/",
        "find . -name '*.py' -type f",
        "ps aux | grep python",
        "netstat -tulpn | grep :80",
        "sudo apt update && sudo apt upgrade",
        "docker ps -a --format 'table {{.Names}}\t{{.Status}}'",
        "git log --oneline --graph --decorate --all",
        "chmod 755 script.sh && ./script.sh"
    ]

def typed_vs_expected(text):
    for expected in text:
        typed = read_char()
        yield (typed, expected)

def color_char(typed, expected):
    color = '\033[92m' if typed == expected else '\033[91m'
    return f'{color}{typed}\033[0m'

def typing_speed(text, start_time, end_time):
    characters = len(text)  # 글자 수로 계산
    minutes = (end_time - start_time) / 60
    return characters / minutes if minutes > 0 else 0

def display_typed(text):
    start_time = time.time()
    typed_list = []
    for typed, expected in typed_vs_expected(text):
        colored_char = color_char(typed, expected)
        print(colored_char, end='', flush=True)
        typed_list.append((typed, expected))
    end_time = time.time()
    elapsed_time = end_time - start_time
    return elapsed_time, typed_list

def accuracy(typed_list):
    if not typed_list:
        return 0
    correct = sum(1 for typed, expected in typed_list if typed == expected)
    return correct / len(typed_list) * 100

def main():
    print("Shell History Typing Practice")
    print("=" * 40)
    
    # shell history에서 명령어 가져오기
    commands = get_shell_history()
    
    if not commands:
        print("사용할 수 있는 명령어가 없습니다.")
        return
    
    # 랜덤하게 명령어 선택
    selected_command = random.choice(commands)
    
    print(f"다음 명령어를 입력하세요:")
    print(f"\033[96m{selected_command}\033[0m")
    print()
    print("타이핑을 시작하세요:")
    
    elapsed_time, typed_list = display_typed(selected_command)
    speed = typing_speed(selected_command, 0, elapsed_time)
    acc = accuracy(typed_list)
    
    print(f"\n\n결과:")
    print(f"타이핑 속도: {speed:.2f} 글자/분")
    print(f"정확도: {acc:.2f}%")
    print(f"소요 시간: {elapsed_time:.2f}초")

if __name__ == "__main__":
    main()