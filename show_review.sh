#!/bin/bash

# 코드 리뷰 저장 디렉토리 생성
REVIEW_DIR="reviews"
mkdir -p "$REVIEW_DIR"

# 프로젝트 이름 가져오기 (git 원격 저장소 URL에서 추출)
get_project_name() {
  local remote_url=$(git config --get remote.origin.url 2>/dev/null)
  if [ -z "$remote_url" ]; then
    # 원격 저장소가 없으면 현재 디렉토리 이름 사용
    basename "$(pwd)"
  else
    # 원격 URL에서 프로젝트 이름 추출 (.git 제거)
    basename "$remote_url" .git | sed 's/\.git$//'
  fi
}

# 현재 커밋 해시 가져오기 (작업 중인 변경사항이므로 HEAD가 아닌 index 기준)
get_commit_hash() {
  git rev-parse --short HEAD 2>/dev/null || echo "initial"
}

# 현재 날짜와 시간
get_datetime() {
  date +"%Y%m%d_%H%M"
}

# 리뷰 파일명 생성
PROJECT_NAME=$(get_project_name)
COMMIT_HASH=$(get_commit_hash)
DATETIME=$(get_datetime)
REVIEW_FILENAME="${PROJECT_NAME}_${COMMIT_HASH}_${DATETIME}.md"
REVIEW_PATH="$REVIEW_DIR/$REVIEW_FILENAME"

# 리뷰 내용 복사
cp code_review_feedback.md "$REVIEW_PATH"
echo "리뷰가 $REVIEW_PATH 에 저장되었습니다."

# 터미널 초기화
clear

# 코드 리뷰 내용 표시
echo "================================"
echo "코드 리뷰 내용:"
echo "================================"
if command -v bat > /dev/null 2>&1; then
  bat code_review_feedback.md
else
  cat code_review_feedback.md
fi
echo
echo "================================"
echo "리뷰가 $REVIEW_PATH 에 저장되었습니다."
echo "================================"
read -r  # 사용자 입력 대기
