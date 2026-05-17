import streamlit as st
import tempfile
import os
import json
import base64

# =========================
# OpenAI Whisper による音声認識
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


# =========================
# GPT：ショット入力 or キャディへの質問を自動判断して処理
# =========================

def handle_voice_input(text: str, club_names: list, context: dict) -> dict:
    """
    音声テキストを受け取り、GPTが以下を自動判断して返す：
    - mode: "shot"（ショット入力）or "caddy"（キャディへの質問）
    - shotの場合: {"mode":"shot", "club":..., "dist":..., "result":...}
    - caddyの場合: {"mode":"caddy", "message":"キャディの返答テキスト"}
    """
    try:
        import openai
        api_key = st.secrets.get("OPENAI_API_KEY", "")
        if not api_key:
            return {"mode": "caddy", "message": "APIキーが設定されていません。"}
        client = openai.OpenAI(api_key=api_key)

        clubs_str      = "、".join(club_names)
        result_options = "FW、ラフ、OB、池、赤杭、ロスト、空振り、プレ4、プレ3、Gオン"

        # キャディに渡す現在の状況
        hole_memo = context.get("hole_memo", "")
        situation = f"""
現在の状況：
- ホール：{context['hole']}番ホール  Par{context['par']}  {context['yard']}ヤード
- 残り距離：{context['remaining']}ヤード
- 目標スコア：{context['target']}打（パーより{context['target']-context['par']:+d}）
- 残りショット数：{context['remaining_strokes']}回
- これまでのショット履歴：{context['history_text']}
- 次のAI推奨クラブ：{context['next_club']}（{context['next_dist']}ヤード）
- ホールのメモ：{hole_memo if hole_memo else "特になし"}
"""

        prompt = f"""
あなたはベテランのゴルフキャディです。プレーヤーの発話を受け取り、以下のどちらかを判断してJSON形式で返してください。

【発話】「{text}」

【利用可能なクラブ】{clubs_str}
【ショット結果の選択肢】{result_options}

{situation}

---
■ 判断ルール：

▶ ショット入力の場合（クラブ名・飛距離・結果が含まれる）：
{{"mode": "shot", "club": "クラブ名", "dist": 飛距離の数値, "result": "結果"}}

▶ キャディへの質問・相談の場合（戦略・アドバイスを求めている）：
{{"mode": "caddy", "message": "キャディとしての返答"}}

■ キャディとして返答する際のルール：
- 口調は「〜ですよ」「〜しましょう」など、親しみやすいキャディらしい話し方
- 数字や図ではなく、自然な会話で答える
- 長くなりすぎず、2〜4文程度でまとめる
- 「えーっと」「うーん」など曖昧な発話でも、現在の状況から意図を読み取って答える
- ショットの結果報告（「OBだった」「乗った」など）はshotモードとして処理する
- 「ナイスショット」など励ましも自然に入れてよい

■ ショット判断の補助ルール：
- 「セブン」→「7I」、「ピーダブ」→「PW」など口語も対応
- 飛距離が不明な場合は0
- 結果が不明な場合は「FW」

JSONのみ返してください（説明文・マークダウン不要）。
"""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
        )

        raw   = response.choices[0].message.content.strip()
        start = raw.find("{")
        end   = raw.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(raw[start:end])

    except Exception as e:
        st.error(f"解析エラー：{e}")

    return {"mode": "caddy", "message": "すみません、うまく聞き取れませんでした。もう一度お願いできますか？"}


# =========================
# OpenAI TTS による音声読み上げ
# =========================

def speak_with_openai_tts(text: str):
    """OpenAI TTSでテキストを音声に変換してブラウザで再生する"""
    try:
        import openai
        api_key = st.secrets.get("OPENAI_API_KEY", "")
        if not api_key:
            speak_with_browser(text)
            return
        client = openai.OpenAI(api_key=api_key)

        response = client.audio.speech.create(
            model="tts-1",   # 高品質にしたい場合は "tts-1-hd" に変更するだけ
            voice="onyx",    # 落ち着いた男性キャディ風の声
            input=text,
        )

        audio_bytes = response.content
        audio_b64   = base64.b64encode(audio_bytes).decode()

        # HTMLのaudioタグで自動再生
        st.markdown(
            f"""
            <audio autoplay style="display:none;">
                <source src="data:audio/mp3;base64,{audio_b64}" type="audio/mp3">
            </audio>
            """,
            unsafe_allow_html=True,
        )

    except Exception as e:
        # TTSに失敗した場合はブラウザ読み上げにフォールバック
        st.warning(f"TTS読み上げに切り替えます：{e}")
        speak_with_browser(text)


def speak_with_browser(text: str):
    """ブラウザ標準の音声読み上げ（無料・フォールバック用）"""
    escaped = text.replace("'", "\\'").replace("\n", " ")
    st.markdown(
        f"""
        <script>
            const u = new SpeechSynthesisUtterance('{escaped}');
            u.lang = 'ja-JP';
            u.rate = 1.0;
            window.speechSynthesis.speak(u);
        </script>
        """,
        unsafe_allow_html=True,
    )


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

/* ===== カード風コンテナ ===== */
.card {
    background: white;
    border-radius: 16px;
    padding: 16px;
    margin-bottom: 20px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.08);
}

