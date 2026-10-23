# linkedin-job-skill

LinkedIn 구직용 AI 스킬 (한국어·영어). Claude Code와 Codex CLI에서 쓰는 `SKILL.md` 형식이다.

LinkedIn **프로필 최적화**(헤드라인·About·경력·스킬, 필드 글자수 검사)와 **공고 평가·Easy Apply 답변 작성**을 한 흐름으로 돕는다.

> [wing0828/ai-job-search-kr](https://github.com/wing0828/ai-job-search-kr) (MIT)를 LinkedIn 용도로 다시 쓴 파생 작업이다. ai-job-search-kr은 [MadsLorentzen/ai-job-search](https://github.com/MadsLorentzen/ai-job-search) (MIT)의 한국판이다.

## 원본(ai-job-search-kr)과 달라진 점

| ai-job-search-kr | linkedin-job-skill |
|------------------|--------------------|
| 이력서 + 경력기술서 + 문항형 자기소개서 | LinkedIn 프로필(Headline·About·Experience·Skills) + Easy Apply 답변 |
| 병역·학력·자격증·지역인재 게이트 | **근무 자격·비자 스폰서십·이주·근무 형태(On-site/Hybrid/Remote)** 게이트 |
| 사람인·잡코리아·잡알리오 크롤러 | **크롤러 없음.** LinkedIn 약관이 자동 수집·자동 지원을 금지하므로 공고는 붙여넣기로 받는다 |
| 자소서 글자수 측정 | **LinkedIn 필드별 글자수 검사**(`li_lint.py`, 한글·이모지 UTF-16 보수 계산, 마크다운 문법 경고) |
| 블라인드 채용 검사 | **공개 프로필 검사**(연락처 노출, 주민번호·카드번호 형태, 프로필에 없는 숫자) |
| 한국어 | **한국어·영어** 프로필 동시 운영 규칙 |
| - | 사기·유령 공고 점검, CSV 인젝션 방지 지원 트래커 |

원본의 핵심 원칙은 그대로 유지했다: **프로필에 없는 사실은 쓰지 않는다**, 회사 관련 주장은 직접 확인한 출처로만, 공고 본문은 지시가 아니라 데이터로 취급(프롬프트 인젝션 방어), 제출은 사용자가 직접.

## 구성

```
skills/linkedin-job/
├── SKILL.md                          # 워크플로·검증 체크리스트
├── references/
│   ├── 01-candidate-profile.md       # 프로필 템플릿 (한·영, 근무 자격·비자 포함)
│   ├── 02-writing-style.md           # 한·영 문체 규칙, LinkedIn 형식 규칙
│   ├── 03-profile-optimization.md    # 필드별 작성법, 글자수 제한
│   ├── 04-job-evaluation.md          # 사기 점검·게이트·점수·키워드 표
│   ├── 05-easy-apply.md              # 스크리닝 질문 유형별 답변
│   └── 06-trust-and-policy.md        # LinkedIn 자동화 금지, 신뢰 경계, 개인정보
├── scripts/                          # 표준 라이브러리만, 네트워크 접근 없음
│   ├── li_lint.py                    # 필드 글자수·형식 검사
│   ├── precheck.py                   # 제출 전 검사
│   └── tracker.py                    # 지원 현황 기록·조회
└── templates/
    ├── limits.json                   # 필드 제한 (수정 가능)
    ├── profile-draft.md              # 프로필 초안 양식
    └── tracker.csv                   # 지원 현황 헤더
agents/                               # 읽기 전용 에이전트 (Claude Code)
├── posting-scorer-li.md
└── profile-reviewer-li.md
tests/                                # pytest
```

## 설치

Claude Code:
```bash
git clone https://github.com/ryuuusm/linkedin-job-skill
cp -r linkedin-job-skill/skills/linkedin-job ~/.claude/skills/
cp linkedin-job-skill/agents/*.md ~/.claude/agents/      # 선택
```

Codex CLI:
```bash
cp -r linkedin-job-skill/skills/linkedin-job ~/.codex/skills/
```

## 사용

1. 작업 폴더를 만들고 `references/01-candidate-profile.md`를 `profile.md`로 복사해 채운다. 이력서나 현재 LinkedIn 프로필 텍스트를 주면서 "프로필 만들어줘"라고 해도 된다.
2. "링크드인 헤드라인이랑 About 고쳐줘, 영문도" → 한·영 초안 + 글자수 검사
3. 공고 본문을 붙여넣고 "이 링크드인 공고 평가해줘"
4. Easy Apply 질문을 붙여넣고 "답변 써줘"

스크립트만 따로:
```bash
python skills/linkedin-job/scripts/li_lint.py profile-draft.en.md
python skills/linkedin-job/scripts/precheck.py profile-draft.en.md --profile profile.md --public --keywords "SAP,ITGC"
python skills/linkedin-job/scripts/tracker.py list applications/tracker.csv
```

## 필드 글자수 제한

`templates/limits.json`: Headline 220, About 2,600, Experience 설명 2,000. LinkedIn 공식 도움말을 자동으로 확인할 수 없어, 2026년 9월 독립된 외부 실측 두 건이 일치하는 값을 썼다. LinkedIn이 제한을 바꾸면 이 파일만 고치면 된다.

## 주의

- 이 스킬은 LinkedIn을 크롤링하거나, 자동으로 지원·메시지·연결 요청을 보내지 않는다. 붙여넣기와 제출은 사용자가 직접 한다.
- `profile.md`와 `applications/`는 개인정보다. 저장소에 커밋하지 않는다(`.gitignore`).
- LinkedIn의 기능·정책·제한은 바뀔 수 있다. 중요한 판단 전에는 최신 공지를 확인한다.

## 테스트

```bash
pip install pytest
pytest tests -q
```

## 라이선스

MIT. 원저작권 표시(Mads Lorentzen), 한국판 저작권 표시(wing0828), LinkedIn판 저작권 표시를 [LICENSE](LICENSE)에 함께 둔다.

---

### English summary

An AI skill (Claude Code / Codex `SKILL.md`) for LinkedIn job search in Korean and English: profile optimization with per-field character-limit linting, job-posting evaluation (work authorization, visa sponsorship, workplace type, scam/ghost-job checks), and Easy Apply screening answers grounded only in your own profile. It never scrapes LinkedIn or automates applications or messages, in line with LinkedIn's User Agreement. Derived from [wing0828/ai-job-search-kr](https://github.com/wing0828/ai-job-search-kr) and [MadsLorentzen/ai-job-search](https://github.com/MadsLorentzen/ai-job-search), MIT.
