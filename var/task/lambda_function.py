from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time
import math
import boto3
import urllib3
import json
import os
from decimal import Decimal
import re

dynamo_db = boto3.resource('dynamodb')
wish_list_table = dynamo_db.Table('wish_list')

slack_url = os.environ['SLACK_URL']
slack_user_id = os.environ['SLACK_USER_ID']
wish_list_url = os.environ['WISH_LIST_URL']

# テーブルスキャン
def table_scan():
    scan_data = wish_list_table.scan()
    if 'Items' in scan_data:
        data_items = scan_data['Items']
        return data_items


# 項目検索
def get_data_price(asin_code):
    query_data = wish_list_table.get_item(Key={'asin_code': asin_code})
    if 'Item' in query_data:
        item = query_data['Item']
        return item['price']
    return


def add_record(asin_code, price):
    wish_list_table.put_item(
        Item={
            'asin_code': asin_code,
            'price': price
        }
    )


def delete_recodes(deleted_saved_cart_asin_codes):
    with wish_list_table.batch_writer() as batch:
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

    # 対象のほしいものリストへアクセス
    browser.get(wish_list_url)
    time.sleep(1)

    asin_codes = []
    price_lower_items = []

    list_items = browser.find_elements_by_css_selector('.a-spacing-none.g-item-sortable')
    for list_item in list_items:
        # TODO:Amazon側では価格情報を小数第一を含めて表示しているが、小数第一を切り捨て対応（小数第一が0以外の商品が存在する可能性もあり得る？）
        price = math.floor(float(list_item.get_attribute('data-price')))
        data_reposition_action_params = list_item.get_attribute('data-reposition-action-params')
        data_reposition_action_params_dict = json.loads(data_reposition_action_params)
        asin_code = (re.search(r'ASIN:(.*)\|', data_reposition_action_params_dict['itemExternalId'])).group(1)

        item_id = list_item.get_attribute('data-itemId')
        item_name = browser.find_element_by_id('itemName_' + item_id).get_attribute('title')

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
    # dynamoDBには存在するがほしいものリスト内には存在しないasinコードを検索→ほしいものリストから削除された商品
    deleted_saved_cart_asin_codes = set(data_asin_codes) ^ set(asin_codes)

    if len(deleted_saved_cart_asin_codes) != 0:
        delete_recodes(deleted_saved_cart_asin_codes)

    browser.quit()
