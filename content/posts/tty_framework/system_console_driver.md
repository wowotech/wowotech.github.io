---
title: "Linux TTY framework(5)_System console driver"
date: 2016-10-29T22:43:44+08:00
url: "/tty_framework/system_console_driver.html"
gid: "346"
emlog_type: "blog"
summary: "\r\n\t由[1]中的介绍可知，Linux kernel的console框架，主要提供“控制台终端”的功能，用于：\r\n\r\n\r\n\t\r\n\t\t1）kernel日志信息（printk）的输出。\r\n\t\r\n\t\r\n\t\t2）实现基础的、基于控制台的人机交互。\r\n\t\r\n\r\n\r\n\t本文将从console driver开发者的视角，介绍：console有关的机制；编写一个console驱动需要哪些步骤；从用户的角度怎么使用"
author: "wowo"
category: "TTY子系统"
category_alias: "tty_framework"
tags: ["Linux", "Kernel", "内核", "driver", "console"]
views: 16377
comment_count: 13
aliases:
  - "/tty_framework/346.html"
  - "/346.html"
---

## 1. 前言

由[1]中的介绍可知，Linux kernel的console框架，主要提供“控制台终端”的功能，用于：

> 1）kernel日志信息（printk）的输出。
>
> 2）实现基础的、基于控制台的人机交互。

本文将从console driver开发者的视角，介绍：console有关的机制；编写一个console驱动需要哪些步骤；从用户的角度怎么使用；等等。

## 2. 设计思路介绍

不知道大家是否有这样的疑问：既然已经有了TTY框架，为什么要多出来一个console框架，为什么不能直接使用TTY driver的接口实现console功能？

确实，由[2]中的介绍可知，TTY框架的核心功能，就是管理TTY设备，并提供访问TTY设备的API（如数据收发）。而console的两个功能需求，“日志输出”就是向TTY设备发送数据，“控制台人机交互”就是标准的TTY功能。因此从功能上看，完全可以直接使用TTY框架的API啊。

不过，既然存在，一定有其意义。内核之所以要抽象出console框架，思路如下：

1）Linux kernel有一个很强烈的隐性规则----内核空间的代码不应该直接利用用户空间接口访问某些资源，例如kernel代码不应该直接使用文件系统接口访问文件（虽然它可以）。回到本文的场景里面，TTY框架通过字符设备（也即文件系统）向用户空间提供接口，那么kernel的代码（如printk），就不能直接使用TTY的接口访问TTY设备，怎么办呢？开一个口子，从kernel里面再拉出一套接口，这就是console框架，如下图所示：

[![tty_console](/content/uploadfile/201610/2353f5ec19cfd61483d4bd56be223f1e20161029144338.gif "tty_console")](/content/uploadfile/201610/ef430ff7c5a612be31435ed48b50922020161029144335.gif)

2）console框架构建在TTY框架之上，大部分的实现（特别是访问硬件的部分）都和TTY框架复用。

3）系统中可以有多个TTY设备，只有那些附加了console驱动的设备，才有机会成为kernel日志输出的目的地，有机会成为控制台终端。因此，console框架变相的成为管理TTY设备的一个框架。

4）驱动工程师在为某个TTY设备编写TTY driver的时候，会根据实际的需求，评估该TTY设备是否可能成为控制台设备，如果可能，则同时为其编写system console driver，使其成为候选的控制台设备。系统工程师在系统启动的时候，可以通过kernel命令行参数，决定printk会在哪些候选设备上输出，那个候选设备最终会成为控制台设备。示意图如下：

[![console_overview](/content/uploadfile/201610/cea0c551d7ad671f31da3159ecddae1920161029144343.gif "console_overview")](/content/uploadfile/201610/2034292f6db4207e536bad2020f4063420161029144342.gif)

## 3. 核心数据结构

理解了console框架的设计思路之后，再来看它的实现，就很简单了。其核心数据结构为struct console，如下：

> /\* include/linux/console.h \*/
>
> struct console {   
> char name[16];   
> void (\*write)(struct console \*, const char \*, unsigned);   
> int (\*read)(struct console \*, char \*, unsigned);   
> struct tty\_driver \*(\*device)(struct console \*, int \*);   
> void (\*unblank)(void);   
> int (\*setup)(struct console \*, char \*);   
> int (\*match)(struct console \*, char \*name, int idx, char \*options);   
> short flags;   
> short index;   
> int cflag;   
> void \*data;   
> struct console \*next;   
> };

