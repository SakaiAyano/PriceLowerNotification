from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
import time
import math
import boto3
import urllib3
import json
import os
from decimal import Decimal
import pickle
import os.path
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow

dynamo_db = boto3.resource('dynamodb')
saved_cart_item_table = dynamo_db.Table('saved_cart_item')
scope = ['https://www.googleapis.com/auth/gmail.readonly']

amazon_id = os.environ['AMAZON_ID']
amazon_password = os.environ['AMAZON_PASSWORD']
slack_url = os.environ['SLACK_URL']
slack_user_id = os.environ['SLACK_USER_ID']


# gmailAPI OAuth2認証機能
def google_get_auth():
    creds = None
    if os.path.exists('/tmp/token.pickle'):
        with open('/tmp/token.pickle', 'rb') as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', scope)
            creds = flow.run_local_server()
        # Todo:「Please visit this URL to authorize this application:
        #  https://accounts.google.com/o/oauth2/・・」で手動で認可する必要あり →完全な自動化は不可能と思われる、、
        with open('/tmp/token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    return build('gmail', 'v1', credentials=creds)


# テーブルスキャン
def table_scan():
    scan_data = saved_cart_item_table.scan()
    if 'Items' in scan_data:
        data_items = scan_data['Items']
        return data_items


# 項目検索
def get_data_price(asin_code):
    query_data = saved_cart_item_table.get_item(Key={'asin_code': asin_code})
    if 'Item' in query_data:
        item = query_data['Item']
        return item['price']
    return


def add_record(asin_code, price):
    saved_cart_item_table.put_item(
        Item={
            'asin_code': asin_code,
            'price': price
        }
    )


def delete_recodes(deleted_saved_cart_asin_codes):
    with saved_cart_item_table.batch_writer() as batch:
        for deleted_saved_cart_asin_code in deleted_saved_cart_asin_codes:
            batch.delete_item(Key={'asin_code': deleted_saved_cart_asin_code})


# Slackへの通知処理
def price_lower_notification(price_lower_items):
    http = urllib3.PoolManager()
    items_list = ''
    for price_lower_item_name in price_lower_items:
        items_list += '★' + price_lower_item_name['item_name'] + '  ' \
                      + str(price_lower_item_name['data_price']) + '円→' \
                      + str(price_lower_item_name['price']) + '円\n '

    msg = {
        'attachments': [
            {
                'fallback': 'Amazon商品の値下げお知らせ',
                'pretext': '<@' + slack_user_id + '>',
                'color': '#D00000',
                'fields': [
                    {
                        'title': '以下の商品が20%OFFになりました。',
                        'value': items_list
                    }
                ]
            }
        ]
    }

    encoded_msg = json.dumps(msg).encode('utf-8')
    http.request('POST', slack_url, body=encoded_msg)


def lambda_handler(event, context):
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--single-process')
    options.binary_location = '/opt/headless/python/bin/headless-chromium'
    browser = webdriver.Chrome('/opt/headless/python/bin/chromedriver', options=options)
    browser.implicitly_wait(10)

    # Amazonのログイン画面
    browser.get('https://qr.paps.jp/t6xn7')
    email_elem = browser.find_element_by_id('ap_email')
    email_elem.send_keys(amazon_id)

    next_button = browser.find_element_by_class_name('a-button-input')
    next_button.click()
    time.sleep(1)

    password_elem = browser.find_element_by_id('ap_password')
    password_elem.send_keys(amazon_password)

    next_button = browser.find_element_by_id('signInSubmit')
    next_button.click()
    time.sleep(20)

    # TODO:Amazon側ではログイン時にセキュリティメールを送信することがある。登録したメール側から承認する作業を行う必要がある
    # ※新しく別ドライブを立ち上げてGmailに自動ログインするのはGoogleセキュリティ上、現在不可能
    # Oauth2よりGmailAPIを使用したいが手動で作業が必要となり、下記google_get_auth関数は自動で動作しない
    google_get_auth()

    cart_button = browser.find_element_by_id('nav-cart')
    cart_button.click()
    time.sleep(1)

    # 画面描画のため（「後で買うリスト」全ての商品情報）を取得するため画面下までスクロール
    html = browser.find_element_by_tag_name('html')
    html.send_keys(Keys.END)
    time.sleep(1)

    saved_cart_items = browser.find_elements_by_css_selector('.a-row.sc-list-item.sc-java-remote-feature')
    item_names = browser.find_elements_by_css_selector('.a-truncate.a-size-base-plus .a-truncate-full')

    asin_codes = []
    price_lower_items = []

    for saved_cart_item, item_name in zip(saved_cart_items, item_names):
        asin_code = saved_cart_item.get_attribute('data-asin')
        # TODO:Amazon側では価格情報を小数第一を含めて表示しているが、小数第一を切り捨て対応（小数第一が0以外の商品が損じあスる可能性もあり得る？）
        price = math.floor(float(saved_cart_item.get_attribute('data-price')))
        item_name = item_name.get_attribute("innerHTML")

        # 在庫切れ商品や出品者が取り下げた商品については価格情報が0円で取得されているためそういった商品は取り扱わない
        if price != 0:
            data_price = get_data_price(asin_code)
            if not data_price:
                add_record(asin_code, price)
            else:
                data_price_20_off = data_price * Decimal(80 / 100)
                if data_price_20_off >= price:
                    price_lower_items.append({'item_name': item_name, 'data_price': data_price, 'price': price})
                add_record(asin_code, price)

        asin_codes.append(asin_code)

    if len(price_lower_items) != 0:
        price_lower_notification(price_lower_items)

    data_items = table_scan()
    data_asin_codes = []
    for data_item in data_items:
        data_asin_codes.append(data_item['asin_code'])

    # 対象差集合
    # dynamoDBには存在するがcart内には存在しないasinコードを検索→cart画面から削除された商品
    deleted_saved_cart_asin_codes = set(data_asin_codes) ^ set(asin_codes)

    if len(deleted_saved_cart_asin_codes) != 0:
        delete_recodes(deleted_saved_cart_asin_codes)

    browser.quit()
