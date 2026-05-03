我要做一個天然瓦斯自報度數的hacs

https://www.slgas.com.tw/Report_SQL.asp 這是第一道
能在hacs 內讓使用者自訂欄位值嗎
1.用戶編號 CusNo:018519
2.用戶名稱 CusName :林鑫秦
3.用戶手機 Cuscallno:0911617190
4.能拉取homeassisant 攝影機 裝置,選了記錄entity id 存檔嗎
5.能拉取homeassisant input.text 裝置,選了記錄entity id　存檔嗎
6.瓦斯錶度數 CusDegree 
一個每日,幾時幾分,
時間到 執行排程 選擇 4.能拉取homeassisant 攝影機 裝置  拍照,存檔在這個目錄下叫 gas.jpg
用action google ai ocr 讀出瓦斯表度數,將值存入 5.能拉取homeassisant input.text 裝置
使用 Sensor 的擴展屬性 (Extra Attributes) —— 最簡單直接
我們可以建立一個專門的感測器，例如叫做 sensor.slgas_last_report。
第二道 ttps://www.slgas.com.tw/GetDegree_SQL.asp
用 6.瓦斯錶度數 CusDegree
1個按鈕 submit 送出


在功能上加入一個按鈕,執行以上功能 https://www.slgas.com.tw/Report_SQL.asp
成功後會顯示 html
<html> 
<head>
<meta http-equiv="Content-Type" content="text/html; charset=big5"> 
<title>線上自報度數</title> 
</head> 

<body link="#FF0000" text="#800000">

  <br>
  <center>
  <table width="90%" border="0" cellpadding="3" cellspacing="2">
    <tr>
      <td align="center" valign="middle" bgcolor="#008080" width="100%" height="60" colspan="2"> 
        <font color="#FFFF00" size="5">用戶線上自報度數</font>
        <p>
        <font color="#FFFF00" size="3">瓦斯錶度數已登錄完成，謝謝您！</font>
      </td>
    </tr>
    <tr bgcolor="#336699"> 
      <td width="25%" bgcolor="#FFCC66" align="right"><font color="#336699">用戶編號</font></td>
      <td width="75%" bgcolor="#FFCC66"><font color="#800000">018519</font></td>
    </tr>
    <tr bgcolor="#336699"> 
      <td width="25%" bgcolor="#FFCC66" align="right"><font color="#336699">用戶名稱</font></td>
      <td width="75%" bgcolor="#FFCC66"><font color="#800000">林鑫秦</font></td>
    </tr>
    <tr bgcolor="#336699"> 
      <td width="25%" bgcolor="#FFCC66" align="right"><font color="#336699">原留電話</font></td>
      <td width="75%" bgcolor="#FFCC66"><font color="#800000">                </font></td>
    </tr>
    <tr bgcolor="#336699"> 
      <td width="25%" bgcolor="#FFCC66" align="right"><font color="#336699">更新電話</font></td>
      <td width="75%" bgcolor="#FFCC66"><font color="#800000">               </font></td>
    </tr>
    <tr bgcolor="#336699"> 
      <td width="25%" bgcolor="#FFCC66" align="right"><font color="#336699">裝置住址</font></td>
      <td width="75%" bgcolor="#FFCC66"><font color="#800000">基隆市正義路100巷70號</font></td>
    </tr>
    <tr bgcolor="#336699"> 
      <td width="25%" bgcolor="#FFCC66" align="right"><font color="#336699">電子郵件信箱</font></td>
      <td width="75%" bgcolor="#FFCC66"><font color="#800000">maxrd@gmail.com</font></td>
    </tr>
    <tr bgcolor="#336699"> 
      <td width="25%" bgcolor="#FFCC66" align="right"><font color="#336699">瓦斯錶度數</font></td>
      <td width="75%" bgcolor="#FFCC66"><font color="#800000">131</font></td>
    </tr>
    <tr bgcolor="#336699"> 
	  <td width=100% align=center colspan=2 bgcolor=#FF9900><a href=Report_SQL.asp><img border=0 src=images/button10.gif></a></td>
    </tr>  
  </table>  
  </center>  


</body>    
</html> 

我能在成功後,計錄 日期,度數,在哪裏方便hacs 整合查看

git add releas

git add .
git commit -m "Update to version 2026.5.1"
git push
