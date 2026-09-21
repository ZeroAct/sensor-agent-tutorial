# 수강생 실습 가이드

실습 **50분**. 기동은 [README](../README.md). 이론 대본은 [진행자 가이드](INSTRUCTOR.md).

코딩하지 않습니다.

---

## 끝나면 할 수 있어야 하는 것

1. 공장 지도를 연다
2. 더미 공장 → SQLite → MCP → Claude Desktop 경로를 말로 설명한다
3. Skill을 붙인 Claude에게 설비/센서를 조회시킨다
4. 답이 `/demo/sensors`와 같은지 보고, **에이전트가 필요한 일**과 **지도만 보면 되는 일**을 가른다

---

## 연결

```text
[더미 공장 + SQLite]  :8000  →  MCP stdio  →  [Claude Desktop] + Skill
```

챗봇이 값을 아는 것이 아닙니다. **도구를 호출해서** 압니다.

기동: [README](../README.md)

- 공장 http://localhost:8000
- 챗봇: Claude Desktop. 도구 목록에 **dummy-plant**가 있어야 합니다.

### MCP

추가 방법은 [README](../README.md) `Claude Desktop에 MCP 추가`. Settings → Developer 에 **dummy-plant** 가 있어야 합니다.

### Skill

[`playground/skills/vibration-pdm.md`](../playground/skills/vibration-pdm.md) 전체를 프로젝트 지시 또는 첫 메시지에 붙여 넣기.

하지 말 것: 로컬 Python Tool 작성, Skill에 비밀, “숫자를 적당히 채워라”.

---

## 질문

dummy-plant와 Skill을 켠 채팅에서 순서대로.

**1.** 지금 플랜트에 설비가 뭐가 있고, 진동 센서는 뭐가 있나요? 도구로 확인한 뒤 표로 보여 주세요.

기대: 센서 **10줄**. `pump-a`(설비)와 `pump-a-de`(센서)를 섞지 않는다.

**2.** `pump-a-de`의 최신 진동 값. RMS와 시각을 지어내지 말고 도구 결과 그대로.

**3.** 최근 이벤트(이상·전원·고장)를 요약. 도구 결과를 인용.

**4.** (시간 남으면) 더미에서 `pump-a`를 고장 내고 교체. 새 시리얼을 인용하고, 실설비 승인이 아니라고 적기.

**5.** `pump-a` 이상이 쌓이기 전에 작업자에게 고쳐 달라고 요청. 직접 고친 것처럼 말하지 말 것.

기대: `request_fix`. 공장 화면에서 **수락**. 수락 전에는 카운트 그대로.

대조:

```powershell
curl -s http://localhost:8000/demo/sensors
curl -s http://localhost:8000/demo/assets
curl -s http://localhost:8000/demo/events
```

챗봇 숫자와 JSON이 다르면 도구를 안 불렀거나 추측한 것입니다. 그게 오늘 핵심입니다.

---

## 답을 현장 언어로

| 상태 | 오늘 뜻 | 하면 안 되는 해석 |
| --- | --- | --- |
| normal | 수업용 임계값 아래 | 설비 안전 인증 |
| warning | 주의. 오늘 추세 도구 없음 | 내일 고장난다 |
| anomaly | RMS가 높다. 더미 스파이크일 수 있음 | 즉시 분해 정비 |

데이터는 **가짜**입니다. 이 화면으로 실제 펌프를 멈추지 마세요.

---

## 막힐 때

- **dummy-plant 없음** — `uv run claude-config` 후 Claude Desktop을 트레이까지 종료하고 재실행. `uv`는 절대 경로로 들어갑니다.
- **도구 실패** — 공장 `:8000`이 떠 있는지. 다른 터미널에서 `uv run plant`.
- **답이 비면** — 공장 JSON은 `/demo/sensors`로 이어서 보면 됩니다.
- **센서가 항상 정상** — 약 10초마다 스파이크. 같은 센서 3회면 트립. 잠시 뒤 질문 3을 다시.

---

## 가져갈 문장

1. 챗봇은 센서가 아니다. **MCP 도구**가 센서다.
2. 한 숫자를 보는 일에는 에이전트가 **과할 수** 있다. 여러 도구를 이을 때 맞다.
3. 더미의 on/off·교체는 수업용이다. **실설비 변경을 모델에게 주는 것은 보통 과하고 위험하다.**
