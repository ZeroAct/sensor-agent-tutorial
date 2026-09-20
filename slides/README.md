# 슬라이드

- [`예지보전_에이전트_실습.pptx`](예지보전_에이전트_실습.pptx) — 강의용 (와이드 16:9, 노트에 시간)
- [`예지보전_에이전트_실습.pdf`](예지보전_에이전트_실습.pdf) — 배포·프로젝터 백업

한국어 본문, 다크 테마. 애니메이션 없음.

## 다시 만들기

나눔 폰트가 있는 Linux에서:

```bash
pip install python-pptx
python slides/generate_slides.py
# PDF (LibreOffice)
soffice --headless --convert-to pdf --outdir slides slides/예지보전_에이전트_실습.pptx
```

Windows에서 PPTX를 열 때 글자가 깨지면 [나눔글꼴](https://hangeul.naver.com/font)을 설치하세요.
노트(발표자 노트)에 블록별 분이 들어 있습니다. 진행 대본은 `docs/INSTRUCTOR.md`가 더 깁니다.
