---
title: "蓝牙协议分析(8)_BLE安全机制之白名单"
date: 2016-11-10T14:20:47+08:00
url: "/bluetooth/ble_white_list.html"
gid: "351"
emlog_type: "blog"
summary: "\r\n\t在万物联网的时代，安全问题将会受到非常严峻的挑战（相应地，也会获得最大的关注度），因为我们身边的每一个IOT设备，都是一个处于封印状态的天眼，随时都有被开启的危险。想想下面的场景吧：\r\n\r\n\r\n\t\r\n\t\t凌晨2点，x米手环的闹钟意外启动，将你从睡梦中惊醒，然后床头的灯光忽明忽暗……\r\n\t\r\n\t\r\n\t\t你的心率、血压、睡眠质量等信息，默默地被竞争对手收集着，并通过大数据分析你的情绪、健康等，随"
author: "wowo"
category: "蓝牙"
category_alias: "bluetooth"
tags: ["蓝牙", "Bluetooth", "BLE", "白名单", "white_list"]
views: 37954
comment_count: 12
aliases:
  - "/bluetooth/351.html"
  - "/351.html"
---

## 1. 前言

在万物联网的时代，安全问题将会受到非常严峻的挑战（相应地，也会获得最大的关注度），因为我们身边的每一个IOT设备，都是一个处于封印状态的天眼，随时都有被开启的危险。想想下面的场景吧：

> 凌晨2点，x米手环的闹钟意外启动，将你从睡梦中惊醒，然后床头的灯光忽明忽暗……
>
> 你的心率、血压、睡眠质量等信息，默默地被竞争对手收集着，并通过大数据分析你的情绪、健康等，随时准备给你致命一击……
>
> 我知道你家里有几盏灯、几台电器、几个人，知道你几点睡觉几时醒来，知道你一周做过几顿饭，甚至知道你有一个xx棒、一周使用几次、每次使用多久……
>
> ……

算了，不罗列了，有时间的话可以建个iot eyes的站点，专门收集、整理物联网安全有关的内容。这里就先言归正传。

经过前面几篇的蓝牙协议分析，我们对蓝牙（特别是蓝牙低功耗）已经有了一个比较全面的了解。随后几篇文章，我会focus在BLE的安全机制上。毕竟，知己知彼，才能攻防有度。

话说，蓝牙SIG深知物联网安全的水有多深，因此使用了大量的篇幅，定义BLE安全有关的机制，甚至可以不夸张的说，BLE协议中内容最多、最难理解的部分，非安全机制莫属。本文先从介绍最简单的----白名单机制（White list）。

## 2. 白名单机制

白名单（white list）是BLE协议中最简单、直白的一种安全机制。其原理很简单，总结如下（前面的分析文章中都有介绍）：

> 所谓的白名单，就是一组蓝牙地址；
>
> 通过白名单，可以只允许特定的蓝牙设备（白名单中列出的）扫描（Scan）、连接（connect）我们，也可以只扫描、连接特定的蓝牙设备（白名单中列出的）。

例如，如果某个BLE设备，只需要被受信任的某几个设备扫描、连接，我们就可以把这些受信任设备的蓝牙地址加入到该设备的白名单中，这样就可以有效避免其它“流氓设备”的骚扰了。

不过呢，该机制只防君子不防小人，因为它是靠地址去过滤“流氓”的，如果有些资深流氓，伪装一下，将自己的设备地址修改为受信任设备的地址，那就惨了……

## 3. 白名单有关的HCI命令

注1：本文主要从HCI的角度分析、介绍，如非必要，不再会涉及HCI之下的BLE协议（后续的分析文章，也大抵如此）。

#### 3.1 白名单维护相关的命令

BLE协议在HCI层定义了4个和白名单维护有关的命令，分别如下：

1）LE Read White List Size Command，获取controller可保存白名单设备的个数

该命令的格式为：

|  |  |  |
| --- | --- | --- |
| OCF | Command parameters | Return Parameters |
| 0x000F |  | Status    White\_List\_Size |

> Status，命令执行的结果，0为success。
>
> White\_List\_Size，size，范围是1～255。

注2：由此可知，白名单是保存在controller中，由于size的范围是1～255，因此controller必须实现白名单功能（最少保存一个）。

