# Push / Codespaces 메모

## 이 저장소를 쓰는 가장 빠른 방법

1. GitHub에서 **Code → Codespaces → Create codespace on main**
2. 첫 생성 시 `.devcontainer`가 Docker-in-Docker를 켭니다.
3. `playground/.env.example`을 `playground/.env`로 복사하고 **본인 무료 LLM 키**만 넣습니다.
4. `playground/scripts/up.sh` 실행 후 포트 **8080** (Open WebUI)을 엽니다.

## 로컬에서 푸시

```bash
git add -A
git status
git commit -m "Describe the teaching change, not the files."
git push origin main
```

`main` 보호가 켜져 있으면 브랜치를 만들어 PR로 올립니다.

## 하지 말 것

- `.env` 커밋
- 세션에서 복사한 토큰을 README에 붙여 넣기
- Open WebUI 관리자 비밀번호를 슬라이드에 박제하기
