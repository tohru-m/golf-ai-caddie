import streamlit as st

st.markdown("""
<style>

/* =========================
   共通ラベル
========================= */

.ui-label {
    font-size: 20px;
    font-weight: bold;
    display: flex;
    align-items: center;
    height: 34px;
    margin: 0;
}

/* 小ラベル */

.ui-label-small {
    font-size: 16px;
    font-weight: normal;
    display: flex;
    align-items: center;
    height: 38px;
    margin: 0;
}

div[data-testid="stFormSubmitButton"] > button {
    height: 38px;
    padding-top: 0px !important;
    padding-bottom: 0px !important;
}

.ui-row {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 10px;
}

.ui-label-fixed {
    font-size: 20px;
    font-weight: bold;
    min-width: 260px;
}

div[data-testid="stSelectbox"] {
    max-width: 90px;
}

/* 大ラベル */

.ui-label-large {
    font-size: 28px;
    font-weight: bold;
    display: flex;
    align-items: center;
    height: 44px;
    margin: 0;
}

/* 小さいプルダウン */

.ui-select-small {
    max-width: 90px;
}

/* 中くらいプルダウン */

.ui-select-medium {
    max-width: 140px;
}

/* 大きいプルダウン */

.ui-select-large {
    max-width: 220px;
}

</style>
""", unsafe_allow_html=True)

TOTAL_DIST = 350

