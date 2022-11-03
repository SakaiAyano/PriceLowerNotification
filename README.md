# PriceLowerNotification

## システム概要
Amazon提供の「ほしいもの」リスト（公開）に登録している商品が前回よりも20%値下げした場合に  
Slackにて値下がり対象商品を通知するシステム。  
当初はAmazonの「後で買う」リストからデータを取得・比較する予定であったが、Amazonアカウントへログインする必要があり  ログイン時におけるセキュリティに対する自動化が厳しかったためログインする必要のない「ほしいもの」リスト（公開）に対象を変更。


## 使用ライブラリ
- AWS Lambda
- python3.7
- AWS DynamoDB
- AWS Cloud Watch
- headless-chromium
- chromedriver
- selenium==3.141.0
- urllib3==1.26.12
