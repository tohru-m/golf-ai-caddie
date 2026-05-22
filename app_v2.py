import streamlit as st
import tempfile
import os

st.set_page_config(
    page_title="AIキャディ",
    page_icon="⛳"
)

from streamlit_local_storage import LocalStorage
_localS = LocalStorage()

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
                language="ja",
                prompt="ゴルフ、ドライバー、ワンウッド、1W、3W、5W、7W、アイアン、3番、4番、5番、6番、7番、8番、9番、PW、AW、SW、パター、フェアウェイ、ラフ、バンカー、グリーン、OB、ピン、パー、バーディー、ボギー、ヤード、残り、距離"
            )
        os.unlink(tmp_path)
        text = transcript.text
        # 既知の誤認識・話し言葉をクラブ名に変換（長い語を先に処理）
        _corrections = {
            # 1W
            "1番ウッド": "1W", "１番ウッド": "1W",
            "イチバット": "1W", "いちばっと": "1W", "1バット": "1W", "一バット": "1W",
            "ワンバット": "1W", "ワンウッド": "1W", "ドライバー": "1W",
            # 2W
            "2番ウッド": "2W", "２番ウッド": "2W", "ツーウッド": "2W", "ツーバット": "2W",
            # 3W
            "3番ウッド": "3W", "３番ウッド": "3W", "スリーウッド": "3W", "スリーバット": "3W", "3バット": "3W",
            # 5W
            "5番ウッド": "5W", "５番ウッド": "5W", "ファイブウッド": "5W", "ファイブバット": "5W", "5バット": "5W",
            # UT（番号付きを先に）
            "3番ユーティリティー": "3U", "3番ユーティリティ": "3U", "３番ユーティリティー": "3U", "３番ユーティリティ": "3U",
            "4番ユーティリティー": "4U", "4番ユーティリティ": "4U", "４番ユーティリティー": "4U", "４番ユーティリティ": "4U",
            "5番ユーティリティー": "5U", "5番ユーティリティ": "5U", "５番ユーティリティー": "5U", "５番ユーティリティ": "5U",
            "ユーティリティー": "UT", "ユーティリティ": "UT",
            # アイアン
            "3番アイアン": "3I", "３番アイアン": "3I",
            "4番アイアン": "4I", "４番アイアン": "4I",
            "5番アイアン": "5I", "５番アイアン": "5I",
            "6番アイアン": "6I", "６番アイアン": "6I",
            "7番アイアン": "7I", "７番アイアン": "7I",
            "8番アイアン": "8I", "８番アイアン": "8I",
            "9番アイアン": "9I", "９番アイアン": "9I",
            # ウェッジ
            "ピッチングウェッジ": "PW", "ピッチング": "PW", "ピーダブリュー": "PW", "ピーダブル": "PW",
            "アンダーウェッジ": "UW",
            "サンドウェッジ": "SW", "エスダブリュー": "SW",
            "エーダブリュー": "AW",
        }
        for wrong, correct in _corrections.items():
            text = text.replace(wrong, correct)
        import re
        # 「イチ/ワン/1/一 + バット/バッド/パット系」→ 1W（Whisperの誤認識を正規表現で一括処理）
        text = re.sub(r'[iイ][tチ][iイ]?\s*[bバぱパ][aァ]?[tッっ][tトドど]', '1W', text, flags=re.IGNORECASE)
        text = re.sub(r'(イチ|ワン|1|１|一)\s*[バパぱ][ッっ][トドど]', '1W', text)
        # 話し言葉の「度」を°に変換してクラブ名と一致させる（52度 → 52°）
        text = re.sub(r'(\d+)\s*度', lambda m: m.group(1) + "°", text)
        return text
    except Exception as e:
        st.error(f"音声認識エラー：{e}")
        return ""


# =========================
# GPT：ショット入力 or キャディへの質問を自動判断
# =========================

def _best_club(remaining: int, clubs: list) -> dict:
    """届くクラブの中で最短のもの。届かなければ最大飛距離クラブ。"""
    reachable = [c for c in clubs if c["dist"] >= remaining]
    if reachable:
        return min(reachable, key=lambda c: c["dist"])
    return max(clubs, key=lambda c: c["dist"])



def handle_voice_input(text: str, clubs: list, context: dict) -> str:
    try:
        import openai, re as _re
        api_key = st.secrets.get("OPENAI_API_KEY", "")
        if not api_key:
            return "APIキーが設定されていません。"
        client = openai.OpenAI(api_key=api_key)

        hole_memo = context.get("hole_memo", "")
        remaining = context["remaining"]

        def _plan_to_voice(plan_data):
            parts = []
            for i, p in enumerate(plan_data):
                d = min(p["dist"], p["before"])
                if d <= 0 or p["before"] <= 0:
                    continue
                c = _normalize_for_tts(p["club"])
                prefix = "" if i == 0 else ("次に" if i == 1 else "さらに")
                if p["remain"] == 0:
                    parts.append(f"{prefix}{c}で{d}ヤードを打ってグリーンオン")
                else:
                    parts.append(f"{prefix}{c}で{d}ヤード")
            if parts:
                if parts[-1].endswith("グリーンオン"):
                    parts[-1] += "です"
                else:
                    parts[-1] += "を打ちます"
            return "、".join(parts)

        # 発話に「○ヤード飛んだ／飛ばなかった」が含まれる場合はゲーム状態を更新してプランを返す
        _shot_dist = _re.search(r'(\d+)\s*ヤード', text)
        _shot_ctx  = _re.search(r'(飛|打った|打ち|打ちました|だった|でした|しか|だけ|届か|飛ばなかった|飛んだ|飛びました)', text)
        shot_match = _shot_dist if (_shot_dist and _shot_ctx) else None
        if shot_match:
            actual = int(shot_match.group(1))
            new_remaining = max(remaining - actual, 0)
            strokes_left = max(context["remaining_strokes"] - 1, 1)
            club_used = context.get("next_club", "?")
            st.session_state.history.append({
                "club": club_used, "dist": actual,
                "result": "FW", "penalty": 0, "green_on": (new_remaining == 0), "voice": True,
            })
            st.session_state.remaining = new_remaining
            if new_remaining == 0:
                return f"{actual}ヤードでグリーンオンです！お見事でした。"
            used_new = sum(1 + h.get("penalty", 0) for h in st.session_state.history)
            plan_data = plan(new_remaining, strokes_left, used_new, context["par"], context["hole"])
            return f"{actual}ヤードでしたか。残り{new_remaining}ヤードです。{_plan_to_voice(plan_data)}。"

        # 戦略・プランに関する質問は plan() で直接計算して返す
        strategy_match = _re.search(r'(戦略|プラン|作戦|計画|どう打|何打|どのクラブ|クラブは|どれ|見直)', text)
        if strategy_match and context.get("remaining_strokes", 0) > 0:
            _used = sum(1 + h.get("penalty", 0) for h in st.session_state.history)
            _rs = context["remaining_strokes"]
            _plan_data = plan(remaining, _rs, _used, context["par"], context["hole"])
            _shots_to_green = next((i+1 for i, p in enumerate(_plan_data) if p["remain"] == 0), len(_plan_data))
            _spare = _rs - _shots_to_green
            _spare_note = f"、{_spare}打余裕があります" if _spare > 0 else ""
            _raw_memo = context.get("hole_memo", "")
            _memo_sentences = [s for s in _raw_memo.split("。") if s.strip()]
            _memo_short = "。".join(_memo_sentences[:2]) + ("。" if _memo_sentences else "")
            _memo_note = f"　なお、{_memo_short}" if _memo_short else ""
            return f"{context['hole']}番ホール、{remaining}ヤード、{_plan_to_voice(_plan_data)}{_spare_note}。{_memo_note}"

        rec = _best_club(remaining, clubs)
        calc_info = f"残り{remaining}y → 推奨クラブ：{rec['name']}（{rec['dist']}y）"

        prompt = f"""あなたはベテランのゴルフキャディです。以下の計算結果と状況を踏まえ、2〜3文でキャディらしく答えてください。

【計算済み推奨】{calc_info}
【状況】{context['hole']}番ホール Par{context['par']} {context['yard']}y／残り{remaining}y／残りショット{context['remaining_strokes']}回／目標{context['target']}打
【戦略プラン】{context.get("plan_text", "なし")}
【ホールメモ】{hole_memo if hole_memo else "なし"}
【質問】{text}

ルール：
- 「〜ですよ」「〜しましょう」など親しみやすいキャディ口調
- 戦略を聞かれたら「戦略プラン」を自然な会話に変換して答える
- クラブ推奨は必ず「計算済み推奨」をそのまま使うこと（変更しない）
- 回答のみ返す（前置き不要）"""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=150,
        )
        return response.choices[0].message.content.strip()

    except Exception as e:
        st.error(f"エラー：{e}")
        return "すみません、うまく聞き取れませんでした。もう一度お願いできますか？"


# =========================
# OpenAI TTS による音声読み上げ
# =========================

def _normalize_for_tts(text: str) -> str:
    _tts = {
        "S字": "エス字",
        "とよい": "といいです",
        "と良い": "といいです",
        "1W": "ドライバー", "2W": "2番ウッド", "3W": "3番ウッド",
        "4W": "4番ウッド", "5W": "5番ウッド", "7W": "7番ウッド",
        "3U": "3番ユーティリティ", "4U": "4番ユーティリティ",
        "5U": "5番ユーティリティ", "6U": "6番ユーティリティ",
        "3I": "3番アイアン", "4I": "4番アイアン", "5I": "5番アイアン",
        "6I": "6番アイアン", "7I": "7番アイアン", "8I": "8番アイアン", "9I": "9番アイアン",
        "PW": "ピッチングウェッジ", "UW": "アンダーウェッジ",
        "AW": "アプローチウェッジ", "SW": "サンドウェッジ",
        "°": "度",
    }
    for abbr, spoken in _tts.items():
        text = text.replace(abbr, spoken)
    return text


def _plan_to_voice(plan_data):
    parts = []
    for i, p in enumerate(plan_data):
        d = min(p["dist"], p["before"])
        if d <= 0 or p["before"] <= 0:
            continue
        c = _normalize_for_tts(p["club"])
        prefix = "" if i == 0 else ("次に" if i == 1 else "さらに")
        if p["remain"] == 0:
            parts.append(f"{prefix}{c}で{d}ヤードを打ってグリーンオン")
        else:
            parts.append(f"{prefix}{c}で{d}ヤード")
    if parts:
        if parts[-1].endswith("グリーンオン"):
            parts[-1] += "です"
        else:
            parts[-1] += "を打ちます"
    return "、".join(parts)


def get_tts_bytes(text: str):
    try:
        import openai
        api_key = st.secrets.get("OPENAI_API_KEY", "")
        if not api_key:
            return None
        client = openai.OpenAI(api_key=api_key)
        response = client.audio.speech.create(
            model="tts-1",
            voice="nova",
            speed=1.2,
            input=_normalize_for_tts(text),
        )
        return response.content
    except Exception as _e:
        st.warning(f"音声生成エラー: {_e}")
        return None


def speak_with_browser(text: str, label: str = "▶ キャディの回答を聞く", pausable: bool = False):
    text = _normalize_for_tts(text)
    escaped = text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")
    import streamlit.components.v1 as components
    if pausable:
        onclick = (
            f"if (window.speechSynthesis.paused) {{"
            f"  window.speechSynthesis.resume();"
            f"  this.innerHTML = '⏸ 一時停止';"
            f"}} else if (window.speechSynthesis.speaking) {{"
            f"  window.speechSynthesis.pause();"
            f"  this.innerHTML = '▶ 再生を再開';"
            f"}} else {{"
            f"  window.speechSynthesis.cancel();"
            f"  var u = new SpeechSynthesisUtterance('{escaped}');"
            f"  u.lang = 'ja-JP'; u.rate = 1.1;"
            f"  var b = document.getElementById('btn');"
            f"  u.onend = function() {{ b.innerHTML = '{label}'; }};"
            f"  window.speechSynthesis.speak(u);"
            f"  this.innerHTML = '⏸ 一時停止';"
            f"}}"
        )
    else:
        onclick = (
            f"window.speechSynthesis.cancel();"
            f"var u = new SpeechSynthesisUtterance('{escaped}');"
            f"u.lang = 'ja-JP'; u.rate = 1.1;"
            f"window.speechSynthesis.speak(u);"
            f"this.innerHTML = '⏸ 再生中...';"
            f"u.onend = function() {{ document.getElementById('btn').innerHTML = '▶ もう一度聞く'; }};"
        )
    components.html(
        f"""
        <button onclick="{onclick}" id="btn" style="
            font-size:22px; font-weight:700;
            padding:14px 20px; width:100%;
            background:#1a2e44; color:white;
            border:none; border-radius:14px;
            cursor:pointer; margin-top:4px;
        ">{label}</button>
        """,
        height=62,
    )


# =========================
# スマホ向けグローバルCSS（app_v2.pyと同じ）
# =========================

st.markdown("""
<style>

@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;700;900&display=swap');

html, body, [class*="css"] {
    font-family: 'Noto Sans JP', sans-serif;
}
.stApp { background: #f0f4f8; }

.ui-label { font-size:17px; font-weight:700; color:#1a2e44; display:block; margin-top:20px; margin-bottom:6px; }
.ui-label-small { font-size:22px; font-weight:700; color:#4a5568; display:block; margin-bottom:4px; margin-top:8px; }
.ui-label-fixed { font-size:16px; font-weight:700; color:#1a2e44; display:block; margin-bottom:6px; margin-top:10px; }

.card { background:white; border-radius:16px; padding:16px; margin-bottom:20px; box-shadow:0 2px 12px rgba(0,0,0,0.08); }

.shot-row { background:#dbeafe; border-left:4px solid #3b82f6; border-radius:8px; padding:10px 20px; margin:6px 0; font-size:26px; line-height:1.5; }
.shot-row-history { background:#ffffff; border-left:4px solid #60a5fa; border-radius:8px; padding:10px 20px; margin:6px 0; font-size:26px; color:#1e40af; line-height:1.5; }
.shot-row-warn { background:#fff7ed; border-left:4px solid #f97316; border-radius:8px; padding:10px 20px; margin:6px 0; font-size:26px; line-height:1.5; }

.voice-box { background:#f0fdf4; border:2px solid #86efac; border-radius:20px; padding:20px 16px; margin:10px 0 20px 0; }
.voice-box-caddy { background:#eff6ff; border:2px solid #93c5fd; border-radius:20px; padding:20px 16px; margin:10px 0 20px 0; }
.voice-result { background:#fefce8; border:2px solid #fde68a; border-radius:10px; padding:10px 20px; font-size:22px; font-weight:700; color:#92400e; margin-top:8px; }

.caddy-bubble { background:#1a2e44; color:white; border-radius:18px 18px 18px 4px; padding:16px 20px; margin:10px 0 16px 0; font-size:24px; font-weight:700; line-height:1.6; }
.caddy-bubble::before { content:"🏌️ キャディ"; display:block; font-size:16px; font-weight:900; color:#93c5fd; margin-bottom:6px; }

[data-testid="stAudioInput"] label p { font-size:26px !important; font-weight:700 !important; color:#b91c1c !important; }
[data-testid="stAudioInput"] button { width:72px !important; height:72px !important; min-width:72px !important; min-height:72px !important; border-radius:50% !important; }
[data-testid="stAudioInput"] button svg { width:38px !important; height:38px !important; }
[data-testid="stAudioInput"] button svg rect { display:none !important; }
[data-testid="stAudioInput"] button:has(svg rect) { background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E%3Cpath fill='white' d='M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3zm-1-9c0-.55.45-1 1-1s1 .45 1 1v6c0 .55-.45 1-1 1s-1-.45-1-1V5zm6 6c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z'/%3E%3C/svg%3E") !important; background-repeat:no-repeat !important; background-position:center !important; background-size:38px 38px !important; }



div:has(> #voice-apply-anchor) + div[data-testid="stButton"] > button { height:80px !important; font-size:38px !important; }
div:has(#adjust-btn-anchor) ~ div [data-testid="stColumn"] button { font-size:26px !important; font-weight:700 !important; }

[data-testid="stColumn"]:has(#confirm-score-anchor) button { font-size:22px !important; font-weight:900 !important; background-color:#d0e8ff !important; border:2px solid #1a56a0 !important; color:#1a2e44 !important; }
[data-testid="stColumn"]:has(#reset-all-anchor) button { background-color:#fce7f3 !important; border-color:#f472b6 !important; color:#9d174d !important; font-size:22px !important; }
div:has(#load-preset-anchor) + div[data-testid="stButton"] > button { font-size:22px !important; }

.hole-header { background:linear-gradient(135deg,#1a2e44 0%,#2d4a6e 100%); color:white; border-radius:20px; padding:12px 18px; margin:10px 0 8px 0; display:flex; align-items:center; justify-content:flex-start; gap:2px; }
.hole-header h2 { margin:0; font-size:24px; font-weight:900; color:white; white-space:nowrap; }
.hole-header .sub { font-size:28px; font-weight:900; color:#93c5fd; white-space:nowrap; }

.remain-badge { background:linear-gradient(135deg,#065f46,#059669); color:white; border-radius:12px; padding:12px 18px; font-size:20px; font-weight:900; text-align:center; margin:10px 0; }

div[data-testid="stFormSubmitButton"] > button,
div[data-testid="stButton"] > button { height:62px !important; font-size:22px !important; font-weight:700 !important; border-radius:12px !important; width:100% !important; padding-top:0 !important; padding-bottom:0 !important; transition:all 0.15s ease; }
div[data-testid="stFormSubmitButton"] > button:active,
div[data-testid="stButton"] > button:active { transform:scale(0.97); }

div:has(#target-score-anchor) + div [data-testid="stSelectbox"] > div > div,
div:has(#target-score-anchor) + div [data-testid="stSelectbox"] select { font-size:30px !important; font-weight:700 !important; }
div:has(#target-score-anchor) + div [data-testid="stSelectbox"] span { font-size:30px !important; font-weight:700 !important; }
[data-testid="stSelectboxVirtualDropdown"] li, [data-testid="stSelectboxVirtualDropdown"] li span { font-size:16px !important; }

div:has(#preset-select-anchor) + div [data-testid="stSelectbox"] > div > div,
div:has(#preset-select-anchor) + div [data-testid="stSelectbox"] select { font-size:14px !important; min-height:28px !important; }
div:has(#preset-select-anchor) + div [data-testid="stSelectbox"] span { font-size:14px !important; }
div:has(#preset-select-anchor) + div [data-testid="stSelectbox"] label p { font-size:14px !important; }

div[data-testid="stSelectbox"] { max-width:100% !important; }
div[data-testid="stSelectbox"] select, div[data-testid="stSelectbox"] > div > div { font-size:26px !important; min-height:52px !important; font-weight:700 !important; background-color:#fefce8 !important; }
div[data-testid="stSelectbox"] span { font-size:26px !important; font-weight:700 !important; }

div[data-testid="stNumberInput"] input { font-size:26px !important; height:52px !important; font-weight:700 !important; background-color:#fefce8 !important; }

div[data-testid="stCheckbox"] label { font-size:26px !important; font-weight:700 !important; }
div[data-testid="stCheckbox"] input[type="checkbox"] { width:24px !important; height:24px !important; accent-color:#1a2e44; cursor:pointer; outline:3px solid #1a2e44 !important; outline-offset:2px; }

div[data-testid="stExpander"] summary,
div[data-testid="stExpander"] summary p,
div[data-testid="stExpander"] summary span,
div[data-testid="stExpander"] details summary { font-size:22px !important; font-weight:900 !important; line-height:1.2 !important; }

div[data-testid="stForm"] { background:white; border-radius:16px; padding:16px !important; box-shadow:0 2px 12px rgba(0,0,0,0.08); border:none !important; }

.score-cell { font-size:22px; padding:4px 0; }
.section-divider { height:1px; background:#e2e8f0; margin:20px 0; }

div[data-testid="stRadio"] { border:none !important; box-shadow:none !important; background:transparent !important; padding:0 !important; width:100% !important; display:block !important; }
div[data-testid="stRadio"] [data-testid="stWidgetLabel"] { display:none !important; }
div[data-testid="stRadio"] > div:last-child { display:grid !important; grid-template-columns:repeat(3, 1fr) !important; gap:6px !important; width:100% !important; }
div[data-testid="stRadio"] label { display:flex !important; align-items:center !important; justify-content:center !important; height:60px !important; background:white !important; border:2px solid #9ca3af !important; border-radius:8px !important; cursor:pointer !important; padding:0 8px !important; margin:0 !important; color:#1a1a1a !important; }
div[data-testid="stRadio"] label p, div[data-testid="stRadio"] label span { font-size:24px !important; font-weight:700 !important; color:#1a1a1a !important; }
div[data-testid="stRadio"] label:has(input[type="radio"]:checked) { background:#1a2e44 !important; border-color:#1a2e44 !important; }
div[data-testid="stRadio"] label:has(input[type="radio"]:checked) p,
div[data-testid="stRadio"] label:has(input[type="radio"]:checked) span { color:white !important; }
div[data-testid="stRadio"] input[type="radio"] { display:none !important; }

[data-testid="stRadio"] > div:last-child:has(> label:nth-child(18)):not(:has(> label:nth-child(19))) { grid-template-columns:repeat(6, 1fr) !important; }
[data-testid="stRadio"] > div:last-child:has(> label:nth-child(18)):not(:has(> label:nth-child(19))) label > *:first-child { display:none !important; }
[data-testid="stRadio"] > div:last-child:has(> label:nth-child(8)):not(:has(> label:nth-child(9))) { grid-template-columns:repeat(5, 1fr) !important; width:100% !important; }
[data-testid="stRadio"] > div:last-child:has(> label:nth-child(8)):not(:has(> label:nth-child(9))) label > *:first-child { display:none !important; }
[data-testid="stRadio"] > div:last-child:has(> label:nth-child(4)):not(:has(> label:nth-child(5))) { grid-template-columns:repeat(4, 1fr) !important; width:100% !important; }
[data-testid="stRadio"] > div:last-child:has(> label:nth-child(4)):not(:has(> label:nth-child(5))) label > *:first-child { display:none !important; }
[data-testid="stRadio"] > div:last-child:has(> label:nth-child(16)):not(:has(> label:nth-child(17))) { grid-template-columns:repeat(4, 1fr) !important; width:100% !important; }
[data-testid="stRadio"] > div:last-child:has(> label:nth-child(16)):not(:has(> label:nth-child(17))) label > *:first-child { display:none !important; }
[data-testid="stRadio"] > div:last-child:has(> label:nth-child(10)):not(:has(> label:nth-child(11))) { grid-template-columns:repeat(4, 1fr) !important; width:100% !important; }
[data-testid="stRadio"] > div:last-child:has(> label:nth-child(10)):not(:has(> label:nth-child(11))) label > *:first-child { display:none !important; }
[data-testid="stRadio"] > div:last-child:has(> label:nth-child(10)):not(:has(> label:nth-child(11))) label p,
[data-testid="stRadio"] > div:last-child:has(> label:nth-child(10)):not(:has(> label:nth-child(11))) label span { font-size:18px !important; }
[data-testid="stRadio"] > div:last-child:has(> label:nth-child(10)):not(:has(> label:nth-child(11))) label:nth-child(10) p,
[data-testid="stRadio"] > div:last-child:has(> label:nth-child(10)):not(:has(> label:nth-child(11))) label:nth-child(10) span { color:#e53e3e !important; }
[data-testid="stRadio"] > div:last-child:has(> label:nth-child(11)):not(:has(> label:nth-child(12))) { grid-template-columns:repeat(5, 1fr) !important; width:100% !important; }
[data-testid="stRadio"] > div:last-child:has(> label:nth-child(11)):not(:has(> label:nth-child(12))) label > *:first-child { display:none !important; }

</style>
""", unsafe_allow_html=True)

