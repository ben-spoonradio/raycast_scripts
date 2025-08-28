#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Required parameters:
# @raycast.schemaVersion 1
# @raycast.title  PDF Max Compression
# @raycast.mode fullOutput

# Optional parameters:
# @raycast.icon 📄
# @raycast.packageName PDF Tools
# @raycast.needsConfirmation false

# Documentation:
# @raycast.description Rasterize to native pixel size derived from original PDF so x-ppi/y-ppi match (uses Finder selection)
# @raycast.author moonbc
# @raycast.authorURL https://raycast.com/moonbc

import subprocess
import os
from pathlib import Path
import sys
import shutil
import tempfile
import re

# ====== 품질/압축 설정 (필요시만 조정) ======
JPEG_QUALITY = "70"
SAMPLING     = "4:2:0"
# 이미지가 없는(벡터) 페이지의 보수적 기본 PPI
FALLBACK_PPI = 108.0

# ====== 공용 유틸 ======
def run(cmd, **kwargs):
    return subprocess.run(cmd, check=True, capture_output=True, **kwargs)

def run_text(cmd, **kwargs):
    return subprocess.run(cmd, check=True, capture_output=True, text=True, **kwargs)

def which_or(paths):
    for p in paths:
        if shutil.which(p):
            return p
    return None

def sanitize_filename(filename: str) -> str:
    return re.sub(r'[^\w\-\. ]', '_', filename)

# ====== Finder 선택 ======
def get_selected_files_from_finder():
    apple_script = r'''
    tell application "Finder"
        set sel_items to selection as alias list
        set output_text to ""
        repeat with i in sel_items
            set file_path to POSIX path of i
            set output_text to output_text & file_path & "\n"
        end repeat
        return output_text
    end tell
    '''
    try:
        result = subprocess.run(['osascript', '-e', apple_script],
                                capture_output=True, text=True, check=True)
        return [p.strip() for p in result.stdout.strip().split('\n') if p.strip()]
    except subprocess.CalledProcessError:
        return []

# ====== 의존성 확인 ======
def check_bins():
    bins = {}
    bins['magick']    = which_or(['magick', '/opt/homebrew/bin/magick', '/usr/local/bin/magick'])
    bins['gs']        = which_or(['gs', '/opt/homebrew/bin/gs', '/usr/local/bin/gs'])
    bins['pdfinfo']   = which_or(['pdfinfo', '/opt/homebrew/bin/pdfinfo', '/usr/local/bin/pdfinfo'])
    bins['pdfimages'] = which_or(['pdfimages', '/opt/homebrew/bin/pdfimages', '/usr/local/bin/pdfimages'])

    missing = [k for k, v in bins.items() if v is None]
    if missing:
        print("❌ 다음 도구가 필요합니다 (Homebrew로 설치):", ", ".join(missing))
        print("   brew install imagemagick ghostscript poppler")
        return None
    return bins

# ====== 원본 페이지 크기 / PPI 추정 ======
def get_page_size_points(pdfinfo_bin: str, pdf_path: str):
    """
    첫 페이지 기준 Page size(pts) 파싱.
    (자료가 전부 슬라이드 규격이면 페이지 크기는 대개 동일)
    """
    out = run_text([pdfinfo_bin, pdf_path]).stdout
    m = re.search(r"Page size:\s+([\d\.]+)\s+x\s+([\d\.]+)\s+pts", out)
    if not m:
        raise RuntimeError("원본 페이지 크기(pts) 파싱 실패")
    w_pt = float(m.group(1))
    h_pt = float(m.group(2))
    return w_pt, h_pt

