import numpy as np
import pandas as pd
import pandas_ta as ta

def calculate_hurst(series, max_lag=20):
    """
    시계열의 허스트 지수를 계산합니다. (RS Analysis)
    Hurst Exponent 산출을 통해 현재 시장이 평균회귀(Mean Reversion)인지 추세(Trend) 국면인지 판단합니다.
    """
    lags = range(2, max_lag)
    if len(series) < max_lag or np.std(series) == 0:
        return 0.5
    try:
        tau = [np.sqrt(np.std(np.subtract(series[lag:], series[:-lag]))) for lag in lags]
        poly = np.polyfit(np.log(lags), np.log(tau), 1)
        return poly[0] * 2.0
    except:
        return 0.5

def add_zscore_features(df, window=20, column='Close', ma_name='MA', std_name='STD', z_name='Z-Score'):
    """
    주어진 윈도우(기본 20일)에 대한 이동평균과 표준편차를 구하고, 이를 바탕으로 Z-Score를 계산해 DataFrame에 추가합니다.
    """
    df[ma_name] = df[column].rolling(window=window).mean()
    df[std_name] = df[column].rolling(window=window).std()
    df[z_name] = (df[column] - df[ma_name]) / df[std_name]
    return df

def add_adx_feature(df, length=14, adx_name='ADX'):
    """
    ADX(Average Directional Index) 지표를 계산하여 DataFrame에 추가합니다.
    추세의 강도를 판단하는 데 사용됩니다.
    """
    adx_df = df.ta.adx(length=length)
    if adx_df is not None and f'ADX_{length}' in adx_df.columns:
        df[adx_name] = adx_df[f'ADX_{length}']
    else:
        df[adx_name] = 0
    return df

def add_moving_averages(df, windows=[5, 20, 60], column='Close', prefix='MA'):
    """
    입력된 윈도우 리스트에 대한 이동평균선(MA)들을 한 번에 계산하여 DataFrame에 추가합니다.
    """
    for w in windows:
        df[f'{prefix}{w}'] = df[column].rolling(window=w).mean()
    return df