2）LE Clear White List Command，将controller中的白名单清空

该命令的格式为：

|  |  |  |
| --- | --- | --- |
| OCF | Command parameters | Return Parameters |
| 0x0010 |  | Status |

> Status，命令执行的结果，0为success。

3）LE Add Device To White List Command，将指定的设备添加到白名单

该命令的格式为：

|  |  |  |
| --- | --- | --- |
| OCF | Command parameters | Return Parameters |
| 0x0011 | Address\_type(1 byte)    Address(6 bytes) | Status |

> Address\_type，设备的地址类型[1]，0为Public Device Address，1为Random Device Address。
>
> Address，设备的地址。
>
> Status，命令执行的结果，0为success。

4）LE Remove Device From White List Command，将指定的设备从白名单中移除的命令

该命令的格式为：

|  |  |  |
| --- | --- | --- |
| OCF | Command parameters | Return Parameters |
| 0x0012 | Address\_type(1 byte)    Address(6 bytes) | Status |

> Address\_type，设备的地址类型[1]，0为Public Device Address，1为Random Device Address。
>
> Address，设备的地址。
>
> Status，命令执行的结果，0为success。

最后需要说明的是，当controller处于以下三个状态的时候，以上命令除“LE Read Resolving List Size Command”外，均不能执行：

> 正在advertising；
>
> 正在scanning；
>
> 正在connecting。

#### 3.2 白名单使用策略有关的命令

BLE设备在发起Advertising、Scanning或者Connecting操作的时候，可以通过Set Advertising Parameters、Set Scan Parameters或者LE Create Connection Command，设置Advertising、Scanning或者Connecting的过滤策略（Filter\_Policy），具体如下：

1）Advertising时的白名单策略

LE Set Advertising Parameters Command的命令格式为：

|  |  |  |
| --- | --- | --- |
| OCF | Command parameters | Return Parameters |
| 0x0006 | …    Advertising\_Filter\_Policy(1 byte) | Status |

该命令的其它参数请参考[2]，Advertising\_Filter\_Policy的含义如下：

> 0x00，禁用白名单机制，允许任何设备连接和扫描。
>
> 0x01，允许任何设备连接，但只允许白名单中的设备扫描（scan data中有敏感信息？）。
>
> 0x02，允许任何设备扫描，但只允许白名单中的设备连接。
>
> 0x03，只允许白名单中的设备扫描和连接。

2）Scanning时的白名单策略

LE Set Scan Parameters Command的命令格式为：

|  |  |  |
| --- | --- | --- |
| OCF | Command parameters | Return Parameters |
| 0x000B | …    Scanning\_Filter\_Policy(1 byte) | Status |

该命令的其它参数请参考[2]，Scanning\_Filter\_Policy的含义如下：

> 0x00，禁用白名单机制，接受所有的广播包（除了那些不是给我的directed advertising packets）。
>
> 0x01，只接受在白名单中的那些设备发送的广播包（除了那些不是给我的directed advertising packets）。
>
> 0x02，和白名单无关，不再介绍。
>
> 0x03，接受如下的广播包：在白名单中的那些设备发送的广播包；广播者地址为resolvable private address的directed advertising packets；给我的给我的directed advertising packets。

注3：Scanning时的白名单策略有点奇怪，既然是主动发起的，要白名单的意义就不大了吧？

3）Connecting时的白名单策略

LE Create Connection Command的命令格式为：

|  |  |  |
| --- | --- | --- |
| OCF | Command parameters | Return Parameters |
| 0x000D | …    Initiator\_Filter\_Policy(1 byte)    … | Status |

该命令的其它参数请参考[4]，Initiator\_Filter\_Policy的含义如下：

> 0x00，禁用白名单机制，使用Peer\_Address\_Type and Peer\_Address指定需要连接的设备。
>
> 0x01，连接那些在白名单中的设备，不需要提供Peer\_Address\_Type and Peer\_Address参数。

## 4. 使用示例

## 4.1 准备工作

后续的测试需要用到如下的设备和软件：

1）蓝牙设备A，作为Advertiser，发送广播数据，接受连接。

2）蓝牙设备B，作为Scanner，扫描设备A的广播数据，发起连接。

上述的1）和2）可以是如下一种：

