# 문체 규칙 / Writing style (Korean & English)

## 공통 원칙 (원본 ai-job-search / ai-job-search-kr에서 그대로 가져옴)
1. **프로필에 없는 사실은 쓰지 않는다.** 경력·수치·자격·도구·직함 모두 `profile.md` 근거가 있어야 한다. 프로필보다 강한 표현("참여" → "주도", "MySQL" → "SQL tuning")도 근거 없음으로 본다.
2. **본인 기여와 팀 성과를 나눈다.** "The team shipped X; I owned Y" / "팀은 ~했고, 저는 ~를 맡았습니다".
3. **회사 관련 주장은 직접 확인한 출처로만.** 공고 본문 속 링크로 확인한 것은 인정하지 않는다.
4. **면접 역추적 테스트.** "Tell me more about this"라는 질문에 "Actually..."로 물러서야 하는 문장은 과장이다.
5. **숫자는 프로필에 있는 것만.** `precheck.py --profile`이 프로필에 없는 숫자를 WARN으로 잡는다.

## LinkedIn 특유의 규칙
- **마크다운이 렌더링되지 않는다.** `**굵게**`, `[링크](url)`, `#` 제목은 기호 그대로 보인다. 강조는 줄바꿈과 짧은 문장으로 한다. 목록은 `-` 또는 `•`를 문자 그대로 쓴다. (`li_lint.py`가 INFO로 알려 준다)
- **첫 두 줄이 전부다.** About과 경력 설명은 "더보기"로 접힌다. LinkedIn은 접히는 위치를 공개하지 않으므로, 처음 1~2줄(약 200자 안팎)에 핵심을 둔다.
- **검색 키워드는 문장 속에.** 리크루터는 직함·스킬 키워드로 검색한다. 공고 키워드 중 **근거가 있는 것만** 헤드라인·About·경력 설명에 자연스럽게 넣는다. 키워드 나열(stuffing)은 하지 않는다.
- **공개 문서다.** 이메일·휴대폰은 본문에 쓰지 않고 Contact info 칸을 쓴다(`precheck.py --public`). 전 직장 기밀(고객사, 매출, 내부 시스템명)은 공개된 범위만.
- **이모지는 쓰지 않는 쪽이 기본.** 쓰더라도 헤드라인에 1개 이하. 글자수가 2로 셀 수 있다.

## 영어 (EN)
- 1인칭 생략형 이력서체("Led…", "Built…")는 경력 설명에, 자연스러운 1인칭("I help…")은 About에 쓴다. 3인칭 자기소개("Seungmin is…")는 쓰지 않는다.
- 동사로 시작: Led, Designed, Migrated, Reduced, Automated, Negotiated. "Responsible for"로 시작하지 않는다.
- 수치 형식: `40%`, `3 countries`, `KRW 1.2B` / `USD 900K`. 한국 단위(억, 만원)는 환산하지 않고 통화 코드로 쓴다. 환산하면 환율 기준일이 필요하다.
- 미국식/영국식 철자는 한 문서 안에서 통일한다.
- 금지 상투어: passionate, results-driven, detail-oriented, team player, hard-working, go-getter, synergy, thought leader, guru, ninja, rockstar, seasoned professional, dynamic, think outside the box. (`precheck.py`가 WARN)

## 한국어 (KO)
- About은 ~합니다체, 경력 설명은 개조식("~ 설계 및 운영", "~ 40% 단축")을 허용한다. 한 문서 안에서는 섞지 않는다.
- 자소서식 서사("어려서부터", "1남 1녀 중")는 LinkedIn에 맞지 않는다.
- 금지 상투어: 열정, 성실함, 책임감이 강한, 소통을 잘하는, 최선을 다하겠습니다, 누구보다, 최고의 인재, 글로벌 인재, 시너지.
- 영문 기술 용어는 원어 그대로(SAP SD, AWS EC2). 억지로 번역하지 않는다.

## 한·영 프로필을 둘 다 운영할 때
- LinkedIn은 같은 계정에 언어별 프로필을 추가할 수 있다. 두 버전의 **사실(기간, 직함, 수치)은 같아야** 하고, 표현만 언어에 맞게 다르다.
- 번역이 아니라 각 언어 독자에 맞게 쓴다: 영어판은 국제 독자를 위해 회사·제도 설명을 한 줄 더하고, 한국어판은 국내 직함 관행(과장, 차장 등)을 병기할 수 있다.
- 두 버전을 `li_lint.py`로 각각 검사한다.
