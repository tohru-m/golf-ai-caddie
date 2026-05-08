import streamlit as st
 
st.markdown("""
<style>
 
/* =========================
   スマホ向け共通スタイル
========================= */
 
/* ラベル */
.ui-label {
    font-size: 18px;
    font-weight: bold;
    display: block;
    margin-bottom: 6px;
    margin-top: 10px;
}
 
.ui-label-small {
    font-size: 15px;
    font-weight: normal;
    display: block;
    margin-bottom: 4px;
}
 
.ui-label-fixed {
    font-size: 16px;
    font-weight: bold;
    display: block;
    margin-bottom: 6px;
}
 
/* ボタンを大きく・押しやすく */
div[data-testid="stFormSubmitButton"] > button {
    height: 48px;
    font-size: 16px;
    width: 100%;
    padding-top: 0px !important;
    padding-bottom: 0px !important;
}
 
div[data-testid="stButton"] > button {
    height: 48px;
    font-size: 16px;
    width: 100%;
}
 
/* セレクトボックスの幅制限を解除 */
div[data-testid="stSelectbox"] {
    max-width: 100%;
}
 
/* 数値入力も大きく */
div[data-testid="stNumberInput"] input {
    font-size: 18px;
    height: 48px;
}
 
div[data-testid="stCheckbox"] label {
    font-size: 16px;
}
 
div[data-testid="stExpander"] summary {
    font-size: 16px;
}
 
.ui-row {
    display: block;
    margin-bottom: 10px;
}
 
.ui-label-large {
    font-size: 22px;
    font-weight: bold;
    display: block;
    margin-bottom: 8px;
}
 
</style>
""", unsafe_allow_html=True)
 
TOTAL_DIST = 350
 
