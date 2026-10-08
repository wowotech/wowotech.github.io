---
title: "玩转BLE(1)_Eddystone beacon"
date: 2016-04-29T22:50:43+08:00
url: "/bluetooth/eddystone_test.html"
gid: "292"
emlog_type: "blog"
summary: "\r\n\t你相信两条命令就可以把自己的破手机变成一个Beacon节点吗？不相信的话就接着往下看吧。\r\n\r\n\r\n\t通过前几篇“蓝牙协议分析”相关的文章，特别是“蓝牙协议分析(3)_蓝牙低功耗(BLE)协议栈介绍”，相信大家对BLE协议栈已经有了基本的认识。在继续后续的分析之前，我们有必要换个视角，从应用的角度，以“玩”的心态，学习并理解BLE的工作原理，并作为后续分析文章的引子和入口。这就是撰写“玩转B"
author: "wowo"
category: "蓝牙"
category_alias: "bluetooth"
tags: ["BLE", "eddystone", "beacon", "hcitool"]
views: 37678
comment_count: 16
aliases:
  - "/bluetooth/292.html"
  - "/292.html"
---

#### 1. 前言

你相信两条命令就可以把自己的破手机变成一个Beacon节点吗？不相信的话就接着往下看吧。

通过前几篇“蓝牙协议分析”相关的文章，特别是“[蓝牙协议分析(3)\_蓝牙低功耗(BLE)协议栈介绍](/bluetooth/ble_stack_overview.html)”，相信大家对BLE协议栈已经有了基本的认识。在继续后续的分析之前，我们有必要换个视角，从应用的角度，以“玩”的心态，学习并理解BLE的工作原理，并作为后续分析文章的引子和入口。这就是撰写“玩转BLE”系列文章的缘由。

之所以起名为“玩转”，是因为我不会在这些文章中涉及任何的技术细节，仅仅是描述一些操作步骤，普及一些蓝牙BLE有关的使用场景。

另外，由于Linux平台使用的蓝牙协议栈是Bluez[1]，Bluez协议栈提供了很多方便、灵活又强大的测试工具（如hcitool、gatttool等）。因此，简单起见，在写“玩转”系列文章的时候，我会尽可能的使用这些测试工具，而不引入复杂的编程手段。从另一个角度看，“玩转”系列文章也是BLE测试的一些步骤总结，方便自己和他人查阅。

本文是“玩转”系列文章的第一篇，以简单的两条hcitool命令，将自己的手机或者开发板变成一个BLE Beacon节点，进而体会BLE技术的简洁和神奇。

#### 2. Eddystone beacon简介

Eddystone beacon是谷歌于2015年7月发布的、开源的、可以多平台使用的、挑战平台iBeacon的低功耗蓝牙Beacon技术。

本文将会直奔主题，介绍怎样把自己的手机或者开发板变成一个Eddystone beacon节点，并使用Android APP测试这个节点。如果读者需要了解Eddystone beacon的技术细节，可参考位于Github的Eddystone的source code及文档[2]，或者参考本站后续有关的分析文章。

#### 3. 创建Eddystone beacon

创建一个（或者多个，如果你喜欢）Eddystone beacon，需要如下条件和步骤。

1）一个具备蓝牙4.0（及以上）功能的、运行Linux系统的、具有Bluez协议栈、可运行hcitool命令的硬件，可以是：

> 一台运行Linux系统（如Ubuntu、Debian）的PC，自身具有蓝牙4.0以上的功能，或者配备一个蓝牙4.0的dongle；
>
> 一个具有蓝牙4.0功能的开发板，如树莓派3，或者树莓派2+蓝牙4.0 dongle；
>
> 一个具有蓝牙4.0功能的Android手机（现在大家使用的手机一般都支持蓝牙4.0，不过Android版本最好是4.3以下，因为4.3以上Android不再使用Bluez协议栈）；
>
> 其它。

