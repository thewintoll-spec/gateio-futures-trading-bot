# Git 커밋 가이드

## 기본 규칙

✅ **모든 커밋 메시지는 한글로 작성합니다**

## 커밋 메시지 템플릿

```
[제목] 간결한 변경사항 요약 (50자 이내)

주요 업데이트:
- 변경사항 1 (구체적으로)
- 변경사항 2 (구체적으로)
- 변경사항 3 (있다면)

[추가 설명이 필요한 경우 여기에 작성]

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

## 예시

### ✅ 좋은 예시:

```
전략 파라미터 최적화 및 성과 개선

주요 업데이트:
- RSI 파라미터를 9/25/65로 조정 (30일 백테스트 기반)
- 레버리지 5배로 설정하여 리스크 관리
- 손절 1.5%, 익절 5.0%로 최적화
- 자본 사용률 95%로 설정 (수수료 버퍼 5%)

성과:
- 30일 수익률 +3.16% 달성
- 샤프 비율 1.88 기록
- 하락장 대응 능력 검증 완료

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

### ❌ 나쁜 예시:

```
Update strategy parameters
- Fixed RSI
- Changed leverage
```

## 커밋 타입별 제목 예시

- **기능 추가**: `새로운 RSI 전략 추가`
- **버그 수정**: `포지션 마진 계산 오류 수정`
- **최적화**: `파라미터 최적화 시스템 구현`
- **문서화**: `README 및 사용 가이드 작성`
- **리팩토링**: `백테스트 엔진 코드 정리`
- **설정**: `최적화된 파라미터 적용`

## 커밋 주의사항

1. **제목은 명령문**으로 작성 ("추가했음" ❌ → "추가" ✅)
2. **구체적인 변경사항** 명시
3. **Why(왜)**와 **What(무엇을)** 모두 포함
4. **성과나 결과**가 있다면 함께 기록
5. **영어 금지** - 모든 내용은 한글로!

## Git 명령어

### 기본 워크플로우:
```bash
# 변경사항 확인
git status
git diff

# 스테이징
git add .

# 커밋 (HEREDOC 사용 - 여러 줄 메시지)
git commit -m "$(cat <<'EOF'
전략 파라미터 최적화 및 성과 개선

주요 업데이트:
- RSI 파라미터를 9/25/65로 조정
- 레버리지 5배로 설정

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"

# 푸시
git push
```

### 마지막 커밋 수정:
```bash
git commit --amend -m "수정된 커밋 메시지"
git push -f origin main  # 주의: force push
```

## 자동화

Claude Code에게 커밋을 요청할 때:
- "커밋 메시지 한글로 작성해줘"
- "변경사항 커밋해줘"
- Claude가 자동으로 한글 템플릿을 사용합니다

---

**이 가이드를 항상 따라주세요!** 🇰🇷
