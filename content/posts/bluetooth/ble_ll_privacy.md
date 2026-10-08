---
title: "蓝牙协议分析(9)_BLE安全机制之LL Privacy"
date: 2016-11-25T16:28:10+08:00
url: "/bluetooth/ble_ll_privacy.html"
gid: "358"
emlog_type: "blog"
summary: "\r\n\t在上一篇文章[1]中，我们介绍了BLE的白名单机制，这是一种通过地址进行简单的访问控制的安全机制。同时我们也提到了，这种安全机制只防君子，不防小人，试想这样一种场景：\r\n\r\n\r\n\t\r\n\t\tA设备表示只信任B、C、D设备，因此就把它们的地址加入到了自己的白名单中，表示只愿意和它们沟通。与此同时，E设备对它们的沟通非常感兴趣，但A对自己不信任啊，肿么办？\r\n\t\r\n\t\r\n\t\tE眼珠子一转，想出一个"
author: "wowo"
category: "蓝牙"
category_alias: "bluetooth"
tags: ["蓝牙", "BLE", "resolvable", "privacy", "安全"]
views: 34003
comment_count: 38
aliases:
  - "/bluetooth/358.html"
  - "/358.html"
---

## 1. 前言

在上一篇文章[1]中，我们介绍了BLE的白名单机制，这是一种通过地址进行简单的访问控制的安全机制。同时我们也提到了，这种安全机制只防君子，不防小人，试想这样一种场景：

> A设备表示只信任B、C、D设备，因此就把它们的地址加入到了自己的白名单中，表示只愿意和它们沟通。与此同时，E设备对它们的沟通非常感兴趣，但A对自己不信任啊，肿么办？
>
> E眼珠子一转，想出一个坏主意：把自己的地址伪装成成B、C、D中任意一个（这个还是很容易办到的，随便扫描一下就得它们的地址了）就行了，嘿嘿嘿！

那么问题来了，怎么摆脱“小人E“的偷听呢？不着急，我们还有手段：“链路层的Privacy（隐私）机制”。

## 2. LL Privacy机制介绍

总结来说，LL Privacy机制是白名单（white list）机制的进阶和加强，它在白名单的基础上，将设备地址转变成Private addresses[2]地址，以降低“小人E“窃得设备地址进而进行伪装的概率。

从白名单的角度看，Non-resolvable private address和Public Device Address/Static Device Address没有任何区别，因此LL Privacy机制主要指Resolvable Private Addresses。因此，LL Privacy机制的本质是：

> 通过Resolvable Private Addresses，将在空中传输的设备地址加密，让“小人E”无法窃得，从而增加其伪装的难度。

注1：当然，LL Privacy机制可以脱离白名单机制单独使用，不过这样的话好像没什么威力。

注2：有关Resolvable Private Addresses、Identity Address、IRK（Local/Peer IRK）等概念的详细介绍，可参考“[蓝牙协议分析(6)\_BLE地址类型](/bluetooth/ble_address_type.html)[2]”，本文将会直接使用。

## 3. Resolving List

和白名单机制上的White List类似，如果设备需要使用LL Privacy机制，则需要在Controller端保存一个Resolving List，其思路为：

1）BLE设备要按照[1]中的介绍，配置并使能白名单机制，把那些受信任设备的地址（这里为Identity Address）加入到自己的白名单中，并采用合适的白名单策略。

2）如果设备需要使用LL Privacy策略，保护自己（以及对方）的地址不被窃取，则需要将自己（local）和对方（peer）的地址和加密key保存在一个称作Resolving List的列表中。

3）Resolving List的每一个条目，都保存了一对BLE设备的key/address信息，其格式为：Local IRK | Peer IRK | Peer Device Identity Address | Address Type。

> Local IRK，本地的IRK，用于将本地设备的Identity Address转换为Resolvable Private Address。可以为0，表示本地地址直接使用Identity Address；
>
> Peer IRK，对端的IRK，用于将对端设备的Resolvable Private Address解析回Identity Address。可以为零，表示对端地址是Identity Address；
>
> Peer Device Identity Address、Address Type，对端设备的Identity Address及类型，用于和解析回的Identity Address进行比对。

4）Resolving List是Host通过HCI命令提供给Controller的，Controller的LL负责如下事项：

> 发送数据包[3]时：   
> 如果有AdvA需要填充，则判断Resolving List是否有非0的Local IRK，如果有，则使用Local IRK将Identity Address加密为Resolvable Private Address，填充到AdvA中。否则，直接填充Identity Address；   
> 同理，如果有InitA需要填充，则判断Resolving List是否有匹配的、非0的Peer IRK，如果有，则使用Peer IRK将对端的Identity Address加密为Resolvable Private Address，填充到InitA中。否则，直接填充Identity Address。
>
> 接收数据包时：   
> 如果数据包中的AdvA或者InitA为普通的Identity Address，则直接做后续的处理；   
> 如果它们为Resolvable Private Address，则会遍历Resolving List中所有的“IRK | Identity Address”条目，使用IRK解出Identity Address和条目中的对比，如果匹配，则地址解析成功，可以做进一步处理。如果不匹配，且使能了白名单/LL Privacy策略，则会直接丢弃。