# =========================
# 定数・初期データ（ホールメモ付きプリセット）
# =========================

PRESET_COURSES = {
    "大阪パブリックゴルフ場（フロント）": {
        "name": "大阪パブリックゴルフ場", "tee": "FRO",
        "holes": {
            1:  {"par": 4, "yard": 228, "memo": "難易度14位。第1打はフェアウェイをキープし2打目でグリーンを狙う。グリーン奥のOBゾーンに注意。"},
            2:  {"par": 4, "yard": 282, "memo": "難易度5位。OB率49%とコース屈指の難ホール。第1打は正面バンカー左横が狙い目。地形のアップダウンで距離感に注意。右側バンカーに入れるとパーセーブが難しくなる。"},
            3:  {"par": 5, "yard": 506, "memo": "難易度4位。OB率63%と非常に高い。第1打は前方左斜面が狙い目。右の並木越え最短ルートはOBリスク大。グリーンはピンより手前からの攻めがベター。"},
            4:  {"par": 4, "yard": 235, "memo": "難易度16位。第1打は右斜面中央方向が狙い目。グリーンはピンより手前の攻めがよい。グリーン奥のOBに注意。"},
            5:  {"par": 5, "yard": 410, "memo": "難易度3位。OB率64%。左ドッグレッグのロングホール。第1打はフェアウェイ左側が狙い目。第2打は正面ガイドポール狙い。左に落とすと2打目が攻めにくい。"},
            6:  {"par": 3, "yard": 115, "memo": "難易度17位。打ち下ろしのショートホール。風の影響を受けやすく距離感も難しい。クラブ選択に注意。"},
            7:  {"par": 3, "yard": 154, "memo": "難易度15位。打ち下ろしのショートホール。バンカーに入れるとパーセーブが難しくなる。グリーン上から早いのでピン手前につけたい。"},
            8:  {"par": 4, "yard": 226, "memo": "難易度6位。OB率50%。2打目は打ち上げになるので距離感に注意。バンカー脱出が困難。グリーンはピンより奥につけると難易度が増す。"},
            9:  {"par": 3, "yard": 146, "memo": "難易度13位。谷越えのショートホール。グリーンは右奥より手前にかけて早いため、手前から攻めたい。"},
            10: {"par": 4, "yard": 257, "memo": "難易度7位。OB率65%。第1打は左のバンカー方向が狙いどころ。グリーン奥はOBゾーンが迫っているため、アプローチでのグリーンオーバーに注意。"},
            11: {"par": 3, "yard": 180, "memo": "難易度10位。OB率37%。第1打はやや左グリーン方向が狙い目。高低差があるため距離感に注意。17番との境目はOBなし。グリーン奥はOBが迫っているため注意。"},
            12: {"par": 3, "yard": 127, "memo": "難易度9位。打ち上げのショートホール。高低差と砲台グリーンのためクラブ選択に注意。右側バンカーはやや深め。"},
            13: {"par": 5, "yard": 530, "memo": "難易度1位。OB率68%。右ドッグレッグのロングホール。1打目の並木越えはOBリスク大。2打目以降は高低差と傾斜に注意。アプローチはグリーン手前狙いでグリーン奥はOBのため要注意。"},
            14: {"par": 4, "yard": 295, "memo": "難易度2位。OB率54%。第1打は左フェアウェイ方向の斜面が狙いどころ。アプローチはグリーン奥が早いため手前から攻めるのがベター。"},
            15: {"par": 4, "yard": 234, "memo": "難易度12位。コース幅が狭く第1打はフェアウェイか左側が狙い。グリーンは奥に長く2段グリーンのためアプローチの精度が要求される。"},
            16: {"par": 4, "yard": 298, "memo": "難易度11位。打ち下ろしのミドルホール。コース幅が狭くフェアウェイキープが重要。狙い目はカート道方向。グリーン奥はOBが迫るためアプローチに注意。"},
            17: {"par": 4, "yard": 238, "memo": "難易度8位。OB率54%。左方向11番との境界はOBなし。第1打は谷越えセンターが狙い目。2打目はやや打ち上げ。グリーンは奥から手前にかなり早く、ピン奥につけるとパーセーブが難しくなる。"},
            18: {"par": 4, "yard": 250, "memo": "難易度18位。打ち下ろしのミドルホール。第1打はクラブハウス方向のフェアウェイが狙い目。右側バンカー（アゴが深め）に注意。グリーンはアングレーションが効いているため注意。"},
        }
    },
    "大阪パブリックゴルフ場（レディース）": {
        "name": "大阪パブリックゴルフ場", "tee": "LADIES",
        "holes": {
            1:  {"par": 4, "yard": 223, "memo": "難易度14位。第1打はフェアウェイをキープし2打目でグリーンを狙う。グリーン奥のOBゾーンに注意。"},
            2:  {"par": 4, "yard": 282, "memo": "難易度5位。OB率49%とコース屈指の難ホール。第1打は正面バンカー左横が狙い目。地形のアップダウンで距離感に注意。右側バンカーに入れるとパーセーブが難しくなる。"},
            3:  {"par": 5, "yard": 435, "memo": "難易度4位。OB率63%と非常に高い。第1打は前方左斜面が狙い目。右の並木越え最短ルートはOBリスク大。グリーンはピンより手前からの攻めがベター。"},
            4:  {"par": 4, "yard": 230, "memo": "難易度16位。第1打は右斜面中央方向が狙い目。グリーンはピンより手前の攻めがよい。グリーン奥のOBに注意。"},
            5:  {"par": 5, "yard": 358, "memo": "難易度3位。OB率64%。左ドッグレッグのロングホール。第1打はフェアウェイ左側が狙い目。第2打は正面ガイドポール狙い。左に落とすと2打目が攻めにくい。"},
            6:  {"par": 3, "yard": 112, "memo": "難易度17位。打ち下ろしのショートホール。風の影響を受けやすく距離感も難しい。クラブ選択に注意。"},
            7:  {"par": 3, "yard": 154, "memo": "難易度15位。打ち下ろしのショートホール。バンカーに入れるとパーセーブが難しくなる。グリーン上から早いのでピン手前につけたい。"},
            8:  {"par": 4, "yard": 200, "memo": "難易度6位。OB率50%。2打目は打ち上げになるので距離感に注意。バンカー脱出が困難。グリーンはピンより奥につけると難易度が増す。"},
            9:  {"par": 3, "yard": 146, "memo": "難易度13位。谷越えのショートホール。グリーンは右奥より手前にかけて早いため、手前から攻めたい。"},
            10: {"par": 4, "yard": 255, "memo": "難易度7位。OB率65%。第1打は左のバンカー方向が狙いどころ。グリーン奥はOBゾーンが迫っているため、アプローチでのグリーンオーバーに注意。"},
            11: {"par": 3, "yard": 178, "memo": "難易度10位。OB率37%。第1打はやや左グリーン方向が狙い目。高低差があるため距離感に注意。17番との境目はOBなし。グリーン奥はOBが迫っているため注意。"},
            12: {"par": 3, "yard": 127, "memo": "難易度9位。打ち上げのショートホール。高低差と砲台グリーンのためクラブ選択に注意。右側バンカーはやや深め。"},
            13: {"par": 5, "yard": 418, "memo": "難易度1位。OB率68%。右ドッグレッグのロングホール。1打目の並木越えはOBリスク大。2打目以降は高低差と傾斜に注意。アプローチはグリーン手前狙いでグリーン奥はOBのため要注意。"},
            14: {"par": 4, "yard": 292, "memo": "難易度2位。OB率54%。第1打は左フェアウェイ方向の斜面が狙いどころ。アプローチはグリーン奥が早いため手前から攻めるのがベター。"},
            15: {"par": 4, "yard": 232, "memo": "難易度12位。コース幅が狭く第1打はフェアウェイか左側が狙い。グリーンは奥に長く2段グリーンのためアプローチの精度が要求される。"},
            16: {"par": 4, "yard": 298, "memo": "難易度11位。打ち下ろしのミドルホール。コース幅が狭くフェアウェイキープが重要。狙い目はカート道方向。グリーン奥はOBが迫るためアプローチに注意。"},
            17: {"par": 4, "yard": 234, "memo": "難易度8位。OB率54%。左方向11番との境界はOBなし。第1打は谷越えセンターが狙い目。2打目はやや打ち上げ。グリーンは奥から手前にかなり早く、ピン奥につけるとパーセーブが難しくなる。"},
            18: {"par": 4, "yard": 250, "memo": "難易度18位。打ち下ろしのミドルホール。第1打はクラブハウス方向のフェアウェイが狙い目。右側バンカー（アゴが深め）に注意。グリーンはアングレーションが効いているため注意。"},
        }
    },
    "宝塚ゴルフ倶楽部 新コース（レギュラー）": {
        "name": "宝塚ゴルフ倶楽部", "tee": "REG",
        "holes": {
            1:  {"par": 5, "yard": 438, "elevation": 8.0,
                 "green_side_bunkers": [{"position": "left", "approx_dist": 115, "note": "フェアウェイ左バンカー"}, {"position": "right", "approx_dist": 115, "note": "フェアウェイ右バンカー"}],
                 "green": {"approach_from": "正面手前", "note": "打ち上げ8y。グリーン右サイドにバンカー。手前から攻める"},
                 "memo": "距離の短いストレートなパー5。グリーン左手前30ヤード付近のフェアウェイバンカーを避ける事。2段グリーンのためピン位置に注意。"},
            2:  {"par": 4, "yard": 287, "elevation": 4.8,
                 "green_side_bunkers": [{"position": "left", "approx_dist": 123, "note": "グリーン左バンカー"}, {"position": "right", "approx_dist": 123, "note": "グリーン右バンカー"}],
                 "green": {"approach_from": "正面", "note": "グリーン周りバンカー多数。二段グリーン"},
                 "memo": "距離は短いがバンカーが効いているためセカンドを考えてティーショットすること。グリーンは砲台で奥行きが短いため、正確な距離感が求められる。"},
            3:  {"par": 3, "yard": 205, "elevation": 0,
                 "green_side_bunkers": [{"position": "left", "approx_dist": 0, "note": "グリーン左バンカー"}],
                 "green": {"approach_from": "正面", "note": "打ち降ろしのPar3。グリーン複雑な傾斜"},
                 "memo": "距離のある打ち降ろしのパー3。2段グリーンで右手前には深いグラスバンカーがあり、グリーンをオーバーすると難しいアプローチが残る。風への注意が必要。"},
            4:  {"par": 5, "yard": 450, "elevation": 16.5,
                 "green_side_bunkers": [{"position": "left", "approx_dist": 89, "note": "グリーン左サイド。左に池"}],
                 "green": {"approach_from": "正面手前", "note": "打ち上げ16.5y。急傾斜。絶対に奥に外さない"},
                 "memo": "右ドッグレッグのパー5。ティーショットは左サイドが狙い目。グリーン手前50ヤード付近には松があるため刻むか攻めるかの判断が必要。"},
            5:  {"par": 4, "yard": 352, "elevation": 0,
                 "green_side_bunkers": [{"position": "left", "approx_dist": 93, "note": "グリーン左バンカー"}],
                 "green": {"approach_from": "正面", "note": "比較的フラット。二段グリーン気味"},
                 "memo": "ティーショットはフェアウェイ右バンカーを避け左サイド狙い。残り80ヤード付近からくぼんでいるため打ち過ぎに注意。グリーン手前バンカーにつかまると厄介。"},
            6:  {"par": 4, "yard": 455, "elevation": -11.0,
                 "green_side_bunkers": [{"position": "left", "approx_dist": 65, "note": "フェアウェイ左バンカー"}],
                 "green": {"approach_from": "正面", "note": "打ち下ろし11y。比較的フラット"},
                 "memo": "距離のあるストレートなパー4。アウトでは一番難易度の高いホール。グリーン左手前のバンカーに注意。"},
            7:  {"par": 3, "yard": 158, "elevation": 0,
                 "green_side_bunkers": [],
                 "green": {"approach_from": "正面", "note": "Par3。グリーン奥は急傾斜+11"},
                 "memo": "グリーンはバンカーに囲まれているため正確なショットが要求される。ダムからの吹き抜け風に注意が必要。縦長の2段グリーンで奥から手前に速い。"},
            8:  {"par": 4, "yard": 424, "elevation": -5.6,
                 "green_side_bunkers": [{"position": "left", "approx_dist": 104, "note": "グリーン左バンカー"}],
                 "green": {"approach_from": "右（花道）", "note": "打ち下ろし5.6y。左に川。グリーン複雑"},
                 "memo": "左ドッグレッグのパー4。ティーショットは右サイドからコースを広く使いたいが、ロングヒッターは右への突き抜けに注意。セカンドからは方向性に注意し無理せず安全に攻めたい。"},
            9:  {"par": 4, "yard": 400, "elevation": -6.3,
                 "green_side_bunkers": [{"position": "left", "approx_dist": 113, "note": "グリーン左バンカー"}, {"position": "right", "approx_dist": 113, "note": "グリーン右バンカー"}],
                 "green": {"approach_from": "正面", "note": "打ち下ろし6.3y。グリーン左右バンカー"},
                 "memo": "やや打ち下ろしのストレートなパー4。ティーショット・セカンドともに風への注意が必要。グリーンは手前から速い。"},
            10: {"par": 5, "yard": 522, "elevation": -5.9,
                 "green_side_bunkers": [{"position": "left", "approx_dist": 53, "note": "グリーン左バンカー"}],
                 "green": {"approach_from": "右（花道）", "note": "打ち下ろし5.9y。グリーン複雑な傾斜"},
                 "memo": "S字のパー5。方向性と距離のジャッジを正確に。グリーン手前30ヤード付近に松があるためセカンドの方向性に注意が必要。"},
            11: {"par": 4, "yard": 288, "elevation": 4.1,
                 "green_side_bunkers": [{"position": "left", "approx_dist": 103, "note": "グリーン左バンカー"}, {"position": "right", "approx_dist": 103, "note": "グリーン右バンカー"}],
                 "green": {"approach_from": "正面手前", "note": "打ち上げ4.1y。グリーン奥は急傾斜。手前から"},
                 "memo": "バンカーが多いためティーショットがキーポイントとなる。打ち上げのため距離感がつかみにくい。グリーンは2段で奥に外すと難しいアプローチが残る。"},
            12: {"par": 3, "yard": 152, "elevation": 0,
                 "green_side_bunkers": [],
                 "green": {"approach_from": "正面", "note": "Par3。グリーン奥は急傾斜+9"},
                 "memo": "グリーンは左手前から右奥に向かって長く大きい。ピン位置によっては1クラブ以上の違いあり。方向性と距離感が要求されるホール。"},
            13: {"par": 4, "yard": 391, "elevation": 0,
                 "green_side_bunkers": [{"position": "left", "approx_dist": 87, "note": "グリーン左バンカー"}, {"position": "right", "approx_dist": 87, "note": "グリーン右バンカー"}],
                 "green": {"approach_from": "正面", "note": "グリーン左右バンカー。手前から攻める"},
                 "memo": "ティーショットは左方向が狙い目。右はOB、左はレッドペナルティーエリア。グリーン両サイドは奥行きがないため正確な距離感が必要。"},
            14: {"par": 4, "yard": 439, "elevation": 10.6,
                 "green_side_bunkers": [{"position": "left", "approx_dist": 114, "note": "グリーン左バンカー"}],
                 "green": {"approach_from": "正面手前", "note": "打ち上げ10.6y。グリーン奥は急傾斜+11"},
                 "memo": "距離のあるパー4。ティーショットは右カート道（カートみち）方向が狙い目。左の谷へ落ちた場合は無理をせずフェアウェイに戻した方がよい。フェアウェイ・グリーンともに左に傾斜している。"},
            15: {"par": 3, "yard": 193, "elevation": -4.4,
                 "green_side_bunkers": [{"position": "left", "approx_dist": 83, "note": "グリーン左バンカー"}],
                 "green": {"approach_from": "右（花道）", "note": "打ち下ろし4.4y。グリーン左バンカー注意"},
                 "memo": "名物ホールのパー3。打ち下ろしのため距離感に注意。手前バンカーにつかまった場合は、後方または横に出す勇気も必要。"},
            16: {"par": 4, "yard": 340, "elevation": -1.8,
                 "green_side_bunkers": [],
                 "green": {"approach_from": "正面", "note": "グリーン手前に小さな池。手前から攻める"},
                 "memo": "戦略性のあるやや右ドッグレッグのパー4。左右にフェアウェイバンカーがあるためティーショットがキーポイントとなる。グリーン左手前には池。セカンドは見た目以上に上っているため少し大き目のクラブで。"},
            17: {"par": 5, "yard": 490, "elevation": -2.6,
                 "green_side_bunkers": [{"position": "left", "approx_dist": 68, "note": "グリーン左バンカー"}, {"position": "right", "approx_dist": 68, "note": "グリーン右バンカー"}],
                 "green": {"approach_from": "正面", "note": "打ち下ろし2.6y。グリーン左右バンカー注意"},
                 "memo": "ゆるやかに打ち上げている右ドッグレッグのパー5。全体的に左から攻めるとよい。2段グリーンのためピン位置に注意。"},
            18: {"par": 4, "yard": 445, "elevation": -6.3,
                 "green_side_bunkers": [{"position": "left", "approx_dist": 113, "note": "グリーン左バンカー"}],
                 "green": {"approach_from": "右（花道）", "note": "打ち下ろし6.3y。グリーン左バンカー注意"},
                 "memo": "距離のある打ち下ろしのパー4。ティーショットはやや右サイドが狙い目だが、右に行き過ぎるとOBになりやすく残り距離が長くなるため注意が必要。3段グリーンでピン位置により難易度が変わる。"},
        }
    },
    "宝塚ゴルフ倶楽部 新コース（フロント）": {
        "name": "宝塚ゴルフ倶楽部", "tee": "FRO",
        "holes": {
            1:  {"par": 5, "yard": 425, "elevation": 8.0,
                 "green_side_bunkers": [{"position": "left", "approx_dist": 115, "note": "フェアウェイ左バンカー"}, {"position": "right", "approx_dist": 115, "note": "フェアウェイ右バンカー"}],
                 "green": {"approach_from": "正面手前", "note": "打ち上げ8y。グリーン右サイドにバンカー。手前から攻める"},
                 "memo": "距離の短いストレートなパー5。グリーン左手前30ヤード付近のフェアウェイバンカーを避ける事。2段グリーンのためピン位置に注意。"},
            2:  {"par": 4, "yard": 276, "elevation": 4.8,
                 "green_side_bunkers": [{"position": "left", "approx_dist": 123, "note": "グリーン左バンカー"}, {"position": "right", "approx_dist": 123, "note": "グリーン右バンカー"}],
                 "green": {"approach_from": "正面", "note": "グリーン周りバンカー多数。二段グリーン"},
                 "memo": "距離は短いがバンカーが効いているためセカンドを考えてティーショットすること。グリーンは砲台で奥行きが短いため、正確な距離感が求められる。"},
            3:  {"par": 3, "yard": 180, "elevation": 0,
                 "green_side_bunkers": [{"position": "left", "approx_dist": 0, "note": "グリーン左バンカー"}],
                 "green": {"approach_from": "正面", "note": "打ち降ろしのPar3。グリーン複雑な傾斜"},
                 "memo": "距離のある打ち降ろしのパー3。2段グリーンで右手前には深いグラスバンカーがあり、グリーンをオーバーすると難しいアプローチが残る。風への注意が必要。"},
            4:  {"par": 5, "yard": 438, "elevation": 16.5,
                 "green_side_bunkers": [{"position": "left", "approx_dist": 89, "note": "グリーン左サイド。左に池"}],
                 "green": {"approach_from": "正面手前", "note": "打ち上げ16.5y。急傾斜。絶対に奥に外さない"},
                 "memo": "右ドッグレッグのパー5。ティーショットは左サイドが狙い目。グリーン手前50ヤード付近には松があるため刻むか攻めるかの判断が必要。グリーンは左手前から右奥へ縦長の2段グリーン。"},
            5:  {"par": 4, "yard": 316, "elevation": 0,
                 "green_side_bunkers": [{"position": "left", "approx_dist": 93, "note": "グリーン左バンカー"}],
                 "green": {"approach_from": "正面", "note": "比較的フラット。二段グリーン気味"},
                 "memo": "ティーショットはフェアウェイ右バンカーを避け左サイド狙い。残り80ヤード付近からくぼんでいるため打ち過ぎに注意する事。グリーン手前バンカーにつかまると厄介。"},
            6:  {"par": 4, "yard": 425, "elevation": -11.0,
                 "green_side_bunkers": [{"position": "left", "approx_dist": 65, "note": "フェアウェイ左バンカー"}],
                 "green": {"approach_from": "正面", "note": "打ち下ろし11y。比較的フラット"},
                 "memo": "距離のあるストレートなパー4。アウトでは一番難易度の高いホール。グリーン左手前のバンカーに注意。"},
            7:  {"par": 3, "yard": 138, "elevation": 0,
                 "green_side_bunkers": [],
                 "green": {"approach_from": "正面", "note": "Par3。グリーン奥は急傾斜+11"},
                 "memo": "グリーンはバンカーに囲まれているため正確なショットが要求される。ダムからの吹き抜け風に注意が必要。縦長の2段グリーンで奥から手前に速い。"},
            8:  {"par": 4, "yard": 424, "elevation": -5.6,
                 "green_side_bunkers": [{"position": "left", "approx_dist": 104, "note": "グリーン左バンカー"}],
                 "green": {"approach_from": "右（花道）", "note": "打ち下ろし5.6y。左に川。グリーン複雑"},
                 "memo": "左ドッグレッグのパー4。ティーショットは右サイドからコースを広く使っていきたいが、ロングヒッターは右への突き抜けに注意。セカンドからは方向性に注意し無理せず安全に攻めたい。"},
            9:  {"par": 4, "yard": 388, "elevation": -6.3,
                 "green_side_bunkers": [{"position": "left", "approx_dist": 113, "note": "グリーン左バンカー"}, {"position": "right", "approx_dist": 113, "note": "グリーン右バンカー"}],
                 "green": {"approach_from": "正面", "note": "打ち下ろし6.3y。グリーン左右バンカー"},
                 "memo": "やや打ち下ろしのストレートなパー4。ティーショット・セカンドともに風への注意が必要。グリーンは手前から速い。"},
            10: {"par": 5, "yard": 457, "elevation": -5.9,
                 "green_side_bunkers": [{"position": "left", "approx_dist": 53, "note": "グリーン左バンカー"}],
                 "green": {"approach_from": "右（花道）", "note": "打ち下ろし5.9y。グリーン複雑な傾斜"},
                 "memo": "S字のパー5。方向性と距離のジャッジを正確に。グリーン手前30ヤード付近に松があるためセカンドの方向性に注意が必要。"},
            11: {"par": 4, "yard": 271, "elevation": 4.1,
                 "green_side_bunkers": [{"position": "left", "approx_dist": 103, "note": "グリーン左バンカー"}, {"position": "right", "approx_dist": 103, "note": "グリーン右バンカー"}],
                 "green": {"approach_from": "正面手前", "note": "打ち上げ4.1y。グリーン奥は急傾斜。手前から"},
                 "memo": "バンカーが多いためティーショットがキーポイントとなる。打ち上げのため距離感がつかみにくい。グリーンは2段で奥に外すと難しいアプローチが残る。"},
            12: {"par": 3, "yard": 134, "elevation": 0,
                 "green_side_bunkers": [],
                 "green": {"approach_from": "正面", "note": "Par3。グリーン奥は急傾斜+9"},
                 "memo": "グリーンは左手前から右奥に向かって長く大きい。ピン位置によっては1クラブ以上の違いあり。方向性と距離感が要求されるホール。"},
            13: {"par": 4, "yard": 376, "elevation": 0,
                 "green_side_bunkers": [{"position": "left", "approx_dist": 87, "note": "グリーン左バンカー"}, {"position": "right", "approx_dist": 87, "note": "グリーン右バンカー"}],
                 "green": {"approach_from": "正面", "note": "グリーン左右バンカー。手前から攻める"},
                 "memo": "ティーショットは左方向が狙い目。右はOB、左はレッドペナルティーエリア。グリーン両サイドは奥行きがないため正確な距離感が必要。"},
            14: {"par": 4, "yard": 423, "elevation": 10.6,
                 "green_side_bunkers": [{"position": "left", "approx_dist": 114, "note": "グリーン左バンカー"}],
                 "green": {"approach_from": "正面手前", "note": "打ち上げ10.6y。グリーン奥は急傾斜+11"},
                 "memo": "距離のあるパー4。ティーショットは右カート道（カートみち）方向が狙い目。左の谷へ落ちた場合は無理をせずフェアウェイに戻した方がよい。フェアウェイ・グリーンともに左に傾斜している。"},
            15: {"par": 3, "yard": 179, "elevation": -4.4,
                 "green_side_bunkers": [{"position": "left", "approx_dist": 83, "note": "グリーン左バンカー"}],
                 "green": {"approach_from": "右（花道）", "note": "打ち下ろし4.4y。グリーン左バンカー注意"},
                 "memo": "名物ホールのパー3。打ち下ろしのため距離感に注意。手前バンカーにつかまった場合は、後方または横に出す勇気も必要。"},
            16: {"par": 4, "yard": 320, "elevation": -1.8,
                 "green_side_bunkers": [],
                 "green": {"approach_from": "正面", "note": "グリーン手前に小さな池。手前から攻める"},
                 "memo": "戦略性のあるやや右ドッグレッグのパー4。左右にフェアウェイバンカーがあるためティーショットがキーポイントとなる。グリーン左手前には池。セカンドは見た目以上に上っているため少し大き目のクラブで。"},
            17: {"par": 5, "yard": 478, "elevation": -2.6,
                 "green_side_bunkers": [{"position": "left", "approx_dist": 68, "note": "グリーン左バンカー"}, {"position": "right", "approx_dist": 68, "note": "グリーン右バンカー"}],
                 "green": {"approach_from": "正面", "note": "打ち下ろし2.6y。グリーン左右バンカー注意"},
                 "memo": "ゆるやかに打ち上げている右ドッグレッグのパー5。全体的に左から攻めるとよい。2段グリーンのためピン位置に注意。"},
            18: {"par": 4, "yard": 408, "elevation": -6.3,
                 "green_side_bunkers": [{"position": "left", "approx_dist": 113, "note": "グリーン左バンカー"}],
                 "green": {"approach_from": "右（花道）", "note": "打ち下ろし6.3y。グリーン左バンカー注意"},
                 "memo": "距離のある打ち下ろしのパー4。ティーショットはやや右サイドが狙い目だが、右に行き過ぎるとOBになりやすく残り距離が長くなるため注意が必要。3段グリーンでピン位置により難易度が変わる。"},
        }
    },
    "宝塚ゴルフ倶楽部 旧コース（レギュラー）": {
        "name": "宝塚ゴルフ倶楽部", "tee": "REG",
        "holes": {
            1:  {"par": 4, "yard": 370, "elevation": -13.9,
                 "green_side_bunkers": [{"position": "left", "approx_dist": 142, "note": "グリーン手前左に2つ"}],
                 "green": {"approach_from": "右（花道）", "note": "右サイドにバンカー。手前右から攻めるのが安全"},
                 "memo": "右に行くと木がスタイミーになるためティーショットは左サイドが狙い目。グリーンは小さく奥行がないため手前から攻めていきたい。"},
            2:  {"par": 3, "yard": 170, "elevation": -4.3,
                 "green_side_bunkers": [{"position": "left", "approx_dist": 0, "note": "グリーン左サイドにバンカー"}],
                 "green": {"approach_from": "右（花道）", "note": "グリーン左にバンカー。右から攻める"},
                 "memo": "距離は短いが縦長のグリーンでバンカーに囲まれているため、方向性を重視したい。グリーンは手前から速い。"},
            3:  {"par": 4, "yard": 391, "elevation": -12.2,
                 "green_side_bunkers": [{"position": "left", "approx_dist": 149, "note": "グリーン手前左バンカー"}, {"position": "right", "approx_dist": 130, "note": "グリーン右サイド"}],
                 "green": {"approach_from": "左（花道）", "note": "奥からは速い。手前から攻める"},
                 "memo": "距離のあるパー4。グリーンが左奥から右手前にかけて速いため、ティーショット・セカンドともに右サイドから攻めていきたい。"},
            4:  {"par": 5, "yard": 535, "elevation": -6.5,
                 "green_side_bunkers": [{"position": "left", "approx_dist": 119, "note": "フェアウェイ左バンカー"}, {"position": "right", "approx_dist": 72, "note": "グリーン手前右バンカー"}],
                 "green": {"approach_from": "左（花道）", "note": "グリーン手前右にバンカー。左から攻める"},
                 "memo": "グリーンまで障害物はないためティーショット・セカンドともに思い切りせめたいが、全体的に緩やかな左足下がりとなっているため球筋に注意したい。グリーンは2段だが手前から速い。"},
            5:  {"par": 5, "yard": 550, "elevation": -9.2,
                 "green_side_bunkers": [{"position": "left", "approx_dist": 56, "note": "グリーン左バンカー"}, {"position": "right", "approx_dist": 56, "note": "グリーン右バンカー"}],
                 "green": {"approach_from": "正面（花道広め）", "note": "グリーン奥が高い。手前から攻める"},
                 "memo": "左ドッグレッグのパー5。ティーショットは右が狙い目。グリーンは左から右への傾斜が強いため上りのパットを残したい。"},
            6:  {"par": 3, "yard": 150, "elevation": 0,
                 "green_side_bunkers": [{"position": "left", "approx_dist": 0, "note": "グリーン左バンカー"}],
                 "green": {"approach_from": "正面", "note": "奥は急傾斜。手前から攻めること"},
                 "memo": "グリーン手前のバンカーと左奥のOBに注意。グリーンは奥から手前に速い。"},
            7:  {"par": 4, "yard": 368, "elevation": 0,
                 "green_side_bunkers": [{"position": "left", "approx_dist": 153, "note": "フェアウェイ左バンカー"}],
                 "green": {"approach_from": "正面右（花道）", "note": "グリーン奥から手前への急傾斜"},
                 "memo": "使用ティーで狙い目が変わる。残り100y付近にある右の谷に注意。セカンドは上りがきついため大きめのクラブで。グリーンは2段で縦長。"},
            8:  {"par": 3, "yard": 175, "elevation": 0,
                 "green_side_bunkers": [{"position": "left", "approx_dist": 0, "note": "グリーン左バンカー"}],
                 "green": {"approach_from": "正面", "note": "グリーン周りバンカー注意"},
                 "memo": "奥行きのない横長グリーン。手前は急な下り斜面のためショートは避けたい。しっかりとしたキャリーボールが必要。"},
            9:  {"par": 4, "yard": 340, "elevation": 0,
                 "green_side_bunkers": [{"position": "left", "approx_dist": 121, "note": "フェアウェイ左バンカー"}, {"position": "right", "approx_dist": 134, "note": "フェアウェイ右バンカー"}],
                 "green": {"approach_from": "右（花道）", "note": "グリーン手前左右にバンカー。花道は右"},
                 "memo": "広々としたパー4。ティーショットはフェアウェイ右バンカーを避け、気持ちよく振っていきたい。グリーンは砲台のためセカンドは少し上りをみる。"},
            10: {"par": 3, "yard": 160, "elevation": 0,
                 "green_side_bunkers": [],
                 "green": {"approach_from": "右（花道）", "note": "比較的フラット。右から攻める"},
                 "memo": "グリーン奥は谷になっているため、オーバーに注意。グリーンは小さく奥からの傾斜がきつい。"},
            11: {"par": 4, "yard": 300, "elevation": 0,
                 "green_side_bunkers": [],
                 "green": {"approach_from": "右（花道）", "note": "グリーン右から花道経由が安全"},
                 "memo": "やや打ち上げの短いパー4。ティーショットは左サイドが狙い目。グリーン手前のバンカーはアゴが高く打ち上げのため高い球が要求される。グリーンは左奥より右手前にかけて速い。"},
            12: {"par": 3, "yard": 155, "elevation": 0,
                 "green_side_bunkers": [],
                 "green": {"approach_from": "正面", "note": "川沿いホール"},
                 "memo": "両サイドをクリークに挟まれた打ち下ろしのパー3。風の影響を受けやすく、距離感・方向性ともに気を使う難ホール。"},
            13: {"par": 4, "yard": 354, "elevation": 0,
                 "green_side_bunkers": [{"position": "left", "approx_dist": 97, "note": "グリーン手前左バンカー"}],
                 "green": {"approach_from": "正面手前", "note": "急傾斜。絶対に奥に外さない"},
                 "memo": "左の林に行くとグリーンが狙えないためティーショットは慎重に。グリーンは奥から手前にかけて速い。"},
            14: {"par": 5, "yard": 505, "elevation": 14.1,
                 "green_side_bunkers": [{"position": "right", "approx_dist": 122, "note": "グリーン手前右バンカー"}],
                 "green": {"approach_from": "左（花道）", "note": "打ち上げ14.1y。グリーン左が高い"},
                 "memo": "広々とした距離のあるパー5。ピン位置により難易度が変わるためセカンドが鍵となる。グリーン手前50ヤード付近には松が効いており高い球が必要。グリーンは奥から手前にかけて速い。"},
            15: {"par": 4, "yard": 392, "elevation": 0,
                 "green_side_bunkers": [{"position": "left", "approx_dist": 128, "note": "グリーン手前左バンカー"}],
                 "green": {"approach_from": "正面（花道広め）", "note": "グリーン手前左バンカー注意"},
                 "memo": "打ち上げで距離のあるパー4。グリーン手前のバンカーを避けセカンドは積極的に攻めるか刻むかの判断が必要。縦長の2段グリーンのため方向性と距離感も重視したい。"},
            16: {"par": 3, "yard": 185, "elevation": 0,
                 "green_side_bunkers": [],
                 "green": {"approach_from": "正面", "note": "非常に短いPar3。複雑なグリーン"},
                 "memo": "グリーンは奥方向に高くなっているように見えるが、ボールの転がりは見た目以上に速いため手前から攻めるのがベスト。"},
            17: {"par": 5, "yard": 490, "elevation": -15.0,
                 "green_side_bunkers": [{"position": "right", "approx_dist": 110, "note": "川が右サイドに沿っている"}],
                 "green": {"approach_from": "左（花道）", "note": "右に川。グリーン左から攻める"},
                 "memo": "ティーショットはやや左サイドが狙い目。2オンも狙えるがグリーン左右のOBに注意。グリーンは左から右への傾斜が強く、手前からも速い。"},
            18: {"par": 4, "yard": 417, "elevation": 4.0,
                 "green_side_bunkers": [{"position": "left", "approx_dist": 93, "note": "グリーン左バンカー"}],
                 "green": {"approach_from": "右（花道）", "note": "二段グリーン。左にバンカー。右から攻める"},
                 "memo": "ティーショットは正面の木の右サイドが狙い目。左に行くと木が邪魔になりグリーンが狙いにくい。グリーンは手前から奥に向かって速い。"},
        }
    },
    "宝塚ゴルフ倶楽部 旧コース（フロント）": {
        "name": "宝塚ゴルフ倶楽部", "tee": "FRO",
        "holes": {
            1:  {"par": 4, "yard": 359, "elevation": -13.9,
                 "green_side_bunkers": [{"position": "left", "approx_dist": 142, "note": "グリーン手前左に2つ"}],
                 "green": {"approach_from": "右（花道）", "note": "右サイドにバンカー。手前右から攻めるのが安全"},
                 "memo": "右に行くと木がスタイミーになるためティーショットは左サイドが狙い目。グリーンは小さく奥行がないため手前から攻めていきたい。"},
            2:  {"par": 3, "yard": 136, "elevation": -4.3,
                 "green_side_bunkers": [{"position": "left", "approx_dist": 0, "note": "グリーン左サイドにバンカー"}],
                 "green": {"approach_from": "右（花道）", "note": "グリーン左にバンカー。右から攻める"},
                 "memo": "距離は短いが縦長のグリーンでバンカーに囲まれているため、方向性を重視したい。グリーンは手前から速い。"},
            3:  {"par": 4, "yard": 356, "elevation": -12.2,
                 "green_side_bunkers": [{"position": "left", "approx_dist": 149, "note": "グリーン手前左バンカー"}, {"position": "right", "approx_dist": 130, "note": "グリーン右サイド"}],
                 "green": {"approach_from": "左（花道）", "note": "奥からは速い。手前から攻める"},
                 "memo": "距離のあるパー4。グリーンが左奥から右手前にかけて速いため、ティーショット・セカンドともに右サイドから攻めていきたい。"},
            4:  {"par": 5, "yard": 528, "elevation": -6.5,
                 "green_side_bunkers": [{"position": "left", "approx_dist": 119, "note": "フェアウェイ左バンカー"}, {"position": "right", "approx_dist": 72, "note": "グリーン手前右バンカー"}],
                 "green": {"approach_from": "左（花道）", "note": "グリーン手前右にバンカー。左から攻める"},
                 "memo": "グリーンまで障害物はないためティーショット・セカンドともに思い切りせめたいが、全体的に緩やかな左足下がりとなっているため球筋に注意したい。グリーンは2段だが手前から速い。"},
            5:  {"par": 5, "yard": 512, "elevation": -9.2,
                 "green_side_bunkers": [{"position": "left", "approx_dist": 56, "note": "グリーン左バンカー"}, {"position": "right", "approx_dist": 56, "note": "グリーン右バンカー"}],
                 "green": {"approach_from": "正面（花道広め）", "note": "グリーン奥が高い。手前から攻める"},
                 "memo": "左ドッグレッグのパー5。ティーショットは右が狙い目。グリーンは左から右への傾斜が強いため上りのパットを残したい。"},
            6:  {"par": 3, "yard": 128, "elevation": 0,
                 "green_side_bunkers": [{"position": "left", "approx_dist": 0, "note": "グリーン左バンカー"}],
                 "green": {"approach_from": "正面", "note": "奥は急傾斜。手前から攻めること"},
                 "memo": "グリーン手前のバンカーと左奥のOBに注意。グリーンは奥から手前に速い。"},
            7:  {"par": 4, "yard": 344, "elevation": 0,
                 "green_side_bunkers": [{"position": "left", "approx_dist": 153, "note": "フェアウェイ左バンカー"}],
                 "green": {"approach_from": "正面右（花道）", "note": "グリーン奥から手前への急傾斜"},
                 "memo": "使用ティーで狙い目が変わる。残り100y付近にある右の谷に注意。セカンドは上りがきついため大きめのクラブで。グリーンは2段で縦長。"},
            8:  {"par": 3, "yard": 163, "elevation": 0,
                 "green_side_bunkers": [{"position": "left", "approx_dist": 0, "note": "グリーン左バンカー"}],
                 "green": {"approach_from": "正面", "note": "グリーン周りバンカー注意"},
                 "memo": "奥行きのない横長グリーン。手前は急な下り斜面のためショートは避けたい。しっかりとしたキャリーボールが必要。"},
            9:  {"par": 4, "yard": 330, "elevation": 0,
                 "green_side_bunkers": [{"position": "left", "approx_dist": 121, "note": "フェアウェイ左バンカー"}, {"position": "right", "approx_dist": 134, "note": "フェアウェイ右バンカー"}],
                 "green": {"approach_from": "右（花道）", "note": "グリーン手前左右にバンカー。花道は右"},
                 "memo": "広々としたパー4。ティーショットはフェアウェイ右バンカーを避け、気持ちよく振っていきたい。グリーンは砲台のためセカンドは少し上りをみる。"},
            10: {"par": 3, "yard": 150, "elevation": 0,
                 "green_side_bunkers": [],
                 "green": {"approach_from": "右（花道）", "note": "比較的フラット。右から攻める"},
                 "memo": "グリーン奥は谷になっているため、オーバーに注意。グリーンは小さく奥からの傾斜がきつい。"},
            11: {"par": 4, "yard": 292, "elevation": 0,
                 "green_side_bunkers": [],
                 "green": {"approach_from": "右（花道）", "note": "グリーン右から花道経由が安全"},
                 "memo": "やや打ち上げの短いパー4。ティーショットは左サイドが狙い目。グリーン手前のバンカーはアゴが高く打ち上げのため高い球が要求される。グリーンは左奥より右手前にかけて速い。"},
            12: {"par": 3, "yard": 144, "elevation": 0,
                 "green_side_bunkers": [],
                 "green": {"approach_from": "正面", "note": "川沿いホール"},
                 "memo": "両サイドをクリークに挟まれた打ち下ろしのパー3。風の影響を受けやすく、距離感・方向性ともに気を使う難ホール。"},
            13: {"par": 4, "yard": 340, "elevation": 0,
                 "green_side_bunkers": [{"position": "left", "approx_dist": 97, "note": "グリーン手前左バンカー"}],
                 "green": {"approach_from": "正面手前", "note": "急傾斜。絶対に奥に外さない"},
                 "memo": "左の林に行くとグリーンが狙えないためティーショットは慎重に。グリーンは奥から手前にかけて速い。"},
            14: {"par": 5, "yard": 495, "elevation": 14.1,
                 "green_side_bunkers": [{"position": "right", "approx_dist": 122, "note": "グリーン手前右バンカー"}],
                 "green": {"approach_from": "左（花道）", "note": "打ち上げ14.1y。グリーン左が高い"},
                 "memo": "広々とした距離のあるパー5。ピン位置により難易度が変わるためセカンドが鍵となる。グリーン手前50ヤード付近には松が効いており高い球が必要。グリーンは奥から手前にかけて速い。"},
            15: {"par": 4, "yard": 380, "elevation": 0,
                 "green_side_bunkers": [{"position": "left", "approx_dist": 128, "note": "グリーン手前左バンカー"}],
                 "green": {"approach_from": "正面（花道広め）", "note": "グリーン手前左バンカー注意"},
                 "memo": "打ち上げで距離のあるパー4。グリーン手前のバンカーを避けセカンドは積極的に攻めるか刻むかの判断が必要。縦長の2段グリーンのため方向性と距離感も重視したい。"},
            16: {"par": 3, "yard": 175, "elevation": 0,
                 "green_side_bunkers": [],
                 "green": {"approach_from": "正面", "note": "非常に短いPar3。複雑なグリーン"},
                 "memo": "グリーンは奥方向に高くなっているように見えるが、ボールの転がりは見た目以上に速いため手前から攻めるのがベスト。"},
            17: {"par": 5, "yard": 475, "elevation": -15.0,
                 "green_side_bunkers": [{"position": "right", "approx_dist": 110, "note": "川が右サイドに沿っている"}],
                 "green": {"approach_from": "左（花道）", "note": "右に川。グリーン左から攻める"},
                 "memo": "ティーショットはやや左サイドが狙い目。2オンも狙えるがグリーン左右のOBに注意。グリーンは左から右への傾斜が強く、手前からも速い。"},
            18: {"par": 4, "yard": 398, "elevation": 4.0,
                 "green_side_bunkers": [{"position": "left", "approx_dist": 93, "note": "グリーン左バンカー"}],
                 "green": {"approach_from": "右（花道）", "note": "二段グリーン。左にバンカー。右から攻める"},
                 "memo": "ティーショットは正面の木の右サイドが狙い目。左に行くと木が邪魔になりグリーンが狙いにくい。グリーンは手前から奥に向かって速い。"},
        }
    },
    "宝塚ゴルフ倶楽部 旧コース（ホワイト）": {
        "name": "宝塚ゴルフ倶楽部", "tee": "WHT",
        "holes": {
            1:  {"par": 4, "yard": 233, "elevation": -13.9,
                 "green_side_bunkers": [{"position": "left", "approx_dist": 142, "note": "グリーン手前左に2つ"}],
                 "green": {"approach_from": "右（花道）", "note": "右サイドにバンカー。手前右から攻めるのが安全"},
                 "memo": "打ち下ろし13.9y。グリーン手前左バンカー。花道は右から。"},
            2:  {"par": 4, "yard": 233, "elevation": -4.3,
                 "green_side_bunkers": [{"position": "left", "approx_dist": 0, "note": "グリーン左サイドにバンカー"}],
                 "green": {"approach_from": "右（花道）", "note": "グリーン左にバンカー。右から攻める"},
                 "memo": "打ち下ろし4.3y。左サイドにバンカー。花道は右。"},
            3:  {"par": 5, "yard": 186, "elevation": -12.2,
                 "green_side_bunkers": [{"position": "left", "approx_dist": 149, "note": "グリーン手前左バンカー"}, {"position": "right", "approx_dist": 130, "note": "グリーン右サイド"}],
                 "green": {"approach_from": "左（花道）", "note": "奥からは速い。手前から攻める"},
                 "memo": "打ち下ろし12.2y。左右にバンカー。手前から攻める。"},
            4:  {"par": 4, "yard": 236, "elevation": -6.5,
                 "green_side_bunkers": [{"position": "left", "approx_dist": 119, "note": "フェアウェイ左バンカー"}, {"position": "right", "approx_dist": 72, "note": "グリーン手前右バンカー"}],
                 "green": {"approach_from": "左（花道）", "note": "グリーン手前右にバンカー。左から攻める"},
                 "memo": "打ち下ろし6.5y。グリーン手前右バンカーに注意。"},
            5:  {"par": 5, "yard": 188, "elevation": -9.2,
                 "green_side_bunkers": [{"position": "left", "approx_dist": 56, "note": "グリーン左バンカー"}, {"position": "right", "approx_dist": 56, "note": "グリーン右バンカー"}],
                 "green": {"approach_from": "正面（花道広め）", "note": "グリーン奥が高い。手前から攻める"},
                 "memo": "打ち下ろし9.2y。グリーン左右バンカー。手前から攻める。"},
            6:  {"par": 3, "yard": 133, "elevation": 0,
                 "green_side_bunkers": [{"position": "left", "approx_dist": 0, "note": "グリーン左バンカー"}],
                 "green": {"approach_from": "正面", "note": "奥は急傾斜。手前から攻めること"},
                 "memo": "Par3。グリーン奥は急傾斜。絶対に奥には外さない。"},
            7:  {"par": 4, "yard": 224, "elevation": 0,
                 "green_side_bunkers": [{"position": "left", "approx_dist": 153, "note": "フェアウェイ左バンカー"}],
                 "green": {"approach_from": "正面右（花道）", "note": "グリーン奥から手前への急傾斜"},
                 "memo": "フェアウェイ左バンカー注意。グリーンは奥から手前に傾斜。"},
            8:  {"par": 3, "yard": 174, "elevation": 0,
                 "green_side_bunkers": [{"position": "left", "approx_dist": 0, "note": "グリーン左バンカー"}],
                 "green": {"approach_from": "正面", "note": "グリーン周りバンカー注意"},
                 "memo": "Par3。池あり。グリーン左バンカー注意。"},
            9:  {"par": 4, "yard": 234, "elevation": 0,
                 "green_side_bunkers": [{"position": "left", "approx_dist": 121, "note": "フェアウェイ左バンカー"}, {"position": "right", "approx_dist": 134, "note": "フェアウェイ右バンカー"}],
                 "green": {"approach_from": "右（花道）", "note": "グリーン手前左右にバンカー。花道は右"},
                 "memo": "フェアウェイ中央バンカー左右に注意。花道は右から。"},
            10: {"par": 4, "yard": 235, "elevation": 0,
                 "green_side_bunkers": [],
                 "green": {"approach_from": "右（花道）", "note": "比較的フラット。右から攻める"},
                 "memo": "フェアウェイ左にバンカー。グリーンは比較的フラット。"},
            11: {"par": 4, "yard": 235, "elevation": 0,
                 "green_side_bunkers": [],
                 "green": {"approach_from": "右（花道）", "note": "グリーン右から花道経由が安全"},
                 "memo": "グリーン手前右から攻める。"},
            12: {"par": 4, "yard": 0, "elevation": 0,
                 "green_side_bunkers": [],
                 "green": {"approach_from": "正面", "note": "川沿いホール。距離データ不明"},
                 "memo": "川沿いホール。距離は要設定。"},
            13: {"par": 5, "yard": 207, "elevation": 0,
                 "green_side_bunkers": [{"position": "left", "approx_dist": 97, "note": "グリーン手前左バンカー"}],
                 "green": {"approach_from": "正面手前", "note": "急傾斜。絶対に奥に外さない"},
                 "memo": "打ち上げホール。グリーン奥は急傾斜+12。手前から必ず攻める。"},
            14: {"par": 4, "yard": 230, "elevation": 14.1,
                 "green_side_bunkers": [{"position": "right", "approx_dist": 122, "note": "グリーン手前右バンカー"}],
                 "green": {"approach_from": "左（花道）", "note": "打ち上げ14.1y。グリーン左が高い"},
                 "memo": "打ち上げ14.1y。グリーン手前右バンカー注意。花道は左から。"},
            15: {"par": 5, "yard": 228, "elevation": 0,
                 "green_side_bunkers": [{"position": "left", "approx_dist": 128, "note": "グリーン手前左バンカー"}],
                 "green": {"approach_from": "正面（花道広め）", "note": "グリーン手前左バンカー注意"},
                 "memo": "グリーン手前左バンカー注意。花道は正面から。"},
            16: {"par": 3, "yard": 20, "elevation": 0,
                 "green_side_bunkers": [],
                 "green": {"approach_from": "正面", "note": "非常に短いPar3。複雑なグリーン"},
                 "memo": "超短距離Par3（距離要確認）。グリーンのアンジュレーションに注意。"},
            17: {"par": 4, "yard": 228, "elevation": -15.0,
                 "green_side_bunkers": [{"position": "right", "approx_dist": 110, "note": "川が右サイドに沿っている"}],
                 "green": {"approach_from": "左（花道）", "note": "右に川。グリーン左から攻める"},
                 "memo": "打ち下ろし15.0y。右サイドに川。グリーン左から攻める。"},
            18: {"par": 4, "yard": 221, "elevation": 4.0,
                 "green_side_bunkers": [{"position": "left", "approx_dist": 93, "note": "グリーン左バンカー"}],
                 "green": {"approach_from": "右（花道）", "note": "二段グリーン。左にバンカー。右から攻める"},
                 "memo": "打ち上げ4.0y。二段グリーン。左バンカー注意。花道は右から。"},
        }
    },
    "宝塚ゴルフ倶楽部 新コース（ホワイト）": {
        "name": "宝塚ゴルフ倶楽部", "tee": "WHT",
        "holes": {
            1:  {"par": 5, "yard": 225, "elevation": 8.0,
                 "green_side_bunkers": [{"position": "left", "approx_dist": 115, "note": "フェアウェイ左バンカー"}, {"position": "right", "approx_dist": 115, "note": "フェアウェイ右バンカー"}],
                 "green": {"approach_from": "正面手前", "note": "打ち上げ8y。グリーン右サイドにバンカー。手前から攻める"},
                 "memo": "打ち上げ8.0y。フェアウェイ左右バンカー注意。グリーン奥は急傾斜。"},
            2:  {"par": 4, "yard": 223, "elevation": 4.8,
                 "green_side_bunkers": [{"position": "left", "approx_dist": 123, "note": "グリーン左バンカー"}, {"position": "right", "approx_dist": 123, "note": "グリーン右バンカー"}],
                 "green": {"approach_from": "正面", "note": "グリーン周りバンカー多数。二段グリーン"},
                 "memo": "打ち上げ4.8y。グリーン左右バンカー。二段グリーンに注意。"},
            3:  {"par": 3, "yard": 27, "elevation": 0,
                 "green_side_bunkers": [{"position": "left", "approx_dist": 0, "note": "グリーン左バンカー"}],
                 "green": {"approach_from": "正面", "note": "短いPar3。グリーン複雑な傾斜"},
                 "memo": "短距離Par3（距離要確認）。グリーン左バンカー注意。"},
            4:  {"par": 4, "yard": 199, "elevation": 16.5,
                 "green_side_bunkers": [{"position": "left", "approx_dist": 89, "note": "グリーン左サイド。左に池"}],
                 "green": {"approach_from": "正面手前", "note": "打ち上げ16.5y。急傾斜。絶対に奥に外さない"},
                 "memo": "大きな打ち上げ16.5y。左サイドに池。グリーン奥は急傾斜。手前必須。"},
            5:  {"par": 4, "yard": 199, "elevation": 0,
                 "green_side_bunkers": [{"position": "left", "approx_dist": 93, "note": "グリーン左バンカー"}],
                 "green": {"approach_from": "正面", "note": "比較的フラット。二段グリーン気味"},
                 "memo": "グリーン左バンカー注意。二段グリーン。"},
            6:  {"par": 5, "yard": 215, "elevation": -11.0,
                 "green_side_bunkers": [{"position": "left", "approx_dist": 65, "note": "フェアウェイ左バンカー"}],
                 "green": {"approach_from": "正面", "note": "打ち下ろし11y。比較的フラット"},
                 "memo": "打ち下ろし11.0y。フェアウェイ左バンカー注意。"},
            7:  {"par": 3, "yard": 0, "elevation": 0,
                 "green_side_bunkers": [],
                 "green": {"approach_from": "正面", "note": "Par3。グリーン奥は急傾斜+11"},
                 "memo": "Par3（距離要確認）。グリーン奥は非常に急傾斜。"},
            8:  {"par": 5, "yard": 226, "elevation": -5.6,
                 "green_side_bunkers": [{"position": "left", "approx_dist": 104, "note": "グリーン左バンカー"}],
                 "green": {"approach_from": "右（花道）", "note": "打ち下ろし5.6y。左に川。グリーン複雑"},
                 "memo": "打ち下ろし5.6y。左サイドに川。グリーン左バンカー注意。"},
            9:  {"par": 4, "yard": 228, "elevation": -6.3,
                 "green_side_bunkers": [{"position": "left", "approx_dist": 113, "note": "グリーン左バンカー"}, {"position": "right", "approx_dist": 113, "note": "グリーン右バンカー"}],
                 "green": {"approach_from": "正面", "note": "打ち下ろし6.3y。グリーン左右バンカー"},
                 "memo": "打ち下ろし6.3y。グリーン左右バンカー注意。"},
            10: {"par": 4, "yard": 175, "elevation": -5.9,
                 "green_side_bunkers": [{"position": "left", "approx_dist": 53, "note": "グリーン左バンカー"}],
                 "green": {"approach_from": "右（花道）", "note": "打ち下ろし5.9y。グリーン複雑な傾斜"},
                 "memo": "打ち下ろし5.9y。グリーン左バンカー注意。複雑なアンジュレーション。"},
            11: {"par": 4, "yard": 218, "elevation": 4.1,
                 "green_side_bunkers": [{"position": "left", "approx_dist": 103, "note": "グリーン左バンカー"}, {"position": "right", "approx_dist": 103, "note": "グリーン右バンカー"}],
                 "green": {"approach_from": "正面手前", "note": "打ち上げ4.1y。グリーン奥は急傾斜。手前から"},
                 "memo": "打ち上げ4.1y。グリーン左右バンカー。奥は急傾斜。必ず手前から攻める。"},
            12: {"par": 3, "yard": 0, "elevation": 0,
                 "green_side_bunkers": [],
                 "green": {"approach_from": "正面", "note": "Par3。グリーン奥は急傾斜+9"},
                 "memo": "Par3（距離要確認）。グリーン奥は急傾斜。"},
            13: {"par": 4, "yard": 197, "elevation": 0,
                 "green_side_bunkers": [{"position": "left", "approx_dist": 87, "note": "グリーン左バンカー"}, {"position": "right", "approx_dist": 87, "note": "グリーン右バンカー"}],
                 "green": {"approach_from": "正面", "note": "グリーン左右バンカー。手前から攻める"},
                 "memo": "グリーン左右バンカー注意。左に池あり。手前から攻める。"},
            14: {"par": 5, "yard": 226, "elevation": 10.6,
                 "green_side_bunkers": [{"position": "left", "approx_dist": 114, "note": "グリーン左バンカー"}],
                 "green": {"approach_from": "正面手前", "note": "打ち上げ10.6y。グリーン奥は急傾斜+11"},
                 "memo": "打ち上げ10.6y。グリーン奥は急傾斜。絶対に手前から攻める。"},
            15: {"par": 4, "yard": 217, "elevation": -4.4,
                 "green_side_bunkers": [{"position": "left", "approx_dist": 83, "note": "グリーン左バンカー"}],
                 "green": {"approach_from": "右（花道）", "note": "打ち下ろし4.4y。グリーン左バンカー注意"},
                 "memo": "打ち下ろし4.4y。グリーン左バンカー注意。花道は右から。"},
            16: {"par": 4, "yard": 211, "elevation": -1.8,
                 "green_side_bunkers": [],
                 "green": {"approach_from": "正面", "note": "グリーン手前に小さな池。手前から攻める"},
                 "memo": "グリーン手前に池注意。奥から手前への傾斜。"},
            17: {"par": 5, "yard": 189, "elevation": -2.6,
                 "green_side_bunkers": [{"position": "left", "approx_dist": 68, "note": "グリーン左バンカー"}, {"position": "right", "approx_dist": 68, "note": "グリーン右バンカー"}],
                 "green": {"approach_from": "正面", "note": "打ち下ろし2.6y。グリーン左右バンカー注意"},
                 "memo": "打ち下ろし2.6y。グリーン左右バンカー注意。複雑なアンジュレーション。"},
            18: {"par": 4, "yard": 228, "elevation": -6.3,
                 "green_side_bunkers": [{"position": "left", "approx_dist": 113, "note": "グリーン左バンカー"}],
                 "green": {"approach_from": "右（花道）", "note": "打ち下ろし6.3y。グリーン左バンカー注意"},
                 "memo": "打ち下ろし6.3y。グリーン左バンカー注意。花道は右から。"},
        }
    },
    "琵琶湖レークサイドGC 中→南（レギュラー）": {
        "name": "琵琶湖レークサイドGC", "tee": "REG",
        "holes": {
            1:  {"par": 4, "yard": 334, "memo": "思いっきりティーショットを打っていけるホール。狙いはフェアウェイ左バンカーの右側狙い。グリーンは手前から攻めるのがベスト。"},
            2:  {"par": 3, "yard": 129, "memo": "グリーン周りはOBが出やすい。ピンポジションにかかわらず、グリーンセンターを狙う。"},
            3:  {"par": 4, "yard": 341, "memo": "左ドッグレッグのミドルホール。ティーショットは正面クロスバンカー狙い。左サイドの池に注意。"},
            4:  {"par": 4, "yard": 303, "memo": "軽く右にドッグレッグしたホール。ティーショットはフェアウェイやや右狙い。安全に左サイドに刻んでいくのも一つの手段。"},
            5:  {"par": 5, "yard": 421, "memo": "距離の短いロングホール。ティーショットはフェアウェイセンター狙い。グリーン手前の池に注意。"},
            6:  {"par": 3, "yard": 114, "memo": "ピンポジションにかかわらず、グリーンセンター狙い。左ガードバンカーに注意。"},
            7:  {"par": 4, "yard": 293, "memo": "ティーショットはフェアウェイセンターのバンカーに注意。二打目は確実にグリーンセンターへ。グリーンを外すと周りからのアプローチは寄せがむずかしい。"},
            8:  {"par": 3, "yard": 167, "memo": "池が気になるショートホール。グリーン右側は比較的安全。"},
            9:  {"par": 4, "yard": 288, "memo": "ティーショットはフェアウェイ正面の木を目標に。二打目は確実にグリーンセンターへ。バーディーの確率が高いホール。"},
            10: {"par": 4, "yard": 312, "memo": "軽く左にドッグレッグしたホール。ティーショットはフェアウェイやや右サイド狙い。ガードバンカーのアゴ高く。二打目は高い弾道で。"},
            11: {"par": 3, "yard": 121, "memo": "グリーン手前の池に注意。グリーン奥からのアプローチもむずかしい。確実にグリーンセンターへ。"},
            12: {"par": 5, "yard": 482, "memo": "ティーショットは正面の木狙い。二打目は左サイドの池に注意。グリーン周りからのアプローチは寄せがむずかしい。"},
            13: {"par": 4, "yard": 329, "memo": "右ドッグレッグのミドルホール。ティーショットはフェアウェイセンター狙い。右を狙いすぎると、二打目が木超えのむずかしいショットに。"},
            14: {"par": 3, "yard": 145, "memo": "グリーン周りのガードバンカーに注意。確実にグリーンセンターへ。グリーン奥はOB。"},
            15: {"par": 4, "yard": 324, "memo": "ティーショットはフェアウェイセンター狙い。グリーン左サイドは比較的安全。"},
            16: {"par": 4, "yard": 304, "memo": "ティーショットはフェアウェイセンター狙い。グリーン右手前のバンカーに注意。二打目は確実にグリーンセンターへ。"},
            17: {"par": 3, "yard": 127, "memo": "グリーン手前のバンカーに注意。高い弾道で、確実にグリーンセンターへ。"},
            18: {"par": 4, "yard": 328, "memo": "軽く左ドッグレッグしたホール。ティーショットはフェアウェイ右サイド狙い。グリーン左サイドはOBが近いので注意。"},
        }
    },
    "琵琶湖レークサイドGC 中→南（フロント）": {
        "name": "琵琶湖レークサイドGC", "tee": "FRO",
        "holes": {
            1:  {"par": 4, "yard": 327, "memo": "思いっきりティーショットを打っていけるホール。狙いはフェアウェイ左バンカーの右側狙い。グリーンは手前から攻めるのがベスト。"},
            2:  {"par": 3, "yard": 123, "memo": "グリーン周りはOBが出やすい。ピンポジションにかかわらず、グリーンセンターを狙う。"},
            3:  {"par": 4, "yard": 330, "memo": "左ドッグレッグのミドルホール。ティーショットは正面クロスバンカー狙い。左サイドの池に注意。"},
            4:  {"par": 4, "yard": 271, "memo": "軽く右にドッグレッグしたホール。ティーショットはフェアウェイやや右狙い。安全に左サイドに刻んでいくのも一つの手段。"},
            5:  {"par": 5, "yard": 410, "memo": "距離の短いロングホール。ティーショットはフェアウェイセンター狙い。グリーン手前の池に注意。"},
            6:  {"par": 3, "yard": 114, "memo": "ピンポジションにかかわらず、グリーンセンター狙い。左ガードバンカーに注意。"},
            7:  {"par": 4, "yard": 283, "memo": "ティーショットはフェアウェイセンターのバンカーに注意。二打目は確実にグリーンセンターへ。グリーンを外すと周りからのアプローチは寄せがむずかしい。"},
            8:  {"par": 3, "yard": 148, "memo": "池が気になるショートホール。グリーン右側は比較的安全。"},
            9:  {"par": 4, "yard": 278, "memo": "ティーショットはフェアウェイ正面の木を目標に。二打目は確実にグリーンセンターへ。バーディーの確率が高いホール。"},
            10: {"par": 4, "yard": 297, "memo": "軽く左にドッグレッグしたホール。ティーショットはフェアウェイやや右サイド狙い。ガードバンカーのアゴ高く。二打目は高い弾道で。"},
            11: {"par": 3, "yard": 114, "memo": "グリーン手前の池に注意。グリーン奥からのアプローチもむずかしい。確実にグリーンセンターへ。"},
            12: {"par": 5, "yard": 459, "memo": "ティーショットは正面の木狙い。二打目は左サイドの池に注意。グリーン周りからのアプローチは寄せがむずかしい。"},
            13: {"par": 4, "yard": 329, "memo": "右ドッグレッグのミドルホール。ティーショットはフェアウェイセンター狙い。右を狙いすぎると、二打目が木超えのむずかしいショットに。"},
            14: {"par": 3, "yard": 128, "memo": "グリーン周りのガードバンカーに注意。確実にグリーンセンターへ。グリーン奥はOB。"},
            15: {"par": 4, "yard": 300, "memo": "ティーショットはフェアウェイセンター狙い。グリーン左サイドは比較的安全。"},
            16: {"par": 4, "yard": 294, "memo": "ティーショットはフェアウェイセンター狙い。グリーン右手前のバンカーに注意。二打目は確実にグリーンセンターへ。"},
            17: {"par": 3, "yard": 112, "memo": "グリーン手前のバンカーに注意。高い弾道で、確実にグリーンセンターへ。"},
            18: {"par": 4, "yard": 323, "memo": "軽く左ドッグレッグしたホール。ティーショットはフェアウェイ右サイド狙い。グリーン左サイドはOBが近いので注意。"},
        }
    },
    "琵琶湖レークサイドGC 中→南（レディース）": {
        "name": "琵琶湖レークサイドGC", "tee": "LADIES",
        "holes": {
            1:  {"par": 4, "yard": 318, "memo": "思いっきりティーショットを打っていけるホール。狙いはフェアウェイ左バンカーの右側狙い。グリーンは手前から攻めるのがベスト。"},
            2:  {"par": 3, "yard": 117, "memo": "グリーン周りはOBが出やすい。ピンポジションにかかわらず、グリーンセンターを狙う。"},
            3:  {"par": 4, "yard": 311, "memo": "左ドッグレッグのミドルホール。ティーショットは正面クロスバンカー狙い。左サイドの池に注意。"},
            4:  {"par": 4, "yard": 265, "memo": "軽く右にドッグレッグしたホール。ティーショットはフェアウェイやや右狙い。安全に左サイドに刻んでいくのも一つの手段。"},
            5:  {"par": 5, "yard": 401, "memo": "距離の短いロングホール。ティーショットはフェアウェイセンター狙い。グリーン手前の池に注意。"},
            6:  {"par": 3, "yard": 104, "memo": "ピンポジションにかかわらず、グリーンセンター狙い。左ガードバンカーに注意。"},
            7:  {"par": 4, "yard": 263, "memo": "ティーショットはフェアウェイセンターのバンカーに注意。二打目は確実にグリーンセンターへ。グリーンを外すと周りからのアプローチは寄せがむずかしい。"},
            8:  {"par": 3, "yard": 128, "memo": "池が気になるショートホール。グリーン右側は比較的安全。"},
            9:  {"par": 4, "yard": 260, "memo": "ティーショットはフェアウェイ正面の木を目標に。二打目は確実にグリーンセンターへ。バーディーの確率が高いホール。"},
            10: {"par": 4, "yard": 290, "memo": "軽く左にドッグレッグしたホール。ティーショットはフェアウェイやや右サイド狙い。ガードバンカーのアゴ高く。二打目は高い弾道で。"},
            11: {"par": 3, "yard": 103, "memo": "グリーン手前の池に注意。グリーン奥からのアプローチもむずかしい。確実にグリーンセンターへ。"},
            12: {"par": 5, "yard": 438, "memo": "ティーショットは正面の木狙い。二打目は左サイドの池に注意。グリーン周りからのアプローチは寄せがむずかしい。"},
            13: {"par": 4, "yard": 316, "memo": "右ドッグレッグのミドルホール。ティーショットはフェアウェイセンター狙い。右を狙いすぎると、二打目が木超えのむずかしいショットに。"},
            14: {"par": 3, "yard": 119, "memo": "グリーン周りのガードバンカーに注意。確実にグリーンセンターへ。グリーン奥はOB。"},
            15: {"par": 4, "yard": 289, "memo": "ティーショットはフェアウェイセンター狙い。グリーン左サイドは比較的安全。"},
            16: {"par": 4, "yard": 281, "memo": "ティーショットはフェアウェイセンター狙い。グリーン右手前のバンカーに注意。二打目は確実にグリーンセンターへ。"},
            17: {"par": 3, "yard": 107, "memo": "グリーン手前のバンカーに注意。高い弾道で、確実にグリーンセンターへ。"},
            18: {"par": 4, "yard": 307, "memo": "軽く左ドッグレッグしたホール。ティーショットはフェアウェイ右サイド狙い。グリーン左サイドはOBが近いので注意。"},
        }
    },
    "琵琶湖レークサイドGC 南→北（レギュラー）": {
        "name": "琵琶湖レークサイドGC", "tee": "REG",
        "holes": {
            1:  {"par": 4, "yard": 312, "memo": "軽く左にドッグレッグしたホール。ティーショットはフェアウェイやや右サイド狙い。ガードバンカーのアゴ高く。二打目は高い弾道で。"},
            2:  {"par": 3, "yard": 121, "memo": "グリーン手前の池に注意。グリーン奥からのアプローチもむずかしい。確実にグリーンセンターへ。"},
            3:  {"par": 5, "yard": 482, "memo": "ティーショットは正面の木狙い。二打目は左サイドの池に注意。グリーン周りからのアプローチは寄せがむずかしい。"},
            4:  {"par": 4, "yard": 329, "memo": "右ドッグレッグのミドルホール。ティーショットはフェアウェイセンター狙い。右を狙いすぎると、二打目が木超えのむずかしいショットに。"},
            5:  {"par": 3, "yard": 145, "memo": "グリーン周りのガードバンカーに注意。確実にグリーンセンターへ。グリーン奥はOB。"},
            6:  {"par": 4, "yard": 324, "memo": "ティーショットはフェアウェイセンター狙い。グリーン左サイドは比較的安全。"},
            7:  {"par": 4, "yard": 304, "memo": "ティーショットはフェアウェイセンター狙い。グリーン右手前のバンカーに注意。二打目は確実にグリーンセンターへ。"},
            8:  {"par": 3, "yard": 127, "memo": "グリーン手前のバンカーに注意。高い弾道で、確実にグリーンセンターへ。"},
            9:  {"par": 4, "yard": 328, "memo": "軽く左ドッグレッグしたホール。ティーショットはフェアウェイ右サイド狙い。グリーン左サイドはOBが近いので注意。"},
            10: {"par": 4, "yard": 351, "memo": "砲台グリーンのミドルホール。ティーショットは右サイド広く、やや右狙い。左クロスバンカーに入れると2オンは難しい。"},
            11: {"par": 5, "yard": 509, "memo": "距離の長いロングホール。ティーショットは距離とフェアウェイキープが重要。二打目、右クロスバンカーより軽いドローで攻めるのが狙い目。左傾斜のグリーンで落とし所に注意。"},
            12: {"par": 3, "yard": 115, "memo": "池越えショートホール。距離は短いが、風に要注意。奥につけてしまえば下りのタッチが難しい。"},
            13: {"par": 5, "yard": 450, "memo": "距離の短いロングホール。ティーショットはやや左狙い。右サイドは広いが距離が残る。二打目、フェアウェイ左クロスバンカーに注意。"},
            14: {"par": 4, "yard": 389, "memo": "グリーン手前100Yから軽く右ドッグレッグ。ティーショットはフェアウェイやや左サイド狙い。二打目グリーンオーバーしやすく、突っ込み過ぎに注意。グリーン左横のグラスバンカーにも注意。"},
            15: {"par": 4, "yard": 376, "memo": "砲台グリーンのミドルホール。ティーショットは左右イエローペナルティエリアに注意。グリーンは奥に傾斜しており、高い弾道が必要不可欠。"},
            16: {"par": 3, "yard": 150, "memo": "砲台2段グリーンのショートホール。距離を合わせるのが難しい。左右バンカーはアゴが高く、パーセーブが困難。"},
            17: {"par": 4, "yard": 369, "memo": "受けグリーンのミドルホール。フェアウェイ右サイド、残り150Y地点にコブあり。ティーショットはフェアウェイやや左サイド狙い。二打目、手前バンカーを避け花道からフェード気味に狙う。"},
            18: {"par": 4, "yard": 408, "memo": "距離のあるミドルホール。ティーショットはフェアウェイの右サイド狙いで距離をかせぐ。二打目グリーン手前左右のバンカーに注意。無理せず手前より攻める。"},
        }
    },
    "琵琶湖レークサイドGC 南→北（フロント）": {
        "name": "琵琶湖レークサイドGC", "tee": "FRO",
        "holes": {
            1:  {"par": 4, "yard": 297, "memo": "軽く左にドッグレッグしたホール。ティーショットはフェアウェイやや右サイド狙い。ガードバンカーのアゴ高く。二打目は高い弾道で。"},
            2:  {"par": 3, "yard": 114, "memo": "グリーン手前の池に注意。グリーン奥からのアプローチもむずかしい。確実にグリーンセンターへ。"},
            3:  {"par": 5, "yard": 459, "memo": "ティーショットは正面の木狙い。二打目は左サイドの池に注意。グリーン周りからのアプローチは寄せがむずかしい。"},
            4:  {"par": 4, "yard": 329, "memo": "右ドッグレッグのミドルホール。ティーショットはフェアウェイセンター狙い。右を狙いすぎると、二打目が木超えのむずかしいショットに。"},
            5:  {"par": 3, "yard": 128, "memo": "グリーン周りのガードバンカーに注意。確実にグリーンセンターへ。グリーン奥はOB。"},
            6:  {"par": 4, "yard": 300, "memo": "ティーショットはフェアウェイセンター狙い。グリーン左サイドは比較的安全。"},
            7:  {"par": 4, "yard": 294, "memo": "ティーショットはフェアウェイセンター狙い。グリーン右手前のバンカーに注意。二打目は確実にグリーンセンターへ。"},
            8:  {"par": 3, "yard": 112, "memo": "グリーン手前のバンカーに注意。高い弾道で、確実にグリーンセンターへ。"},
            9:  {"par": 4, "yard": 323, "memo": "軽く左ドッグレッグしたホール。ティーショットはフェアウェイ右サイド狙い。グリーン左サイドはOBが近いので注意。"},
            10: {"par": 4, "yard": 339, "memo": "砲台グリーンのミドルホール。ティーショットは右サイド広く、やや右狙い。左クロスバンカーに入れると2オンは難しい。"},
            11: {"par": 5, "yard": 450, "memo": "距離の長いロングホール。ティーショットは距離とフェアウェイキープが重要。二打目、右クロスバンカーより軽いドローで攻めるのが狙い目。左傾斜のグリーンで落とし所に注意。"},
            12: {"par": 3, "yard": 106, "memo": "池越えショートホール。距離は短いが、風に要注意。奥につけてしまえば下りのタッチが難しい。"},
            13: {"par": 5, "yard": 420, "memo": "距離の短いロングホール。ティーショットはやや左狙い。右サイドは広いが距離が残る。二打目、フェアウェイ左クロスバンカーに注意。"},
            14: {"par": 4, "yard": 374, "memo": "グリーン手前100Yから軽く右ドッグレッグ。ティーショットはフェアウェイやや左サイド狙い。二打目グリーンオーバーしやすく、突っ込み過ぎに注意。グリーン左横のグラスバンカーにも注意。"},
            15: {"par": 4, "yard": 362, "memo": "砲台グリーンのミドルホール。ティーショットは左右イエローペナルティエリアに注意。グリーンは奥に傾斜しており、高い弾道が必要不可欠。"},
            16: {"par": 3, "yard": 139, "memo": "砲台2段グリーンのショートホール。距離を合わせるのが難しい。左右バンカーはアゴが高く、パーセーブが困難。"},
            17: {"par": 4, "yard": 357, "memo": "受けグリーンのミドルホール。フェアウェイ右サイド、残り150Y地点にコブあり。ティーショットはフェアウェイやや左サイド狙い。二打目、手前バンカーを避け花道からフェード気味に狙う。"},
            18: {"par": 4, "yard": 377, "memo": "距離のあるミドルホール。ティーショットはフェアウェイの右サイド狙いで距離をかせぐ。二打目グリーン手前左右のバンカーに注意。無理せず手前より攻める。"},
        }
    },
    "琵琶湖レークサイドGC 南→北（レディース）": {
        "name": "琵琶湖レークサイドGC", "tee": "LADIES",
        "holes": {
            1:  {"par": 4, "yard": 290, "memo": "軽く左にドッグレッグしたホール。ティーショットはフェアウェイやや右サイド狙い。ガードバンカーのアゴ高く。二打目は高い弾道で。"},
            2:  {"par": 3, "yard": 103, "memo": "グリーン手前の池に注意。グリーン奥からのアプローチもむずかしい。確実にグリーンセンターへ。"},
            3:  {"par": 5, "yard": 438, "memo": "ティーショットは正面の木狙い。二打目は左サイドの池に注意。グリーン周りからのアプローチは寄せがむずかしい。"},
            4:  {"par": 4, "yard": 316, "memo": "右ドッグレッグのミドルホール。ティーショットはフェアウェイセンター狙い。右を狙いすぎると、二打目が木超えのむずかしいショットに。"},
            5:  {"par": 3, "yard": 119, "memo": "グリーン周りのガードバンカーに注意。確実にグリーンセンターへ。グリーン奥はOB。"},
            6:  {"par": 4, "yard": 289, "memo": "ティーショットはフェアウェイセンター狙い。グリーン左サイドは比較的安全。"},
            7:  {"par": 4, "yard": 281, "memo": "ティーショットはフェアウェイセンター狙い。グリーン右手前のバンカーに注意。二打目は確実にグリーンセンターへ。"},
            8:  {"par": 3, "yard": 107, "memo": "グリーン手前のバンカーに注意。高い弾道で、確実にグリーンセンターへ。"},
            9:  {"par": 4, "yard": 307, "memo": "軽く左ドッグレッグしたホール。ティーショットはフェアウェイ右サイド狙い。グリーン左サイドはOBが近いので注意。"},
            10: {"par": 4, "yard": 284, "memo": "砲台グリーンのミドルホール。ティーショットは右サイド広く、やや右狙い。左クロスバンカーに入れると2オンは難しい。"},
            11: {"par": 5, "yard": 419, "memo": "距離の長いロングホール。ティーショットは距離とフェアウェイキープが重要。二打目、右クロスバンカーより軽いドローで攻めるのが狙い目。左傾斜のグリーンで落とし所に注意。"},
            12: {"par": 3, "yard": 106, "memo": "池越えショートホール。距離は短いが、風に要注意。奥につけてしまえば下りのタッチが難しい。"},
            13: {"par": 5, "yard": 377, "memo": "距離の短いロングホール。ティーショットはやや左狙い。右サイドは広いが距離が残る。二打目、フェアウェイ左クロスバンカーに注意。"},
            14: {"par": 4, "yard": 335, "memo": "グリーン手前100Yから軽く右ドッグレッグ。ティーショットはフェアウェイやや左サイド狙い。二打目グリーンオーバーしやすく、突っ込み過ぎに注意。グリーン左横のグラスバンカーにも注意。"},
            15: {"par": 4, "yard": 275, "memo": "砲台グリーンのミドルホール。ティーショットは左右イエローペナルティエリアに注意。グリーンは奥に傾斜しており、高い弾道が必要不可欠。"},
            16: {"par": 3, "yard": 124, "memo": "砲台2段グリーンのショートホール。距離を合わせるのが難しい。左右バンカーはアゴが高く、パーセーブが困難。"},
            17: {"par": 4, "yard": 315, "memo": "受けグリーンのミドルホール。フェアウェイ右サイド、残り150Y地点にコブあり。ティーショットはフェアウェイやや左サイド狙い。二打目、手前バンカーを避け花道からフェード気味に狙う。"},
            18: {"par": 4, "yard": 302, "memo": "距離のあるミドルホール。ティーショットはフェアウェイの右サイド狙いで距離をかせぐ。二打目グリーン手前左右のバンカーに注意。無理せず手前より攻める。"},
        }
    },
    "琵琶湖レークサイドGC 北→中（レギュラー）": {
        "name": "琵琶湖レークサイドGC", "tee": "REG",
        "holes": {
            1:  {"par": 4, "yard": 351, "memo": "砲台グリーンのミドルホール。ティーショットは右サイド広く、やや右狙い。左クロスバンカーに入れると2オンは難しい。"},
            2:  {"par": 5, "yard": 509, "memo": "距離の長いロングホール。ティーショットは距離とフェアウェイキープが重要。二打目、右クロスバンカーより軽いドローで攻めるのが狙い目。左傾斜のグリーンで落とし所に注意。"},
            3:  {"par": 3, "yard": 115, "memo": "池越えショートホール。距離は短いが、風に要注意。奥につけてしまえば下りのタッチが難しい。"},
            4:  {"par": 5, "yard": 450, "memo": "距離の短いロングホール。ティーショットはやや左狙い。右サイドは広いが距離が残る。二打目、フェアウェイ左クロスバンカーに注意。"},
            5:  {"par": 4, "yard": 389, "memo": "グリーン手前100Yから軽く右ドッグレッグ。ティーショットはフェアウェイやや左サイド狙い。二打目グリーンオーバーしやすく、突っ込み過ぎに注意。グリーン左横のグラスバンカーにも注意。"},
            6:  {"par": 4, "yard": 376, "memo": "砲台グリーンのミドルホール。ティーショットは左右イエローペナルティエリアに注意。グリーンは奥に傾斜しており、高い弾道が必要不可欠。"},
            7:  {"par": 3, "yard": 150, "memo": "砲台2段グリーンのショートホール。距離を合わせるのが難しい。左右バンカーはアゴが高く、パーセーブが困難。"},
            8:  {"par": 4, "yard": 369, "memo": "受けグリーンのミドルホール。フェアウェイ右サイド、残り150Y地点にコブあり。ティーショットはフェアウェイやや左サイド狙い。二打目、手前バンカーを避け花道からフェード気味に狙う。"},
            9:  {"par": 4, "yard": 408, "memo": "距離のあるミドルホール。ティーショットはフェアウェイの右サイド狙いで距離をかせぐ。二打目グリーン手前左右のバンカーに注意。無理せず手前より攻める。"},
            10: {"par": 4, "yard": 334, "memo": "思いっきりティーショットを打っていけるホール。狙いはフェアウェイ左バンカーの右側狙い。グリーンは手前から攻めるのがベスト。"},
            11: {"par": 3, "yard": 129, "memo": "グリーン周りはOBが出やすい。ピンポジションにかかわらず、グリーンセンターを狙う。"},
            12: {"par": 4, "yard": 341, "memo": "左ドッグレッグのミドルホール。ティーショットは正面クロスバンカー狙い。左サイドの池に注意。"},
            13: {"par": 4, "yard": 303, "memo": "軽く右にドッグレッグしたホール。ティーショットはフェアウェイやや右狙い。安全に左サイドに刻んでいくのも一つの手段。"},
            14: {"par": 5, "yard": 421, "memo": "距離の短いロングホール。ティーショットはフェアウェイセンター狙い。グリーン手前の池に注意。"},
            15: {"par": 3, "yard": 114, "memo": "ピンポジションにかかわらず、グリーンセンター狙い。左ガードバンカーに注意。"},
            16: {"par": 4, "yard": 293, "memo": "ティーショットはフェアウェイセンターのバンカーに注意。二打目は確実にグリーンセンターへ。グリーンを外すと周りからのアプローチは寄せがむずかしい。"},
            17: {"par": 3, "yard": 167, "memo": "池が気になるショートホール。グリーン右側は比較的安全。"},
            18: {"par": 4, "yard": 288, "memo": "ティーショットはフェアウェイ正面の木を目標に。二打目は確実にグリーンセンターへ。バーディーの確率が高いホール。"},
        }
    },
    "琵琶湖レークサイドGC 北→中（フロント）": {
        "name": "琵琶湖レークサイドGC", "tee": "FRO",
        "holes": {
            1:  {"par": 4, "yard": 339, "memo": "砲台グリーンのミドルホール。ティーショットは右サイド広く、やや右狙い。左クロスバンカーに入れると2オンは難しい。"},
            2:  {"par": 5, "yard": 450, "memo": "距離の長いロングホール。ティーショットは距離とフェアウェイキープが重要。二打目、右クロスバンカーより軽いドローで攻めるのが狙い目。左傾斜のグリーンで落とし所に注意。"},
            3:  {"par": 3, "yard": 106, "memo": "池越えショートホール。距離は短いが、風に要注意。奥につけてしまえば下りのタッチが難しい。"},
            4:  {"par": 5, "yard": 420, "memo": "距離の短いロングホール。ティーショットはやや左狙い。右サイドは広いが距離が残る。二打目、フェアウェイ左クロスバンカーに注意。"},
            5:  {"par": 4, "yard": 374, "memo": "グリーン手前100Yから軽く右ドッグレッグ。ティーショットはフェアウェイやや左サイド狙い。二打目グリーンオーバーしやすく、突っ込み過ぎに注意。グリーン左横のグラスバンカーにも注意。"},
            6:  {"par": 4, "yard": 362, "memo": "砲台グリーンのミドルホール。ティーショットは左右イエローペナルティエリアに注意。グリーンは奥に傾斜しており、高い弾道が必要不可欠。"},
            7:  {"par": 3, "yard": 139, "memo": "砲台2段グリーンのショートホール。距離を合わせるのが難しい。左右バンカーはアゴが高く、パーセーブが困難。"},
            8:  {"par": 4, "yard": 357, "memo": "受けグリーンのミドルホール。フェアウェイ右サイド、残り150Y地点にコブあり。ティーショットはフェアウェイやや左サイド狙い。二打目、手前バンカーを避け花道からフェード気味に狙う。"},
            9:  {"par": 4, "yard": 377, "memo": "距離のあるミドルホール。ティーショットはフェアウェイの右サイド狙いで距離をかせぐ。二打目グリーン手前左右のバンカーに注意。無理せず手前より攻める。"},
            10: {"par": 4, "yard": 327, "memo": "思いっきりティーショットを打っていけるホール。狙いはフェアウェイ左バンカーの右側狙い。グリーンは手前から攻めるのがベスト。"},
            11: {"par": 3, "yard": 123, "memo": "グリーン周りはOBが出やすい。ピンポジションにかかわらず、グリーンセンターを狙う。"},
            12: {"par": 4, "yard": 330, "memo": "左ドッグレッグのミドルホール。ティーショットは正面クロスバンカー狙い。左サイドの池に注意。"},
            13: {"par": 4, "yard": 271, "memo": "軽く右にドッグレッグしたホール。ティーショットはフェアウェイやや右狙い。安全に左サイドに刻んでいくのも一つの手段。"},
            14: {"par": 5, "yard": 410, "memo": "距離の短いロングホール。ティーショットはフェアウェイセンター狙い。グリーン手前の池に注意。"},
            15: {"par": 3, "yard": 114, "memo": "ピンポジションにかかわらず、グリーンセンター狙い。左ガードバンカーに注意。"},
            16: {"par": 4, "yard": 283, "memo": "ティーショットはフェアウェイセンターのバンカーに注意。二打目は確実にグリーンセンターへ。グリーンを外すと周りからのアプローチは寄せがむずかしい。"},
            17: {"par": 3, "yard": 148, "memo": "池が気になるショートホール。グリーン右側は比較的安全。"},
            18: {"par": 4, "yard": 278, "memo": "ティーショットはフェアウェイ正面の木を目標に。二打目は確実にグリーンセンターへ。バーディーの確率が高いホール。"},
        }
    },
    "琵琶湖レークサイドGC 北→中（レディース）": {
        "name": "琵琶湖レークサイドGC", "tee": "LADIES",
        "holes": {
            1:  {"par": 4, "yard": 284, "memo": "砲台グリーンのミドルホール。ティーショットは右サイド広く、やや右狙い。左クロスバンカーに入れると2オンは難しい。"},
            2:  {"par": 5, "yard": 419, "memo": "距離の長いロングホール。ティーショットは距離とフェアウェイキープが重要。二打目、右クロスバンカーより軽いドローで攻めるのが狙い目。左傾斜のグリーンで落とし所に注意。"},
            3:  {"par": 3, "yard": 106, "memo": "池越えショートホール。距離は短いが、風に要注意。奥につけてしまえば下りのタッチが難しい。"},
            4:  {"par": 5, "yard": 377, "memo": "距離の短いロングホール。ティーショットはやや左狙い。右サイドは広いが距離が残る。二打目、フェアウェイ左クロスバンカーに注意。"},
            5:  {"par": 4, "yard": 335, "memo": "グリーン手前100Yから軽く右ドッグレッグ。ティーショットはフェアウェイやや左サイド狙い。二打目グリーンオーバーしやすく、突っ込み過ぎに注意。グリーン左横のグラスバンカーにも注意。"},
            6:  {"par": 4, "yard": 275, "memo": "砲台グリーンのミドルホール。ティーショットは左右イエローペナルティエリアに注意。グリーンは奥に傾斜しており、高い弾道が必要不可欠。"},
            7:  {"par": 3, "yard": 124, "memo": "砲台2段グリーンのショートホール。距離を合わせるのが難しい。左右バンカーはアゴが高く、パーセーブが困難。"},
            8:  {"par": 4, "yard": 315, "memo": "受けグリーンのミドルホール。フェアウェイ右サイド、残り150Y地点にコブあり。ティーショットはフェアウェイやや左サイド狙い。二打目、手前バンカーを避け花道からフェード気味に狙う。"},
            9:  {"par": 4, "yard": 302, "memo": "距離のあるミドルホール。ティーショットはフェアウェイの右サイド狙いで距離をかせぐ。二打目グリーン手前左右のバンカーに注意。無理せず手前より攻める。"},
            10: {"par": 4, "yard": 318, "memo": "思いっきりティーショットを打っていけるホール。狙いはフェアウェイ左バンカーの右側狙い。グリーンは手前から攻めるのがベスト。"},
            11: {"par": 3, "yard": 117, "memo": "グリーン周りはOBが出やすい。ピンポジションにかかわらず、グリーンセンターを狙う。"},
            12: {"par": 4, "yard": 311, "memo": "左ドッグレッグのミドルホール。ティーショットは正面クロスバンカー狙い。左サイドの池に注意。"},
            13: {"par": 4, "yard": 265, "memo": "軽く右にドッグレッグしたホール。ティーショットはフェアウェイやや右狙い。安全に左サイドに刻んでいくのも一つの手段。"},
            14: {"par": 5, "yard": 401, "memo": "距離の短いロングホール。ティーショットはフェアウェイセンター狙い。グリーン手前の池に注意。"},
            15: {"par": 3, "yard": 104, "memo": "ピンポジションにかかわらず、グリーンセンター狙い。左ガードバンカーに注意。"},
            16: {"par": 4, "yard": 263, "memo": "ティーショットはフェアウェイセンターのバンカーに注意。二打目は確実にグリーンセンターへ。グリーンを外すと周りからのアプローチは寄せがむずかしい。"},
            17: {"par": 3, "yard": 128, "memo": "池が気になるショートホール。グリーン右側は比較的安全。"},
            18: {"par": 4, "yard": 260, "memo": "ティーショットはフェアウェイ正面の木を目標に。二打目は確実にグリーンセンターへ。バーディーの確率が高いホール。"},
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
    _saved_clubs = _localS.getItem("golf_ai_clubs")
    st.session_state.clubs = _saved_clubs if _saved_clubs else CLUBS.copy()
if "selected_club" not in st.session_state:
    st.session_state.selected_club = st.session_state.clubs[0]["name"]
if "caddy_log" not in st.session_state:
    st.session_state.caddy_log = []
if "last_caddy_message" not in st.session_state:
    st.session_state.last_caddy_message = ""
if "pending_speech_text" not in st.session_state:
    st.session_state.pending_speech_text = ""
if "caddy_audio_bytes" not in st.session_state:
    st.session_state.caddy_audio_bytes = None
if "safety_margin" not in st.session_state:
    st.session_state.safety_margin = 0

if "course" not in st.session_state:
    st.session_state.course = {
        h: {
            "par": d["par"], "yard": d["yard"], "memo": d.get("memo", ""),
            "elevation": d.get("elevation", 0),
            "green_side_bunkers": d.get("green_side_bunkers", []),
            "green": d.get("green", {}),
        }
        for h, d in PRESET_COURSES["宝塚ゴルフ倶楽部 新コース（フロント）"]["holes"].items()
    }

# =========================
# クラブ選択ロジック（app_v2と同一）
# =========================

def get_valid_clubs(margin=None):
    if margin is None:
        margin = st.session_state.get("safety_margin", 0)
    valid = [c for c in st.session_state.clubs if c["dist"] > 0 and c["name"] != "なし"]
    if margin == 0 or not valid:
        return valid
    if margin < 0:
        # アプローチ用：全クラブをフラットにブースト（早打ちで短くした分を補う）
        boost = -margin
        return [{**c, "dist": c["dist"] + boost} for c in valid]
    # 早打ち用：長いクラブほど大きく差し引く
    max_dist = max(c["dist"] for c in valid)
    min_dist = min(c["dist"] for c in valid)
    dist_range = max_dist - min_dist or 1
    return [
        {**c, "dist": max(round(c["dist"] - margin * (c["dist"] - min_dist) / dist_range), 1)}
        for c in valid
    ]

def choose_club(remaining, shots_left, is_first_shot, par_num, hole, _margin=None):
    hole_data  = st.session_state.course.get(hole, {}) if isinstance(hole, (int, str)) else {}
    _elevation = hole_data.get("elevation", 0)
    _total_y   = hole_data.get("yard", 0)
    if _elevation != 0 and _total_y > 0:
        remaining = max(round(remaining + _elevation * remaining / _total_y), 1)
    _go_threshold = st.session_state.get("green_on_threshold", 130)
    if _go_threshold > 0 and remaining <= _go_threshold and shots_left > 1:
        shots_left = 1
    safety_m = _margin if _margin is not None else st.session_state.get("safety_margin", 0)
    effective_margin = 0 if shots_left == 1 else safety_m
    valid_clubs = get_valid_clubs(margin=effective_margin)
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
                dtype  = st.session_state.get(f"danger_type_{hole}_{i}", "未入力")
                dstart = st.session_state.get(f"danger_start_{hole}_{i}", 0)
                dend   = st.session_state.get(f"danger_end_{hole}_{i}", 0)
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
            dtype  = st.session_state.get(f"danger_type_{hole}_{i}", "未入力")
            dstart = st.session_state.get(f"danger_start_{hole}_{i}", 0)
            dend   = st.session_state.get(f"danger_end_{hole}_{i}", 0)
            if dtype != "未入力" and dstart <= club["dist"] <= dend:
                danger_penalty += danger_scores.get(dtype, 0)

        if club["name"] == "1W": continue
        if shots_left > 1 and club["dist"] >= remaining: continue
        if shots_left == 2:
            longest = max(c["dist"] for c in valid_clubs)
            if remaining - club["dist"] > longest: continue

        good      = club["dist"]
        miss_dist = club["dist"] * 0.6
        miss_rate = club["miss"]
        expected_after = (1 - miss_rate) * (remaining - good) + miss_rate * (remaining - miss_dist)
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
    safety_m = st.session_state.get("safety_margin", 0)
    # Phase 1: standard plan (margin=0)
    result_std = []
    remaining  = total_dist
    for i in range(strokes):
        shots_left    = strokes - i
        is_first_shot = (used + i == 0)
        club = choose_club(remaining, shots_left, is_first_shot, par_num, hole, _margin=0)
        if len(result_std) == strokes - 1:
            reachable = [c for c in get_valid_clubs(margin=0) if c["dist"] >= remaining]
            if reachable:
                club = min(reachable, key=lambda c: c["dist"])
        shot_dist = club["dist"]
        result_std.append({"shot": i+1, "club": club["name"], "dist": shot_dist,
                           "remain": max(remaining - shot_dist, 0), "before": remaining})
        remaining = max(remaining - shot_dist, 0)
    if safety_m == 0:
        return result_std
    # Phase 2: apply safety overlay
    safe_result   = []
    remaining     = total_dist
    approach_boost = safety_m * (strokes - 1)
    for i, p in enumerate(result_std):
        is_approach = (i == len(result_std) - 1)
        if is_approach:
            boosted   = get_valid_clubs(margin=-approach_boost)
            reachable = [c for c in boosted if c["dist"] >= remaining]
            if reachable:
                bc = min(reachable, key=lambda c: c["dist"])
                club_name = bc["name"]
                shot_dist = min(bc["dist"], remaining)
            else:
                club_name = p["club"]
                shot_dist = remaining
        else:
            club_name = p["club"]
            shot_dist = max(p["dist"] - safety_m, 1)
        safe_result.append({"shot": i+1, "club": club_name, "dist": shot_dist,
                            "remain": max(remaining - shot_dist, 0), "before": remaining})
        remaining = max(remaining - shot_dist, 0)
    return safe_result

# =========================
# ホール難易度・目標打数計算（app_v2と同一）
# =========================

def calc_hole_targets(target_score):
    hole_difficulty = {}
    for h, data in st.session_state.course.items():
        yard = data["yard"]; par = data["par"]
        score = yard / 100
        if par == 5: score -= 3
        elif par == 3: score += 1
        if par == 4 and yard > 380: score += 1.5
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
                hole_targets[h] -= 1; diff_total += 1
            else: idx += 1
    elif diff_total > 0:
        harder = sorted_holes[::-1]; idx = 0
        while diff_total > 0 and idx < len(harder):
            h = harder[idx][0]; hole_targets[h] += 1; diff_total -= 1; idx += 1
    return hole_targets

def calc_remaining_targets(target_score):
    holes = sorted(st.session_state.course.keys())
    actual_sum = 0; remaining_holes = []
    for h in holes:
        actual = st.session_state.get(f"actual_{h}", "")
        if actual != "": actual_sum += int(actual)
        else: remaining_holes.append(h)
    if not remaining_holes or actual_sum == 0:
        return calc_hole_targets(target_score)
    remaining_budget = target_score - actual_sum
    remaining_par    = sum(st.session_state.course[h]["par"] for h in remaining_holes)
    hole_difficulty  = {}
    for h in remaining_holes:
        data = st.session_state.course[h]; yard = data["yard"]; par = data["par"]
        score = yard / 100
        if par == 5: score -= 3
        elif par == 3: score += 1
        if par == 4 and yard > 380: score += 1.5
        hole_difficulty[h] = score
    sorted_remaining = sorted(hole_difficulty.items(), key=lambda x: x[1])
    average_diff = (remaining_budget - remaining_par) / len(remaining_holes) if remaining_holes else 0
    base_diff    = int(average_diff)
    original_targets = calc_hole_targets(target_score)
    hole_targets = {}
    for h in holes:
        actual = st.session_state.get(f"actual_{h}", "")
        if actual != "": hole_targets[h] = original_targets[h]
        else: hole_targets[h] = st.session_state.course[h]["par"] + base_diff
    current_remaining_total = sum(hole_targets[h] for h in remaining_holes)
    diff_total = remaining_budget - current_remaining_total
    if diff_total < 0:
        idx = 0
        while diff_total < 0 and idx < len(sorted_remaining):
            h = sorted_remaining[idx][0]
            if hole_targets[h] > st.session_state.course[h]["par"]:
                hole_targets[h] -= 1; diff_total += 1
            else: idx += 1
    elif diff_total > 0:
        harder = sorted_remaining[::-1]; idx = 0
        while diff_total > 0 and idx < len(harder):
            h = harder[idx][0]; hole_targets[h] += 1; diff_total -= 1; idx += 1
    return hole_targets

def score_info(diff):
    if diff <= -1:  return "★ バーディ", "#8B0000"
    elif diff == 0: return "◎ パー",     "#e53e3e"
    elif diff == 1: return "○ ボギー",   "#2b6cb0"
    elif diff == 2: return "△ ダブル",   "#276749"
    else:           return "▼ トリプル+", "#2d3748"

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
        deviation     = ""; dev_color = "#1a1a1a"
        if actual != "":
            gap = int(actual) - target
            if gap > 0: deviation = f"+{gap}"; dev_color = "#dc2626"
            elif gap < 0: deviation = str(gap); dev_color = "#2563eb"
            else: deviation = "±0"
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
                f"</div>", unsafe_allow_html=True)
        st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)

# ============================================================
# アプリ本体
# ============================================================

import base64 as _b64, os as _os
_logo_path = _os.path.join(_os.path.dirname(__file__), "rogo.png")
if _os.path.exists(_logo_path):
    with open(_logo_path, "rb") as _f:
        _logo_b64 = _b64.b64encode(_f.read()).decode()
    _logo_tag = f"<img src='data:image/png;base64,{_logo_b64}' style='height:80px; vertical-align:middle; margin-right:12px;'>"
else:
    _logo_tag = "⛳"
st.markdown(f'<div style="font-size:40px; font-weight:900; color:#1a2e44; margin-bottom:6px; display:flex; align-items:center;">{_logo_tag}AIキャディ</div>', unsafe_allow_html=True)

# ---------- ラウンド目標 ----------
goal_col1, goal_col2 = st.columns([1, 1])
with goal_col1:
    st.markdown('<div style="font-size:22px; font-weight:900; color:#1a2e44; margin-top:20px; margin-bottom:-14px;">⛳ ラウンドスコア目標</div>', unsafe_allow_html=True)
with goal_col2:
    st.markdown('<div id="target-score-anchor"></div>', unsafe_allow_html=True)
    target_score = st.selectbox("", list(range(60, 151)), index=40, key="target_score", label_visibility="collapsed")

if "adjust_plan"          not in st.session_state: st.session_state.adjust_plan          = False
if "dismissed_triggers"   not in st.session_state: st.session_state.dismissed_triggers   = set()
if st.session_state.get("_last_target_score") != target_score:
    st.session_state.adjust_plan        = False
    st.session_state.dismissed_triggers = set()
    st.session_state["_last_target_score"] = target_score

if st.session_state.adjust_plan:
    hole_targets = calc_remaining_targets(target_score)
else:
    hole_targets = calc_hole_targets(target_score)

with st.expander(f"目標{target_score}の計画＆実績", expanded=False):
    holes = sorted(st.session_state.course.keys())
    render_score_table(holes, hole_targets)

holes           = sorted(st.session_state.course.keys())
total_par       = sum(st.session_state.course[h]["par"] for h in holes)
original_targets = calc_hole_targets(target_score)
projected_total = 0; completed_count = 0
for h in holes:
    actual = st.session_state.get(f"actual_{h}", "")
    if actual != "": projected_total += int(actual); completed_count += 1
    else: projected_total += original_targets[h]

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
    f"</div></div>", unsafe_allow_html=True)

