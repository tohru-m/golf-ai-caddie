import streamlit as st

TOTAL_DIST = 350

CLUBS = [
    {"name": "1W", "dist": 200, "miss": 0.25},
    {"name": "5W", "dist": 180, "miss": 0.25},
    {"name": "4U", "dist": 170, "miss": 0.25},
    {"name": "5U", "dist": 160, "miss": 0.25},
    {"name": "6I", "dist": 150, "miss": 0.20},
    {"name": "7I", "dist": 145, "miss": 0.20},
    {"name": "8I", "dist": 135, "miss": 0.18},
    {"name": "9I", "dist": 125, "miss": 0.15},
    {"name": "PW", "dist": 115, "miss": 0.15},
    {"name": "52°", "dist": 95, "miss": 0.15},
    {"name": "56°", "dist": 85, "miss": 0.15},
    {"name": "58°", "dist": 75, "miss": 0.15},
    {"name": "60°", "dist": 65, "miss": 0.15},
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

def choose_club(remaining, shots_left, is_first_shot, par_num, strategy):

    # 👇 ① 有効クラブだけ抽出（ここ追加）
    valid_clubs = [c for c in st.session_state.clubs if c["dist"] > 0 and c["name"] != "なし"]

    # 👇 ② クラブがない場合
    if not valid_clubs:
        return {"name": "なし", "dist": 0, "miss": 1.0}

    # 👇 ③ 1打目ロジック
    if is_first_shot:

        if remaining <= 220:

            # 👇 安全モードなら届くクラブを除外
            if strategy == "安全（刻む）":
                safe_clubs = [c for c in valid_clubs if c["dist"] < remaining]

                if safe_clubs:
                    return min(
                        safe_clubs, 
                        key=lambda c: abs(c["dist"] - remaining)
                    )

        return min(
            valid_clubs,
            key=lambda c: abs(c["dist"] - remaining)
        )

        return max(valid_clubs, key=lambda c: c["dist"])

    # 👇 ④ ここから元のロジック（残す）
    best = None
    best_score = 999

    target = remaining / shots_left

    if par_num == 5 and not is_first_shot and shots_left >= 2 and remaining > 180:
        target = remaining * 0.7   # ←ここがポイント（強気に距離を取りに行く）

    for club in valid_clubs:

        if club["name"] == "1W":
            continue

        if shots_left > 1 and club["dist"] > remaining:
            continue

        good = club["dist"]
        miss = club["dist"] * 0.6
        miss_rate = club["miss"]

        expected_after = (
            (1 - miss_rate) * (remaining - good)
            + miss_rate * (remaining - miss)
        )

        if shots_left > 1:
            next_best = min(
                abs(expected_after - c["dist"])
                for c in valid_clubs
            )

            score = (
                expected_after
                + next_best * (3 / shots_left)
                + abs(club["dist"] - target) * 1.5
            )
        else:
            score = abs(expected_after)

        if score < best_score:
            best_score = score
            best = club

    if best is None:
        best = min(valid_clubs, key=lambda c: c["dist"])

    return best

def find_replacement_club(remaining):
    candidates = [c for c in st.session_state.clubs if c["dist"] >= remaining]

    if candidates:
        return min(candidates, key=lambda x: x["dist"])

    return None

def plan(total_dist, strokes, used, par_num, strategy):
    result = []
    remaining = total_dist

    for i in range(strokes):
        shots_left = strokes - i

        # 1打目かどうか
        is_first_shot = (used + i == 0)

        # クラブ選択
        club = choose_club(remaining, shots_left, is_first_shot, par_num, strategy)

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

target_score = st.number_input(
    "何打で回りたい？",
    60, 150, 88
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

# 初期化
target_par_holes = []
target_double_holes = []

if target_score <= bogey_base:
    # パーを取る必要があるケース（90以下）
    needed_par = bogey_base - target_score
    target_par_holes = [h[0] for h in sorted_holes[:needed_par]]

else:
    # ダボOKを作るケース（90以上）
    extra = target_score - bogey_base
    target_double_holes = [h[0] for h in sorted_holes[::-1][:extra]]

st.markdown(
    "<div style='font-size:18px; font-weight:bold'>🧠 ラウンドスコア戦略</div>",
    unsafe_allow_html=True
)

holes = sorted(st.session_state.course.keys())

cols = st.columns(6)

for i, h in enumerate(holes):
    col = cols[i % 6]

    par = st.session_state.course[h]["par"]

    if h in target_par_holes:
        label = "◎パー"
    elif h in target_double_holes:
        label = "△ダボ"
    else:
        label = "〇ボギー"

    with col:
        st.markdown(
            f"""
            <div style='font-size:14px; line-height:1.7'>
            <b>{h}番 Par{par}</b><br>
            {label}
            </div>
            """,
            unsafe_allow_html=True
        )

st.markdown("<div style='margin-top:20px;'></div>", unsafe_allow_html=True)

st.markdown(
    "<div style='font-size:20px; font-weight:bold; margin-bottom:-8px;'>ホールを選択</div>",
    unsafe_allow_html=True
)




hole = st.selectbox(
    "",
    list(st.session_state.course.keys()),
    key="hole_select"
)


TOTAL_DIST = st.session_state.course[hole]["yard"]
par_num = st.session_state.course[hole]["par"]





# 👇 ここ追加
if "prev_hole" not in st.session_state:
    st.session_state.prev_hole = hole

if hole != st.session_state.prev_hole:
    st.session_state.remaining = st.session_state.course[hole]["yard"]
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

strategy = st.selectbox(
    "戦略モード",
    ["最短（攻め）", "安全（刻む）"]
)

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
plan_data = plan(st.session_state.remaining, shot_strokes, 0, par_num, strategy)

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
    plan_data = plan(st.session_state.remaining, remaining_strokes, used, par_num, strategy)

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

if st.button("クラブ設定を初期に戻す"):

    st.session_state.clubs = CLUBS.copy()

    # UIのkeyをリセット（これ重要）
    for k in list(st.session_state.keys()):
        if k.startswith("name_") or k.startswith("dist_") or k.startswith("miss_"):
            del st.session_state[k]

    st.rerun()

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

    unique_id = f"{i}_{c['name']}" 

    col1, col2, col3 = st.columns([1, 1, 3])

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

    # 👇ここに入れる（重要）
    if name != "（未選択）":
        edited_clubs.append({
            "name": name,
            "dist": dist,
            "miss": miss
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
