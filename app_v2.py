import streamlit as st
import tempfile
import os
import json
 
# =========================
# OpenAI Whisper + GPT による音声解析
# =========================
 
def transcribe_audio(audio_bytes: bytes) -> str:
    """WhisperAPIで音声をテキストに変換する"""
    try:
        import openai
        api_key = st.secrets.get("OPENAI_API_KEY", "")
        if not api_key:
            return ""
        client = openai.OpenAI(api_key=api_key)
        with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as f:
            f.write(audio_bytes)
            tmp_path = f.name
        with open(tmp_path, "rb") as f:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=f,
                language="ja"
            )
        os.unlink(tmp_path)
        return transcript.text
    except Exception as e:
        st.error(f"音声認識エラー：{e}")
        return ""
 
 
def parse_shot_from_text(text: str, club_names: list) -> dict:
    """
    OpenAI GPTでテキストからショット情報を抽出する
    戻り値: {"club": "7I", "dist": 150, "result": "FW"} など
    """
    try:
        import openai
        api_key = st.secrets.get("OPENAI_API_KEY", "")
        if not api_key:
            return {}
        client = openai.OpenAI(api_key=api_key)

        clubs_str = "、".join(club_names)
        result_options = "FW、ラフ、OB、池、赤杭、ロスト、空振り、プレ4、プレ3、Gオン"

        prompt = f"""
        以下の発話からゴルフのショット情報を抽出してください。

        発話：「{text}」

        利用可能なクラブ一覧：{clubs_str}
        結果の選択肢：{result_options}

        以下のJSON形式だけで返してください（説明文は不要）：
        {{"club": "クラブ名", "dist": 飛距離の数値, "result": "結果"}}

        判断のルール：
        - クラブは上記一覧から最も近いものを選ぶ（「セブン」→「7I」、「ピーダブ」→「PW」など）
        - 飛距離は数値のみ（単位なし）
        - 結果が明示されていない場合は「FW」とする
        - 「グリーンオン」「乗った」→「Gオン」
        - 「OB」「アウト」→「OB」
        - 飛距離が不明な場合は0とする
        """

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
        )

        raw = response.choices[0].message.content.strip()
        start = raw.find("{")
        end   = raw.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(raw[start:end])

    except Exception as e:
        st.error(f"解析エラー：{e}")

    return {}


# =========================
# スマホ向けグローバルCSS
# =========================
 
