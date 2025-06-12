# -*- coding: utf-8 -*-

# !pip install -qqU matplotlib seaborn requests beautifulsoup4 scikit-learn nltk --no-cache-dir
# !pip install -qqU google-genai pillow kaleido yfinance anvil-uplink tabulate --no-cache-dir

# @title genai initialization

from google import genai
from PIL import Image
import io
import requests
import datetime
from zoneinfo import ZoneInfo

ny_now = datetime.datetime.now(ZoneInfo('America/New_York'))

client = genai.Client(api_key=GOOGLE_API_KEY)

MODEL_ID = 'gemini-2.5-flash-preview-04-17' # @param ['gemini-2.0-flash-lite','gemini-2.0-flash','gemini-2.5-flash-preview-04-17','gemini-2.5-pro-exp-03-25']

SYSTEM_INST_trade = '''
You are a Stock Trader specializing in Technical Analysis at a top financial institution.
Analyze the stock chart technical indicators and provide a buy/hold/sell recommendation.
Base your recommendation only on the candlestick chart and the displayed technical indicators.
First, provide the recommendation, then, provide your detailed reasoning.
'''

SYSTEM_INST_code = '''
You are an expert software developer and a helpful coding assistant.
You are able to generate high-quality code in any programming language.
'''

CHAT_CONFIG = genai.types.GenerateContentConfig(
    max_output_tokens = 500,
    temperature = 0.1,
    system_instruction = SYSTEM_INST_trade # @param ['SYSTEM_INST_trade','SYSTEM_INST_code'] {'type':'raw'}
)

# @title anvil uplink

import anvil.server

anvil.server.connect(ANVIL_UPLINK_KEY)

"""# 1 Chart"""

# @title yfinance

import yfinance as yf

# internal
def get_df(stock_str):
    spy = yf.Ticker(stock_str)

    period = '1y' # @param ['1d', '5d', '1mo', '3mo', '6mo', '1y', '2y', '5y', '10y', 'ytd', 'max']
    interval = '1d' # @param ['1m', '2m', '5m', '15m', '30m', '60m', '90m', '1h', '4h', '1d', '5d', '1wk', '1mo', '3mo']
    df = spy.history(period=period, interval=interval, actions=False)

    # ema
    df['EMA20'] = df['Close'].ewm(span=20, adjust=False).mean()

    # bollinger
    df['MB'] = df['Close'].rolling(window=20).mean()

    df['StdDev'] = df['Close'].rolling(window=20).std()

    df['UB'] = df['MB'] + 2 * df['StdDev']
    df['LB'] = df['MB'] - 2 * df['StdDev']

    return df

@anvil.server.callable
def test_ticker(stock_str):
    if stock_str == '':
        return False
    else:
        test = yf.Ticker(stock_str)

    try:
        test.info
        return True
    except Exception as e:
        return False

@anvil.server.callable
def get_df_markdown(stock_str):
    df2 = get_df(stock_str)[['Open', 'High', 'Low', 'Close', 'Volume']]

    # code volumn column so tabulate won't affect
    df2['Volume'] = df2['Volume'].apply(lambda x: f'{x:,}')

    # code index column as str
    new_index = df2.index.strftime('%Y-%m-%d %Z%z')
    df2.index = new_index

    # rest are float columns
    df_markdown = df2.tail(20)[::-1].to_markdown(floatfmt='.2f', stralign='right')

    return df_markdown

# @title plotly

import plotly.graph_objects as go

@anvil.server.callable
def get_fig_data(stock_str):
    df = get_df(stock_str)

    data = [go.Candlestick(x=df.index,
                            open=df['Open'],
                            high=df['High'],
                            low=df['Low'],
                            close=df['Close'],
                            name='Candlestick'
                            ),
            go.Scatter(x=df.index,
                    y=df['EMA20'],
                    mode='lines',
                    name='EMA 20',
                    line={'color':'orange'}
                    ),
            go.Scatter(x=df.index,
                    y=df['MB'],
                    mode='lines',
                    name='Middle Band (SMA 20)',
                    line={'color':'blue'}
                    ),
            go.Scatter(x=df.index,
                    y=df['UB'],
                    mode='lines',
                    name='Upper Band',
                    line={'color':'grey', 'dash':'dot'}
                    ),
            go.Scatter(x=df.index,
                    y=df['LB'],
                    mode='lines',
                    name='Lower Band',
                    line={'color':'grey', 'dash':'dot'}
                    )
    ]

    tickvals = df.iloc[::20].index
    ticktext = [d.strftime('%Y-%m-%d') for d in tickvals]

    layout = go.Layout(
        title=stock_str + ', 1y 1d chart',
        xaxis_title='Date',
        yaxis_title='Price',
        xaxis_rangeslider_visible=False,
        width=1800,
        height=800,
        xaxis=dict(
            type='category',
            tickvals=tickvals,
            ticktext=ticktext
        ),
        legend=dict(
            x=0.01,
            y=0.99,
            xanchor='left',
            yanchor='top'
        ),
        margin=dict(
            l=40,
            r=20,
            b=40,
            t=40,
            pad=0
        )
    )

    return data, layout