# 計画変更トリガー
_completed_holes = [h for h in holes if st.session_state.get(f"actual_{h}", "") != ""]
_trigger = False; _trigger_window = None
for _i in range(len(_completed_holes) - 2):
    _window     = tuple(_completed_holes[_i:_i+3])
    _window_dev = sum(int(st.session_state.get(f"actual_{h}", 0)) - original_targets[h] for h in _window)
    if _window_dev >= 6 and _window not in st.session_state.dismissed_triggers:
        _trigger = True; _trigger_window = _window; break

if _trigger and _trigger_window is not None:
    remaining_count = 18 - completed_count
    if remaining_count > 0:
        st.markdown(
            f"<div style='background:#fef2f2; border:2px solid #fca5a5; border-radius:10px; "
            f"padding:10px 16px; margin-top:8px; font-size:22px; font-weight:700; color:#991b1b;'>"
            f"⚠️ 目標達成が難しくなっています（見込み {projected_total}）。<br>"
            f"目標{target_score}達成のために今後の計画を攻めのゴルフに変更しますか？"
            f"</div>", unsafe_allow_html=True)
        st.markdown('<div id="adjust-btn-anchor"></div>', unsafe_allow_html=True)
        yes_col, no_col, _ = st.columns([1, 1, 1])
        with yes_col:
            if st.button("はい（計画を変更）", key="btn_adjust_yes", use_container_width=True):
                st.session_state.adjust_plan = True
                st.session_state.dismissed_triggers.add(_trigger_window)
                st.rerun()
        with no_col:
            if st.button("いいえ（このまま）", key="btn_adjust_no", use_container_width=True):
                st.session_state.dismissed_triggers.add(_trigger_window)
                st.rerun()

