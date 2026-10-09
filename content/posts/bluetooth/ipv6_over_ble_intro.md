---
title: "蓝牙协议分析(4)_IPv6 Over BLE介绍"
date: 2016-04-09T16:44:31+08:00
url: "/bluetooth/ipv6_over_ble_intro.html"
gid: "278"
emlog_type: "blog"
summary: "蓝牙是个奇葩的家伙：它总是以后来者的身份出现，很喜欢打仗，而且还不落下风（有点像某讯的风格）。90年代末期和Wi-Fi的无线标准之争如此，当前和802.15.4系（ZigBee、RF4CE、Thread等）的IoT之争，也如此。 90年代末期，蓝牙刚出道的时候，就曾叫嚣着把Wi-Fi（802.11）从地球上抹去。反过来，1999年Wi-Fi 802.11b标准发布后，也宣称会把蓝牙干掉。最终，二者"
author: "wowo"
category: "蓝牙"
category_alias: "bluetooth"
tags: ["BLE", "ipv6", "ipss", "ipsp"]
views: 32262
comment_count: 5
aliases:
  - "/bluetooth/278.html"
  - "/278.html"
---

#### 1. 前言

蓝牙是个奇葩的家伙：它总是以后来者的身份出现，很喜欢打仗，而且还不落下风（有点像某讯的风格）。90年代末期和Wi-Fi的无线标准之争如此，当前和802.15.4系（ZigBee、RF4CE、Thread等）的IoT之争，也如此。

> 90年代末期，蓝牙刚出道的时候，就曾叫嚣着把Wi-Fi（802.11）从地球上抹去。反过来，1999年Wi-Fi 802.11b标准发布后，也宣称会把蓝牙干掉。最终，二者划江而治，瓜分了天下，Wi-Fi占据了家庭和办公室中的电脑网络，而蓝牙成为了广受欢迎的电脑和外设之间的连通性工具。
>
> 与此同时，在IoT的战场上，以ZigBee（2001年）为代表的802.15.4技术，苦心经营近15年，依旧不愠不火、默默无闻，而蓝牙BLE技术问世（2010年）至今，短短5年左右的时间，已经红遍大江南北，装机量爆棚。于是，硝烟再起。

标准之争，不是本文的议题，我们要思考的问题是：蓝牙有何长处，可以支撑它四处征战？答案是“灵活性”。本文将以用于支持IPv6的IPSP（Internet Protocol Service Profile）为例，说明这个特性。

#### 2. IPSP（Internet Protocol Service Profile）

我们知道，ZigBee等基于802.15.4标准衍生出的无线标准，有4大杀手锏：低功耗、低成本、IP组网（基于6LoWPAN）和自组网（Mesh network）。蓝牙在2010年推出Bluetooth4.0（BLE）之后，低功耗和低成本方面，已经旗鼓相当了。那IP组网和自组网呢？

抛开自组网技术不谈（Bluetooth® Smart Mesh工作组已经成立，标准草稿已经讨论到第7版，今年有望发布），先看看在BLE的基础上，增加IPv6的支持，需要新增多少工作量。

> 如果我告诉你，仅需不超过5页的规范文档、不超过50行的代码，你相信吗？

蓝牙技术联盟（Bluetooth SIG）为支持基于BLE的IPv6，仅仅做了一件事情：在Bluetooth4.1推出之后，发布了一份总页数为14页、有效内容不足5页的Profile规范----Internet Protocol Support Profile[1]，用于支持Internet Protocol（IPv6）。该Profile在BLE协议栈中的定义如下：

[![IPSP](/content/uploadfile/201604/fccd2ff75938da708dc76ba2bb00743f20160409084430.gif "IPSP")](/content/uploadfile/201604/3f644cc7910facb4628afacf72f7b83320160409084429.gif)

图片1 IPSP协议栈

看似复杂，但仅仅左上角那个小小的红色block（IPSS）属于新增内容，具体如下。

##### 2.1 IPSP profile

IPSP是Internet Protocol Support Profile的缩写，它是一个蓝牙profile，规定了“IPv6 over BLE”这样一个应用场景，要怎么实现。主要包括：

> 1）定义两个角色，IPSP Node和IPSP Router。IPSP Router是用来转发IPv6 packet的设备，IPSP Node只能产生或者消费IPv6 packet。如果某一个Router需要连接其它Router，它可以同时实现Node和Router两种角色。
>
> 2）Node需要提供一个用于服务发现（Service discovery）的功能，以便让Router发现它。由“[蓝牙协议分析(3)\_蓝牙低功耗(BLE)协议栈介绍](/bluetooth/ble_stack_overview.html)”中的描述可知，BLE使用GATT作为服务发现。因此，Node基于GATT，提供了IPSS（Internet Protocol Support Service），用于服务发现。
>
> 3）IPv6 packets在Node和Router之间通过面向连接的L2CAP传输，并使用LE\_PSM\_IPSP（0x0023）作为协议识别码（需要在连接建立的时候提供）[3]，同时规定MTU为1280。
>
> 4）在L2CAP之上，依次是6LoWPAN、IPv6、UDP、TCP等网络协议栈，不过已经和蓝牙无关了。

