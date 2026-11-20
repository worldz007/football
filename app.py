import pandas as pd
import streamlit as st

st.set_page_config(page_title="Sport Predictor", page_icon="⚽", layout="centered")

LEAGUES = {"PL": "Premier League", "ELC": "Championship", "PD": "La Liga",
           "SA": "Serie A", "BL1": "Bundesliga", "FL1": "Ligue 1",
           "DED": "Eredivisie", "PPL": "Primeira Liga", "BSA": "Brazil Série A"}

GROUPS = {
    "Result": ["Home win", "Draw", "Away win"],
    "Double chance": ["Double chance 1X (Home/Draw)", "Double chance 12 (Home/Away)",
                      "Double chance X2 (Away/Draw)"],
    "Team goals (1.5 line)": ["Home team over 1.5", "Home team under 1.5",
                              "Away team over 1.5", "Away team under 1.5"],
    "Total goals (2.5 line)": ["Over 2.5 goals", "Under 2.5 goals"],
    "Combos": ["Home or Over 2.5", "Home or Under 2.5",
               "Away or Over 2.5", "Away or Under 2.5"],
}

STYLES = {
    "Safer": ["Home win", "Away win", "Double chance 1X (Home/Draw)",
              "Double chance 12 (Home/Away)", "Double chance X2 (Away/Draw)"],
    "Balanced": ["Home win", "Away win", "Double chance 1X (Home/Draw)",
                 "Double chance X2 (Away/Draw)"],
    "Bolder": ["Home win", "Away win"],
}


@st.cache_data
def load():
    df = pd.read_csv("predictions.csv")
    return df.sort_values(["date", "league"]).reset_index(drop=True)


def prob_bar(h, d, a):
    return ('<div style="display:flex;height:8px;border-radius:4px;overflow:hidden;'
            'gap:2px;margin:8px 0 4px">'
            f'<div style="flex:{h:.3f};background:#B8F04A"></div>'
            f'<div style="flex:{d:.3f};background:#5F7B6E"></div>'
            f'<div style="flex:{a:.3f};background:#E8F0EC"></div></div>')


def risk_zone(odds):
    if odds <= 2:
        return "Coin flip"
    if odds <= 10:
        return "Low chance"
    if odds <= 100:
        return "Long shot"
    return "Lottery"


preds = load()
dates = sorted(preds["date"].unique())

st.title("Sport Predictor")
st.caption(f"Estimates, not tips. Matches from {dates[0]} to {dates[-1]}.")

tab_m, tab_s, tab_r = st.tabs(["Matches", "Build my slip", "How reliable"])

with tab_m:
    c1, c2 = st.columns(2)
    league = c1.selectbox("League", ["All"] + list(LEAGUES),
                          format_func=lambda c: "All leagues" if c == "All" else LEAGUES.get(c, c))
    day = c2.selectbox("Day", ["Whole week"] + dates)
    view = preds
    if league != "All":
        view = view[view["league"] == league]
    if day != "Whole week":
        view = view[view["date"] == day]
    st.caption(f"{len(view)} matches")

    for _, r in view.iterrows():
        with st.container(border=True):
            st.caption(f"{LEAGUES.get(r['league'], r['league'])} · {r['date']}")
            st.markdown(f"**{r['home_team']}** vs **{r['away_team']}**")
            st.markdown(prob_bar(r["Home win"], r["Draw"], r["Away win"]),
                        unsafe_allow_html=True)
            st.caption(f"Home {r['Home win']:.0%} · Draw {r['Draw']:.0%} · "
                       f"Away {r['Away win']:.0%}")
            with st.expander("All markets"):
                st.write(f"Expected goals: {r['Exp home goals']} - {r['Exp away goals']}")
                for title, markets in GROUPS.items():
                    st.markdown(f"**{title}**")
                    for m in markets:
                        st.write(f"{m}: {r[m]:.0%}")
                st.warning("Injuries and lineups are not in the model. "
                           "Check team news before trusting any number.")

with tab_s:
    st.subheader("Build my slip")
    target = st.number_input("Odds I want", min_value=1.2, max_value=1000.0,
                             value=2.0, step=0.5)
    style = st.radio("Risk style", list(STYLES), horizontal=True)
    st.caption("Safer: more picks, each very likely. Bolder: fewer picks, each less "
               "likely. The combined chance stays about the same.")
    day2 = st.selectbox("Day", ["Whole week"] + dates, key="slip_day")

    pool = preds if day2 == "Whole week" else preds[preds["date"] == day2]
    legs = []
    for _, r in pool.iterrows():
        m = max(STYLES[style], key=lambda k: r[k])
        legs.append({"Date": r["date"], "Match": f"{r['home_team']} vs {r['away_team']}",
                     "Pick": m, "prob": float(r[m])})
    legs.sort(key=lambda x: -x["prob"])

    slip, joint = [], 1.0
    for leg in legs:
        slip.append(leg)
        joint *= leg["prob"]
        if 1 / joint >= target:
            break

    if slip:
        fair = 1 / joint
        st.markdown(f"**Risk level: {risk_zone(fair)}**")
        k1, k2, k3 = st.columns(3)
        k1.metric("Chance all win", f"{joint:.1%}")
        k2.metric("Fair odds", f"{fair:.2f}")
        k3.metric("Picks", len(slip))
        st.caption(f"That is about 1 in {fair:.0f}.")
        table = pd.DataFrame(slip)
        table["Chance"] = (table["prob"] * 100).round(0).astype(int).astype(str) + "%"
        table["Fair odds"] = (1 / table["prob"]).round(2)
        st.dataframe(table[["Date", "Match", "Pick", "Chance", "Fair odds"]],
                     hide_index=True, use_container_width=True)
        if fair < target:
            st.warning("Not enough matches in this period to reach your odds.")
    else:
        st.info("No matches for this day.")

    st.warning("The higher the odds, the lower the chance: 5.00 is about 1 in 5, and "
               "500 is about 1 in 500. Fair odds are not bookmaker prices, and "
               "bookmakers usually pay less. Only stake what you can afford to lose.")

with tab_r:
    st.subheader("How reliable is this?")
    st.caption("Tested on matches the model had not seen.")
    st.metric("Result accuracy", "49.9%",
              help="Bookmaker: 52.3%. Always picking the home team: 43.1%. 2,862 matches.")
    st.write("The bookmakers were more accurate: 52.3%. Always picking the home team "
             "gets 43.1%.")
    st.metric("Value-bet test (profit per unit staked)", "-19.0%")
    st.write("Betting every match our model rated as value lost 19.0% per unit. "
             "Betting every bookmaker favourite lost 4.1%.")
    st.info("Use this as a free estimate of likely outcomes, not as a way to win money.")
