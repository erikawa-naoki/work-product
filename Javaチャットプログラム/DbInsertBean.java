package usedb;

import java.io.*;
import java.sql.*;

public class DbInsertBean implements Serializable {
	
	private String server = "//172.21.40.30:5432/";
	private String database = "firstdb";
	private String url="jdbc:postgresql:" + server + database;

	private String message;
	
	public void setMessage(String message){
		this.message = message; 
	}
    public String getMessage(){
    	return message;
    }
    public void Record(String message) {
		try {
			Class.forName("org.postgresql.Driver");
			// SQL文を定義
			String sql = "INSERT INTO T_LOG VALUES (?,?,?,?)";
			Connection con = DriverManager.getConnection(url,"shibaura", "toyosu");
			
			PreparedStatement prestmt = con.prepareStatement(sql);
			prestmt.setString(1, "AL22001");
			prestmt.setString(2, "江利川直葵");
			prestmt.setString(3, message);
			prestmt.setTimestamp(4, new Timestamp(System.currentTimeMillis() + 32400000));
			// データベースの更新
			prestmt.executeUpdate();
			// PreparedStatementをクローズ
			prestmt.close();
			con.close();
		} catch (Exception e) {
			e.printStackTrace();
		}	
    }
}

