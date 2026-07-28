# WebSocketリアルタイムチャット（Live Server版）

VS Codeの拡張機能「Live Server」と、Node.jsのWebSocketサーバを使ったリアルタイムチャットです。

- Live Server：`index.html`、`style.css`、`client.js`をブラウザに表示（5500番ポート）
- `server.js`：メッセージを各ブラウザへ中継（8888番ポート）

チャットを動かすには、Live Serverと`server.js`の両方を起動する必要があります。

## 主な機能

- 複数のブラウザ間でメッセージをリアルタイムに送受信
- 自分のメッセージを右側、相手のメッセージを左側に表示
- 表示名と送信時刻の表示
- 絵文字の入力と送信
- 同じWi-Fiに接続している相手へ参加URLを共有
- WebSocket切断時の自動再接続

## ファイル構成

```text
websocket-chat-live-server/
├── .vscode/
│   └── settings.json
├── index.html
├── client.js
├── style.css
├── server.js
├── package.json
├── package-lock.json
└── README.md
```

## 初回だけ行う準備

### 1. ZIPファイルを展開する

ダウンロードしたZIPファイルを右クリックし、「すべて展開」を選択します。

### 2. Visual Studio Codeをインストールする

VS Codeをインストールしていない場合は、次の公式サイトからインストールします。

<https://code.visualstudio.com/>

### 3. Node.jsをインストールする

次の公式サイトから、Node.jsのLTS版をインストールします。

<https://nodejs.org/>

インストール後は、VS Codeを一度終了して開き直してください。

VS Codeで「ターミナル」→「新しいターミナル」を選び、次の2つを順番に実行します。

```bash
node -v
npm -v
```

どちらもバージョン番号が表示されれば、Node.jsとnpmの準備は完了です。

### 4. Live Serverをインストールする

1. VS Codeを開く
2. 画面左側の「拡張機能」アイコンを押す
3. 検索欄に`Live Server`と入力する
4. 提供元が「Ritwick Dey」のLive Serverを選択する
5. 「インストール」を押す

Live Server：

<https://marketplace.visualstudio.com/items?itemName=ritwickdey.LiveServer>

### 5. プロジェクトのフォルダを開く

VS Codeの「ファイル」→「フォルダーを開く」から、ZIPを展開した`websocket-chat-live-server`フォルダを選択します。

`index.html`だけを開くのではなく、プロジェクトのフォルダ全体を開いてください。

### 6. 必要なライブラリをインストールする

VS Codeで「ターミナル」→「新しいターミナル」を選び、次を実行します。

```bash
npm install
```

完了すると`node_modules`フォルダが作成されます。`node_modules`は実行に必要ですが、授業へ提出する必要はありません。

## プログラムの実行方法

### 1. WebSocketサーバを起動する

VS Codeのターミナルで次を実行します。

```bash
npm start
```

次のように表示されれば、WebSocketサーバの起動に成功しています。

```text
WebSocket server: ws://localhost:8888
```

このターミナルは、チャットを利用している間は閉じないでください。ターミナルを閉じると、メッセージを中継するサーバも停止します。

### 2. Live Serverを起動する

1. VS Code左側のファイル一覧から`index.html`を探す
2. `index.html`を右クリックする
3. 「Open with Live Server」を選択する
4. ブラウザが自動的に開くまで待つ

ブラウザのURLは、次のようになります。

```text
http://192.168.1.10:5500/index.html
```

自分のPCだけで開く場合は、次のようになることもあります。

```text
http://localhost:5500/index.html
```

画面上部の通信状態が「接続中」になれば、Live ServerとWebSocketサーバの両方が正常に動いています。

### 3. チャットを試す

1台のPCで確認する場合は、ChromeとEdge、または通常ウィンドウとシークレットウィンドウなど、2つのブラウザ画面で同じURLを開きます。

1. それぞれの画面で異なる表示名を入力する
2. メッセージまたは絵文字を入力する
3. 「送信」を押す
4. 両方の画面にメッセージが表示されることを確認する

自分が送信したメッセージは右側、相手が送信したメッセージは左側に表示されます。

## 同じWi-Fiにいる相手とチャットする方法

1. サーバ役のPCで`npm start`とLive Serverを起動する
2. 相手の端末を、サーバ役のPCと同じWi-Fiへ接続する
3. チャット画面左下の「URLをコピー」を押す
4. コピーしたURLを相手へ送る
5. 相手がブラウザでURLを開く

相手へ共有するURLには、サーバ役のPCのローカルIPアドレスが必要です。

共有できるURLの例：

```text
http://192.168.1.10:5500/index.html
```

次のURLは自分のPC専用なので、相手へ共有しても開けません。

```text
http://localhost:5500/index.html
http://127.0.0.1:5500/index.html
```

Windows Defenderファイアウォールの確認画面が表示された場合は、「プライベートネットワーク」にチェックを入れ、Node.jsとVS Codeの通信を許可してください。

## 2回目以降の起動方法

初回準備が終わっていれば、毎回必要な操作は次の2つです。

1. VS Codeのターミナルで`npm start`を実行する
2. `index.html`を右クリックし、「Open with Live Server」を選択する

`npm install`とLive Serverのインストールは、通常は初回だけで構いません。

## 終了方法

1. `npm start`を実行しているターミナルを選び、`Ctrl + C`を押す
2. VS Code右下の「Port: 5500」、または「Go Live」を押してLive Serverを停止する
3. ブラウザを閉じる

## うまく動かない場合

### 「サーバに接続中」のままになる

- `npm start`を実行したターミナルが開いたままか確認する
- ターミナルに`WebSocket server: ws://localhost:8888`と表示されているか確認する
- 8888番ポートを別のプログラムが使用していないか確認する

### 「Open with Live Server」が表示されない

- VS Codeの拡張機能でLive Serverがインストール済みか確認する
- `index.html`を右クリックしているか確認する
- VS Codeを一度終了し、開き直す

### 自分は使えるが、相手がURLを開けない

- 相手が同じWi-Fiに接続しているか確認する
- URLが`localhost`や`127.0.0.1`ではなく、`192.168`などから始まっているか確認する
- Windows DefenderファイアウォールでNode.jsとVS Codeを許可する
- 学内Wi-Fiなど、端末間通信を禁止しているネットワークでは利用できない場合がある

### メッセージを送信できない

- 画面上部が「接続中」になっているか確認する
- `npm start`を一度停止し、もう一度実行する
- ブラウザを再読み込みする

## 利用上の注意

- Live Serverで相手と通信できるのは、原則として同じWi-Fi内です。
- 別の家や別のネットワークから、URLだけで参加することはできません。
- インターネットへ公開するには、外部サーバや安全なトンネルサービスが別途必要です。
- Live Serverは開発・授業内の動作確認向けであり、本番公開用のWebサーバではありません。

## 提出するファイル

- `index.html`
- `client.js`
- `style.css`
- `server.js`
- `package.json`
- `package-lock.json`
- `README.md`
- `CODE_GUIDE.md`
- `.vscode/settings.json`
