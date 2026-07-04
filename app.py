import os
import re
import json
from pathlib import Path
import streamlit as st
from dotenv import load_dotenv
from google import genai
from google.genai import types
from openai import OpenAI
from streamlit_local_storage import LocalStorage

load_dotenv()

STORAGE_KEY = "arcadia_chat_state"


def get_gemini_key():
    try:
        return st.secrets["GEMINI_API_KEY"]
    except Exception:
        return os.getenv("GEMINI_API_KEY")


def get_deepseek_key():
    try:
        return st.secrets["DEEPSEEK_API_KEY"]
    except Exception:
        return os.getenv("DEEPSEEK_API_KEY")


GEMINI_API_KEY = get_gemini_key()
DEEPSEEK_API_KEY = get_deepseek_key()
GEMINI_MODEL = "gemini-2.5-flash"
DEEPSEEK_MODEL = "deepseek-v4-pro"

# 메인: 딥시크 (OpenAI 호환 방식)
if "deepseek_client" not in st.session_state:
    st.session_state.deepseek_client = OpenAI(
        api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com"
    )
deepseek_client = st.session_state.deepseek_client

# 백업: 제미나이
if "genai_client" not in st.session_state:
    st.session_state.genai_client = genai.Client(api_key=GEMINI_API_KEY)
gemini_client = st.session_state.genai_client

OPENING_SCENE = (
    "*새벽 두 시, 침대에 엎드려 휴대폰으로 로판 소설 《핑크 로즈 오브 아르카디아》를 읽던 "
    "당신. 여주인공 로잘린 하르티엔의 가장 친한 친구이자 서브 인물인 '세레나 에델린'이 "
    "결국 후반부에 조용히 사라지는 결말을 보고 씁쓸하게 마지막 화를 넘긴다.*\n\n"
    "\"세레나로 살면 편하긴 하겠다.\" *피식 웃으며 휴대폰을 내려놓으려던 순간, "
    "화면이 이상하게 번쩍인다.*\n\n"
    "\"…어?\" *눈앞이 새하얗게 물들고, 몸이 아래로 꺼지는 듯한 감각과 함께 차가운 바닥의 "
    "감촉이 느껴진다. 천천히 눈을 뜨자 거대한 거울과 낯선 방, 그리고 거울 속에는 검은 "
    "생머리와 푸른 눈동자를 가진 여자가 서 있다.*\n\n"
    "'…설마, 세레나 에델린으로 빙의됐다고?'\n\n"
    "*그렇게 생각한 순간, 문밖에서 낮은 목소리가 들린다.*\n\n"
    "\"세레나.\" \"황태자 전하께서 무도회에 함께 들어가길 원하신답니다.\"\n\n"
    "*원작에는 없던 대사다.*"
)

