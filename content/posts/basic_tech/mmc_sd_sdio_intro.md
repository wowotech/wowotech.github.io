---
title: "MMC/SD/SDIO介绍"
date: 2016-12-25T21:52:05+08:00
url: "/basic_tech/mmc_sd_sdio_intro.html"
gid: "365"
emlog_type: "blog"
summary: "熟悉Linux kernel的人都知道，kernel使用MMC subsystem统一管理MMC、SD、SDIO等设备，为什么呢？到底什么是MMC？SD和SDIO又是什么？为什么可以用MMC统称呢？ 在分析Linux kernel的MMC subsystem之前，有必要先介绍一些概念，以便对MMC/SD/SDIO有一个大致的了解，这就是本文的目的。"
author: "wowo"
category: "基础技术"
category_alias: "basic_tech"
tags: ["emmc", "mmc", "sd", "sdio"]
views: 55971
comment_count: 6
aliases:
  - "/basic_tech/365.html"
  - "/365.html"
---

## 1. 前言

熟悉Linux kernel的人都知道，kernel使用MMC subsystem统一管理MMC、SD、SDIO等设备，为什么呢？到底什么是MMC？SD和SDIO又是什么？为什么可以用MMC统称呢？

在分析Linux kernel的MMC subsystem之前，有必要先介绍一些概念，以便对MMC/SD/SDIO有一个大致的了解，这就是本文的目的。

## 2. 基本概念

MMC是MultiMediaCard的简称，从本质上看，它是一种用于固态非易失性存储的内存卡（memory card）规范[1]，定义了诸如卡的形态、尺寸、容量、电气信号、和主机之间的通信协议等方方面面的内容。

从1997年MMC规范发布至今，基于不同的考量（物理尺寸、电压范围、管脚数量、最大容量、数据位宽、clock频率、安全特性、是否支持SPI mode、是否支持DDR mode、等等），进化出了MMC、SD、microSD、SDIO、eMMC等不同的规范（如下面图片1所示）。虽然乱花迷人，其本质终究还是一样的，丝毫未变，这就是Linux kernel将它们统称为MMC的原因。

[![mmc_sd_sdio_history](/content/uploadfile/201612/95d6d6a51a757c21cdc3108e12d16d0320161225135202.gif "mmc_sd_sdio_history")](/content/uploadfile/201612/45b6e3aeed9e014036481cbdc767d96920161225135201.gif)

图片1 MMC/SD/SDIO evolution

关于该图片，这里强调几点（其它的，大家可参考[1][2]，不再详细介绍）：

> MMC、SD、SDIO的技术本质是一样的（使用相同的总线规范，等等），都是从MMC规范演化而来；
>
> MMC强调的是多媒体存储（MM，MultiMedia）；
>
> SD强调的是安全和数据保护（S，Secure）；
>
> SDIO是从SD演化出来的，强调的是接口（IO，Input/Output），不再关注另一端的具体形态（可以是WIFI设备、Bluetooth设备、GPS等等）。

## 3. 规范简介

MMC分别从卡（Card Concept）、总线（Bus Concept）以及控制器（Host Controller）三个方面，定义MMC system的行为，如下面图片2所示：

[![mmc_sd_sdio_hw_block](/content/uploadfile/201612/fbcc70f4593e41a6f96a28c4667a9c3420161225135203.gif "mmc_sd_sdio_hw_block")](/content/uploadfile/201612/1dd98218bcd00111510a094902eccf4720161225135203.gif)

图片2 mmc\_sd\_sdio\_hw\_block

不同岗位的工程师，可以根据自己的工作性质，重点理解某一部分的规范，下面从嵌入式软件工程师的视角，简单的介绍一下。

#### 3.1 卡的规范

卡的规范主要规定卡的形状、物理尺寸、管脚，内部block组成、寄存器等等，以eMMC为例[3]：

[![Card Concept(eMMC)](/content/uploadfile/201612/4ca87abb20c96c2362ed22855c0fb89a20161225135205.gif "Card Concept(eMMC)")](/content/uploadfile/201612/78483df39a056808e374a54d62e5534e20161225135204.gif)

图片3 Card Concept(eMMC)

1）有关形状、尺寸的内容，这里不再介绍，感兴趣的同学可参考[1]。

2）卡的内部由如下几个block组成：

> Memory core，存储介质，一般是NAND flash、NOR flash等；
>
> Memory core interface，管理存储介质的接口，用于访问（读、写、擦出等操作）存储介质；
>
> Card interface（CMD、CLK、DATA），总线接口，外界访问卡内部存储介质的接口，和具体的管脚相连；
>
> Card interface controller，将总线接口上的协议转换为Memory core interface的形式，用于访问内部存储介质；
>
> Power模块，提供reset、上电检测等功能；
>
> 寄存器（图片1中位于Card interface controller的左侧，那些小矩形），用于提供卡的信息、参数、访问控制等功能。