本文的例子所使用是一个破手机（酷派5872），刚好符合条件，呵呵呵，手机破就是好！！

2）一个具备蓝牙4.0（及以上）功能的、运行Android5.1系统的平板（或手机，或者开发板），用于运行测试用的APP

> 这个条件不易满足，大家尽量找吧，找不到的话，可以留言，我给大家推荐一些开发板，如S900 96board（此处不是广告，因为没有人给我广告费，呵呵）。

3）以我的手机为例，打开蓝牙功能，使用adb登录到shell（如果是其他环境，则不需要adb），输入下面两条命令：

> # enable BLE advertising   
> hcitool -i hci0 cmd 0x08 0x000A 01
>
> # set advertising data to Eddystone UUID   
> hcitool -i hci0 cmd 0x08 0x0008 1e 02 01 06 03 03 aa fe 17 16 aa fe 00 -10 00 01 02 03 04 05 06 07 08 090a 0b 0e 0f 00 00 00 00

没错，不要惊讶，你的手机已经变成了Eddystone beacon节点。本文先不解释这两条神奇的命令（后续蓝牙分析文章以此为例，分析蓝牙BLE的advertising功能，大家稍安勿躁）。

接下来让我们在Android上下载一个APK，查看我们的成果。

#### 4. 使用Android APP测试Beacon功能

##### 4.1 APP下载

Android具备蓝牙4.0功能，并且是Android5.1（及之后）的版本。测试用的APK有两个（我所知道的）：

1）iBeacon & Eddystone Scanner

Google开发的，可以从Google Play下载运行（地址为：[https://play.google.com/store/apps/details?id=de.flurp.beaconscanner.app&hl=zh\_CN](https://play.google.com/store/apps/details?id=de.flurp.beaconscanner.app&hl=zh_CN "https://play.google.com/store/apps/details?id=de.flurp.beaconscanner.app&hl=zh_CN")）。

如果你的Android设备不能访问Google Play，也可以通过在线APK下载网站（<https://apkpure.com/>）将APK下载到电脑后安装。

如果无论怎样你都下载不到，找我吧，我把下载后的APK共享出来。

2）EddystoneValidator

Eddystone的github出品，网址如下：

[https://github.com/google/eddystone/releases/download/v1.0.0/EddystoneValidator-release-1.0.0.apk](https://github.com/google/eddystone/releases/download/v1.0.0/EddystoneValidator-release-1.0.0.apk "https://github.com/google/eddystone/releases/download/v1.0.0/EddystoneValidator-release-1.0.0.apk")

##### 4.2 安装APP并测试

本文以“iBeacon & Eddystone Scanner”为例，另一个我没有截图，就不描述了。安装成功后打开，点击右下角的扫描按钮，会扫描出Beacon设备的列表，如下：

[![1](/content/uploadfile/201604/b04d1fab75dac2f6b1e003d0235aee3c20160430080025.gif "1")](/content/uploadfile/201604/cba745ebb78753759f3af4dcb9b10bc720160430080024.gif)

点击列表中的Beacon设备，就会出现如下的状态界面：

[![2](/content/uploadfile/201604/3e093b842a3cb417f475319ddd43cf2820160430080027.gif "2")](/content/uploadfile/201604/5a38a1191fb1b17ff350f6654bb3e9d920160430080026.gif)

各状态的具体意义，本文就不过多解释了，大家玩玩就明白了。

#### 5. 参考文档

[1] bluez，[http://www.bluez.org/](http://www.bluez.org/ "http://www.bluez.org/")

[2] Eddystone beacon spec，[https://github.com/google/eddystone](https://github.com/google/eddystone "https://github.com/google/eddystone")

[3] Google beacon开发者页面，[https://developers.google.com/beacons/](https://developers.google.com/beacons/ "https://developers.google.com/beacons/")

*原创文章，转发请注明出处。蜗窝科技，[www.wowotech.net](/bluetooth/eddystone_test.html)。*
