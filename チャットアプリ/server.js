// You have to do "npm install websocket"
// node server.js
//
// 授業資料 server.js の http / websocket / request / message /
// connection.send() を基に、複数人チャットへ発展させた。

var http = require("http");
var os = require("os");
var WSServer = require("websocket").server;

var connections = [];

// HTMLはここから配信せず、VS CodeのLive Serverから配信する。
// このHTTPサーバはWebSocketの接続開始（Upgrade）のために使用する。
var server = http.createServer(function (req, res) {
  if (req.url === "/network-info") {
    res.writeHead(200, {
      "Content-Type": "application/json; charset=utf-8",
      "Access-Control-Allow-Origin": "*"
    });
    res.end(JSON.stringify({ ip: getLocalIpAddress() }));
    return;
  }

  res.writeHead(200, { "Content-Type": "text/plain; charset=utf-8" });
  res.end("WebSocket server is running.");
});

function getLocalIpAddress() {
  var interfaces = os.networkInterfaces();
  var candidates = [];

  Object.keys(interfaces).forEach(function (name) {
    interfaces[name].forEach(function (address) {
      if (address.family === "IPv4" && !address.internal) {
        candidates.push(address.address);
      }
    });
  });

  var privateAddress = candidates.find(function (address) {
    return (
      address.startsWith("192.168.") ||
      address.startsWith("10.") ||
      /^172\.(1[6-9]|2[0-9]|3[01])\./.test(address)
    );
  });

  return privateAddress || candidates[0] || "localhost";
}

server.listen(8888, "0.0.0.0", function () {
  console.log("WebSocket server: ws://localhost:8888");
});

var webSocketServer = new WSServer({
  httpServer: server,
  autoAcceptConnections: false
});

webSocketServer.on("request", function (req) {
  // Live Server（別ポート）からの接続を受け付ける。
  var connection = req.accept(null, req.origin);
  connections.push(connection);
  console.log("connected: " + connections.length + " client(s)");

  connection.on("message", function (msg) {
    if (msg.type !== "utf8") {
      return;
    }

    var received;

    try {
      received = JSON.parse(msg.utf8Data);
    } catch (error) {
      return;
    }

    if (received.type !== "chat") {
      return;
    }

    var name = String(received.name || "匿名").trim().slice(0, 20);
    var text = String(received.text || "").trim().slice(0, 300);
    var clientId = String(received.clientId || "").slice(0, 100);

    if (!text || !clientId) {
      return;
    }

    var data = JSON.stringify({
      type: "chat",
      clientId: clientId,
      name: name || "匿名",
      text: text,
      time: new Date().toLocaleTimeString("ja-JP", {
        hour: "2-digit",
        minute: "2-digit"
      })
    });

    console.log('"' + text + '" is received');

    // 授業資料の connection.send() を、接続中の全員への送信へ発展させた。
    connections.forEach(function (client) {
      if (client.connected) {
        client.send(data);
      }
    });
  });

  connection.on("close", function () {
    connections = connections.filter(function (client) {
      return client !== connection;
    });
    console.log("disconnected: " + connections.length + " client(s)");
  });
});
