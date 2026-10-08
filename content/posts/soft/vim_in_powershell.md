---
title: "在PowerShell中使用Vim"
date: 2014-06-18T11:41:24+08:00
url: "/soft/vim_in_powershell.html"
gid: "55"
emlog_type: "blog"
summary: "\r\n\t闲来无事，买了一个Win8系统的小平板，带键盘，准备打造成专门用来写博客的工具（本文就是用它写的第一篇）。捣鼓一圈之后，首先要解决的是用什么看代码。在PC时代，习惯了Linux命令行的方式，一般都是Windows系统+VMWare虚拟机+Linux系统+Vim+SecureCRT，但是这个庞大配置，显然不适合小平板。于是蜗蜗就打起PowerShell的主意了。\r\n\r\n\r\n\t蜗蜗想要的无非就是"
author: "wowo"
category: "软件开发"
category_alias: "soft"
tags: ["vim", "win8", "powershell"]
views: 35703
comment_count: 7
aliases:
  - "/soft/55.html"
  - "/55.html"
---

闲来无事，买了一个Win8系统的小平板，带键盘，准备打造成专门用来写博客的工具（本文就是用它写的第一篇）。捣鼓一圈之后，首先要解决的是用什么看代码。在PC时代，习惯了Linux命令行的方式，一般都是Windows系统+VMWare虚拟机+Linux系统+Vim+SecureCRT，但是这个庞大配置，显然不适合小平板。于是蜗蜗就打起PowerShell的主意了。

蜗蜗想要的无非就是一个命令行的环境，加上Vim工具。而微软在WIN7、WIN8时，就在系统中集成了一个Shell工具----PowerShell，这个工具虽然没有Linux系统的Shell强大，但相比Windows的Command Line，还是强大不少。那是否可以利用它呢？答案是肯定的。

首先，需要去Vim官网下载并安装一个可运行于Win8系统的[执行文件](ftp://ftp.vim.org/pub/vim/pc/gvim74.exe)。

然后，设置PowerShell环境，使能“allow scripts to run”选项，步骤如下：

- 以管理员的身份运行PowerShell
- 执行Set-ExecutionPolicy RemoteSigned命令，在对话框中选择Y，如下

```
PS C:\Windows\system32> Set-ExecutionPolicy RemoteSigned

执行策略更改

执行策略可帮助你防止执行不信任的脚本。更改执行策略可能会产生安全风险，如 http://go.microsoft.com/fwlink/?LinkID=135170

中的 about_Execution_Policies 帮助主题所述。是否要更改执行策略?

[Y] 是(Y)  [N] 否(N)  [S] 挂起(S)  [?] 帮助 (默认值为“Y”): Y

PS C:\Windows\system32>
```

接下来，使用new-item命令，创建一个PowerShell的配置文件Profile。

```
new-item -path $profile -itemtype file -force
```

最后，编辑配置文件（notepad $profile），添加vim相关的alias。

```
set-alias vim "C:/Program Files/Vim/Vim74/./vim.exe"



# To edit the Powershell Profile

# (Not that I'll remember this)

Function Edit-Profile

{

    vim $profile

}



# To edit Vim settings

Function Edit-Vimrc

{

    vim $HOME\_vimrc

}
```

重启PowerShell后，就可以正常使用了，如下（后续可以按照正常的方式，配置VIM，这里就不多说了）。![vim_in_powershell.gif](/content/uploadfile/201406/c1671403066468.gif "点击查看原图")

原创文章，转发请注明出处。蜗窝科技，[/soft/vim_in_powershell.html](/soft/vim_in_powershell.html)
