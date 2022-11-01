# PriceLowerNotification

## Overview
Amazonの公開している「ほしいもの」リストの商品が前回よりも20%値下げした場合に
Slackにて値下がり対象商品を通知するシステム。
当初はAmazonの「後で買う」リストからデータを取得・比較する予定であったが、Amazonアカウントへログインする必要があり、
ログインの際のセキュリティ対策にて自動化が厳しかったため「ほしもの」リストへ変更。
また、「ほしいもの」リストは公開可能で且つ任意の名称をつけることが可能なため「後で買う」リストからデータを取得するシステムよりも、
より汎用的なシステムとして使用可能と思われる。

## Requirement
- AWS Lambda
- python3.7
- AWS DynamoDB
- AWS Cloud Watch
- headless-chromium
- chromedriver
- selenium==3.141.0
- urllib3==1.26.12