CLUBS = [
    {"name": "1W", "dist": 200, "miss": 0.25, "favorite": 0},
    {"name": "5W", "dist": 180, "miss": 0.25, "favorite": 0},
    {"name": "4U", "dist": 170, "miss": 0.25, "favorite": 0},
    {"name": "5U", "dist": 160, "miss": 0.25, "favorite": 0},
    {"name": "6I", "dist": 150, "miss": 0.20, "favorite": 0},
    {"name": "7I", "dist": 145, "miss": 0.20, "favorite": 0},
    {"name": "8I", "dist": 135, "miss": 0.18, "favorite": 140},
    {"name": "9I", "dist": 125, "miss": 0.15, "favorite": 130},
    {"name": "PW", "dist": 115, "miss": 0.15, "favorite": 120},
    {"name": "52°", "dist": 95, "miss": 0.15, "favorite": 100},
    {"name": "56°", "dist": 85, "miss": 0.15, "favorite": 90},
    {"name": "58°", "dist": 75, "miss": 0.15, "favorite": 80},
    {"name": "60°", "dist": 65, "miss": 0.15, "favorite": 70},
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

def choose_club(remaining, shots_left, is_first_shot, par_num):

# =========================
# 有効クラブ抽出
# =========================

    valid_clubs = get_valid_clubs()

    if not valid_clubs:
        return {"name": "なし", "dist": 0, "miss": 1.0}
    
 # =========================
# 危険エリア危険度
# =========================

    danger_scores = {
        "バンカー": 50,
        "池": 120,
        "OBゾーン": 300,
        "谷越え": 80,
        "ドッグレッグ": 40
    }   
    

# =========================
# 1打目ロジック
# =========================

    if is_first_shot:

        # Par3や最後の1打はグリーンを狙う
        if shots_left == 1:

            reachable = [
                c for c in valid_clubs
                if c["dist"] >= remaining
            ]

            if reachable:
                return min(
                    reachable,
                    key=lambda c: c["dist"]
                )

        # Par4・Par5は基本刻む
        if remaining <= 220:

            safe_clubs = [
                c for c in valid_clubs
                if c["dist"] < remaining
            ]

            if safe_clubs:
                return min(
                    safe_clubs,
                    key=lambda c: abs(c["dist"] - remaining)
                )

        safe_clubs = []

        for club in valid_clubs:

            danger_hit = False

            for i in range(1, 3):

                danger_type = st.session_state.get(
                    f"danger_type_{hole}_{i}",
                    "未入力"
                )

                danger_start = st.session_state.get(
                    f"danger_start_{hole}_{i}",
                    0
                )

                danger_end = st.session_state.get(
                    f"danger_end_{hole}_{i}",
                    0
                )

                if (
                    danger_type != "未入力"
                    and club["dist"] >= danger_start
                    and club["dist"] <= danger_end
                ):
                    danger_hit = True

            if not danger_hit:
                safe_clubs.append(club)

        if safe_clubs:

            return max(
                safe_clubs,
                key=lambda c: c["dist"]
            )

        return max(
            valid_clubs,
            key=lambda c: c["dist"]
        )

# =========================
# 通常ショットロジック
# =========================

    best = None
    best_score = 999

    # 最後の1打は「届く最短クラブ」
    if shots_left == 1:

        reachable = [
            c for c in valid_clubs
            if c["dist"] >= remaining
        ]

        if reachable:
            return min(
                reachable,
                key=lambda c: c["dist"]
            )

        # どれも届かない場合
        return max(
            valid_clubs,
            key=lambda c: c["dist"]
        )

# =========================
# 目標距離計算
# =========================

    if shots_left > 1:

        favorite_targets = [
            c["favorite"]
            for c in valid_clubs
            if c.get("favorite", 0) > 0
        ]

        if favorite_targets:
            target = remaining - min(favorite_targets)
        else:
            target = remaining / shots_left

    else:
        target = remaining

    if par_num == 5 and not is_first_shot and shots_left >= 2 and remaining > 180:
        target = remaining * 0.7   # ←ここがポイント（強気に距離を取りに行く）

# =========================
# クラブ評価ループ
# =========================

    for club in valid_clubs:

        favorite = club.get("favorite", 0)

        # =========================
        # 危険エリア判定
        # =========================

        danger_penalty = 0

        for i in range(1, 3):

            danger_type = st.session_state.get(
                f"danger_type_{hole}_{i}",
                "未入力"
            )

            danger_start = st.session_state.get(
                f"danger_start_{hole}_{i}",
                0
            )

            danger_end = st.session_state.get(
                f"danger_end_{hole}_{i}",
                0
            )

            # 危険範囲に入るか判定
            if (
                danger_type != "未入力"
                and club["dist"] >= danger_start
                and club["dist"] <= danger_end
            ):

                danger_penalty += danger_scores.get(
                    danger_type,
                    0
                )


        if club["name"] == "1W":
            continue

        # 途中段階では基本的にグリーンオンを狙わない
        
        if shots_left > 1 and club["dist"] >= remaining:
            continue

# 最後に届かなくなるクラブは禁止
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

        # 次ショットが極端に短くなるのを嫌う
        if shots_left > 1:

            next_distance = expected_after
    
            if next_distance < club["dist"] * 0.5:
                distance_balance_penalty = 80

        if shots_left > 1:
            next_best = min(
                abs(expected_after - c["dist"])
                for c in valid_clubs
            )

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

    # 最後の1打は必ず届くクラブ
    if shots_left == 1:

        reachable = [
            c for c in valid_clubs
            if c["dist"] >= remaining
        ]

        if reachable:
            return min(
                reachable,
                key=lambda c: c["dist"]
            )

        else:
            return max(
                valid_clubs,
                key=lambda c: c["dist"]
            )

    # 通常時
    if best is None:

        reachable = [
            c for c in valid_clubs
            if c["dist"] >= remaining
        ]

        if reachable:
            best = min(
                reachable,
                key=lambda c: c["dist"]
            )

        else:
            best = max(
                valid_clubs,
                key=lambda c: c["dist"]
            )

    return best

def find_replacement_club(remaining):
    candidates = [c for c in st.session_state.clubs if c["dist"] >= remaining]

    if candidates:
        return min(candidates, key=lambda x: x["dist"])

    return None

def plan(total_dist, strokes, used, par_num):
    result = []
    remaining = total_dist

    for i in range(strokes):
        shots_left = strokes - i

        print("shots_left =", shots_left)
        print("remaining =", remaining)

        # 1打目かどうか
        is_first_shot = (used + i == 0)

        # クラブ選択
        club = choose_club(
            remaining, 
            shots_left, 
            is_first_shot, 
            par_num)

        # 最後の1打は必ず届くクラブ
        if len(result) == strokes - 1:

            reachable = [
                c for c in st.session_state.clubs
                if c["dist"] >= remaining
            ]

            if reachable:
                club = min(
                    reachable,
                    key=lambda c: c["dist"]
                )

        shot_dist = club["dist"]

        result.append({
            "shot": i + 1,
            "club": club["name"],
            "dist": shot_dist,
            "remain": max(remaining - shot_dist, 0),
            "before": remaining
        })

        remaining = max(remaining - shot_dist, 0)

        if remaining <= 0:
            remaining = 0
            break

    return result

import streamlit as st


st.title("⛳ AIキャディ")

st.markdown("### 🎯 ラウンド目標")

goal_label, goal_select, goal_space = st.columns([2.2, 1, 4])

with goal_label:

    st.markdown(
        '<div class="ui-label-fixed">何打で回りたい？</div>',
        unsafe_allow_html=True
    )

with goal_select:

    target_score = st.selectbox(
        "",
        list(range(60, 151)),
        index=40,
        key="target_score",
        label_visibility="collapsed"
    )

if "course" not in st.session_state:
    st.session_state.course = {
        1: {"par": 4, "yard": 350},
        2: {"par": 3, "yard": 160},
        3: {"par": 5, "yard": 520},
        4: {"par": 4, "yard": 380},
        5: {"par": 4, "yard": 360},
        6: {"par": 3, "yard": 170},
        7: {"par": 5, "yard": 500},
        8: {"par": 4, "yard": 390},
        9: {"par": 4, "yard": 370},

        10: {"par": 4, "yard": 380},
        11: {"par": 5, "yard": 520},
        12: {"par": 3, "yard": 180},
        13: {"par": 4, "yard": 400},
        14: {"par": 4, "yard": 360},
        15: {"par": 3, "yard": 170},
        16: {"par": 5, "yard": 510},
        17: {"par": 4, "yard": 390},
        18: {"par": 4, "yard": 420},
    }



# 🎯 ホール難易度計算
hole_difficulty = {}

for h, data in st.session_state.course.items():
    yard = data["yard"]
    par = data["par"]

    score = yard / 100

    if par == 5:
        score -= 2
        score -= 1   # Par5優遇

    elif par == 3:
        score += 1

    if par == 4 and yard > 380:
        score += 1.5

    hole_difficulty[h] = score

# 合計パー
total_par = sum(h["par"] for h in st.session_state.course.values())

# ボギーペース
bogey_base = total_par + 18

# 難易度でソート（簡単→難しい）
sorted_holes = sorted(hole_difficulty.items(), key=lambda x: x[1])

# 🎯 ホール別AI推奨打数
hole_targets = {}

# 目標スコアに応じた基準
average_diff = (target_score - total_par) / 18

base_diff = int(average_diff)

for h, data in st.session_state.course.items():
    hole_targets[h] = data["par"] + base_diff

# 現在の合計
current_total = sum(hole_targets.values())

# 目標との差
diff_total = target_score - current_total

# 目標が低い場合（削る）
if diff_total < 0:

    easier_holes = sorted_holes

    idx = 0

    while diff_total < 0 and idx < len(easier_holes):

        h = easier_holes[idx][0]

        # パーまでは削れる
        if hole_targets[h] > st.session_state.course[h]["par"]:

            hole_targets[h] -= 1
            diff_total += 1

        else:
            idx += 1

# 目標が高い場合（増やす）
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

    h1, h2, h3, h4, h5 = st.columns([0.8,0.8,1.5,1.0,0.8])

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

        row1, row2, row3, row4, row5 = st.columns([0.8,0.8,1.5,1.0,0.8])

        par = st.session_state.course[h]["par"]

        target = hole_targets[h]

        diff = target - par

        if diff <= -1:
            mark = "★"
            color = "#8B0000"
            score_name = "birdie"

        elif diff == 0:
            mark = "◎"
            color = "#FF0000"
            score_name = "par"

        elif diff == 1:
            mark = "○"
            color = "#0070FF"
            score_name = "bog"

        elif diff == 2:
            mark = "△"
            color = "#008000"
            score_name = "dbl"

        else:
            mark = "▼"
            color = "#000000"
            score_name = "tri"

        strategy_html = (
            f"<span style='color:{color}; font-weight:bold;'>"
            f"{mark} {target} {score_name}"
            f"</span>"
        )

        actual = st.session_state.get(f"actual_{h}", "")

        with row4:
            st.markdown(
                f"<div style='font-size:18px'>{actual}</div>",
                unsafe_allow_html=True
            )

        deviation = ""

        if actual != "":

            gap = target - int(actual)

            if gap > 0:
                deviation = f"+{gap}"

            else:
                deviation = str(gap)

        with row1:
            st.markdown(
                f"<div style='font-size:18px'>{h}</div>",
                unsafe_allow_html=True
            )

        with row2:
            st.markdown(
                f"<div style='font-size:18px'>{par}</div>",
                unsafe_allow_html=True
            )

        with row3:
            st.markdown(
                f"<div style='font-size:18px'>{strategy_html}</div>",
                unsafe_allow_html=True
            )

        with row5:
            st.markdown(
                f"<div style='font-size:18px'>{deviation}</div>",
                unsafe_allow_html=True
            )

with st.expander("🧠 ラウンドスコア戦略", expanded=False):

    holes = sorted(st.session_state.course.keys())

    front9 = holes[:9]
    back9 = holes[9:]


    left_block, right_block = st.columns(2)

    with left_block:
        render_score_table(front9)

    with right_block:
        render_score_table(back9)

st.markdown("<div style='margin-top:20px;'></div>", unsafe_allow_html=True)

hole_col1, hole_col2, hole_col3 = st.columns([1.2, 0.6, 4])

with hole_col1:

    st.markdown(
        '<div class="ui-label">ホールを選択</div>',
        unsafe_allow_html=True
    )

with hole_col2:

    hole = st.selectbox(
        "",
        list(st.session_state.course.keys()),
        key="hole_select",
        label_visibility="collapsed"
    )

TOTAL_DIST = st.session_state.course[hole]["yard"]
par_num = st.session_state.course[hole]["par"]

st.markdown(f"<h3>⛳ {hole}番ホール <span style='color:red'>{TOTAL_DIST}y / Par {par_num}</span></h3>", unsafe_allow_html=True)

# 👇 ここ追加
if "prev_hole" not in st.session_state:
    st.session_state.prev_hole = hole

if hole != st.session_state.prev_hole:
    st.session_state.remaining = st.session_state.course[hole]["yard"]
    st.session_state.history = []   # ← これ追加（超重要）
    st.session_state.prev_hole = hole

with hole_col1:

    st.markdown(
        f"""
        <div style="display:flex; align-items:center; gap:15px;">

            

        </div>
        """,
        unsafe_allow_html=True
    )

# ② 残り距離の初期化（ここ重要）
if "remaining" not in st.session_state:
    st.session_state.remaining = TOTAL_DIST

if "history" not in st.session_state:
    st.session_state.history = []

# ③ 打数入力

recommended_score = hole_targets[hole]

diff = recommended_score - par_num

if diff <= -1:
    score_name = "バーディ"
    recommend_color = "#8B0000"

elif diff == 0:
    score_name = "パー"
    recommend_color = "#FF0000"

elif diff == 1:
    score_name = "ボギー"
    recommend_color = "#0070FF"

elif diff == 2:
    score_name = "ダブルボギー"
    recommend_color = "#008000"

else:
    score_name = "トリプル以上"
    recommend_color = "#000000"

target_label, target_select = st.columns([2, 1])

with target_label:

    st.markdown(
        f"""
        <div class='ui-label-fixed'>
        何打で上がる計画？
        <span style='color:{recommend_color}; font-weight:bold;'>
        （AI推奨：{recommended_score}打 {score_name}）
        </span>
        </div>
        """,
        unsafe_allow_html=True
    )

target_key = f"target_{hole}"

options = list(range(1, 16))

default_index = options.index(recommended_score)

with target_select:

    target_score = st.selectbox(
        "",
        options,
        index=default_index,
        key=f"target_select_{hole}",
        label_visibility="collapsed"
    )



putt_row1, putt_row2, putt_row3 = st.columns([2.2, 1, 4])

with putt_row1:

    st.markdown(
        '<div class="ui-label-putt">パット数は何回？</div>',
        unsafe_allow_html=True
    )

with putt_row2:

    putts = st.selectbox(
        "",
        [1, 2, 3, 4, 5],
        index=1,
        key="putt_select",
        label_visibility="collapsed"
    )

shot_strokes = target_score - putts

st.markdown(
    f"""
    <div class='ui-label-small'>
    ショット数：{shot_strokes}回 ＋ パット：{putts}回
    </div>
    """,
    unsafe_allow_html=True
)

min_strokes = par_num - 1

if target_score < min_strokes:

    st.error("それは無謀です！")
    st.stop()

# ④ 戦略作成（remainingを使う）
plan_data = plan(st.session_state.remaining, shot_strokes, 0, par_num)

st.markdown(
    "<div style='margin-top:20px;'></div>",
    unsafe_allow_html=True
)

use_danger = st.checkbox(
    "要注意エリアを設定",
    key=f"use_danger_{hole}"
)

if not use_danger:

    for i in range(1, 3):

        st.session_state[f"danger_type_{hole}_{i}"] = "未入力"

        st.session_state[f"danger_start_{hole}_{i}"] = 0

        st.session_state[f"danger_end_{hole}_{i}"] = 0

if use_danger:

    # =========================
    # 要注意エリア設定
    # =========================

    st.markdown(
        '<div class="ui-label">⚠️ 要注意エリア</div>',
        unsafe_allow_html=True
    )

    danger_options = [
        "未入力",
        "バンカー",
        "池",
        "OBゾーン",
        "谷越え",
        "ドッグレッグ"
    ]

    yard_options = [
        "未入力",
        0,
        50,
        100,
        150,
        170,
        200,
        230,
        250,
        300,
        350,
        400,
        450,
        500
    ]

    default_danger = ["未入力", "未入力"]
    default_start = [0, 0]
    default_end = [0, 0]
    
    for i in range(1, 3):
        
       
        c1, spacer, c2, c3, c4, c5, spacer, = st.columns([2, 0.1, 1.3, 0.6, 1.3, 1, 1])

        with c1:
                     
                       
           

            st.selectbox(
                "",
                danger_options,
                index=danger_options.index(default_danger[i-1]),
                key=f"danger_type_{hole}_{i}",
                label_visibility="collapsed"
            )

        with c2:


            
            st.selectbox(
                "",
                yard_options,
                key=f"danger_start_{hole}_{i}",
                index=yard_options.index(default_start[i-1]),
                label_visibility="collapsed"
            )

        with c3:

            st.markdown(
                '<div class="ui-label-small">から</div>',
                unsafe_allow_html=True
            )

        with c4:
            
            
            st.selectbox(
                "",
                yard_options,
                index=yard_options.index(default_end[i-1]),
                key=f"danger_end_{hole}_{i}",
                label_visibility="collapsed"
            )

        with c5:

            st.markdown(
                '<div class="ui-label-small">ヤード</div>',
                unsafe_allow_html=True
            )

       
        
# ⑤ 戦略表示

st.markdown(
    '<div class="ui-label">📋 この戦略でいこう！</div>',
    unsafe_allow_html=True
)


current_shot = 1

for h in st.session_state.history:

    result_text = ""

    # =========================
    # 結果表示
    # =========================

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
        f"<div style='font-size:20px; color:#007bff;'>"
        f"{current_shot}打目（実績）："
        f"{h['club']}（{h['dist']}y）"
        f"{result_text}"
        f"</div>",
        unsafe_allow_html=True
    )

    # 実際の1打
    current_shot += 1

    # ペナルティ加算
    current_shot += h.get("penalty", 0)


