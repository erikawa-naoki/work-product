package usedb;

import java.sql.*;
import java.time.*;
import java.time.format.*;
import java.util.*;

public class DbSelectBean {
	
	public ArrayList<String[]> calc() {
		ArrayList<String[]> list = new ArrayList<>();
	  
	    try {
	    	String server = "//172.21.40.30:5432/";
	    	String database = "firstdb";
	    	String url="jdbc:postgresql:" + server + database;
	    	Class.forName("org.postgresql.Driver");
	    	Connection con = DriverManager.getConnection(url,"shibaura", "toyosu");
			Statement stmt = con.createStatement();
			String sql = "SELECT * FROM T_LOG ORDER BY WRITTENDATE DESC LIMIT 20";
			ResultSet rs = stmt.executeQuery(sql);
			
			String name = "江利川直葵";
			LocalDate today = LocalDate.now();
			DateTimeFormatter date = DateTimeFormatter.ofPattern("MM/dd");
			DateTimeFormatter time = DateTimeFormatter.ofPattern("HH:mm");
	      
			while (rs.next()) { 
				String[] slist = new String[4];
				LocalDateTime timestamp = rs.getTimestamp("WRITTENDATE").toLocalDateTime();
				if (name.equals(rs.getString("NAME"))) {
					slist[0] = "";
					slist[1] = "";
					slist[3] = rs.getString("MESSAGE");
					
					if (timestamp.toLocalDate().equals(today)) {
						slist[2] = timestamp.toLocalTime().format(time);
					} else {
						slist[2] = timestamp.toLocalDate().format(date);
					}
					list.add(slist);
					continue;
				}
				
				slist[0] = rs.getString("NAME");
				slist[1] = rs.getString("MESSAGE");
				
				if (timestamp.toLocalDate().equals(today)) {
					slist[2] = timestamp.toLocalTime().format(time);
				} else {
					slist[2] = timestamp.toLocalDate().format(date);				
				}
				
				slist[3] = "";
				list.add(slist);
			}
	    } catch (SQLException | ClassNotFoundException e) {
	    	e.printStackTrace();
	    }
	    Collections.reverse(list); // 昇順に並べ替え
	    return list;
	}
}