5）需要重点说明的是，Controller和Host之间所有的事件交互（除了Resolving List操作之外），均使用Identity Address。也就是说，设备地址的加密、解密、比对等操作，都是在controller中完成的，对上层实体（HCI之上）是透明的。

## 4. 使用场景说明

结合上面2章的解释，罗列一下LL Privacy策略有关的使用场景（大部分翻译自蓝牙spec）。

#### 4.1 设备处于广播状态（Advertising state）时

由[3]中的介绍可知，处于广播状态的BLE设备，根据需要可发送ADV\_IND、ADV\_DIRECT\_IND、ADV\_NONCONN\_IND和ADV\_SCAN\_IND 4种类型的广播包，也就是说有4种不同的广播状态，它们的LL privacy策略有稍微的不同，下面分别描述。

1）ADV\_IND

设备（Advertiser）发送ADV\_IND时，其PDU（connectable undirected advertising event PDU）有一个AdvA字段，该字段的填充策略为（由controller的LL执行）：

> 检查Resolving List，查看是否存在非0的Local IRK条目，如果有，则使用Local IRK将自己的Identity Address加密为Resolvable Private Addresses，并填充到AdvA中。否则，直接使用Identity Address。

Advertiser收到连接请求时，请求者的地址会包含在PDU的InitA中，该字段的解析策略为（由controller的LL执行）：

> 如果InitA是Resolvable Private Addresses，且当前使能了地址解析功能，LL会遍历Resolving List中所有的“Peer IRK | Peer Device Identity Address | Address Type”条目，使用Peer IRK解析出Identity Address后和Peer Device Identity Address做比对，如果匹配，则解析成功，再基于具体的白名单策略，觉得是否接受连接；
>
> 如果解析不成功，则无法建立连接；
>
> 如果InitA不是Resolvable Private Addresses，则走正常的连接过程。

Advertiser收到扫描请求时，对ScanA的处理策略，和InitA类似。

2）ADV\_DIRECT\_IND

设备（Advertiser）发送ADV\_DIRECT\_IND 时，其PDU（connectable directed advertising event PDU）包含AdvA和InitA两个地址，它们填充策略为（由controller的LL执行）：

> 检查Resolving List，查看是否存在非0的Local IRK条目，如果有，则使用Local IRK将自己的Identity Address加密为Resolvable Private Addresses，并填充到AdvA中。否则，直接使用Identity Address；
>
> 检查Resolving List，查看是否存在非0、和InitA的Identity Address匹配的Peer IRK条目，如果有，则使用Peer IRK将InitA的Identity Address加密为Resolvable Private Addresses，并填充到InitA中。否则，直接使用Identity Address。

Advertiser收到连接请求时，请求者的地址会包含在PDU的InitA中，该字段的解析策略为和上面ADV\_IND类似，不再详细说明。

3）ADV\_NONCONN\_IND and ADV\_SCAN\_IND

这两个状态下，AdvA的填充策略和上面1）和2）一样，不再详细说明。

当Advertiser收到SCAN请求时，对ScanA的处理策略，和1）中InitA类似，不再详细说明。

#### 4.2 设备处于扫描状态（Scanning state）时

处于Scanning状态的设备（Scanner）在接收到Advertiser发送的scannable的广播包时，需要按照4.1中解析InitA的方法，解析广播包中的AdvA，并根据当前的白名单策略，进行过滤。

Scanner发送scan请求时，需要指定ScanA和AdvA两个地址。其实ScanA的填充策略和4.1中的AdvA类似，不再详细说明。而AdvA，需要和接收到的广播包的AdvA完全一样，不能有改动。

#### 4.3 设备处于连接状态（Initiating state）时

处于Initiating状态的设备（Initiator）在接收到Advertising发送的connectable的广播包时，需要按照4.1中解析InitA的方法，解析广播包中的AdvA，并根据当前的白名单策略，进行过滤。

同理，Initiator发送连接请求时，需要指定InitA和AdvA两个地址。其实InitA的填充策略和4.1中的AdvA类似，不再详细说明。而AdvA，需要和接收到的广播包的AdvA完全一样，不能有改动。

最后，Initiator在接收到Advertising发送的directed connectable广播包时，除了要解析AdvA，如果InitA是Resolvable Private Addresses，则需要使用Local IRK解析InitA。

## 5. 和LL Privacy有关的HCI命令

不太想写了，需要了解的直接去掰spec吧。

## 6. 参考文档

[1] [蓝牙协议分析(8)\_BLE安全机制之白名单](/bluetooth/ble_white_list.html)

[2] [蓝牙协议分析(6)\_BLE地址类型](/bluetooth/ble_address_type.html)

[3] [蓝牙协议分析(5)\_BLE广播通信相关的技术分析](/bluetooth/ble_broadcast.html)

原创文章，转发请注明出处。蜗窝科技，[www.wowotech.net](/bluetooth/ble_ll_privacy.html)。
