---
title: "玩转BLE(3)_使用微信蓝牙精简协议伪造记步数据"
date: 2017-03-11T11:42:14+08:00
url: "/bluetooth/weixin_ble_1.html"
gid: "385"
emlog_type: "blog"
summary: "在物联网时代，有一个问题肯定会让人头疼（现在已经初露端倪了）： 物联网中的IOT设备有两个主要特点： 1）简单小巧（不具备复杂的人机交互接口，需要手机等终端设备辅助完成配置、控制等功能）。 2）数量和种类繁多（消费者面对的可是数量众多的不同厂家、不同类型的设备）。 基于这两个特点，手机等终端设备一般通过APP（或APK）对IOT设备进行控制，不同厂家的不同设备，通常需要不同的APP/APK。于是出"
author: "wowo"
category: "蓝牙"
category_alias: "bluetooth"
tags: ["蓝牙", "Bluetooth", "BLE", "golang", "微信", "airsync", "iot"]
views: 35328
comment_count: 21
aliases:
  - "/bluetooth/385.html"
  - "/385.html"
---

## 1. 前言

在物联网时代，有一个问题肯定会让人头疼（现在已经初露端倪了）：

> 物联网中的IOT设备有两个主要特点：   
> 1）简单小巧（不具备复杂的人机交互接口，需要手机等终端设备辅助完成配置、控制等功能）。   
> 2）数量和种类繁多（消费者面对的可是数量众多的不同厂家、不同类型的设备）。
>
> 基于这两个特点，手机等终端设备一般通过APP（或APK）对IOT设备进行控制，不同厂家的不同设备，通常需要不同的APP/APK。于是出现了这样的结果：   
> 如果你家里有一个小米yeelight的床头灯，你需要安装一个yeelight的APP/APK；   
> 如果你手上戴一个百度智能手环，你需要安装一个百度智能手环APP/APK；   
> 如果你跑步时戴一个xxx运动蓝牙耳机，你需要安装一个xxx运动蓝牙耳机APP/APK；   
> 如果你要骑摩拜单车，你需要安装一个摩拜单车APP/APK；   
> 如果你也行骑一下优拜单车，你需要安装一个优拜单车APP/APK；   
> ……（要列的话，我觉得永远都列不完，大家可以想象一下，这是不是一个灾难？？）

既然有问题，肯定就有人试图解决，于是微信IoT、阿里小智、亚马逊IoT等等，互联网大佬们就各显神通了。最终谁能称霸天下，现在还不得而知，本文也不去讨论这些。

作为蓝牙BLE的介绍文章，本文将以微信IoT的“微信蓝牙精简协议”为例，通过“把一个蓝牙适配器模拟成微信计步器”，分别从BLE技术（怎样注册一个GATT service）和微信IoT（微信物联网平台的思路和想法）两个角度，窥一窥IoT江湖的冰山一角（权当开阔眼界了）。

## 2. 微信蓝牙精简协议简介

