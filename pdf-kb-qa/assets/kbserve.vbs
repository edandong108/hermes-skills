' kbserve.vbs — 图文知识库图片服务(127.0.0.1:8377)开机自启
' 根目录: C:\code\kb\<doc-id>\images\ 多文档布局,URL = /<doc-id>/images/pXX_xNN.png
' 防重复:python socket 探测 8377,已监听则直接退出
Dim shell, fso, py, probe, rc
Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

If Not fso.FolderExists("C:\code\kb") Then WScript.Quit

py = "C:\Python\python.exe"  '【必改】换成对方机器上任意存在的 python.exe 绝对路径
If Not fso.FileExists(py) Then WScript.Quit

probe = py & " -c ""import socket,sys;s=socket.socket();s.settimeout(1);sys.exit(0 if s.connect_ex(('127.0.0.1',8377))==0 else 1)"""
rc = shell.Run(probe, 0, True)
If rc = 0 Then WScript.Quit  ' 端口已在服务,勿重复启动

shell.Run py & " -m http.server 8377 --bind 127.0.0.1 --directory C:\code\kb", 0, False
