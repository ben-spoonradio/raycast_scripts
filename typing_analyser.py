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

def get_tldr_description(command):
    """tldr 명령어를 사용하여 명령어 설명을 가져오는 함수 (첫 번째 설명 줄만)"""
    try:
        # 명령어에서 첫 번째 단어만 추출 (파이프나 옵션 제거)
        base_command = command.split()[0] if command.split() else command
        
        # 특수문자 제거 (sudo, &&, || 등 처리)
        if base_command in ['sudo', 'nohup']:
            # sudo나 nohup 다음의 실제 명령어 찾기
            parts = command.split()
            if len(parts) > 1:
                base_command = parts[1]
        
        # tldr 명령어 실행
        result = subprocess.run(
            ['tldr', base_command], 
            capture_output=True, 
            text=True, 
            timeout=5
        )
        
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            # 두 번째 줄이 보통 설명 (첫 번째 줄은 명령어 이름)
            if len(lines) >= 2:
                description_line = lines[1].strip()
                # 빈 줄이 아닌 경우 반환
                if description_line:
                    return description_line
            
            # 두 번째 줄이 비어있거나 없으면 세 번째 줄부터 찾기
            for line in lines[2:]:
                line = line.strip()
                if line and not line.startswith('-') and not line.startswith('More information'):
                    return line
                    
            return f"'{base_command}' 명령어 설명"
        else:
            return f"'{base_command}' 명령어에 대한 설명을 찾을 수 없습니다."
            
    except subprocess.TimeoutExpired:
        return "tldr 명령어 실행 시간 초과"
    except FileNotFoundError:
        return "tldr 명령어가 설치되어 있지 않습니다. 'npm install -g tldr' 또는 'pip install tldr' 로 설치하세요."
    except Exception as e:
        return f"tldr 실행 중 오류: {e}"

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
    
    # tldr 설명 가져오기
    print("명령어 설명을 가져오는 중...")
    description = get_tldr_description(selected_command)
    
    print(f"\n명령어 설명:")
    print(f"\033[94m{description}\033[0m")
    print()
    
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