CLUBS = [
    {"name": "1W", "dist": 200, "miss": 0.25, "favorite": 0},
    {"name": "4U", "dist": 180, "miss": 0.25, "favorite": 0},
    {"name": "5U", "dist": 170, "miss": 0.25, "favorite": 0},
    {"name": "6I", "dist": 160, "miss": 0.20, "favorite": 0},
    {"name": "7I", "dist": 150, "miss": 0.20, "favorite": 0},
    {"name": "8I", "dist": 140, "miss": 0.18, "favorite": 140},
    {"name": "9I", "dist": 130, "miss": 0.15, "favorite": 130},
    {"name": "PW", "dist": 120, "miss": 0.15, "favorite": 120},
    {"name": "UW", "dist": 110, "miss": 0.15, "favorite": 110},
    {"name": "52°", "dist": 100, "miss": 0.15, "favorite": 100},
    {"name": "56°", "dist": 80, "miss": 0.15, "favorite": 80},
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
 
COURSE = {
    1: {"par": 4, "yard": 350},
    2: {"par": 3, "yard": 160},
    3: {"par": 5, "yard": 520},
    4: {"par": 4, "yard": 380},
    5: {"par": 4, "yard": 360},
    6: {"par": 3, "yard": 170},
    7: {"par": 5, "yard": 500},
    8: {"par": 4, "yard": 390},
    9: {"par": 4, "yard": 370},
}
 
# =========================
# 有効クラブ取得
# =========================
 
def get_valid_clubs():
    return [
        c for c in st.session_state.clubs
        if c["dist"] > 0 and c["name"] != "なし"
    ]
 
# ★修正①：holeを引数として受け取る
def choose_club(remaining, shots_left, is_first_shot, par_num, hole):
 
    valid_clubs = get_valid_clubs()
 
    if not valid_clubs:
        return {"name": "なし", "dist": 0, "miss": 1.0}
 
    danger_scores = {
        "バンカー": 50,
        "池": 120,
        "OBゾーン": 300,
        "谷越え": 80,
        "ドッグレッグ": 40
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
                danger_type = st.session_state.get(f"danger_type_{hole}_{i}", "未入力")
                danger_start = st.session_state.get(f"danger_start_{hole}_{i}", 0)
                danger_end = st.session_state.get(f"danger_end_{hole}_{i}", 0)
                if (
                    danger_type != "未入力"
                    and club["dist"] >= danger_start
                    and club["dist"] <= danger_end
                ):
                    danger_hit = True
            if not danger_hit:
                safe_clubs.append(club)
 
        if safe_clubs:
            return max(safe_clubs, key=lambda c: c["dist"])
 
        return max(valid_clubs, key=lambda c: c["dist"])
 
    best = None
    best_score = 999
 
    if shots_left == 1:
        reachable = [c for c in valid_clubs if c["dist"] >= remaining]
        if reachable:
            return min(reachable, key=lambda c: c["dist"])
        return max(valid_clubs, key=lambda c: c["dist"])
 
    if shots_left > 1:
        favorite_targets = [
            c["favorite"] for c in valid_clubs if c.get("favorite", 0) > 0
        ]
        if favorite_targets:
            target = remaining - min(favorite_targets)
        else:
            target = remaining / shots_left
    else:
        target = remaining
 
    if par_num == 5 and not is_first_shot and shots_left >= 2 and remaining > 180:
        target = remaining * 0.7
 
    for club in valid_clubs:
 
        favorite = club.get("favorite", 0)
 
        danger_penalty = 0
        for i in range(1, 3):
            danger_type = st.session_state.get(f"danger_type_{hole}_{i}", "未入力")
            danger_start = st.session_state.get(f"danger_start_{hole}_{i}", 0)
            danger_end = st.session_state.get(f"danger_end_{hole}_{i}", 0)
            if (
                danger_type != "未入力"
                and club["dist"] >= danger_start
                and club["dist"] <= danger_end
            ):
                danger_penalty += danger_scores.get(danger_type, 0)
 
        if club["name"] == "1W":
            continue
 
        if shots_left > 1 and club["dist"] >= remaining:
            continue
 
        if shots_left == 2:
            longest = max(c["dist"] for c in valid_clubs)
            if remaining - club["dist"] > longest:
                continue
 
        good = club["dist"]
        miss = club["dist"] * 0.6
        miss_rate = club["miss"]
 
        expected_after = (
            (1 - miss_rate) * (remaining - good)
            + miss_rate * (remaining - miss)
        )
 
        favorite_penalty = 0
        if favorite > 0:
            favorite_penalty = abs(expected_after - favorite)
 
        distance_balance_penalty = 0
        if shots_left > 1:
            if expected_after < club["dist"] * 0.5:
                distance_balance_penalty = 80
 
        # ★修正②：scoreを必ず計算する
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
 
    if shots_left == 1:
        reachable = [c for c in valid_clubs if c["dist"] >= remaining]
        if reachable:
            return min(reachable, key=lambda c: c["dist"])
        else:
            return max(valid_clubs, key=lambda c: c["dist"])
 
    if best is None:
        reachable = [c for c in valid_clubs if c["dist"] >= remaining]
        if reachable:
            best = min(reachable, key=lambda c: c["dist"])
        else:
            best = max(valid_clubs, key=lambda c: c["dist"])
 
    return best
 
def find_replacement_club(remaining):
    candidates = [c for c in st.session_state.clubs if c["dist"] >= remaining]
    if candidates:
        return min(candidates, key=lambda x: x["dist"])
    return None
 
# ★修正①：holeを引数として受け取る
def plan(total_dist, strokes, used, par_num, hole):
    result = []
    remaining = total_dist
 
    for i in range(strokes):
        shots_left = strokes - i
        is_first_shot = (used + i == 0)
 
        club = choose_club(remaining, shots_left, is_first_shot, par_num, hole)
 
        if len(result) == strokes - 1:
            reachable = [c for c in st.session_state.clubs if c["dist"] >= remaining]
            if reachable:
                club = min(reachable, key=lambda c: c["dist"])
 
        shot_dist = club["dist"]
 
        result.append({
            "shot": i + 1,
            "club": club["name"],
            "dist": shot_dist,
            "remain": max(remaining - shot_dist, 0),
            "before": remaining
        })
 
        remaining = max(remaining - shot_dist, 0)
 
    return result
 
 
# =========================
# アプリ本体
# =========================
 
st.title("⛳ AIキャディ")
 
st.markdown("### 🎯 ラウンド目標")
 
# ★スマホ向け：縦並び
st.markdown('<div class="ui-label-fixed">何打で回りたい？</div>', unsafe_allow_html=True)
 
target_score = st.selectbox(
    "",
    list(range(60, 151)),
    index=40,
    key="target_score",
    label_visibility="collapsed"
)
 
if "course" not in st.session_state:
    st.session_state.course = {
        1: {"par": 5, "yard": 425},
        2: {"par": 4, "yard": 276},
        3: {"par": 3, "yard": 180},
        4: {"par": 5, "yard": 438},
        5: {"par": 4, "yard": 316},
        6: {"par": 4, "yard": 425},
        7: {"par": 3, "yard": 138},
        8: {"par": 4, "yard": 424},
        9: {"par": 4, "yard": 388},
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
 
# ホール難易度計算
hole_difficulty = {}
 
for h, data in st.session_state.course.items():
    yard = data["yard"]
    par = data["par"]
    score = yard / 100
    if par == 5:
        score -= 2
        score -= 1
    elif par == 3:
        score += 1
    if par == 4 and yard > 380:
        score += 1.5
    hole_difficulty[h] = score
 
total_par = sum(h["par"] for h in st.session_state.course.values())
bogey_base = total_par + 18
sorted_holes = sorted(hole_difficulty.items(), key=lambda x: x[1])
 
hole_targets = {}
average_diff = (target_score - total_par) / 18
base_diff = int(average_diff)
 
for h, data in st.session_state.course.items():
    hole_targets[h] = data["par"] + base_diff
 
current_total = sum(hole_targets.values())
diff_total = target_score - current_total
 
if diff_total < 0:
    easier_holes = sorted_holes
    idx = 0
    while diff_total < 0 and idx < len(easier_holes):
        h = easier_holes[idx][0]
        if hole_targets[h] > st.session_state.course[h]["par"]:
            hole_targets[h] -= 1
            diff_total += 1
        else:
            idx += 1
 
elif diff_total > 0:
    harder_holes = sorted_holes[::-1]
    idx = 0
    while diff_total > 0 and idx < len(harder_holes):
        h = harder_holes[idx][0]
        hole_targets[h] += 1
        diff_total -= 1
        idx += 1
 
# =========================
# ホール一覧表示関数
# =========================
 
def render_score_table(holes):
 
    h1, h2, h3, h4, h5 = st.columns([0.8, 0.8, 1.5, 1.0, 0.8])
    with h1:
        st.markdown("**Hole**")
    with h2:
        st.markdown("**Par**")
    with h3:
        st.markdown("**戦略**")
    with h4:
        st.markdown("**実績**")
    with h5:
        st.markdown("**乖離**")
 
    for h in holes:
 
        row1, row2, row3, row4, row5 = st.columns([0.8, 0.8, 1.5, 1.0, 0.8])
        par = st.session_state.course[h]["par"]
        target = hole_targets[h]
        diff = target - par
 
        if diff <= -1:
            mark = "★"; color = "#8B0000"; score_name = "birdie"
        elif diff == 0:
            mark = "◎"; color = "#FF0000"; score_name = "par"
        elif diff == 1:
            mark = "○"; color = "#0070FF"; score_name = "bog"
        elif diff == 2:
            mark = "△"; color = "#008000"; score_name = "dbl"
        else:
            mark = "▼"; color = "#000000"; score_name = "tri"
 
        strategy_html = (
            f"<span style='color:{color}; font-weight:bold;'>"
            f"{mark} {target} {score_name}</span>"
        )
 
        actual = st.session_state.get(f"actual_{h}", "")
 
        with row4:
            st.markdown(f"<div style='font-size:15px'>{actual}</div>", unsafe_allow_html=True)
 
        deviation = ""
        if actual != "":
            gap = target - int(actual)
            deviation = f"+{gap}" if gap > 0 else str(gap)
 
        with row1:
            st.markdown(f"<div style='font-size:15px'>{h}</div>", unsafe_allow_html=True)
        with row2:
            st.markdown(f"<div style='font-size:15px'>{par}</div>", unsafe_allow_html=True)
        with row3:
            st.markdown(f"<div style='font-size:15px'>{strategy_html}</div>", unsafe_allow_html=True)
        with row5:
            st.markdown(f"<div style='font-size:15px'>{deviation}</div>", unsafe_allow_html=True)
 
with st.expander("🧠 ラウンドスコア戦略", expanded=False):
    holes = sorted(st.session_state.course.keys())
    front9 = holes[:9]
    back9 = holes[9:]
    left_block, right_block = st.columns(2)
    with left_block:
        render_score_table(front9)
    with right_block:
        render_score_table(back9)
 
st.markdown("<div style='margin-top:12px;'></div>", unsafe_allow_html=True)
 
# ★スマホ向け：ホール選択を縦並びに
st.markdown('<div class="ui-label">ホールを選択</div>', unsafe_allow_html=True)
 
hole = st.selectbox(
    "",
    list(st.session_state.course.keys()),
    key="hole_select",
    label_visibility="collapsed"
)
 
TOTAL_DIST = st.session_state.course[hole]["yard"]
par_num = st.session_state.course[hole]["par"]
 
st.markdown(
    f"<h3>⛳ {hole}番ホール <span style='color:red'>{TOTAL_DIST}y / Par {par_num}</span></h3>",
    unsafe_allow_html=True
)
 
if "prev_hole" not in st.session_state:
    st.session_state.prev_hole = hole
 
if hole != st.session_state.prev_hole:
    st.session_state.remaining = st.session_state.course[hole]["yard"]
    st.session_state.history = []
    st.session_state.prev_hole = hole
 
if "remaining" not in st.session_state:
    st.session_state.remaining = TOTAL_DIST
 
if "history" not in st.session_state:
    st.session_state.history = []
 
# =========================
# AI推奨打数
# =========================
 
recommended_score = hole_targets[hole]
diff = recommended_score - par_num
 
if diff <= -1:
    score_name = "バーディ"; recommend_color = "#8B0000"
elif diff == 0:
    score_name = "パー"; recommend_color = "#FF0000"
elif diff == 1:
    score_name = "ボギー"; recommend_color = "#0070FF"
elif diff == 2:
    score_name = "ダブルボギー"; recommend_color = "#008000"
else:
    score_name = "トリプル以上"; recommend_color = "#000000"
 
# ★スマホ向け：縦並び
st.markdown(
    f"""
    <div class='ui-label-fixed'>
    何打で上がる計画？<br>
    <span style='color:{recommend_color}; font-weight:bold; font-size:14px;'>
    （AI推奨：{recommended_score}打 {score_name}）
    </span>
    </div>
    """,
    unsafe_allow_html=True
)
 
options = list(range(1, 16))
default_index = options.index(recommended_score)
 
target = st.selectbox(
    "",
    options,
    index=default_index,
    key=f"target_select_{hole}",
    label_visibility="collapsed"
)
 
# ★スマホ向け：パット数も縦並びに
st.markdown('<div class="ui-label">パット数は何回？</div>', unsafe_allow_html=True)
 
putts = st.selectbox(
    "",
    [1, 2, 3, 4, 5],
    index=1,
    key="putt_select",
    label_visibility="collapsed"
)
 
shot_strokes = target - putts
 
st.markdown(
    f"<div class='ui-label-small'>ショット数：{shot_strokes}回 ＋ パット：{putts}回</div>",
    unsafe_allow_html=True
)
 
min_strokes = par_num - 1
 
if target < min_strokes:
    st.error("それは無謀です！")
    st.stop()
 
# =========================
# 要注意エリア設定
# =========================
 
st.markdown("<div style='margin-top:8px;'></div>", unsafe_allow_html=True)
 
use_danger = st.checkbox("⚠️ 要注意エリアを設定", key=f"use_danger_{hole}")
 
if not use_danger:
    for i in range(1, 3):
        st.session_state[f"danger_type_{hole}_{i}"] = "未入力"
        st.session_state[f"danger_start_{hole}_{i}"] = 0
        st.session_state[f"danger_end_{hole}_{i}"] = 0
 
if use_danger:
 
    st.markdown('<div class="ui-label">⚠️ 要注意エリア</div>', unsafe_allow_html=True)
 
    danger_options = ["未入力", "バンカー", "池", "OBゾーン", "谷越え", "ドッグレッグ"]
    yard_options = ["未入力", 0, 50, 100, 150, 170, 200, 230, 250, 300, 350, 400, 450, 500]
    default_danger = ["未入力", "未入力"]
    default_start = [0, 0]
    default_end = [0, 0]
 
    for i in range(1, 3):
 
        st.markdown(f"**エリア {i}**")
 
        # ★スマホ向け：種類を縦、距離を2列に
        st.selectbox(
            "種類",
            danger_options,
            index=danger_options.index(default_danger[i-1]),
            key=f"danger_type_{hole}_{i}"
        )
 
        col_from, col_to = st.columns(2)
 
        with col_from:
            st.selectbox(
                "開始（ヤード）",
                yard_options,
                key=f"danger_start_{hole}_{i}",
                index=yard_options.index(default_start[i-1])
            )
 
        with col_to:
            st.selectbox(
                "終了（ヤード）",
                yard_options,
                index=yard_options.index(default_end[i-1]),
                key=f"danger_end_{hole}_{i}"
            )
 
        st.markdown("---")
 
# =========================
# 戦略表示
# =========================
 
st.markdown('<div class="ui-label">📋 この戦略でいこう！</div>', unsafe_allow_html=True)
 
current_shot = 1
 
for h in st.session_state.history:
 
    result_text = ""
    if h.get("result") == "OB":
        result_text = " → OB（1打罰）"
    elif h.get("result") == "池":
        result_text = " → 池（1打罰）"
    elif h.get("result") == "赤杭":
        result_text = " → 赤杭（1打罰）"
    elif h.get("result") == "ロスト":
        result_text = " → ロスト（2打罰）"
    elif h.get("result") == "空振り":
        result_text = " → 空振り"
 
    st.markdown(
        f"<div style='font-size:18px; color:#007bff; padding:4px 0;'>"
        f"{current_shot}打目（実績）：{h['club']}（{h['dist']}y）{result_text}"
        f"</div>",
        unsafe_allow_html=True
    )
 
    current_shot += 1
    current_shot += h.get("penalty", 0)
 
# 使用打数計算
used = 0
for h in st.session_state.history:
    used += 1
    used += h.get("penalty", 0)
 
remaining_strokes = shot_strokes - used
 
if remaining_strokes > 0:
 
    plan_data = plan(st.session_state.remaining, remaining_strokes, used, par_num, hole)
 
    for i, p in enumerate(plan_data):
 
        display_club = p["club"]
        display_dist = min(p["dist"], p["before"])
 
        if i == len(plan_data) - 1:
            if display_dist >= p["before"]:
                msg = f"グリーンオン → パット {putts}回"
            else:
                msg = f"⚠️ 届かない（あと{p['before'] - display_dist}y不足）"
        else:
            msg = f"残り{max(p['before'] - display_dist, 0)}y"
 
        st.markdown(
            f"<div style='font-size:18px; padding:4px 0;'>"
            f"{used + p['shot']}打目：{display_club}（{display_dist}y） → {msg}"
            f"</div>",
            unsafe_allow_html=True
        )
 
    if plan_data and st.session_state.remaining <= 5:
        st.markdown(
            f"<div style='font-size:18px;'>→ パット {putts}回</div>",
            unsafe_allow_html=True
        )
 
elif remaining_strokes == 0:
    if st.session_state.remaining <= 5:
        st.write("→ グリーンオン（パットのみ）")
    else:
        st.error("⚠️ この計画では届きません")
 
else:
    st.error("ショット数が不足しています")
 
# =========================
# ショット結果入力フォーム
# =========================
 
with st.form("shot_form"):
 
    st.markdown('<div class="ui-label">🎯 ショットの結果は？</div>', unsafe_allow_html=True)
 
    # ★スマホ向け：入力項目を縦並びに
    st.markdown('<div class="ui-label-small">使ったクラブ</div>', unsafe_allow_html=True)
    actual_club = st.selectbox(
        "",
        [c["name"] for c in CLUBS],
        label_visibility="collapsed"
    )
 
    st.markdown('<div class="ui-label-small">飛距離（ヤード）</div>', unsafe_allow_html=True)
    actual_dist = st.number_input(
        "",
        0, 300, 100,
        label_visibility="collapsed"
    )
 
    st.markdown('<div class="ui-label-small">結果</div>', unsafe_allow_html=True)
    shot_result = st.selectbox(
        "",
        ["通常", "OB", "池", "赤杭", "ロスト", "空振り"],
        label_visibility="collapsed"
    )
 
    # ★スマホ向け：ボタンを横並び2列
    btn_col1, btn_col2 = st.columns(2)
 
    with btn_col1:
        submitted = st.form_submit_button("✅ 反映", use_container_width=True)
 
    with btn_col2:
        undo = st.form_submit_button("↩️ 取消", use_container_width=True)
 
    if submitted:
 
        penalty = 0
        remain_adjust = actual_dist
 
        if shot_result == "OB":
            penalty = 1
            remain_adjust = 0
        elif shot_result == "池":
            penalty = 1
            remain_adjust = actual_dist
        elif shot_result == "赤杭":
            penalty = 1
            remain_adjust = actual_dist
        elif shot_result == "ロスト":
            penalty = 2
            remain_adjust = actual_dist
        elif shot_result == "空振り":
            remain_adjust = 0
 
        st.session_state.history.append({
            "club": actual_club,
            "dist": actual_dist,
            "result": shot_result,
            "penalty": penalty
        })
 
        st.session_state.remaining -= remain_adjust
 
        if st.session_state.remaining < 0:
            st.session_state.remaining = 0
 
        st.rerun()
 
    if undo:
        if len(st.session_state.history) > 0:
            last_shot = st.session_state.history.pop()
            actual_back = last_shot["dist"]
            if last_shot["result"] == "OB":
                actual_back = 0
            elif last_shot["result"] == "空振り":
                actual_back = 0
            st.session_state.remaining += actual_back
            st.rerun()
 
# =========================
# 残り距離表示
# =========================
 
st.markdown(
    f"""
    <div style="text-align:left; margin-top:12px; font-size:20px;">
        現在の残り距離
        <span style="color:#2E8B57; font-weight:bold; margin-left:10px;">
            {st.session_state.remaining}y
        </span>
    </div>
    """,
    unsafe_allow_html=True
)
 
st.markdown("<hr style='margin-top:8px; margin-bottom:8px;'>", unsafe_allow_html=True)
 
# =========================
# 最終スコア入力
# =========================
 
st.markdown('<div class="ui-label">🏁 このホールの最終スコア</div>', unsafe_allow_html=True)
 
def update_actual_score():
    st.session_state[f"actual_{hole}"] = int(
        st.session_state[f"final_score_input_{hole}"]
    )
 
final_score = st.selectbox(
    "",
    list(range(1, 17)),
    index=max(int(st.session_state.get(f"actual_{hole}", 1)) - 1, 0),
    key=f"final_score_input_{hole}",
    on_change=update_actual_score,
    label_visibility="collapsed"
)
 
# =========================
# クラブ設定
# =========================
 
st.divider()
 
with st.expander("⚙️ クラブ設定", expanded=False):
 
    if st.button("クラブ設定を初期に戻す"):
        st.session_state.clubs = CLUBS.copy()
        for k in list(st.session_state.keys()):
            if k.startswith("name_") or k.startswith("dist_") or k.startswith("miss_"):
                del st.session_state[k]
        st.rerun()
 
    col1, col2, col3, col4 = st.columns([1, 1, 2, 1])
    with col1:
        st.markdown("**クラブ**")
    with col2:
        st.markdown("**距離(y)**")
    with col3:
        st.markdown("**ミス率**")
    with col4:
        st.markdown("**得意**")
 
    edited_clubs = []
 
    for i, c in enumerate(st.session_state.clubs):
 
        unique_id = f"{i}_{c['name']}"
        col1, col2, col3, col4 = st.columns([1, 1, 2, 1])
 
        with col1:
            name = st.selectbox(
                "",
                CLUB_OPTIONS,
                index=CLUB_OPTIONS.index(c["name"]) if c["name"] in CLUB_OPTIONS else 0,
                key=f"name_{unique_id}"
            )
 
        with col2:
            dist_options = list(range(300, 19, -10))
            dist = st.selectbox(
                "",
                dist_options,
                index=dist_options.index(c["dist"]) if c["dist"] in dist_options else 0,
                key=f"dist_{i}"
            )
 
        with col3:
            miss = st.slider("", 0.0, 0.8, c["miss"], 0.01, key=f"miss_{i}")
 
        with col4:
            favorite_options = ["未設定"] + list(range(300, 19, -10))
            favorite = st.selectbox(
                "",
                favorite_options,
                index=favorite_options.index(
                    c.get("favorite", 0)
                ) if c.get("favorite", 0) in favorite_options else 0,
                key=f"favorite_{i}"
            )
 
            if name != "（未選択）":
                edited_clubs.append({
                    "name": name,
                    "dist": 0 if dist == "未設定" else dist,
                    "miss": miss,
                    "favorite": 0 if favorite == "未設定" else favorite
                })
 
if st.button("クラブ設定を更新"):
 
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
        "52°": 17, "56°": 18, "58°": 19, "60°": 20
    }
 
    st.session_state.clubs = sorted(
        edited_clubs,
        key=lambda x: club_order.get(x["name"], 999)
    )
 
    st.session_state.pop("name_0", None)
    st.rerun()
 
# =========================
# コース設定
# =========================
 
with st.expander("⛳ コース設定", expanded=False):
 
    st.markdown("### コース情報")
 
    course_col1, course_col2 = st.columns([3, 1])
 
    with course_col1:
        course_name = st.text_input(
            "コース名",
            value=st.session_state.get("course_name", ""),
            placeholder="例：宝塚ゴルフ倶楽部"
        )
 
    with course_col2:
        tee_options = ["BACK", "REG", "FRO", "LADIES"]
        tee_type = st.selectbox(
            "ティー",
            tee_options,
            index=tee_options.index(st.session_state.get("tee_type", "REG"))
        )
 
    st.divider()
 
    edited_course = {}
    holes = list(st.session_state.course.keys())
    left_holes = holes[:9]
    right_holes = holes[9:]
    col_left, col_right = st.columns(2)
 
    def render_holes(holes_subset):
        for h in holes_subset:
            c1, c2, c3, c4, c5 = st.columns([0.8, 0.6, 1, 0.6, 1])
            with c1:
                st.markdown(f"**{h}番**")
            with c2:
                st.markdown("Par")
            with c3:
                par = st.number_input(
                    "", 3, 6,
                    st.session_state.course[h]["par"],
                    key=f"par_{h}",
                    label_visibility="collapsed"
                )
            with c4:
                st.markdown("Yard")
            with c5:
                yard = st.number_input(
                    "", 50, 700,
                    st.session_state.course[h]["yard"],
                    key=f"yard_{h}",
                    label_visibility="collapsed"
                )
            edited_course[h] = {"par": par, "yard": yard}
 
    with col_left:
        render_holes(left_holes)
    with col_right:
        render_holes(right_holes)
 
if st.button("コース設定を更新"):
    st.session_state.course = edited_course
    st.session_state.course_name = course_name
    st.session_state.tee_type = tee_type
    st.rerun()
