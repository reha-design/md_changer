# MD Changer Test Document

이 문서는 `md_changer`의 PDF 변환 테스트를 위한 샘플 Markdown 파일입니다.

## 기본 문단

이 문단은 한글과 English text가 함께 있을 때 줄바꿈과 글꼴 표시가 자연스러운지 확인하기 위한 예시입니다.

## 목록

- 첫 번째 항목
- 두 번째 항목
- 세 번째 항목

1. 순서 항목 하나
2. 순서 항목 둘
3. 순서 항목 셋

## 인용문

> 변환 결과에서 인용문 스타일과 들여쓰기가 정상인지 확인합니다.

## 코드 블록

```python
def greet(name: str) -> str:
    return f"Hello, {name}"


print(greet("MD Changer"))
```

## 표

| 항목 | 값 | 비고 |
| --- | --- | --- |
| 제목 | 정상 | 헤더 스타일 확인 |
| 본문 | 정상 | 문단 간격 확인 |
| 표 | 정상 | 테두리 확인 |

## 링크

[OpenAI](https://www.openai.com)

## 구분선

---

## 이미지 경로 테스트

아래처럼 상대 경로 이미지가 있을 경우 렌더링 여부를 확인할 수 있습니다.

![sample image](./sample-image.png)
