---
title: "Linux I2C framework(1)_概述"
date: 2016-02-14T22:01:19+08:00
url: "/comm/i2c_overview.html"
gid: "263"
emlog_type: "blog"
summary: "\r\n\tI2C协议是嵌入式系统中广泛使用的一类通信协议，主要用于CPU和各种外设之间的低速数据通信。Linux kernel使用I2C \r\nframework抽象、管理相应的资源，并以各种形式，向各类使用者提供API。另外，作为总线（bus）的一种，I2C framework的实现体现了linux设备模型的精髓，值得研究与学习。这就是攥写“Linux \r\nI2C framework”系列文章的缘由和"
author: "wowo"
category: "通信类协议"
category_alias: "comm"
tags: ["Linux", "Architecture", "framework", "I2C"]
views: 30475
comment_count: 20
aliases:
  - "/comm/263.html"
  - "/263.html"
---

#### 1. 前言

I2C协议是嵌入式系统中广泛使用的一类通信协议，主要用于CPU和各种外设之间的低速数据通信。Linux kernel使用I2C framework抽象、管理相应的资源，并以各种形式，向各类使用者提供API。另外，作为总线（bus）的一种，I2C framework的实现体现了[linux设备模型](/sort/device_model)的精髓，值得研究与学习。这就是攥写“Linux I2C framework”系列文章的缘由和目的。

按照分析各类framework的老规矩，蜗蜗会从4个角度分4篇文章介绍I2C framework：

> 1）Linux I2C framework的整体介绍，包括基础知识、软件框架、API汇整等。就是本文。
>
> 2）从Provider的角度，介绍怎么借助I2C framework管理I2C相关的SOC资源。换句话说，就是怎么编写一个I2C driver。具体可参考“Linux I2C framework(2)\_I2C provider”。
>
> 3）从Consumer的角度，介绍I2C framework为使用者提供了哪些功能、哪些API，以及怎样利用I2C framework编写程序。具体可参考“Linux I2C framework(3)\_I2C consumer”。
>
> 4）从内部实现的角度，分析I2C framework的实现逻辑。具体可参考“Linux I2C framework(4)\_I2C core”。

#### 2. I2C的总线拓扑

I2C是总线的一种，其硬件拓扑如下图所示：[![I2C_hw_topology](/content/uploadfile/201602/211e76f46618e68a19454aacfc39872320160214140113.gif "I2C_hw_topology")](/content/uploadfile/201602/1e95e7bbc6c62d6c9126000073f075c820160214140113.gif)

图片1 I2C H/W topology

关于I2C的硬件拓扑，相信驱动工程师都很熟悉，这里就不过多描述了，但有一点要强调：

> 我们都知道，I2C协议是主从式的，包括master（主设备）和slave（从设备），而Linux kernel的I2C framework只抽象了I2C master有关的功能，换句话说，linux kernel有这样的一个假设：
>
> 所有运行linux kernel的设备，在I2C总线里面，都是I2C master（至于I2C slave，抱歉，kernel不管！）。
>
> 正是基于这样的假设，linux I2C framework才成为当前的样子，具体可参考本文后续的描述。

linux kernel I2C framework使用如下的软件拓扑抽象I2C硬件（我们可以一起领会一下其中的“[设备模型](/sort/device_model)”思想）：

[![I2C_sw_topology](/content/uploadfile/201602/e37c4da1dcb2d9b5a190002b60b3923620160214140115.gif "I2C_sw_topology")](/content/uploadfile/201602/915a833b05f6e3673f579428ccd1fb9420160214140114.gif)

图片2 I2C S/W topology

> 1）platform bus（/sys/bus/platform）是驱动工程师常见的bus，用于挂载和CPU通过系统总线连接的各类外设。在I2C framework中，I2C控制器直接从属于platform bus，我们在linux kernel中常说的I2C driver，都是指I2C controller driver，都是以platform driver的形式存在，当然，对应的控制器是platform device。
>
> 2）与此同时，kernel抽象出I2C bus（/sys/bus/i2c），用于挂载和I2C controller通过I2C总线连接的各个I2C slave device。
>
> 3）比较特殊的地方是，I2C core使用一个虚拟实体----I2C adapter，抽象I2C controller有关的功能（主要是数据的收发），I2C adapter也挂载在I2C bus上。
>
> 4）I2C adapter和I2C slave device都挂载在I2C bus上，就可以方便的进行Master（I2C adapter）和Slave之间的匹配操作，并通过I2C core提供的统一接口，访问I2C salve device，进行数据的收发。
>
> 5）以上各实体在sysfs中的位置，已经在“图片2”中通过红色字体标注，大家可自行理解。

#### 3. 软件框架

基于第2章所述的总线拓扑，Linux kernel抽象出如下的软件框架：

[![I2C_software_architecture](/content/uploadfile/201602/4f2cb4076dab75bd6b582c4ca60e349920160214140116.gif "I2C_software_architecture")](/content/uploadfile/201602/33d425800562e1a03578ff0d8706b3f220160214140116.gif)

图片3 I2C framework software architecture

> 1）I2C framework的最终目标，是提供一种“访问I2C slave devices”的方法。由于这些slave devices由I2C controller控制，因而主要由I2C controller驱动实现这一目标。
>
> 2）经过I2C framework的抽象，consumer可以不用关心I2C总线的技术细节，只需要通过简单的API，就可以与slave devices进行数据交互。正常情况下，consumer是位于内核态的其它driver（如HDMI driver、touch screen driver等等）。与此同时，I2C framework也通过字符设备向用户空间提供类似的接口，用户空间程序可以通过该接口访问slave devices。
>
> 3）在I2C framework内部，有I2C core、I2C busses、I2C algos和I2C muxes四个模块。
>
> 4）I2C core使用I2C adapter和I2C algorithm两个子模块抽象I2C controller的功能，使用I2C client和I2C driver抽象I2C slave device的功能（对应设备模型中的device和device driver）。另外，基于I2C协议，通过smbus模块实现SMBus（System Management Bus，系统管理总线）的功能。
>
> 5）I2C busses是各个I2C controller drivers的集合，位于drivers/i2c/busses/目录下，驱动工程师常说的“I2C driver”就是指它们。
>
> 6）I2C algos包含了一些通用的I2C algorithm，所谓的algorithm，是指I2C协议包的生成方法，进而组合成I2C的read/write指令，一般情况下，都是由硬件实现，不需要特别关注该目录。
>
> 7）I2C muxes用于实现I2C bus的多路复用功能，属于奇葩的冷门功能，暂不过多介绍。

#### 4. I2C有关的软件流程总结

TODO（会在后续文章完成之后再回来补充）。

*原创文章，转发请注明出处。蜗窝科技*，[www.wowotech.net](/comm/i2c_overview.html)。
