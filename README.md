# duidu

经典对读制作：多版本对读网页制作工具，支持科判、注解

## 安装

## 简易免安装

在 发行版(releases)可下载 64位 Windows/Mac 免安装包程序。运行时遇到360或杀毒软件警告时，选择允许运行或信任，是误报。
本地db数据库中用户 admin 和 demo 的初始密码为 d123，在自动打开的网页中可用此直接登录。

### 开发和维护

- 安装 Python 3.8 ~ 3.11
  - Win7 用 3.8.10，Win 10/11 最高选择 3.11
    - 勾选 Add Python 3.x to PATH
    - 勾选 py launcher，以便可直接运行 python 脚本文件
  - Mac、Linux 用默认的或升级到3.8以上
- 安装可选的 MongoDB 5.0+(个人使用可不安装，用本地文件数据库即可)
- 安装依赖库 `pip3 install -r requirements.txt`
- 运行脚本`python3 main.py`，或在 PyCharm 中选中 `main.py` 调试，然后打开控制台提示的页面
  - 用本地文件数据库时，用户 admin 和 demo 的初始密码为 d123

### 打包

如上安装了开发环境后，运行下列命令制作免安装包(退出360安全卫士等杀毒软件)
```
pip3 install pyinstaller
pyinstaller main.spec -y
```

## 欢迎改进

本项目采用MIT开源许可，您可参与改进或改编使用，可提 issue 讨论或在微信群提问。

## 参考资料
- [jQuery contextMenu](https://swisnl.github.io/jQuery-contextMenu/docs.html)
- [Bootstrap 3.x](https://v3.bootcss.com/components/)
- [jsTree](https://www.bookstack.cn/read/jsTree-doc/)
- [SweetAlert2](https://sweetalert2.github.io)
- [Tornado](https://www.osgeo.cn/tornado/)
