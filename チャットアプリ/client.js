// 授業資料の new WebSocket、send、onmessage、onclose を基に発展させた。
var ws;
var reconnectTimer;

var statusText = document.getElementById("status");
var nameInput = document.getElementById("name");
var messageInput = document.getElementById("message");
var chatForm = document.getElementById("chat-form");
var messages = document.getElementById("messages");
var emptyMessage = document.getElementById("empty-message");
var emojiButton = document.getElementById("emoji-button");
var emojiPanel = document.getElementById("emoji-panel");
var copyUrlButton = document.getElementById("copy-url-button");
var copyResult = document.getElementById("copy-result");

var clientId = sessionStorage.getItem("chatClientId");
if (!clientId) {
  clientId = "client-" + Date.now() + "-" + Math.random().toString(16).slice(2);
  sessionStorage.setItem("chatClientId", clientId);
}

nameInput.value = localStorage.getItem("chatName") || "";

function setStatus(text, state) {
  statusText.textContent = text;
  statusText.className = "status status--" + state;
}

function getWebSocketUrl() {
  // Live Serverを開いたPCのホスト名/IPアドレスへ接続する。
  // 例: http://192.168.1.10:5500 → ws://192.168.1.10:8888
  var protocol = location.protocol === "https:" ? "wss:" : "ws:";
  var host = location.hostname || "localhost";
  return protocol + "//" + host + ":8888/";
}

function start() {
  clearTimeout(reconnectTimer);
  setStatus("サーバに接続中...", "connecting");

  try {
    ws = new WebSocket(getWebSocketUrl());
  } catch (error) {
    scheduleReconnect();
    return;
  }

  ws.onopen = function () {
    setStatus("接続中", "connected");
    messageInput.focus();
  };

  // 授業資料の ws.onmessage を、JSON形式のチャット表示へ発展させた。
  ws.onmessage = function (event) {
    var data;

    try {
      data = JSON.parse(event.data);
    } catch (error) {
      return;
    }

    if (data.type === "chat") {
      addMessage(data);
    }
  };

  ws.onerror = function () {
    setStatus("通信エラー", "disconnected");
  };

  // 授業資料の ws.onclose を再接続処理へ発展させた。
  ws.onclose = function () {
    setStatus("切断中・再接続します", "disconnected");
    scheduleReconnect();
  };
}

function scheduleReconnect() {
  clearTimeout(reconnectTimer);
  reconnectTimer = setTimeout(start, 3000);
}

function sendMsg() {
  var text = messageInput.value.trim();
  var name = nameInput.value.trim() || "匿名";

  if (!text) {
    return;
  }

  if (!ws || ws.readyState !== WebSocket.OPEN) {
    setStatus("サーバ未接続：server.jsを確認してください", "disconnected");
    return;
  }

  localStorage.setItem("chatName", name);

  // 授業資料の ws.send(msg) を、名前・本文・送信者IDを含むJSON送信へ発展させた。
  ws.send(JSON.stringify({
    type: "chat",
    clientId: clientId,
    name: name,
    text: text
  }));

  messageInput.value = "";
  messageInput.focus();
}

function addMessage(data) {
  if (emptyMessage) {
    emptyMessage.remove();
    emptyMessage = null;
  }

  var isMine = data.clientId === clientId;
  var wrapper = document.createElement("article");
  var sender = document.createElement("p");
  var bubble = document.createElement("div");
  var text = document.createElement("p");
  var time = document.createElement("time");

  // 一般的なチャット表示に合わせ、自分を右、相手を左へ表示する。
  wrapper.className = "message " + (isMine ? "message--mine" : "message--other");
  sender.className = "message__sender";
  bubble.className = "message__bubble";
  text.className = "message__text";
  time.className = "message__time";

  sender.textContent = isMine ? "自分" : data.name;
  text.textContent = data.text;
  time.textContent = data.time;

  bubble.appendChild(text);
  bubble.appendChild(time);
  wrapper.appendChild(sender);
  wrapper.appendChild(bubble);
  messages.appendChild(wrapper);
  messages.scrollTop = messages.scrollHeight;
}

chatForm.addEventListener("submit", function (event) {
  event.preventDefault();
  sendMsg();
});

nameInput.addEventListener("change", function () {
  localStorage.setItem("chatName", nameInput.value.trim());
});

emojiButton.addEventListener("click", function () {
  var willOpen = emojiPanel.hidden;
  emojiPanel.hidden = !willOpen;
  emojiButton.setAttribute("aria-expanded", String(willOpen));
});

document.querySelectorAll(".emoji-choice").forEach(function (button) {
  button.addEventListener("click", function () {
    messageInput.value += button.textContent;
    emojiPanel.hidden = true;
    emojiButton.setAttribute("aria-expanded", "false");
    messageInput.focus();
  });
});

async function getShareUrl() {
  var shareUrl = new URL(location.href);

  // localhostで開いている場合も、相手が開けるローカルIPのURLへ変換する。
  if (["localhost", "127.0.0.1", "0.0.0.0"].includes(location.hostname)) {
    try {
      var response = await fetch("http://" + location.hostname + ":8888/network-info");
      var network = await response.json();

      if (network.ip) {
        shareUrl.hostname = network.ip;
      }
    } catch (error) {
      // 取得できない場合は、現在のURLをコピーして手動変更できるようにする。
    }
  }

  return shareUrl.href;
}

copyUrlButton.addEventListener("click", async function () {
  var shareUrl = await getShareUrl();

  try {
    await navigator.clipboard.writeText(shareUrl);
    copyResult.textContent = "コピーしました";
  } catch (error) {
    window.prompt("このURLをコピーしてください", shareUrl);
  }

  setTimeout(function () {
    copyResult.textContent = "";
  }, 2500);
});

window.addEventListener("load", start);
