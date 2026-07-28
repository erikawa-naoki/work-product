# ソースコード詳細説明

## 1. アプリケーションの役割

このアプリは、同じWi-Fi内にいる複数の利用者が、ブラウザからリアルタイムにメッセージを送受信するチャットアプリです。

画面の表示はVS CodeのLive Server、メッセージの中継はNode.jsの`server.js`が担当します。Live Serverだけではチャットは成立しないため、両方を同時に起動します。

## 2. システム構成

```text
利用者Aのブラウザ ─┐
                    ├─ WebSocket ─ Node.js server.js（8888番）
利用者Bのブラウザ ─┘

HTML・CSS・client.js ─ Live Server（5500番）
```

- Live Server：`index.html`、`style.css`、`client.js`を配信
- WebSocketサーバ：接続の受付、受信、時刻付与、全員への一斉配信
- ブラウザ：入力、JSON送信、JSON受信、メッセージ表示

## 3. 通信の流れ

1. `client.js`が`new WebSocket("ws://サーバPC:8888/")`を実行する
2. HTTP接続がWebSocketへUpgradeされ、継続的な双方向接続が確立する
3. 利用者が送信ボタンを押す
4. `ws.send()`が表示名・本文・送信者IDをJSON文字列で送る
5. `server.js`の`message`イベントがJSONを受信する
6. サーバが入力を検査し、送信時刻を付与する
7. `connection.send()`により、接続中の全ブラウザへ一斉配信する
8. 各ブラウザの`onmessage`が受信し、画面へ吹き出しを追加する

## 4. ファイルごとの説明

### `package.json`：起動コマンドと使用ライブラリ

Node.jsでこのアプリを実行するための基本設定を記述したファイルです。

- `"start": "node server.js"`：`npm start`を実行したときに、WebSocketサーバの`server.js`を起動する
- `"websocket": "^1.0.35"`：WebSocketサーバの作成に使用する`websocket`ライブラリを指定する
- `"private": true`：このアプリを誤ってnpmへ公開しないようにする

このファイルがあることで、利用者は起動コマンドや必要なライブラリを確認でき、`npm install`と`npm start`で実行準備とサーバ起動を行えます。そのため、ソースコード一式に含めて提出します。

### `package-lock.json`：ライブラリの正確なバージョン情報

`npm install`によって自動生成され、実際にインストールするライブラリと、その関連ライブラリの正確なバージョンを記録するファイルです。

`package.json`の`"websocket": "^1.0.35"`は利用可能なバージョンの範囲を示しますが、`package-lock.json`には実際に使用するバージョンや依存関係が固定されています。これにより、別のPCでも開発時と同じ構成を再現しやすくなります。

このファイルは手作業で編集せず、`package.json`と一緒にソースコード一式へ含めて提出します。なお、容量の大きい`node_modules`フォルダは提出せず、提出先では`npm install`を実行して復元します。

### `.vscode/settings.json`：Live Serverのポート・LAN公開設定

VS CodeのLive Serverを、このプロジェクトでどのように起動するかを指定する設定ファイルです。

```json
{
  "liveServer.settings.host": "0.0.0.0",
  "liveServer.settings.port": 5500,
  "liveServer.settings.useLocalIp": true,
  "liveServer.settings.NoBrowser": false
}
```

- `"liveServer.settings.host": "0.0.0.0"`：自分のPCだけでなく、LAN内からの接続も受け付ける
- `"liveServer.settings.port": 5500`：Live Serverを5500番ポートで起動する
- `"liveServer.settings.useLocalIp": true`：`192.168.x.x`などのLAN内IPアドレスでページを開けるようにする
- `"liveServer.settings.NoBrowser": false`：Live Server起動時にブラウザを自動で開く

この設定により、同じWi-Fiに接続した別端末から`http://サーバPCのLAN内IP:5500`へアクセスできます。LAN内でチャット画面を共有するために必要な設定なので、`.vscode`フォルダごとソースコード一式へ含めて提出します。

### `index.html`

チャット画面の構造を定義します。

- `#status`：サーバ接続状態
- `#name`：表示名
- `#messages`：受信メッセージの表示領域
- `#chat-form`：メッセージ入力と送信
- `#emoji-panel`：絵文字選択
- `#copy-url-button`：共有URLのコピー

### `style.css`

チャット画面の見た目を定義します。CSSのクラスを切り替えることで、自分と相手の表示を分けます。

- `.message--mine`：自分のメッセージを右側・緑色で表示
- `.message--other`：相手のメッセージを左側・白色で表示
- `@media`：画面幅520px以下のスマートフォン表示を調整