> 一个具有bluez（hcitool等工具）的Android手机，可能需要较旧的android版本才行；
>
> 带有蓝牙功能的树莓派，允许Debian、Ubuntu等系统（只要不是Android就行）；
>
> Linux PC（或者虚拟机）加上一个具有BLE功能的蓝牙适配器。

3）bluez工具集，我们需要使用其中的hcitool命令。

#### 4.2 相关的hcitool命令说明

hcitool中的一些命令，和白名单机制有关，总结如下。

1）hcitool lewlsz，获取controller白名单的size，对应3.1中的LE Read White List Size Command，该命令不需要参数，可直接使用，如下：

> root@android:/ # hcitool lewlsz   
> hcitool lewlsz   
> White list size: 26

2）hcitool lewlclr，情况controller的白名单，对应3.1中的LE Clear White List Command，该命令也不需要参数，可直接使用，如下：

> root@android:/ # hcitool lewlclr   
> hcitool lewlclr

3）hcitool lewladd，将指定设备添加到白名单中，对应3.1中的LE Add Device To White List Command，其格式如下：

> root@android:/ # hcitool lewladd --help   
> hcitool lewladd --help   
> Usage:   
> lewladd [--random]

其中是必选项，为要添加的蓝牙设备的地址。地址有public和random两种，默认是public，如果需要添加random类型的地址，则要指定--random参数，例如：

> root@android:/ # hcitool lewladd 22:22:21:CD:F4:58   
> hcitool lewladd 22:22:21:CD:F4:58
>
> root@android:/ # hcitool lewladd --random 11:22:33:44:55:66   
> hcitool lewladd --random 11:22:33:44:55:66

4）hcitool lewlrm，将指定设备从白名单中移除，对应3.1中的LE Remove Device From White List Command，该命令只需要蓝牙地址作为参数，如下：

> root@android:/ # hcitool lewlrm --help   
> hcitool lewlrm --help   
> Usage:   
> lewlrm

5）hcitool lecc，连接BLE设备的命令，对应3.2中的LE Create Connection Command，可以连接指定地址的设备，也可以直接连接白名单中的设备：

> root@android:/ # hcitool lecc --help   
> hcitool lecc --help   
> Usage:   
> lecc [--random]    
> lecc --whitelist

一般情况下，我们都是通过hcitool lecc 的方式连接蓝牙设备，不过如果我们需要连接白名单中的设备，可直接使用如下命令：

> hcitool lecc --whitelist

6）hcitool cmd，对于其它没有直接提供hcitool命令的HCI操作，我们可以使用hcitool cmd直接发送命令，其使用方法如下：

> root@android:/ # hcitool cmd --help   
> hcitool cmd --help   
> Usage:   
> cmd   [parameters]   
> Example:   
> cmd 0x03 0x0013 0xAA 0x0000BBCC 0xDDEE 0xFF

其中ogf、ocf和parameters可以去蓝牙spec的“HCI COMMANDS AND EVENTS”章节查询。需要注意的是，parameters可以使用各种类型（8位、16位、32位），还是很方便的。

#### 4.3 测试步骤

这里仅仅罗列一个简单的测试，步骤包括：

> 1）设备A作为Advertising设备，不使用白名单，发送正常的ADV\_IND（可连接、可扫描）广播包。
>
> 2）设备B扫描并连接设备A（应该可以正常连接）。
>
> 3）设备A作为Advertising设备，启用白名单，设置Advertising\_Filter\_Policy为0x2(只允许白名单中的设备连接)，且没有把B的地址添加到白名单中。
>
> 4）设备B扫描并连接设备A（应该不可以正常连接）。
>
> 5）设备A把设备B添加到白名单中，其它策略保持不变。
>
> 6）设备B扫描并连接设备A（应该可以正常连接）。

详细步骤如下（我没有测试，有问题的请大家留言告诉我）：  
1）设备A作为Advertising设备，不使用白名单，发送正常的ADV\_IND（可连接、可扫描）广播包。

