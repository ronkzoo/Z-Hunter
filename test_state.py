import streamlit as st
import pandas as pd
df = pd.DataFrame({"A": [1], "B": [2]})
event = st.dataframe(df, on_select="rerun", selection_mode="single-cell")
print(type(event))
print(dir(event))
print(event.selection)
