# PriceLowerNotification

## Overview
Amazonのマイページにて「後で買う」に入っている商品が前回よりも20%値下げした場合に
Slackにて値下がり対照商品を通知するシステム。
個人的に値段で迷っている場合に「後で買う」リストに追加することが多いため。

## Requirement
- AWS Lambda
- python3.7
- AWS DynamoDB
- AWS Cloud Watch
- headless-chromium
- chromedriver
- selenium==3.141.0
- urllib3==1.26.12