> # disable BLE advertising   
> hcitool cmd 0x08 0x000A 0x00   
>   
> # 设置广播参数和广播策略   
> # Advertising\_Interval\_Min=0x0800 (1.28 second, default)   
> # Advertising\_Interval\_Max=0x0800 (1.28 second, default)   
> # Advertising\_Type=0x00(ADV\_IND, default)   
> # Own\_Address\_Type=0x00(Public Device Address, default)   
> # Peer\_Address\_Type=0x00(Public Device Address, default)   
> # Peer\_Address=00 00 00 00 00 00 (no use)   
> # Advertising\_Channel\_Map=0x07(all channels enabled, Default)   
> # Advertising\_Filter\_Policy=0x0(禁用白名单)  
> hcitool -i hci0 cmd 0x08 0x0006 0x0800 0x0800 0x00 0x00 0x00 00 00 00 00 00 00 0x07 0x00   
>   
> # enable BLE advertising   
> hcitool cmd 0x08 0x000A 0x01
>
> # set advertising data to Eddystone UUID(可参考[3]中的介绍)   
> hcitool -i hci0 cmd 0x08 0x0008 1e 02 01 06 03 03 aa fe 17 16 aa fe 00 -10 00 01 02 03 04 05 06 07 08 09 0a 0b 0e 0f 00 00 00 00

2）设备B扫描并连接设备A（应该可以正常连接）。

> hcitool lescan   
> hcitool lecc [bdaddr of A]

3）设备A作为Advertising设备，启用白名单，设置Advertising\_Filter\_Policy为0x2(只允许白名单中的设备连接)，且没有把B的地址添加到白名单中。

> # disable BLE advertising   
> hcitool cmd 0x08 0x000A 0x00   
>   
> # 设置广播参数和广播策略   
> # …   
> # Advertising\_Filter\_Policy=0x2(只允许白名单中的设备连接)  
> hcitool -i hci0 cmd 0x08 0x0006 0x0800 0x0800 0x00 0x00 0x00 00 00 00 00 00 00 0x07 0x02
>
> # 清空白名单   
> hcitool lewlclr   
>   
> # 随便加一个地址到白名单   
> hcitool lewladd 11:22:33:44:55:66
>
> # enable BLE advertising   
> hcitool cmd 0x08 0x000A 0x01
>
> # set advertising data to Eddystone UUID(可参考[3]中的介绍)   
> hcitool -i hci0 cmd 0x08 0x0008 1e 02 01 06 03 03 aa fe 17 16 aa fe 00 -10 00 01 02 03 04 05 06 07 08 09 0a 0b 0e 0f 00 00 00 00

4）设备B扫描并连接设备A（应该不可以正常连接）。

> hcitool lescan   
> hcitool lecc [bdaddr of A]

5）设备A把设备B添加到白名单中，其它策略保持不变。

> # disable BLE advertising   
> hcitool cmd 0x08 0x000A 0x00   
>   
> # 设置广播参数和广播策略   
> # …   
> # Advertising\_Filter\_Policy=0x2(只允许白名单中的设备连接)  
> hcitool -i hci0 cmd 0x08 0x0006 0x0800 0x0800 0x00 0x00 0x00 00 00 00 00 00 00 0x07 0x02
>
> # 将B添加到白名单中   
> hcitool lewladd [bdaddr of B]
>
> # enable BLE advertising   
> hcitool cmd 0x08 0x000A 0x01
>
> # set advertising data to Eddystone UUID(可参考[3]中的介绍)   
> hcitool -i hci0 cmd 0x08 0x0008 1e 02 01 06 03 03 aa fe 17 16 aa fe 00 -10 00 01 02 03 04 05 06 07 08 09 0a 0b 0e 0f 00 00 00 00

6）设备B扫描并连接设备A（应该可以正常连接）。

> hcitool lescan   
> hcitool lecc [bdaddr of A]

## 5. 参考文档

[1] [蓝牙协议分析(6)\_BLE地址类型](/bluetooth/ble_address_type.html)

[2] [蓝牙协议分析(5)\_BLE广播通信相关的技术分析](/bluetooth/ble_broadcast.html)

[3] [玩转BLE(1)\_Eddystone beacon](/bluetooth/eddystone_test.html)

[4] [蓝牙协议分析(7)\_BLE连接有关的技术分析](/bluetooth/ble_connection.html)

[5] Core\_v4.2.pdf

原创文章，转发请注明出处。蜗窝科技，[www.wowotech.net](/bluetooth/ble_white_list.html)。
