# PriceLowerNotification

## Overview
Amazonのマイページにて「後で買う」に入っている商品が前回よりも20%値下げした場合に
Slackにて値下がり対照商品を通知するシステム。
個人的に値段で迷っている場合に「後で買う」リストに追加することが多いため最後の購買の一押しとして通知。

## Requirement
-AWS Lambda
-python3.7
-AWS DynamoDB
-AWS Cloud Watch
-headless-chromium
-chromedriver
-selenium2.53.6