SYSTEM_PROMPT = """너는 로맨스 판타지 소설 《핑크 로즈 오브 아르카디아》 세계관을 진행하는 스토리텔러(게임 마스터)야.

[세계관]
아르카디아 제국은 대륙의 중심에 위치한 최강의 제국. 푸른색과 금색을 상징으로 쓰는 황실이
"태양의 축복을 받은 혈통"이라 불리며 절대 권력을 쥐고 있다. 겉으로는 하얀 궁전과 황금 장식,
끝없는 연회로 눈부시게 아름답지만, 그 안은 집착·정치·욕망·배신으로 물들어 있고 사랑은
감정보다 권력에 가까운 것으로 여겨진다. 제국은 다음 가문들을 중심으로 움직인다.
- 황실(청색·금색): 카이사르 아르카디아(황태자)가 차기 황위 유력 후보. 조용한 후계 다툼이
  진행 중이다.
- 크로젠 공작가(흑색·은색), '피의 가문': 군권과 전쟁을 지배함. 가주는 데미안. 배신자에게
  자비 없고 냉정하며 자존심이 강한 가풍.
- 루벤하르트 공작가(청색·사파이어), 부의 가문: 보석·무역·사교계를 장악. 가주는 아젤.
  우아해 보이지만 실제로는 누구보다 계산적이고 정보에 능함.
- 발렌티노 공작가(은백색·청색), 정보와 외교의 가문: 가주는 루시엘. 자유롭고 능글맞아
  보이지만 실제로는 누구보다 영리하고 계산적임.
- 에델린 후작가(남색·은색): 화려하게 드러나기보다 조용히 황실과 귀족 사회의 균형을 지켜온
  중립 명문가. 세레나(플레이어)의 친정이며, 장남은 오빠 루카스 에델린. 세레나는 이 집안의
  막내딸로 별명은 '푸른 달의 영애'.
- 하르티엔 백작가(연분홍·금색): 예술 후원과 사교 문화로 유명한 화려한 가문. 영애는 로잘린,
  별명 '핑크 로즈 오브 아르카디아'.
- 로제타 백작가(진홍·검은 장미), '독장미의 가문': 화려함과 권모술수로 악명 높음. 영애는
  비비안.

현실의 플레이어가 에델린 후작가의 막내딸 '세레나 에델린'의 몸에 빙의했다. 원작에서 세레나는
여주인공 로잘린 하르티엔의 가장 친한 친구로, 늘 로잘린 곁에서 도와주고 조용히 뒤를 받쳐주다가
후반부 정치 싸움에 휘말려 조용히 사라지는 조연이었다. 원작에서는 황태자 카이사르를 포함한 모든
남자가 결국 로잘린을 사랑하게 됐지만, 빙의 이후 원작에는 없던 전개로 황태자와 공작들의 관심이
세레나(플레이어)에게 쏠리기 시작한다.

[플레이어 역할]
플레이어는 '세레나 에델린' 그 자체야. 너는 절대 세레나의 대사, 생각, 감정, 행동을 대신 쓰지
않는다. 오직 플레이어가 입력한 내용만이 세레나의 말과 행동이며, 너는 오직 등장인물 자신의
반응과 시점, 그리고 그다음 상황만 이어간다.

[네가 연기하는 등장인물]
아래 인물 중, 지금 장면에 자연스럽게 등장할 만한 인물을 네가 판단해서 등장시키고, 그 인물의
성격과 말투를 살려서 대사를 말해. 한 장면에 여러 인물이 동시에 있어도 된다. 아직 등장하지 않은
인물을 갑자기 아무 맥락 없이 부르지 말고, 이야기 흐름에 맞게 자연스럽게 배치해.

1. 데미안 크로젠 - 남, 27세, 189cm. 흑발, 흑안, 창백한 피부, 검은 제복. 크로젠 공작가 가주로
   아르카디아 제국 최강의 군권을 쥐고 있음. 별명 '피의 공작', '밤을 뒤집어쓴 남자'. 냉정하고
   잔혹하며 집착적. 원하는 건 반드시 손에 넣고, 특히 사랑 앞에서는 파괴적일 만큼 집착함.
   반말, 짧고 단호한 말투.
2. 아젤 루벤하르트 - 남, 28세, 186cm. 남색 머리, 남청색 눈동자, 푸른 사파이어 장식이
   트레이드마크. 루벤하르트 공작가 가주로 아르카디아 제국 최고의 재력과 권력을 가짐. 별명
   '푸른 밤의 공작'. 우아하고 다정해 보이지만 사람을 천천히 옭아매는 위험한 남자. 화를 내는
   대신 상대를 조용히 무너뜨리고, 사랑 앞에서는 집요할 정도로 집착함. 존댓말, 부드럽고
   여유로운 말투.
3. 카이사르 아르카디아 - 남, 26세, 185cm. 찬란한 금발, 푸른빛 눈동자. 아르카디아 제국의
   유일한 '황태자'이자 차기 황위 계승자, '황실의 자존심'이라 불림. 냉철하고 완벽주의적이며
   감정을 잘 드러내지 않고, 권력과 책임 속에서 누구보다 외롭게 살아감. 정치·검술·전략 모두
   뛰어나지만 사람을 믿지 않아 늘 거리를 둠. 격식 있는 말투와 명령조, 가끔 서툰 진심이
   드러남. 오프닝에서 세레나를 무도회에 초대한 사람이 바로 이 카이사르다. '황태자'라는
   지위는 오직 카이사르만의 것이며, 다른 인물(데미안·아젤·루시엘은 모두 '공작'이지 황태자가
   아니다)이 그 초대를 자신이 보낸 것처럼 착각해서 말하지 않도록 주의해.
4. 루시엘 발렌티노 - 남, 27세. 백금발, 보라빛 눈동자, 사람 홀리는 듯한 미소. 발렌티노 공작,
   사교계 최고의 문제아. 장난스럽고 여유로우나 속내를 절대 쉽게 보여주지 않는 위험한 인물.
   능글거리며 사람을 휘두르는 데 능하고, 마음에 든 상대는 끝까지 놀리듯 집착함. 반말에
   장난기 섞인 가벼운 말투.
5. 로잘린 하르티엔 - 여, 24세, 163cm. 눈부신 분홍빛 머리, 장밋빛 눈동자. 하르티엔 백작가
   영애, 원작 여주인공, 별명 '핑크 로즈'. 우아하고 연약해 보이지만 속은 누구보다 냉철하고
   강단 있음. 쉽게 사람을 믿지 않지만 세레나(플레이어)처럼 사랑하는 사람에게는 한없이
   다정함. 다정하고 친근한 말투.
6. 비비안 로제타 - 여, 25세, 171cm. 강렬한 붉은 머리, 치명적인 미소. 로제타 백작가 영애,
   소설 속 악녀로 로잘린을 방해하는 인물. 아름답고 우아하지만 원하는 것을 얻기 위해 수단을
   가리지 않음. 사람의 감정을 가지고 노는 데 능하며 사랑과 질투를 가장 재밌는 게임처럼
   여김. 새침하고 도발적인 말투.

[남성 등장인물 말투 강화 - 매우 중요]
데미안·아젤·카이사르·루시엘은 모두 제국 최상류층의 권력자다. 절대 여성스럽거나 애교 섞인
감탄사·어미("어머", "어멋", "어머나", "~네요오", "~용", "~잖아요오" 등)를 쓰지 마. 감탄이
필요하면 "허", "흠", "그래", "재밌군" 같은 남성적이고 절제된 표현을 써. 각 인물의 지위와
성격이 드러나는 말투를 지켜라.
- 데미안: 반말, 짧고 위압적. 감정을 눌러 담은 단답.
  예) "쓸데없는 소리군." / "따라와. 두 번 말하게 하지 마." / "네가 어디로 도망치든, 결국
  내 앞이야."
- 아젤: 여유롭고 우아한 존댓말 속에 은근한 위협과 소유욕. 부드럽게 옭아맨다.
  예) "혼자 계셨군요. …그거 참, 안심이 안 되는 소식입니다." / "제 눈을 피하실 수 있으리라
  생각하셨습니까?" / "곁을 내어드릴 테니, 다른 이는 볼 것 없습니다."
- 카이사르: 격식 있는 명령조, 절제된 위엄. 감정을 잘 드러내지 않는다.
  예) "가까이 오시오." / "그대에게 선택권은 없소." / "…이건 명령이 아니라, 부탁이오."
- 루시엘: 반말에 능글맞고 장난스럽되 뼈가 있는 여유.
  예) "이런, 혼자 두기엔 아까운데. 내가 데려다줄까?" / "겁먹은 얼굴도 제법이네." / "도망쳐
  봐. 쫓는 재미가 있잖아?"
여성 인물(로잘린·비비안)은 각자 설정된 말투(로잘린=다정, 비비안=도발적)를 유지하되, 역시
과한 애교체는 피한다.

[몰입 유지 규칙]
- 반복 금지: 플레이어의 문장이나 직전 답변의 표현을 그대로 되풀이하지 말고, 항상 새로운
  전개와 묘사를 써.
- 시간 점프 금지: "잠시 후", "며칠 뒤" 같은 요약형 생략 없이, 지금 이 순간의 공기와 미세한
  움직임에 집중해.
- 정적 속의 신호: 인물이 말없이 있을 때도 손짓, 시선, 표정 같은 신체 신호로 감정을 드러내.
- 마무리 멘트 금지: 답변 끝에 교훈·요약·소감을 붙이지 말고, 마지막 대사나 행동에서 바로
  끝내서 긴장감과 여운을 남겨.
- 배경 인물(NPC) 최소화: 주변에 사람이 많아도 서술의 중심은 항상 플레이어와 등장인물 사이의
  거리에 집중하고, 지나가는 행인·시종의 대사를 직접 인용하지 마.
- 설정/사실 고정: 이미 확정된 사건, 관계, 감정 변화, 인물의 등장·퇴장을 절대 잊거나 뒤집지
  마. 플레이어가 "이미 말했잖아", "설정이 틀렸어"라고 지적하면 즉시 인정하고 그 사실에 맞춰
  바로잡아.
- 감정은 누적된다: 호감·애착·신뢰·질투·경계심 같은 감정 변화는 한 번 생기면 다음 턴에도
  유지되고 서서히 깊어지며, 이유 없이 초기화되지 않아.
- 과도한 말줄임표("...", "…")나 인터넷체 끊어쓰기를 남발하지 말고 자연스러운 문장으로 써.
- 세계관에 맞지 않는 현실 요소(현대 물건, 현대어 등)를 등장시키지 마.

[진행 규칙]
- 행동·표정 같은 지문은 *별표 안에*, 대사는 큰따옴표로 구분해서 써.
- 매 답변 끝에는 플레이어가 다시 반응할 수 있는 여지를 남겨.
- 상황 묘사와 대사를 합쳐 5~8문장 정도로, 몰입에 필요한 만큼만 쓰고 불필요한 사족은
  덧붙이지 마.
- 등장인물의 성격과 말투에서 절대 벗어나지 마 (캐릭터 붕괴 금지).

[출력 형식 - 반드시 지킬 것]
답변의 맨 첫 줄에 이번 장면에서 가장 비중있게 말하거나 행동하는 인물 한 명을 아래 형식 그대로 표시해:
[등장인물: 이름]
- 이름에는 위 6명의 이름 중 하나를 정확히 그대로 사용해 (예: [등장인물: 아젤 루벤하르트])
- 특정 인물 없이 순수한 배경 묘사만 있다면 [등장인물: 없음] 이라고 써.
- 이 태그 다음 줄부터 실제 이야기 내용을 이어서 써."""

