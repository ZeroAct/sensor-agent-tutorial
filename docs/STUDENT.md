# 수강생 실습 가이드

이 문서는 **실습 50분**용입니다. 이론 슬라이드를 대체하지 않습니다.

필요하면 [진행자 가이드](INSTRUCTOR.md), [슬라이드](../slides/예지보전_에이전트_실습.pptx), [개요 README](../README.md)를 보세요.

---

## 오늘 실습이 끝나면 할 수 있어야 하는 것

1. Codespaces(또는 로컬 Docker)에서 Open WebUI를 연다
2. 더미 진동 값이 MQTT를 거쳐 MCP 도구로 챗봇에 들어가는 그림을 말로 설명한다
3. Markdown Skill을 붙인 챗봇에게 센서 목록·최신 값·최근 이상을 묻는다
4. 답의 숫자가 맞는지 `/demo/sensors`와 대조하고, 정비 명령은 사람이 한다고 구분한다

코딩은 하지 않습니다. 파일을 고치지 않아도 됩니다.

---

## 준비물

- GitHub 계정
- **본인** 무료 LLM 키 1개 (OpenAI 호환)
  - Groq, OpenRouter, Google AI Studio 등
  - 강의장 Wi-Fi에서 가입이 막힐 수 있으니 **오기 전에** 발급
- 브라우저
- (선택) 로컬 Docker — 없어도 Codespaces로 가능

진동 센서, MQTT 지식, Python은 필요 없습니다.

---

## 0. 한 장으로 보는 연결

```text
[더미 센서] --진동 JSON--> [MQTT] --구독--> [MCP 서버 :8000]
                                              | 도구 3개
                                              v
                              [Open WebUI :8080] + [Markdown Skill]
                                              |
                                              v
                                         [무료 LLM]
```

챗봇이 똑똑해서 값을 아는 것이 아닙니다. **도구를 호출해서** 압니다.

---

## 1. Codespaces 열기 (약 5분)

1. 저장소 페이지에서 **Code → Codespaces → Create codespace on main**
2. 처음이면 컨테이너 준비가 몇 분 걸립니다. 터미널이 뜨면 성공입니다.
3. 왼쪽 **Ports**에 8080, 8000이 보이면 이후가 편합니다.

로컬 Docker를 쓸 때도 명령은 같습니다. 저장소 루트에서 아래를 실행하세요.

---

## 2. 비밀 키만 넣고 스택 켜기 (약 5분)

터미널:

```bash
cd playground
cp .env.example .env
```

`.env`를 열어 **값만** 바꿉니다. 키를 채팅·슬라이드·깃에 붙여 넣지 마세요.

최소 항목:

```env
OPENAI_API_BASE_URL=https://api.groq.com/openai/v1
OPENAI_API_KEY=여기에_본인_키
OPENAI_API_MODEL=llama-3.1-8b-instant
WEBUI_AUTH=false
```

공급자가 다르면 `.env.example` 주석의 URL·모델 이름을 따릅니다.  
`OPENAI_API_KEY=` 가 비어 있으면 챗봇은 답이 없고, MCP JSON 실습만 가능합니다.

기동:

```bash
./scripts/up.sh
```

처음이면 이미지 받기에 몇 분이 걸립니다. 끝나면 대략 이렇게 보입니다.

- `mosquitto` running
- `dummy-sensor` running
- `mcp-server` running
- `open-webui` running

확인:

```bash
curl -s http://localhost:8000/health
```

`"ok": true` 와 센서 이름이 보이면 데이터 경로는 살아있는 것입니다.

끄기:

```bash
./scripts/down.sh
```

---

## 3. Open WebUI 열기