3）卡的管脚有VDD、GND、RST、CLK、CMD和DATA等，VDD和GND提供power，RST用于复位，CLK、CMD和DATA为MMC总线协议（具体可参考3.2小节）的物理通道：

> CLK有一条，提供同步时钟，可以在CLK的上升沿（或者下降沿，或者上升沿和下降沿）采集数据；
>
> CMD有一条，用于传输双向的命令。
>
> DATA用于传说双向的数据，根据MMC的类型，可以有一条（1-bit）、四条（4-bit）或者八条（8-bit）。

4）以eMMC为例，规范定义了OCR, CID, CSD, EXT\_CSD, RCA 以及DSR 6组寄存器，具体含义后面再介绍。

## 3.2 总线规范

前面我们提到过，MMC的本质是提供一套可以访问固态非易失性存储介质的通信协议，从产业化的角度看，这些存储介质一般集成在一个独立的外部模块中（卡、WIFI模组等），通过物理总线和CPU连接。对任何有线的通信协议来说，总线规范都是非常重要的。关于MMC总线规范，简单总结如下：

1）物理信号有CLK、CMD和DATA三类。

2）电压范围为1.65V和3.6V（参考上面图片2），根据工作电压的不同，MMC卡可以分为两类：

> High Voltage MultiMediaCard，工作电压为2.7V~3.6V。
>
> Dual Voltage MultiMediaCard，工作电压有两种，1.70V~1.95V和2.7V~3.6V，CPU可以根据需要切换。

3）数据传输的位宽（称作data bus width mode）是允许动态配置的，包括1-bit (默认)模式、4-bit模式和8-bit模式。

> 注1：不使用的数据线，需要保持上拉状态，这就是图片2中的DATA中标出上拉的原因。另外，由于数据线宽度是动态可配的，这要求CPU可以动态的enable/disable数据线的那些上拉电阻。

4）MMC规范定义了CLK的频率范围，包括0-20MHz、0-26MHz、0-52MHz等几种，结合数据线宽度，基本决定了MMC的访问速度。

5）总线规范定义了一种简单的、主从式的总线协议，MMC卡位从机（slave），CPU为主机（Host）。

6）协议规定了三种可以在总线上传输的信标（token）：

> Command，Host通过CMD线发送给Slave的，用于启动（或结束）一个操作（后面介绍）；
>
> Response，Slave通过CMD线发送给Host，用于回应Host发送的Command；
>
> Data，Host和Slave之间通过数据线传说的数据。方向可以是Host到Slave，也可以是Slave到Host。数据线的个数可以是1、4或者8。在每一个时钟周期，每根数据线上可以传输1bit或者2bits的数据。

7）一次数据传输过程，需要涉及所有的3个信标。一次数据传输的过程也称作Bus Operation，根据场景的不同，MMC协议规定了很多类型的Bus Operation（具体可参考相应的规范）。

#### 3.3 控制器规范

Host控制器是MMC总线规范在Host端的实现，也是Linux驱动工程师比较关注的地方，后面将会结合Linux MMC framework的有关内容，再详细介绍。

## 4. 总结

本文对MMC/SD/SDIO等做了一个简单的介绍，有了这些基本概念之后，在Linux kernel中编写MMC驱动将不再是一个困难的事情（因为MMC是一个协议，所有有关协议的事情，都很简单，因为协议是固定的），我们只需要如下步骤即可完成：

> 1）结合MMC的规范，阅读Host MMC controller的spec，理解有关的功能和操作方法。
>
> 2）根据Linux MMC framework的框架，将MMC bus有关的操作方法通过MMC controller实现。

具体可参考后续MMC framework的分析文档。

## 5. 参考文档

[1] [https://en.wikipedia.org/wiki/MultiMediaCard](https://en.wikipedia.org/wiki/MultiMediaCard "https://en.wikipedia.org/wiki/MultiMediaCard")

[2] [https://en.wikipedia.org/wiki/Secure\_Digital](https://en.wikipedia.org/wiki/Secure_Digital "https://en.wikipedia.org/wiki/Secure_Digital")

[3] eMM spec（注册后可免费下载），[http://www.jedec.org/standards-documents/results/jesd84-b51](http://www.jedec.org/standards-documents/results/jesd84-b51 "http://www.jedec.org/standards-documents/results/jesd84-b51")

原创文章，转发请注明出处。蜗窝科技，[www.wowotech.net](/basic_tech/mmc_sd_sdio_intro.html)。