# =========================
# 使用打数計算
# =========================

used = 0

for h in st.session_state.history:

    # 実際に打った1打
    used += 1

    # ペナルティ加算
    used += h.get("penalty", 0)

remaining_strokes = shot_strokes - used

# ③ 残り戦略

if remaining_strokes > 0:
    plan_data = plan(st.session_state.remaining, remaining_strokes, used, par_num)

    for i, p in enumerate(plan_data):

        # 👇 ここから全部1段下げる
        display_club = p["club"]
        display_dist = min(p["dist"], p["before"])
        label = ""

        if i == len(plan_data) - 1:
            if display_dist >= p["before"]:
                msg = "グリーンオン"
                msg += f"<br>→ パッティング {putts}回"
                
            else:
                msg = f"⚠️ 届かない（あと{p['before'] - display_dist}y不足）"
        else:
            msg = f"残り{max(p['before'] - display_dist, 0)}y"

        st.markdown(
            f"<div style='font-size:20px;'>"
            f"{used + p['shot']}打目：{display_club}（{display_dist}y）{label} → {msg}"
            f"</div>",
            unsafe_allow_html=True
        )
        if i == len(plan_data) - 1 and st.session_state.remaining <= 5:
            st.markdown(
                f"<div style='font-size:20px;'>→ パット {putts}回</div>",
                unsafe_allow_html=True
            )


