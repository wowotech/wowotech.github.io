---
title: "快讯：蓝牙5.0发布（新特性速览）"
date: 2016-12-08T11:05:39+08:00
url: "/bluetooth/bluetooth_5_0_overview.html"
gid: "362"
emlog_type: "blog"
summary: "\r\n\t2016年12月6日，蓝牙SIG发布了5.0版本的核心规范，该规范从距离、速度等多个方面，对BLE进行了增强，蓝牙官网的总结如下[1]：\r\n\r\n\r\n\t\r\n\t\tWith the launch of Bluetooth 5, Bluetooth® technology continues to \r\nevolve to meet the needs of the industry as the g"
author: "wowo"
category: "蓝牙"
category_alias: "bluetooth"
tags: ["蓝牙", "Bluetooth", "5.0", "2M", "Extensions"]
views: 35447
comment_count: 10
aliases:
  - "/bluetooth/362.html"
  - "/362.html"
---

## 1. 前言

2016年12月6日，蓝牙SIG发布了5.0版本的核心规范，该规范从距离、速度等多个方面，对BLE进行了增强，蓝牙官网的总结如下[1]：

> With the launch of Bluetooth 5, *Bluetooth®* technology continues to evolve to meet the needs of the industry as the global wireless standard for simple, secure connectivity. With 4x range, 2x speed and 8x broadcasting message capacity, the enhancements of Bluetooth 5 focus on increasing the functionality of Bluetooth for the IoT. These features, along with improved interoperability and coexistence with other wireless technologies, continue to advance the IoT experience by enabling simple and effortless interactions across the vast range of connected devices.

相比蓝牙4.2，新增的特性包括[3]：

> Several new features are introduced in the Bluetooth Core Specification 5.0   
> Release. The major areas of improvement are:   
> • Slot Availability Mask (SAM)   
> • 2 Msym/s PHY for LE   
> • LE Long Range   
> • High Duty Cycle Non-Connectable Advertising   
> • LE Advertising Extensions   
> • LE Channel Selection Algorithm #2

下面对一些比较有意思的做个简单的介绍（后续有时间会做比较细致的分析）。

## 2. 2 Msym/s PHY for LE

在蓝牙4.2 1M符号速率（symbol rate）的PHY（称作LE 1M PHY）基础上，增加2M符号速率的PHY（称作LE 2M PHY），二者的区别为：

> 1）LE 1M PHY的符号速率为1Msym/s，为必选PHY（每个LE设备必须支持），支持ECC（error correction coding，可选），根据不同的编码方式，支持3种bit速率：1Mb/s（LE 1M）、500Bb/s（LE Coded）和125Kb/s（LE Coded）。
>
> 2）LE 2M PHY的符号速率为2Msym/s，为可选PHY，不支持ECC（error correction coding），bit速率为2Mb/s（LE 2M，uncoded）。

## 3. LE Long Range

将最大的发送功率，从4.0/4.1/4.2中的10mW增大到5.0的100mW（够粗暴，哈哈）。

关于BLE的发射功率，spec中有张表，贴过来供大家参考：

[![ble_tx_power](/content/uploadfile/201612/1537232e44e87415bb21f7d8bca6d37920161208030538.gif "ble_tx_power")](/content/uploadfile/201612/d998ffd183a969becfd1e19e8f9084fb20161208030537.gif)

## 4. High Duty Cycle Non-Connectable Advertising

蓝牙4.0将Scannable Undirected和Non-connectable Undirected两种Advertising Event的advInterval的最小值限制为100ms，这就限制了BLE广播的最高速率（2.48kbps，参考[4]）。而蓝牙5.0不再区别对待，将最小值统一限制为20ms，从理论上讲，最高的广播速率就可以提高5倍（12.4kbps）。

## 5. LE Advertising Extensions

这个扩展比较好玩。

蓝牙4.0/4.1/4.2的广播通道（可参考[4]），比较简单、直接，预留3个（可以更少）Physical Channel，用于传输Advertising Event。可传输的数据长度为6～37 octets（加上了协议开销）。

而蓝牙5.0，则搞出了新花样（实用性大增，从此之后就没有连接的必要了啊！），总结为：

> 1）抽象出primary advertising channel和secondary advertising channel的概念。
>
> 2）primary advertising channel就是蓝牙4.2及以前的、预留出的、用于传输Advertising Event。
>
> 3）而secondary advertising channel，则直接复用了剩余的37个data channel，用于传输扩展的Advertising Event（称作Extended Advertising Event）。此时可传输的数据长度为0 ～ 255 octets，相比之前的37，暴增了很多倍，好爽啊！！
>
> 4）因此，在原有的用于传输广播数据的PDU（ADV\_IND、ADV\_DIRECT\_IND、ADV\_NONCONN\_IND以及ADV\_SCAN\_IND，称作legacy PDUs）的基础上，增加了扩展的PDU（ADV\_EXT\_IND、AUX\_ADV\_IND、AUX\_SYNC\_IND以及AUX\_CHAIN\_IND，称作extended advertising PDUs）。
>
> 5）相应的，Advertising Event也分为Legacy Advertising Event和Extenteded Advertising Event。

## 6. 参考文档

[1] [https://www.bluetooth.com/specifications/bluetooth-core-specification/bluetooth5](https://www.bluetooth.com/specifications/bluetooth-core-specification/bluetooth5 "https://www.bluetooth.com/specifications/bluetooth-core-specification/bluetooth5")

[2] [https://www.bluetooth.com/specifications/adopted-specifications](https://www.bluetooth.com/specifications/adopted-specifications "https://www.bluetooth.com/specifications/adopted-specifications")

[3] [https://www.bluetooth.org/DocMan/handlers/DownloadDoc.ashx?doc\_id=421043](https://www.bluetooth.org/DocMan/handlers/DownloadDoc.ashx?doc_id=421043 "https://www.bluetooth.org/DocMan/handlers/DownloadDoc.ashx?doc_id=421043")

[4] [蓝牙协议分析(5)\_BLE广播通信相关的技术分析](/bluetooth/ble_broadcast.html)

原创文章，转发请注明出处。蜗窝科技，[www.wowotech.net](/bluetooth/bluetooth_5_0_overview.html)。
