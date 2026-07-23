---
name: md_changer
description: Markdown (.md) 문서를 Playwright Chromium 엔진으로 고품질 A4 PDF로 변환하는 CLI 및 파이썬 도구 (uvx 원라이너 실행 지원)
---

# MD Changer Agent Skill Guide

이 도구는 Markdown 파일을 시각적으로 뛰어난 A4 PDF 문서로 변환합니다.

## ⚡ 추천 실행 방법 (`uvx` 사용 - Node.js `npx` 스타일)

사전 가상환경 설치 없이 `uvx` 명령 한 줄로 즉시 변환을 수행할 수 있습니다.

### 1. AI 에이전트 전용 JSON 구조화 출력 (`--json`)
변환 결과 및 생성된 PDF 파일 경로를 JSON으로 파싱하고자 할 때 사용합니다.

```bash
# 로컬 소스 기반 실행
uvx --from c:/Users/prist/OneDrive/문서/md_changer md-changer -i input.md -o output_dir --json

# GitHub 저장소 기반 실행
uvx --from git+https://github.com/사용자계정/md_changer.git md-changer -i input.md -o output_dir --json
```

**JSON 출력 예시:**
```json
{
  "status": "success",
  "converted_count": 1,
  "output_directory": "C:/path/to/output_dir",
  "files": [
    {
      "source": "input.md",
      "pdf": "C:/path/to/output_dir/input.pdf"
    }
  ]
}
```

---

## 💻 일반 CLI 직접 실행 방법 (`main.py`)

```bash
python main.py -i input.md -o output_dir --json
```

## 🐍 Python 코드 직접 연동

```python
from md_changer.core import convert_markdown_to_pdf
from pathlib import Path

pdf_path = convert_markdown_to_pdf(
    input_file=Path("document.md"),
    output_folder=Path("./dist")
)
```
