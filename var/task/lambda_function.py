from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from boto3.dynamodb.conditions import Key
import time
import math
import boto3
import urllib3
import json
import os
from decimal import Decimal

http = urllib3.PoolManager()

dynamo_db = boto3.resource('dynamodb')
saved_cart_item_table = dynamo_db.Table('saved_cart_item')

#テーブルスキャン
def table_scan():
    scan_data = saved_cart_item_table.scan()
    if 'Items' in scan_data:
        data_items = scan_data['Items']
        return data_items
    return

#項目検索
def get_data_price(partitionKey):
    query_data = saved_cart_item_table.get_item(Key={'asin_code':partitionKey})
    if 'Item' in query_data:
        item = query_data['Item']
        return item['price']
    return

#項目追加
def add_record(partitionKey, price):
    add_response = saved_cart_item_table.put_item(
        Item={
            'asin_code': partitionKey,
            'price': price
        }
    )

    if add_response['ResponseMetadata']['HTTPStatusCode'] != 200:
        #エラーレスポンスの表示
        print(add_response)
    else:
        print('PUT Successed.')

#項目削除
#Todo:通信回数が多い、バッチを使用して減らす
def delete_recode(partitionKey):
    delete_response = saved_cart_item_table.delete_item(
       Key={
           'asin_code': partitionKey
       }
    )
    if delete_response['ResponseMetadata']['HTTPStatusCode'] != 200:
        #エラーレスポンスの表示
        print(delete_response)
    else:
        print('DEL Successed.')


#Slackへの通知処理
def price_lower_notification(lower_cart_item_names):
    slack_url = os.environ['SLACK_URL']
    items_list = ''
    for lower_cart_item_name in lower_cart_item_names:
        items_list += '★'+lower_cart_item_name+'\n'

    msg = {
        'attachments':[
        {
         'fallback':'Amazonからのお知らせ',
         'pretext':'<@JhonLenon>',
         'link_names': 1,
         'color':'#D00000',
         'fields':[
            {
               'title':'以下は20%OFFの商品になります！お買い忘れはございませんか？',
               'value':items_list
            }
         ]
        }
      ]
    }

    encoded_msg = json.dumps(msg).encode('utf-8')
    resp = http.request('POST', slack_url, body=encoded_msg)
    print({
        'message': 'Hello From Lambda',
        'status_code': resp.status,
        'response': resp.data
    })



def lambda_handler(event, context):
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--single-process')
    options.binary_location = '/opt/headless/python/bin/headless-chromium'
    browser = webdriver.Chrome('/opt/headless/python/bin/chromedriver',options=options)
    browser.implicitly_wait(10)

    # #Todo:URL長すぎる、短くしたい
    browser.get('https://www.amazon.co.jp/ap/signin?openid.pape.max_auth_age=0&openid.return_to=https%3A%2F%2Fwww.amazon.co.jp%2F%3F_encoding%3DUTF8%26adgrpid%3D56100363354%26gclid%3DCj0KCQjw7KqZBhCBARIsAI-fTKJUkaERllaAt-iDDJUKripHExMBJ4xO9UHIbsSe7s8waee151S7I8caAhy5EALw_wcB%26hvadid%3D592007363477%26hvdev%3Dc%26hvdvcmdl%3D%26hvlocint%3D%26hvlocphy%3D1009293%26hvnetw%3Dg%26hvpone%3D%26hvpos%3D%26hvptwo%3D%26hvqmt%3De%26hvrand%3D14326568463174793788%26hvtargid%3Dkwd-10573980%26hydadcr%3D27922_14541005%26ref%3Dpd_sl_7ibq2d37on_e%26tag%3Dhydraamazonav-22%26ref_%3Dnav_em_hd_re_signin&openid.identity=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0%2Fidentifier_select&openid.assoc_handle=jpflex&openid.mode=checkid_setup&openid.claimed_id=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0%2Fidentifier_select&openid.ns=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0&&ref_%3Dnav_em_hd_clc_signin_0_1_1_36')

    email_elem = browser.find_element_by_id('ap_email')
    email_elem.send_keys(os.environ['AMAZON_ID'])

    next_button = browser.find_element_by_class_name('a-button-input')
    next_button.click()
    time.sleep(1)

    password_elem = browser.find_element_by_id('ap_password')
    password_elem.send_keys(os.environ['AMAZON_PASSWORD'])

    next_button = browser.find_element_by_id('signInSubmit')
    next_button.click()
    time.sleep(20)

    #Todo:Amazon側ではログイン時にセキュリティメールを送信することがある。登録したメール側から承認する作業を行う必要がある
    #※新しく別ドライブを立ち上げてGmailに自動ログインするのはGoogleの仕様上、現在不可能
    #Gmailアプリを使用して自動承認機能を追加したい

    cart_button = browser.find_element_by_id('nav-cart')
    cart_button.click()
    time.sleep(1)

    #全ての「後で買うリスト」の商品情報を取得するため画面下までスクロール
    html = browser.find_element_by_tag_name('html')
    html.send_keys(Keys.END)
    time.sleep(1)

    saved_cart_items = browser.find_elements_by_css_selector('.a-row.sc-list-item.sc-java-remote-feature')
    saved_cart_item_names = browser.find_elements_by_css_selector('.a-truncate.a-size-base-plus .a-truncate-full')

    saved_cart_item_asin_codes = []
    lower_cart_item_names = []
    i = 0


    for saved_cart_item in saved_cart_items:
        saved_cart_item_asin_code = saved_cart_item.get_attribute('data-asin')
        #Todo:Amazon側では価格情報を小数第一を含めて表示しているが一旦、切り捨てして整数で値を取得している（少数第一が0以外のデータが存在するかもしれない
        saved_cart_item_price = math.floor(float(saved_cart_item.get_attribute('data-price')))
        saved_cart_item_name = saved_cart_item_names[i].get_attribute("innerHTML")

        #在庫切れ商品や出品者が取り下げた商品については価格情報が0円で取得されているためそういった商品は取り扱わない
        if saved_cart_item_price != 0:
            data_price = get_data_price(saved_cart_item_asin_code)
            if not data_price:
                add_record(saved_cart_item_asin_code, saved_cart_item_price)
            else:
                data_price_20_off = data_price * Decimal(80/100)
                if(data_price_20_off >= saved_cart_item_price):
                    lower_cart_item_names.append(saved_cart_item_name)

        saved_cart_item_asin_codes.append(saved_cart_item_asin_code)
        i+=1


    if len(lower_cart_item_names) != 0:
        price_lower_notification(lower_cart_item_names)

    data_items = table_scan()
    data_asin_codes = []
    for data_item in data_items:
        data_asin_codes.append(data_item['asin_code'])

    #対象差集合
    #dynamoDBには存在するがcart内には存在しないasinコードを検索→cart画面から削除された商品
    deleted_saved_cart_asin_codes = set(data_asin_codes) ^ set(saved_cart_item_asin_codes)

    if len(deleted_saved_cart_asin_codes) != 0:
        for deleted_saved_cart_asin_code in deleted_saved_cart_asin_codes:
            delete_recode(deleted_saved_cart_asin_code)


    browser.quit()
