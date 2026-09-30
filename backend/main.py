import os
import random
import re
import threading
import time
from collections import deque
from datetime import date

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator

app = FastAPI(title="Today's Fortune API")

# 배포 시 CORS_ORIGINS에 프론트 주소를 넣는다. 기본값을 "*"로 두면 아무 사이트나 이 API를 호출해
# 내 Anthropic 크레딧을 쓸 수 있다. 쿠키/인증을 안 쓰므로 credentials도 끈다.
origins = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

# 비용 방어: IP당 분당 요청 수 + 서버 전체 하루 LLM 호출 상한 (넘으면 에러 대신 준비된 문구로 대체)
RATE_LIMIT_PER_MIN = int(os.getenv("RATE_LIMIT_PER_MIN", "10"))
DAILY_LLM_CAP = int(os.getenv("DAILY_LLM_CAP", "300"))

_lock = threading.Lock()
_hits: dict[str, deque] = {}
_llm_calls = {"day": date.today(), "count": 0}
_cache: dict[tuple, str] = {}  # (날짜, 이름, MBTI) -> 운세. 같은 사람이 새로고침해도 LLM을 다시 부르지 않는다


def _allow_request(ip: str) -> bool:
    now = time.monotonic()
    with _lock:
        q = _hits.setdefault(ip, deque())
        while q and now - q[0] > 60:
            q.popleft()
        if len(q) >= RATE_LIMIT_PER_MIN:
            return False
        q.append(now)
        return True


def _take_llm_budget() -> bool:
    with _lock:
        if _llm_calls["day"] != date.today():
            _llm_calls.update(day=date.today(), count=0)
            _cache.clear()
        if _llm_calls["count"] >= DAILY_LLM_CAP:
            return False
        _llm_calls["count"] += 1
        return True

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
print(f"[DEBUG] ANTHROPIC_API_KEY loaded: {'YES' if ANTHROPIC_API_KEY else 'NO'}")

FALLBACK_FORTUNES = [
    "오늘은 새로운 기회가 찾아올 거예요. 주변을 잘 살펴보세요.",
    "작은 행운이 쌓여 큰 행복이 되는 하루입니다.",
    "조급해하지 마세요. 천천히 가도 충분히 도착합니다.",
    "오늘 만나는 사람과의 대화에서 좋은 인사이트를 얻을 수 있어요.",
    "예상치 못한 곳에서 기분 좋은 소식이 들려올 수 있어요.",
]


MBTI_RE = re.compile(r"^[EI][NS][TF][JP]$")


class FortuneRequest(BaseModel):
    # 길이 제한이 없으면 이름칸에 긴 글(프롬프트 인젝션 포함)을 넣어 입력 토큰 비용을 키울 수 있다
    name: str = Field(min_length=1, max_length=20)
    mbti: str

    @field_validator("name")
    @classmethod
    def _clean_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("이름을 입력하세요")
        return v

    @field_validator("mbti")
    @classmethod
    def _check_mbti(cls, v: str) -> str:
        v = v.strip().upper()
        if not MBTI_RE.match(v):
            raise ValueError("MBTI는 INTJ 같은 4글자여야 해요")
        return v


class FortuneResponse(BaseModel):
    name: str
    mbti: str
    fortune: str


_client = None


def generate_with_llm(name: str, mbti: str) -> str:
    global _client
    if _client is None:
        from anthropic import Anthropic
        _client = Anthropic(api_key=ANTHROPIC_API_KEY)  # 요청마다 새로 만들면 커넥션 재사용이 안 된다
    client = _client
    prompt = (
        f"'{name}'님은 MBTI가 '{mbti}'입니다. 이 사람을 위한 오늘의 운세를 "
        "한국어로 2~3문장, 따뜻하고 긍정적인 톤으로 작성해줘."
    )
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=300,
        temperature=0.9,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text.strip()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/fortune", response_model=FortuneResponse)
def fortune(req: FortuneRequest, request: Request):
    ip = request.client.host if request.client else "unknown"
    if not _allow_request(ip):
        raise HTTPException(429, "요청이 너무 많아요. 잠시 후 다시 시도해주세요.")

    key = (date.today(), req.name, req.mbti)
    text = _cache.get(key)
    if text is None:
        if ANTHROPIC_API_KEY and _take_llm_budget():
            try:
                text = generate_with_llm(req.name, req.mbti)
                _cache[key] = text
            except Exception as e:
                text = random.choice(FALLBACK_FORTUNES)
                print(f'풀백 - 에러: {e}')
        else:
            text = random.choice(FALLBACK_FORTUNES)

    return FortuneResponse(name=req.name, mbti=req.mbti, fortune=text)
