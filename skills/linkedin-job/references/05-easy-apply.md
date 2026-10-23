# Easy Apply 답변 / Easy Apply answers

Easy Apply 양식은 회사마다 질문이 다르다. 사용자가 **질문을 그대로 붙여넣으면** 답변 초안을 만들고, 사용자가 직접 입력·제출한다. 제출 버튼은 대신 누르지 않는다.

## 원칙
- **정직이 최우선.** 스크리닝 질문은 자동 탈락 필터로 쓰인다. 통과하려고 사실과 다르게 답하면 면접·레퍼런스 체크에서 드러난다. 프로필로 답할 수 없는 질문은 추측하지 말고 사용자에게 묻는다.
- **답변은 질문 언어로.** 영어 질문엔 영어, 한국어 질문엔 한국어.
- **민감 정보는 쓰지 않는다.** 주민등록번호, 여권번호, 계좌, 비밀번호는 Easy Apply에 필요 없다. 요구하면 사기 신호로 본다(`04-job-evaluation.md`). `precheck.py`가 주민번호·카드번호 형태를 ERROR로 잡는다.
- **선택 항목(성별·장애·보훈 등 자발적 공개 항목)**은 사용자의 선택이다. 대신 고르지 않고 "응답하지 않음(Prefer not to say)" 선택지가 있다는 것만 알린다.

## 질문 유형별
| 유형 | 예 | 답하는 법 |
|------|---|----------|
| 경력 연수 (숫자) | "How many years of experience do you have with SAP SD?" | `profile.md` 경력 기간을 오늘 기준으로 합산해 **정수로 내림**. 계산식을 사용자에게 보여준다. 겹치는 기간은 한 번만 센다 |
| 예/아니오 자격 | "Are you legally authorized to work in Singapore?" / "Will you require sponsorship?" | 프로필의 근무 자격·스폰서십 칸 그대로. 칸이 비어 있으면 묻는다 |
| 근무 조건 | "Are you comfortable commuting to this job's location?" / "Willing to relocate?" | 프로필의 출퇴근·이주 칸 기준 |
| 희망 연봉 | "What is your expected salary?" | 프로필의 희망 연봉 범위를 **통화와 연 총액(gross) 기준**으로. 숫자 입력칸이면 범위의 하한이 아니라 사용자가 정한 값을 쓴다. 프로필에 없으면 묻는다 |
| 입사 가능일 | "When can you start?" | 프로필의 notice period |
| 언어 수준 | "What is your level of proficiency in English?" | 프로필의 LinkedIn 수준 표기 그대로 |
| 짧은 서술 | "Why are you interested in this role?" (보통 수백 자) | 공고 문장 1개 + 회사에 대한 **확인된** 사실 1개 + 내 근거 경험 1개. 3~5문장 |
| 커버레터 (선택) | 첨부 또는 텍스트 | 원본 커버레터 규칙: 첫 문단에 지원 직함과 핵심 근거, 둘째 문단 대표 성과 2개, 끝에 기여할 일. 한 쪽 이내 |
| 이력서 선택 | 업로드된 이력서 중 선택 | 공고 언어에 맞는 버전. 파일명에 회사명이 남아 있지 않은지 확인 |

글자수 제한이 보이면 사용자에게 제한 값을 받아 맞춘다. 길이는 눈대중하지 말고 스크립트로 잰다:
`python scripts/li_lint.py answers.md --max 500` (제한이 질문마다 다르면 질문별로 파일을 나누거나 가장 작은 값을 쓴다).

## 결과물
`applications/<회사>_<직함>/answers.md`:
```
## Q1: How many years of experience do you have with SAP SD?
> 근거: profile.md 경력 A(2015.03-2020.02), B(2021.01-현재) → 2026-10-23 기준 4y11m + 5y9m = 10y8m → 10
10
```
`>` 메모 줄은 제출 대상이 아니다(근거 기록용). 제출 전 `precheck.py answers.md --profile profile.md --target <회사>`로 검사한다.

## 제출 후
`tracker.py add applications/tracker.csv --company ... --title ... --url ... --source "Easy Apply" --status 지원완료 --applied-on <오늘>`. 후속 연락 시점은 `--next`로 기록하고 `tracker.py list`로 확인한다.