# internal
def get_fig(stock_str):
    data, layout = get_fig_data(stock_str)
    fig = go.Figure(data=data, layout=layout)
    return fig

# @title gemini old

# internal
def ask_google_chart_deleted(stock_str):
    fig = get_fig(stock_str)
    img_bytes = fig.to_image(format='png')
    image = Image.open(io.BytesIO(img_bytes))

    prompt = '''
    You are a Stock Trader specializing in Technical Analysis at a top financial institution.
    Analyze the stock chart based on its candlestick chart and the displayed technical indicators.
    Provide a detailed justification of your analysis, explaining what patterns, signals, and trends you observe.
    Then, based solely on the chart, provide a recommendation from the following options:
    'Strong Buy', 'Buy', 'Weak Buy', 'Hold', 'Weak Sell', 'Sell', or 'Strong Sell'.
    '''

    # token
    token = client.models.count_tokens(
        model = MODEL_ID,
        contents = [image, prompt]
    )

    # chat
    response = client.models.generate_content(
        model = MODEL_ID,
        # config = CHAT_CONFIG,
        contents=[image, prompt]
    )

    re = f'{stock_str}, 1y 1d chart\n'
    re += f'{MODEL_ID}, token count: {int(token.total_tokens):,}\n'
    re += response.text

    # response in markdown
    return re

# @title gemini new

# global
_global_ai_output = ''
_global_ai_complete = False

@anvil.server.background_task
def ask_google_chart(stock_str):
    global _global_ai_output, _global_ai_complete

    # reset
    _global_ai_output = ''
    _global_ai_complete = False

    # fig
    fig = get_fig(stock_str)
    img_bytes = fig.to_image(format='png')
    image = Image.open(io.BytesIO(img_bytes))

    prompt = '''
    You are a Stock Trader specializing in Technical Analysis at a top financial institution.
    Analyze the stock chart based on its candlestick chart and the displayed technical indicators.
    Provide a detailed justification of your analysis, explaining what patterns, signals, and trends you observe.
    Then, based solely on the chart, provide a recommendation from the following options:
    'Strong Buy', 'Buy', 'Weak Buy', 'Hold', 'Weak Sell', 'Sell', or 'Strong Sell'.
    '''

    # token
    token = client.models.count_tokens(
        model = MODEL_ID,
        contents = [image, prompt]
    )

    _global_ai_output = f'{stock_str}, 1y 1d chart\n'
    _global_ai_output += f'{MODEL_ID}, token count: {int(token.total_tokens):,}\n'

    # chat
    response = client.models.generate_content_stream(
        model = MODEL_ID,
        # config = CHAT_CONFIG,
        contents=[image, prompt]
    )

    for chunk in response:
        _global_ai_output += chunk.text

    # return
    _global_ai_complete = True

@anvil.server.callable
def start_google(stock_str):
    anvil.server.launch_background_task('ask_google_chart', stock_str)
    return 'started'

@anvil.server.callable
def stream_google_result():
    global _global_ai_output, _global_ai_complete
    return _global_ai_output, _global_ai_complete

"""# 2 Option"""

# @title yfinance

import yfinance as yf

@anvil.server.callable
def get_opt_dates_yf(stock_str):
    spy = yf.Ticker(stock_str)

    return spy.options

# @title exp date

# internal
def get_opt_chain_yf(stock_str, exp_str):
    ticker = yf.Ticker(stock_str)
    current = ticker.history(period='1d')['Close'].iloc[0]
    offset = 20

    # dfs
    dfcall = ticker.option_chain(exp_str).calls
    csvcall = dfcall.to_csv(index=False)
    dfcallcenter = dfcall[(dfcall['strike'] > current - offset) & (dfcall['strike'] < current + offset)]

    dfput = ticker.option_chain(exp_str).puts
    csvput = dfput.to_csv(index=False)
    dfputcenter = dfput[(dfput['strike'] > current - offset) & (dfput['strike'] < current + offset)]

    return dfcall, csvcall, dfput, csvput