if st.session_state.adjust_plan:
    st.markdown(
        f"<div style='background:#f0fdf4; border:2px solid #86efac; border-radius:10px; "
        f"padding:8px 16px; margin-top:8px; font-size:20px; font-weight:700; color:#166534;'>"
        f"✅ 目標{target_score}達成に向けて残りホールの計画を再設定しました"
        f"</div>", unsafe_allow_html=True)
    if st.button("元の計画に戻す", key="btn_adjust_cancel", use_container_width=False):
        st.session_state.adjust_plan = False
        st.rerun()

st.markdown("<div style='margin-top:2px'></div>", unsafe_allow_html=True)

# ---------- ホール選択 ----------
st.markdown('<div style="font-size:22px; font-weight:900; color:#1a2e44; margin-top:4px; margin-bottom:6px;">⛳ ホールを選択</div>', unsafe_allow_html=True)

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
hole = st.radio("", _hole_keys, key="hole_select", label_visibility="collapsed", horizontal=True)

TOTAL_DIST = st.session_state.course[hole]["yard"]
par_num    = st.session_state.course[hole]["par"]
hole_memo  = st.session_state.course[hole].get("memo", "")

st.markdown(
    f"""<div class="hole-header">
        <h2>⛳ {hole}番ホール</h2>
        <div class="sub">{TOTAL_DIST}y ／ Par {par_num}</div>
    </div>""", unsafe_allow_html=True)


