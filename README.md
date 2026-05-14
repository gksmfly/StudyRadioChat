# StudyRadioChat

Python으로 만든 가벼운 멀티스레드 소켓 기반 채팅 시스템입니다. 실시간 메시징, 파일 전송, 방 관리, 협업 기능을 제공합니다.

## 주요 기능

- **멀티스레드 아키텍처**: 스레딩을 사용하여 여러 클라이언트 동시 처리
- **방 관리**: 동적 채팅방 생성 및 입장
- **실시간 메시징**: 방의 모든 사용자에게 메시지 브로드캐스트
- **비공개 메시징**: 특정 사용자에게 직접 메시지 전송
- **메시지 히스토리**: 최근 채팅 로그 조회 (Base64 인코딩)
- **채팅 요약**: 키워드 추출을 사용한 AI 기반 요약
- **파일 전송**: 사용자 간 파일 공유
- **핀 메시지**: 방별 공지사항 설정 및 관리
- **일정 관리**: 협업용 일정 추가, 조회, 삭제
- **상태 관리**: 연결 → 인증 → 입장 상태 전환
- **에러 처리**: 포괄적인 에러 코드 및 상태 검증

## 요구사항

- Python 3.10 이상
- 표준 라이브러리만 사용 (외부 의존성 없음)

## 설치

```bash
git clone https://github.com/yourusername/StudyRadioChat.git
cd StudyRadioChat
```

## 빠른 시작

### 1. 서버 시작

```bash
python server.py
```

서버가 `localhost:5001`에서 실행됩니다.

### 2. 클라이언트 시작

별도의 터미널에서:

```bash
python client.py
```

여러 사용자를 테스트하려면 여러 클라이언트 인스턴스를 열어주세요.

## 사용법

### 기본 명령어

```
/id <이름>              사용자 ID 등록
/join <방이름>          채팅방 입장
/leave                  현재 방 나가기
/rooms                  사용 가능한 모든 방 조회
/msg <메시지>           방에 메시지 전송
/whisper <아이디> <메시지>  특정 사용자에게 비공개 메시지 전송
/hist                   최근 20개 메시지 조회
/summary                채팅 요약 조회
/pin_set <내용>         방 공지사항 설정
/pin                    방 공지사항 조회
/pin_clear              방 공지사항 삭제
/sched_add <내용>       일정 추가
/sched                  일정 목록 조회
/sched_clear            모든 일정 삭제
/file <사용자> <경로>    파일 전송 요청
/file_ack <사용자> <응답> 파일 수락/거절
/quit                   연결 종료 및 프로그램 종료
```

### 사용 예제

```
> /id alice
✓ ID 등록 완료

> /join study_group
✓ study_group 방 입장

> /msg 안녕하세요!
✓ 메시지 전송 완료

> /whisper bob 비공개 메시지
✓ bob에게 전송 완료

> /summary
🧠 대화 요약: 주요 키워드 → study, python, project

> /sched_add 중간고사 다음주
✓ 일정 추가 완료

> /file bob homework.pdf
✓ 파일 요청 전송 완료

> /quit
안녕히 가세요!
```

## 아키텍처

### 프로토콜

메시지는 파이프(|)로 구분된 형식으로 전송됩니다:

```
CMD|FROM_ID|TARGET|PAYLOAD\n
```

예시:
```
MSG|alice|study_group|Hello world!\n
WHISPER|alice|bob|비공개 메시지\n
```

### 서버 컴포넌트

- **server.py**: 소켓 처리 및 명령 처리 메인 서버
- **protocol.py**: 메시지 인코딩/디코딩 및 상태 정의
- **utils.py**: 로깅, 히스토리 조회, 요약 기능

### 클라이언트 컴포넌트

- **client.py**: 사용자 인터페이스 및 소켓 통신

## 파일 구조

```
StudyRadioChat/
├── server.py          # 메인 서버
├── client.py          # 클라이언트 애플리케이션
├── protocol.py        # 프로토콜 정의
├── utils.py           # 유틸리티 함수
├── README.md          # 이 파일
└── logs/              # 채팅 로그 (자동 생성)
    └── <방이름>.log
```

## 기술 상세

### 상태 머신

```
CONNECTED (연결됨)
    ↓ (ID_REQ)
IDENTIFIED (인증됨)
    ↓ (JOIN)
JOINED (입장함)
    ↓ (LEAVE)
IDENTIFIED (인증됨)
```

### 명령어 분류

| 분류 | 명령어 |
|------|--------|
| 인증 | ID_REQ, ID_RES |
| 방 관리 | JOIN, LEAVE, ROOMS_REQ |
| 채팅 | MSG, WHISPER, HIST_REQ, SUM_REQ |
| 파일 | FILE_REQ, FILE_ACK, FILE_START, FILE_DATA, FILE_END |
| 방 기능 | PIN_SET, PIN_GET, PIN_CLEAR, SCHED_ADD, SCHED_LIST, SCHED_CLEAR |
| 시스템 | NOTICE, ERROR, QUIT |

### 스레드 안전성

- `threading.Lock`을 사용한 스레드 안전 메시지 전송
- 소켓별 송신 락으로 메시지 손상 방지
- GIL로 보호된 전역 방 및 클라이언트 딕셔너리

### 데이터 영속성

- 채팅 로그는 `./logs/<방이름>.log`에 저장
- 방별 하나의 로그 파일
- 쉬운 검사를 위한 평문 형식

## 제한사항

- 메모리 기반 방 데이터 (서버 재시작 시 손실)
- 사용자 인증 미지원
- 암호화 미지원
- 파일 전송 프로토콜 제한 (Base64 인코딩 오버헤드)
- 클라이언트당 싱글 스레드 (메시지 큐잉 없음)