def get_original_ppi_estimate(pdfimages_bin: str, pdf_path: str):
    """
    pdfimages -list 결과에서 각 페이지의 '가장 큰 이미지'를 찾아
    첫 페이지의 x-ppi/y-ppi를 추정.
    이미지가 없으면 None 반환.
    """
    out = run_text([pdfimages_bin, "-list", pdf_path]).stdout
    # 첫 페이지(page==1)에서 가장 큰 이미지 찾기
    max_w = max_h = 0
    for line in out.splitlines():
        if not line.strip() or line.startswith("page") or line.startswith("-"):
            continue
        cols = line.split()
        # 예시: page num type width height ...
        if len(cols) >= 5:
            try:
                page_no = int(cols[0])
                img_w   = int(cols[3])
                img_h   = int(cols[4])
            except:
                continue
            if page_no == 1:
                if img_w * img_h > max_w * max_h:
                    max_w, max_h = img_w, img_h
    if max_w > 0 and max_h > 0:
        return max_w, max_h
    return None, None

# ====== 변환 파이프라인 ======
def raster_preserve_ppi(magick_bin, gs_bin, pdfinfo_bin, pdfimages_bin, input_pdf, output_pdf):
    """
    1) 원본 페이지 크기(pts) → inches
    2) 첫 페이지에서 최대 이미지 픽셀(W,H) 추출 (없으면 FALLBACK_PPI 사용)
    3) TARGET_W/H 계산:
       - (이미지 있음) TARGET_W = max_img_w, TARGET_H = max_img_h
       - (이미지 없음) TARGET_W = round(page_w_in * FALLBACK_PPI), H 동일
    4) magick: PDF → JPEG (TARGET_W×TARGET_H, quality/sampling 유지)
    5) gs: 원본 페이지 크기(pts)로 재조립 → x-ppi/y-ppi 동일
    """
    input_path = Path(input_pdf)
    output_path = Path(output_pdf)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 1) 페이지 크기
    page_w_pt, page_h_pt = get_page_size_points(pdfinfo_bin, str(input_path))
    page_w_in = page_w_pt / 72.0
    page_h_in = page_h_pt / 72.0
    print(f"원본 페이지 크기: {page_w_pt:.2f} × {page_h_pt:.2f} pts "
          f"({page_w_in:.3f} × {page_h_in:.3f} inches)")

    # 2) 원본 최대 이미지 픽셀
    max_img_w, max_img_h = get_original_ppi_estimate(pdfimages_bin, str(input_path))

    # 3) TARGET_W/H 결정
    if max_img_w and max_img_h:
        TARGET_W = max_img_w
        TARGET_H = max_img_h
        x_ppi = TARGET_W / page_w_in
        y_ppi = TARGET_H / page_h_in
        print(f"원본 기반 추정 PPI: x-ppi={x_ppi:.2f}, y-ppi={y_ppi:.2f}")
    else:
        # 이미지가 없는 벡터 위주 문서: 보수적 PPI로 픽셀 크기 결정
        TARGET_W = int(round(page_w_in * FALLBACK_PPI))
        TARGET_H = int(round(page_h_in * FALLBACK_PPI))
        x_ppi = FALLBACK_PPI
        y_ppi = FALLBACK_PPI
        print(f"페이지에 이미지가 없어 기본 PPI({FALLBACK_PPI}) 사용 → "
              f"추정 PPI: x-ppi={x_ppi:.2f}, y-ppi={y_ppi:.2f}")

    print(f"타깃 픽셀 크기: {TARGET_W} × {TARGET_H}")

    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        jpg_pattern = str(td_path / "page-%04d.jpg")

        # 4) 래스터화
        # density는 안전하게 300으로 렌더 → 정확한 픽셀로 강제 리사이즈(!)
        magick_cmd = [
            magick_bin, "-density", "300", str(input_path),
            "-resize", f"{TARGET_W}x{TARGET_H}!",
            "-quality", JPEG_QUALITY,
            "-sampling-factor", SAMPLING,
            "-background", "white",
            "-alpha", "remove",
            jpg_pattern
        ]
        print("실행:", " ".join(magick_cmd))
        run(magick_cmd)

        jpgs = sorted(td_path.glob("page-*.jpg"))
        if not jpgs:
            raise RuntimeError("JPEG 생성 실패(파일 없음).")

        # 5) 재조립 (원본 페이지 크기 그대로) - Using magick convert approach
        # Create individual PDF pages first, then combine them
        pdf_pages = []
        for i, jpg in enumerate(jpgs):
            page_pdf = td_path / f"page-{i:04d}.pdf"
            
            # Convert JPEG to PDF preserving original pixel dimensions and PPI
            # Calculate the density needed to maintain original PPI when placing in page
            magick_pdf_cmd = [
                magick_bin, str(jpg),
                "-units", "PixelsPerInch",
                "-density", f"{x_ppi}",  # Use original PPI
                str(page_pdf)
            ]
            print(f"JPEG→PDF 변환: {jpg.name}")
            run(magick_pdf_cmd)
            pdf_pages.append(str(page_pdf))
        
        # Combine all PDF pages into final output
        if len(pdf_pages) == 1:
            # Single page, just copy
            shutil.copy2(pdf_pages[0], output_path)
        else:
            # Multiple pages, use Ghostscript to combine
            gs_cmd = [
                gs_bin,
                "-sDEVICE=pdfwrite",
                "-dBATCH", "-dNOPAUSE", "-dQUIET",
                "-sOutputFile=" + str(output_path),
            ] + pdf_pages
            
            print("PDF 병합:", " ".join(gs_cmd))
            try:
                run(gs_cmd)
            except subprocess.CalledProcessError as e:
                result = subprocess.run(gs_cmd, capture_output=True)
                try:
                    stderr_text = result.stderr.decode('utf-8', errors='replace')
                    print(f"Ghostscript stderr: {stderr_text}")
                except:
                    print(f"Ghostscript stderr (raw): {result.stderr}")
                raise e

    # 결과 요약
    orig = os.path.getsize(input_path)
    out  = os.path.getsize(output_path)
    red  = 100.0 * (1 - out / orig) if orig > 0 else 0.0
    print(f"✅ 완료: {output_path}")
    print(f"   원본 크기: {orig/1024:.1f} KB")
    print(f"   결과 크기: {out/1024:.1f} KB")
    print(f"   절감율: {red:.2f}%")
    print(f"   예상 x-ppi/y-ppi: {x_ppi:.2f} / {y_ppi:.2f} (pdfimages -list로 확인 가능)")