### `client.js`

ブラウザで動く通信処理です。

#### `getWebSocketUrl()`

Live Serverを開いているホスト名を使い、8888番ポートのWebSocket URLを作ります。

```javascript
var host = location.hostname || "localhost";
return "ws://" + host + ":8888/";
```

このため、相手が`http://192.168.x.x:5500`を開いた場合、同じサーバPCの`ws://192.168.x.x:8888`へ接続できます。

#### `start()`

`new WebSocket()`でサーバへ接続し、4種類のイベントを登録します。

- `onopen`：接続成功
- `onmessage`：メッセージ受信
- `onerror`：通信エラー
- `onclose`：切断と再接続

#### `sendMsg()`

入力内容をJSONに変換し、`ws.send()`で送信します。

```json
{
  "type": "chat",
  "clientId": "タブごとの識別子",
  "name": "表示名",
  "text": "メッセージ本文"
}
```

#### `addMessage()`

受信した`clientId`が自分のIDと一致すれば右側、一致しなければ左側へ表示します。

本文の表示には`innerHTML`ではなく`textContent`を使い、入力されたHTMLやJavaScriptが実行されないようにしています。

#### Web Storage

- `sessionStorage`：タブごとの`clientId`を保持
- `localStorage`：表示名をブラウザに保存

### `server.js`

Node.jsで動くWebSocketサーバです。

#### HTTPサーバ

WebSocket接続開始時のHTTP Upgradeを受け付けます。また、`/network-info`でLAN内IPアドレスを返し、共有URLの生成を補助します。

#### `request`イベント

新しいWebSocket接続を受け付け、`connections`配列へ保存します。

#### `message`イベント

クライアントから届いたJSONを解析し、次を検査します。

- データがUTF-8文字列か
- JSONとして解析できるか
- `type`が`chat`か
- 本文と送信者IDが空でないか
- 表示名、本文、IDが最大長以内か

#### 一斉配信

接続中の全クライアントに対して`connection.send()`を実行します。

```javascript
connections.forEach(function (client) {
  if (client.connected) {
    client.send(data);
  }
});
```

#### `close`イベント

切断したクライアントを`connections`配列から削除します。

## 5. 使用した技術

### WebSocket

一度接続すると、クライアントとサーバのどちらからでもデータを送れる双方向通信です。チャットでは新しいメッセージを即時配信できるため、繰り返しHTTPで問い合わせる方式より適しています。

### Node.js

ブラウザと同じJavaScriptでサーバ側処理を実行します。イベント駆動で複数接続を扱い、受信時に全クライアントへ配信します。

### `websocket`ライブラリ

授業資料と同じライブラリを利用し、HTTPサーバ上でWebSocket接続の`request`、`message`、`close`イベントを扱います。

### JSON

表示名、本文、送信者ID、時刻を、項目名付きの1つの文字列として送受信します。

### Live Server

HTML・CSS・クライアントJavaScriptをブラウザへ配信します。通信サーバとは役割を分け、5500番ポートを使用します。

### Web Storage API

`sessionStorage`でタブごとの識別子、`localStorage`で表示名を保存します。

### DOM API

受信メッセージごとに要素を作り、`textContent`で安全に画面へ追加します。

## 6. 授業資料から発展させた点

| 授業資料の処理 | 本アプリでの発展 |
| --- | --- |
| 固定URLへの`new WebSocket()` | Live Serverのホスト名から接続先を自動生成 |
| 文字列を`ws.send()` | 表示名・本文・IDをJSONで送信 |
| 受信文字列の表示 | 自分と相手を判定して左右の吹き出しで表示 |
| 一つの接続へ`connection.send()` | 接続中の全員へ一斉配信 |
| `onclose`で終了表示 | 3秒後の自動再接続 |
| 単純なフォーム | 絵文字、表示名保存、URLコピーを追加 |

## 7. ポート番号

| ポート | 担当 | 用途 |
| --- | --- | --- |
| 5500 | Live Server | HTML・CSS・client.jsの配信 |
| 8888 | Node.js | WebSocket通信、LAN内IPの取得 |

## 8. 動作範囲と制約

- 原則として同じWi-Fi内で利用する
- 学内Wi-Fiなど、端末間通信を禁止するネットワークでは使えない場合がある
- 別ネットワークから利用するには、外部サーバや安全なトンネルが必要
- Live Serverは授業内の実行・開発確認向けであり、本番公開用ではない
