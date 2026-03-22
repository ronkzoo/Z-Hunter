import re

with open('data_loader.py', 'r', encoding='utf-8') as f:
    code = f.read()

# Remove calculate_hurst
code = re.sub(r'def calculate_hurst.*?except:\n        return 0\.5\n', '', code, flags=re.DOTALL)

# Add imports
if 'from indicators import' not in code:
    code = code.replace(
        'from utils import get_ticker_name',
        'from utils import get_ticker_name\nfrom indicators import calculate_hurst, add_zscore_features, add_adx_feature, add_moving_averages'
    )

# Replace in backtest_symbol
code = code.replace(
"""        # 지표 산출
        df['MA'] = df['Close'].rolling(window=20).mean()
        df['STD'] = df['Close'].rolling(window=20).std()
        df['Z-Score'] = (df['Close'] - df['MA']) / df['STD']
        
        adx_df = df.ta.adx(length=14)
        df['ADX'] = adx_df['ADX_14'] if adx_df is not None else 0""",
"""        # 지표 산출
        df = add_zscore_features(df)
        df = add_adx_feature(df)"""
)

# Replace in get_hybrid_signal
code = code.replace(
"""        df['MA5'] = df['Close'].rolling(window=5).mean()
        df['MA20'] = df['Close'].rolling(window=20).mean()
        df['MA60'] = df['Close'].rolling(window=60).mean()
        df['STD20'] = df['Close'].rolling(window=20).std()
        df['Z-Score'] = (df['Close'] - df['MA20']) / df['STD20']""",
"""        df = add_moving_averages(df, windows=[5, 20, 60])
        df = add_zscore_features(df, window=20, ma_name='MA20', std_name='STD20', z_name='Z-Score')"""
)

# Replace in get_live_signal
code = code.replace(
"""        df['MA'] = df['Close'].rolling(window=20).mean()
        df['STD'] = df['Close'].rolling(window=20).std()
        df['Z-Score'] = (df['Close'] - df['MA']) / df['STD']
        
        adx_df = df.ta.adx(length=14)
        df['ADX'] = adx_df['ADX_14'] if adx_df is not None else 0""",
"""        df = add_zscore_features(df)
        df = add_adx_feature(df)"""
)

with open('data_loader.py', 'w', encoding='utf-8') as f:
    f.write(code)
