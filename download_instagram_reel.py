import yt_dlp
import argparse
import os

def download_instagram_reel(url, output_dir="."):
    # 저장 폴더 자동 생성
    os.makedirs(output_dir, exist_ok=True)

    ydl_opts = {
        "outtmpl": os.path.join(output_dir, "%(title)s.%(ext)s"),  # 파일명: 제목.mp4
        "format": "bestvideo+bestaudio/best",  # 최고 화질 + 오디오
        "merge_output_format": "mp4",
        "quiet": False,
        "no_warnings": False,
        "progress_hooks": [lambda d: print(f"다운로드 중... {d.get('_percent_str', '')}") if d['status'] == 'downloading' else None],
    }

    try:
        print(f"🔗 다운로드 시작: {url}")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        print("✅ 다운로드 완료! 저장 폴더 확인하세요~")
    except Exception as e:
        print(f"❌ 오류: {e}")
        print("힌트: 로그인 필요할 수 있어요 → --cookies-from-browser 사용 방법 아래에 있어요")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="인스타 릴 파이썬 다운로더")
    parser.add_argument("url", nargs="?", help="인스타 릴 링크 (없으면 입력받음)")
    parser.add_argument("-o", "--output", default=".", help="저장 폴더 (기본: 현재 폴더)")

    args = parser.parse_args()

    if not args.url:
        args.url = input("인스타 릴 링크를 붙여넣으세요: ").strip()

    download_instagram_reel(args.url, args.output)
