import streamlit as st

PAGE_AQI = "AQI Checker"
PAGE_QA = "Health Q&A"

# page config must be the first st call
st.set_page_config(
    page_title="Urban Health Risk Assistant",
    layout="centered"
)

st.markdown("""
<style>
:root {
    --brand: #2f9e6e;
    --brand-dark: #1f7a52;
    --brand-light: #e6f5ee;
}

h1, h2, h3 { color: #1d3b2f; }

/* Primary action buttons (Ask, Find monitoring stations, Check air quality) */
.stButton > button[kind="secondary"],
.stButton > button {
    border-radius: 8px;
    border: 1px solid #cfe3da;
    transition: all 0.15s ease;
}
.stButton > button:hover {
    border-color: var(--brand);
    color: var(--brand-dark);
}
.stButton > button:focus:not(:active) {
    border-color: var(--brand);
    color: var(--brand-dark);
}

div[data-testid="stSidebar"] {
    background-color: var(--brand-light);
}

hr {
    border-top: 1px solid #cfe3da;
}

/* Quick-question chips */
div[data-testid="column"] .stButton > button {
    background-color: #fafdfb;
}

/* Source excerpt card */
.source-card {
    background: var(--brand-light);
    border-left: 4px solid var(--brand);
    border-radius: 6px;
    padding: 10px 14px;
    margin-bottom: 10px;
    font-size: 14px;
    color: #2b3d35;
}

/* Metric value color */
div[data-testid="stMetricValue"] {
    color: var(--brand-dark);
}
</style>
""", unsafe_allow_html=True)

page = st.sidebar.radio("Navigate", [PAGE_AQI, PAGE_QA], index=0)

st.sidebar.divider()
st.sidebar.caption(
    "Combines live air quality data with your health profile, "
    "plus a Q&A assistant grounded in WHO documents."
)

# session state defaults
defaults = {
    "locations": None,
    "city": None,
    "selected_area": None,
    "diseases": [],
}
for key, default in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = default

# =========================================================
# PAGE 1 - AQI Checker
# =========================================================
if page == PAGE_AQI:

    from aqi_fetcher import (
        get_coordinates,
        get_locations,
        get_latest_measurement,
        health_advice,
        personalised_risk,
        disease_warnings,
        general_tips,
    )

    st.title("Urban Health Risk Assistant")
    st.caption("Enter your profile, pick your area, get a personalised risk report.")

    # --- Step 1: profile ---
    st.subheader("Step 1: Your profile")

    city = st.text_input("City name", placeholder="e.g. Jaipur, Mumbai, Delhi").strip()

    age = st.slider(
        "Age",
        min_value=1, max_value=100, value=25, step=1,
        help="Drag to set your age"
    )
    if age < 5:
        st.caption("Infant (0-4) - high sensitivity group")
    elif age < 12:
        st.caption("Child (5-11) - high sensitivity group")
    elif age < 18:
        st.caption("Teen (12-17)")
    elif age < 65:
        st.caption("Adult (18-64)")
    else:
        st.caption("Senior (65+) - high sensitivity group")

    act_map = {0: "Low", 1: "Moderate", 2: "High"}
    act_desc = {
        0: "Mostly sedentary - desk work or rest",
        1: "Regular daily movement, light walks",
        2: "Active workouts, outdoor sports or manual labour",
    }
    act_val = st.select_slider(
        "Activity level",
        options=[0, 1, 2],
        value=1,
        format_func=lambda x: act_map[x],
        help="Higher activity means more air inhaled, so more exposure"
    )
    st.caption(act_desc[act_val])

    st.markdown("**Past or existing health conditions** (select all that apply)")

    disease_options = [
        "Asthma", "COPD", "Heart disease",
        "Hypertension", "Diabetes", "Allergies",
        "Sinusitis", "Pregnancy"
    ]

    cols = st.columns(4)
    selected_diseases = []
    for i, disease in enumerate(disease_options):
        with cols[i % 4]:
            checked = st.checkbox(disease, key=f"dis_{disease}")
            if checked:
                selected_diseases.append(disease)

    st.session_state.diseases = selected_diseases

    st.divider()

    find_disabled = not bool(city)
    if find_disabled:
        st.caption("Enter a city name to continue")

    if st.button("Find monitoring stations", disabled=find_disabled):
        with st.spinner(f"Searching stations near {city}..."):
            lat, lon = get_coordinates(city)
        if not lat:
            st.error("City not found. Check the spelling and try again.")
            st.stop()
        with st.spinner("Loading nearby stations..."):
            locations = get_locations(lat, lon)
        if not locations:
            st.error(
                f"No air quality monitoring stations found within 25 km of {city}. "
                "Try a larger nearby city."
            )
            st.stop()
        st.session_state.locations = locations
        st.session_state.city = city
        st.session_state.selected_area = None

    # --- Step 2: area selection ---
    if st.session_state.locations:
        st.divider()
        st.subheader("Step 2: Select your area")

        area_names = [loc["name"] for loc in st.session_state.locations]
        st.caption(f"Found {len(area_names)} station(s) near {st.session_state.city}")

        selected = st.selectbox(
            f"Stations near {st.session_state.city}",
            options=["-- Select an area --"] + area_names
        )

        if selected != "-- Select an area --":
            if st.button("Check air quality"):
                st.session_state.selected_area = selected

    # --- Step 3: results ---
    if st.session_state.get("selected_area"):
        st.divider()
        st.subheader(f"Step 3: Air quality at {st.session_state.selected_area}")

        selected_loc = next(
            (loc for loc in st.session_state.locations
             if loc["name"] == st.session_state.selected_area),
            None
        )
        if not selected_loc:
            st.error("Location data not found. Please reselect your area.")
            st.stop()

        sensors = selected_loc.get("sensors", [])
        useful_sensors = [
            s for s in sensors
            if s.get("parameter", {}).get("name") in ["pm25", "pm10"]
        ]
        if not useful_sensors:
            st.warning("No PM2.5 or PM10 sensors at this station.")
            st.stop()

        sensor_values = {}
        metric_cols = st.columns(len(useful_sensors))

        any_data = False
        for i, sensor in enumerate(useful_sensors):
            sensor_id = sensor["id"]
            param = sensor.get("parameter", {})
            param_name = param.get("name")
            display_name = param.get("displayName", param_name)
            unit = param.get("units", "")

            with st.spinner(f"Fetching {display_name}..."):
                value = get_latest_measurement(sensor_id)

            sensor_values[param_name] = value

            with metric_cols[i]:
                if value is not None:
                    any_data = True
                    st.metric(label=display_name, value=f"{value:.1f} {unit}")
                    status, color = health_advice(param_name, value)
                    if status:
                        if color == "green":
                            st.success(status)
                        elif color == "orange":
                            st.warning(status)
                        else:
                            st.error(status)
                else:
                    st.metric(label=display_name, value="No data")

        if not any_data:
            st.warning("This station hasn't reported recent readings. Results below may be limited.")

        st.divider()
        st.subheader("Your personalised risk")

        pm25 = sensor_values.get("pm25")
        risk_level, risk_color = personalised_risk(
            pm25, age, act_val, selected_diseases
        )

        if risk_color == "green":
            st.success(f"Overall personal risk: **{risk_level}**")
        elif risk_color == "orange":
            st.warning(f"Overall personal risk: **{risk_level}**")
        else:
            st.error(f"Overall personal risk: **{risk_level}**")

        if selected_diseases and pm25 is not None:
            st.markdown("**Condition-specific warnings:**")
            for warning in disease_warnings(selected_diseases, pm25):
                st.error(warning)

        st.markdown("**Recommendations for you:**")
        for tip in general_tips(pm25, age, act_val):
            st.info(tip)

        st.divider()
        if st.button("Check another area"):
            st.session_state.selected_area = None
            st.rerun()