##### 2.2 IPSS service

IPSS（Internet Protocol Support Service）提供了一个名称为IP Support Service UUID（0x1820[6]）的GATT service[5]，用于服务发现。

##### 2.3 6LoWPAN、IPv6、UDP、TCP等网络协议栈

6LoWPAN是IPv6 over Low power Wireless Personal Area Networks的缩写，是为了在802.15.4网络上传输IPv6 packet而提出的一个标准，包括了帧格式的定义、地址的自动配置、IP header的压缩算法等。

IPv6、UDP、TCP等都是标准协议，就不多说了。

#### 3. IETF RFC7668[2]

IPSP规范发布之后，IETF（Internet Engineering Task Force，互联网工程任务组）便发布了名称为“IPv6 over BLUETOOTH(R) Low Energy”的RFC7668标准[2]，该标准详细规定了基于蓝牙BLE的IPv6组网方式，以及一些实现细节。

下面是摘录的两种组网方式，可以看出，已经和传统的IP网络没有什么区别了：

> ```
>                                              /
>             .---------------.               /
>            /           6LN   \             /
>           /               \   \           /
>          |                 \   |         /
>          | 6LN -----------   6LBR ----- |  Internet
>          |     <--link-->  /   |         \
>           \               /   /           \
>            \           6LN   /             \
>             '---------------'               \
>                                              \
> 
>           <------ subnet="" -----=""><-- ipv6="" connection="" --="">
>                                       to Internet
> 
>          Figure 4: Bluetooth LE Network Connected to the Internet
> ```
>
> ```
>                     .-------------------.
>                    /                     \
>                   /     6LN      6LN      \
>                  /        \      /         \
>                 |          \    /           |
>                 |   6LN --- 6LBR --- 6LN    |
>                 |          /    \           |
>                  \        /      \         /
>                   \     6LN      6LN      /
>                    \                     /
>                     '-------------------'
>                 <--------- subnet="" ----------="">
> 
>               Figure 5: Isolated Bluetooth LE Network
> ```

注：6LN是6LoWPAN Node缩写，对应IPSP中的IPSP Node，6LBR是6LoWPAN Board Router的缩写，对应IPSP中的IPSP Router。

#### 4. 参考文档

[1] IPSP SPEC, [1.0](https://www.bluetooth.org/docman/handlers/DownloadDoc.ashx?doc_id=296307 "1.0"), [https://www.bluetooth.org/docman/handlers/DownloadDoc.ashx?doc\_id=296307](https://www.bluetooth.org/docman/handlers/DownloadDoc.ashx?doc_id=296307 "https://www.bluetooth.org/docman/handlers/DownloadDoc.ashx?doc_id=296307")

[2] IETF RFC7668, IPv6 over BLUETOOTH(R) Low Energy, [https://datatracker.ietf.org/doc/rfc7668/?include\_text=1](https://datatracker.ietf.org/doc/rfc7668/?include_text=1 "https://datatracker.ietf.org/doc/rfc7668/?include_text=1")

[3] LE\_PSM\_IPSP, [https://www.bluetooth.com/specifications/assigned-numbers/logical-link-control](https://www.bluetooth.com/specifications/assigned-numbers/logical-link-control "https://www.bluetooth.com/specifications/assigned-numbers/logical-link-control")

[4] [http://embedded-computing.com/articles/bluetooth-smart-and-zigbee-if-you-cant-beat-them-join-them/](http://embedded-computing.com/articles/bluetooth-smart-and-zigbee-if-you-cant-beat-them-join-them/ "read:http://embedded-computing.com/articles/bluetooth-smart-and-zigbee-if-you-cant-beat-them-join-them/")

[5] [蓝牙协议分析(3)\_蓝牙低功耗(BLE)协议栈介绍](/bluetooth/ble_stack_overview.html)

[6] [https://developer.bluetooth.org/gatt/services/Pages/ServicesHome.aspx](https://developer.bluetooth.org/gatt/services/Pages/ServicesHome.aspx "https://developer.bluetooth.org/gatt/services/Pages/ServicesHome.aspx")

[7] IETF RFC4944, [https://tools.ietf.org/html/rfc4944](https://tools.ietf.org/html/rfc4944 "https://tools.ietf.org/html/rfc4944")

原创文章，转发请注明出处。蜗窝科技，[www.wowotech.net](/bluetooth/ipv6_over_ble_intro.html)。