微信蓝牙精简协议的思路很简单（具体可参考“[http://iot.weixin.qq.com/wiki/new/index.html?page=4-3](http://iot.weixin.qq.com/wiki/new/index.html?page=4-3 "http://iot.weixin.qq.com/wiki/new/index.html?page=4-3")“），如下图：

[![微信蓝牙精简协议-框图](/content/uploadfile/201703/8f462a23fdb34fdb6b8d38d5969921c420170311034149.gif "微信蓝牙精简协议-框图")](/content/uploadfile/201703/e9b5ae4516aafc95f622f0acb2b333ac20170311034148.gif)

图片1 微信蓝牙精简协议框架

总结来说，就是：

> 通过微信（可以运行在手机、平板、电脑、等硬件上面）统一和IoT设备交互；
>
> 交互的介质是BLE协议（可以摇身变为其它无线协议）；
>
> 交互的过程可由服务器协助完成（服务器可选择微信服务器或者第三方服务器）。

虽然思路简单，背后却有深深的“不怀好意”，因为：

> 1）IoT设备想要和微信（或者微信背后的服务器）交互，就必须遵守微信定义的协议；
>
> 2）IoT设备通过微信和服务的交互（无论是第三方服务器，还是微信服务器），都必须遵守微信定义的协议，并经由微信服务器转发。
>
> 基于上面两点，物联网中最重要的两个环节：设备和数据，都掌握在微信的手中了。恐怖！！

到目前为止，“微信蓝牙精简协议”有一个比较成熟的应用实例：微信计步器，其工作流程为：

> 1）在带有计步功能的BLE设备上，按照协议规定的方式，基于BLE GATT，实现相应的Profile、Service、Attribute。
>
> 2）在微信公众平台，为该设备申请一个唯一的设备ID，并和设备的MAC地址一起，在公众平台上注册、授权。
>
> 3）在微信的微信运动小程序中，扫描并添加该设备，即可通过BLE读取设备的计步信息。
>
> 4）微信运动读取计步信息后，可以进行后续的动作（例如在朋友圈刷排名等）。

以上步骤，后面章节将会使用一个蓝牙适配器（模拟蓝牙计步器），配合自己的手机微信，进行演示说明。

## 3. 将蓝牙适配器模拟成一个计步器

#### 3.1 环境准备

后续实验基于如下的硬件、软件环境（其它环境也okay，不过我没有测试）。

> 运行Ubuntu为例的PC、笔记本（或者开发板），包含蓝牙4.0（及以上）功能（自带或者使用蓝牙适配器）；
>
> Ubuntu中安装有较新版本的Bluez协议栈及工具集，以及其它必须的软禁包（具体步骤略，碰到问题的时候可以一点点解决）；
>
> 具有BLE功能的手机（上面有可以正常使用的微信）；

#### 3.2 搭建Golang开发环境

在包含Bluez（及相关工具集）的Linux OS中，使用Bluez的工具，可以完成大部分的BLE实验，例如：

> hcitool、bluetoothctl等工具，可以进行BLE设备的扫描、连接、配对、广播等操作；
>
> hcitool可以发送HCI command，设置BLE的广播数据；
>
> gatttool可以在GATT层面，完成GATT profile的连接、service attribute的读写等操作；
>
> 等等。

但有一个功能点，不是很容易实现，就是如何自定义一个GATT profile（要知道，BLE 90%以上的功能都是通过GATT实现的，如果做到这一点，学习BLE就非常方便了）。当然，BLE不复杂，我们可以直接使用BLuez提供的API，自行开发。如果是产品开发，无可厚非，但是如果仅仅只做个实验，这样大张旗鼓的就不划算了，最好能有一些开源的工具。确实有，我搜集、尝试过几种工具：

> 1）使用bluez的测试代码（bluez-5.37/test/example-gatt-server），是一个python脚本。这个家伙对环境依赖度比较高，很难用，最终没有用起来。
>
> 2）一个由nodejs脚本写的工具（[https://github.com/luluxie/weixin-iot](https://github.com/luluxie/weixin-iot "https://github.com/luluxie/weixin-iot")）。基本功能还好，不过本人对js不太熟，就算了。
>
> 3）一个由Go语言写的工具（[https://github.com/paypal/gatt）](https://github.com/paypal/gatt "https://github.com/paypal/gatt
> ")。功能OK，关键还是新奇的Go语言，果断使用～～

这就是搭建Golang开发环境的原因。至于步骤，很简单（以Ubuntu为例）：

> 1）安装Go语言   
> sudo apt install golang
>
> 2）创建GOPATH环境变量   
> mkdir ~/gopath   
> export GOPATH=$HOME/gopath #为了方便，可以放到~/.profile中

#### 3.3 代码准备

在github上，从<https://github.com/paypal/gatt>中clone一个仓库，clone的仓库地址为<https://github.com/wowotech/gatt>。clone后使用go get命令，下载代码到本地：

> vim@ubuntu:~$ go get github.com/wowotech/gatt

下载后代码的位置为：

> vim@ubuntu:~$ ls $GOPATH/src/github.com/wowotech/
>
> gatt

然后，手动将代码中所有的“github.com/paypal”类型的import修改为“github.com/wowotech”（fuck Go！！）

> cd $GOPATH/src/github.com/wowotech/gatt
>
> find . -name "\*.go" | xargs sed -i 's/paypal/wowotech/g'

提交记录如下：

> <https://github.com/wowotech/gatt/commit/1f1c23e94cb7e1b54078a568a60cf1aaef7de195>

#### 3.4 编译并运行一个示例文件.

（略）。

#### 3.5 支持“微信蓝牙精简协议”

参考examples/server.go以及蓝牙精简协议的定义[1]，新建weixin.go，增加微信蓝牙精简协议。最终的文件如下（代码很简单，熟悉BLE GATT协议的同学，很容易看懂，就不过多解释了）：

> [https://github.com/wowotech/gatt/commit/942e7480ad1664dabacdb5561fa98a831621f7de](https://github.com/wowotech/gatt/commit/942e7480ad1664dabacdb5561fa98a831621f7de "https://github.com/wowotech/gatt/commit/942e7480ad1664dabacdb5561fa98a831621f7de")

注1：可以通过代码中如下的定义修改计步的步数（想刷爆微信运动朋友圈的同学注意了，嘿嘿！！）：

> + // steps little endian
>
> + // 01(steps) 10 27 00(0x002710 = 10000)
>
> + // http://iot.weixin.qq.com/wiki/new/index.html?page=4-3
>
> + steps := []byte{ 0x01, 0x5c, 0x74, 0x01 }

#### 3.6 编译、运行、测试

编译：

> vim@ubuntu:~/gopath/src/github.com/wowotech/gatt/examples$ go build weixin.go

运行：

> vim@ubuntu:~/gopath/src/github.com/wowotech/gatt/examples$ sudo ./weixin
>
> [sudo] password for vim:
>
> 2017/03/04 01:03:13 dev: hci0 up   
> 2017/03/04 01:03:14 dev: hci0 down   
> 2017/03/04 01:03:14 dev: hci0 opened   
> State: PoweredOn   
> 2017/03/04 01:03:14 BD Addr: 5C:F3:70:6A:BA:27   
> 2017/03/04 01:03:14 Generating attribute table:   
> 2017/03/04 01:03:14 handle type props secure pvt value   
> 2017/03/04 01:03:14 0x0001 0x2800 0x02 0x00 \*gatt.Service [ E7 FE ]   
> 2017/03/04 01:03:14 0x0002 0x2803 0x32 0x00 \*gatt.Characteristic [ 32 03 00 A1 FE ]   
> 2017/03/04 01:03:14 0x0003 0xfea1 0x32 0x00 \*gatt.Characteristic [ ]   
> 2017/03/04 01:03:14 0x0004 0x2902 0x0E 0x00 \*gatt.Descriptor [ 00 00 ]   
> 2017/03/04 01:03:14 0x0005 0x2803 0x3E 0x00 \*gatt.Characteristic [ 3E 06 00 A2 FE ]   
> 2017/03/04 01:03:14 0x0006 0xfea2 0x3E 0x00 \*gatt.Characteristic [ ]   
> 2017/03/04 01:03:14 0x0007 0x2902 0x0E 0x00 \*gatt.Descriptor [ 00 00 ]   
> 2017/03/04 01:03:14 0x0008 0x2803 0x02 0x00 \*gatt.Characteristic [ 02 09 00 C9 FE ]   
> 2017/03/04 01:03:14 0x0009 0xfec9 0x02 0x00 \*gatt.Characteristic [ ]

然后在手机下载AirSyncDebugger2.3.0.apk（<http://iot.weixin.qq.com/wiki/new/index.html?page=4-3>的底部）测试精简协议是否okay：

> 打开APK---->精简协议---->计步器测试

测试界面如下（Android平台）：

[![wx-蓝牙精简协议-AirSyncDebugger](/content/uploadfile/201703/3c26d09fdcbc5720c2b118f92ed4f38020170311035024.gif "wx-蓝牙精简协议-AirSyncDebugger")](/content/uploadfile/201703/801a5f17b152b1884cbefeb7070633aa20170311035023.gif)

## 4. 在微信公众平台注册并授权设备

第2章成功模拟出来一个遵守“微信蓝牙精简协议”的计步器之后，我们需要登录微信的公众平台（可以使用测试帐号），注册一个产品类别，并授权该设备，之后就可以在微信运动界面使用这个设备了。

#### 4.1 登录“微信公众平台接口测试帐号”

打开下面链接：

<http://mp.weixin.qq.com/debug/cgi-bin/sandbox?t=sandbox/login>

点击登录按钮，用自己微信的扫一扫登录，登录后的界面如下：

[![wx-iot-登录界面](/content/uploadfile/201703/e4718e03a9ad108655faed51f1e3dede20170311035025.gif "wx-iot-登录界面")](/content/uploadfile/201703/69e83b9ff1d4742ac740b292f959c31b20170311035025.gif)

注意图中红色涂抹的三个信息（要记录下来，后面有用）：

> 微信号：   
> appID：   
> appsecret：

#### 4.2 开启设备功能接口

将上面的登录界面往下拉，找到“功能服务”，“设备功能”，点击“开启”，开启设备功能接口，如下图：

[![wx-iot-设备功能接口](/content/uploadfile/201703/ee1b2bd43a61ff7fd99414ee2bead83f20170311035026.gif "wx-iot-设备功能接口")](/content/uploadfile/201703/4002748d55e3ef83c015c851b734186a20170311035026.gif)

#### 4.3 添加产品

设备功能接口开启后，会出现“设置”按钮，点击进入下一个界面，进行设备功能管理。在该界面，点击“添加产品”按钮，为我们的计步器设备添加一个产品类别：

[![wx-iot-添加产品](/content/uploadfile/201703/cff110489efab3a74063cb7141d04b0120170311035027.gif "wx-iot-添加产品")](/content/uploadfile/201703/ff8d489cdce08a88e7d8ad2726ff3cb120170311035027.gif)

按照提示填入相关的信息（需要注意红色圈出的地方）：

[![wx-iot-基础资料登记1](/content/uploadfile/201703/093f0d51fc9f6e69a12def20df1458bc20170311035028.gif "wx-iot-基础资料登记1")](/content/uploadfile/201703/d7fe96cb32bbffb6e02c8c967b18771d20170311035028.gif)

[![wx-iot-基础资料登记2](/content/uploadfile/201703/c0b150e4eb768306de5287a9c4d326bc20170311035029.gif "wx-iot-基础资料登记2")](/content/uploadfile/201703/a8875994cfd2124bce3218a0a8ab693920170311035029.gif)

点击“下一步”进入“产品能力登记”界面：

[![wx-iot-产品能力登记](/content/uploadfile/201703/4a49dae6018c8ebce4825ed96309728420170311035031.gif "wx-iot-产品能力登记")](/content/uploadfile/201703/0f9a0a839a289727c4635cb514e9fc3020170311035030.gif)

最后，点击“添加”按钮，将产品添加进去。添加成功后，进入如下的界面（注意其中红色涂抹的那一串数字，是产品的ID，记下来，后面有用）：

[![wx-iot-product_id](/content/uploadfile/201703/3870a5c05d6d6889e4d5c3791c08c06220170311035032.gif "wx-iot-product_id")](/content/uploadfile/201703/3ffe94ae28e19280739652c4001596bd20170311035031.gif)

#### 4.4 授权设备

**4.4.1 获取access\_token**

根据上面得到的appID和appsecret，在浏览器里面输入如下指令，获取访问微信公众平台的token（令牌）：

https://api.weixin.qq.com/cgi-bin/token?grant\_type=client\_credential&appid=xxxxxxxxxx&secret=xxxxxxxx

注意红色部分要修改为实际内容（具体可参考4.1章节获取的信息）。

浏览器会返回如下内容：

> {"access\_token":"xxxxxxxxxxxxxxxxxxx","expires\_in":7200}

有两个字段，access\_token（记录下来，后面有用）和有效时间（7200秒，很长了）。

**4.4.2 为设备生成一个唯一ID（device\_id）及二维码（通过微信扫描即可添加设备）**

在浏览器输入如下指令：

https://api.weixin.qq.com/device/getqrcode?access\_token=xxxxxxxxxxxx&product\_id=xxxxx

其中access\_token为4.4.1中获取的，product\_id为4.3中获取的。

浏览器的返回如下：

> {"base\_resp":{"errcode":0,"errmsg":"ok"},"deviceid":"xxxxxx","qrticket":"http:\/\/we.qq.com\/d\/AQArGYez06UDOcqKNe1jqWeeLhiF7fIKebEP5hiT"}

deviceid为新生成的唯一ID，记录下来，后面有用。

qrticket是设备的二维码，随便找一个二维码生成的网站（例如<http://cli.im/>），就可得到图片二维码，如下（注意需要将浏览器返回的转义字符改回正常）：

[![wx-iot-二维码获取](/content/uploadfile/201703/01d97c6ad1a29f9062fc9f07e86e7e3920170311035033.gif "wx-iot-二维码获取")](/content/uploadfile/201703/0c6bf00bed43e4241ec6e687538bb70120170311035032.gif)

**4.4.3 设备鉴权**

这一步要借助微信公众平台的debug页面了，单纯的浏览器无法搞定。打开如下的debug地址：

> <http://mp.weixin.qq.com/debug/>

找到如下界面：

[![wx-iot-设备授权](/content/uploadfile/201703/da6a58a408e7a54c932090e2aa29e86320170311035034.gif "wx-iot-设备授权")](/content/uploadfile/201703/357b8e0799ce33e8c3e797eb70d703b620170311035034.gif)

body输入的内容如下：

> {   
> "device\_num":"1",   
> "device\_list":[   
> {   
> "id":" xxxxxxxx",   
> "mac":"5CF3706ABA27",   
> "connect\_protocol":"3",   
> "auth\_key":"",   
> "close\_strategy":"1",   
> "conn\_strategy":"5",   
> "crypt\_method":"0",   
> "auth\_ver":"0",   
> "manu\_mac\_pos":"-1",   
> "ser\_mac\_pos":"-2",   
> "ble\_simple\_protocol": "1"   
> }   
> ],   
> "op\_type":"0",   
> "product\_id": "xxxxx"   
> }

注意上面红色的字段，id是4.4.2中获得的deviceid，mac是蓝牙设备的物理地址，product\_id是4.3中获得产品ID的。

点击“检查问题”，看到如下的成功信息，说明授权成功了：

[![wx-iot-授权成功](/content/uploadfile/201703/8a3078de65dc1a410fdc1c91d43b1f8020170311035036.gif "wx-iot-授权成功")](/content/uploadfile/201703/fb1f3ab18cbce5295ae795d63717098720170311035035.gif)

## 5. 使用手机微信绑定设备

使用微信扫一扫，扫描刚才获得的二维码，点击“绑定设备”，即可添加设备，如下：

[![wx-扫一扫绑定设备](/content/uploadfile/201703/0150f57a6dee327744e45127586facd920170311035037.gif "wx-扫一扫绑定设备")](/content/uploadfile/201703/7357f550baefad98e82cafcb85730aa420170311035036.gif)

绑定成功后，设备显示未连接，如下：

[![wx-绑定设备未连接](/content/uploadfile/201703/872eb8b21a7c8d53bb8e56032fffb40020170311034209.gif "wx-绑定设备未连接")](/content/uploadfile/201703/89c57c8ec0ba4e5fdedb924120b32f3720170311034208.gif)

接下来要连接设备。对iOS来说，在设置界面无法主动连接BLE设备，必须有应用程序自行连接，这里以微信运动为例，搜索并连接刚才授权的那个设备，即可看到计步数据的更新。步骤如下面图片（不再解释了，大家可以自己试试）：

[![wx-微信运动-设置](/content/uploadfile/201703/b97837a961548c4ccc592a5e766149c120170311034210.gif "wx-微信运动-设置")](/content/uploadfile/201703/16b8b149232eafea146907597829b2d120170311034209.gif)

[![wx-微信运动-添加数据来源](/content/uploadfile/201703/695e217b9f8275de82a4e7ff44a7c49a20170311034212.gif "wx-微信运动-添加数据来源")](/content/uploadfile/201703/c4a4bd51dc3c6f9427733731f1bc58cf20170311034211.gif)

[![wx-微信运动-搜索并添加设备](/content/uploadfile/201703/7eb66f0f2812121a53a04c06ca39729c20170311034213.gif "wx-微信运动-搜索并添加设备")](/content/uploadfile/201703/6cd07beddddb64e7ac5d1fd466d75d1b20170311034212.gif)

## 6. 参考文档

[1] 微信蓝牙精简协议，[http://iot.weixin.qq.com/wiki/new/index.html?page=4-3](http://iot.weixin.qq.com/wiki/new/index.html?page=4-3 "http://iot.weixin.qq.com/wiki/new/index.html?page=4-3")

[2] <https://github.com/paypal/gatt>

```
原创文章，转发请注明出处。蜗窝科技，www.wowotech.net。
```
