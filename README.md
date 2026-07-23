# Markdown PDF 변환기 (md-changer)

Markdown 문서를 고품질 A4 PDF로 변환하는 프로그램입니다. 기존 브라우저에서 PDF로 출력하던 결과와 동일한 품질을 보장하기 위해 Playwright의 Chromium headless 렌더링을 사용하며, **Windows GUI 앱**과 **CLI (Command Line Interface)**를 모두 지원합니다.

---

## ⚡ CLI 및 AI 에이전트 실행 방법 (`uvx` 사용 - Node.js `npx` 스타일)

Node.js의 `npx`처럼 **별도의 가상환경 설치나 복잡한 설정 없이 `uvx` 명령 한 줄로 즉시 변환**을 실행할 수 있습니다.

### 1. 기본 CLI 실행 (`uvx` 로컬 소스 또는 Git 저장소)

* **로컬 디렉터리 기반 실행:**
  ```bash
  uvx --from . md-changer -i input.md -o ./output_dir
  ```

* **GitHub 저장소 기반 실행 (전역 위치에 관계없이 설치 없이 즉시 실행):**
  ```bash
  uvx --from git+https://github.com/사용자계정/md_changer.git md-changer -i input.md -o ./output_dir
  ```

### 2. AI 에이전트용 JSON 출력 실행 (`--json`)
AI 에이전트(LLM Agent)가 처리 결과를 구조화된 JSON 데이터로 파싱하고자 할 때 사용합니다:

```bash
uvx --from . md-changer -i input.md -o ./output_dir --json
```

**JSON 출력 예시:**
```json
{
  "status": "success",
  "converted_count": 1,
  "output_directory": "C:\\path\\to\\output_dir",
  "files": [
    {
      "source": "input.md",
      "pdf": "C:\\path\\to\\output_dir\\input.pdf"
    }
  ]
}
```

---

## 🖥️ Windows GUI 실행 및 사용 방법

1. `main.py`를 실행하거나 포터블 `.exe` 파일을 실행합니다.
   ```bash
   python main.py
   ```
2. **파일 추가** 버튼으로 `.md` 또는 `.markdown` 파일을 선택하거나, 목록 상자로 끌어다 놓습니다(Drag & Drop).
3. **출력 폴더 선택**으로 PDF 저장 위치를 지정합니다.
4. **PDF 변환** 버튼을 누르면 일괄 변환이 진행됩니다.

---

## 🛠️ 주요 기능

- **GUI / CLI / AI 에이전트 지원**: 드래그 앤 드롭 GUI, 터미널 CLI, 에이전트 파싱용 `--json` 출력 지원
- **단일 / 다중 / 디렉터리 일괄 변환**: 파일 개별 지정 및 디렉터리 전체 변환 지원
- **완벽한 한글 및 CSS 스타일 렌더링**: 표, 코드블록, 이미지, blockquote 등 깔끔한 A4 레이아웃
- **Self-Contained Browser**: Playwright Chromium 헤드리스 렌더러 기반

---

## 🔧 개발 환경 실행 및 빌드

이 프로젝트는 패키지 관리를 위해 `uv`를 사용합니다.

```powershell
# 개발 의존성 설치 및 Playwright 브라우저 다운로드
uv sync --group build
uv run playwright install chromium

# CLI 실행 테스트
uv run python main.py -i sample_test.md -o test_output --json

# GUI 실행
uv run python main.py
```

### EXE 포터블 빌드

```powershell
.\build.ps1
```

---

## 📁 프로젝트 구조

```text
src/md_changer/
├── core.py       # Playwright 기반 핵심 PDF 변환 엔진
├── cli.py        # CLI 파서 및 JSON 출력 처리기
├── gui.py        # TkinterDnD2 GUI 애플리케이션
├── styles.py     # PDF 전용 기본 CSS 스타일 정의
└── __init__.py
main.py           # 통합 실행 엔트리포인트 (인자 유무에 따라 CLI/GUI 분기)
SKILL.md          # AI 에이전트 전용 스킬 정의 문서
pyproject.toml    # 패키지 정보 및 Scripts 설정
```
