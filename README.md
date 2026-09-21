# 더미 공장 + Claude Desktop

공장 http://localhost:8000 · 챗봇은 **Claude Desktop**. Docker 없음. API 키 없음.

- 슬라이드: [slides/예지보전_에이전트_실습.pptx](slides/예지보전_에이전트_실습.pptx)
- 수강생: [docs/STUDENT.md](docs/STUDENT.md)
- 진행자: [docs/INSTRUCTOR.md](docs/INSTRUCTOR.md)

---

## 1. 준비

**uv**

```powershell
irm https://astral.sh/uv/install.ps1 | iex
```

macOS / Linux: `curl -LsSf https://astral.sh/uv/install.sh | sh`

새 터미널에서 `uv --version`.

**Claude Desktop** — [설치](https://claude.ai/download) 후 로그인.

---

## 2. 공장

```powershell
cd playground
uv run plant
```

브라우저: http://localhost:8000  
지도 **아래**에 Claude가 부르는 MCP 도구 목록이 있습니다. 이 터미널은 켜 둡니다.

---

## 3. Claude Desktop에 MCP 추가

공장을 켠 다음, **다른 터미널**에서 `playground`로 갑니다.

### 방법 A — 스크립트

```powershell
uv run claude-config
```

이 명령이 `uv`와 `playground`의 **절대 경로**를 Claude 설정에 넣습니다.

그다음 Claude Desktop을 **트레이 아이콘까지 종료**하고 다시 엽니다.

### 방법 B — 설정 파일을 직접 고치기

Claude Desktop → **Settings → Developer → Edit Config**

파일 위치

| OS | 경로 |
| --- | --- |
| Windows | `%APPDATA%\Claude\claude_desktop_config.json` |
| Windows (Store) | `%LOCALAPPDATA%\Packages\Claude_pzs8sxrjxfjjc\LocalCache\Roaming\Claude\claude_desktop_config.json` |
| macOS | `~/Library/Application Support/Claude/claude_desktop_config.json` |

`mcpServers` 안에 아래를 넣습니다. `command`와 `--directory`는 **본인 PC의 절대 경로**로 바꿉니다. `uv`는 보통 `C:\Users\<이름>\.local\bin\uv.exe` 입니다.

```json
{
  "mcpServers": {
    "dummy-plant": {
      "command": "C:\\Users\\<이름>\\.local\\bin\\uv.exe",
      "args": [
        "run",
        "--directory",
        "C:\\Users\\<이름>\\ws\\sensor-agent-tutorial\\playground",
        "plant-mcp"
      ]
    }
  }
}
```

저장한 뒤 Claude Desktop을 **트레이까지 종료**하고 다시 엽니다. Claude는 사용자 PATH를 못 보는 경우가 많아서 `uv`는 상대 경로로 적지 않습니다.

### 확인

Settings → Developer 에 **dummy-plant** 가 Connected 여야 합니다.

안 보이면: 공장이 `:8000`에 떠 있는지, `uv` 절대 경로가 맞는지, Claude를 트레이까지 죽였는지를 봅니다.

---

## 4. 채팅

[playground/skills/vibration-pdm.md](playground/skills/vibration-pdm.md) 전체를 프로젝트 지시 또는 첫 메시지에 붙여 넣습니다. 질문은 [docs/STUDENT.md](docs/STUDENT.md).
