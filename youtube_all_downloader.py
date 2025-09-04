import yt_dlp
import os

# URL 입력
url = input("Enter the URL of the YouTube video you want to download: ")

# yt-dlp 옵션 설정
ydl_opts = {
    'format': 'bestvideo+bestaudio',  # 비디오와 오디오를 따로 최상의 품질로 선택
    'outtmpl': '%(title)s.%(ext)s',  # 파일 이름 설정
    'merge_output_format': 'mp4',  # 비디오 파일을 mp4로 합침
    'postprocessors': [
        {  # 비디오와 오디오를 iOS 호환 포맷으로 변환
            'key': 'FFmpegVideoConvertor',
            'preferedformat': 'mp4',
        },
        {  # 오디오를 MP3로 추출
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',  # MP3 형식으로 변환
            'preferredquality': '192',  # 비트레이트 설정
        },
    ],
    'postprocessor_args': [
        '-c:v', 'libx264',  # 비디오 코덱을 H.264로 설정
        '-movflags', 'faststart'  # iOS 스트리밍을 위한 옵션 설정
    ],
    'keepvideo': True,  # 비디오 파일을 삭제하지 않도록 설정
}

# yt-dlp 실행 후 다운로드 완료 후 삭제 처리
with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    result = ydl.download([url])

    # 다운로드된 파일들을 삭제
    for info_dict in ydl.prepare_filename(ydl.extract_info(url, download=False)):
        webm_files = [f for f in os.listdir() if f.endswith('.webm')]
        for webm in webm_files:
            try:
                os.remove(webm)
                print(f"Deleted {webm} file.")
            except Exception as e:
                print(f"Error deleting {webm}: {e}")