st.markdown("""
<style>
 
/* ===== フォント・ベース ===== */
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;700;900&display=swap');
 
html, body, [class*="css"] {
    font-family: 'Noto Sans JP', sans-serif;
}
 
/* ===== 全体の背景 ===== */
.stApp {
    background: #f0f4f8;
}
 
/* ===== ラベル共通 ===== */
.ui-label {
    font-size: 17px;
    font-weight: 700;
    color: #1a2e44;
    display: block;
    margin-top: 20px;
    margin-bottom: 6px;
}
 
.ui-label-small {
    font-size: 22px;
    font-weight: 700;
    color: #4a5568;
    display: block;
    margin-bottom: 4px;
    margin-top: 8px;
}
 
.ui-label-fixed {
    font-size: 16px;
    font-weight: 700;
    color: #1a2e44;
    display: block;
    margin-bottom: 6px;
    margin-top: 10px;
}
 
/* ===== カード風コンテナ ===== */
.card {
    background: white;
    border-radius: 16px;
    padding: 16px;
    margin-bottom: 20px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.08);
}
 
/* ===== 戦略表示行 ===== */
.shot-row {
    background: #dbeafe;
    border-left: 4px solid #3b82f6;
    border-radius: 8px;
    padding: 10px 20px;
    margin: 6px 0;
    font-size: 26px;
    line-height: 1.5;
}
 
.shot-row-history {
    background: #ffffff;
    border-left: 4px solid #60a5fa;
    border-radius: 8px;
    padding: 10px 20px;
    margin: 6px 0;
    font-size: 26px;
    color: #1e40af;
    line-height: 1.5;
}
 
.shot-row-warn {
    background: #fff7ed;
    border-left: 4px solid #f97316;
    border-radius: 8px;
    padding: 10px 20px;
    margin: 6px 0;
    font-size: 26px;
    line-height: 1.5;
}
 
/* ===== 音声入力エリア ===== */
.voice-box {
    background: #f0fdf4;
    border: 2px solid #86efac;
    border-radius: 20px;
    padding: 20px 16px;
    margin: 10px 0 20px 0;
}

.voice-result {
    background: #fefce8;
    border: 2px solid #fde68a;
    border-radius: 10px;
    padding: 10px 20px;
    font-size: 22px;
    font-weight: 700;
    color: #92400e;
    margin-top: 8px;
}

/* ===== 音声入力ウィジェット拡大 ===== */
[data-testid="stAudioInput"] label p {
    font-size: 26px !important;
    font-weight: 700 !important;
    color: #b91c1c !important;
}
[data-testid="stAudioInput"] button {
    width: 72px !important;
    height: 72px !important;
    min-width: 72px !important;
    min-height: 72px !important;
    border-radius: 50% !important;
}
[data-testid="stAudioInput"] button svg {
    width: 38px !important;
    height: 38px !important;
}

/* ===== この内容で反映するボタン拡大 ===== */
div:has(> #voice-apply-anchor) + div[data-testid="stButton"] > button {
    height: 80px !important;
    font-size: 38px !important;
}

/* ===== 入力ボタン ===== */
div:has(#confirm-score-anchor) + div[data-testid="stButton"] > button {
    font-size: 22px !important;
    font-weight: 900 !important;
}

/* ===== 実績をすべてリセットボタン ===== */
[data-testid="stColumn"]:has(#reset-all-anchor) button {
    background-color: #fce7f3 !important;
    border-color: #f472b6 !important;
    color: #9d174d !important;
    font-size: 22px !important;
}

/* ===== コース情報を読み込むボタン拡大 ===== */
div:has(#load-preset-anchor) + div[data-testid="stButton"] > button {
    font-size: 22px !important;
}

/* ===== ホール見出し ===== */
.hole-header {
    background: linear-gradient(135deg, #1a2e44 0%, #2d4a6e 100%);
    color: white;
    border-radius: 20px;
    padding: 20px 18px;
    margin: 10px 0 20px 0;
    display: flex;
    align-items: center;
    justify-content: flex-start;
    gap: 2px;
}
.hole-header h2 {
    margin: 0;
    font-size: 24px;
    font-weight: 900;
    color: white;
    white-space: nowrap;
}
.hole-header .sub {
    font-size: 28px;
    font-weight: 900;
    color: #93c5fd;
    white-space: nowrap;
}
 
/* ===== 残り距離バッジ ===== */
.remain-badge {
    background: linear-gradient(135deg, #065f46, #059669);
    color: white;
    border-radius: 12px;
    padding: 12px 18px;
    font-size: 20px;
    font-weight: 900;
    text-align: center;
    margin: 10px 0;
}
 
/* ===== ボタン共通 ===== */
div[data-testid="stFormSubmitButton"] > button,
div[data-testid="stButton"] > button {
    height: 62px !important;
    font-size: 22px !important;
    font-weight: 700 !important;
    border-radius: 12px !important;
    width: 100% !important;
    padding-top: 0 !important;
    padding-bottom: 0 !important;
    transition: all 0.15s ease;
}
 
div[data-testid="stFormSubmitButton"] > button:active,
div[data-testid="stButton"] > button:active {
    transform: scale(0.97);
}
 
/* ===== ラウンドスコア目標セレクトボックス ===== */
div:has(#target-score-anchor) + div [data-testid="stSelectbox"] > div > div,
div:has(#target-score-anchor) + div [data-testid="stSelectbox"] select {
    font-size: 30px !important;
    font-weight: 700 !important;
}
div:has(#target-score-anchor) + div [data-testid="stSelectbox"] span {
    font-size: 30px !important;
    font-weight: 700 !important;
}
[data-testid="stSelectboxVirtualDropdown"] li,
[data-testid="stSelectboxVirtualDropdown"] li span {
    font-size: 30px !important;
}

/* ===== プリセット選択セレクトボックス（小） ===== */
div:has(#preset-select-anchor) + div [data-testid="stSelectbox"] > div > div,
div:has(#preset-select-anchor) + div [data-testid="stSelectbox"] select {
    font-size: 14px !important;
    min-height: 28px !important;
}
div:has(#preset-select-anchor) + div [data-testid="stSelectbox"] span {
    font-size: 14px !important;
}
div:has(#preset-select-anchor) + div [data-testid="stSelectbox"] label p {
    font-size: 14px !important;
}

/* ===== セレクトボックス ===== */
div[data-testid="stSelectbox"] {
    max-width: 100% !important;
}
 
div[data-testid="stSelectbox"] select,
div[data-testid="stSelectbox"] > div > div {
    font-size: 26px !important;
    min-height: 52px !important;
    font-weight: 700 !important;
    background-color: #fefce8 !important;
}
 
div[data-testid="stSelectbox"] span {
    font-size: 26px !important;
    font-weight: 700 !important;
}
 
/* ===== 数値入力 ===== */
div[data-testid="stNumberInput"] input {
    font-size: 26px !important;
    height: 52px !important;
    font-weight: 700 !important;
    background-color: #fefce8 !important;
}
 
/* ===== チェックボックス ===== */
div[data-testid="stCheckbox"] label {
    font-size: 26px !important;
    font-weight: 700 !important;
}
 
div[data-testid="stCheckbox"] input[type="checkbox"] {
    width: 24px !important;
    height: 24px !important;
    accent-color: #1a2e44;
    cursor: pointer;
    outline: 3px solid #1a2e44 !important;
    outline-offset: 2px;
}
 
/* ===== Expander ===== */
div[data-testid="stExpander"] summary,
div[data-testid="stExpander"] summary p,
div[data-testid="stExpander"] summary span,
div[data-testid="stExpander"] details summary {
    font-size: 22px !important;
    font-weight: 900 !important;
    line-height: 1.2 !important;
}
 
/* ===== フォームのパディング削減 ===== */
div[data-testid="stForm"] {
    background: white;
    border-radius: 16px;
    padding: 16px !important;
    box-shadow: 0 2px 12px rgba(0,0,0,0.08);
    border: none !important;
}
 
/* ===== スコア表の文字 ===== */
.score-cell {
    font-size: 22px;
    padding: 4px 0;
}
 
/* ===== セクション区切り ===== */
.section-divider {
    height: 1px;
    background: #e2e8f0;
    margin: 20px 0;
}
 
/* ===== スライダー ===== */
div[data-testid="stSlider"] {
    padding-top: 4px;
}
 
/* ===== ラジオボタン共通 ===== */
div[data-testid="stRadio"] {
    border: none !important;
    box-shadow: none !important;
    background: transparent !important;
    padding: 0 !important;
    width: 100% !important;
    display: block !important;
}
div[data-testid="stRadio"] [data-testid="stWidgetLabel"] {
    display: none !important;
}
div[data-testid="stRadio"] > div:last-child {
    display: grid !important;
    grid-template-columns: repeat(3, 1fr) !important;
    gap: 6px !important;
    width: 100% !important;
}
div[data-testid="stRadio"] label {
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    height: 60px !important;
    background: white !important;
    border: 2px solid #9ca3af !important;
    border-radius: 8px !important;
    cursor: pointer !important;
    padding: 0 8px !important;
    margin: 0 !important;
    color: #1a1a1a !important;
}
div[data-testid="stRadio"] label p,
div[data-testid="stRadio"] label span {
    font-size: 24px !important;
    font-weight: 700 !important;
    color: #1a1a1a !important;
}
div[data-testid="stRadio"] label:has(input[type="radio"]:checked) {
    background: #1a2e44 !important;
    border-color: #1a2e44 !important;
}
div[data-testid="stRadio"] label:has(input[type="radio"]:checked) p,
div[data-testid="stRadio"] label:has(input[type="radio"]:checked) span {
    color: white !important;
}
div[data-testid="stRadio"] input[type="radio"] {
    display: none !important;
}
 
/* ===== ホール選択グリッド（18択） ===== */
[data-testid="stRadio"] > div:last-child:has(> label:nth-child(18)):not(:has(> label:nth-child(19))) {
    grid-template-columns: repeat(6, 1fr) !important;
}
[data-testid="stRadio"] > div:last-child:has(> label:nth-child(18)):not(:has(> label:nth-child(19))) label > *:first-child {
    display: none !important;
}
 
/* ===== 目標スコアグリッド（8択） ===== */
[data-testid="stRadio"] > div:last-child:has(> label:nth-child(8)):not(:has(> label:nth-child(9))) {
    grid-template-columns: repeat(5, 1fr) !important;
    width: 100% !important;
}
[data-testid="stRadio"] > div:last-child:has(> label:nth-child(8)):not(:has(> label:nth-child(9))) label > *:first-child {
    display: none !important;
}
 
/* ===== パット数グリッド（4択） ===== */
[data-testid="stRadio"] > div:last-child:has(> label:nth-child(4)):not(:has(> label:nth-child(5))) {
    grid-template-columns: repeat(4, 1fr) !important;
    width: 100% !important;
}
[data-testid="stRadio"] > div:last-child:has(> label:nth-child(4)):not(:has(> label:nth-child(5))) label > *:first-child {
    display: none !important;
}
 
/* ===== 最終スコアグリッド（16択） ===== */
[data-testid="stRadio"] > div:last-child:has(> label:nth-child(16)):not(:has(> label:nth-child(17))) {
    grid-template-columns: repeat(4, 1fr) !important;
    width: 100% !important;
}
[data-testid="stRadio"] > div:last-child:has(> label:nth-child(16)):not(:has(> label:nth-child(17))) label > *:first-child {
    display: none !important;
}
 
/* ===== 結果グリッド（10択） ===== */
[data-testid="stRadio"] > div:last-child:has(> label:nth-child(10)):not(:has(> label:nth-child(11))) {
    grid-template-columns: repeat(4, 1fr) !important;
    width: 100% !important;
}
[data-testid="stRadio"] > div:last-child:has(> label:nth-child(10)):not(:has(> label:nth-child(11))) label > *:first-child {
    display: none !important;
}
[data-testid="stRadio"] > div:last-child:has(> label:nth-child(10)):not(:has(> label:nth-child(11))) label p,
[data-testid="stRadio"] > div:last-child:has(> label:nth-child(10)):not(:has(> label:nth-child(11))) label span {
    font-size: 18px !important;
}
[data-testid="stRadio"] > div:last-child:has(> label:nth-child(10)):not(:has(> label:nth-child(11))) label:nth-child(10) p,
[data-testid="stRadio"] > div:last-child:has(> label:nth-child(10)):not(:has(> label:nth-child(11))) label:nth-child(10) span {
    color: #e53e3e !important;
}
 
/* ===== クラブ選択グリッド（11択） ===== */
[data-testid="stRadio"] > div:last-child:has(> label:nth-child(11)):not(:has(> label:nth-child(12))) {
    grid-template-columns: repeat(5, 1fr) !important;
    width: 100% !important;
}
[data-testid="stRadio"] > div:last-child:has(> label:nth-child(11)):not(:has(> label:nth-child(12))) label > *:first-child {
    display: none !important;
}
 
</style>
""", unsafe_allow_html=True)
 