CHARACTER_IMAGES = {
    "데미안 크로젠": "https://image.zeta-ai.io/profile-image/c3383e0c-66ef-4a90-bdee-681da1539636/f639ab88-1fc4-4fdc-b324-0292ea9e3486.png?w=384&q=75&f=webp",
    "아젤 루벤하르트": "https://image.zeta-ai.io/profile-image/c3383e0c-66ef-4a90-bdee-681da1539636/3647c40b-393d-4e87-85d1-55adafd832b3.png?w=384&q=75&f=webp",
    "로잘린 하르티엔": "https://image.zeta-ai.io/profile-image/c3383e0c-66ef-4a90-bdee-681da1539636/5e9f51da-348c-4c27-be0b-c3ac68c53821.png?w=384&q=75&f=webp",
    "카이사르 아르카디아": "https://image.zeta-ai.io/profile-image/c3383e0c-66ef-4a90-bdee-681da1539636/b3128ebc-ebb9-4f00-83a2-570822dd92a0.png?w=384&q=75&f=webp",
    "비비안 로제타": "https://image.zeta-ai.io/profile-image/c3383e0c-66ef-4a90-bdee-681da1539636/39e17364-d98e-498d-a6e1-8b11d196234e.png?w=384&q=75&f=webp",
    "루시엘 발렌티노": "https://image.zeta-ai.io/profile-image/c3383e0c-66ef-4a90-bdee-681da1539636/b4fcd817-6503-4e86-9bdd-2cd602f92d3a.png?w=384&q=75&f=webp",
}


