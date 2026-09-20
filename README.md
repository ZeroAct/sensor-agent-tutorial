# 예지보전 에이전트 실습

더미 공장(센서 10) → MCP → Open WebUI. **100분** 워크숍.

| 자료 | |
| --- | --- |
| 슬라이드 | [slides/예지보전_에이전트_실습.pptx](slides/예지보전_에이전트_실습.pptx) |
| 진행자 | [docs/INSTRUCTOR.md](docs/INSTRUCTOR.md) |
| 수강생 | [docs/STUDENT.md](docs/STUDENT.md) |

공장 http://localhost:8000 · 챗봇 http://localhost:8080 · MCP http://localhost:8000/mcp

Docker는 쓰지 않습니다. **uv**만 있으면 됩니다.

---

## 1. uv 설치

**Windows (PowerShell)**

`powershell
irm https://astral.sh/uv/install.ps1 | iex
`

**macOS / Linux**

`ash
curl -LsSf https://astral.sh/uv/install.sh | sh
`

터미널을 다시 연 뒤 uv --version.

---

## 2. API 키 발급

[Groq](https://console.groq.com/keys) (무료, 기본값)

1. 가입 / 로그인
2. **API Keys → Create API Key**
3. 키 복사. 채팅·슬라이드·깃에 붙이지 말 것

다른 공급자: [OpenRouter](https://openrouter.ai/keys), [Google AI Studio](https://aistudio.google.com/apikey)

---

## 3. 키 넣기

`powershell
cd playground
copy .env.example .env
`

macOS / Linux는 cp .env.example .env.

.env에서 이 한 줄만 채웁니다.

`env
OPENAI_API_KEY=여기에_키
`

기본 모델은 Groq llama-3.1-8b-instant. 공급자를 바꾸면 .env.example 주석의 URL·모델 이름을 따릅니다.

---

## 4. 실행 (터미널 2개)

둘 다 playground 폴더에서.

**터미널 1 — 공장 + MCP**

`powershell
uv run --python 3.12 --env-file .env python mcp-server/server.py
`

→ http://localhost:8000

**터미널 2 — Open WebUI**

`powershell
uv run --python 3.12 --with open-webui==0.11.3 --env-file .env open-webui serve --host 127.0.0.1 --port 8080
`

→ http://localhost:8080

첫 Open WebUI 실행은 패키지 받느라 몇 분 걸릴 수 있습니다. 끄려면 각 터미널에서 Ctrl+C.

---

## 5. MCP + Skill

Open WebUI → **Admin → External Tools / Integrations → Add**

- 타입: **MCP (Streamable HTTP)** (OpenAPI 아님)
- URL: http://127.0.0.1:8000/mcp
- Auth: **None**

Skill: [playground/skills/vibration-pdm.md](playground/skills/vibration-pdm.md) 전체를 **Workspace → Skills** (없으면 Prompts)에 붙여 넣기.

질문 목록은 [docs/STUDENT.md](docs/STUDENT.md).