# =========================
# 定数・初期データ
# =========================

PRESET_COURSES = {
    "大阪パブリックゴルフ場（フロント）": {
        "name": "大阪パブリックゴルフ場",
        "tee": "FRO",
        "holes": {
            1:  {"par": 4, "yard": 228},
            2:  {"par": 4, "yard": 282},
            3:  {"par": 5, "yard": 506},
            4:  {"par": 4, "yard": 235},
            5:  {"par": 5, "yard": 410},
            6:  {"par": 3, "yard": 115},
            7:  {"par": 3, "yard": 154},
            8:  {"par": 4, "yard": 226},
            9:  {"par": 3, "yard": 146},
            10: {"par": 4, "yard": 257},
            11: {"par": 3, "yard": 180},
            12: {"par": 3, "yard": 127},
            13: {"par": 5, "yard": 530},
            14: {"par": 4, "yard": 295},
            15: {"par": 4, "yard": 234},
            16: {"par": 4, "yard": 298},
            17: {"par": 4, "yard": 238},
            18: {"par": 4, "yard": 250},
        }
    },
    "大阪パブリックゴルフ場（レディース）": {
        "name": "大阪パブリックゴルフ場",
        "tee": "LADIES",
        "holes": {
            1:  {"par": 4, "yard": 223},
            2:  {"par": 4, "yard": 282},
            3:  {"par": 5, "yard": 435},
            4:  {"par": 4, "yard": 230},
            5:  {"par": 5, "yard": 358},
            6:  {"par": 3, "yard": 112},
            7:  {"par": 3, "yard": 154},
            8:  {"par": 4, "yard": 200},
            9:  {"par": 3, "yard": 146},
            10: {"par": 4, "yard": 255},
            11: {"par": 3, "yard": 178},
            12: {"par": 3, "yard": 127},
            13: {"par": 5, "yard": 418},
            14: {"par": 4, "yard": 292},
            15: {"par": 4, "yard": 232},
            16: {"par": 4, "yard": 298},
            17: {"par": 4, "yard": 234},
            18: {"par": 4, "yard": 250},
        }
    },
    "宝塚ゴルフ倶楽部新C（フロント）": {
        "name": "宝塚ゴルフ倶楽部",
        "tee": "FRO",
        "holes": {
            1:  {"par": 5, "yard": 425},
            2:  {"par": 4, "yard": 276},
            3:  {"par": 3, "yard": 180},
            4:  {"par": 5, "yard": 438},
            5:  {"par": 4, "yard": 316},
            6:  {"par": 4, "yard": 425},
            7:  {"par": 3, "yard": 138},
            8:  {"par": 4, "yard": 424},
            9:  {"par": 4, "yard": 388},
            10: {"par": 5, "yard": 457},
            11: {"par": 4, "yard": 271},
            12: {"par": 3, "yard": 134},
            13: {"par": 4, "yard": 376},
            14: {"par": 4, "yard": 423},
            15: {"par": 3, "yard": 179},
            16: {"par": 4, "yard": 320},
            17: {"par": 5, "yard": 478},
            18: {"par": 4, "yard": 408},
        }
    },
}

CLUBS = [
    {"name": "1W",  "dist": 200, "miss": 0.25, "favorite": 0},
    {"name": "4U",  "dist": 180, "miss": 0.25, "favorite": 0},
    {"name": "5U",  "dist": 170, "miss": 0.25, "favorite": 0},
    {"name": "6I",  "dist": 160, "miss": 0.20, "favorite": 0},
    {"name": "7I",  "dist": 150, "miss": 0.20, "favorite": 0},
    {"name": "8I",  "dist": 140, "miss": 0.18, "favorite": 140},
    {"name": "9I",  "dist": 130, "miss": 0.15, "favorite": 130},
    {"name": "PW",  "dist": 120, "miss": 0.15, "favorite": 120},
    {"name": "UW",  "dist": 110, "miss": 0.15, "favorite": 110},
    {"name": "52°", "dist": 100, "miss": 0.15, "favorite": 100},
    {"name": "56°", "dist":  80, "miss": 0.15, "favorite":  80},
]
 
CLUB_OPTIONS = [
    "（未選択）",
    "1W", "3W", "5W",
    "3U", "4U", "5U", "6U",
    "5I", "6I", "7I", "8I", "9I",
    "PW", "AW", "UW",
    "SW", "52°", "56°", "58°", "60°"
]
 
if "clubs" not in st.session_state:
    st.session_state.clubs = CLUBS.copy()
if "selected_club" not in st.session_state:
    st.session_state.selected_club = CLUBS[0]["name"]
 
