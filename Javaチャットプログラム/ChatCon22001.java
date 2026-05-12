import java.io.*;
import java.util.*;

import javax.servlet.*;
import javax.servlet.http.*;

import usedb.*;
public class ChatCon22001 extends HttpServlet {


    public void doGet(HttpServletRequest request, HttpServletResponse response)
        throws IOException, ServletException {
    	
    	String message = request.getParameter("MESSAGE");
    	String url;
    	if (!message.equals("Q")) {
    		
    		DbInsertBean dib = new DbInsertBean();
    		dib.setMessage(message);
    		dib.Record(message);
    		request.setAttribute("dib", dib);
				
    		url="/chatResult22001.jsp";
    	}else {
    		
    		DbSelectBean dsb = new DbSelectBean();
    		ArrayList<String[]> list = dsb.calc();
    		
    		request.setAttribute("list", list);
    		url="/chatView22001.jsp";
    	}

	//JSPのURL
		RequestDispatcher dispatcher
	     =getServletContext().getRequestDispatcher(url);
		dispatcher.forward(request, response);
    }
}