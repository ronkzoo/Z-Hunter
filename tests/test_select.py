import streamlit as st
import pandas as pd
df = pd.DataFrame({'티커': ['AAPL', 'MSFT'], 'A': [1,2]})
e = st.dataframe(df, on_select="rerun", selection_mode=["single-row"])
st.write("Event:", e)
if isinstance(e, dict) and e.get("selection", {}).get("rows"):
    st.write("Selected:", df.iloc[e["selection"]["rows"][0]]["티커"])