if "course" not in st.session_state:
    st.session_state.course = {
        1:  {"par": 5, "yard": 425},
        2:  {"par": 4, "yard": 276},
        3:  {"par": 3, "yard": 180},
        4:  {"par": 5, "yard": 438},
        5:  {"par": 4, "yard": 316},
        6:  {"par": 4, "yard": 425},
        7:  {"par": 3, "yard": 138},
        8:  {"par": 4, "yard": 424},
        9:  {"par": 4, "yard": 388},
        10: {"par": 5, "yard": 457},
        11: {"par": 4, "yard": 271},
        12: {"par": 3, "yard": 134},
        13: {"par": 4, "yard": 376},
        14: {"par": 4, "yard": 423},
        15: {"par": 3, "yard": 179},
        16: {"par": 4, "yard": 320},
        17: {"par": 5, "yard": 478},
        18: {"par": 4, "yard": 408},
    }
 
# =========================
# クラブ選択ロジック
# =========================
 
def get_valid_clubs():
    return [
        c for c in st.session_state.clubs
        if c["dist"] > 0 and c["name"] != "なし"
    ]
 
def choose_club(remaining, shots_left, is_first_shot, par_num, hole):
 
    valid_clubs = get_valid_clubs()
 
    if not valid_clubs:
        return {"name": "なし", "dist": 0, "miss": 1.0}
 
    danger_scores = {
        "バンカー": 50,
        "池": 120,
        "OBゾーン": 300,
        "谷越え": 80,
        "ドッグレッグ": 40,
    }
 
    if is_first_shot:
 
        if shots_left == 1:
            reachable = [c for c in valid_clubs if c["dist"] >= remaining]
            if reachable:
                return min(reachable, key=lambda c: c["dist"])
 
        if remaining <= 220:
            safe_clubs = [c for c in valid_clubs if c["dist"] < remaining]
            if safe_clubs:
                return min(safe_clubs, key=lambda c: abs(c["dist"] - remaining))
 
        safe_clubs = []
        for club in valid_clubs:
            danger_hit = False
            for i in range(1, 3):
                dtype  = st.session_state.get(f"danger_type_{hole}_{i}",  "未入力")
                dstart = st.session_state.get(f"danger_start_{hole}_{i}", 0)
                dend   = st.session_state.get(f"danger_end_{hole}_{i}",   0)
                if dtype != "未入力" and dstart <= club["dist"] <= dend:
                    danger_hit = True
            if not danger_hit:
                safe_clubs.append(club)
 
        if safe_clubs:
            return max(safe_clubs, key=lambda c: c["dist"])
        return max(valid_clubs, key=lambda c: c["dist"])
 
    if shots_left == 1:
        reachable = [c for c in valid_clubs if c["dist"] >= remaining]
        if reachable:
            return min(reachable, key=lambda c: c["dist"])
        return max(valid_clubs, key=lambda c: c["dist"])
 
    if shots_left > 1:
        favorite_targets = [c["favorite"] for c in valid_clubs if c.get("favorite", 0) > 0]
        target = (remaining - min(favorite_targets)) if favorite_targets else (remaining / shots_left)
    else:
        target = remaining
 
    if par_num == 5 and not is_first_shot and shots_left >= 2 and remaining > 180:
        target = remaining * 0.7
 
    best = None
    best_score = 999
 
    for club in valid_clubs:
 
        favorite = club.get("favorite", 0)
 
        danger_penalty = 0
        for i in range(1, 3):
            dtype  = st.session_state.get(f"danger_type_{hole}_{i}",  "未入力")
            dstart = st.session_state.get(f"danger_start_{hole}_{i}", 0)
            dend   = st.session_state.get(f"danger_end_{hole}_{i}",   0)
            if dtype != "未入力" and dstart <= club["dist"] <= dend:
                danger_penalty += danger_scores.get(dtype, 0)
 
        if club["name"] == "1W":
            continue
        if shots_left > 1 and club["dist"] >= remaining:
            continue
        if shots_left == 2:
            longest = max(c["dist"] for c in valid_clubs)
            if remaining - club["dist"] > longest:
                continue
 
        good      = club["dist"]
        miss_dist = club["dist"] * 0.6
        miss_rate = club["miss"]
 
        expected_after = (
            (1 - miss_rate) * (remaining - good)
            + miss_rate * (remaining - miss_dist)
        )
 
        favorite_penalty        = abs(expected_after - favorite) if favorite > 0 else 0
        distance_balance_penalty = 80 if (shots_left > 1 and expected_after < club["dist"] * 0.5) else 0
 
        next_best = min(abs(expected_after - c["dist"]) for c in valid_clubs)
 
        score = (
            expected_after
            + next_best * (3 / shots_left)
            + abs(club["dist"] - target)
            + favorite_penalty * 2
            + distance_balance_penalty
            + danger_penalty
        )
 
        if score < best_score:
            best_score = score
            best = club
 
    if best is None:
        reachable = [c for c in valid_clubs if c["dist"] >= remaining]
        best = min(reachable, key=lambda c: c["dist"]) if reachable else max(valid_clubs, key=lambda c: c["dist"])
 
    return best
 
 
def plan(total_dist, strokes, used, par_num, hole):
    result    = []
    remaining = total_dist
 
    for i in range(strokes):
        shots_left    = strokes - i
        is_first_shot = (used + i == 0)
 
        club = choose_club(remaining, shots_left, is_first_shot, par_num, hole)
 
        if len(result) == strokes - 1:
            reachable = [c for c in st.session_state.clubs if c["dist"] >= remaining]
            if reachable:
                club = min(reachable, key=lambda c: c["dist"])
 
        shot_dist = club["dist"]
        result.append({
            "shot":   i + 1,
            "club":   club["name"],
            "dist":   shot_dist,
            "remain": max(remaining - shot_dist, 0),
            "before": remaining,
        })
        remaining = max(remaining - shot_dist, 0)
 
    return result
 
# =========================
# ホール難易度・目標打数計算
# =========================
 
def calc_hole_targets(target_score):
    hole_difficulty = {}
    for h, data in st.session_state.course.items():
        yard = data["yard"]
        par  = data["par"]
        score = yard / 100
        if par == 5:
            score -= 3
        elif par == 3:
            score += 1
        if par == 4 and yard > 380:
            score += 1.5
        hole_difficulty[h] = score
 
    total_par    = sum(h["par"] for h in st.session_state.course.values())
    sorted_holes = sorted(hole_difficulty.items(), key=lambda x: x[1])
 
    average_diff = (target_score - total_par) / 18
    base_diff    = int(average_diff)
 
    hole_targets = {h: data["par"] + base_diff for h, data in st.session_state.course.items()}
 
    current_total = sum(hole_targets.values())
    diff_total    = target_score - current_total
 
    if diff_total < 0:
        idx = 0
        while diff_total < 0 and idx < len(sorted_holes):
            h = sorted_holes[idx][0]
            if hole_targets[h] > st.session_state.course[h]["par"]:
                hole_targets[h] -= 1
                diff_total += 1
            else:
                idx += 1
    elif diff_total > 0:
        harder = sorted_holes[::-1]
        idx = 0
        while diff_total > 0 and idx < len(harder):
            h = harder[idx][0]
            hole_targets[h] += 1
            diff_total -= 1
            idx += 1
 
    return hole_targets

