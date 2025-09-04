import yt_dlp

# URL 입력
url = input("Enter the URL of the YouTube video you want to download: ")

ydl_opts = {
    'format': 'bestaudio/best',  # 가장 좋은 품질의 오디오 선택
    'outtmpl': '%(title)s.%(ext)s',  # 파일 이름 설정
    'postprocessors': [
        {  # MP3로 변환하려면 아래 postprocessor를 사용
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',  # 파일 형식 (mp3, wav 등 선택 가능)
            'preferredquality': '192',  # 비트레이트
        }
    ],
}

with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    ydl.download([url])
