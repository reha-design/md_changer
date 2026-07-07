# Markdown PDF 변환기

Markdown 파일을 PDF로 변환하는 Windows GUI 프로그램입니다. 기존에 브라우저에서 PDF로 출력하던 결과와 최대한 비슷하게 만들기 위해 Playwright의 Chromium headless 렌더링을 사용합니다.

## 주요 기능

- Markdown 파일 선택
- PDF 저장 폴더 선택
- 버튼 한 번으로 PDF 변환
- 한글 Markdown 문서 지원
- 표, 코드블록, 이미지, 링크 등 기본 Markdown 요소 지원
- Windows 포터블 패키지 배포

## 사용 기술 스택

- Python 3.13+
- tkinter
- markdown
- Playwright
- Chromium headless
- PyInstaller
- uv
- PowerShell

## 다운로드 및 사용 방법

1. GitHub Releases에서 `md_changer_portable.zip`을 다운로드합니다.
2. 원하는 폴더에 압축을 풉니다.
3. 압축 해제한 폴더 안의 `md_changer.exe`를 실행합니다.
4. `입력 파일 선택` 버튼으로 `.md` 또는 `.markdown` 파일을 선택합니다.
5. `출력 폴더 선택` 버튼으로 PDF 저장 위치를 선택합니다.
6. `PDF 변환` 버튼을 클릭합니다.

출력 PDF는 입력 Markdown 파일과 같은 이름으로 저장되며, 확장자만 `.pdf`로 바뀝니다. 같은 이름의 PDF가 이미 있으면 새 파일로 덮어씁니다.

## 개발 환경 실행

이 프로젝트는 Python 패키지 관리를 위해 `uv`를 사용합니다.

```powershell
uv sync --group build
$env:PLAYWRIGHT_BROWSERS_PATH = "ms-playwright"
uv run playwright install chromium
uv run python md_changer.py
```

## EXE 빌드

```powershell
.\build.ps1
```

빌드가 끝나면 실행 파일은 아래 위치에 생성됩니다.

```text
dist\md_changer\md_changer.exe
```

## 배포 패키지 만들기

Chromium 리소스가 필요하기 때문에 `md_changer.exe` 단일 파일만 배포하지 않고, `dist\md_changer` 폴더 전체를 zip으로 묶어 배포합니다.

```powershell
tar -a -cf dist\md_changer_portable.zip -C dist md_changer
```

배포할 파일:

```text
dist\md_changer_portable.zip
```

## 프로젝트 구조

```text
md_changer.py       GUI와 Markdown to PDF 변환 로직
md_changer.spec     PyInstaller 빌드 설정
build.ps1           uv 기반 Windows 빌드 스크립트
pyproject.toml      프로젝트 메타데이터와 의존성
uv.lock             재현 가능한 의존성 잠금 파일
```