_serena_file = Path(__file__).parent / "세레나.png"
SERENA_AVATAR = str(_serena_file) if _serena_file.exists() else "🙂"

NARRATOR_AVATAR = "🌹"
CHARACTER_TAG_RE = re.compile(r"^\s*\[등장인물\s*[:：]\s*(.+?)\]\s*\n+")


def split_character_tag(reply):
    match = CHARACTER_TAG_RE.match(reply)
    if not match:
        return NARRATOR_AVATAR, reply
    name = match.group(1).strip()
    text = reply[match.end():]
    return CHARACTER_IMAGES.get(name, NARRATOR_AVATAR), text


def build_system_prompt():
    facts = st.session_state.get("custom_facts", [])
    if not facts:
        return SYSTEM_PROMPT
    facts_text = "\n".join(f"- {fact}" for fact in facts)
    return (
        SYSTEM_PROMPT
        + "\n\n[플레이어가 확정한 설정 - 반드시 지킬 것]\n"
        + "아래 내용은 이야기 전개에서 절대적인 사실이야. 앞으로 이 내용과 모순되는 전개나 "
        + "대사를 절대 만들지 말고, 이야기 진행에 반드시 반영해.\n"
        + facts_text
    )


def build_deepseek_messages():
    """지금까지의 대화를 딥시크(OpenAI 호환) 메시지 목록으로 변환.
    st.session_state.messages 는 이미 맨 끝에 방금 넣은 플레이어 입력을 포함한다."""
    system = (
        build_system_prompt()
        + "\n\n[참고] 플레이어는 이미 아래 오프닝 장면을 봤어. 그다음부터 이어서 진행해.\n"
        + OPENING_SCENE
    )
    msgs = [{"role": "system", "content": system}]
    for m in st.session_state.messages[1:]:
        role = "assistant" if m["role"] == "model" else "user"
        msgs.append({"role": role, "content": m["text"]})
    return msgs


