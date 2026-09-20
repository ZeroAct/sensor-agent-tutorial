# 기여 안내

이 저장소는 **비개발자 대상 100분 예지보전 실습** 교재입니다.
코드보다 **수업이 깨지지 않는 것**이 우선입니다.

## 원칙

- 문서·슬라이드는 **한국어**, 코드·주석은 **영어**
- Skills는 **Markdown만** (Python Function/Tool 코드를 Skill로 넣지 말 것)
- 실제 API 키, 사내 URL, 현장 센서 데이터를 커밋하지 말 것
- 진행자는 신호처리 전문가가 아닙니다. 진동 이론을 깊게 확장하지 말 것

## 작은 수정

1. 이슈 또는 PR에서 어떤 슬라이드/실습 분(minute)이 바뀌는지 밝히기
2. `docs/INSTRUCTOR.md` 타임테이블과 슬라이드 노트 시간을 같이 맞추기
3. playground를 바꿨으면 `playground/tests` 또는 해당 스크립트를 함께 수정

## 슬라이드 다시 만들기

```bash
pip install python-pptx
python slides/generate_slides.py
```

가능하면 LibreOffice로 PDF도 생성합니다. 자세한 내용은 `slides/README.md`.

## 실습 스택 확인

```bash
cd playground
cp .env.example .env   # 키는 로컬에만
./scripts/up.sh
python -m pytest tests -q
./scripts/down.sh
```