该数据结构中经常被使用的字段有：

name，该console的名称，配合index字段，可用来和命令行中的“console=xxx”中的“xxx”匹配，例如：

> 如果name为“ttyXS”，index为大于等于0的数字（例如2），则可以和“console=ttyXS2”匹配；
>
> 如果name为“ttyXS”，index为小于0的数字（例如-1），则可以和“console=ttySXn“（n=0,1,2…）任意一个匹配。

write，如果某个console被选中作为printk的输出，则kernel printk模块会调用write回调函数，将日志信息输出到。

device，获取该console对应的TTY driver，用于将console和对应的TTY设备绑定，这样控制台终端就可以和console共用同一个TTY设备了。

setup，用于初始化console的回调函数，console driver可以在该回调函数中对硬件做出现动作。可以不实现，如果实现，则必须返回0，否则该console不可用。

flags，指示属性的flags，常用的包括：

> CON\_BOOT，该console是一个临时console，只在启动的时候使用，kernel会在真正的console注册后，把它注销掉。
>
> CON\_CONSDEV，表示该console会被用作控制台终端（和/dev/console对应），对应命令行中的最后一个，例如“console=ttyXS0 console=ttyUSB2”中的ttyUSB2。
>
> CON\_PRINTBUFFER，如果设置了该flag，kernel在该console被注册的时候，会将那些被缓存到buffer中的之前的日志，统统输出到该console上。通常注册的console，如串口console，都会设置该flag，以便可以看到console注册前的日志输出。
>
> CON\_ENABLED，表示该console正在被使用。

## 4. 接口说明

#### 4.1 console driver的注册接口

对具体的console driver来说，只需要关心console的注册/注销接口即可：

> /\* include/linux/console.h \*/
>
> extern void register\_console(struct console \*);   
> extern int unregister\_console(struct console \*);

在正确填充struct console变量之后，通过register\_console接口将其注册到kernel中即可。该接口将会完成如下的事情：

> 检查该console的name和index，确认之前没有注册过，否则注册失败；
>
> 如果该console为boot console（CON\_BOOT），确认是第一个注册的boot console，否则注册失败；
>
> 如果系统中从来没有注册过console，则将第一个被注册的、可以setup成功（.setup为NULL或者返回0）的console作为正在使用的console，并使能之（CON\_ENABLED）；
>
> 和command line中的“console=xxx”最对比，使能那些在命令行中指定的console；
>
> 查找在command line中指定的最后一个console，并置位其CON\_CONSDEV flag，表明选择它为控制台console。

#### 4.2 用户层面接口

系统console的使用控制，主要由命令行参数（一般都是bootloader传递而来的）指定，总结如下：

1）如果某个console只需要在启动的时候使用，则需要在注册console的时候，置位其CON\_BOOT标志，例如[3]中介绍的early console。

2）如果系统中注册了多个console，可以通过命令行参数指定使用哪个或者哪些，kernel的日志将会输出到所有在命令行指定了的console上面。

3）命令行中指定的最后一个console，将会作为控制台console，应用程序打开/dev/console将会打开该console对应的TTY设备（由.device回调返回的tty driver指定）。

## 5. console driver的编写步骤

理解了system console的原理之后，编写一个console driver就比较简单了，包括：

1）如果希望该console可以作为系统控制台（/dev/console），则必须先实现该console对应的TTY设备的TTY driver。

2）定义一个console变量，并根据实际情况填充对应的字段，包括name、index、setup（可选）、write、device（可选）等。

3）调用register\_console将其注册到kernel中即可。

## 6. 参考文档

[1] [Linux TTY framework(3)\_从应用的角度看TTY设备](/tty_framework/application_view.html)

[2] [Linux TTY framework(4)\_TTY driver](/tty_framework/tty_driver.html)

[3] [X-012-KERNEL-serial early console的移植](/x_project/kernel_earlycon_porting.html)

*原创文章，转发请注明出处。蜗窝科技*，[www.wowotech.net](/tty_framework/system_console_driver.html)。