def call_deepseek():
    """메인 AI. 지금까지의 전체 대화를 넘겨서 다음 이야기를 받아온다."""
    response = deepseek_client.chat.completions.create(
        model=DEEPSEEK_MODEL,
        max_tokens=2000,  # 딥시크는 답변 전 '생각'에도 토큰을 써서 여유있게 잡음
        messages=build_deepseek_messages(),
    )
    return response.choices[0].message.content


def call_gemini(user_input):
    """백업 AI. 딥시크가 실패했을 때만 쓰인다. 전체 대화 맥락을 넘겨서 이어간다."""
    history = [
        {"role": m["role"], "parts": [{"text": m["text"]}]}
        for m in st.session_state.messages[1:-1]  # 오프닝과 방금 넣은 입력은 제외
    ]
    chat = gemini_client.chats.create(
        model=GEMINI_MODEL,
        config=types.GenerateContentConfig(
            system_instruction=build_system_prompt(),
            thinking_config=types.ThinkingConfig(thinking_budget=0),
        ),
        history=history,
    )
    return chat.send_message(user_input).text


def generate_reply(user_input):
    # 1순위: 딥시크 (메인)
    try:
        return call_deepseek()
    except Exception:
        pass

    # 2순위: 제미나이 (백업)
    st.info("딥시크가 잠시 응답하지 못해서, 제미나이로 이어서 진행해볼게요.")
    try:
        return call_gemini(user_input)
    except Exception:
        st.error(
            "지금은 딥시크도 제미나이도 응답하지 못했어요. 잠시 후 다시 시도해주세요. "
            "(딥시크 크레딧이 남아있는지, 제미나이 오늘 사용량이 남아있는지 확인해보세요.)"
        )
        return None


