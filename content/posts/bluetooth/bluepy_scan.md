---
title: "玩转BLE(2)_使用bluepy扫描BLE的广播数据"
date: 2016-05-19T15:17:18+08:00
url: "/bluetooth/bluepy_scan.html"
gid: "298"
emlog_type: "blog"
summary: "在linux平台下，bluez是一个很不错的软件，提供了很多基于命令行的测试工具，如hciconfig、hcitool、hcidump、bluetoothctl等。利用这些工具，我们可以方便的测试、demo各种蓝牙功能。例如，在“ 玩转BLE(1)_Eddystone beacon ”中，我们利用hcitool命令，演示了将手机变成一个Beacon设备的神奇效果。 Beacon的演示，从本质上看，"
author: "wowo"
category: "蓝牙"
category_alias: "bluetooth"
tags: ["蓝牙", "Bluetooth", "BLE", "scan", "bluepy", "advertising"]
views: 42977
comment_count: 15
aliases:
  - "/bluetooth/298.html"
  - "/298.html"
---

#### 1. 前言

在linux平台下，bluez是一个很不错的软件，提供了很多基于命令行的测试工具，如hciconfig、hcitool、hcidump、bluetoothctl等。利用这些工具，我们可以方便的测试、demo各种蓝牙功能。例如，在“[玩转BLE(1)\_Eddystone beacon](/bluetooth/eddystone_test.html)”中，我们利用hcitool命令，演示了将手机变成一个Beacon设备的神奇效果。

Beacon的演示，从本质上看，是BLE Advertising（广播）功能的测试和验证。自然而然的，我们会好奇：怎么接收这些广播数据呢（其实就是BLE Scanning功能）？这就是本文要介绍的内容。

虽然hcitool（以及后来的bluetoothctl）可以进行简单的LE scan操作，但返回的结果仅包括简单的地址和名称，显然无法满足我们的需求（要知道，BLE的广播数据可能包含其它内容哦，如我们的Beacon演示）。怎么办呢？不着急，强大的python出马了。

#### 2. bluepy[1]介绍

bluepy是linux平台中，用python脚本封装的BLE接口。为什么用python呢？说实话，在写这篇文章之前，我对python的印象是极其平淡的，但此时却好感大增。以蓝牙的测试为例：

> 在linux下，bluez提供的原生接口是一个C库（bluetooth lib），我们想利用这个接口，在命令行里面玩转一些功能，几乎不可能；
>
> 提供C库的同时，为了图形界面操作方便，bluez又封装出来了一层dbus API。虽然从理论上讲，使用dbus-send等命令，可以满足我们在命令行的测试需求。但是，我觉得没有人喜欢dbus-send后面带的那长长的一串参数……
>
> 在开源的世界里，有需求就有动力，因此就出现了很多有python封装的蓝牙API。以BLE为例，bluepy是一个比较好的一个。有了该接口之后，蓝牙功能的测试，真的是很爽！

#### 3. bluepy安装

bluepy的安装非常简单，开始之前先交代一下我的测试环境：

> 硬件环境是树莓派2（大家随便用一个运行linux的PC、开发板应该都okay）；
>
> OS是raspbian（Ubuntu），版本应该不是很重要；
>
> bluez的版本是5.23（比较新的一个版本了，不过旧版本应该也没有问题）。

```
安装bluepy只需要两个命令，如下：
```

> `#安装python的包管理工具—pip`
>
> `sudo apt-get install python-pip libglib2.0-dev`
>
> `#使用pip安装bluepy`
>
> `sudo pip install bluepy`

#### 4. 使用bluepy

```
本章我们将使用bluepy的Scanner class，扫描正在广播的BLE设备。bluepy的文档中有sample code：
```

> ```
> http://ianharvey.github.io/bluepy-doc/scanner.html
> ```

```
在本地新建一个python脚本（ble_scan.py），将sample code中的代码拷贝进去即可，如下：
```

> ```
> from bluepy.btle import Scanner, DefaultDelegate
> ```
>
> class ScanDelegate(DefaultDelegate):   
> def \_\_init\_\_(self):   
> DefaultDelegate.\_\_init\_\_(self)
>
> def handleDiscovery(self, dev, isNewDev, isNewData):   
> if isNewDev:   
> print "Discovered device", dev.addr   
> elif isNewData:   
> print "Received new data from", dev.addr
>
> scanner = Scanner().withDelegate(ScanDelegate())   
> devices = scanner.scan(10.0)
>
> for dev in devices:   
> print "Device %s (%s), RSSI=%d dB" % (dev.addr, dev.addrType, dev.rssi)   
> for (adtype, desc, value) in dev.getScanData():   
> print " %s = %s" % (desc, value)

按照“[玩转BLE(1)\_Eddystone beacon](/bluetooth/eddystone_test.html)”中的说明，将自己的手机变成一个Eddystone Beacon设备。然后执行python脚本，扫描：

> sudo python ble\_scan.py

结果如下：

> pi@raspberrypi:~$ sudo python ble\_scan.py   
> Discovered device cb:07:c8:52:ce:d6   
> Discovered device 18:dc:56:a6:25:6f   
> Device 18:dc:56:a6:25:6f (public), RSSI=-59 dB   
> Flags = 06  
> Complete 16b Services = aafe  
> 16b Service Data = aafe00f0000102030405060708090a0b0e0f000000  
> Device cb:07:c8:52:ce:d6 (random), RSSI=-85 dB   
> Complete Local Name = My Mambo   
> Complete 16b Services = e7fe   
> Manufacturer = 0000cb07c852ced6   
> 128b Service Solicitation = d0002d121e4b0fa4994eceb531f40579   
> Flags = 06

对比一下我们在“[玩转BLE(1)\_Eddystone beacon](/bluetooth/eddystone_test.html)”中广播的数据（对应三个颜色）：

> 1e 02 01 0603 03 aa fe17 16 aa fe 00 -10 00 01 02 03 04 05 06 07 08 09 0a 0b 0e 0f 00 00 00 00

```
成功了！
```

#### 5. 总结

`本文简单的介绍了利用bluepy功能，扫描BLE的广播包的过程。并没有对bluepy的软件逻辑，以及BLE Advertising的细节，做过多的说明，感兴趣的同学可以自行阅读，不理解的地方可以留言讨论。`

`另外，后续BLE Advertising & Scanning有关的分析文章中，会借助该工具，以帮助理解。`

#### 6. 参考文档

```
[1] bluepy github主页，
```

```
 
```

```
原创文章，转发请注明出处。蜗窝科技，www.wowotech.net。
```