def calc_remaining_targets(target_score):
    """実績済みホールを固定し、残りホールに残予算を配分する"""
    holes = sorted(st.session_state.course.keys())

    actual_sum      = 0
    remaining_holes = []
    for h in holes:
        actual = st.session_state.get(f"actual_{h}", "")
        if actual != "":
            actual_sum += int(actual)
        else:
            remaining_holes.append(h)

    # 全ホール未入力なら通常計算
    if not remaining_holes or actual_sum == 0:
        return calc_hole_targets(target_score)

    remaining_budget = target_score - actual_sum
    remaining_par    = sum(st.session_state.course[h]["par"] for h in remaining_holes)

    # 残りホールの難易度
    hole_difficulty = {}
    for h in remaining_holes:
        data  = st.session_state.course[h]
        yard  = data["yard"]
        par   = data["par"]
        score = yard / 100
        if par == 5:  score -= 3
        elif par == 3: score += 1
        if par == 4 and yard > 380: score += 1.5
        hole_difficulty[h] = score

    sorted_remaining = sorted(hole_difficulty.items(), key=lambda x: x[1])

    average_diff = (remaining_budget - remaining_par) / len(remaining_holes) if remaining_holes else 0
    base_diff    = int(average_diff)

    # 実績済みホールは元の計画値を維持（表示用）、残りホールは新たに配分
    original_targets = calc_hole_targets(target_score)
    hole_targets = {}
    for h in holes:
        actual = st.session_state.get(f"actual_{h}", "")
        if actual != "":
            hole_targets[h] = original_targets[h]  # 計画は元の値を維持
        else:
            hole_targets[h] = st.session_state.course[h]["par"] + base_diff

    # 残りホールのみ調整
    current_remaining_total = sum(hole_targets[h] for h in remaining_holes)
    diff_total = remaining_budget - current_remaining_total

    if diff_total < 0:
        idx = 0
        while diff_total < 0 and idx < len(sorted_remaining):
            h = sorted_remaining[idx][0]
            if hole_targets[h] > st.session_state.course[h]["par"]:
                hole_targets[h] -= 1
                diff_total += 1
            else:
                idx += 1
    elif diff_total > 0:
        harder = sorted_remaining[::-1]
        idx = 0
        while diff_total > 0 and idx < len(harder):
            h = harder[idx][0]
            hole_targets[h] += 1
            diff_total -= 1
            idx += 1

    return hole_targets

# =========================
# スコア名・色ヘルパー
# =========================
 
def score_info(diff):
    if diff <= -1:
        return "★ バーディ", "#8B0000"
    elif diff == 0:
        return "◎ パー",     "#e53e3e"
    elif diff == 1:
        return "○ ボギー",   "#2b6cb0"
    elif diff == 2:
        return "△ ダブル",   "#276749"
    else:
        return "▼ トリプル+", "#2d3748"
 
# =========================
# ホールスコアテーブル描画
# =========================
 
def render_score_table(holes, hole_targets):
 
    for h in holes:
        par    = st.session_state.course[h]["par"]
        yard   = st.session_state.course[h]["yard"]
        target = hole_targets[h]
        diff   = target - par
        label, color = score_info(diff)
 
        label_text    = label.split(' ', 1)[1] if ' ' in label else label
        strategy_html = f"<span style='color:{color}; font-weight:700; font-size:26px;'>計画 {target}{label_text}</span>"
        actual        = st.session_state.get(f"actual_{h}", "")
        deviation     = ""
        dev_color     = "#1a1a1a"
        if actual != "":
            gap = int(actual) - target
            if gap > 0:
                deviation = f"+{gap}"
                dev_color = "#dc2626"
            elif gap < 0:
                deviation = str(gap)
                dev_color = "#2563eb"
            else:
                deviation = "±0"
                dev_color = "#1a1a1a"
 
        r1, r2 = st.columns([1.2, 2.0])
        with r1: st.markdown(f"<div class='score-cell' style='font-size:26px;'><b>{h}番</b> Par{par}&nbsp;&nbsp;{yard}y</div>", unsafe_allow_html=True)
        with r2: st.markdown(f"<div class='score-cell'>{strategy_html}</div>", unsafe_allow_html=True)
 
        if actual != "":
            actual_diff = int(actual) - par
            actual_label, actual_color = score_info(actual_diff)
            actual_name = actual_label.split(' ', 1)[1] if ' ' in actual_label else actual_label
            st.markdown(
                f"<div class='score-cell' style='padding-left:8px; font-size:26px;'>"
                f"<span style='color:{actual_color}; font-weight:700;'>実績{actual}{actual_name}</span>"
                f"　<span style='color:{dev_color}; font-weight:700;'>差異{deviation}</span>"
                f"</div>",
                unsafe_allow_html=True
            )
 
        st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)
 
# ============================================================
# アプリ本体
# ============================================================
 
st.markdown('<div style="font-size:22px; font-weight:900; color:#1a2e44; margin-bottom:6px;">⛳ AIキャディLite</div>', unsafe_allow_html=True)
 
# ---------- ラウンド目標 ----------
goal_col1, goal_col2 = st.columns([1, 1])
 
with goal_col1:
    st.markdown('<div style="font-size:22px; font-weight:900; color:#1a2e44; margin-top:20px; margin-bottom:6px;">⛳ ラウンドスコア目標</div>', unsafe_allow_html=True)
 
with goal_col2:
    st.markdown('<div id="target-score-anchor"></div>', unsafe_allow_html=True)
    target_score = st.selectbox(
        "",
        list(range(60, 151)),
        index=40,
        key="target_score",
        label_visibility="collapsed"
    )
 
# adjust_plan: 当初目標達成に向けて残りホールを再配分するかどうか
if "adjust_plan"       not in st.session_state: st.session_state.adjust_plan       = False
if "adjust_plan_asked" not in st.session_state: st.session_state.adjust_plan_asked = False
# 目標スコアが変わったらフラグをリセット
if st.session_state.get("_last_target_score") != target_score:
    st.session_state.adjust_plan       = False
    st.session_state.adjust_plan_asked = False
    st.session_state["_last_target_score"] = target_score

