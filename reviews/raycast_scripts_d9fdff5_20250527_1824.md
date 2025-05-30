## 코드 리뷰

### 1. 변경된 내용의 요약
- 새로운 Python 스크립트 파일 `convert_wav_to_mp3.py`가 생성되었습니다. 이 스크립트는 WAV 파일을 MP3 형식으로 변환하는 기능을 제공합니다. FFmpeg를 외부 도구로 사용하며, 변환 과정에서의 오류 처리와 파일 경로 정규화 기능을 포함하고 있습니다.

### 2. 수정된 부분에 대한 건설적인 피드백
- **코드 구조 및 문서화**: 각 함수에 대한 docstring이 잘 작성되어 있어 함수의 역할과 매개변수를 명확하게 이해할 수 있습니다. 이는 코드 유지보수에 큰 도움이 됩니다.
- **FFmpeg 설치 확인**: `check_ffmpeg_installed` 함수를 통해 FFmpeg 설치 여부를 확인하고, 설치되지 않았을 경우 적절한 오류 메시지를 출력하는 부분은 사용자 친화적입니다.
- **파일 변환 로직**: `convert_wav_to_mp3` 함수에서 WAV 파일의 존재 여부 및 형식을 체크하는 로직이 잘 구성되어 있습니다.
- **에러 처리**: 다양한 예외를 포괄적으로 처리하여 프로그램이 예기치 않게 종료되지 않도록 하고, 사용자에게 적절한 오류 메시지를 제공합니다.

### 3. 개선점이나 해결해야 할 문제에 대한 제안
- **FFmpeg 경로 설정**: 현재 코드에서는 `which ffmpeg` 명령어로 FFmpeg의 경로를 확인하고 있습니다. 만약 사용자가 경로를 변경하였거나 FFmpeg가 PATH에 포함되지 않았다면 오류가 발생할 수 있습니다. 사용자가 FFmpeg의 경로를 직접 지정할 수 있도록 기능을 추가하는 것이 좋습니다.
  
- **비트레이트 설정 기능**: 현재 비트레이트는 기본값으로 192k로 설정되어 있으며, 사용자가 커맨드라인 인자로 비트레이트를 지정할 수 있는 옵션을 추가하면 더욱 유용할 것입니다. 예를 들어:
  ```bash
  python convert_wav_to_mp3.py path/to/file.wav 128k
  ```

- **파일 변환 진행률 표시**: 여러 파일을 변환할 때 진행률을 표시하는 기능을 추가하면 사용자가 변환 진행 상황을 더 쉽게 파악할 수 있습니다. 예를 들어, 변환 중인 파일 수와 총 파일 수를 표시하는 방법으로 진행 상황을 나타낼 수 있습니다.

- **유니코드 처리**: `normalize_path` 함수에서 유니코드를 처리하는 부분은 잘 구현되어 있으나, 만약 경로에 특수 문자나 비정상적인 문자들이 포함된 경우 예외 처리를 추가하여 사용자에게 더 나은 피드백을 제공하는 것이 좋습니다.

- **테스트 코드 추가**: 기능이 추가됨에 따라, 이 스크립트의 주요 기능을 검증할 수 있는 단위 테스트를 추가하는 것이 좋습니다. 이를 통해 코드 변경 시 기능이 정상적으로 작동하는지 지속적으로 확인할 수 있습니다.

이러한 개선 사항을 반영하면 코드의 안정성과 사용자 경험이 더욱 향상될 것입니다.
