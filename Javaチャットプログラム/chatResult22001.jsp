<%@ page contentType="text/html; charset=UTF-8" %>
<html>
<head>
<meta http-equiv="Content-Type" content="text/html; charset=Shift_JIS">
<title>chatResult</title>
</head>
<body>
<%
  String message = request.getParameter("MESSAGE");
%>
<h1>メッセージ<%= message %>を登録しました。</h1>
</body>
</html>