- Codespaces: **Ports → 8080 → Open in Browser**
- 로컬: [http://localhost:8080](http://localhost:8080)

워크숍 기본은 로그인 없음 (`WEBUI_AUTH=false`)입니다.  
로그인 화면이 나오면 진행자에게 알리세요. **첫 가입자가 관리자**가 되어 수업이 멈출 수 있습니다.

왼쪽 모델 목록에 `.env`에서 정한 모델이 보여야 합니다. 비어 있으면 키·URL을 다시 보세요.

---

## 4. MCP 연결 (관리자 화면)

Open WebUI 버전에 따라 메뉴 이름이 조금 다릅니다.

1. **Admin Settings (관리자) → Integrations** 또는 **외부 도구 / Tool Servers**
2. **Add Server (+)**
3. 타입: **MCP (Streamable HTTP)**  
   기본값 OpenAPI로 두면 오늘 서버와 맞지 않습니다.
4. URL:
   - Open WebUI가 Docker 안(오늘 compose 기본): `http://mcp-server:8000/mcp`
   - 브라우저·호스트에서 직접 넣을 때: `http://localhost:8000/mcp`
5. 인증: **None**  
   Bearer를 고르고 토큰을 비우면 연결이 깨지는 경우가 있습니다.
6. 저장 후, **새 채팅**에서 도구(MCP) 토글을 켭니다.

compose가 미리 연결을 넣어 두었을 수 있습니다. 채팅창에 `Vibration PdM` 같은 도구가 보이면 이 절은 건너뛰어도 됩니다.

---

## 5. Skill은 Markdown만

파일을 엽니다: [`playground/skills/vibration-pdm.md`](../playground/skills/vibration-pdm.md)

1. 내용 **전체**를 복사합니다.
2. Open WebUI에서 **Workspace → Skills** 가 있으면 새 Skill로 붙여 넣습니다.
3. Skills 메뉴가 없으면 **Prompts (프롬프트)** 에 같은 본문을 저장하고, 채팅에 그 프롬프트를 적용합니다.

하지 말 것

- Python Tool / Function 작성
- Skill 안에 API 키 넣기
- “너는 진동 박사다, 숫자도 적당히 채워라” 같은 문장 추가

Skill은 **코드가 아니라 절차서**입니다.

---

## 6. 따라 하는 질문

모델·MCP·Skill을 켠 채팅에서 순서대로 보냅니다.

**질문 1**

> 지금 플랜트에 진동 센서가 뭐가 있나요? 도구로 확인한 뒤 ID와 상태만 표로 보여 주세요.

기대: `pump-a-de`, `pump-a-nde`, `fan-b-motor` 세 줄.

**질문 2**

> `pump-a-de`의 최신 진동 값을 알려 주세요. RMS 숫자와 시각을 지어내지 말고 도구 결과 그대로 인용하세요.

기대: `rms_mm_s` 숫자, 시간, 상태(normal / warning / anomaly).

**질문 3**

> 최근 이상이 있으면 요약해 주세요. 지금 설비를 정지해야 하는지는 당신이 결정하지 말고, 사람이 확인해야 한다고 분명히 적으세요.

기대: 이상이 없으면 “지금은 목록이 비어 있다” (몇 초 뒤 다시 물어보면 스파이크가 보일 수 있음). 명령조 정지 지시가 없어야 합니다.

답이 이상하면 바로 대조합니다.

```bash
curl -s http://localhost:8000/demo/sensors
curl -s http://localhost:8000/demo/anomalies
```

챗봇 숫자와 JSON이 **전혀** 다르면 도구를 안 불렀거나 모델이 추측한 것입니다.  
그 사실을 찾는 것이 오늘 실습의 핵심입니다.

---

## 7. 답을 현장 언어로 읽기

| 상태 | 오늘 실습에서의 뜻 | 하면 안 되는 해석 |
| --- | --- | --- |
| normal | 수업용 임계값 아래 | “설비 안전 인증” |
| warning | 주의 구간. 오늘 추세 도구는 없음 | “내일 고장난다” |
| anomaly | RMS가 잠깐 또는 계속 높게 나옴. 더미 스파이크일 수 있음 | “즉시 분해 정비” |

오늘 데이터는 **가짜**입니다. 이 화면으로 실제 펌프를 멈추지 마세요.

---

## 막힐 때

### 모델이 없다 / 답 대신 오류

- `.env`의 `OPENAI_API_KEY`, `OPENAI_API_BASE_URL`, `OPENAI_API_MODEL` 확인
- `./scripts/down.sh` 후 `./scripts/up.sh`
- 무료 티어 **429**면 잠시 쉬거나, JSON `curl`로 실습을 이어 가세요. 키가 잘못된 것이 아닐 수 있습니다.

### MCP를 못 붙인다

- 타입이 MCP (Streamable HTTP)인지
- URL이 `...:8000/mcp` 인지 (`/sse` 아님)
- Auth가 None인지
- 도구 토글이 채팅에서 켜졌는지

### 센서가 항상 정상

45초마다 `pump-a-de`가 한 번 튀도록 되어 있습니다. 잠시 뒤 질문 3을 다시 보내세요.

### Open WebUI가 느리다 / 컨테이너가 죽는다

메모리가 부족합니다. Codespaces 머신 스펙을 8 GB 이상으로 올리거나, 진행자 화면을 같이 보세요.

### 관리자 메뉴가 없다

인증이 켜져 있고 일반 사용자로 들어온 상태입니다. 워크숍은 `WEBUI_AUTH=false`가 기본입니다. 진행자에게 화면을 보여 주세요.

---

## 가져갈 문장

집에 가서 팀 채널에 이 세 줄만 적어도 충분합니다.

1. 챗봇은 센서가 아니다. **MCP 도구**가 센서다.
2. 도구가 있어도 모델은 거짓말을 한다. **Markdown Skill**이 절차를 고정한다.
3. 정비 시작/정지는 **사람**의 권한이다.

수고하셨습니다.
