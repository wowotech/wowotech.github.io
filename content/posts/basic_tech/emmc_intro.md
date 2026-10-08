---
title: "eMMC 原理 2 ：eMMC 简介"
date: 2017-01-12T20:28:40+08:00
url: "/basic_tech/emmc_intro.html"
gid: "369"
emlog_type: "blog"
summary: "eMMC 是 embedded MultiMediaCard 的简称。MultiMediaCard，即 MMC， 是一种闪存卡（Flash Memory Card）标准，它定义了 MMC 的架构以及访问　Flash Memory 的接口和协议。而 eMMC 则是对 MMC 的一个拓展，以满足更高标准的性能、成本、体积、稳定、易用等的需求。"
author: "codingbelief"
category: "基础技术"
category_alias: "basic_tech"
tags: ["emmc"]
views: 36791
comment_count: 3
aliases:
  - "/basic_tech/369.html"
  - "/369.html"
---

eMMC 是 embedded MultiMediaCard 的简称。MultiMediaCard，即 MMC， 是一种闪存卡（Flash Memory Card）标准，它定义了 MMC 的架构以及访问　Flash Memory 的接口和协议。而 eMMC 则是对 MMC 的一个拓展，以满足更高标准的性能、成本、体积、稳定、易用等的需求。

eMMC 的整体架构如下图片所示：

![](https://linux.codingbelief.com/zh/storage/flash_memory/emmc/emmc_architecture.png)

图片： eMMC 整体架构

eMMC 内部主要可以分为 Flash Memory、Flash Controller 以及 Host Interface 三大部分。

## 1. Flash Memory

Flash Memory 是一种非易失性的存储器，通常在嵌入式系统中用于存放系统、应用和数据等，类似与 PC 系统中的硬盘。

目前，绝大部分手机和平板等移动设备中所使用的 eMMC 内部的 Flash Memory 都属于 NAND Flash，关于 NAND Flash 的更多细节可以参考 [Flash Memory](https://linux.codingbelief.com/zh/storage/flash_memory/index.html) 章节。

eMMC 在内部对 Flash Memory 划分了几个主要区域，如下图所示：

![](https://linux.codingbelief.com/zh/storage/flash_memory/emmc/emmc_partitions.png)

图片：eMMC 内部分区

1. BOOT Area Partition 1 & 2  
   此分区主要是为了支持从 eMMC 启动系统而设计的。  
   该分区的数据，在 eMMC 上电后，可以通过很简单的协议就可以读取出来。同时，大部分的 SOC 都可以通过 GPIO 或者 FUSE 的配置，让 ROM 代码在上电后，将 eMMC BOOT 分区的内容加载到 SOC 内部的 SRAM 中执行。
2. RPMB Partition  
   RPMB 是 Replay Protected Memory Block 的简称，它通过 HMAC SHA-256 和 Write Counter 来保证保存在 RPMB 内部的数据不被非法篡改。  
   在实际应用中，RPMB 分区通常用来保存安全相关的数据，例如指纹数据、安全支付相关的密钥等。
3. General Purpose Partition 1～4  
   此区域则主要用于存储系统或者用户数据。 General Purpose Partition 在芯片出厂时，通常是不存在的，需要主动进行配置后，才会存在。
4. User Data Area  
   此区域则主要用于存储系统和用户数据。  
   User Data Area 通常会进行再分区，例如 Android 系统中，通常在此区域分出 boot、system、userdata 等分区。

更多 eMMC 分区相关的细节，请参考 [eMMC 分区管理](https://linux.codingbelief.com/zh/storage/flash_memory/emmc/emmc_partitions.html) 章节。

## 2. Flash Controller

NAND Flash 直接接入 Host 时，Host 端通常需要有 NAND Flash Translation Layer，即 NFTL 或者 NAND Flash 文件系统来做坏块管理、ECC等的功能。

eMMC 则在其内部集成了 Flash Controller，用于完成擦写均衡、坏块管理、ECC校验等功能。相比于直接将 NAND Flash 接入到 Host 端，eMMC 屏蔽了 NAND Flash 的物理特性，可以减少 Host 端软件的复杂度，让 Host 端专注于上层业务，省去对 NAND Flash 进行特殊的处理。同时，eMMC 通过使用 Cache、Memory Array 等技术，在读写性能上也比 NAND Flash 要好很多。

![](https://linux.codingbelief.com/zh/storage/flash_memory/emmc/emmc_vs_nand_flash.png)

图片：NAND Flash 与 eMMC

## 3. Host Interface

eMMC 与 Host 之间的连接如下图所示：

![](https://linux.codingbelief.com/zh/storage/flash_memory/emmc/emmc_host_interfaces.png)

图片：eMMC Interface

各个信号的用途如下所示：

CLK  
用于同步的时钟信号

Data Strobe  
此信号是从 Device 端输出的时钟信号，频率和 CLK 信号相同，用于同步从 Device 端输出的数据。该信号在 eMMC 5.0 中引入。

CMD  
此信号用于发送 Host 的 command 和 Device 的 response。

DAT0-7  
用于传输数据的 8 bit 总线。

Host 与 eMMC 之间的通信都是 Host 以一个 Command 开始发起的。针对不同的 Command，Device 会做出不同的响应。详细的通信协议相关内容，请参考 [eMMC 总线协议](https://linux.codingbelief.com/zh/storage/flash_memory/emmc/emmc_bus_protocol.html) 章节。

## 4. 参考资料

1. [Embedded Multi-Media Card (e•MMC) Electrical Standard (5.1)](http://www.jedec.org/sites/default/files/docs/JESD84-B51.pdf) [PDF]

*原创文章，转发请注明出处。蜗窝科技*
