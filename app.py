import streamlit as st
import pandas as pd
import io
import os

# --- Page config ---
st.set_page_config(
    page_title="ABS Journal Filter",
    page_icon="📚",
    layout="centered"
)

# --- Load the bundled ABS list ---
@st.cache_data
def load_abs():
    base_dir = os.path.dirname(__file__)
    abs_path = os.path.join(base_dir, "ABS_with_ISSN.xlsx")
    df = pd.read_excel(abs_path)
    df['match_title'] = df['Journal Title'].astype(str).str.lower().str.strip()
    return df

abs_df = load_abs()

# --- Ranking order for filtering ---
RANK_ORDER = ['1', '2', '3', '4', '4*']

# --- UI ---
st.title("📚 ABS Journal Filter")
st.markdown(
    "Upload your **Scopus CSV export** and get back only the articles "
    "published in journals listed on the **ABS Academic Journal Guide 2024**."
)

st.divider()

# Step 1: Star rating filter
st.subheader("Step 1 — Choose minimum ABS ranking")
rank_labels = {
    '1':  '⭐ 1 — All ABS journals',
    '2':  '⭐⭐ 2 and above',
    '3':  '⭐⭐⭐ 3 and above',
    '4':  '⭐⭐⭐⭐ 4 and above',
    '4*': '⭐⭐⭐⭐✨ 4* only (world elite)',
}
min_rank = st.radio(
    label="Keep articles from journals rated at least:",
    options=list(rank_labels.keys()),
    format_func=lambda x: rank_labels[x],
    index=1  # default: 2 and above
)

# Step 2: Upload
st.subheader("Step 2 — Upload your Scopus CSV")
uploaded_file = st.file_uploader(
    "Drag and drop your Scopus export here",
    type=["csv"],
    help="Export your results from Scopus as CSV (all fields)."
)

if uploaded_file:
    # --- Read Scopus file ---
    try:
        scopus_df = pd.read_csv(uploaded_file, encoding='utf-8-sig')
    except Exception:
        scopus_df = pd.read_csv(uploaded_file, encoding='latin-1')

    if 'Source title' not in scopus_df.columns:
        st.error(
            "❌ Could not find a 'Source title' column in your CSV. "
            "Please make sure you exported from Scopus with all fields included."
        )
        st.stop()

    scopus_df['match_title'] = scopus_df['Source title'].astype(str).str.lower().str.strip()

    # --- Filter ABS list by minimum ranking ---
    selected_ranks = RANK_ORDER[RANK_ORDER.index(min_rank):]
    abs_filtered = abs_df[abs_df['AJG 2024'].isin(selected_ranks)]
    abs_to_merge = abs_filtered[['match_title', 'AJG 2024']].drop_duplicates(subset=['match_title'])
    abs_to_merge = abs_to_merge.rename(columns={'AJG 2024': 'ABS Ranking'})

    # --- Merge ---
    merged_df = scopus_df.merge(abs_to_merge, on='match_title', how='inner')
    merged_df = merged_df.drop(columns=['match_title'])

    total_input = len(scopus_df)
    total_output = len(merged_df)

    st.divider()
    st.subheader("Step 3 — Results")

    col1, col2, col3 = st.columns(3)
    col1.metric("Articles uploaded", total_input)
    col2.metric("Articles matched", total_output)
    col3.metric("Filtered out", total_input - total_output)

    if total_output == 0:
        st.warning(
            "⚠️ No articles matched. This might be due to journal name formatting differences. "
            "Try lowering the minimum ranking, or check that your Scopus export includes the 'Source title' column."
        )
    else:
        # Preview
        st.markdown("**Preview of matched articles:**")
        preview_cols = ['Authors', 'Title', 'Source title', 'Year', 'ABS Ranking']
        available_cols = [c for c in preview_cols if c in merged_df.columns]
        st.dataframe(merged_df[available_cols].head(10), use_container_width=True)

        # Breakdown by ranking
        st.markdown("**Breakdown by ABS ranking:**")
        breakdown = merged_df['ABS Ranking'].value_counts().reindex(
            [r for r in reversed(RANK_ORDER) if r in merged_df['ABS Ranking'].values]
        ).reset_index()
        breakdown.columns = ['ABS Ranking', 'Count']
        st.dataframe(breakdown, use_container_width=True, hide_index=True)

        # Download
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            merged_df.to_excel(writer, index=False, sheet_name='Filtered Articles')
        output.seek(0)

        st.download_button(
            label="⬇️ Download filtered list as Excel",
            data=output,
            file_name="Filtered_Scopus_ABS.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

st.divider()
st.caption("ABS Academic Journal Guide 2024 · Built with Streamlit · Made by Karol")