# ショット戦略用の hole_targets
if st.session_state.adjust_plan:
    hole_targets = calc_remaining_targets(target_score)   # 当初目標に向けて再配分
else:
    hole_targets = calc_hole_targets(target_score)        # 元の計画

# ---------- ラウンドスコア戦略（折りたたみ） ----------
with st.expander(f"目標{target_score}の計画＆実績", expanded=False):
    holes = sorted(st.session_state.course.keys())
    render_score_table(holes, hole_targets)

# ---------- 現状の見込み ----------
holes           = sorted(st.session_state.course.keys())
total_par       = sum(st.session_state.course[h]["par"] for h in holes)
original_targets = calc_hole_targets(target_score)
projected_total = 0
completed_count = 0
for h in holes:
    actual = st.session_state.get(f"actual_{h}", "")
    if actual != "":
        projected_total += int(actual)
        completed_count += 1
    else:
        projected_total += original_targets[h]

diff_from_target = projected_total - target_score
diff_from_par    = projected_total - total_par

target_str   = f"+{diff_from_target}" if diff_from_target > 0 else ("±0" if diff_from_target == 0 else str(diff_from_target))
target_color = "#dc2626" if diff_from_target > 0 else ("#2563eb" if diff_from_target < 0 else "#1a1a1a")
par_str      = f"+{diff_from_par}" if diff_from_par > 0 else ("±0" if diff_from_par == 0 else str(diff_from_par))
par_color    = "#dc2626" if diff_from_par > 0 else ("#2563eb" if diff_from_par < 0 else "#1a1a1a")

st.markdown(
    f"<div style='background:#f0f9ff; border:2px solid #7dd3fc; border-radius:10px; padding:12px 16px; margin-top:8px;'>"
    f"<div style='font-size:24px; font-weight:700; color:#1a1a1a;'>現状の見込みスコア　<b style='font-size:28px;'>{projected_total}</b></div>"
    f"<div style='font-size:24px; font-weight:700; margin-top:0px;'>"
    f"目標比：<span style='color:{target_color}; font-size:26px;'>{target_str}</span>"
    f"　パー比：<span style='color:{par_color}; font-size:26px;'>{par_str}</span>"
    f"</div>"
    f"</div>",
    unsafe_allow_html=True
)

# 連続3ホールで目標比+6以上の場合：計画変更を提案
_completed_holes = [h for h in holes if st.session_state.get(f"actual_{h}", "") != ""]
_trigger = False
for _i in range(len(_completed_holes) - 2):
    _window = _completed_holes[_i:_i + 3]
    _window_dev = sum(
        int(st.session_state.get(f"actual_{h}", 0)) - original_targets[h]
        for h in _window
    )
    if _window_dev >= 6:
        _trigger = True
        break

if _trigger and not st.session_state.adjust_plan:
    remaining_count = 18 - completed_count
    if remaining_count > 0:
        st.markdown(
            f"<div style='background:#fef2f2; border:2px solid #fca5a5; border-radius:10px; "
            f"padding:10px 16px; margin-top:8px; font-size:22px; font-weight:700; color:#991b1b;'>"
            f"⚠️ 目標達成が難しくなっています（見込み {projected_total}）。<br>"
            f"目標{target_score}達成のために今後の計画を変更しますか？"
            f"</div>",
            unsafe_allow_html=True
        )
        yes_col, no_col, _ = st.columns([1, 1, 1])
        with yes_col:
            if st.button("はい（計画を変更）", key="btn_adjust_yes", use_container_width=True):
                st.session_state.adjust_plan       = True
                st.session_state.adjust_plan_asked = True
                st.rerun()
        with no_col:
            if st.button("いいえ（このまま）", key="btn_adjust_no", use_container_width=True):
                st.session_state.adjust_plan_asked = True
                st.rerun()

# 計画変更中の表示
if st.session_state.adjust_plan:
    st.markdown(
        f"<div style='background:#f0fdf4; border:2px solid #86efac; border-radius:10px; "
        f"padding:8px 16px; margin-top:8px; font-size:20px; font-weight:700; color:#166534;'>"
        f"✅ 目標{target_score}達成に向けて残りホールの計画を再設定しました"
        f"</div>",
        unsafe_allow_html=True
    )
    if st.button("元の計画に戻す", key="btn_adjust_cancel", use_container_width=False):
        st.session_state.adjust_plan = False
        st.rerun()
 
st.markdown("<div style='margin-top:8px'></div>", unsafe_allow_html=True)
 
# ---------- ホール選択 ----------
st.markdown('<div style="font-size:22px; font-weight:900; color:#1a2e44; margin-top:20px; margin-bottom:6px;">⛳ ホールを選択</div>', unsafe_allow_html=True)

# 実績済みホールを黄色にする動的CSS
_hole_keys = list(st.session_state.course.keys())
_done_css  = ""
for _idx, _h in enumerate(_hole_keys, start=1):
    if st.session_state.get(f"actual_{_h}", "") != "":
        _done_css += (
            f"div:has(#hole-select-anchor) + div [data-testid='stRadio'] > div:last-child"
            f" > label:nth-child({_idx}) {{ background:#fef9c3 !important; border-radius:8px !important; }}\n"
        )
if _done_css:
    st.markdown(f"<style>{_done_css}</style>", unsafe_allow_html=True)

st.markdown('<div id="hole-select-anchor"></div>', unsafe_allow_html=True)
hole = st.radio(
    "",
    _hole_keys,
    key="hole_select",
    label_visibility="collapsed",
    horizontal=True,
)
 
TOTAL_DIST = st.session_state.course[hole]["yard"]
par_num    = st.session_state.course[hole]["par"]
 
st.markdown(
    f"""
    <div class="hole-header">
        <h2>⛳ {hole}番ホール</h2>
        <div class="sub">{TOTAL_DIST}y ／ Par {par_num}</div>
    </div>
    """,
    unsafe_allow_html=True
)
 
if "prev_hole" not in st.session_state:
    st.session_state.prev_hole = hole
 
if hole != st.session_state.prev_hole:
    st.session_state.remaining    = TOTAL_DIST
    st.session_state.history      = []
    st.session_state.prev_hole    = hole
    st.session_state.green_on_flag = False
 
if "remaining" not in st.session_state:
    st.session_state.remaining = TOTAL_DIST
if "history" not in st.session_state:
    st.session_state.history = []
 
# ---------- AI推奨・打数・パット設定 ----------
recommended_score = hole_targets[hole]
diff              = recommended_score - par_num
label, rec_color  = score_info(diff)
 
label_text = label.split(' ', 1)[1] if ' ' in label else label