@anvil.server.callable
def get_opt_markdown_yf(stock_str, exp_str):
    dfcall, csvcall, dfput, csvput = get_opt_chain_yf(stock_str, exp_str)

    cols = ['contractSymbol', 'strike', 'bid', 'ask', 'change',
            'percentChange', 'volume', 'openInterest', 'impliedVolatility']

    dfcall = dfcall[cols].copy()
    dfcall['volume'] = dfcall['volume'].fillna(0).apply(lambda x: f'{x:,.0f}')
    dfcall['openInterest'] = dfcall['openInterest'].fillna(0).apply(lambda x: f'{x:,.0f}')

    dfput = dfput[cols].copy()
    dfput['volume'] = dfput['volume'].fillna(0).apply(lambda x: f'{x:,.0f}')
    dfput['openInterest'] = dfput['openInterest'].fillna(0).apply(lambda x: f'{x:,.0f}')

    return (dfcall.to_markdown(index=False, floatfmt='.2f', stralign='right'),
            dfput.to_markdown(index=False, floatfmt='.2f', stralign='right')
    )

# @title gemini

@anvil.server.callable
def ask_google_csv(stock_str, exp_str, main=True):

    if main:
        # yf library
        exp_str = exp_str.replace(':w','').replace(':m','')
        dfcall, csvcall, dfput, csvput = get_opt_chain_yf(stock_str, exp_str)
    else:
        # backup method
        dfcall, csvcall, dfput, csvput, code = get_opt_chain_oc(stock_str, exp_str)

    prompt = f'Today is {ny_now.strftime("%Y-%m-%d")}' + '''
    You are a Stock Trader specializing in Technical Analysis at a top financial institution.
    Analyze the stock option chain of both calls and puts.
    Provide a detailed justification of your analysis, explaining what patterns, signals, and trends you observe.
    Then, based solely on the option chain, provide a recommendation from the following options:
    'Strong Buy', 'Buy', 'Weak Buy', 'Hold', 'Weak Sell', 'Sell', or 'Strong Sell'.
    '''

    # token
    token = client.models.count_tokens(
        model = MODEL_ID,
        contents = [prompt, csvcall, csvput]
    )

    # chat
    response = client.models.generate_content(
        model = MODEL_ID,
        contents = [prompt, csvcall, csvput]
    )

    re = f'{stock_str}, Expiration: {exp_str}\n'
    re += f'{MODEL_ID}, token count: {int(token.total_tokens):,}\n'
    re += response.text

    # response in markdown
    return re

"""# 3 Option backup"""

# !pip install -q -U selenium lxml
# !apt-get update -qq
# !apt-get install -qq chromium-chromedriver

# @title fetch option dates

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
import datetime
import io
import time
import pandas as pd

# internal
def fetch_selenium(url):
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    user_agent = ('Mozilla/5.0 (X11; CrOS x86_64 14541.0.0) AppleWebKit/537.36 '
                '(KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36')
    options.add_argument(f'--user-agent={user_agent}')

    driver = webdriver.Chrome(options=options)
    driver.get(url)
    time.sleep(2)
    html = driver.page_source
    driver.quit()

    return html

@anvil.server.callable
def get_opt_dates_oc(stock_str):
    try:
        html = fetch_selenium(f'https://optioncharts.io/options/{stock_str}/option-chain')

        soup = BeautifulSoup(html, 'html.parser')

        target_input = soup.find_all('input', {'name': 'expiration_date[]'})

        option_dates = [i['value'] for i in target_input]

        return option_dates
    except Exception as e:
        return [ny_now.strftime('%Y-%m-%d')]

# @title fetch option data

# internal
def get_opt_chain_oc(stock_str, exp_str):
    try:
        # try yahoo first
        exp_str = exp_str.replace(':w','').replace(':m','')
        stamp = int(datetime.datetime.strptime(exp_str, '%Y-%m-%d').timestamp())
        url = (f'https://finance.yahoo.com/quote/{stock_str}/options/?'
                f'straddle=false&date={stamp}'
        )
        html = fetch_selenium(url)
        df = pd.read_html(io.StringIO(html))

        # df
        dfcall = df[0]
        dfput = df[1]

        if len(dfcall) == 1:
            raise Exception('no yahoo dates')

        # int column clean up
        arr = ['Volume', 'Open Interest']
        for col in arr:
            dfcall[col] = dfcall[col].astype(str).str.replace('-', '0')
            dfcall[col] = pd.to_numeric(dfcall[col], errors='coerce')
            dfput[col] = dfput[col].astype(str).str.replace('-', '0')
            dfput[col] = pd.to_numeric(dfput[col], errors='coerce')

        # csv
        csvcall = dfcall.to_csv(index=False)
        csvput = dfput.to_csv(index=False)

        return dfcall, csvcall, dfput, csvput, 1
    except Exception as e:
        try:
            # try oc second
            url = (f'https://optioncharts.io/options/{stock_str}/option-chain?'
                    f'option_type=all&expiration_dates={exp_str}&view=list&strike_range=all'
            )
            html = fetch_selenium(url)
            df = pd.read_html(io.StringIO(html))

            # df
            dfcall = df[0]
            dfput = df[4]

            # csv
            csvcall = dfcall.to_csv(index=False)
            csvput = dfput.to_csv(index=False)

            return dfcall, csvcall, dfput, csvput, 2
        except Exception as e:
            return None, None, None, None, 3

