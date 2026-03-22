import re

with open("regime_risk_manager.py", "r", encoding="utf-8") as f:
    code = f.read()

# Remove _calc_hurst
code = re.sub(r'    def _calc_hurst.*?return poly\[0\] \* 2\.0\n', '', code, flags=re.DOTALL)

# Replace self._calc_hurst
code = code.replace("self._calc_hurst", "calculate_hurst")

# Update preparation
code = code.replace(
"""        df['MA20'] = df['Close'].rolling(window=20).mean()
        df['STD20'] = df['Close'].rolling(window=20).std()
        df['Z-Score'] = (df['Close'] - df['MA20']) / df['STD20']""",
"""        df = add_zscore_features(df, window=20, ma_name='MA20', std_name='STD20', z_name='Z-Score')"""
)

code = code.replace(
"""        adx_df = df.ta.adx(length=14)
        df['ADX'] = adx_df['ADX_14'] if adx_df is not None else 0""",
"""        df = add_adx_feature(df, length=14, adx_name='ADX')"""
)

# Add imports
if 'from indicators import' not in code:
    code = code.replace(
        "import pandas_ta as ta\nfrom typing import Tuple, Dict",
        "import pandas_ta as ta\nfrom typing import Tuple, Dict\nfrom indicators import calculate_hurst, add_zscore_features, add_adx_feature"
    )

with open("regime_risk_manager.py", "w", encoding="utf-8") as f:
    f.write(code)