target       = recommended_score
putts        = 2
shot_strokes = target - putts
 
 
for i in range(1, 3):
    st.session_state[f"danger_type_{hole}_{i}"]  = "未入力"
    st.session_state[f"danger_start_{hole}_{i}"] = 0
    st.session_state[f"danger_end_{hole}_{i}"]   = 0
 
# =========================
# ショット戦略表示
# =========================
 
 
st.markdown(
    f"<div style='background:linear-gradient(135deg,#064e3b,#065f46); color:white; border-radius:20px; padding:20px 18px; margin:10px 0 20px 0; display:flex; align-items:center; gap:8px;'>"
    f"<span style='font-size:24px; font-weight:900; white-space:nowrap; margin-right:16px;'>ショット戦略</span>"
    f"<span style='font-size:24px; font-weight:900; color:#6ee7b7; white-space:nowrap;'>{recommended_score}打／{label_text}</span>"
    f"</div>",
    unsafe_allow_html=True
)
 
current_shot = 1
for h in st.session_state.history:
    result_text = {
        "OB":    "OB（1打罰）",
        "池":    "池（1打罰）",
        "赤杭":  "赤杭（1打罰）",
        "ロスト": "ロスト（2打罰）",
        "空振り": "空振り",
        "FW":    "FW",
        "ラフ":  "ラフ",
        "プレ4": "プレ4（2打罰）",
        "プレ3": "プレ3（1打罰）",
    }.get(h.get("result", ""), "")
 
    green_on_mark = " <span style='font-size:20px;'>🚩グリーンオン</span>" if h.get("green_on") else ""
    suffix = f" ⚡ {result_text}" if result_text else ""
    st.markdown(
        f"<div class='shot-row-history'>"
        f"✅ （実績）：{h['club']} {h['dist']}y{green_on_mark}{suffix}"
        f"</div>",
        unsafe_allow_html=True
    )
    current_shot += 1
    current_shot += h.get("penalty", 0)
 
used              = sum(1 + h.get("penalty", 0) for h in st.session_state.history)
remaining_strokes = shot_strokes - used
 
if st.session_state.remaining == 0:
    st.markdown(
        f"<div class='shot-row'><strong>パット {putts}回</strong></div>",
        unsafe_allow_html=True
    )
elif remaining_strokes > 0:
    plan_data      = plan(st.session_state.remaining, remaining_strokes, used, par_num, hole)
    shots_to_green = next((i + 1 for i, p in enumerate(plan_data) if p["remain"] == 0), len(plan_data))
 
    for i, p in enumerate(plan_data):
        if p["before"] == 0:
            continue
        display_dist  = min(p["dist"], p["before"])
        is_last       = (i == len(plan_data) - 1)
        green_on_here = (p["remain"] == 0)
 
        if green_on_here or (is_last and display_dist >= p["before"]):
            st.markdown(
                f"<div class='shot-row'><strong>{p['club']} ／{display_dist}y</strong>（🚩Gオン！）</div>",
                unsafe_allow_html=True
            )
            margin = remaining_strokes - shots_to_green
            if margin > 0:
                st.markdown(
                    f"<div style='background:#dcfce7; border-left:4px solid #16a34a; border-radius:8px; padding:10px 20px; margin-top:8px; font-size:22px; font-weight:700; color:#15803d;'>"
                    f"🟢 {margin}打余裕があります</div>",
                    unsafe_allow_html=True
                )
            st.markdown(
                f"<div class='shot-row'><strong>パット {putts}回</strong></div>",
                unsafe_allow_html=True
            )
            break
        elif is_last:
            st.markdown(
                f"<div class='shot-row-warn'><strong>{p['club']} ／{display_dist}y</strong>（残 {max(p['before'] - display_dist, 0)}y）</div>",
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                f"<div class='shot-row'><strong>{p['club']} ／{display_dist}y</strong>（残 {max(p['before'] - display_dist, 0)}y）</div>",
                unsafe_allow_html=True
            )
elif remaining_strokes == 0:
    st.error("⚠️ この計画では届きません")
else:
    st.error("ショット数が不足しています")
 
 # =========================
# 最終スコア入力
# =========================
 
st.markdown("<div class='section-divider' style='margin:8px 0;'></div>", unsafe_allow_html=True)
st.markdown('<div style="font-size:22px; font-weight:900; color:#1a2e44; margin-top:4px; margin-bottom:6px;">⛳ このホールの最終スコア</div>', unsafe_allow_html=True)
 
def get_score_name(score, par):
    diff = score - par
    if score == 1:
        return "ホールインワン🌸！！", "#e53e3e"
    elif diff <= -3:
        return "アルバトロス！！！", "#7c3aed"
    elif diff == -2:
        return "イーグル！！", "#f97316"
    elif diff == -1:
        return "バーディー！！", "#2563eb"
    elif diff == 0:
        return "パー！", "#1a1a1a"
    elif diff == 1:
        return "ボギー", "#059669"
    elif diff == 2:
        return "ダブルボギー", "#7c3aed"
    else:
        return "トリプルボギー以上", "#7f1d1d"
 
current_score = st.session_state.get(f"final_score_input_{hole}", par_num)
if isinstance(current_score, str):
    current_score = int(current_score.replace("打", ""))
sname, scolor = get_score_name(current_score, par_num)
st.markdown(
    f"<div style='font-size:24px; font-weight:700; color:{scolor}; margin-bottom:4px;'>{current_score}打　{sname}</div>",
    unsafe_allow_html=True
)
 
final_score = st.radio(
    "",
    list(range(1, 17)),
    index=max(current_score - 1, 0),
    key=f"final_score_input_{hole}",
    label_visibility="collapsed",
    horizontal=True,
)

st.markdown('<div id="confirm-score-anchor"></div>', unsafe_allow_html=True)
if st.button("入力", key="btn_confirm_score", use_container_width=True):
    st.session_state[f"actual_{hole}"] = final_score
    st.rerun()

if "reset_confirm" not in st.session_state:
    st.session_state.reset_confirm = False

reset_col, _, __ = st.columns([1, 1, 1])
with reset_col:
    st.markdown('<div id="reset-all-anchor"></div>', unsafe_allow_html=True)
    if st.button("全てリセット", key="btn_reset_all", use_container_width=True):
        st.session_state.reset_confirm = True

