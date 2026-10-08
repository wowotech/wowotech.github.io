---
title: "Linux TTY framework(2)_软件架构"
date: 2016-09-27T22:42:56+08:00
url: "/tty_framework/tty_architecture.html"
gid: "338"
emlog_type: "blog"
summary: "\r\n\t由“Linux TTY \r\nframework(1)_基本概念”的介绍可知，在Linux \r\nkernel中，TTY就是各类终端（Terminal）的简称。为了简化终端的使用，以及终端驱动程序的编写，Linux kernel抽象出了TTY \r\nframework：对上，向应用程序提供使用终端的统一接口；对下，提供编写终端驱动程序（如serial driver）的统一框架。\r\n\r\n\r\n\t本文是"
author: "wowo"
category: "TTY子系统"
category_alias: "tty_framework"
tags: ["Linux", "Kernel", "架构", "Architecture", "tty"]
views: 25442
comment_count: 3
aliases:
  - "/tty_framework/338.html"
  - "/338.html"
---

## 1. 前言

由“[Linux TTY framework(1)\_基本概念](/tty_framework/tty_concept.html)”的介绍可知，在Linux kernel中，TTY就是各类终端（Terminal）的简称。为了简化终端的使用，以及终端驱动程序的编写，Linux kernel抽象出了TTY framework：对上，向应用程序提供使用终端的统一接口；对下，提供编写终端驱动程序（如serial driver）的统一框架。

本文是Linux TTY framework分析的第二篇文章，将从整体架构的角度，介绍Linux TTY framework，以便分解出功能相对独立的子模块，以便后续的分析。

## 2. 软件架构

Linux kernel TTY framework位于“drivers/tty”目录中，其软件框架如下面图片1所示：

[![tty_arch](/content/uploadfile/201609/b0ad364910887baecc41b39602b39ecd20160927144252.gif "tty_arch")](/content/uploadfile/201609/588316ff34005cfdf8f214ff4c806cda20160927144244.gif)

图片1 Linux TTY framework框架

和Linux其它的framework类似，TTY framework通过TTY core屏蔽TTY有关的技术细节，对上以字符设备的形式向应用程序提供统一接口，对下以TTY device/TTY driver的形式提供驱动程序的编写框架。具体请参考后续章节介绍。

#### 2.1 TTY Core

TTY core是TTY framework的核心逻辑，功能包括：

1）以字符设备的形式，向用户空间提供访问TTY设备的接口，例如：

> 设备号(主, 次) 字符设备 备注   
> (5, 0) /dev/tty 控制终端（Controlling Terminal）   
> (5, 1) /dev/console 控制台终端（Console Terminal）   
> (4, 0) /dev/vc/0 or /dev/tty0 虚拟终端（Virtual Terminal）   
> (4, 1) /dev/vc/1 or /dev/tty1 同上   
> … … …   
> (x, x) /dev/ttyS0 串口终端（名称和设备号由驱动自行决定）   
> … … …   
> (x, x) /dev/ttyUSB0 USB转串口终端   
> … … …

注1：控制终端、控制台终端、虚拟终端等概念，比较抽象，我会在后续的文章中详细介绍。

2）通过设备模型中的struct device结构抽象TTY设备，并通过struct tty\_driver抽象该设备的驱动，并提供相应的register接口。TTY驱动程序的编写，简化为填充并注册相应的struct tty\_driver结构。

注2：TTY framework弱化了TTY设备（图片1中使用虚线框标注）的概念，通常情况下，可以在注册TTY驱动的时候，自动分配并注册TTY设备。

3）使用struct tty\_struct、struct tty\_port等数据结构，从逻辑上抽象TTY设备及其“组件”，以实现硬件无关的逻辑。

4）抽象出名称为线路规程（Line Disciplines）的模块，在向TTY硬件发送数据之前，以及从TTY设备接收数据之后，进行相应的处理（如特殊字符的转换等）。

#### 2.2 System Console Core

Linux kernel的system console主要有两个功能：

1）向系统提供控制台终端（Console Terminal） ，以便让用户登录进行交互操作。

2）提供printk功能，以便kernel代码进行日志输出。

System console core模块使用struct console结构抽象system console功能，具体的driver不需要关心console的内部逻辑，填充该接口并注册给kernel即可。

#### 2.3 TTY Line Disciplines

线路规程（Line Disciplines）在TTY framework中是一个非常优雅的设计，我们可以把它看成设备驱动和应用接口之间的一个适配层。从字面意思理解，就是辅助TTY driver，将我们通过TTY设备键入的字符转换成一行一行的数据[3]，当然，实际情况远比这复杂，例如在蜗窝x project所使用的kernel版本中，存在如下的Line Disciplines（以n\_为前缀，我们后续的文章会更为详细的介绍）：

> pengo@DESKTOP-CH8SB7C:~/work/xprj/linux$ ls drivers/tty/n\_\*   
> drivers/tty/n\_gsm.c drivers/tty/n\_r3964.c drivers/tty/n\_tracesink.c drivers/tty/n\_tty.c   
> drivers/tty/n\_hdlc.c drivers/tty/n\_tracerouter.c drivers/tty/n\_tracesink.h

#### 2.4 TTY Drivers以及System Console Drivers

最后，对内核以及驱动工程师来说，更关注的还是具体的TTY设备驱动。在kernel为我们搭建的如此beauty的框架下面，编写相应的driver就成为一件比较简单的事情了。当然的kernel中，主要的TTY driver有两类：

1）虚拟终端（Virtual Terminal，VT）驱动，位于drivers/tty/vt中，负责实现VT（后续文章会详细介绍）有关的功能。

2）串口终端驱动，也即我们所熟知的serial subsystem（话说终于到重点了，哈哈），位于drivers/tty/serial中。

## 3. 总结

本文对Linux TTY framework的软件框架作了一个简单的介绍，目的是从整体上了解Linux TTY有关的软件实现。基于本文的描述，后续计划从如下角度继续TTY framework的分析：

> 控制终端、控制台终端、虚拟终端等概念的理解及解释；
>
> TTY core的分析；
>
> System Console Core的分析；
>
> Serial subsystem（串口子系统）的分析；
>
> 虚拟终端（VT）的分析；
>
> 常用线路规程（Line Disciplines）的介绍和分析；
>
> 等等。

## 4. 参考文档

[1] [TTY驱动分析](/forum/183.html)

[2] 控制终端（controlling terminal），[https://linux.die.net/man/4/tty](https://linux.die.net/man/4/tty "https://linux.die.net/man/4/tty")

[3] [https://utcc.utoronto.ca/~cks/space/blog/unix/TTYLineDisciplineWhy](https://utcc.utoronto.ca/~cks/space/blog/unix/TTYLineDisciplineWhy "https://utcc.utoronto.ca/~cks/space/blog/unix/TTYLineDisciplineWhy")

*原创文章，转发请注明出处。蜗窝科技*，[www.wowotech.net](/tty_framework/tty_architecture.html)。
