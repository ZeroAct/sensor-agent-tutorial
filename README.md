# 더미 공장 예지보전 에이전트 실습

공장 http://localhost:8000 · 챗봇 http://localhost:8080

- 슬라이드: [slides/예지보전_에이전트_실습.pptx](slides/예지보전_에이전트_실습.pptx)
- 수강생: [docs/STUDENT.md](docs/STUDENT.md)
- 진행자: [docs/INSTRUCTOR.md](docs/INSTRUCTOR.md)

Docker 없이 **uv** 만 씁니다.

---

## 1. uv 설치

**Windows (PowerShell)**

```powershell
irm https://astral.sh/uv/install.ps1 | iex
```

**macOS / Linux**

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

새 터미널에서 `uv --version`.

---

## 2. API 키

[Groq](https://console.groq.com/keys)

1. 가입 / 로그인
2. **API Keys → Create API Key**
3. 아래 `.env`에 붙입니다

무료 Groq는 **TPM 8000**. 모델은 `openai/gpt-oss-20b`.

---

## 3. 키 넣기

```powershell
cd playground
copy .env.example .env
```

`.env`의 `OPENAI_API_KEY=` 뒤에 키만 붙입니다.

---

## 4. 실행 (터미널 두 개, playground에서)

```powershell
uv run plant
```

```powershell
uv run open-webui
```

첫 `uv run`은 Open WebUI를 받느라 몇 분 걸립니다. 그다음부터는 위 한 줄입니다.

- 공장 http://localhost:8000
- 챗봇 http://localhost:8080 — Groq, Dummy Plant MCP, `gpt-oss-20b`가 이미 붙어 있습니다. Admin에서 MCP를 다시 추가하지 마세요.

---

## 5. 채팅

1. 모델 **GPT OSS 20B**
2. 도구 **Dummy Plant** ON
3. Skill [playground/skills/vibration-pdm.md](playground/skills/vibration-pdm.md) 를 Workspace → Skills (없으면 Prompts)에 붙여 넣기

질문은 [docs/STUDENT.md](docs/STUDENT.md).

**429** 면 새 채팅에서 한 도구만, 약 30초 뒤 다시.
