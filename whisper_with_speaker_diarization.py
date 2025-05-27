# whisper_with_speaker_diarization.py
import whisper
import os
import sys
import time
import json
import anthropic
from datetime import timedelta
import re
import wave
import contextlib
import subprocess
import pyperclip  # For clipboard functionality

def transcribe_audio(audio_path, output_dir="output", model_name="small"):
    """
    OpenAI Whisper를 사용하여 오디오 파일을 전사하는 함수
    
    Args:
        audio_path (str): 오디오 파일 경로
        output_dir (str): 출력 디렉토리
        model_name (str): 모델 크기 (tiny, base, small, medium, large)
    """
    start_time = time.time()
    
    print(f"===== Whisper 전사 시작 =====")
    print(f"모델: {model_name}")
    print(f"오디오 파일: {audio_path}")
    print("=" * 30)
    
    try:
        # 1. 모델 로드
        print("\n모델 로딩 중...")
        model = whisper.load_model(model_name)
        print(f"모델 로드 완료!")
        
        # 2. 전사 실행
        print("\n전사 진행 중... (시간이 다소 소요될 수 있습니다)")
        result = model.transcribe(
            audio_path,
            verbose=True,  # 진행 상황 표시
            word_timestamps=True  # 단어별 타임스탬프 활성화
        )
        
        # 3. 출력 디렉토리 생성
        os.makedirs(output_dir, exist_ok=True)
        
        # 4. 결과 저장
        base_name = os.path.splitext(os.path.basename(audio_path))[0]
        
        # a. JSON 결과 저장
        json_path = os.path.join(output_dir, f"{base_name}.json")
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        # b. 텍스트 결과 저장
        text_path = os.path.join(output_dir, f"{base_name}.txt")
        with open(text_path, 'w', encoding='utf-8') as f:
            f.write(result["text"])
        
        # c. SRT 자막 생성
        srt_path = os.path.join(output_dir, f"{base_name}.srt")
        create_srt(result["segments"], srt_path)
        
        # 5. 요약 정보 출력
        total_time = time.time() - start_time
        print("\n===== 전사 완료 =====")
        print(f"소요 시간: {timedelta(seconds=int(total_time))}")
        print(f"세그먼트 수: {len(result['segments'])}")
        print("\n생성된 파일:")
        print(f"- 텍스트: {text_path}")
        print(f"- JSON: {json_path}")
        print(f"- SRT: {srt_path}")
        
        return result, json_path
        
    except KeyboardInterrupt:
        print("\n\n작업이 사용자에 의해 중단되었습니다.")
        return None, None
    except Exception as e:
        print(f"\n오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return None, None

def create_srt(segments, output_path):
    """세그먼트로부터 SRT 자막 파일 생성"""
    with open(output_path, 'w', encoding='utf-8') as f:
        for i, segment in enumerate(segments):
            # SRT 형식: 인덱스, 시간 범위, 텍스트
            start = format_timestamp(segment["start"])
            end = format_timestamp(segment["end"])
            
            f.write(f"{i+1}\n")
            f.write(f"{start} --> {end}\n")
            f.write(f"{segment['text'].strip()}\n\n")

def format_timestamp(seconds):
    """초를 SRT 타임스탬프 형식(HH:MM:SS,mmm)으로 변환"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds - int(seconds)) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

def load_json_transcript(json_path):
    """
    기존 JSON 전사 파일을 로드하는 함수
    
    Args:
        json_path (str): JSON 파일 경로
    
    Returns:
        dict: 전사 데이터
    """
    try:
        print(f"\n===== 기존 JSON 전사 파일 로드 =====")
        print(f"파일 경로: {json_path}")
        
        with open(json_path, 'r', encoding='utf-8') as f:
            transcript_data = json.load(f)
        
        # 간단한 유효성 검사
        if "text" not in transcript_data or "segments" not in transcript_data:
            print("\n❌ 유효하지 않은 JSON 형식입니다. 'text'와 'segments' 필드가 필요합니다.")
            return None, None
        
        print(f"\n✅ JSON 파일 로드 성공")
        print(f"세그먼트 수: {len(transcript_data['segments'])}")
        
        return transcript_data, json_path
    
    except Exception as e:
        print(f"\n❌ JSON 파일 로드 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return None, None

def extract_last_speakers(content, num_speakers=5):
    """마지막 n개의 화자 대화를 추출"""
    speaker_pattern = r'\*\*(화자 [A-Z])\*\*: (.*?)(?=\*\*화자|\Z)'
    matches = re.findall(speaker_pattern, content, re.DOTALL)
    
    # 마지막 num_speakers개의 화자 대화 반환
    if matches:
        return "\n".join([f"**{speaker}**: {text.strip()}" for speaker, text in matches[-num_speakers:]])
    else:
        return "아직 식별된 화자가 없습니다."

def extract_all_speakers(content):
    """모든 고유 화자를 추출"""
    speaker_pattern = r'\*\*(화자 [A-Z])\*\*'
    matches = re.findall(speaker_pattern, content)
    if matches:
        return ", ".join(sorted(set(matches)))
    else:
        return "아직 식별된 화자가 없습니다."

def sample_meeting_content(content, max_samples=12, sample_size=300):
    """긴 회의 내용에서 균등하게 샘플 추출"""
    content_length = len(content)
    if content_length <= max_samples * sample_size:
        return content
    
    samples = []
    # 시작 부분 항상 포함 (처음 2개 샘플)
    samples.append(content[:sample_size * 2])
    
    # 중간 부분 균등 샘플링
    step = (content_length - (3 * sample_size)) // (max_samples - 3)
    for i in range(1, max_samples - 2):
        start_idx = (sample_size * 2) + (i - 1) * step
        samples.append(content[start_idx:start_idx + sample_size])
    
    # 끝부분 항상 포함
    samples.append(content[-sample_size:])
    
    return "\n...\n".join(samples)

def post_process_meeting_minutes(content):
    """회의록 내용을 후처리하여 일관성 있는 형식으로 변환"""
    
    # 1. 불필요한 마크업 및 중간 프롬프트 제거
    patterns_to_remove = [
        r'\*\*화자 구분 결과\*\*',
        r'\*\*마지막 화자 컨텍스트\*\*.*?(?=\*\*|##|\Z)',
        r'\*\*지금까지 식별된 화자 목록\*\*.*?(?=\*\*|##|\Z)',
        r'\*\*화자 구분 정리\*\*',
        r'\*\*식별된 화자 목록\*\*.*?(?=\*\*|##|\Z)',
        r'화자 구분된 전사 내용 \(\d+/\d+ 부분\)'
    ]
    
    for pattern in patterns_to_remove:
        content = re.sub(pattern, '', content, flags=re.DOTALL)
    
    # 2. 여러 줄 공백을 한 줄로 줄이기
    content = re.sub(r'\n{3,}', '\n\n', content)
    
    # 3. 화자 일관성 확인 및 수정
    # 화자 목록 추출
    speakers = set(re.findall(r'\*\*화자 ([A-Z])\*\*', content))
    
    # 헤더에서 참석자 목록 추출
    header_match = re.search(r'참석자: (.*?)(?=\n|$)', content)
    if header_match:
        header_participants = header_match.group(1)
        
        # 헤더의 참석자 목록 업데이트
        participants_list = ", ".join([f"화자 {speaker}" for speaker in sorted(speakers)])
        content = re.sub(r'참석자: .*?(?=\n|$)', f'참석자: {participants_list}', content)
    
    # 4. 회의 내용 부분 정리
    content_match = re.search(r'## 회의 내용(.*?)(?=##|$)', content, re.DOTALL)
    if content_match:
        meeting_content = content_match.group(1).strip()
        
        # 연속된 같은 화자의 발언을 하나로 합치기
        current_speaker = None
        merged_lines = []
        lines = meeting_content.split('\n')
        
        buffer = ""
        for line in lines:
            speaker_match = re.match(r'\*\*화자 ([A-Z])\*\*: (.*)', line)
            if speaker_match:
                speaker, text = speaker_match.groups()
                
                if speaker == current_speaker and buffer:
                    # 같은 화자가 계속 말하는 경우
                    buffer += " " + text
                else:
                    # 다른 화자로 전환된 경우
                    if buffer:
                        merged_lines.append(buffer)
                    buffer = f"**화자 {speaker}**: {text}"
                    current_speaker = speaker
            elif line.strip() and buffer:
                # 화자 표시가 없는 텍스트 줄은 이전 화자의 발언에 추가
                buffer += " " + line.strip()
        
        if buffer:  # 마지막 발언 추가
            merged_lines.append(buffer)
        
        # 정리된 회의 내용으로 대체
        cleaned_content = "\n\n".join(merged_lines)
        content = content.replace(content_match.group(0), f"## 회의 내용\n\n{cleaned_content}\n\n")
    
    # 5. 후속 조치 및 결정사항 섹션 정리 (화자 C가 실제로 있는지 확인)
    decision_section = re.search(r'## 주요 결정사항(.*?)(?=##|$)', content, re.DOTALL)
    follow_up_section = re.search(r'## 후속 조치(.*?)(?=##|$)', content, re.DOTALL)
    
    # 화자 C 등 비일관적인 화자 처리
    if 'C' not in speakers and ('화자 C' in content):
        if decision_section:
            decision_content = decision_section.group(1)
            content = content.replace(decision_section.group(0), f"## 주요 결정사항{decision_content.replace('화자 C', '화자 A')}")
        
        if follow_up_section:
            follow_up_content = follow_up_section.group(1)
            content = content.replace(follow_up_section.group(0), f"## 후속 조치{follow_up_content.replace('화자 C', '화자 A')}")
    
    return content

def generate_meeting_minutes(json_path, output_dir, api_key, segment_batch_size=60):
    """
    Anthropic API를 사용하여 전사 결과에서 화자를 구분하고 회의록 생성
    긴 전사 내용을 여러 청크로 나누어 처리합니다.
    
    Args:
        json_path (str): Whisper로 생성된 JSON 파일 경로
        output_dir (str): 출력 디렉토리
        api_key (str): Anthropic API 키
        segment_batch_size (int): 한 번에 처리할 세그먼트 수
    """
    print("\n===== 화자 구분 및 회의록 생성 시작 =====")
    
    # 1. JSON 파일 로드
    with open(json_path, 'r', encoding='utf-8') as f:
        transcript_data = json.load(f)
    
    # 2. 세그먼트 텍스트 추출
    segments = transcript_data["segments"]
    full_text = transcript_data["text"]
    
    # 세그먼트 수가 많은 경우 분할 처리
    total_segments = len(segments)
    
    if total_segments <= segment_batch_size:
        # 세그먼트가 적은 경우 한 번에 처리
        return process_single_batch(segments, full_text, json_path, output_dir, api_key)
    else:
        # 세그먼트가 많은 경우 분할 처리
        return process_multiple_batches(segments, json_path, output_dir, api_key, segment_batch_size)

def process_single_batch(segments, full_text, json_path, output_dir, api_key):
    """단일 배치로 회의록 생성 처리 - 스트리밍 모드 사용"""
    # 3. Anthropic 클라이언트 초기화
    client = anthropic.Anthropic(api_key=api_key)
    
    # 4. 화자 구분 및 회의록 생성 프롬프트 작성
    prompt = f"""
    아래는 회의 녹음의 전사 내용입니다. 이 내용을 바탕으로 구조화된 회의록 형식으로 정리해주세요.
    
    다음과 같은 형식으로 회의록을 작성해 주세요:
    
    # 회의록
    날짜: [회의 날짜 - 년도와 월 표시]
    참석자: [화자 A, 화자 B, 화자 C 등으로 표시]
    주제: [회의의 주요 주제]
    
    ## 회의 내용
    **화자 A**: [화자 A의 발언]
    **화자 B**: [화자 B의 발언]
    ...
    
    ## 주요 결정사항
    - [결정사항 1]
    - [결정사항 2]
    ...
    
    ## 후속 조치
    - [액션 아이템 1] - 담당자: [화자 X]
    - [액션 아이템 2] - 담당자: [화자 Y]
    ...
    
    가능한 한 원본 발화를 보존하면서도 문맥에 맞게 문장 수정하면서, 각 화자별로 발언을 구분하여 정리해주세요.
    각 화자의 이름은 'A', 'B', 'C' 등으로 표시하고, 발언은 원문 그대로 포함해주세요.
    회의 날짜는 현재 시점을 기준으로 가장 가능성 있는 날짜를 추정하되, 정확한 날짜를 알 수 없다면 년도와 월만 표시해도 됩니다.
    
    회의록에 중간 프롬프트나 지시사항 같은 메타 정보는 포함하지 마세요.
    화자 구분된 내용만 정리하여 깔끔한 회의록을 작성해주세요.
    
    전사 내용:
    {full_text}
    
    세부 세그먼트 (타임스탬프 포함):
    """
    
    # 세그먼트 정보 추가
    for i, segment in enumerate(segments):
        start_time = format_time_simple(segment["start"])
        end_time = format_time_simple(segment["end"])
        prompt += f"\n[{start_time} - {end_time}] {segment['text']}"
    
    # 5. Anthropic API 호출
    try:
        print("\nAnthropic API로 화자 구분 및 회의록 생성 중... (스트리밍 모드)")
        
        # 스트리밍 모드로 API 호출
        stream = client.messages.create(
            model="claude-3-7-sonnet-latest",
            max_tokens=64000,
            temperature=0.2,
            messages=[
                {"role": "user", "content": prompt}
            ],
            stream=True  # 스트리밍 모드 활성화
        )
        
        meeting_minutes = ""
        print("\n응답 수신 중...")
        
        # 스트림에서 응답 수집
        for chunk in stream:
            if chunk.type == "content_block_delta" and chunk.delta.text:
                meeting_minutes += chunk.delta.text
                # 진행 상황을 표시하는 점 출력
                print(".", end="", flush=True)
        
        print("\n응답 수신 완료!")
        
        # 회의록 후처리
        meeting_minutes = post_process_meeting_minutes(meeting_minutes)
        
        # 6. 회의록 저장
        base_name = os.path.splitext(os.path.basename(json_path))[0]
        minutes_path = os.path.join(output_dir, f"{base_name}_meeting_minutes.md")
        
        with open(minutes_path, 'w', encoding='utf-8') as f:
            f.write(meeting_minutes)
        
        print(f"\n✅ 회의록 생성 완료: {minutes_path}")
        return minutes_path
        
    except Exception as e:
        print(f"\n회의록 생성 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return None

def process_multiple_batches(segments, json_path, output_dir, api_key, batch_size):
    """여러 배치로 나누어 회의록 생성 처리 - 스트리밍 모드 사용"""
    client = anthropic.Anthropic(api_key=api_key)
    total_segments = len(segments)
    num_batches = (total_segments + batch_size - 1) // batch_size  # 올림 나눗셈
    
    print(f"\n전체 세그먼트 수: {total_segments}, 배치 크기: {batch_size}, 총 배치 수: {num_batches}")
    
    # 중간 결과 저장 경로
    base_name = os.path.splitext(os.path.basename(json_path))[0]
    interim_path = os.path.join(output_dir, f"{base_name}_interim_minutes.md")
    minutes_path = os.path.join(output_dir, f"{base_name}_meeting_minutes.md")
    
    # 1단계: 첫 번째 배치로 회의록 기본 구조 생성
    first_batch = segments[:batch_size]
    first_batch_text = " ".join([segment["text"] for segment in first_batch])
    
    initial_prompt = f"""
    아래는 회의 녹음의 전사 내용 중 첫 번째 부분입니다. 이 내용을 바탕으로 구조화된 회의록 형식으로 정리해주세요.
    
    다음과 같은 형식으로 회의록을 작성해 주세요:
    
    # 회의록
    날짜: [회의 날짜 - 년도와 월 표시]
    참석자: [화자 A, 화자 B, 화자 C 등으로 표시]
    주제: [회의의 주요 주제]
    
    ## 회의 내용
    **화자 A**: [화자 A의 발언]
    **화자 B**: [화자 B의 발언]
    ...
    
    가능한 한 원본 발화를 보존하면서도 문맥에 맞게 문장 수정하면서, 각 화자별로 발언을 구분하여 정리해주세요.
    각 화자의 이름은 'A', 'B', 'C' 등으로 표시하고, 발언은 원문 그대로 포함해주세요.
    회의 날짜는 현재 시점을 기준으로 가장 가능성 있는 날짜를 추정하되, 정확한 날짜를 알 수 없다면 년도와 월만 표시해도 됩니다.
    
    회의록에 중간 프롬프트나 지시사항 같은 메타 정보는 포함하지 마세요.
    화자 구분된 내용만 정리하여 깔끔한 회의록을 작성해주세요.
    
    전사 내용(1/{num_batches} 부분):
    {first_batch_text}
    
    세부 세그먼트 (타임스탬프 포함):
    """
    
    # 세그먼트 정보 추가
    for i, segment in enumerate(first_batch):
        start_time = format_time_simple(segment["start"])
        end_time = format_time_simple(segment["end"])
        initial_prompt += f"\n[{start_time} - {end_time}] {segment['text']}"
    
    try:
        print("\n회의록 구조 생성 중... (1단계) - 스트리밍 모드 사용")
        
        # 스트리밍 모드로 API 호출
        stream = client.messages.create(
            model="claude-3-7-sonnet-latest",
            max_tokens=64000,
            temperature=0.2,
            messages=[
                {"role": "user", "content": initial_prompt}
            ],
            stream=True  # 스트리밍 모드 활성화
        )
        
        initial_minutes = ""
        print("\n응답 수신 중...")
        
        # 스트림에서 응답 수집
        for chunk in stream:
            if chunk.type == "content_block_delta" and chunk.delta.text:
                initial_minutes += chunk.delta.text
                # 진행 상황을 표시하는 점 출력
                print(".", end="", flush=True)
        
        print("\n응답 수신 완료!")
        
        # 회의록에서 회의 내용 부분 이전까지 추출 (헤더 부분)
        header_match = re.search(r'(# 회의록.*?)## 회의 내용', initial_minutes, re.DOTALL)
        if header_match:
            header_content = header_match.group(1)
        else:
            header_content = initial_minutes.split("## 회의 내용")[0]
        
        # 회의록에서 회의 내용 부분 추출
        content_match = re.search(r'## 회의 내용(.*?)(?=##|$)', initial_minutes, re.DOTALL)
        if content_match:
            meeting_content = content_match.group(1).strip()
        else:
            meeting_content = ""
        
        # 회의록에서 결정사항과 후속 조치 추출 (푸터 부분)
        footer_content = ""
        if "## 주요 결정사항" in initial_minutes:
            footer_match = re.search(r'(## 주요 결정사항.*)', initial_minutes, re.DOTALL)
            if footer_match:
                footer_content = footer_match.group(1)
        
        # 2단계: 나머지 배치 처리
        all_meeting_content = meeting_content
        
        # 중간 결과 저장
        with open(interim_path, 'w', encoding='utf-8') as f:
            f.write(f"{header_content}\n## 회의 내용\n{all_meeting_content}\n\n{footer_content}")
        
        print(f"\n✓ 중간 결과 저장 완료: {interim_path} (배치 1/{num_batches})")
        
        for batch_num in range(1, num_batches):
            start_idx = batch_num * batch_size
            end_idx = min(start_idx + batch_size, total_segments)
            current_batch = segments[start_idx:end_idx]
            current_batch_text = " ".join([segment["text"] for segment in current_batch])
            
            # 이전 처리 결과에서 화자 정보 추출
            last_speakers = extract_last_speakers(all_meeting_content, 5)
            all_speakers = extract_all_speakers(all_meeting_content)
            
            # 개선된 프롬프트: 명확한 지시 포함
            context_prompt = f"""
            아래는 긴 회의 녹음의 전사 내용 중 {batch_num+1}/{num_batches} 부분입니다.
            이전 부분에서 이미 다음과 같이 화자를 구분했습니다:
            
            # 마지막 화자 컨텍스트 (참고용)
            {last_speakers}
            
            # 지금까지 식별된 화자 목록
            {all_speakers}
            
            이어서 아래 전사 내용에서 화자를 구분하여 정리해주세요.
            아래 지침을 엄격하게 따라주세요:
            
            1. 각 화자의 이름은 반드시 이전과 동일한 화자 표기(화자 A, 화자 B 등)를 사용해주세요.
            2. 새 화자가 확실하게 식별되지 않는 한, 기존 화자 중 하나로 분류해주세요.
            3. 화자 구분은 "**화자 X**: 발언내용" 형식으로 정확히 표기해주세요.
            4. 참고용 섹션 제목이나 메타데이터를 출력하지 마세요.
            5. 회의 내용만 출력하고, 중간에 "화자 구분 결과"나 "화자 구분 정리" 같은 제목을 넣지 마세요.
            
            전사 내용({batch_num+1}/{num_batches} 부분):
            {current_batch_text}
            
            세부 세그먼트 (타임스탬프 포함):
            """
            
            # 세그먼트 정보 추가
            for i, segment in enumerate(current_batch):
                start_time = format_time_simple(segment["start"])
                end_time = format_time_simple(segment["end"])
                context_prompt += f"\n[{start_time} - {end_time}] {segment['text']}"
            
            print(f"\n회의 내용 추가 처리 중... ({batch_num+1}/{num_batches} 부분)")
            try:
                # API 호출 제한을 피하기 위한 짧은 대기 시간
                if batch_num > 1 and batch_num % 3 == 0:
                    print("API 제한 방지를 위해 3초 대기...")
                    time.sleep(3)
                
                # 스트리밍 모드로 API 호출
                batch_stream = client.messages.create(
                    model="claude-3-7-sonnet-latest",
                    max_tokens=20000,
                    temperature=0.2,
                    messages=[
                        {"role": "user", "content": context_prompt}
                    ],
                    stream=True  # 스트리밍 모드 활성화
                )
                
                batch_content = ""
                print("\n응답 수신 중...")
                

                # 스트림에서 응답 수집
                for chunk in batch_stream:
                    if chunk.type == "content_block_delta" and chunk.delta.text:
                        batch_content += chunk.delta.text
                        # 진행 상황을 표시하는 점 출력
                        print(".", end="", flush=True)
                
                print("\n응답 수신 완료!")
                
                # 회의 내용만 추출하고 메타데이터 제거
                # 특정 제목 패턴을 찾아 제거
                batch_content = re.sub(r'#+\s*화자\s*구분\s*(?:결과|정리).*?(?=\*\*화자|\Z)', '', batch_content, flags=re.DOTALL)
                batch_content = re.sub(r'마지막\s*화자\s*컨텍스트.*?(?=\*\*화자|\Z)', '', batch_content, flags=re.DOTALL)
                batch_content = re.sub(r'지금까지\s*식별된\s*화자\s*목록.*?(?=\*\*화자|\Z)', '', batch_content, flags=re.DOTALL)
                
                # 회의 내용만 추출
                content_match = re.search(r'(?:## 회의 내용)?(.*?)(?=##|$)', batch_content, re.DOTALL)
                if content_match:
                    additional_content = content_match.group(1).strip()
                    all_meeting_content += "\n" + additional_content
                else:
                    all_meeting_content += "\n" + batch_content
                
                # 중간 결과 저장
                with open(interim_path, 'w', encoding='utf-8') as f:
                    f.write(f"{header_content}\n## 회의 내용\n{all_meeting_content}\n\n{footer_content}")
                
                print(f"✓ 중간 결과 업데이트 완료: {interim_path} (배치 {batch_num+1}/{num_batches})")
            
            except Exception as e:
                print(f"\n배치 {batch_num+1} 처리 중 오류 발생: {e}")
                import traceback
                traceback.print_exc()
                
                # 오류 발생 시에도 지금까지의 결과 저장
                print(f"⚠️ 오류 발생: 지금까지의 결과를 저장합니다.")
                with open(interim_path, 'w', encoding='utf-8') as f:
                    f.write(f"{header_content}\n## 회의 내용\n{all_meeting_content}\n\n{footer_content}")
        
        # 3단계: 마지막 배치로 결정사항 및 후속 조치 생성 또는 업데이트
        if not footer_content:
            # 전체 내용에서 샘플링
            meeting_content_samples = sample_meeting_content(all_meeting_content)
            
            summarize_prompt = f"""
            아래는 회의 전체 내용에서 샘플링한 주요 부분입니다. 
            이를 바탕으로 회의의 주요 결정사항과 후속 조치를 정리해주세요.
            
            ## 회의 내용 샘플
            {meeting_content_samples}
            
            회의의 주요 결정사항과 후속 조치를 다음 형식으로 작성해주세요:
            
            ## 주요 결정사항
            - [결정사항 1]
            - [결정사항 2]
            ...
            
            ## 후속 조치
            - [액션 아이템 1] - 담당자: [화자 X]
            - [액션 아이템 2] - 담당자: [화자 Y]
            ...
            
            결정사항과 후속 조치만 출력하고, 다른 메타데이터나 제목은 넣지 마세요.
            반드시 위 형식만 정확히 따라주세요.
            """
            
            print("\n주요 결정사항 및 후속 조치 생성 중...")
            try:
                # 스트리밍 모드로 API 호출
                summary_stream = client.messages.create(
                    model="claude-3-7-sonnet-latest", 
                    max_tokens=4000,
                    temperature=0.2,
                    messages=[
                        {"role": "user", "content": summarize_prompt}
                    ],
                    stream=True  # 스트리밍 모드 활성화
                )
                
                footer_content = ""
                print("\n응답 수신 중...")
                
                # 스트림에서 응답 수집
                for chunk in summary_stream:
                    if chunk.type == "content_block_delta" and chunk.delta.text:
                        footer_content += chunk.delta.text
                        # 진행 상황을 표시하는 점 출력
                        print(".", end="", flush=True)
                
                print("\n응답 수신 완료!")
                
            except Exception as e:
                print(f"\n결정사항 생성 중 오류 발생: {e}")
                footer_content = """
                ## 주요 결정사항
                - 결정사항을 추출할 수 없습니다.
                
                ## 후속 조치
                - 후속 조치를 추출할 수 없습니다.
                """
        
        # 4단계: 최종 회의록 조합 및 후처리
        final_minutes = f"{header_content}\n## 회의 내용\n{all_meeting_content}\n\n{footer_content}"
        
        # 후처리 적용
        final_minutes = post_process_meeting_minutes(final_minutes)
        
        # 최종 회의록 저장
        with open(minutes_path, 'w', encoding='utf-8') as f:
            f.write(final_minutes)
        
        print(f"\n✅ 회의록 생성 완료: {minutes_path}")
        return minutes_path
        
    except Exception as e:
        print(f"\n회의록 생성 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        
        # 에러 발생 시 중간 결과라도 저장
        if os.path.exists(interim_path):
            print(f"⚠️ 중간 결과가 {interim_path}에 저장되어 있습니다.")
            return interim_path
        return None

def format_time_simple(seconds):
   """초를 간단한 시간 형식(HH:MM:SS)으로 변환"""
   hours = int(seconds // 3600)
   minutes = int((seconds % 3600) // 60)
   secs = int(seconds % 60)
   return f"{hours:02d}:{minutes:02d}:{secs:02d}"

def copy_to_clipboard(file_path):
   """회의록 파일의 내용을 클립보드에 복사"""
   try:
       with open(file_path, 'r', encoding='utf-8') as f:
           content = f.read()
       pyperclip.copy(content)
       print(f"\n✅ 회의록 내용이 클립보드에 복사되었습니다.")
       return True
   except Exception as e:
       print(f"\n❌ 클립보드 복사 중 오류 발생: {e}")
       return False

def get_audio_duration(file_path):
   """오디오 파일의 재생 시간 확인"""
   try:
       # WAV 파일 처리
       if file_path.lower().endswith('.wav'):
           with contextlib.closing(wave.open(file_path, 'r')) as f:
               frames = f.getnframes()
               rate = f.getframerate()
               duration = frames / float(rate)
               return duration
       
       # MP3/기타 파일 처리 (ffprobe 사용)
       else:
           result = subprocess.run(
               ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', 
                '-of', 'default=noprint_wrappers=1:nokey=1', file_path],
               stdout=subprocess.PIPE,
               stderr=subprocess.PIPE,
               text=True
           )
           return float(result.stdout.strip())
   except Exception as e:
       print(f"오디오 길이 확인 중 오류: {e}")
       # 기본값 반환 (안전하게 긴 값으로)
       return 3600  # 1시간으로 가정

def main():
   import argparse
   
   parser = argparse.ArgumentParser(description="Whisper 오디오 전사 및 회의록 생성 도구")
   parser.add_argument("--audio", "-a", help="오디오 파일 경로")
   parser.add_argument("--model", "-m", default="small", 
                       choices=["tiny", "base", "small", "medium", "large"],
                       help="모델 크기 (기본값: small)")
   parser.add_argument("--output", "-o", default="output", 
                       help="출력 디렉토리 (기본값: output)")
   parser.add_argument("--no-minutes", "-nm", action="store_true",
                       help="회의록 생성 기능 비활성화")
   parser.add_argument("--api-key", "-k", 
                       help="Anthropic API 키 (환경 변수 ANTHROPIC_API_KEY 사용 가능)")
   parser.add_argument("--batch-size", "-bs", type=int, default=120,
                       help="회의록 생성 시 한 번에 처리할 세그먼트 수 (기본값: 120)")
   parser.add_argument("--skip-transcription", "-st", action="store_true",
                       help="전사 과정을 건너뛰고 기존 JSON 파일을 사용합니다")
   parser.add_argument("--json-path", "-jp", 
                       help="기존 Whisper JSON 파일 경로 (--skip-transcription 옵션 사용 시 필요)")
   parser.add_argument("--force-small-batch", "-fsb", action="store_true",
                       help="긴 오디오에 대해 작은 배치 크기 강제 적용 (15 세그먼트)")
   parser.add_argument("--no-clipboard", "-nc", action="store_true",
                       help="회의록 내용을 클립보드에 복사하지 않음")
   
   args = parser.parse_args()
   
   print("\n🎵 Whisper 오디오 전사 및 회의록 생성 도구")
   print("=" * 50)
   
   # 전사 과정을 건너뛰는 경우
   if args.skip_transcription:
       if not args.json_path:
           print("\n❌ 오류: --skip-transcription 옵션 사용 시 --json-path 옵션이 필요합니다.")
           sys.exit(1)
       
       # audio 인자가 있어도 무시한다는 메시지 표시
       if args.audio:
           print("\n⚠️ 참고: --skip-transcription 옵션 사용 시 --audio 옵션은 무시됩니다.")
           
       # 기존 JSON 파일 로드
       result, json_path = load_json_transcript(args.json_path)
       if not result:
           print("\n❌ JSON 파일 로드에 실패했습니다.")
           sys.exit(1)
   else:
       # 오디오 파일 필요
       if not args.audio:
           print("\n❌ 오류: 오디오 파일 경로(--audio)가 필요합니다.")
           sys.exit(1)
           
       print("지원 모델: tiny, base, small, medium, large")
       print("권장 모델: small (정확도와 속도의 균형)")
       print("예상 처리 시간: tiny(1x), base(1.5x), small(2x), medium(5x), large(10x)")
       print("=" * 50)
       
       # 클립보드 기능 안내
       if not args.no_clipboard:
           print("\n📋 클립보드 기능: 회의록이 자동으로 클립보드에 복사됩니다.")
           print("   ⚠️ 참고: 클립보드 복사를 비활성화하려면 --no-clipboard 옵션을 사용하세요.")
       
       # 오디오 길이에 따른 배치 크기 자동 조정
       audio_duration = get_audio_duration(args.audio)
       print(f"\n🎵 오디오 파일 길이: {int(audio_duration//60)}분 {int(audio_duration%60)}초")
       
       if (audio_duration > 45 * 60 or args.force_small_batch) and args.batch_size > 15:
           adjusted_batch = 15
           print(f"\n⚠️ 긴 오디오 감지됨 - 배치 크기를 {adjusted_batch}로 자동 조정합니다.")
           args.batch_size = adjusted_batch
       
       # 전사 실행
       result, json_path = transcribe_audio(args.audio, args.output, args.model)
   
   # 회의록 생성
   if result and not args.no_minutes:
       # API 키 결정 (인자 > 환경 변수)
       api_key = args.api_key or os.environ.get("ANTHROPIC_API_KEY")
       
       if not api_key:
           print("\n❌ 회의록 생성을 위한 Anthropic API 키가 필요합니다.")
           print("--api-key 인자를 사용하거나 ANTHROPIC_API_KEY 환경 변수를 설정하세요.")
           sys.exit(1)
       
       # 회의록 생성
       minutes_path = generate_meeting_minutes(json_path, args.output, api_key, args.batch_size)
       
       if minutes_path:
           print("\n✅ 전체 작업이 성공적으로 완료되었습니다!")
           print(f"생성된 회의록: {minutes_path}")
           
           # 회의록 첫 부분 미리보기 표시
           try:
               with open(minutes_path, 'r', encoding='utf-8') as f:
                   content = f.read(500)  # 처음 500자만 읽기
               print("\n회의록 미리보기:")
               print("-" * 30)
               print(content + "...")
               print("-" * 30)
           except Exception as e:
               print(f"회의록 미리보기 표시 오류: {e}")
           
           # 회의록 내용을 클립보드에 복사 (--no-clipboard 옵션을 사용하지 않은 경우)
           if not args.no_clipboard:
               copy_to_clipboard(minutes_path)
           else:
               print("\n정보: 클립보드 복사가 비활성화되었습니다 (--no-clipboard 옵션 사용됨)")
       else:
           print("\n⚠️ 전사는 완료되었으나 회의록 생성에 실패했습니다.")
           
           # 중간 결과 파일 확인
           base_name = os.path.splitext(os.path.basename(json_path))[0]
           interim_path = os.path.join(args.output, f"{base_name}_interim_minutes.md")
           if os.path.exists(interim_path):
               print(f"중간 결과가 {interim_path}에 저장되어 있습니다.")
   elif result:
       print("\n✅ 전사 작업이 성공적으로 완료되었습니다!")
       print("회의록 생성 기능이 비활성화되었습니다. (--no-minutes 옵션 사용됨)")
   else:
       print("\n❌ 작업이 실패했습니다.")
       sys.exit(1)

if __name__ == "__main__":
   main()