elif remaining_strokes == 0:
    if st.session_state.remaining <= 5:
        st.write("→ グリーンオン（パットのみ）")
    else:
        st.error("⚠️ この計画では届きません")

else:
    st.error("ショット数が不足しています")





with st.form("shot_form"):


    st.markdown(
        """
        <style>
        div[data-testid="stForm"] {
            padding-top: 0px;
        }
        </style>
        """,
        unsafe_allow_html=True
    )


  
    st.markdown(
        """
        <style>
        div[data-testid="stForm"] {
            padding-top: 0px;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

 
    st.markdown(
        '<div class="ui-label">🎯 ショットの結果はどうだった？</div>',
        unsafe_allow_html=True
    )

    c1, c2, c3, c4, c5 = st.columns([2, 2, 2, 1.2, 1.2])

    with c1:

        st.markdown(
            '<div class="ui-label-small">使ったクラブ</div>',
            unsafe_allow_html=True
        )



        actual_club = st.selectbox(
            "",
            [c["name"] for c in CLUBS],
            label_visibility="collapsed"
        )

    with c2:

        st.markdown(
            '<div class="ui-label-small">飛距離（ヤード）</div>',
            unsafe_allow_html=True
        )

        

        actual_dist = st.number_input(
            "",
            0,
            300,
            100,
            label_visibility="collapsed"
        )

    with c3:

        st.markdown(
            '<div class="ui-label-small">結果</div>',
            unsafe_allow_html=True
        )

        

        shot_result = st.selectbox(
            "",
            [
                "通常",
                "OB",
                "池",
                "赤杭",
                "ロスト",
                "空振り"
            ],
            label_visibility="collapsed"
        )

    with c4:

        st.markdown(
            '<div class="ui-label-small"></div>',
            unsafe_allow_html=True
        )

        submitted = st.form_submit_button(
            "反映"
        )

    with c5:

        st.markdown(
            '<div class="ui-label-small"></div>',
            unsafe_allow_html=True
        )

        undo = st.form_submit_button(
            "取消"
        )

    if submitted:

        penalty = 0
        remain_adjust = actual_dist

    # =========================
    # 結果別処理
    # =========================

        if shot_result == "OB":

            penalty = 1

            # OBは前進なし
            remain_adjust = 0

        elif shot_result == "池":

            penalty = 1

            # 池は落下地点まで進む
            remain_adjust = actual_dist


        elif shot_result == "赤杭":

            penalty = 1

            # 赤杭は飛距離分進む
            remain_adjust = actual_dist


        elif shot_result == "ロスト":

            penalty = 2

            # ロストは前進扱い
            remain_adjust = actual_dist


        elif shot_result == "空振り":

            remain_adjust = 0
    
    # =========================
    # 履歴保存
    # =========================

        st.session_state.history.append({
            "club": actual_club,
            "dist": actual_dist,
            "result": shot_result,
            "penalty": penalty
        })

    # =========================
    # 残り距離更新
    # =========================

        st.session_state.remaining -= remain_adjust

        if st.session_state.remaining < 0:
            st.session_state.remaining = 0

        st.rerun()

    if undo:

        if len(st.session_state.history) > 0:

            last_shot = st.session_state.history.pop()

            actual_back = last_shot["dist"]

            # 結果別に戻す距離を変える
            if last_shot["result"] == "OB":
                actual_back = 0

            elif last_shot["result"] == "空振り":
                actual_back = 0

            st.session_state.remaining += actual_back

            st.rerun()





# ⑦ 残り距離表示
st.markdown(
    f"""
    <div style="text-align:left; margin-top:10px; font-size:20px;">
        現在の残り距離
        <span style="color:#2E8B57; font-weight:bold; margin-left:10px;">
            {st.session_state.remaining}y
        </span>
    </div>
    """,
    unsafe_allow_html=True
)



st.markdown(
    """
    <hr style="
        margin-top:5px;
        margin-bottom:5px;
    ">
    """,
    unsafe_allow_html=True
)

score_col1, score_col2 = st.columns([2.1, 1])

with score_col1:

    st.markdown(
        '<div class="ui-label">🏁 このホールの最終スコア</div>',
        unsafe_allow_html=True
    )


def update_actual_score():
    st.session_state[f"actual_{hole}"] = int(
        st.session_state[f"final_score_input_{hole}"]
    )


with score_col2:

    

    final_score = st.selectbox(
        "",
        list(range(1, 17)),
        index=max(
            int(st.session_state.get(f"actual_{hole}", 1)) - 1,
            0
        ),
        key=f"final_score_input_{hole}",
        on_change=update_actual_score,
        label_visibility="collapsed"
    )










# ⑧ リセット


# ⑨ クラブ設定

st.divider()

with st.expander("⚙️ クラブ設定", expanded=False):

    if st.button("クラブ設定を初期に戻す"):

        st.session_state.clubs = CLUBS.copy()

        # UIのkeyをリセット
        for k in list(st.session_state.keys()):
            if (
                k.startswith("name_") 
                or k.startswith("dist_") 
                or k.startswith("miss_")
            ):
                del st.session_state[k]

        st.rerun()

    # 👇 幅を調整（ここがポイント）
    col1, col2, col3, col4 = st.columns([1, 1, 2, 1])

    with col1:
        st.markdown("**クラブ**")

    with col2:
        st.markdown("**距離 (y)**")

    with col3:
        st.markdown("**ミス率**")

    with col4:
        st.markdown("**得意距離**")

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
        "1W": 1,
        "3W": 2,
        "5W": 3,
        "3U": 4,
        "4U": 5,
        "5U": 6,
        "6U": 7,
        "5I": 8,
        "6I": 9,
        "7I": 10,
        "8I": 11,
        "9I": 12,
        "PW": 13,
        "AW": 14,
        "UW": 15,
        "SW": 16,
        "52°": 17,
        "56°": 18,
        "58°": 19,
        "60°": 20
    }

    st.session_state.clubs = sorted(
        edited_clubs,
        key=lambda x: club_order.get(x["name"], 999)
    )

    st.session_state.pop("name_0", None)

    st.rerun()

# ⑩　コース設定



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
            index=tee_options.index(
                st.session_state.get("tee_type", "REG")
            )
        )


    st.divider()

    edited_course = {}

    holes = list(st.session_state.course.keys())

    # 👇 9ホールずつ分ける
    left_holes = holes[:9]
    right_holes = holes[9:]

    # 👇 左右2カラム
    col_left, col_right = st.columns(2)

    def render_holes(holes_subset):
        for h in holes_subset:

            # 👇 1行を超コンパクトに
            c1, c2, c3, c4, c5 = st.columns([0.8, 0.6, 1, 0.6, 1])

            with c1:
                st.markdown(f"**{h}番**")

            with c2:
                st.markdown("Par")

            with c3:
                par = st.number_input(
                    "",
                    3, 6,
                    st.session_state.course[h]["par"],
                    key=f"par_{h}",
                    label_visibility="collapsed"
                )

            with c4:
                st.markdown("Yard")

            with c5:
                yard = st.number_input(
                    "",
                    50, 700,
                    st.session_state.course[h]["yard"],
                    key=f"yard_{h}",
                    label_visibility="collapsed"
                )

            edited_course[h] = {"par": par, "yard": yard}


    # 👇 左列（1〜9番）
    with col_left:
        render_holes(left_holes)

    # 👇 右列（10〜18番）
    with col_right:
        render_holes(right_holes)


# 更新ボタン
if st.button("コース設定を更新"):

    st.session_state.course = edited_course

    st.session_state.course_name = course_name

    st.session_state.tee_type = tee_type

    st.rerun()