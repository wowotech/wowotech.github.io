---
title: "Linux TTY framework(1)_基本概念"
date: 2016-09-18T22:55:42+08:00
url: "/tty_framework/tty_concept.html"
gid: "335"
emlog_type: "blog"
summary: "\n\t由于串口的缘故，TTY是Linux系统中最普遍的一类设备，稍微了解Linux系统的同学，对它都不陌生。尽管如此，相信很少有人能回到这样的问题：TTY到底是什么东西？我们常常挂在嘴边的终端（terminal）、控制台（console）等概念，到底是什么意思？\n\n\n\t本文是Linux TTY framework分析文章的第一篇，将带着上述疑问，介绍TTY有关的基本概念，为后续的TTY软件框架的分析"
author: "wowo"
category: "TTY子系统"
category_alias: "tty_framework"
tags: ["Linux", "Kernel", "内核", "tty", "terminal", "终端", "console", "控制台"]
views: 32474
comment_count: 16
aliases:
  - "/tty_framework/335.html"
  - "/335.html"
---

#### 1. 前言

由于串口的缘故，TTY是Linux系统中最普遍的一类设备，稍微了解Linux系统的同学，对它都不陌生。尽管如此，相信很少有人能回到这样的问题：TTY到底是什么东西？我们常常挂在嘴边的终端（terminal）、控制台（console）等概念，到底是什么意思？

本文是Linux TTY framework分析文章的第一篇，将带着上述疑问，介绍TTY有关的基本概念，为后续的TTY软件框架的分析，以及Linux serial subsystem的分析，打好基础。

#### 2. 终端（terminal）

##### 2.1 基本概念

在计算机或者通信系统中，终端是一个电子（或电气）设备，用于向系统输入数据（input），或者将系统接收到的数据显示出来（output），即我们常说的“人机交互设备”。

关于终端最典型的例子，就是电传打字机（Teletype）[1][2]----一种基于电报技术的远距离信息传送器械。电传打字机通常由键盘、收发报器和印字机构等组成。发报时，按下某一字符键，就能将该字符的电码信号自动发送到信道（input）；收报时，能自动接收来自信道的电码信号，并打印出相应的字符（output）。

##### 2.2 Unix终端

在计算机的世界里，键盘和显示器，是最常用的终端设备，一个用于向计算机输入信息，一个用于显示计算机的输出信息。

在大型机(mainframe)和小型机(minicomputer)的时代里，终端设备和计算机主机都同属一个整体。但到PC时代，情况发生了变化。Unix创始人肯•汤普逊和丹尼斯•里奇想让Unix成为一个多用户系统。多用户系统意味着要给每个用户配置一个终端，每个用户都要有一个显示器、一个键盘。但当时所有的计算机设备(包括显示器)价格都非常昂贵，而且键盘和主机是集成在一起的，根本没有独立的键盘。

最后他们找到了一样东西，那就是ASR33电传打字机。虽然电传打字机的用途是在电报线路上收发电报，但是它也可以作为人与计算机的接口，而且价格低廉。ASR33打字机的键盘用来输入信息，打印纸用来输出信息。所以他们把ASR33电传打字机作为终端，很多个ASR33连接到同一个主机，每个用户都可以在终端输入用户名和密码登录主机。这样他们创造了计算机历史上的第一个真正的多用户系统Unix，而ASR33成为第一个Unix终端。

#### 2.3 TTY设备

由上面的介绍可知，第一个Unix终端是一个名字为ASR33的电传打字机，而电传打字机的英文单词为Teletype（或Teletypewritter），缩写为TTY。因此，该终端设备也被称为TTY设备。这就是TTY这个名称的来源，当然，在现在的Unix/Linux系统中，TTY设备已经演变为不同的意义了，后面我们会介绍演变的过程。

注1：读到这里，希望读者再仔细思索一下“设备”的概念。ASR33的电传打字机本身是一个硬件设备，在Unix/Linux系统中，这个硬件设备被抽象为“TTY设备”。

##### 2.4 串口终端（Serials Terminal）

早期的TTY终端（这里暂时特指电传打字机），一般通过串口和Unix设备连接的，如下所示：

[![tty_teletype](/content/uploadfile/201610/34b79c4ae0c8973a9108999b01a6fdf720161010133810.gif "tty_teletype")](/content/uploadfile/201610/51f40767d6d71630c29a076a310a4eda20161010133809.gif)

然后，正如你我所熟知的，我们可以把上面红色部分（电传打字机），替换为任意的具有键盘、显示器、串口的硬件设备（如另一台PC），如下：

[![tty_any](/content/uploadfile/201610/3015af0063d35373ad2aebe7268f9ef020161010133810.gif "tty_any")](/content/uploadfile/201610/b2fbe5e31513445c0e59fa31e4d7e79920161010133810.gif)

因此，对Unix/Linux系统来说，只要是通过串口连接的设备，都可以作为终端设备，因而不再需要关注具体的终端形态。久而久之，终端设备、TTY设备、串口设备等概念，逐渐混在一起，就不再区分了，总结来说，在当今的Linux系统中：

> 1）TTY设备就是终端设备，终端设备就是TTY设备，无需区分。
>
> 2）所有的串口设备都是TTY设备。
>
> 3）当然，除了串口设备，也发展出来了其它形式的TTY设备，例如虚拟终端（VT）、伪终端（Pseudo Terminal）等等，这些概念本文就不展开描述了，后续会使用专门的文章分析。

#### 3. 控制台（console）

了解了终端和TTY的概念之后，再来看看另一个比较熟悉的概念：console。

回到Unix系统刚刚支持多用户（2.2小节的描述）的时代，此时的PC有一个自带的、昂贵的终端（自身的键盘、显示器等），另外为了支持多用户，可以通过串口线连接多个TTY终端（Teletype）。为了彰显自带终端崇高的江湖地位，人们称它为console。

当然，“江湖地位”之说，纯属玩笑，不过从console的中文翻译-----控制台，可以看出，自带终端（console）有别于TTY终端的地方如下：

> 1）控制台（console）是昂贵的。
>
> 2）控制台（console）比TTY终端拥有更多的权限，例如用户建立、密码更改、权限分配等等，这也是“控制”的意义所在。
>
> 3）系统的运行日志、出错信息等内容，通常只会输出到控制台（console）终端中，以方便管理员进行“控制”和“管理”。

不过，随着计算机技术的发展、操作系统的改进，控制台（console）终端和普通TTY终端的界限越来越模糊，console能做的事情，普通终端也都能做了。因此，console逐渐退化，以至于在当前的Linux系统中，它仅仅保留了第三点“日志输出”的功能，这就是Linux TTY framework中console的概念（具体可参考后续文章的分析）。

#### 4. 参考文章

[1] [https://en.wikipedia.org/wiki/Teleprinter](https://en.wikipedia.org/wiki/Teleprinter "https://en.wikipedia.org/wiki/Teleprinter")

[2] 电传打字机(Teletype)，[http://baike.baidu.com/view/1773688.htm](http://baike.baidu.com/view/1773688.htm "http://baike.baidu.com/view/1773688.htm")

[3] [你真的知道什么是终端吗？](https://www.linuxdashen.com/%E4%BD%A0%E7%9C%9F%E7%9A%84%E7%9F%A5%E9%81%93%E4%BB%80%E4%B9%88%E6%98%AF%E7%BB%88%E7%AB%AF%E5%90%97%EF%BC%9F)

[4] [串口通信技术浅析](/basic_tech/serial_intro.html)

*原创文章，转发请注明出处。蜗窝科技*，[www.wowotech.net](/tty_framework/tty_concept.html)。
