import streamlit as st

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

goal_col1, goal_col2, goal_col3 = st.columns([1.8, 0.6, 4])

with goal_col1:

    st.markdown(
        "<div style='font-size:20px; font-weight:bold; margin-top:8px;'>"
        "何打で回りたい？"
        "</div>",
        unsafe_allow_html=True
    )

with goal_col2:

    st.markdown(
        "<div style='margin-top:20px;'></div>",
        unsafe_allow_html=True
    )


    target_score = st.selectbox(
        "",
        list(range(60, 151)),
        index=40,
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
        "<div style='font-size:20px; font-weight:bold; margin-top:-8px;'>"
        "ホールを選択"
        "</div>",
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

target_col1, target_col2, target_col3 = st.columns([5.5, 1, 1])

with target_col1:

    st.markdown(
        f"""
        <div style='font-size:20px; font-weight:bold; margin-top:8px;'>
        何打で上がる計画？
        <span style='color:{recommend_color}; font-weight:bold;'>
        （AI推奨：{recommended_score}打 {score_name}）
        </span>
        </div>
        """,
        unsafe_allow_html=True
    )

st.markdown(
    """
    <style>
    div[data-baseweb="select"] {
        width: 120px;
        margin-top: -8px;
    }
    </style>
    """,
    unsafe_allow_html=True
)

target_key = f"target_{hole}"

options = list(range(1, 16))

default_index = options.index(recommended_score)

st.markdown(
    """
    <style>
    div[data-testid="stSelectbox"] {
        margin-top: -8px;
    }
    </style>
    """,
    unsafe_allow_html=True
)


with target_col2:

    target_score = st.selectbox(
        "",
        options,
        index=default_index,
        key=f"target_select_{hole}"
    )



putt_col1, putt_col2 = st.columns([0.5, 1])

with putt_col1:

    st.markdown(
        "<div style='font-size:20px; font-weight:bold; margin-top:-15px;'>パット数は何回？</div>",
        unsafe_allow_html=True
    )

st.markdown(
    """
    <style>
    div[data-testid="stSelectbox"] {
        margin-top: -20px;
    }
    </style>
    """,
    unsafe_allow_html=True
)


with putt_col2:

    putts = st.selectbox(
        "",
        [1, 2, 3, 4, 5],
        index=1,
        label_visibility="collapsed"
    )

shot_strokes = target_score - putts

st.markdown(
    f"""
    <div style='font-size:18px; margin-top:5px; font-weight:normal;'>
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

# ⑤ 戦略表示

st.markdown(
    "<h5 style='margin-top:10px;'>📋 この戦略でいこう！</h5>",
    unsafe_allow_html=True
)


# ① 実績表示
for i, h in enumerate(st.session_state.history):
    st.markdown(
    f"<div style='font-size:20px; color:#007bff; margin-bottom:5px;'>"
    f"{i+1}打目（実績）：{h['club']}（{h['dist']}y）"
    f"</div>",
    unsafe_allow_html=True
)

# ② 残りショット数
used = len(st.session_state.history)
remaining_strokes = shot_strokes - used

# ③ 残り戦略

if remaining_strokes > 0:
    plan_data = plan(st.session_state.remaining, remaining_strokes, used, par_num)

    for i, p in enumerate(plan_data):

        # 👇 ここから全部1段下げる
        display_club = p["club"]
        display_dist = p["dist"]
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


st.markdown(
    "<div style='margin-top:15px;'></div>",
    unsafe_allow_html=True
)


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
        "<h5 style='margin-top:-10px; margin-bottom:0px;'>🎯 ショットの結果はどうだった？</h5>",
        unsafe_allow_html=True
    )

    c1, c2, c3, c4 = st.columns([2, 2, 1.2, 1.2])

    with c1:

        st.markdown(
            "<div style='margin-bottom:5px;'>使ったクラブ</div>",
            unsafe_allow_html=True
        )

        st.markdown(
            "<div style='margin-top:8px;'></div>",
            unsafe_allow_html=True
        )

        actual_club = st.selectbox(
            "",
            [c["name"] for c in CLUBS],
            label_visibility="collapsed"
        )

    with c2:

        st.markdown(
            "<div style='margin-bottom:5px;'>飛距離（ヤード）</div>",
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

        st.markdown("<br>", unsafe_allow_html=True)

        submitted = st.form_submit_button(
            "反映"
        )

    with c4:

        st.markdown("<br>", unsafe_allow_html=True)

        undo = st.form_submit_button(
            "取消"
        )


if submitted:
    st.session_state.history.append({
        "club": actual_club,
        "dist": actual_dist
    })
    st.session_state.remaining -= actual_dist
    st.rerun()

if undo:

    if len(st.session_state.history) > 0:

        last_shot = st.session_state.history.pop()

        st.session_state.remaining += last_shot["dist"]

        st.rerun()






# ⑦ 残り距離表示
st.markdown(
    f"""
    <div style="text-align:left; margin-top:10px; font-size:20px;">
        まだこれだけ残っているね！
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
        "<div style='font-size:20px; font-weight:bold; margin-top:12px;'>"
        "🏁 このホールの最終スコア"
        "</div>",
        unsafe_allow_html=True
    )


def update_actual_score():
    st.session_state[f"actual_{hole}"] = int(
        st.session_state[f"final_score_input_{hole}"]
    )


with score_col2:

    st.markdown(
        "<div style='margin-top:25px;'></div>",
        unsafe_allow_html=True
    )

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
            dist = st.number_input("", 0, 300, c["dist"], key=f"dist_{i}")

        with col3:
            miss = st.slider("", 0.0, 0.8, c["miss"], 0.01, key=f"miss_{i}")

        with col4:
            favorite = st.number_input(
                "",
                0,
                200,
                c.get("favorite", 0),
                key=f"favorite_{i}"
            )


    if name != "（未選択）":
        edited_clubs.append({
            "name": name,
            "dist": dist,
            "miss": miss,
            "favorite": favorite
        })


if st.button("クラブ設定を更新"):

    names = [c["name"] for c in edited_clubs]

    if len(names) != len(set(names)):
        st.error("同じクラブは1本しか選べません")
        st.stop()

    if len(edited_clubs) > 13:
        st.error("クラブはパターを除いて13本までです")
        st.stop()

    st.session_state.clubs = sorted(
        edited_clubs,
        key=lambda x: x["dist"],
        reverse=True
    )

    st.session_state.pop("name_0", None)
    st.rerun()

# ⑩　コース設定

st.divider()

with st.expander("⛳ コース設定", expanded=False):

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
    st.rerun()