if st.session_state.reset_confirm:
    st.markdown(
        "<div style='background:#fef2f2; border:2px solid #fca5a5; border-radius:10px; "
        "padding:10px 16px; margin-top:8px; font-size:22px; font-weight:700; color:#991b1b;'>"
        "⚠️ ほんとにリセットしますか？</div>",
        unsafe_allow_html=True
    )
    yes_col, no_col, _ = st.columns([1, 1, 1])
    with yes_col:
        if st.button("はい", key="btn_reset_yes", use_container_width=True):
            st.session_state.history       = []
            st.session_state.green_on_flag = False
            st.session_state.reset_confirm = False
            st.session_state.pop("hole_select", None)
            st.session_state.remaining     = st.session_state.course[1]["yard"]
            for h in st.session_state.course.keys():
                st.session_state.pop(f"actual_{h}", None)
                st.session_state.pop(f"final_score_input_{h}", None)
            st.rerun()
    with no_col:
        if st.button("いいえ", key="btn_reset_no", use_container_width=True):
            st.session_state.reset_confirm = False
            st.rerun()
 
# =========================
# クラブ設定
# =========================
 
st.divider()
 
with st.expander("⚙️ クラブ設定", expanded=False):
 
    if st.button("クラブ設定を初期に戻す", use_container_width=True):
        st.session_state.clubs = CLUBS.copy()
        for k in list(st.session_state.keys()):
            if k.startswith(("name_", "dist_", "miss_")):
                del st.session_state[k]
        st.rerun()
 
    edited_clubs = []
 
    for i, c in enumerate(st.session_state.clubs):
        uid = f"{i}_{c['name']}"
 
        st.markdown("<div style='font-size:13px; font-weight:600; color:#4a5568; margin-top:6px; margin-bottom:-16px;'>クラブ</div>", unsafe_allow_html=True)
        name = st.selectbox("", CLUB_OPTIONS,
            index=CLUB_OPTIONS.index(c["name"]) if c["name"] in CLUB_OPTIONS else 0,
            key=f"name_{uid}")
 
        st.markdown("<div style='font-size:13px; font-weight:600; color:#4a5568; margin-top:4px; margin-bottom:-16px;'>飛距離（y）</div>", unsafe_allow_html=True)
        dist_options = list(range(300, 19, -10))
        dist = st.selectbox("", dist_options,
            index=dist_options.index(c["dist"]) if c["dist"] in dist_options else 0,
            key=f"dist_{i}")
 
        st.markdown("<div style='font-size:13px; font-weight:600; color:#4a5568; margin-top:4px; margin-bottom:-16px;'>得意距離（y）</div>", unsafe_allow_html=True)
        fav_options = ["未設定"] + list(range(300, 19, -10))
        favorite = st.selectbox("", fav_options,
            index=fav_options.index(c.get("favorite", 0)) if c.get("favorite", 0) in fav_options else 0,
            key=f"favorite_{i}")
 
        st.markdown("<div style='font-size:13px; font-weight:600; color:#4a5568; margin-top:4px; margin-bottom:-16px;'>ミス率</div>", unsafe_allow_html=True)
        miss = st.slider("", 0.0, 0.8, c["miss"], 0.01, key=f"miss_{i}")
 
        if name != "（未選択）":
            edited_clubs.append({
                "name":     name,
                "dist":     0 if dist == "未設定" else dist,
                "miss":     miss,
                "favorite": 0 if favorite == "未設定" else favorite,
            })
 
        st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)
 
if st.button("✅ クラブ設定を更新", use_container_width=True):
    names = [c["name"] for c in edited_clubs]
    if len(names) != len(set(names)):
        st.error("同じクラブは1本しか選べません")
        st.stop()
    if len(edited_clubs) > 13:
        st.error("クラブはパターを除いて13本までです")
        st.stop()
 
    club_order = {
        "1W": 1, "3W": 2, "5W": 3,
        "3U": 4, "4U": 5, "5U": 6, "6U": 7,
        "5I": 8, "6I": 9, "7I": 10, "8I": 11, "9I": 12,
        "PW": 13, "AW": 14, "UW": 15, "SW": 16,
        "52°": 17, "56°": 18, "58°": 19, "60°": 20,
    }
    st.session_state.clubs = sorted(edited_clubs, key=lambda x: club_order.get(x["name"], 999))
    st.session_state.pop("name_0", None)
    st.rerun()
 
# =========================
# コース設定
# =========================
 
if "course_expander_open" not in st.session_state:
    st.session_state.course_expander_open = False

with st.expander("⛳ コース設定", expanded=st.session_state.course_expander_open):

    # ── プリセット選択 ──
    preset_options = ["コースを選択"] + list(PRESET_COURSES.keys())
    st.markdown('<div id="preset-select-anchor"></div>', unsafe_allow_html=True)
    selected_preset = st.selectbox("プリセット選択", preset_options, key="preset_select", label_visibility="collapsed")
    if selected_preset != "コースを選択":
        st.markdown('<div id="load-preset-anchor"></div>', unsafe_allow_html=True)
        if st.button("↓ コース情報を読み込む", key="btn_load_preset", use_container_width=True):
            preset = PRESET_COURSES[selected_preset]
            st.session_state.course               = preset["holes"].copy()
            st.session_state.tee_type             = preset["tee"]
            st.session_state.history              = []
            st.session_state.green_on_flag        = False
            st.session_state.course_expander_open = True
            st.session_state.pop("hole_select", None)
            st.session_state.remaining     = list(preset["holes"].values())[0]["yard"]
            for h, data in preset["holes"].items():
                st.session_state[f"par_{h}"]  = data["par"]
                st.session_state[f"yard_{h}"] = data["yard"]
                st.session_state.pop(f"actual_{h}", None)
                st.session_state.pop(f"final_score_input_{h}", None)
            st.rerun()

    tee_type = st.session_state.get("tee_type", "REG")

    edited_course = {}
    par_options   = ["Par", 3, 4, 5, 6]
 
    for h in st.session_state.course.keys():
        cur_par  = st.session_state.course[h]["par"]
        cur_yard = st.session_state.course[h]["yard"]
 
        c1, c2, c3, c4, c5 = st.columns([0.7, 0.4, 1.0, 0.5, 1.8])
 
        with c1:
            st.markdown(f"<div style='font-size:16px; font-weight:700; color:#2563eb; padding-top:10px;'>{h}番ホール</div>", unsafe_allow_html=True)
        with c2:
            st.markdown("<div style='font-size:22px; font-weight:700; color:#4a5568; padding-top:10px;'>Par</div>", unsafe_allow_html=True)
        with c3:
            par_idx = par_options.index(cur_par) if cur_par in par_options else 0
            par_sel = st.selectbox("", par_options, index=par_idx,
                key=f"par_{h}", label_visibility="collapsed")
            par = cur_par if par_sel == "Par" else int(par_sel)
        with c4:
            st.markdown("<div style='font-size:17px; font-weight:600; color:#4a5568; padding-top:12px;'>距離(y)</div>", unsafe_allow_html=True)
        with c5:
            yard = st.number_input("", 50, 700, cur_yard,
                key=f"yard_{h}", label_visibility="collapsed")
 
        edited_course[h] = {"par": par, "yard": yard}