/* ===== キャディ吹き出し ===== */
.caddy-bubble {
    background: #1a2e44;
    color: white;
    border-radius: 18px 18px 18px 4px;
    padding: 16px 20px;
    margin: 10px 0 16px 0;
    font-size: 24px;
    font-weight: 700;
    line-height: 1.6;
    position: relative;
}
.caddy-bubble::before {
    content: "🏌️ キャディ";
    display: block;
    font-size: 16px;
    font-weight: 900;
    color: #93c5fd;
    margin-bottom: 6px;
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

.voice-box-caddy {
    background: #eff6ff;
    border: 2px solid #93c5fd;
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

/* ===== 実績をすべてリセットボタン ===== */
[data-testid="stColumn"]:has(#reset-all-anchor) button {
    background-color: #fed7aa !important;
    border-color: #fb923c !important;
    color: #7c2d12 !important;
    font-size: 22px !important;
}

/* ===== コース情報を読み込むボタン ===== */
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
    gap: 8px;
}
.hole-header h2 {
    margin: 0;
    font-size: 24px;
    font-weight: 900;
    color: white;
    white-space: nowrap;
}
.hole-header .sub {
    font-size: 24px;
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
    font-size: 32px !important;
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

/* ===== プリセット選択セレクトボックス（小） ===== */
div:has(#preset-select-anchor) + div [data-testid="stSelectbox"] > div > div,
div:has(#preset-select-anchor) + div [data-testid="stSelectbox"] select {
    font-size: 14px !important;
    min-height: 28px !important;
}

/* ===== セレクトボックス ===== */
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

/* ===== Expander ===== */
div[data-testid="stExpander"] summary {
    font-size: 30px !important;
    font-weight: 700;
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

/* ===== 目標スコアグリッド（8択） ===== */
[data-testid="stRadio"] > div:last-child:has(> label:nth-child(8)):not(:has(> label:nth-child(9))) {
    grid-template-columns: repeat(5, 1fr) !important;
}

/* ===== パット数グリッド（4択） ===== */
[data-testid="stRadio"] > div:last-child:has(> label:nth-child(4)):not(:has(> label:nth-child(5))) {
    grid-template-columns: repeat(4, 1fr) !important;
}

/* ===== 最終スコアグリッド（16択） ===== */
[data-testid="stRadio"] > div:last-child:has(> label:nth-child(16)):not(:has(> label:nth-child(17))) {
    grid-template-columns: repeat(4, 1fr) !important;
}

/* ===== 結果グリッド（10択） ===== */
[data-testid="stRadio"] > div:last-child:has(> label:nth-child(10)):not(:has(> label:nth-child(11))) {
    grid-template-columns: repeat(4, 1fr) !important;
}
[data-testid="stRadio"] > div:last-child:has(> label:nth-child(10)):not(:has(> label:nth-child(11))) label p,
[data-testid="stRadio"] > div:last-child:has(> label:nth-child(10)):not(:has(> label:nth-child(11))) label span {
    font-size: 18px !important;
}

/* ===== クラブ選択グリッド（11択） ===== */
[data-testid="stRadio"] > div:last-child:has(> label:nth-child(11)):not(:has(> label:nth-child(12))) {
    grid-template-columns: repeat(5, 1fr) !important;
}

</style>
""", unsafe_allow_html=True)

# =========================
# 定数・初期データ（ホールメモ付きプリセット）
# =========================

PRESET_COURSES = {
    "大阪パブリックゴルフ場（フロント）": {
        "name": "大阪パブリックゴルフ場",
        "tee": "FRO",
        "holes": {
            1:  {"par": 4, "yard": 228, "memo": "難易度14位。パーオン率33%。OB率40%と高め。バンカー率14%。確実にフェアウェイをキープしてパーを狙いたい。"},
            2:  {"par": 4, "yard": 282, "memo": "難易度5位。パーオン率わずか13%、OB率49%とコース屈指の難ホール。距離はあるが慌てず確実に刻んでボギー狙いも視野に。"},
            3:  {"par": 5, "yard": 506, "memo": "難易度4位。OB率63%と非常に高い。パーオン率19%。無理に攻めず3打で確実にグリーンを狙う戦略が有効。"},
            4:  {"par": 4, "yard": 235, "memo": "難易度16位。パーオン率41%とコースで最も高い部類。OB率59%と高いので方向性重視。落ち着いてパーを狙いたい。"},
            5:  {"par": 5, "yard": 410, "memo": "難易度3位。OB率64%とコース最高レベルの難ホール。パーオン率15%。3打勝負で確実に刻む戦略が吉。"},
            6:  {"par": 3, "yard": 115, "memo": "難易度17位。距離は短くパーオン率30%。OB率43%と距離の割に高め。方向性を重視してグリーンを捉えたい。"},
            7:  {"par": 3, "yard": 154, "memo": "難易度15位。パーオン率25%。OB率29%、バンカー率16%。グリーンを外すと難しくなるため正確なショットが必要。"},
            8:  {"par": 4, "yard": 226, "memo": "難易度6位。OB率50%、バンカー率20%。平均スコア5.58と難しいホール。バンカーとOBを避けて確実にプレーしたい。"},
            9:  {"par": 3, "yard": 146, "memo": "難易度13位。パーオン率18%、OB率42%。グリーンを捉えるのが難しく、手前から安全に攻めてボギーオンを狙う選択も有効。"},
            10: {"par": 4, "yard": 257, "memo": "難易度7位。OB率65%とコース最高レベル。パーオン率23%。後半スタートは慎重に。OBだけは避けてスコアをまとめたい。"},
            11: {"par": 3, "yard": 180, "memo": "難易度10位。パーオン率12%、OB率37%。距離のあるパー3。番手をしっかり選んでグリーンを狙いたい。"},
            12: {"par": 3, "yard": 127, "memo": "難易度9位。距離は短いがパーオン率9%と非常に低い。難しいグリーンのため方向性と距離感が重要。"},
            13: {"par": 5, "yard": 530, "memo": "難易度1位。コース最難関ホール。OB率68%、パーオン率14%。無理は禁物、確実に3打でグリーンを狙う戦略を徹底したい。"},
            14: {"par": 4, "yard": 295, "memo": "難易度2位。OB率54%、パーオン率11%。コース2番目の難ホール。ボギー狙いの慎重なマネジメントが賢明。"},
            15: {"par": 4, "yard": 234, "memo": "難易度12位。OB率56%と高め。パーオン率30%。距離は短めだが方向性を重視してOBを避けることが最優先。"},
            16: {"par": 4, "yard": 298, "memo": "難易度11位。OB率53%と高い。パーオン率21%。フェアウェイキープ率45%を意識して確実なティーショットを心がけたい。"},
            17: {"par": 4, "yard": 238, "memo": "難易度8位。OB率54%、パーオン率26%。距離は短めだがOBが多い難ホール。方向性を最優先にして確実にプレーしたい。"},
            18: {"par": 4, "yard": 250, "memo": "難易度18位。最終ホールはコース最易。パーオン率45%、OB率24%と最も攻めやすい。バンカーに注意しながらパーを狙ってフィニッシュしたい。"},
        }
    },
    "大阪パブリックゴルフ場（レディース）": {
        "name": "大阪パブリックゴルフ場",
        "tee": "LADIES",
        "holes": {
            1:  {"par": 4, "yard": 223, "memo": "難易度14位。OB率40%と高め。確実にフェアウェイをキープしてパーを狙いたい。"},
            2:  {"par": 4, "yard": 282, "memo": "難易度5位。OB率49%とコース屈指の難ホール。慌てず確実に刻んでボギー狙いも視野に。"},
            3:  {"par": 5, "yard": 435, "memo": "難易度4位。OB率63%と非常に高い。無理に攻めず3打で確実にグリーンを狙う戦略が有効。"},
            4:  {"par": 4, "yard": 230, "memo": "難易度16位。パーオン率が比較的高い。OB率59%と高いので方向性重視。落ち着いてパーを狙いたい。"},
            5:  {"par": 5, "yard": 358, "memo": "難易度3位。OB率64%とコース最高レベルの難ホール。3打勝負で確実に刻む戦略が吉。"},
            6:  {"par": 3, "yard": 112, "memo": "難易度17位。距離は短くOB率43%と距離の割に高め。方向性を重視してグリーンを捉えたい。"},
            7:  {"par": 3, "yard": 154, "memo": "難易度15位。OB率29%、バンカー率16%。グリーンを外すと難しくなるため正確なショットが必要。"},
            8:  {"par": 4, "yard": 200, "memo": "難易度6位。OB率50%、バンカー率20%。バンカーとOBを避けて確実にプレーしたい。"},
            9:  {"par": 3, "yard": 146, "memo": "難易度13位。OB率42%。手前から安全に攻めてボギーオンを狙う選択も有効。"},
            10: {"par": 4, "yard": 255, "memo": "難易度7位。OB率65%とコース最高レベル。後半スタートは慎重に。OBだけは避けてスコアをまとめたい。"},
            11: {"par": 3, "yard": 178, "memo": "難易度10位。OB率37%。距離のあるパー3。番手をしっかり選んでグリーンを狙いたい。"},
            12: {"par": 3, "yard": 127, "memo": "難易度9位。距離は短いがパーオン率が非常に低い。方向性と距離感が重要。"},
            13: {"par": 5, "yard": 418, "memo": "難易度1位。コース最難関ホール。OB率68%。無理は禁物、確実に3打でグリーンを狙う戦略を徹底したい。"},
            14: {"par": 4, "yard": 292, "memo": "難易度2位。OB率54%。コース2番目の難ホール。ボギー狙いの慎重なマネジメントが賢明。"},
            15: {"par": 4, "yard": 232, "memo": "難易度12位。OB率56%と高め。距離は短めだが方向性を重視してOBを避けることが最優先。"},
            16: {"par": 4, "yard": 298, "memo": "難易度11位。OB率53%と高い。確実なティーショットを心がけたい。"},
            17: {"par": 4, "yard": 234, "memo": "難易度8位。OB率54%。距離は短めだがOBが多い難ホール。方向性を最優先にして確実にプレーしたい。"},
            18: {"par": 4, "yard": 250, "memo": "難易度18位。最終ホールはコース最易。バンカーに注意しながらパーを狙ってフィニッシュしたい。"},
        }
    },
    # ── 宝塚ゴルフ倶楽部 旧コース ──────────────────────────
    "宝塚ゴルフ倶楽部旧C（フロント）": {
        "name": "宝塚ゴルフ倶楽部 旧コース",
        "tee": "FRO",
        "holes": {
            1:  {"par": 4, "yard": 359, "memo": "右に行くと木がスタイミーになるためティーショットは左サイドが狙い目。グリーンは小さく奥行がないため手前から攻めていきたい。"},
            2:  {"par": 3, "yard": 136, "memo": "距離は短いが縦長のグリーンでバンカーに囲まれているため、方向性を重視したい。グリーンは手前から速い。"},
            3:  {"par": 4, "yard": 356, "memo": "距離のあるパー4。グリーンが左奥から右手前にかけて速いため、ティーショット・セカンドともに右サイドから攻めていきたい。"},
            4:  {"par": 5, "yard": 528, "memo": "グリーンまで障害物はないためティーショット・セカンドともに思い切りせめたいが、全体的に緩やかな左足下がりとなっているため球筋に注意したい。グリーンは2段だが手前から速い。"},
            5:  {"par": 5, "yard": 512, "memo": "左ドッグレッグのパー5。ティーショットは右が狙い目。グリーンは左から右への傾斜が強いため上りのパットを残したい。"},
            6:  {"par": 3, "yard": 128, "memo": "グリーン手前のバンカーと左奥のOBに注意。グリーンは奥から手前に速い。"},
            7:  {"par": 4, "yard": 344, "memo": "使用ティーで狙い目が変わる。残り100y付近にある右の谷に注意。セカンドは上りがきついため大きめのクラブで。グリーンは2段で縦長。"},
            8:  {"par": 3, "yard": 163, "memo": "奥行きのない横長グリーン。手前は急な下り斜面のためショートは避けたい。しっかりとしたキャリーボールが必要。"},
            9:  {"par": 4, "yard": 330, "memo": "広々としたパー4。ティーショットはフェアウェイ右バンカーを避け、気持ちよく振っていきたい。グリーンは砲台のためセカンドは少し上りをみる。"},
            10: {"par": 3, "yard": 150, "memo": "グリーン奥は谷になっているため、オーバーに注意。グリーンは小さく奥からの傾斜がきつい。"},
            11: {"par": 4, "yard": 292, "memo": "やや打ち上げの短いパー4。ティーショットは左サイドが狙い目。グリーン手前のバンカーはアゴが高く打ち上げのため高い球が要求される。グリーンは左奥より右手前にかけて速い。"},
            12: {"par": 3, "yard": 144, "memo": "両サイドをクリークに挟まれた打ち下ろしのパー3。風の影響を受けやすく、距離感・方向性ともに気を使う難ホール。"},
            13: {"par": 4, "yard": 340, "memo": "左の林に行くとグリーンが狙えないためティーショットは慎重に。グリーンは奥から手前にかけて速い。"},
            14: {"par": 5, "yard": 495, "memo": "広々とした距離のあるパー5。ピン位置により難易度が変わるためセカンドが鍵となる。グリーン手前50ヤード付近には松が効いており高い球が必要。グリーンは奥から手前にかけて速い。"},
            15: {"par": 4, "yard": 380, "memo": "打ち上げで距離のあるパー4。グリーン手前のバンカーを避けセカンドは積極的に攻めるか刻むかの判断が必要。縦長の2段グリーンのため方向性と距離感も重視したい。"},
            16: {"par": 3, "yard": 175, "memo": "グリーンは奥方向に高くなっているように見えるが、ボールの転がりは見た目以上に速いため手前から攻めるのがベスト。"},
            17: {"par": 5, "yard": 475, "memo": "ティーショットはやや左サイドが狙い目。2オンも狙えるがグリーン左右のOBに注意。グリーンは左から右への傾斜が強く、手前からも速い。"},
            18: {"par": 4, "yard": 398, "memo": "ティーショットは正面の木の右サイドが狙い目。左に行くと木が邪魔になりグリーンが狙いにくい。グリーンは手前から奥に向かって速い。"},
        }
    },
    "宝塚ゴルフ倶楽部旧C（レディース）": {
        "name": "宝塚ゴルフ倶楽部 旧コース",
        "tee": "LADIES",
        "holes": {
            1:  {"par": 4, "yard": 340, "memo": "右に行くと木がスタイミーになるためティーショットは左サイドが狙い目。グリーンは小さく奥行がないため手前から攻めていきたい。"},
            2:  {"par": 3, "yard": 116, "memo": "距離は短いが縦長のグリーンでバンカーに囲まれているため、方向性を重視したい。グリーンは手前から速い。"},
            3:  {"par": 4, "yard": 310, "memo": "距離のあるパー4。グリーンが左奥から右手前にかけて速いため、ティーショット・セカンドともに右サイドから攻めていきたい。"},
            4:  {"par": 5, "yard": 464, "memo": "グリーンまで障害物はないためティーショット・セカンドともに思い切りせめたいが、全体的に緩やかな左足下がりとなっているため球筋に注意したい。グリーンは2段だが手前から速い。"},
            5:  {"par": 5, "yard": 480, "memo": "左ドッグレッグのパー5。ティーショットは右が狙い目。グリーンは左から右への傾斜が強いため上りのパットを残したい。"},
            6:  {"par": 3, "yard": 122, "memo": "グリーン手前のバンカーと左奥のOBに注意。グリーンは奥から手前に速い。"},
            7:  {"par": 4, "yard": 325, "memo": "使用ティーで狙い目が変わる。残り100y付近にある右の谷に注意。セカンドは上りがきついため大きめのクラブで。グリーンは2段で縦長。"},
            8:  {"par": 3, "yard": 146, "memo": "奥行きのない横長グリーン。手前は急な下り斜面のためショートは避けたい。しっかりとしたキャリーボールが必要。"},
            9:  {"par": 4, "yard": 290, "memo": "広々としたパー4。ティーショットはフェアウェイ右バンカーを避け、気持ちよく振っていきたい。グリーンは砲台のためセカンドは少し上りをみる。"},
            10: {"par": 3, "yard": 139, "memo": "グリーン奥は谷になっているため、オーバーに注意。グリーンは小さく奥からの傾斜がきつい。"},
            11: {"par": 4, "yard": 285, "memo": "やや打ち上げの短いパー4。ティーショットは左サイドが狙い目。グリーン手前のバンカーはアゴが高く打ち上げのため高い球が要求される。グリーンは左奥より右手前にかけて速い。"},
            12: {"par": 3, "yard": 134, "memo": "両サイドをクリークに挟まれた打ち下ろしのパー3。風の影響を受けやすく、距離感・方向性ともに気を使う難ホール。"},
            13: {"par": 4, "yard": 330, "memo": "左の林に行くとグリーンが狙えないためティーショットは慎重に。グリーンは奥から手前にかけて速い。"},
            14: {"par": 5, "yard": 454, "memo": "広々とした距離のあるパー5。ピン位置により難易度が変わるためセカンドが鍵となる。グリーン手前50ヤード付近には松が効いており高い球が必要。グリーンは奥から手前にかけて速い。"},
            15: {"par": 4, "yard": 300, "memo": "打ち上げで距離のあるパー4。グリーン手前のバンカーを避けセカンドは積極的に攻めるか刻むかの判断が必要。縦長の2段グリーンのため方向性と距離感も重視したい。"},
            16: {"par": 3, "yard": 160, "memo": "グリーンは奥方向に高くなっているように見えるが、ボールの転がりは見た目以上に速いため手前から攻めるのがベスト。"},
            17: {"par": 5, "yard": 457, "memo": "ティーショットはやや左サイドが狙い目。2オンも狙えるがグリーン左右のOBに注意。グリーンは左から右への傾斜が強く、手前からも速い。"},
            18: {"par": 4, "yard": 298, "memo": "ティーショットは正面の木の右サイドが狙い目。左に行くと木が邪魔になりグリーンが狙いにくい。グリーンは手前から奥に向かって速い。"},
        }
    },
    # ── 宝塚ゴルフ倶楽部 新コース ──────────────────────────
    "宝塚ゴルフ倶楽部新C（フロント）": {
        "name": "宝塚ゴルフ倶楽部 新コース",
        "tee": "FRO",
        "holes": {
            1:  {"par": 5, "yard": 425, "memo": "距離の短いストレートなパー5。グリーン左手前30ヤード付近のフェアウェイバンカーを避ける事。2段グリーンのためピン位置に注意。"},
            2:  {"par": 4, "yard": 276, "memo": "距離は短いがバンカーが効いているためセカンドを考えてティーショットすること。グリーンは砲台で奥行きが短いため、正確な距離感が求められる。"},
            3:  {"par": 3, "yard": 180, "memo": "距離のある打ち降ろしのパー3。2段グリーンで右手前には深いグラスバンカーがあり、グリーンをオーバーすると難しいアプローチが残る。風への注意が必要。"},
            4:  {"par": 5, "yard": 438, "memo": "右ドッグレッグのパー5。ティーショットは左サイドが狙い目。グリーン手前50ヤード付近には松があるため刻むか攻めるかの判断が必要。グリーンは左手前から右奥へ縦長の2段グリーン。"},
            5:  {"par": 4, "yard": 316, "memo": "ティーショットはフェアウェイ右バンカーを避け左サイド狙い。ただし、その先残り80ヤード付近からくぼんでいるため打ち過ぎに注意する事。グリーン手前バンカーにつかまると厄介。"},
            6:  {"par": 4, "yard": 425, "memo": "距離のあるストレートなパー4。アウトでは一番難易度の高いホール。グリーン左手前のバンカーに注意。"},
            7:  {"par": 3, "yard": 138, "memo": "グリーンはバンカーに囲まれているため正確なショットが要求される。ダムからの吹き抜け風に注意が必要。縦長の2段グリーンで奥から手前に速い。"},
            8:  {"par": 4, "yard": 424, "memo": "左ドッグレッグのパー4。ティーショットは右サイドからコースを広く使っていきたいが、ロングヒッターは右への突き抜けに注意。セカンドからは方向性に注意し無理せず安全に攻めたい。"},
            9:  {"par": 4, "yard": 388, "memo": "やや打ち下ろしのストレートなパー4。ティーショット・セカンドともに風への注意が必要。グリーンは手前から速い。"},
            10: {"par": 5, "yard": 457, "memo": "S字のパー5。方向性と距離のジャッジを正確に。グリーン手前30ヤード付近に松があるためセカンドの方向性に注意が必要。"},
            11: {"par": 4, "yard": 271, "memo": "バンカーが多いためティーショットがキーポイントとなる。打ち上げのため距離感がつかみにくい。グリーンは2段で奥に外すと難しいアプローチが残る。"},
            12: {"par": 3, "yard": 134, "memo": "グリーンは左手前から右奥に向かって長く大きい。ピン位置によっては1クラブ以上の違いあり。方向性と距離感が要求されるホール。"},
            13: {"par": 4, "yard": 376, "memo": "ティーショットは左方向が狙い目。右はOB、左はレッドペナルティーエリア。グリーン両サイドは奥行きがないため正確な距離感が必要。"},
            14: {"par": 4, "yard": 423, "memo": "距離のあるパー4。ティーショットは右管理道方向が狙い目。左の谷へ落ちた場合は無理をせずフェアウェイに戻した方がよい。フェアウェイ・グリーンともに左に傾斜している。"},
            15: {"par": 3, "yard": 179, "memo": "名物ホールのパー3。打ち下ろしのため距離感に注意。手前バンカーにつかまった場合は、後方または横に出す勇気も必要。"},
            16: {"par": 4, "yard": 320, "memo": "戦略性のあるやや右ドッグレッグのパー4。左右にフェアウェイバンカーがあるためティーショットがキーポイントとなる。グリーン左手前には池。セカンドは見た目以上に上っているため少し大き目のクラブで。"},
            17: {"par": 5, "yard": 478, "memo": "ゆるやかに打ち上げている右ドッグレッグのパー5。全体的に左から攻めるとよい。2段グリーンのためピン位置に注意。"},
            18: {"par": 4, "yard": 408, "memo": "距離のある打ち下ろしのパー4。ティーショットはやや右サイドが狙い目だが、右に行き過ぎるとOBになりやすく残り距離が長くなるため注意が必要。3段グリーンでピン位置により難易度が変わる。"},
        }
    },
    "宝塚ゴルフ倶楽部新C（レディース）": {
        "name": "宝塚ゴルフ倶楽部 新コース",
        "tee": "LADIES",
        "holes": {
            1:  {"par": 5, "yard": 415, "memo": "距離の短いストレートなパー5。グリーン左手前30ヤード付近のフェアウェイバンカーを避ける事。2段グリーンのためピン位置に注意。"},
            2:  {"par": 4, "yard": 276, "memo": "距離は短いがバンカーが効いているためセカンドを考えてティーショットすること。グリーンは砲台で奥行きが短いため、正確な距離感が求められる。"},
            3:  {"par": 3, "yard": 140, "memo": "距離のある打ち降ろしのパー3。2段グリーンで右手前には深いグラスバンカーがあり、グリーンをオーバーすると難しいアプローチが残る。風への注意が必要。"},
            4:  {"par": 5, "yard": 380, "memo": "右ドッグレッグのパー5。ティーショットは左サイドが狙い目。グリーン手前50ヤード付近には松があるため刻むか攻めるかの判断が必要。グリーンは左手前から右奥へ縦長の2段グリーン。"},
            5:  {"par": 4, "yard": 310, "memo": "ティーショットはフェアウェイ右バンカーを避け左サイド狙い。ただし、その先残り80ヤード付近からくぼんでいるため打ち過ぎに注意する事。グリーン手前バンカーにつかまると厄介。"},
            6:  {"par": 4, "yard": 375, "memo": "距離のあるストレートなパー4。アウトでは一番難易度の高いホール。グリーン左手前のバンカーに注意。"},
            7:  {"par": 3, "yard": 128, "memo": "グリーンはバンカーに囲まれているため正確なショットが要求される。ダムからの吹き抜け風に注意が必要。縦長の2段グリーンで奥から手前に速い。"},
            8:  {"par": 4, "yard": 337, "memo": "左ドッグレッグのパー4。ティーショットは右サイドからコースを広く使っていきたいが、ロングヒッターは右への突き抜けに注意。セカンドからは方向性に注意し無理せず安全に攻めたい。"},
            9:  {"par": 4, "yard": 373, "memo": "やや打ち下ろしのストレートなパー4。ティーショット・セカンドともに風への注意が必要。グリーンは手前から速い。"},
            10: {"par": 5, "yard": 435, "memo": "S字のパー5。方向性と距離のジャッジを正確に。グリーン手前30ヤード付近に松があるためセカンドの方向性に注意が必要。"},
            11: {"par": 4, "yard": 256, "memo": "バンカーが多いためティーショットがキーポイントとなる。打ち上げのため距離感がつかみにくい。グリーンは2段で奥に外すと難しいアプローチが残る。"},
            12: {"par": 3, "yard": 121, "memo": "グリーンは左手前から右奥に向かって長く大きい。ピン位置によっては1クラブ以上の違いあり。方向性と距離感が要求されるホール。"},
            13: {"par": 4, "yard": 352, "memo": "ティーショットは左方向が狙い目。右はOB、左はレッドペナルティーエリア。グリーン両サイドは奥行きがないため正確な距離感が必要。"},
            14: {"par": 4, "yard": 323, "memo": "距離のあるパー4。ティーショットは右管理道方向が狙い目。左の谷へ落ちた場合は無理をせずフェアウェイに戻した方がよい。フェアウェイ・グリーンともに左に傾斜している。"},
            15: {"par": 3, "yard": 142, "memo": "名物ホールのパー3。打ち下ろしのため距離感に注意。手前バンカーにつかまった場合は、後方または横に出す勇気も必要。"},
            16: {"par": 4, "yard": 250, "memo": "戦略性のあるやや右ドッグレッグのパー4。左右にフェアウェイバンカーがあるためティーショットがキーポイントとなる。グリーン左手前には池。セカンドは見た目以上に上っているため少し大き目のクラブで。"},
            17: {"par": 5, "yard": 409, "memo": "ゆるやかに打ち上げている右ドッグレッグのパー5。全体的に左から攻めるとよい。2段グリーンのためピン位置に注意。"},
            18: {"par": 4, "yard": 353, "memo": "距離のある打ち下ろしのパー4。ティーショットはやや右サイドが狙い目だが、右に行き過ぎるとOBになりやすく残り距離が長くなるため注意が必要。3段グリーンでピン位置により難易度が変わる。"},
        }
    },
    # ── 琵琶湖レークサイドゴルフコース ──────────────────────────
    "琵琶湖レークサイド（北・フロント）": {
        "name": "琵琶湖レークサイドゴルフコース 北コース",
        "tee": "FRO",
        "holes": {
            1: {"par": 4, "yard": 339, "memo": "砲台グリーンのミドルホール。ティーショットは右サイド広く、やや右狙い。左クロスバンカーに入れると2オンは難しい。"},
            2: {"par": 5, "yard": 450, "memo": "距離の長いロングホール。ティーショットは距離とフェアウェイキープが重要。二打目、右クロスバンカーより軽いドローで攻めるのが狙い目。左傾斜のグリーンで落とし所に注意。"},
            3: {"par": 3, "yard": 106, "memo": "池越えショートホール。距離は短いが、風に要注意。奥につけてしまえば下りのタッチが難しい。"},
            4: {"par": 5, "yard": 420, "memo": "距離の短いロングホール。ティーショットはやや左狙い。右サイドは広いが距離が残る。二打目、フェアウェイ左クロスバンカーに注意。"},
            5: {"par": 4, "yard": 374, "memo": "グリーン手前100Yから軽く右ドッグレッグのミドルホール。ティーショットはフェアウェイやや左サイド狙い。二打目グリーンオーバーしやすく、突っ込み過ぎに注意。グリーン左横のグラスバンカーにも注意。"},
            6: {"par": 4, "yard": 362, "memo": "砲台グリーンのミドルホール。ティーショットは左右イエローペナルティエリアに注意。グリーンは奥に傾斜しており、高い弾道が必要不可欠。"},
            7: {"par": 3, "yard": 139, "memo": "砲台2段グリーンのショートホール。距離を合わせるのが難しい。左右バンカーはアゴが高く、パーセーブが困難。"},
            8: {"par": 4, "yard": 357, "memo": "受けグリーンのミドルホール。フェアウェイ右サイド、残り150Y地点にコブあり。ティーショットはフェアウェイやや左サイド狙い。二打目、手前バンカーを避け花道からフェード気味に狙う。"},
            9: {"par": 4, "yard": 377, "memo": "距離のあるミドルホール。ティーショットはフェアウェイの右サイド狙いで距離をかせぐ。二打目グリーン手前左右のバンカーに注意。無理せず手前より攻める。"},
        }
    },
    "琵琶湖レークサイド（北・レディース）": {
        "name": "琵琶湖レークサイドゴルフコース 北コース",
        "tee": "LADIES",
        "holes": {
            1: {"par": 4, "yard": 284, "memo": "砲台グリーンのミドルホール。ティーショットは右サイド広く、やや右狙い。左クロスバンカーに入れると2オンは難しい。"},
            2: {"par": 5, "yard": 419, "memo": "距離の長いロングホール。ティーショットは距離とフェアウェイキープが重要。二打目、右クロスバンカーより軽いドローで攻めるのが狙い目。左傾斜のグリーンで落とし所に注意。"},
            3: {"par": 3, "yard": 106, "memo": "池越えショートホール。距離は短いが、風に要注意。奥につけてしまえば下りのタッチが難しい。"},
            4: {"par": 5, "yard": 377, "memo": "距離の短いロングホール。ティーショットはやや左狙い。右サイドは広いが距離が残る。二打目、フェアウェイ左クロスバンカーに注意。"},
            5: {"par": 4, "yard": 335, "memo": "グリーン手前100Yから軽く右ドッグレッグのミドルホール。ティーショットはフェアウェイやや左サイド狙い。二打目グリーンオーバーしやすく、突っ込み過ぎに注意。グリーン左横のグラスバンカーにも注意。"},
            6: {"par": 4, "yard": 275, "memo": "砲台グリーンのミドルホール。ティーショットは左右イエローペナルティエリアに注意。グリーンは奥に傾斜しており、高い弾道が必要不可欠。"},
            7: {"par": 3, "yard": 124, "memo": "砲台2段グリーンのショートホール。距離を合わせるのが難しい。左右バンカーはアゴが高く、パーセーブが困難。"},
            8: {"par": 4, "yard": 315, "memo": "受けグリーンのミドルホール。フェアウェイ右サイド、残り150Y地点にコブあり。ティーショットはフェアウェイやや左サイド狙い。二打目、手前バンカーを避け花道からフェード気味に狙う。"},
            9: {"par": 4, "yard": 302, "memo": "距離のあるミドルホール。ティーショットはフェアウェイの右サイド狙いで距離をかせぐ。二打目グリーン手前左右のバンカーに注意。無理せず手前より攻める。"},
        }
    },
    "琵琶湖レークサイド（中・フロント）": {
        "name": "琵琶湖レークサイドゴルフコース 中コース",
        "tee": "FRO",
        "holes": {
            1: {"par": 4, "yard": 327, "memo": "思いっきりティーショットを打っていけるホール。狙いはフェアウェイ左バンカーの右側狙い。グリーンは手前から攻めるのがベスト。"},
            2: {"par": 3, "yard": 123, "memo": "グリーン周りはOBが出やすい。ピンポジションにかかわらず、グリーンセンターを狙う。"},
            3: {"par": 4, "yard": 330, "memo": "左ドッグレッグのミドルホール。ティーショットは正面クロスバンカー狙い。左サイドの池に注意。"},
            4: {"par": 4, "yard": 271, "memo": "軽く右にドッグレッグしたホール。ティーショットはフェアウェイやや右狙い。安全に左サイドに刻んでいくのも一つの手段。"},
            5: {"par": 5, "yard": 410, "memo": "距離の短いロングホール。ティーショットはフェアウェイセンター狙い。グリーン手前の池に注意。"},
            6: {"par": 3, "yard": 114, "memo": "ピンポジションにかかわらず、グリーンセンター狙い。左ガードバンカーに注意。"},
            7: {"par": 4, "yard": 283, "memo": "ティーショットはフェアウェイセンターのバンカーに注意。二打目は確実にグリーンセンターへ。グリーンを外すと、周りからのアプローチは寄せがむずかしい。"},
            8: {"par": 3, "yard": 148, "memo": "池が気になるショートホール。グリーン右側は比較的安全。"},
            9: {"par": 4, "yard": 278, "memo": "ティーショットはフェアウェイ正面の木を目標に。二打目は確実にグリーンセンターへ。バーディーの確率が高いホール。"},
        }
    },
    "琵琶湖レークサイド（中・レディース）": {
        "name": "琵琶湖レークサイドゴルフコース 中コース",
        "tee": "LADIES",
        "holes": {
            1: {"par": 4, "yard": 318, "memo": "思いっきりティーショットを打っていけるホール。狙いはフェアウェイ左バンカーの右側狙い。グリーンは手前から攻めるのがベスト。"},
            2: {"par": 3, "yard": 117, "memo": "グリーン周りはOBが出やすい。ピンポジションにかかわらず、グリーンセンターを狙う。"},
            3: {"par": 4, "yard": 311, "memo": "左ドッグレッグのミドルホール。ティーショットは正面クロスバンカー狙い。左サイドの池に注意。"},
            4: {"par": 4, "yard": 265, "memo": "軽く右にドッグレッグしたホール。ティーショットはフェアウェイやや右狙い。安全に左サイドに刻んでいくのも一つの手段。"},
            5: {"par": 5, "yard": 401, "memo": "距離の短いロングホール。ティーショットはフェアウェイセンター狙い。グリーン手前の池に注意。"},
            6: {"par": 3, "yard": 104, "memo": "ピンポジションにかかわらず、グリーンセンター狙い。左ガードバンカーに注意。"},
            7: {"par": 4, "yard": 263, "memo": "ティーショットはフェアウェイセンターのバンカーに注意。二打目は確実にグリーンセンターへ。グリーンを外すと、周りからのアプローチは寄せがむずかしい。"},
            8: {"par": 3, "yard": 128, "memo": "池が気になるショートホール。グリーン右側は比較的安全。"},
            9: {"par": 4, "yard": 260, "memo": "ティーショットはフェアウェイ正面の木を目標に。二打目は確実にグリーンセンターへ。バーディーの確率が高いホール。"},
        }
    },
    "琵琶湖レークサイド（南・フロント）": {
        "name": "琵琶湖レークサイドゴルフコース 南コース",
        "tee": "FRO",
        "holes": {
            1: {"par": 4, "yard": 297, "memo": "軽く左にドッグレッグしたホール。ティーショットはフェアウェイやや右サイド狙い。ガードバンカーのアゴ高く。二打目は高い弾道で。"},
            2: {"par": 3, "yard": 114, "memo": "グリーン手前の池に注意。グリーン奥からのアプローチもむずかしい。確実にグリーンセンターへ。"},
            3: {"par": 5, "yard": 459, "memo": "ティーショットは正面の木狙い。二打目は左サイドの池に注意。グリーン周りからのアプローチは寄せがむずかしい。"},
            4: {"par": 4, "yard": 329, "memo": "右ドッグレッグのミドルホール。ティーショットはフェアウェイセンター狙い。右を狙いすぎると、二打目が木超えのむずかしいショットに。"},
            5: {"par": 3, "yard": 128, "memo": "グリーン周りのガードバンカーに注意。確実にグリーンセンターへ。グリーン奥はOB。"},
            6: {"par": 4, "yard": 300, "memo": "ティーショットはフェアウェイセンター狙い。グリーン左サイドは比較的安全。"},
            7: {"par": 4, "yard": 294, "memo": "ティーショットはフェアウェイセンター狙い。グリーン右手前のバンカーに注意。二打目は確実にグリーンセンターへ。"},
            8: {"par": 3, "yard": 112, "memo": "グリーン手前のバンカーに注意。高い弾道で、確実にグリーンセンターへ。"},
            9: {"par": 4, "yard": 323, "memo": "軽く左ドッグレッグしたホール。ティーショットはフェアウェイ右サイド狙い。グリーン左サイドはOBが近いので注意。"},
        }
    },
    "琵琶湖レークサイド（南・レディース）": {
        "name": "琵琶湖レークサイドゴルフコース 南コース",
        "tee": "LADIES",
        "holes": {
            1: {"par": 4, "yard": 290, "memo": "軽く左にドッグレッグしたホール。ティーショットはフェアウェイやや右サイド狙い。ガードバンカーのアゴ高く。二打目は高い弾道で。"},
            2: {"par": 3, "yard": 103, "memo": "グリーン手前の池に注意。グリーン奥からのアプローチもむずかしい。確実にグリーンセンターへ。"},
            3: {"par": 5, "yard": 438, "memo": "ティーショットは正面の木狙い。二打目は左サイドの池に注意。グリーン周りからのアプローチは寄せがむずかしい。"},
            4: {"par": 4, "yard": 316, "memo": "右ドッグレッグのミドルホール。ティーショットはフェアウェイセンター狙い。右を狙いすぎると、二打目が木超えのむずかしいショットに。"},
            5: {"par": 3, "yard": 119, "memo": "グリーン周りのガードバンカーに注意。確実にグリーンセンターへ。グリーン奥はOB。"},
            6: {"par": 4, "yard": 289, "memo": "ティーショットはフェアウェイセンター狙い。グリーン左サイドは比較的安全。"},
            7: {"par": 4, "yard": 281, "memo": "ティーショットはフェアウェイセンター狙い。グリーン右手前のバンカーに注意。二打目は確実にグリーンセンターへ。"},
            8: {"par": 3, "yard": 107, "memo": "グリーン手前のバンカーに注意。高い弾道で、確実にグリーンセンターへ。"},
            9: {"par": 4, "yard": 307, "memo": "軽く左ドッグレッグしたホール。ティーショットはフェアウェイ右サイド狙い。グリーン左サイドはOBが近いので注意。"},
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
if "caddy_log" not in st.session_state:
    st.session_state.caddy_log = []   # キャディとの会話履歴

if "course" not in st.session_state:
    st.session_state.course = {
        h: {"par": d["par"], "yard": d["yard"], "memo": d["memo"]}
        for h, d in PRESET_COURSES["宝塚ゴルフ倶楽部旧C（フロント）"]["holes"].items()
    }

# =========================
# クラブ選択ロジック
# =========================

def get_valid_clubs():
    return [c for c in st.session_state.clubs if c["dist"] > 0 and c["name"] != "なし"]

def choose_club(remaining, shots_left, is_first_shot, par_num, hole):
    valid_clubs = get_valid_clubs()
    if not valid_clubs:
        return {"name": "なし", "dist": 0, "miss": 1.0}

    danger_scores = {"バンカー": 50, "池": 120, "OBゾーン": 300, "谷越え": 80, "ドッグレッグ": 40}

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

        favorite_penalty         = abs(expected_after - favorite) if favorite > 0 else 0
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
            "shot": i + 1, "club": club["name"], "dist": shot_dist,
            "remain": max(remaining - shot_dist, 0), "before": remaining,
        })
        remaining = max(remaining - shot_dist, 0)
    return result

# =========================
# ホール難易度・目標打数計算
# =========================

def calc_hole_targets(target_score):
    hole_difficulty = {}
    for h, data in st.session_state.course.items():
        yard  = data["yard"]
        par   = data["par"]
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
        with r1:
            st.markdown(f"<div class='score-cell' style='font-size:26px;'><b>{h}番</b> Par{par}&nbsp;&nbsp;{yard}y</div>", unsafe_allow_html=True)
        with r2:
            st.markdown(f"<div class='score-cell'>{strategy_html}</div>", unsafe_allow_html=True)

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

st.title("⛳ AIキャディ（音声版）")

# ---------- ラウンド目標 ----------
goal_col1, goal_col2 = st.columns([1, 1])
with goal_col1:
    st.markdown('<div style="font-size:22px; font-weight:900; color:#1a2e44; margin-top:20px; margin-bottom:6px;">⛳ ラウンドスコア目標</div>', unsafe_allow_html=True)
with goal_col2:
    target_score = st.selectbox("", list(range(60, 151)), index=40, key="target_score", label_visibility="collapsed")

hole_targets = calc_hole_targets(target_score)

with st.expander(f"🧠 目標スコア{target_score}のラウンド戦略", expanded=False):
    holes = sorted(st.session_state.course.keys())
    render_score_table(holes, hole_targets)

# ---------- 現状の見込み ----------
holes = sorted(st.session_state.course.keys())
total_par       = sum(st.session_state.course[h]["par"] for h in holes)
projected_total = 0
for h in holes:
    actual = st.session_state.get(f"actual_{h}", "")
    projected_total += int(actual) if actual != "" else hole_targets[h]

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
    f"</div></div>",
    unsafe_allow_html=True
)

st.markdown("<div style='margin-top:8px'></div>", unsafe_allow_html=True)

# ---------- ホール選択 ----------
st.markdown('<div style="font-size:22px; font-weight:900; color:#1a2e44; margin-top:20px; margin-bottom:6px;">⛳ ホールを選択</div>', unsafe_allow_html=True)
hole = st.radio("", list(st.session_state.course.keys()), key="hole_select", label_visibility="collapsed", horizontal=True)

TOTAL_DIST = st.session_state.course[hole]["yard"]
par_num    = st.session_state.course[hole]["par"]
hole_memo  = st.session_state.course[hole].get("memo", "")

st.markdown(
    f"""<div class="hole-header">
        <h2>⛳ {hole}番ホール</h2>
        <div class="sub">{TOTAL_DIST}y ／ Par {par_num}</div>
    </div>""",
    unsafe_allow_html=True
)

# ホールメモ表示（ある場合）
if hole_memo:
    st.markdown(
        f"<div style='background:#fefce8; border-left:4px solid #fbbf24; border-radius:8px; "
        f"padding:10px 16px; margin-bottom:12px; font-size:20px; color:#78350f;'>"
        f"📋 {hole_memo}</div>",
        unsafe_allow_html=True
    )

if "prev_hole" not in st.session_state:
    st.session_state.prev_hole = hole

if hole != st.session_state.prev_hole:
    st.session_state.remaining     = TOTAL_DIST
    st.session_state.history       = []
    st.session_state.prev_hole     = hole
    st.session_state.green_on_flag = False
    st.session_state.caddy_log     = []   # ホールが変わったら会話履歴もリセット

if "remaining" not in st.session_state:
    st.session_state.remaining = TOTAL_DIST
if "history" not in st.session_state:
    st.session_state.history = []

# ---------- 目標打数・パット設定 ----------
recommended_score = hole_targets[hole]
diff              = recommended_score - par_num
label, rec_color  = score_info(diff)

st.markdown(f'<div style="font-size:22px; font-weight:900; color:#1a2e44; margin-top:20px; margin-bottom:6px;">⛳ {hole}番ホールの目標スコア</div>', unsafe_allow_html=True)

label_text = label.split(' ', 1)[1] if ' ' in label else label
st.markdown(
    f"<div style='font-size:20px; font-weight:700; color:#1a1a1a; padding-bottom:4px;'>（AI推奨：{recommended_score}打 {label_text}）</div>",
    unsafe_allow_html=True
)

default_target = max(1, min(recommended_score, 8)) - 1
current_target = st.session_state.get(f"target_select_{hole}", default_target + 1)
sel_diff       = current_target - par_num
sel_label, sel_color = score_info(sel_diff)
sel_label_text = sel_label.split(' ', 1)[1] if ' ' in sel_label else sel_label
st.markdown(
    f"<div style='font-size:24px; font-weight:700; color:{sel_color}; margin-top:6px; margin-bottom:2px;'>"
    f"{current_target}打　{sel_label_text}</div>",
    unsafe_allow_html=True
)

target = st.radio("", list(range(1, 9)), index=default_target, key=f"target_select_{hole}", label_visibility="collapsed", horizontal=True)

st.markdown('<div style="font-size:22px; font-weight:900; color:#1a2e44; margin-top:20px; margin-bottom:6px;">🏌️ パット数は？</div>', unsafe_allow_html=True)
putts = st.radio("", [1, 2, 3, 4], index=1, key="putt_select", label_visibility="collapsed", horizontal=True)

shot_strokes = target - putts
st.markdown(
    f"<div style='font-size:22px; font-weight:700; color:#e53e3e; margin-top:6px;'>ショット{shot_strokes}回＋パット{putts}回</div>",
    unsafe_allow_html=True
)

if target < par_num - 1:
    st.error("それは無謀です！")
    st.stop()

# ---------- ショット戦略表示 ----------
st.markdown('<div style="font-size:22px; font-weight:900; color:#1a2e44; margin-top:20px; margin-bottom:6px;">⛳ ショット戦略</div>', unsafe_allow_html=True)

st.markdown(
    f"""<div class="remain-badge">
        📍 現在の残り距離　<span style="font-size:32px; font-weight:900;">{st.session_state.remaining}y</span>
    </div>""",
    unsafe_allow_html=True
)

# ショット履歴表示
current_shot = 1
for h in st.session_state.history:
    result_text = {
        "OB": "OB（1打罰）", "池": "池（1打罰）", "赤杭": "赤杭（1打罰）",
        "ロスト": "ロスト（2打罰）", "空振り": "空振り", "FW": "FW",
        "ラフ": "ラフ", "プレ4": "プレ4（2打罰）", "プレ3": "プレ3（1打罰）",
    }.get(h.get("result", ""), "")
    green_on_mark = " <span style='font-size:20px;'>🚩グリーンオン</span>" if h.get("green_on") else ""
    suffix = f" ⚡ {result_text}" if result_text else ""
    st.markdown(
        f"<div class='shot-row-history'>✅ （実績）：{h['club']} {h['dist']}y{green_on_mark}{suffix}</div>",
        unsafe_allow_html=True
    )
    current_shot += 1 + h.get("penalty", 0)

used              = sum(1 + h.get("penalty", 0) for h in st.session_state.history)
remaining_strokes = shot_strokes - used

# 次のショット推奨クラブを先に計算（キャディ応答のcontextに使う）
next_club_name = "なし"
next_club_dist = 0
if st.session_state.remaining > 0 and remaining_strokes > 0:
    plan_data = plan(st.session_state.remaining, remaining_strokes, used, par_num, hole)
    next_club_name = plan_data[0]["club"] if plan_data else "なし"
    next_club_dist = plan_data[0]["dist"] if plan_data else 0

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
            shots_to_green = next((i2 + 1 for i2, p2 in enumerate(plan_data) if p2["remain"] == 0), len(plan_data))
            margin = remaining_strokes - shots_to_green
            if margin > 0:
                st.markdown(
                    f"<div style='background:#dcfce7; border-left:4px solid #16a34a; border-radius:8px; "
                    f"padding:10px 20px; margin-top:8px; font-size:22px; font-weight:700; color:#15803d;'>"
                    f"🟢 {margin}打余裕があります</div>",
                    unsafe_allow_html=True
                )
            st.markdown(f"<div class='shot-row'><strong>パット {putts}回</strong></div>", unsafe_allow_html=True)
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
elif st.session_state.remaining == 0:
    st.markdown(f"<div class='shot-row'><strong>パット {putts}回</strong></div>", unsafe_allow_html=True)
elif remaining_strokes == 0:
    st.error("⚠️ この計画では届きません")
else:
    st.error("ショット数が不足しています")


# =========================
# 🎤 キャディに話しかける（メイン音声入力）
# =========================

st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)
st.markdown(
    "<div style='font-size:26px; font-weight:900; color:#1a2e44; margin-top:16px; margin-bottom:6px;'>"
    "🎤 キャディに話しかける</div>",
    unsafe_allow_html=True
)
st.markdown(
    "<div class='voice-box-caddy'>"
    "<div style='font-size:18px; color:#1e40af;'>💬 なんでも話しかけてください</div>"
    "<div style='font-size:16px; color:#4b5563; margin-top:4px;'>"
    "例：「えーっと、ここどう攻めればいい？」<br>"
    "例：「7番で150ヤード、フェアウェイ」<br>"
    "例：「今何打目だっけ？」"
    "</div></div>",
    unsafe_allow_html=True
)

# セッション変数の初期化
if "voice_club"   not in st.session_state: st.session_state.voice_club   = None
if "voice_dist"   not in st.session_state: st.session_state.voice_dist   = None
if "voice_result" not in st.session_state: st.session_state.voice_result = None
if "voice_text"   not in st.session_state: st.session_state.voice_text   = ""
if "last_caddy_message" not in st.session_state: st.session_state.last_caddy_message = ""

# 直近のキャディの返答を表示
if st.session_state.last_caddy_message:
    st.markdown(
        f"<div class='caddy-bubble'>{st.session_state.last_caddy_message}</div>",
        unsafe_allow_html=True
    )

# 音声入力
caddy_audio = st.audio_input("🎤 タップして話しかける", key="caddy_voice_input")

if caddy_audio is not None:
    with st.spinner("🎤 聞き取り中..."):
        audio_bytes = caddy_audio.read()
        text = transcribe_audio(audio_bytes)

    if text:
        st.markdown(
            f"<div class='voice-result'>🗣️ 「{text}」</div>",
            unsafe_allow_html=True
        )

        # 履歴テキストを作成
        history_text = "なし"
        if st.session_state.history:
            history_text = "、".join(
                [f"{h['club']} {h['dist']}y ({h['result']})" for h in st.session_state.history]
            )

        # GPTに渡すコンテキスト
        context = {
            "hole":             hole,
            "par":              par_num,
            "yard":             TOTAL_DIST,
            "remaining":        st.session_state.remaining,
            "target":           target,
            "remaining_strokes": remaining_strokes,
            "history_text":     history_text,
            "next_club":        next_club_name,
            "next_dist":        next_club_dist,
            "hole_memo":        hole_memo,
        }

        with st.spinner("🤖 キャディが考え中..."):
            result = handle_voice_input(text, [c["name"] for c in st.session_state.clubs], context)

        if result.get("mode") == "shot":
            # ショット入力として処理
            parsed = result
            club_names = [c["name"] for c in st.session_state.clubs]

            st.markdown(
                f"<div style='background:#dbeafe; border:2px solid #93c5fd; border-radius:10px; "
                f"padding:12px 20px; margin-top:8px; font-size:22px; font-weight:700;'>"
                f"✅ ショット入力：{parsed.get('club','?')} ／ {parsed.get('dist','?')}y ／ {parsed.get('result','?')}"
                f"</div>",
                unsafe_allow_html=True
            )

            st.markdown('<div id="voice-apply-anchor"></div>', unsafe_allow_html=True)
            if st.button("✅ この内容で反映する", key="btn_caddy_apply", use_container_width=True):
                club_name = parsed.get("club", "")
                dist_val  = parsed.get("dist", 0)
                result_s  = parsed.get("result", "FW")

                penalty       = 0
                green_on      = (result_s == "Gオン")
                remain_adjust = dist_val

                if result_s == "OB":
                    penalty = 1;  remain_adjust = 0
                elif result_s == "池":
                    penalty = 1;  remain_adjust = dist_val
                elif result_s == "赤杭":
                    penalty = 1;  remain_adjust = dist_val
                elif result_s == "ロスト":
                    penalty = 2;  remain_adjust = dist_val
                elif result_s == "空振り":
                    remain_adjust = 0
                elif result_s == "プレ4":
                    penalty = 2;  remain_adjust = 0
                elif result_s == "プレ3":
                    penalty = 1;  remain_adjust = 0
                elif green_on:
                    remain_adjust = st.session_state.remaining

                st.session_state.history.append({
                    "club": club_name, "dist": dist_val,
                    "result": result_s, "penalty": penalty, "green_on": green_on,
                })
                st.session_state.remaining = max(st.session_state.remaining - remain_adjust, 0)

                # ショット後のキャディコメントを生成
                new_remaining = max(st.session_state.remaining - remain_adjust, 0) if not green_on else 0
                comment_prompt = f"""
あなたはゴルフキャディです。プレーヤーが{club_name}で{dist_val}ヤード打って{result_s}でした。
残り距離は{new_remaining}ヤードです。
ひとこと自然にコメントしてください（1〜2文、キャディらしい口調で）。
"""
                try:
                    import openai
                    api_key = st.secrets.get("OPENAI_API_KEY", "")
                    if api_key:
                        client = openai.OpenAI(api_key=api_key)
                        resp   = client.chat.completions.create(
                            model="gpt-4o-mini",
                            messages=[{"role": "user", "content": comment_prompt}],
                            max_tokens=100,
                        )
                        comment = resp.choices[0].message.content.strip()
                        st.session_state.last_caddy_message = comment
                        speak_with_openai_tts(comment)
                except:
                    pass

                st.session_state.voice_text = ""
                st.rerun()

        elif result.get("mode") == "caddy":
            # キャディとして返答
            message = result.get("message", "")
            st.session_state.last_caddy_message = message
            st.session_state.caddy_log.append({"q": text, "a": message})
            speak_with_openai_tts(message)
            st.rerun()

    elif text == "" and caddy_audio is not None:
        st.warning("音声を認識できませんでした。もう少しはっきり話してみてください。")


# =========================
# 手動ショット結果入力
# =========================

CLUB_SLIDER_RANGE = {
    "1W": (100,250), "4U": (100,220), "5U": (90,210),
    "6I": (80,200),  "7I": (80,190),  "8I": (70,180),
    "9I": (60,170),  "PW": (50,160),  "UW": (50,150),
    "52°": (40,140), "56°": (30,120),
}

st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)
st.markdown('<div style="font-size:22px; font-weight:900; color:#1a2e44; margin-top:20px; margin-bottom:6px;">✏️ 手動でショットを入力</div>', unsafe_allow_html=True)

st.markdown('<div class="ui-label-small">使ったクラブ</div>', unsafe_allow_html=True)
actual_club = st.radio(
    "", [c["name"] for c in st.session_state.clubs],
    key="selected_club", label_visibility="collapsed", horizontal=True,
)

smin, smax = CLUB_SLIDER_RANGE.get(actual_club, (10, 250))
slider_key = f"dist_slider_{actual_club}"
if slider_key not in st.session_state:
    st.session_state[slider_key] = int(smax * 0.7)
current_dist = st.session_state[slider_key]

st.markdown(
    f'<div style="font-size:22px; font-weight:700; color:#4a5568; margin-top:8px; margin-bottom:4px;">'
    f'飛距離　<span style="font-size:42px; color:#1a2e44; font-weight:900;">{current_dist}y</span></div>',
    unsafe_allow_html=True
)
st.slider("", min_value=smin, max_value=smax, step=10, key=slider_key, label_visibility="collapsed")

st.markdown('<div class="ui-label-small">結果</div>', unsafe_allow_html=True)
shot_result = st.radio(
    "", ["FW","ラフ","OB","池","赤杭","ロスト","空振り","プレ4","プレ3","Gオン"],
    key="shot_result_select", label_visibility="collapsed", horizontal=True,
)

btn1, btn2, _ = st.columns([1, 1, 1])
with btn1:
    submitted = st.button("✅ 反映", key="btn_submit_shot", use_container_width=True)
with btn2:
    undo = st.button("↩️ 取消", key="btn_undo_shot", use_container_width=True)

if submitted:
    penalty  = 0
    green_on = (shot_result == "Gオン")
    _, _smax = CLUB_SLIDER_RANGE.get(actual_club, (10, 250))
    dist_val = st.session_state.remaining if green_on else st.session_state.get(f"dist_slider_{actual_club}", int(_smax * 0.7))
    remain_adjust = dist_val

    if shot_result == "OB":
        penalty = 1;  remain_adjust = 0
    elif shot_result == "池":
        penalty = 1;  remain_adjust = dist_val
    elif shot_result == "赤杭":
        penalty = 1;  remain_adjust = dist_val
    elif shot_result == "ロスト":
        penalty = 2;  remain_adjust = dist_val
    elif shot_result == "空振り":
        remain_adjust = 0
    elif shot_result == "プレ4":
        penalty = 2;  remain_adjust = 0
    elif shot_result == "プレ3":
        penalty = 1;  remain_adjust = 0

    st.session_state.history.append({
        "club": actual_club, "dist": dist_val,
        "result": shot_result, "penalty": penalty, "green_on": green_on,
    })
    st.session_state.remaining = max(st.session_state.remaining - remain_adjust, 0)
    st.rerun()

if undo:
    if st.session_state.history:
        last      = st.session_state.history.pop()
        back_dist = 0 if last["result"] in ("OB", "空振り") else last["dist"]
        st.session_state.remaining += back_dist
        st.rerun()

# =========================
# 最終スコア入力
# =========================

st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)
st.markdown('<div style="font-size:22px; font-weight:900; color:#1a2e44; margin-top:20px; margin-bottom:6px;">⛳ このホールの最終スコア</div>', unsafe_allow_html=True)

def get_score_name(score, par):
    diff = score - par
    if score == 1:      return "ホールインワン🌸！！", "#e53e3e"
    elif diff <= -3:    return "アルバトロス！！！", "#7c3aed"
    elif diff == -2:    return "イーグル！！", "#f97316"
    elif diff == -1:    return "バーディー！！", "#2563eb"
    elif diff == 0:     return "パー！", "#1a1a1a"
    elif diff == 1:     return "ボギー", "#059669"
    elif diff == 2:     return "ダブルボギー", "#7c3aed"
    else:               return "トリプルボギー以上", "#7f1d1d"

current_score = st.session_state.get(f"final_score_input_{hole}", par_num)
if isinstance(current_score, str):
    current_score = int(current_score.replace("打", ""))
sname, scolor = get_score_name(current_score, par_num)
st.markdown(
    f"<div style='font-size:24px; font-weight:700; color:{scolor}; margin-bottom:4px;'>{current_score}打　{sname}</div>",
    unsafe_allow_html=True
)

def update_actual_score():
    st.session_state[f"actual_{hole}"] = st.session_state[f"final_score_input_{hole}"]

final_score = st.radio(
    "", list(range(1, 17)),
    index=max(current_score - 1, 0),
    key=f"final_score_input_{hole}",
    label_visibility="collapsed",
    horizontal=True,
    on_change=update_actual_score,
)
st.session_state[f"actual_{hole}"] = final_score

reset_col, _, __ = st.columns([1, 1, 1])
with reset_col:
    st.markdown('<div id="reset-all-anchor"></div>', unsafe_allow_html=True)
    reset_all = st.button("✖ 実績をすべてリセット", key="btn_reset_all", use_container_width=True)

if reset_all:
    st.session_state.history            = []
    st.session_state.green_on_flag      = False
    st.session_state.last_caddy_message = ""
    st.session_state.caddy_log          = []
    st.session_state.pop("hole_select", None)
    st.session_state.remaining = st.session_state.course[1]["yard"]
    for h in st.session_state.course.keys():
        st.session_state.pop(f"actual_{h}", None)
        st.session_state.pop(f"final_score_input_{h}", None)
    st.session_state.voice_club   = None
    st.session_state.voice_dist   = None
    st.session_state.voice_result = None
    st.session_state.voice_text   = ""
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
                "name": name, "dist": 0 if dist == "未設定" else dist,
                "miss": miss, "favorite": 0 if favorite == "未設定" else favorite,
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
        "1W":1,"3W":2,"5W":3,"3U":4,"4U":5,"5U":6,"6U":7,
        "5I":8,"6I":9,"7I":10,"8I":11,"9I":12,
        "PW":13,"AW":14,"UW":15,"SW":16,"52°":17,"56°":18,"58°":19,"60°":20,
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
            st.session_state.last_caddy_message   = ""
            st.session_state.caddy_log            = []
            st.session_state.pop("hole_select", None)
            st.session_state.remaining = list(preset["holes"].values())[0]["yard"]
            for h, data in preset["holes"].items():
                st.session_state[f"par_{h}"]  = data["par"]
                st.session_state[f"yard_{h}"] = data["yard"]
                st.session_state.pop(f"actual_{h}", None)
                st.session_state.pop(f"final_score_input_{h}", None)
            st.rerun()

    edited_course = {}
    par_options   = ["Par", 3, 4, 5, 6]

    for h in st.session_state.course.keys():
        cur_par  = st.session_state.course[h]["par"]
        cur_yard = st.session_state.course[h]["yard"]
        cur_memo = st.session_state.course[h].get("memo", "")

        c1, c2, c3, c4, c5 = st.columns([0.7, 0.4, 1.0, 0.5, 1.8])
        with c1:
            st.markdown(f"<div style='font-size:16px; font-weight:700; color:#2563eb; padding-top:10px;'>{h}番ホール</div>", unsafe_allow_html=True)
        with c2:
            st.markdown("<div style='font-size:22px; font-weight:700; color:#4a5568; padding-top:10px;'>Par</div>", unsafe_allow_html=True)
        with c3:
            par_idx = par_options.index(cur_par) if cur_par in par_options else 0
            par_sel = st.selectbox("", par_options, index=par_idx, key=f"par_{h}", label_visibility="collapsed")
            par = cur_par if par_sel == "Par" else int(par_sel)
        with c4:
            st.markdown("<div style='font-size:17px; font-weight:600; color:#4a5568; padding-top:12px;'>距離(y)</div>", unsafe_allow_html=True)
        with c5:
            yard = st.number_input("", 50, 700, cur_yard, key=f"yard_{h}", label_visibility="collapsed")

        # ホールメモ入力欄
        memo = st.text_area(
            f"{h}番ホール メモ（キャディへの情報）",
            value=cur_memo,
            key=f"memo_{h}",
            height=68,
            placeholder="例：右OBに注意。グリーンは手前から攻めること。",
            label_visibility="visible",
        )
        edited_course[h] = {"par": par, "yard": yard, "memo": memo}

    if st.button("✅ コース設定を保存", key="btn_save_course", use_container_width=True):
        for h, data in edited_course.items():
            st.session_state.course[h] = data
        st.success("コース設定を保存しました")
        st.rerun()

# =========================
# APIキー設定
# =========================

with st.expander("🔑 APIキー設定", expanded=False):
    st.markdown(
        "<div style='font-size:18px; color:#4a5568; margin-bottom:8px;'>"
        "音声機能にはOpenAI APIキーが必要です。<br>"
        "Streamlit CloudのSecretsに <code>OPENAI_API_KEY</code> を設定してください。"
        "</div>",
        unsafe_allow_html=True
    )
    if st.secrets.get("OPENAI_API_KEY", ""):
        st.success("✅ APIキーは設定済みです")
    else:
        st.warning("⚠️ APIキーが未設定です。Streamlit CloudのSecretsに設定してください。")
