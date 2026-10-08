---
title: "Linux MMC framework(1)_软件架构"
date: 2017-01-10T22:24:45+08:00
url: "/comm/mmc_framework_arch.html"
gid: "368"
emlog_type: "blog"
summary: "\r\n\t由[1]中MMC、SD、SDIO的介绍可知，这三种技术都是起源于MMC技术，有很多共性，因此Linux kernel统一使用MMC framework管理所有和这三种技术有关的设备。\r\n\r\n\r\n\t本文将基于[1]对MMC技术的介绍，学习Linux kernel MMC framework的软件架构。\r\n"
author: "wowo"
category: "通信类协议"
category_alias: "comm"
tags: ["Linux", "Kernel", "内核", "架构", "Architecture", "framework", "mmc"]
views: 28162
comment_count: 9
aliases:
  - "/comm/368.html"
  - "/368.html"
---

## 1. 前言

由[1]中MMC、SD、SDIO的介绍可知，这三种技术都是起源于MMC技术，有很多共性，因此Linux kernel统一使用MMC framework管理所有和这三种技术有关的设备。

本文将基于[1]对MMC技术的介绍，学习Linux kernel MMC framework的软件架构。

## 2. 软件架构

Linux kernel的驱动框架有两个要点（尽管本站前面的文章已经多次强调，本文还是要再说明一下，因为这样的设计思想，说一千遍都不会烦）：

> 1）抽象硬件（硬件架构是什么样子，驱动框架就应该是什么样子）。
>
> 2）向“客户”提供使用该硬件的API（之前我们提到最多的客户是“用户空间的Application”，不过也有其它“客户”，例如内核空间的其它driver、其它framework）。

以本文的描述对象为例，MMC framework的软件架构如下面“图片1”所示：

[![mmc_architecture](/content/uploadfile/201701/50b2a0c2bbf76a81a7a5fd9549b7daae20170110142443.gif "mmc_architecture")](/content/uploadfile/201701/d07215f202ec5295dd60b88a86e2660020170110142442.gif)

图片1 Linux MMC framework软件架构

MMC framework分别有“从左到右”和“从下到上”两种层次结构。

1） 从左到右

MMC协议是一个总线协议，因此包括Host controller、Bus、Card三类实体（从左到右）。相应的，MMC framework抽象出了host、bus、card三个软件实体，以便和硬件一一对应：

> host，负责驱动Host controller，提供诸如访问card的寄存器、检测card的插拔、读写card等操作方法。从设备模型的角度看，host会检测卡的插入，并向bus注册MMC card设备；
>
> bus，是MMC bus的虚拟抽象，以标准设备模型的方式，收纳MMC card（device）以及对应的MMC driver（driver）；
>
> card，抽象具体的MMC卡，由对应的MMC driver驱动（从这个角度看，可以忽略MMC的技术细节，只需关心一个个具有特定功能的卡设备，如存储卡、WIFI卡、GPS卡等等）。

2）从下到上

MMC framework从下到上也有3个层次（老生常谈了）：

> MMC core位于中间，是MMC framework的核心实现，负责抽象host、bus、card等软件实体，负责向底层提供统一、便利的编写Host controller driver的API；
>
> MMC host controller driver位于底层，基于MMC core提供的框架，驱动具体的硬件（MMC controller）；
>
> MMC card driver位于最上面，负责驱动MMC core抽象出来的虚拟的card设备，并对接内核其它的framework（例如块设备、TTY、wireless等），实现具体的功能。

## 3. 工作流程

基于图片1中的软件架构，Linux MMC framework的工作流程如下：

[![mmc_opt_flow](/content/uploadfile/201701/610a9ad18af8205f2c8d6e9c2d24c82d20170110142445.gif "mmc_opt_flow")](/content/uploadfile/201701/133ff2349cf343a5d07bccb6c266b5ca20170110142444.gif)

图片2 MMC操作流程

暂时不进行详细介绍，感兴趣的同学可以照着代码先看看。后续其它文章会逐一展开。

*原创文章，转发请注明出处。蜗窝科技*，[www.wowotech.net](/comm/mmc_framework_arch.html)。