if "prev_hole" not in st.session_state:
    st.session_state.prev_hole = hole

if hole != st.session_state.prev_hole:
    st.session_state.remaining     = TOTAL_DIST
    st.session_state.history       = []
    st.session_state.prev_hole     = hole
    st.session_state.green_on_flag = False
    st.session_state.last_caddy_message = ""
    st.session_state.caddy_log     = []

if "remaining" not in st.session_state:
    st.session_state.remaining = TOTAL_DIST
if "history" not in st.session_state:
    st.session_state.history = []

# ---------- ショット戦略表示 ----------
recommended_score = hole_targets[hole]
diff              = recommended_score - par_num
label, rec_color  = score_info(diff)
label_text        = label.split(' ', 1)[1] if ' ' in label else label

target       = recommended_score
putts        = 2
shot_strokes = target - putts

for i in range(1, 3):
    st.session_state[f"danger_type_{hole}_{i}"]  = "未入力"
    st.session_state[f"danger_start_{hole}_{i}"] = 0
    st.session_state[f"danger_end_{hole}_{i}"]   = 0

st.markdown(
    f"<div style='background:linear-gradient(135deg,#064e3b,#065f46); color:white; border-radius:20px; padding:20px 18px; margin:10px 0 0 0; display:flex; align-items:center; gap:8px;'>"
    f"<span style='font-size:24px; font-weight:900; white-space:nowrap; margin-right:16px;'>ショット戦略</span>"
    f"<span style='font-size:24px; font-weight:900; color:#6ee7b7; white-space:nowrap;'>{recommended_score}打／{label_text}</span>"
    f"</div>", unsafe_allow_html=True)