# =========================================================
# PAGE 2 - Health Q&A (RAG)
# =========================================================
elif page == PAGE_QA:

    import time
    from rag import get_answer

    st.title("Health Q&A")
    st.caption("Ask anything about air quality and urban health. Answers are generated using WHO documents.")

    st.markdown("**Quick questions**")

    quick_qs = [
        "What are the health effects of PM2.5?",
        "How does AQI affect children and elderly?",
        "What precautions should I take on high pollution days?",
        "What is a safe AQI for outdoor exercise?",
        "How does air pollution affect asthma?",
    ]

    cols = st.columns(3)

    quick_clicked = False
    for i, q in enumerate(quick_qs):
        with cols[i % 3]:
            if st.button(q, key=f"qq_{i}"):
                st.session_state["active_q"] = q
                quick_clicked = True

    default_q = st.session_state.get("active_q", "")

    question = st.text_input(
        "Ask your question",
        value=default_q,
        placeholder="e.g. What are the effects of PM2.5 on asthma?"
    )

    ask_clicked = st.button("Ask", disabled=not question.strip())

    # Run the query if the Ask button was pressed, or a quick question was
    # just clicked (so the user doesn't have to click twice).
    run_query = ask_clicked or quick_clicked
    active_question = question if ask_clicked else (st.session_state.get("active_q") or question)

    if quick_clicked:
        st.session_state["active_q"] = active_question

    if run_query and active_question.strip():
        try:
            start = time.time()

            with st.spinner("Searching WHO knowledge base..."):
                answer, sources = get_answer(active_question)

            elapsed = time.time() - start

        except Exception as exc:
            st.error("Could not generate an answer.")

            with st.expander("Error details"):
                st.code(str(exc))

            st.stop()

        st.divider()
        st.success("**Answer**")
        st.write(answer)
        st.caption(f"Response generated in {elapsed:.2f} seconds")

        if sources:
            with st.expander(f"View {len(sources)} source excerpt(s)"):
                for i, src in enumerate(sources, 1):
                    page_info = f" (page {src['page']})" if src.get("page") is not None else ""
                    st.markdown(f"**Source {i}{page_info}**")
                    st.markdown(
                        f'<div class="source-card">{src["snippet"]}</div>',
                        unsafe_allow_html=True
                    )