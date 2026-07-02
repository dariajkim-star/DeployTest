import os
import random

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="Today's Fortune API")

origins = os.getenv("CORS_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
print(f"[DEBUG] ANTHROPIC_API_KEY loaded: {'YES' if ANTHROPIC_API_KEY else 'NO'}")

FALLBACK_FORTUNES = [
    "오늘은 새로운 기회가 찾아올 거예요. 주변을 잘 살펴보세요.",
    "작은 행운이 쌓여 큰 행복이 되는 하루입니다.",
    "조급해하지 마세요. 천천히 가도 충분히 도착합니다.",
    "오늘 만나는 사람과의 대화에서 좋은 인사이트를 얻을 수 있어요.",
    "예상치 못한 곳에서 기분 좋은 소식이 들려올 수 있어요.",
]


class FortuneRequest(BaseModel):
    name: str
    mbti: str


class FortuneResponse(BaseModel):
    name: str
    mbti: str
    fortune: str


def generate_with_llm(name: str, mbti: str) -> str:
    from anthropic import Anthropic

    client = Anthropic(api_key=ANTHROPIC_API_KEY)
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
def fortune(req: FortuneRequest):
    if ANTHROPIC_API_KEY:
        try:
            text = generate_with_llm(req.name, req.mbti)
            print(text)
        except Exception as e:
            text = random.choice(FALLBACK_FORTUNES)
            print(f'풀백 - 에러: {e}')
    else:
        text = random.choice(FALLBACK_FORTUNES)
        print('풀백2')

    return FortuneResponse(name=req.name, mbti=req.mbti, fortune=text)