st.markdown("""
<style>
div[data-testid="stRadio"] label { font-size: 20px !important; font-weight: 700 !important; }
div[data-testid="stRadio"] label > div:first-child { display: none !important; }
</style>
""", unsafe_allow_html=True)
_margin_labels = ["標準", "+1", "+2", "+3"]
_margin_values = [0, 5, 10, 15]
if "safety_radio" not in st.session_state:
    st.session_state.safety_radio = "標準"
_col_txt, _col_rad = st.columns([1, 4])
with _col_txt:
    st.markdown("<div style='font-size:20px; font-weight:700; color:red; margin-top:2px;'>安全度</div>", unsafe_allow_html=True)
with _col_rad:
    _selected = st.radio("安全度", _margin_labels, horizontal=True, label_visibility="collapsed", key="safety_radio")
st.session_state.safety_margin = _margin_values[_margin_labels.index(_selected)]

current_shot = 1
for h in st.session_state.history:
    result_text = {
        "OB": "OB（1打罰）", "池": "池（1打罰）", "赤杭": "赤杭（1打罰）",
        "ロスト": "ロスト（2打罰）", "空振り": "空振り", "FW": "FW",
        "ラフ": "ラフ", "プレ4": "プレ4（2打罰）", "プレ3": "プレ3（1打罰）",
    }.get(h.get("result", ""), "")
    green_on_mark = " <span style='font-size:20px;'>🚩グリーンオン</span>" if h.get("green_on") else ""
    suffix = f" ⚡ {result_text}" if result_text else ""
    voice_mark = " 🎤" if h.get("voice") else ""
    st.markdown(
        f"<div class='shot-row-history'>✅ （実績）：{h['club']} {h['dist']}y{voice_mark}{green_on_mark}{suffix}</div>",
        unsafe_allow_html=True)
    current_shot += 1 + h.get("penalty", 0)

