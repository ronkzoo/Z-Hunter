import streamlit as st

import FinanceDataReader as fdr

@st.cache_data(ttl=86400) # cache for 1 day
def get_krx_stocks():
    df = fdr.StockListing("KRX")
    df = df[["Code", "Name", "Market"]]
    
    # Add suffixes for Yahoo Finance
    def get_suffix(market):
        if market == 'KOSPI': return '.KS'
        elif 'KOSDAQ' in market: return '.KQ'
        return '.KS' # Default fallback
    
    df['YfCode'] = df['Code'] + df['Market'].apply(get_suffix)
    return df
