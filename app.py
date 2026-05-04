import streamlit as st

TOTAL_DIST = 350

CLUBS = [
    {"name": "1W", "dist": 200, "miss": 0.25},
    {"name": "U4", "dist": 170, "miss": 0.25},
    {"name": "U5", "dist": 160, "miss": 0.25},
    {"name": "7i", "dist": 145, "miss": 0.20},
    {"name": "9i", "dist": 130, "miss": 0.15},
    {"name": "PW", "dist": 120, "miss": 0.15},
    {"name": "56", "dist": 80, "miss": 0.15},
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

def choose_club(remaining, shots_left, is_first_shot):

    # 👇ここを修正
    if is_first_shot:

        if remaining <= 220:
            return min(
                st.session_state.clubs,
                key=lambda c: abs(c["dist"] - remaining)
            )

        return max(st.session_state.clubs, key=lambda c: c["dist"])

    best = None
    best_score = 999

    target = remaining / shots_left

    for club in st.session_state.clubs:

        if not is_first_shot and club["name"] == "1W":
            continue

        # 👇追加（オーバー防止）
        if shots_left > 1 and club["dist"] > remaining:
            continue


        good = club["dist"]
        miss = club["dist"] * 0.6
        miss_rate = club["miss"]

        # 期待残距離
        expected_after = (
            (1 - miss_rate) * (remaining - good)
            + miss_rate * (remaining - miss)
        )

        # 次の1打も考慮
        if shots_left > 1:
            next_best = min(
                abs(expected_after - c["dist"])
                for c in st.session_state.clubs
            )

            score = (
                expected_after
                + next_best * (3 / shots_left)
                + abs(club["dist"] - target) * 1.5  # 👈追加
            )
        else:
            score = abs(expected_after)

        if score < best_score:
            best_score = score
            best = club

    if best is None:

        if not is_first_shot:
            best = min(st.session_state.clubs, key=lambda c: c["dist"])
        else:
            best = max(st.session_state.clubs, key=lambda c: c["dist"])

    return best

def find_replacement_club(remaining):
    candidates = [c for c in st.session_state.clubs if c["dist"] >= remaining]

    if candidates:
        return min(candidates, key=lambda x: x["dist"])

    return None

def plan(total_dist, strokes, used):
    result = []
    remaining = total_dist

    for i in range(strokes):
        shots_left = strokes - i

        # 1打目かどうか
        is_first_shot = (used + i == 0)

        # クラブ選択
        club = choose_club(remaining, shots_left, is_first_shot)

        shot_dist = club["dist"]

        result.append({
            "shot": i + 1,
            "club": club["name"],
            "dist": shot_dist,
            "remain": max(remaining - shot_dist, 0),
            "before": remaining
        })

        remaining = max(remaining - shot_dist, 0)

        if remaining == 0:
            break

    return result

import streamlit as st

st.title("⛳ AIキャディ")

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

st.markdown(
    "<h4 style='margin-bottom:-30px;'>ホールを選択</h4>",
    unsafe_allow_html=True
)

hole = st.selectbox("", list(COURSE.keys()), key="hole_select")

TOTAL_DIST = COURSE[hole]["yard"]
par_num = COURSE[hole]["par"]

# 👇 ここ追加
if "prev_hole" not in st.session_state:
    st.session_state.prev_hole = hole

if hole != st.session_state.prev_hole:
    st.session_state.remaining = COURSE[hole]["yard"]
    st.session_state.history = []   # ← これ追加（超重要）
    st.session_state.prev_hole = hole

st.markdown(
    f"<h3 style='color:#2E8B57;'>⛳ {hole}番ホール</h3>"
    f"<h3 style='color:#d9534f;'>{TOTAL_DIST}y / Par {par_num}</h3>",
    unsafe_allow_html=True
)

# ② 残り距離の初期化（ここ重要）
if "remaining" not in st.session_state:
    st.session_state.remaining = TOTAL_DIST

if "history" not in st.session_state:
    st.session_state.history = []

# ③ 打数入力
st.markdown(
    "<h5 style='margin-bottom:-30px;'>何打で上がる計画にする？</h5>",
    unsafe_allow_html=True
)

strokes = st.number_input("", 2, 10, 4)

st.markdown(
    "<h5 style='margin-bottom:-30px;'>パット数は何回？</h5>",
    unsafe_allow_html=True
)

putts = st.number_input("", 1, 5, 2)

shot_strokes = strokes - putts

st.markdown(
    f"<h5 style='margin-top:5px;'>ショット数：{shot_strokes}回 ＋ パット：{putts}回</h5>",
    unsafe_allow_html=True
)

st.write(f"ショット数：{shot_strokes}回 ＋ パット：{putts}回")

min_strokes = par_num - 1

if strokes < min_strokes:
    st.error("それは無謀です！")
    st.stop()

# ④ 戦略作成（remainingを使う）
plan_data = plan(st.session_state.remaining, shot_strokes, 0)

# ⑤ 戦略表示
st.markdown("<h5>📋 この戦略でいこう！</h5>", unsafe_allow_html=True)

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
    plan_data = plan(st.session_state.remaining, remaining_strokes, used)

    for i, p in enumerate(plan_data):

        # 👇 ここから全部1段下げる
        display_club = p["club"]
        display_dist = p["dist"]
        changed = False

        is_after_actual = len(st.session_state.history) > 0

        shots_left_now = remaining_strokes - i
        if shots_left_now <= 0:
            shots_left_now = 1

        current_remaining = p["before"]
        target = current_remaining / shots_left_now

        if is_after_actual:
            new_club = min(
                st.session_state.clubs,
                key=lambda c: abs(c["dist"] - target)
            )

            if new_club["name"] != p["club"]:
                display_club = new_club["name"]
                display_dist = new_club["dist"]
                changed = True

        label = "（クラブ変更）" if changed else ""

        if i == len(plan_data) - 1:
            if display_dist >= p["before"]:
                msg = "グリーンオン"
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
    st.markdown("<h5>🎯 ショットの結果はどうだった？</h5>", unsafe_allow_html=True)

    actual_club = st.selectbox(
        "使ったクラブ",
        [c["name"] for c in CLUBS]
    )

    actual_dist = st.number_input("飛距離（ヤード）", 0, 300, 100)

    submitted = st.form_submit_button("このショットを反映")

if submitted:
    st.session_state.history.append({
        "club": actual_club,
        "dist": actual_dist
    })
    st.session_state.remaining -= actual_dist
    st.rerun()

# ⑦ 残り距離表示（これ重要）
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

# ⑧ リセット
if st.button("リセット"):
    st.session_state.remaining = TOTAL_DIST
    st.session_state.history = []
    st.rerun()

# ⑨ クラブ設定

st.divider()
st.markdown("<h5>⚙️ クラブ設定（編集可能）</h5>", unsafe_allow_html=True)

# 👇 幅を調整（ここがポイント）
col1, col2, col3 = st.columns([1, 1, 3])

with col1:
    st.markdown("**クラブ**")

with col2:
    st.markdown("**距離 (y)**")

with col3:
    st.markdown("**ミス率**")

edited_clubs = []

for i, c in enumerate(st.session_state.clubs):

    # 👇 同じ比率を使う（重要）
    col1, col2, col3 = st.columns([1, 1, 3])

    with col1:
        name = st.text_input("", c["name"], key=f"name_{i}")

    with col2:
        dist = st.number_input("", 0, 300, c["dist"], key=f"dist_{i}")

    with col3:
        miss = st.slider("", 0.0, 0.8, c["miss"], 0.01, key=f"miss_{i}")

    edited_clubs.append({
        "name": name,
        "dist": dist,
        "miss": miss
    })

if st.button("クラブ設定を更新"):
    st.session_state.clubs = edited_clubs
    st.rerun()

# ⑩　コース設定

st.divider()
st.markdown("<h5>⛳ コース設定</h5>", unsafe_allow_html=True)

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