used              = sum(1 + h.get("penalty", 0) for h in st.session_state.history)
remaining_strokes = shot_strokes - used

# 次のショット推奨クラブを計算（キャディ応答用）
next_club_name = "なし"; next_club_dist = 0
if st.session_state.remaining > 0 and remaining_strokes > 0:
    plan_data      = plan(st.session_state.remaining, remaining_strokes, used, par_num, hole)
    next_club_name = plan_data[0]["club"] if plan_data else "なし"
    next_club_dist = plan_data[0]["dist"] if plan_data else 0

    shots_to_green = next((i+1 for i, p in enumerate(plan_data) if p["remain"] == 0), len(plan_data))

    # ── 音声で聞くボタン ──
    _sv_spare = remaining_strokes - shots_to_green
    _sv_spare_note = f"、{_sv_spare}打余裕があります" if _sv_spare > 0 else ""
    _sv_memo_raw = st.session_state.course.get(hole, {}).get("memo", "")
    _sv_memo_sentences = [s for s in _sv_memo_raw.split("。") if s.strip()]
    _sv_memo_short = "。".join(_sv_memo_sentences[:2]) + ("。" if _sv_memo_sentences else "")
    _sv_memo_note = f"　なお、{_sv_memo_short}" if _sv_memo_short else ""
    _sv_text = (f"{hole}番ホール、{st.session_state.remaining}ヤード、"
                f"{_plan_to_voice(plan_data)}{_sv_spare_note}。{_sv_memo_note}")
    speak_with_browser(_sv_text, label="🔊 ショット戦略を聞く", pausable=True)
    st.markdown("<div style='margin-top:10px;'></div>", unsafe_allow_html=True)

    _hole_d = st.session_state.course.get(hole, {})
    for i, p in enumerate(plan_data):
        if p["before"] == 0: continue
        display_dist  = min(p["dist"], p["before"])
        is_last       = (i == len(plan_data) - 1)
        green_on_here = (p["remain"] == 0)
        if green_on_here or (is_last and display_dist >= p["before"]):
            st.markdown(f"<div class='shot-row'><strong>{p['club']} ／{display_dist}y</strong>（🚩Gオン！）</div>", unsafe_allow_html=True)
            margin = remaining_strokes - shots_to_green
            if margin > 0:
                st.markdown(
                    f"<div style='background:#dcfce7; border-left:4px solid #16a34a; border-radius:8px; padding:10px 20px; margin-top:8px; font-size:22px; font-weight:700; color:#15803d;'>"
                    f"🟢 {margin}打余裕があります</div>", unsafe_allow_html=True)
            _gnote  = _hole_d.get("green", {}).get("note", "")
            if _gnote:
                st.markdown(
                    f"<div style='background:#fefce8; border-left:4px solid #ca8a04; border-radius:8px; "
                    f"padding:6px 14px; margin:4px 0; font-size:17px; font-weight:600; color:#78350f;'>"
                    f"⚠️ {_gnote}</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='shot-row'><strong>パット {putts}回</strong></div>", unsafe_allow_html=True)
            break
        elif is_last:
            st.markdown(f"<div class='shot-row-warn'><strong>{p['club']} ／{display_dist}y</strong>　残{max(p['before']-display_dist,0)}y</div>", unsafe_allow_html=True)
        else:
            _elev_n = st.session_state.course.get(hole, {}).get("elevation", 0)
            _elev_tag = ""
            if _elev_n > 3:
                _elev_tag = f"<span style='font-size:13px; color:#b45309;'> ↑{abs(_elev_n):.0f}y補正</span>"
            elif _elev_n < -3:
                _elev_tag = f"<span style='font-size:13px; color:#0369a1;'> ↓{abs(_elev_n):.0f}y補正</span>"
            st.markdown(f"<div class='shot-row'><strong>{p['club']} ／{display_dist}y</strong>　残{max(p['before']-display_dist,0)}y{_elev_tag}</div>", unsafe_allow_html=True)
            # 1打目：バンカーまでの距離をティーから表示
            if i == 0 and used == 0:
                _bunkers_ts  = _hole_d.get("green_side_bunkers", [])
                _pos_jp_ts   = {"left": "左", "right": "右", "front": "手前", "back": "奥"}
                _driver_dist = next((c["dist"] for c in st.session_state.clubs if c["name"] == "1W"), 200)
                _tee_bunk    = [
                    f"{_pos_jp_ts.get(b['position'], b['position'])}バンカーまで{p['before'] - b['approx_dist']}y"
                    for b in _bunkers_ts
                    if 0 < b.get("approx_dist", 0) < p["before"]
                    and (p["before"] - b["approx_dist"]) <= _driver_dist + 50
                ]
                if _tee_bunk:
                    st.markdown(
                        f"<div style='background:#fefce8; border-left:4px solid #ca8a04; border-radius:8px; "
                        f"padding:6px 14px; margin:4px 0; font-size:17px; font-weight:600; color:#78350f;'>"
                        f"⚠️ " + "　".join(_tee_bunk) + "</div>", unsafe_allow_html=True)

