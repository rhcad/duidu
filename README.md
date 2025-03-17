# duidu

经典对读制作：多版本对读网页制作工具，支持科判、注解

## 编译调试

- 安装 Python 3.8+、可选的 MongoDB 5.0+(可不安装，用本地文件数据库)
- 安装依赖库 `pip3 install -r requirements.txt`
- 运行脚本`python3 main.py`，或在 PyCharm 中选中 `main.py` 调试，然后打开控制台提示的页面
  - 用本地文件数据库时，用户 admin 和 demo 的初始密码为 d123

如果提示端口被占用，可以按如下结束端口上的进程：
```sh
# Windows
netstat -ano | findstr 8000
taskkill -F -PID 行末的PID号
```
```sh
# MacOS
kill -9 `sudo lsof -i:8000 | grep Python | awk -F" " {'print $2'}`
```

## 欢迎改进

本项目采用MIT开源许可，您可参与改进或改编使用，可提 issue 讨论或在微信群提问。

## 参考资料
- [jQuery contextMenu](https://swisnl.github.io/jQuery-contextMenu/docs.html)
- [Bootstrap 3.x](https://v3.bootcss.com/components/)
- [jsTree](https://www.bookstack.cn/read/jsTree-doc/)
- [SweetAlert2](https://sweetalert2.github.io)
- [Tornado](https://www.osgeo.cn/tornado/)