# @title fetch option markdown

@anvil.server.callable
def get_opt_markdown_oc(stock_str, exp_str):

    # exp_str has :w or :m
    # will try yahoo first then oc
    dfcall, csvcall, dfput, csvput, code = get_opt_chain_oc(stock_str, exp_str)

    if code == 1:
        # yahoo html worked
        cols = ['Contract Name', 'Strike', 'Bid', 'Ask', 'Change',
                '% Change', 'Volume', 'Open Interest', 'Implied Volatility']

        dfcall = dfcall[cols].copy()
        dfcall['Volume'] = dfcall['Volume'].fillna(0).apply(lambda x: f'{x:,.0f}')
        dfcall['Open Interest'] = dfcall['Open Interest'].fillna(0).apply(lambda x: f'{x:,.0f}')

        dfput = dfput[cols].copy()
        dfput['Volume'] = dfput['Volume'].fillna(0).apply(lambda x: f'{x:,.0f}')
        dfput['Open Interest'] = dfput['Open Interest'].fillna(0).apply(lambda x: f'{x:,.0f}')

        return (dfcall.to_markdown(index=False, floatfmt='.2f', stralign='right'),
                dfput.to_markdown(index=False, floatfmt='.2f', stralign='right')
        )
    elif code == 2:
        # oc html worked
        exp_new = exp_str[2:].replace('-','').replace(':w','').replace(':m','')

        dfcall = dfcall.drop(['Last Price', 'Mid'], axis=1).copy()
        dfcall['symbol'] = stock_str + exp_new + 'C' + (dfcall['Strike']*100).astype(int).astype(str)
        dfcall['Volume'] = dfcall['Volume'].fillna(0).apply(lambda x: f'{x:,.0f}')
        dfcall['Open Interest'] = dfcall['Open Interest'].fillna(0).apply(lambda x: f'{x:,.0f}')

        dfcallcols = dfcall.columns.tolist()
        dfcallcols.remove('symbol')
        dfcallcols.insert(0, 'symbol')
        dfcall = dfcall[dfcallcols].copy()

        dfput = dfput.drop(['Last Price', 'Mid'], axis=1).copy()
        dfput['symbol'] = stock_str + exp_new + 'P' + (dfput['Strike']*100).astype(int).astype(str)
        dfput['Volume'] = dfput['Volume'].fillna(0).apply(lambda x: f'{x:,.0f}')
        dfput['Open Interest'] = dfput['Open Interest'].fillna(0).apply(lambda x: f'{x:,.0f}')

        dfputcols = dfput.columns.tolist()
        dfputcols.remove('symbol')
        dfputcols.insert(0, 'symbol')
        dfput = dfput[dfputcols].copy()

        return (dfcall.to_markdown(index=False, floatfmt='.2f', stralign='right'),
                dfput.to_markdown(index=False, floatfmt='.2f', stralign='right')
        )
    else:
        return None, None

"""# 4 Earning"""

# @title fetch

@anvil.server.callable
def get_earning():
    tomorrow = ny_now + datetime.timedelta(days=1)

    # today
    url1 = f'https://finance.yahoo.com/calendar/earnings?day={ny_now.strftime("%Y-%m-%d")}&offset=0&size=15'
    html1 = fetch_selenium(url1)
    df1 = pd.read_html(io.StringIO(html1))

    # tomorrow
    url2 = f'https://finance.yahoo.com/calendar/earnings?day={tomorrow.strftime("%Y-%m-%d")}&offset=0&size=15'
    html2 = fetch_selenium(url2)
    df2 = pd.read_html(io.StringIO(html2))

    re1 = df1[0].dropna(axis=0, how='all').dropna(axis=1, how='all')
    re2 = df2[0].dropna(axis=0, how='all').dropna(axis=1, how='all')

    return (re1.to_markdown(index=False, floatfmt='.2f', stralign='right'),
            re2.to_markdown(index=False, floatfmt='.2f', stralign='right')
    )

"""# 5 anvil"""

anvil.server.wait_forever()
