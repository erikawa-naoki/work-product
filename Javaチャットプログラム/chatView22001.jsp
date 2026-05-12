<%@ page contentType="text/html; charset=UTF-8" %>
<%@ page import="java.util.ArrayList" %>
<%@ page import="usedb.DbSelectBean" %>
<html>
<head>
    <meta http-equiv="Content-Type" content="text/html; charset=Shift_JIS">
    <title>Chat View</title>
    <style>
    	.center{
    		text-align:center;
    	}
    	table td {
	    	background: #eee;
		}
		table tr:nth-child(odd) td {
			background: #fff;
		}
    </style>
</head>
<body>
    <h1><center>最新チャットメッセージ20件</center></h1>
     <a href="http://localhost:8080/WebApplicationTest/chat22001.html">チャット入力へ</a>
    <table align = "center" border="1" bordercolor="black">
        <tr bgcolor="#e3f0fb">  
            <th>発信者        </th>
            <th>友達メッセージ</th>
            <th>更新日/時刻   </th>
            <th>私のメッセージ</th>
    	</tr>;
        <% ArrayList<String[]> list = (ArrayList<String[]>) request.getAttribute("list"); %>
	   		<% for (String[]  hyou: list) { %>
               <% if (hyou[0] != null) {%>
                <tr>
                    <td><%= hyou[0] %></td>
                    <td><%= hyou[1] %></td>
                    <td class="center"><%= hyou[2] %></td>
                    <td><%= hyou[3] %></td>
                </tr>
               <% }else {%>
                <tr bgcolor="yellow">
                    <td><%= hyou[0] %></td>
                    <td><%= hyou[1] %></td>
                    <td class="center"><%= hyou[2] %></td>
                    <td><%= hyou[3] %></td>
                </tr>
               <% }%>
           <% } %>
	</table>
</body>
</html>
