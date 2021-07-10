# UmaTournamentBot
Discord bot for hosting tournaments in Uma Musume

## Introduction

このBotはdiscord上での大規模トーナメントをサポートします。
抽選・グループ分け・集計・チャンネル作成を自動で行うので、トーナメント開催が非常にスムーズになります。

Botの操作主に求められる行動は、いくつかのコマンドの入力、参加者への説明と催促、不適切人物の排除程度です。

[![Deploy](https://www.herokucdn.com/deploy/button.svg)](https://heroku.com/deploy)

## Usage

## Botをサーバーに追加する

Bot招待url: https://discord.com/api/oauth2/authorize?client_id=857220750549450782&permissions=268528848&scope=bot

上記リンクをクリックし、サーバーを選択して認証することでbotを追加できます。
この操作にはサーバーの管理者権限が必要です。

<img src="https://i.imgur.com/X5u8Fwt.png" style="width: 60vw" alt="Botの追加">


## トーナメントの開催

### 開催・参加者の募集: `?open <num=3> <maxNum=81>`

**まずは`?open`でトーナメントを開催します。**
自動でトーナメント用のチャンネルとカテゴリが作成されます。


| 引数     |  内容            | 既定値 |
| -------- | ----------------- | ------ |
| `num`    | 1試合当たりの人数 | 3      |
| `maxNum` | 最大参加人数      | 81     |

<img src="https://i.imgur.com/u4SYoT8.png" alt="トーナメントの開催: open">


参加募集メッセージが流れるので、参加希望者はそこにリアクションを追加します。
(リアクションの種類は何でも構いません。また、一人が複数押しても影響はありません。)

参加希望者は随時announceチャンネルに表示されます。
希望者が十分集まったら、主催者(`?open`と入力した人)が`!next`と入力して、次に進みます。
以降も、このトーナメントに関してのコマンドは、主催者のものしか受け付けません。

<img src="https://i.imgur.com/gGz7IDj.png" alt="参加希望者の募集締め切り">


### 1回戦 グループ分け・チャンネル役職作成・勝利報告

`!next`の入力で1回戦が始まります。
最大参加人数やトーナメント調整のため、1回戦では必要に応じて抽選が行われます。

<img src="https://i.imgur.com/1GUYx3r.png" alt="1回戦開始">

1回戦のグループ分けはannounceチャンネルで確認できます。
<img src="https://i.imgur.com/p9Q65pO.png" alt="1回戦グループ分け発表">

同時にグループ用のテキストチャンネルが作成され、グループの参加者ごとにメンションが飛ばされています。
これでグループ数が多くなっても、自分のグループを見逃す心配はありませんね！
<img src="https://i.imgur.com/EWBnn1Z.png" alt="グループごとのメンション">


1回戦の勝者は該当のメッセージにスタンプを押します。
報告された勝者はグループ分けのメッセージで確認できます。(名前の左に〇が付きます。)

未報告、あるいは複数人が勝利報告しているグループは下部に明示されます。グループ番号の横にも報告状況に応じて、`未/複/済`が表示されます。
なお、1回戦に参加していない人がスタンプを押しても影響はありません。
<img src="https://i.imgur.com/HZ1tppw.png" alt="1回戦勝利報告状況">

勝者が適切に出そろったら、`!next`で2回戦に進みます。
<img src="https://i.imgur.com/F8RxPHW.png" alt="2回戦開始">

<!--
announceチャンネルに新しいグループ分けが発表されます。
<img src="https://i.imgur.com/2nJUCou.png" alt="2回戦グループ分け">
-->

#### 勝利報告: 不適切な人がいた場合

いつまでも勝利報告をしないグループがあった場合、`!nextForce`により、未報告グループを無視して、次に進むことができます。
あるいは、`!win <@name>/<name>#<4桁の数字>`で勝者に追加できます。(リアクションの追加にすら手間取る人は無視して進んだ方がいいかもしれませんが。)
<img src="https://i.imgur.com/KfPwxf3.png" alt="!win">

逆に複数人が勝利報告をし続けるグループがあった場合、`!kick <@name>/<name>#<4桁の数字>`で不適切なトレーナーをトーナメントから除名できます。

<img src="https://i.imgur.com/X3fMSMO.png" alt="!kick">


<!--
<img src="https://i.imgur.com/Lu8MKCD.png" alt="適切な勝利報告">
-->


### トーナメントの終了

2回戦以降も同様に続きます。
最終的に勝者が1名になれば、トーナメントは終了です。

<img src="https://i.imgur.com/iiTP9EZ.png" alt="トーナメント終了">


途中でbot支援の必要がなくなれば、`!cancel`でトーナメントを中止できます。

<img src="https://i.imgur.com/Pmj2VFr.png" alt="!cancel">


## その他のコマンド

### 邪魔なチャンネル・役職の削除

- `?deleteRes`: 終了したトーナメントに関してのみ削除 (推奨・便利)
- `?delete <tour_id>`: 指定したトーナメントに関してのみ削除 (推奨)
- `?deleteAll`: すべてのトーナメントに関して削除 (非推奨)

### bot操作権限の切り替え: `?onlyAdmin`

botの操作をサーバーの管理者権限に限定するかどうかを切り替えます。
既定では管理者権限所有者に限定されています。

### 役職利用の切り替え: `?roleIsValid`

大人数では一部操作が重くなりすぎる可能性があります。
既定では役職は利用しません。

## 注意点

botがherokuで運用されている場合、


