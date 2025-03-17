# 常见问题

## 提示端口被占用

可将 srv 下任意py文件改为语法错误的，服务进程就自动停止，或以按如下结束端口上的进程：
```sh
# Windows
netstat -ano | findstr 8000
taskkill -F -PID 行末的PID号
```
```sh
# MacOS
kill -9 `sudo lsof -i:8000 | grep Python | awk -F" " {'print $2'}`
```
