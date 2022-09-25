from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
import time
import math

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
    email_elem.send_keys('Amazonで登録しているメールアドレス')

    next_button = browser.find_element_by_class_name('a-button-input')
    next_button.click()
    time.sleep(1)

    #Todo:パスワードがべた書きなのはセキュリティ上良くない
    password_elem = browser.find_element_by_id('ap_password')
    password_elem.send_keys('Amazonで登録しているパスワード')

    next_button = browser.find_element_by_id('signInSubmit')
    next_button.click()
    time.sleep(1)

    #Todo:Amazon側ではログイン時にセキュリティメールを送信することがある。登録したメール側から承認する作業を行う必要がある
    #※新しく別ドライブを立ち上げてGmailに自動ログインするのはGoogleの仕様上、現在不可能

    cart_button = browser.find_element_by_id('nav-cart')
    cart_button.click()
    time.sleep(1)

    #全ての「後で買うリスト」の商品情報を取得するため画面下までスクロール
    html = browser.find_element_by_tag_name('html')
    html.send_keys(Keys.END)
    time.sleep(1)

    saved_cart_items = browser.find_elements_by_css_selector('.a-row.sc-list-item.sc-java-remote-feature')

    for saved_cart_item in saved_cart_items:
        saved_cart_item_asin = saved_cart_item.get_attribute('data-asin')
        #Todo:Amazon側では価格情報を小数第一を含めて表示しているが一旦、切り捨てして整数で値を取得している（少数第一が0以外のデータが存在するかもしれない
        saved_cart_item_price = math.floor(float(saved_cart_item.get_attribute('data-price')))

        #在庫切れ商品や出品者が取り下げた商品については価格情報が0円で取得されているためそういった商品は取り扱わない
        if saved_cart_item_price != 0:
            #dynamoDBの処理記述
            print('test')