def save_to_browser():
    """지금까지의 대화와 설정을 브라우저에 저장 (새로고침해도 유지).
    내용이 바뀌었을 때만 실제로 저장해서 불필요한 반복을 막는다."""
    data = json.dumps(
        {
            "messages": st.session_state.messages,
            "custom_facts": st.session_state.get("custom_facts", []),
        },
        ensure_ascii=False,
    )
    if st.session_state.get("_last_saved") == data:
        return
    st.session_state["_last_saved"] = data
    localS.setItem(STORAGE_KEY, data, key="save_chat")


st.set_page_config(page_title="아르카디아의 푸른 달", page_icon="🌙")

localS = LocalStorage()

# 브라우저에 저장된 이전 대화 복원 (새로고침해도 유지)
def _parse_saved(value):
    """저장된 값을 딕셔너리로 안전하게 해석. 형식이 이상하면 None."""
    for _ in range(3):  # 이중 인코딩된 경우까지 대비해 몇 번 풀어본다
        if isinstance(value, dict):
            return value
        if isinstance(value, str) and value:
            try:
                value = json.loads(value)
            except (ValueError, TypeError):
                return None
        else:
            return None
    return value if isinstance(value, dict) else None


if "messages" not in st.session_state:
    restored = None
    try:
        restored = _parse_saved(localS.getItem(STORAGE_KEY))
    except Exception:
        restored = None

    if restored and isinstance(restored.get("messages"), list) and restored["messages"]:
        st.session_state.messages = restored["messages"]
        facts = restored.get("custom_facts", [])
        st.session_state.custom_facts = facts if isinstance(facts, list) else []
    else:
        st.session_state.custom_facts = []
        st.session_state.messages = [
            {"role": "model", "text": OPENING_SCENE, "avatar": NARRATOR_AVATAR}
        ]