elif st.session_state.remaining == 0:
    st.markdown(f"<div class='shot-row'><strong>パット {putts}回</strong></div>", unsafe_allow_html=True)
elif remaining_strokes == 0:
    st.error("⚠️ この計画では届きません")
else:
    st.error("ショット数が不足しています")


# =========================
# 🎤 キャディの回答を聞く（新機能）
# =========================

st.markdown("<div class='section-divider' style='margin:6px 0;'></div>", unsafe_allow_html=True)

if "voice_text"         not in st.session_state: st.session_state.voice_text         = ""
if "last_audio_id"      not in st.session_state: st.session_state.last_audio_id      = None
if "caddy_result_cache" not in st.session_state: st.session_state.caddy_result_cache = None

caddy_audio = st.audio_input("🎤 キャディに話しかける", key="caddy_voice_input")

st.markdown(
    "<div style='font-size:26px; font-weight:900; color:#1a2e44; margin-top:-12px; margin-bottom:6px;'>"
    "🎤 キャディの回答を聞く</div>", unsafe_allow_html=True)

# 直近のキャディ返答をボタン表示
if st.session_state.last_caddy_message:
    st.session_state.pending_speech_text = st.session_state.last_caddy_message
    st.session_state.last_caddy_message = ""
if st.session_state.pending_speech_text:
    speak_with_browser(st.session_state.pending_speech_text)

if caddy_audio is not None:
    # 同じ音声を2回処理しないようにIDで管理
    audio_id = hash(caddy_audio.read())
    caddy_audio.seek(0)

    if audio_id != st.session_state.last_audio_id:
        st.session_state.last_audio_id = audio_id

        with st.spinner("🎤 聞き取り中..."):
            audio_bytes = caddy_audio.read()
            text = transcribe_audio(audio_bytes)

        if text:
            st.markdown(f"<div class='voice-result'>🗣️ 「{text}」</div>", unsafe_allow_html=True)

            history_text = "なし"
            if st.session_state.history:
                history_text = "、".join([f"{h['club']} {h['dist']}y ({h['result']})" for h in st.session_state.history])

            # 残りショット全体の戦略テキストを生成
            if st.session_state.remaining > 0 and remaining_strokes > 0:
                _plan = plan(st.session_state.remaining, remaining_strokes, used, par_num, hole)
                _plan_parts = []
                for _i, _p in enumerate(_plan):
                    _d = min(_p["dist"], _p["before"])
                    _label = f"第{_i+1}打" if _i > 0 else "第1打（ティーショット）" if used == 0 else f"第{used+_i+1}打"
                    if _p["remain"] == 0:
                        _plan_parts.append(f"{_label}：{_p['club']}で{_d}ヤード（グリーンオン）")
                    else:
                        _plan_parts.append(f"{_label}：{_p['club']}で{_d}ヤード（残り{_p['remain']}ヤード）")
                plan_text = "、".join(_plan_parts)
            else:
                plan_text = "なし"

            context = {
                "hole": hole, "par": par_num, "yard": TOTAL_DIST,
                "remaining": st.session_state.remaining,
                "target": target, "remaining_strokes": remaining_strokes,
"history_text": history_text,
                "next_club": next_club_name, "next_dist": next_club_dist,
                "hole_memo": hole_memo,
                "plan_text": plan_text,
            }

            with st.spinner("🤖 キャディが考え中..."):
                message = handle_voice_input(text, st.session_state.clubs, context)

            if message:
                st.session_state.last_caddy_message = message
                st.session_state.caddy_audio_bytes = None
                st.session_state.caddy_log.append({"q": text, "a": message})
                st.rerun()

        elif text == "":
            st.warning("音声を認識できませんでした。もう少しはっきり話してみてください。")

# ショット反映ボタン（キャッシュから表示）
if st.session_state.caddy_result_cache:
    parsed = st.session_state.caddy_result_cache
    st.markdown('<div id="voice-apply-anchor"></div>', unsafe_allow_html=True)
    if st.button("✅ この内容で反映する", key="btn_caddy_apply", use_container_width=True):
        club_name = parsed.get("club", "")
        dist_val  = parsed.get("dist", 0)
        result_s  = parsed.get("result", "FW")
        penalty = 0; green_on = (result_s == "Gオン"); remain_adjust = dist_val
        if result_s == "OB":     penalty = 1; remain_adjust = 0
        elif result_s == "池":   penalty = 1
        elif result_s == "赤杭": penalty = 1
        elif result_s == "ロスト": penalty = 2
        elif result_s == "空振り": remain_adjust = 0
        elif result_s == "プレ4": penalty = 2; remain_adjust = 0
        elif result_s == "プレ3": penalty = 1; remain_adjust = 0
        elif green_on: remain_adjust = st.session_state.remaining

        st.session_state.history.append({
            "club": club_name, "dist": dist_val,
            "result": result_s, "penalty": penalty, "green_on": green_on,
        })
        st.session_state.remaining = max(st.session_state.remaining - remain_adjust, 0)

        # ショット後のコメント生成
        try:
            import openai
            api_key = st.secrets.get("OPENAI_API_KEY", "")
            if api_key:
                client = openai.OpenAI(api_key=api_key)
                comment_prompt = f"あなたはゴルフキャディです。プレーヤーが{club_name}で{dist_val}ヤード打って{result_s}でした。残り距離は{st.session_state.remaining}ヤードです。ひとこと自然にコメントしてください（1〜2文、キャディらしい口調で）。"
                resp    = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role":"user","content":comment_prompt}], max_tokens=100)
                comment = resp.choices[0].message.content.strip()
                st.session_state.last_caddy_message = comment
                st.session_state.caddy_audio_bytes = None
        except: pass

        st.session_state.caddy_result_cache = None
        st.session_state.voice_text = ""
        st.rerun()


# =========================
# 最終スコア入力（app_v2と同一）
# =========================

st.markdown("<div class='section-divider' style='margin:8px 0;'></div>", unsafe_allow_html=True)
st.markdown('<div style="font-size:22px; font-weight:900; color:#1a2e44; margin-top:4px; margin-bottom:6px;">⛳ このホールの最終スコア</div>', unsafe_allow_html=True)

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
st.markdown(f"<div style='font-size:24px; font-weight:700; color:{scolor}; margin-bottom:4px;'>{current_score}打　{sname}</div>", unsafe_allow_html=True)

final_score = st.radio(
    "", list(range(1, 17)),
    index=max(current_score - 1, 0),
    key=f"final_score_input_{hole}",
    label_visibility="collapsed",
    horizontal=True,
)

_confirm_col, = st.columns([1])
with _confirm_col:
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
        "⚠️ ほんとにリセットしますか？</div>", unsafe_allow_html=True)
    yes_col, no_col, _ = st.columns([1, 1, 1])
    with yes_col:
        if st.button("はい", key="btn_reset_yes", use_container_width=True):
            st.session_state.history            = []
            st.session_state.green_on_flag      = False
            st.session_state.reset_confirm      = False
            st.session_state.adjust_plan        = False
            st.session_state.dismissed_triggers = set()
            st.session_state.last_caddy_message = ""
            st.session_state.caddy_log          = []
            st.session_state.pop("hole_select", None)
            st.session_state.remaining = st.session_state.course[1]["yard"]
            for h in st.session_state.course.keys():
                st.session_state.pop(f"actual_{h}", None)
                st.session_state.pop(f"final_score_input_{h}", None)
            st.rerun()
    with no_col:
        if st.button("いいえ", key="btn_reset_no", use_container_width=True):
            st.session_state.reset_confirm = False
            st.rerun()

# =========================
# クラブ設定（app_v2と同一）
# =========================

st.divider()

with st.expander("⚙️ クラブ設定", expanded=False):
    if st.button("クラブ設定を初期に戻す", use_container_width=True):
        st.session_state.clubs = CLUBS.copy()
        _localS.removeItem("golf_ai_clubs")
        for k in list(st.session_state.keys()):
            if k.startswith(("name_", "dist_", "miss_")):
                del st.session_state[k]
        st.rerun()

    st.markdown("<div style='font-size:20px; font-weight:700; color:#1d4ed8; margin-top:12px; margin-bottom:8px;'>この距離以下はグリーンを狙う</div>", unsafe_allow_html=True)
    st.session_state.green_on_threshold = st.slider(
        "この距離以下はグリーンを狙う", min_value=80, max_value=170, value=st.session_state.get("green_on_threshold", 130),
        step=5, format="%dy", label_visibility="collapsed", key="green_on_slider"
    )

    edited_clubs = []
    for i, c in enumerate(st.session_state.clubs):
        uid = f"{i}_{c['name']}"
        st.markdown("<div style='font-size:13px; font-weight:600; color:#4a5568; margin-top:6px; margin-bottom:-16px;'>クラブ</div>", unsafe_allow_html=True)
        name = st.selectbox("", CLUB_OPTIONS, index=CLUB_OPTIONS.index(c["name"]) if c["name"] in CLUB_OPTIONS else 0, key=f"name_{uid}")
        st.markdown("<div style='font-size:13px; font-weight:600; color:#4a5568; margin-top:4px; margin-bottom:-16px;'>飛距離（y）</div>", unsafe_allow_html=True)
        dist_options = list(range(300, 19, -10))
        dist = st.selectbox("", dist_options, index=dist_options.index(c["dist"]) if c["dist"] in dist_options else 0, key=f"dist_{i}")
        st.markdown("<div style='font-size:13px; font-weight:600; color:#4a5568; margin-top:4px; margin-bottom:-16px;'>得意距離（y）</div>", unsafe_allow_html=True)
        fav_options = ["未設定"] + list(range(300, 19, -10))
        favorite = st.selectbox("", fav_options, index=fav_options.index(c.get("favorite", 0)) if c.get("favorite", 0) in fav_options else 0, key=f"favorite_{i}")
        st.markdown("<div style='font-size:13px; font-weight:600; color:#4a5568; margin-top:4px; margin-bottom:-16px;'>ミス率</div>", unsafe_allow_html=True)
        miss = st.slider("", 0.0, 0.8, c["miss"], 0.01, key=f"miss_{i}")
        if name != "（未選択）":
            edited_clubs.append({"name": name, "dist": 0 if dist == "未設定" else dist, "miss": miss, "favorite": 0 if favorite == "未設定" else favorite})
        st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)

if st.button("✅ クラブ設定を更新", use_container_width=True):
    names = [c["name"] for c in edited_clubs]
    if len(names) != len(set(names)):
        st.error("同じクラブは1本しか選べません"); st.stop()
    if len(edited_clubs) > 13:
        st.error("クラブはパターを除いて13本までです"); st.stop()
    club_order = {"1W":1,"3W":2,"5W":3,"3U":4,"4U":5,"5U":6,"6U":7,"5I":8,"6I":9,"7I":10,"8I":11,"9I":12,"PW":13,"AW":14,"UW":15,"SW":16,"52°":17,"56°":18,"58°":19,"60°":20}
    st.session_state.clubs = sorted(edited_clubs, key=lambda x: club_order.get(x["name"], 999))
    _localS.setItem("golf_ai_clubs", st.session_state.clubs)
    st.session_state.pop("name_0", None)
    st.rerun()

# =========================
# コース設定（app_v2と同一＋メモ欄追加）
# =========================

if "course_expander_open" not in st.session_state:
    st.session_state.course_expander_open = False

with st.expander("⛳ コース設定", expanded=st.session_state.course_expander_open):
    preset_options = ["コースを選択"] + list(PRESET_COURSES.keys())
    st.markdown('<div id="preset-select-anchor"></div>', unsafe_allow_html=True)
    selected_preset = st.selectbox("プリセット選択", preset_options, key="preset_select", label_visibility="collapsed")
    if selected_preset != "コースを選択":
        st.markdown(
            f"<div style='font-size:18px; font-weight:700; color:#065f46; "
            f"background:#ecfdf5; border-left:4px solid #059669; border-radius:8px; "
            f"padding:8px 14px; margin:4px 0;'>⛳ {selected_preset}</div>",
            unsafe_allow_html=True)
        st.markdown('<div id="load-preset-anchor"></div>', unsafe_allow_html=True)
        if st.button("↓ コース情報を読み込む", key="btn_load_preset", use_container_width=True):
            preset = PRESET_COURSES[selected_preset]
            st.session_state.course = {
                h: {
                    "par": d["par"], "yard": d["yard"], "memo": d.get("memo", ""),
                    "elevation": d.get("elevation", 0),
                    "green_side_bunkers": d.get("green_side_bunkers", []),
                    "green": d.get("green", {}),
                }
                for h, d in preset["holes"].items()
            }
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
                st.session_state[f"memo_{h}"] = data.get("memo", "")
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
        with c1: st.markdown(f"<div style='font-size:16px; font-weight:700; color:#2563eb; padding-top:10px;'>{h}番ホール</div>", unsafe_allow_html=True)
        with c2: st.markdown("<div style='font-size:22px; font-weight:700; color:#4a5568; padding-top:10px;'>Par</div>", unsafe_allow_html=True)
        with c3:
            par_idx = par_options.index(cur_par) if cur_par in par_options else 0
            par_sel = st.selectbox("", par_options, index=par_idx, key=f"par_{h}", label_visibility="collapsed")
            par = cur_par if par_sel == "Par" else int(par_sel)
        with c4: st.markdown("<div style='font-size:17px; font-weight:600; color:#4a5568; padding-top:12px;'>距離(y)</div>", unsafe_allow_html=True)
        with c5:
            yard = st.number_input("", 50, 700, cur_yard, key=f"yard_{h}", label_visibility="collapsed")

        memo = st.text_area(
            f"{h}番 メモ", value=cur_memo, key=f"memo_{h}", height=68,
            placeholder="例：右OBに注意。グリーンは手前から攻めること。",
            label_visibility="visible")
        edited_course[h] = {"par": par, "yard": yard, "memo": memo}

    if st.button("✅ コース設定を保存", key="btn_save_course", use_container_width=True):
        for h, data in edited_course.items():
            st.session_state.course[h].update(data)
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
        "</div>", unsafe_allow_html=True)
    if st.secrets.get("OPENAI_API_KEY", ""):
        st.success("✅ APIキーは設定済みです")
    else:
        st.warning("⚠️ APIキーが未設定です。Streamlit CloudのSecretsに設定してください。")
