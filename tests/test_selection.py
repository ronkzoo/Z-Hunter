import streamlit as st
import pandas as pd
df = pd.DataFrame({"A": [1, 2], "B": [3, 4]})
e = st.dataframe(df, on_select="rerun", selection_mode=["single-row"])
st.write(type(e))
st.write(dir(e))