st.markdown(
    """
    <style>
    /* 예쁜 명조체 폰트 불러오기 */
    @import url('https://fonts.googleapis.com/css2?family=Gowun+Batang:wght@400;700&family=Nanum+Myeongjo:wght@400;700;800&display=swap');
    /* 위쪽 헤더 완전히 없애기 (흰 줄 제거) */
    header[data-testid="stHeader"] {display: none !important;}
    /* 하단 "Hosted with Streamlit" 문구·메뉴·배지 숨기기 */
    footer {display: none !important;}
    [data-testid="stToolbar"] {display: none !important;}
    [data-testid="stStatusWidget"] {display: none !important;}
    [data-testid="stDecoration"] {display: none !important;}
    [data-testid="stAppDeployButton"] {display: none !important;}
    .stAppDeployButton {display: none !important;}
    /* 우측 하단 떠있는 배지들 (스트림릿 로고 등) */
    a[href*="streamlit.io"] {display: none !important;}
    a[href*="streamlit.app"] {display: none !important;}
    a[href*="share.streamlit"] {display: none !important;}
    [class*="viewerBadge"] {display: none !important;}
    [class*="profileContainer"] {display: none !important;}
    [class*="_profileContainer"] {display: none !important;}
    [class*="_viewerBadge"] {display: none !important;}
    [class*="_link_"][href*="streamlit"] {display: none !important;}
    div[class*="viewerBadge"] {display: none !important;}
    /* 본문 위쪽 여백 줄이기 */
    .stMainBlockContainer, .block-container {
        padding-top: 1.5rem !important;
        padding-bottom: 1rem !important;
    }
    /* 하단 입력창 영역도 검은색으로 (흰 줄 제거) */
    [data-testid="stBottomBlockContainer"],
    [data-testid="stBottom"] > div {
        background-color: #0D0D0D !important;
    }
    /* 전체 배경 검은색 */
    .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"] {
        background-color: #0D0D0D !important;
    }
    /* 모든 글자에 명조체 적용 */
    .stApp, .stApp p, .stApp li, .stApp span, .stApp label,
    .stApp h1, .stApp h2, .stApp h3, .stApp em, .stApp strong,
    [data-testid="stChatMessageContent"], [data-testid="stChatInput"] textarea {
        font-family: 'Gowun Batang', 'Nanum Myeongjo', serif !important;
    }
    /* 아이콘(화살표 등)은 원래 아이콘 폰트 유지 — 깨짐 방지 */
    [data-testid="stIconMaterial"],
    span[translate="no"],
    .material-symbols-rounded {
        font-family: 'Material Symbols Rounded' !important;
    }
    /* 제목은 조금 더 굵은 명조체로 */
    .stApp h1 {
        font-family: 'Nanum Myeongjo', 'Gowun Batang', serif !important;
        font-weight: 800 !important;
    }
    /* 본문 글자 크기와 줄간격을 소설처럼 여유있게 */
    [data-testid="stChatMessageContent"] p {
        font-size: 1.05rem !important;
        line-height: 1.9 !important;
    }
    /* 기본 글자 흰색 */
    .stApp, .stApp p, .stApp li, .stApp span, .stApp label,
    .stApp h1, .stApp h2, .stApp h3, .stApp em, .stApp strong,
    [data-testid="stChatMessageContent"] {
        color: #F5F5F5 !important;
    }
    /* 캐릭터(상대) 말풍선 배경 */
    div[data-testid="stChatMessage"] {
        background-color: transparent;
    }
    /* 세레나(나) 메시지: 오른쪽 정렬 + 보라색 */
    div[data-testid="stChatMessage"]:has([aria-label="Chat message from user"]) {
        flex-direction: row-reverse;
        margin-left: auto;
        width: fit-content;
        max-width: 85%;
    }
    div[data-testid="stChatMessage"]:has([aria-label="Chat message from user"])
        [data-testid="stChatMessageContent"] {
        text-align: right;
        background-color: #2A1A3E;
        border-radius: 12px;
        padding: 6px 12px;
    }
    /* 세레나(나) 입력 글자만 보라색 */
    div[data-testid="stChatMessage"]:has([aria-label="Chat message from user"])
        [data-testid="stChatMessageContent"] * {
        color: #C77DFF !important;
    }
    /* 입력창 어둡게 */
    [data-testid="stChatInput"] textarea {
        background-color: #1A1A1A;
        color: #F5F5F5;
    }
    /* 접이식 메뉴 배경 */
    [data-testid="stExpander"] {
        border-color: #333333;
    }
    /* 버튼: 보라색 배경 + 흰 글자로 또렷하게 */
    .stButton button {
        background-color: #3D2A5C !important;
        border: 1px solid #6B4E9E !important;
        border-radius: 8px !important;
    }
    .stButton button p,
    .stButton button div,
    .stButton button span {
        color: #F5F5F5 !important;
    }
    .stButton button:hover {
        background-color: #5A3E8A !important;
        border-color: #C77DFF !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# 맨 위 위치 표시 + 떠있는 스크롤 버튼(▲ 맨 위로 / ▼ 맨 아래로)
st.markdown('<div id="page-top"></div>', unsafe_allow_html=True)
st.markdown(
    """
    <a href="#page-top" class="scroll-btn scroll-top" title="맨 위로">▲</a>
    <a href="#page-bottom" class="scroll-btn scroll-bottom" title="맨 아래로">▼</a>
    <style>
    .scroll-btn {
        position: fixed; left: 14px; z-index: 9999;
        width: 42px; height: 42px; border-radius: 50%;
        background-color: #3D2A5C; color: #F5F5F5 !important;
        border: 1px solid #6B4E9E;
        display: flex; align-items: center; justify-content: center;
        font-size: 16px; text-decoration: none; line-height: 1;
        box-shadow: 0 2px 6px rgba(0,0,0,0.4);
    }
    .scroll-btn:hover { background-color: #5A3E8A; }
    .scroll-top { bottom: 205px; }
    .scroll-bottom { bottom: 155px; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("아르카디아의 푸른 달")
st.caption("당신은 '세레나 에델린'입니다. 이야기 속에서 원하는 대로 말하고 행동해보세요.")

with st.expander("등장인물 보기"):
    cols = st.columns(len(CHARACTER_IMAGES))
    for col, (char_name, img_url) in zip(cols, CHARACTER_IMAGES.items()):
        with col:
            st.image(img_url, use_container_width=True)
            st.caption(char_name)

with st.expander("📌 이야기 설정 고정하기"):
    st.caption(
        "결혼, 새 인물 등장처럼 앞으로 절대 바뀌면 안 되는 내용을 적어두면, "
        "AI가 이후 이야기를 쓸 때 항상 이 내용을 사실로 지키고 반영해요."
    )
    for i, fact in enumerate(st.session_state.custom_facts):
        fcol1, fcol2 = st.columns([5, 1])
        fcol1.write(f"- {fact}")
        if fcol2.button("삭제", key=f"del_fact_{i}"):
            st.session_state.custom_facts.pop(i)
            st.rerun()

    new_fact = st.text_input(
        "추가할 설정", placeholder="예: 세레나와 아젤은 이미 비밀리에 약혼했다"
    )
    if st.button("설정 추가") and new_fact.strip():
        st.session_state.custom_facts.append(new_fact.strip())
        st.rerun()

top_col1, top_col2 = st.columns(2)
if top_col1.button("처음부터 다시 시작"):
    st.session_state.messages = [
        {"role": "model", "text": OPENING_SCENE, "avatar": NARRATOR_AVATAR}
    ]
    st.session_state.custom_facts = []
    st.rerun()

# 대화 편집 스위치: 켜면 각 대화 아래에 삭제 버튼이 나타남
edit_mode = top_col2.toggle("🗑️ 대화 편집", help="켜면 특정 대화만 골라서 지울 수 있어요")
if edit_mode:
    st.caption("지우고 싶은 대화 아래의 '이 대화 삭제'를 누르세요. (내 말과 그 답변이 함께 지워져요)")

for i, msg in enumerate(st.session_state.messages):
    if msg["role"] == "model":
        with st.chat_message("assistant", avatar=msg["avatar"]):
            st.write(msg["text"])
            # 편집 스위치가 켜졌을 때만, 오프닝을 제외한 답변에 삭제 버튼 표시
            if edit_mode and i > 0:
                if st.button("🗑️ 이 대화 삭제", key=f"del_msg_{i}"):
                    # 이 답변과 바로 앞의 내 입력을 한 쌍으로 삭제
                    del st.session_state.messages[i]
                    if i - 1 >= 1 and st.session_state.messages[i - 1]["role"] == "user":
                        del st.session_state.messages[i - 1]
                    st.rerun()
    else:
        with st.chat_message("user", avatar=SERENA_AVATAR):
            st.write(msg["text"])

# 맨 아래 위치 표시 (▼ 버튼이 여기로 이동)
st.markdown('<div id="page-bottom"></div>', unsafe_allow_html=True)

user_input = st.chat_input("세레나로서 말하거나 행동해보세요")
if user_input:
    st.session_state.messages.append({"role": "user", "text": user_input})
    with st.chat_message("user", avatar=SERENA_AVATAR):
        st.write(user_input)

    with st.spinner("이야기가 이어지는 중..."):
        raw_reply = generate_reply(user_input)

    if raw_reply:
        avatar, reply_text = split_character_tag(raw_reply)
        with st.chat_message("assistant", avatar=avatar):
            st.write(reply_text)
        st.session_state.messages.append(
            {"role": "model", "text": reply_text, "avatar": avatar}
        )
    else:
        # 응답 실패: 방금 넣은 내 메시지를 되돌려서 다시 시도할 수 있게 함
        st.session_state.messages.pop()

# 화면을 다 그린 뒤, 현재 대화·설정을 브라우저에 저장 (바뀐 게 있을 때만)
save_to_browser()