# ====== main ======
def main():
    print("PDF 최적화(원본 x-ppi/y-ppi & 페이지 크기 유지) 시작...")

    bins = check_bins()
    if not bins:
        return

    selected = get_selected_files_from_finder()
    if not selected and len(sys.argv) > 1:
        print("Finder 선택이 없어 명령줄 인자를 사용합니다.")
        selected = sys.argv[1:]

    if not selected:
        print("처리할 파일이 없습니다.")
        print("사용법: Finder에서 PDF 선택 후 실행 또는 python script.py /path/to/file.pdf")
        return

    print("선택된 파일 목록:")
    for i, p in enumerate(selected, 1):
        print(f"  {i}. {p}")

    pdfs = [p for p in selected if p.lower().endswith(".pdf")]
    if not pdfs:
        print("선택된 PDF 파일이 없습니다.")
        return

    success = 0
    for pdf in pdfs:
        inp = Path(pdf)
        out_dir = inp.parent
        out_name = f"{sanitize_filename(inp.stem)}_max_compressed.pdf"
        out_path = out_dir / out_name

        print(f"\n처리 중: {inp}")
        print(f"출력 파일: {out_path}")

        try:
            raster_preserve_ppi(
                bins['magick'], bins['gs'], bins['pdfinfo'], bins['pdfimages'],
                str(inp), str(out_path)
            )
            success += 1
        except Exception as e:
            print(f"❌ 실패: {e}")

    print(f"\n총 {len(pdfs)}개 중 {success}개 완료")

if __name__ == "__main__":
    main()