---
title: "蓝牙协议分析(5)_BLE广播通信相关的技术分析"
date: 2016-05-27T16:15:22+08:00
url: "/bluetooth/ble_broadcast.html"
gid: "303"
emlog_type: "blog"
summary: "大家都知道，相比传统蓝牙，蓝牙低功耗（BLE）最大的突破就是加大了对广播通信（Advertising）的支持和利用。关于广播通信，通过“ 玩转BLE(1)_Eddystone beacon ”和“ 玩转BLE(2)_使用bluepy扫描BLE的广播数据 ”两篇文章的介绍，我们已经有了一个整体的认识。本文将依此为基础，从技术的角度，分析和理解BLE协议中有关广播通信的定义和实现。 注1：之前的蓝牙协"
author: "wowo"
category: "蓝牙"
category_alias: "bluetooth"
tags: ["蓝牙", "BLE", "scan", "advertising", "广播", "discover", "connect"]
views: 100215
comment_count: 57
aliases:
  - "/bluetooth/303.html"
  - "/303.html"
---

#### 1. 前言

大家都知道，相比传统蓝牙，蓝牙低功耗（BLE）最大的突破就是加大了对广播通信（Advertising）的支持和利用。关于广播通信，通过“[玩转BLE(1)\_Eddystone beacon](/bluetooth/eddystone_test.html)”和“[玩转BLE(2)\_使用bluepy扫描BLE的广播数据](/bluetooth/bluepy_scan.html)”两篇文章的介绍，我们已经有了一个整体的认识。本文将依此为基础，从技术的角度，分析和理解BLE协议中有关广播通信的定义和实现。

注1：之前的蓝牙协议分析文章（如“[蓝牙协议分析(3)\_蓝牙低功耗(BLE)协议栈介绍](/bluetooth/ble_stack_overview.html)”），偏向于从横向、从大而全的角度，介绍蓝牙协议，以便让大家有一个整体的认识。而从本文开始，我们会收敛到一个个的功能点上，以功能为出发点，从纵向的角度，游走于蓝牙协议的各个层次中，以加深对蓝牙协议的理解，进而达到融会贯通的目的。

#### 2. 概述

##### 2.1 使用场景

在BLE协议中，广播通信主要有两类使用场景：

1）单一方向的、无连接的数据通信，数据发送者在广播信道上广播数据，数据接收者扫描、接收数据。

2）连接的建立。

后续的分析，将围绕这两个使用场景展开。

##### 2.2 协议层次

在BLE协议中，和广播通信相关的协议层次比较简单，主要包括：

> GAP-------->HCI-------->LL

LL(Link Layer)位于最底层，负责广播通信有关功能的定义和实现，包括物理通道的选择、相关的链路状态的定义、PDU的定义、设备过滤（Device Filtering）机制的实现等。

HCI负责将LL提供的所有功能，以Command/Event的形式抽象出来，供Host使用。

GAP负责从应用程序的角度，抽象并封装LL提供的功能，以便让应用以比较傻瓜的方式进行广播通信。当然，这不是必须的，也就是说，我们可以在没有GAP参与的情况下，进行广播通信。

#### 3. Link Layer

##### 3.1 状态定义

在某一个时刻，参与广播通信的BLE设备，从LL的角度看，可以处于如下三种状态的一种：

> Advertising，数据发送方，周期性的发送广播数据；
>
> Scanning，数据接收方，扫描、接收广播数据；
>
> Initiating，连接发起方，扫描带有“可连接”标志的广播数据，一旦发现，则发起连接请求（都是由Link Layer自动完成，不需要Host软件参与）。

##### 3.2 PDU定义

根据应用场景的不同，处于不同状态的BLE设备，可以发送不同类型的PDU（Packet Data Unit），具体如下。

**3.2.1 PDU格式**

广播通信中，传输的PDU有如下的格式：

|  |  |
| --- | --- |
| Header(16bits) | Payload(长度由Header中的“Length”字段决定) |

Header的格式如下：

|  |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
| PDU Type(4 bits) | RFU(2 bits) | TxAdd(1 bit) | RxAdd(1 bit) | Length(6 bits) | RFU(2 bits) |

> PDU Type，指示PDU的类型，具体可参考后面的介绍。
>
> RFU，reserved for future use。
>
> TxAdd、RxAdd，由具体的PDU Type决定其意义。
>
> Length，PDU的长度，6 bits，有效范围是6~37 octets。

**3.2.2 PDU类型**

|  |  |  |  |
| --- | --- | --- | --- |
| 状**态** | **PDU类型** | **PDU格式** | **说明** |
| Advertising | ADV\_IND | AdvA(6 octets)    AdvData(0~31 octets) | connectable undirected advertising event，用于常规的广播，可携带不超过31bytes的广播数据，可被连接，可被扫描：    AdvA，6bytes的广播者地址，并由PDU Header的TxAdd bit决定地址的类型（0 public，1 random）；    AdvData，广播数据。 |
|  | ADV\_DIRECT\_IND | AdvA(6 octets)    InitA(6 octets) | connectable directed advertising event，专门用于点对点连接，且已经知道双方的蓝牙地址，不可携带广播数据，可被指定的设备连接，不可被扫描：    AdvA，6bytes的广播者地址，并由PDU Header的TxAdd bit决定地址的类型（0 public，1 random）；    InitA，6bytes的接收者（也是连接发起者）地址，并由PDU Header的RxAdd bit决定地址的类型（0 public，1 random）。 |
|  | ADV\_NONCONN\_IND | AdvA(6 octets)    AdvData(0~31 octets) | 和ADV\_IND类似，但不可以被连接，不可以被扫描。 |
|  | ADV\_SCAN\_IND | AdvA(6 octets)    AdvData(0~31 octets) | 和ADV\_IND类似，但不可以被连接，可以被扫描。 |
| Scanning | SCAN\_REQ | ScanA(6 octets)    AdvA(6 octets) | 当接收到ADV\_IND或者ADV\_SCAN\_IND类型的广播数据的时候，可以通过该PDU，请求广播者广播更多的信息：    ScanA，6bytes的本机地址，并由PDU Header的TxAdd bit决定地址的类型（0 public，1 random）；    AdvA，6bytes的广播者地址，并由PDU Header的RxAdd bit决定地址的类型（0 public，1 random）。 |
|  | SCAN\_RSP | AdvA(6 octets)    ScanRspData(0~31 octets) | 广播者收到SCAN\_REQ请求后，通过该PDU响应，把更多的数据传送给接受者。    AdvA，6bytes的广播者地址，并由PDU Header的TxAdd bit决定地址的类型（0 public，1 random）；    ScanRspData，scan的应答数据。 |
| Initiating | CONNECT\_REQ | InitA (6 octets)    AdvA (6 octets)    LLData (22 octets) | 当接收到ADV\_IND或者ADV\_DIRECT\_IND类型的广播数据的时候，可以通过该PDU，请求和对方建立连接：    InitA，6bytes的本机地址，并由PDU Header的TxAdd bit决定地址的类型（0 public，1 random）；    AdvA，6bytes的广播者地址，并由PDU Header的RxAdd bit决定地址的类型（0 public，1 random）；    LLData，BLE连接有关的参数信息，具体请参考后续文章的介绍。 |

**3.2.3 总结**

有关广播通信的PDU类型，总结如下：

> 1）如果只需要定时传输一些简单的数据（如某一个温度节点的温度信息），后续不需要建立连接，则可以使用ADV\_NONCONN\_IND。广播者只需要周期性的广播该类型的PDU即可，接收者按照自己的策略扫描、接收，二者不需要任何额外的数据交互。
>
> 2）如果除了广播数据之外，还有一些额外的数据需要传输，由于种种原因，如广播数据的长度限制、私密要求等，可以使用ADV\_SCAN\_IND。广播者在周期性广播的同时，会监听SCAN\_REQ请求。接收者在接收到广播数据之后，可以通过SCAN\_REQ PDU，请求更多的数据。
>
> 3）如果后续需要建立点对点的连接，则可使用ADV\_IND。广播者在周期性广播的同时，会监听CONNECT\_REQ请求。接收者在接收到广播数据之后，可以通过CONNECT\_REQ PDU，请求建立连接。
>
> 4）通过ADV\_IND/CONNECT\_REQ的组合建立连接，花费的时间比较长。如果双方不关心广播数据，而只是想快速建立连接，恰好如果连接发起者又知道对方（广播者）的蓝牙地址（如通过扫码的方式获取），则可以通过ADV\_DIRECT\_IND/CONNECT\_REQ的方式。

##### 3.3 Advertising状态

**3.3.1 Advertising Channel的选择**

我们在“[蓝牙协议分析(3)\_蓝牙低功耗(BLE)协议栈介绍](/bluetooth/ble_stack_overview.html)”中提到过，BLE可以使用40个Physical Channel中的3个作为广播通信的物理信道，综合各种因素（抗干扰等），最终选取了如下三个：

|  |  |  |
| --- | --- | --- |
| RF Channel | RF Center Frequency | Advertising Channel Index |
| 0 | 2402MHz | 37 |
| 12 | 2426MHz | 38 |
| 39 | 2480MHz | 39 |

与此同时，Link Layer允许Host在这这三个物理信道中，任意选取一个或者多个，用于广播。Link Layer将相同的广播数据，在每一个被中的Channel中，发送一次。

**3.3.2 Advertising Event的定义**

由前面的描述可知，BLE广播的过程中，根据使用场景的不同，会在被使用的每一个物理Channel上，发送（或接收）多种类型的PDU。基于此，BLE协议提出了“Advertising Event”的概念，即：

> Advertising Event是在所有被使用的物理Channel上，发送的Advertising PDU的组合。

如果觉得有点绕口的话，我们再用用通俗的语言解释：

> BLE设备处于Advertising状态的目的，就是要广播数据。并且，根据应用场景的不同，可广播4种类型的数据。
>
> 另外，BLE设备最多可以在3个物理Channel上广播数据。也就是说，同一个数据（4中类型中的一种），需要在多个Channel上依次广播。因此，这样依次在多个Channel上广播的过程，就叫做一个Advertising Event。
>
> 与此同时，有些广播（如可连接、可扫描）发送出去之后，允许接收端在对应的Channel上，回应一些请求（如连接请求、扫描请求）。并且，广播者接收到扫描请求后，需要在同样的Channel上回应。这些过程，也会计算在一个Advertising Event中。

以上可参考“BLUETOOTH SPECIFICATION Version 4.2 [Vol 6, Part B]” 4.4.2章节中的有关图示，本文不再详细介绍了。

**3.3.3 Advertising Event Type**

根据应用场景的不同（基本对应3.2.3小节所总结的4中场景），BLE协议也规定了不同类型的Advertising Event，包括：

> Connectable Undirected Event；
>
> Connectable Directed Event（包括Low Duty Cycle和High Duty Cycle）；
>
> Scannable Undirected Event；
>
> Non-connectable Undirected Event。

不同的Advertising Event，所对应的Advertising参数（如周期等）也不同，具体请参考后面的描述。

**3.3.4 Advertising周期的设定**

对BLE广播通信来说，Advertising的周期是一个比较重要的参数，因为它关系到系统的功耗和通信的效率，因此需要根据使用场景，小心设定。

对除High Duty Cycle Connectable Directed Event之外的其它Advertising Event来说，Advertising周期主要由advInterval、advDelay两个参数决定的，如下图所示：

[![Advertising events perturbed in time using advDelay](/content/uploadfile/201605/262a13538758bf5601c3ae87ab33532420160527081520.gif "Advertising events perturbed in time using advDelay")](/content/uploadfile/201605/7e1aac0ffc2d4c2b67558904d10b694620160527081520.gif)

图片1 Advertising周期

> 其中，advInterval是一个可由Host设定的参数：对于Scannable Undirected和Non-connectable Undirected两种Advertising Event，该值不能小于100ms（从功耗的角度考虑的，也决定了广播数据的速率）；对于Connectable Undirected和Low Duty Cycle Connectable Directed两种Advertising Event，该值不能小于20ms（建立连接嘛，要快点）。
>
> advDelay则是一个0~10ms的伪随机数。

High Duty Cycle Connectable Directed Event则是一个比较狂暴的家伙，其Advertising周期不受上面的参数控制，可以小到3.75ms。不过呢，BLE协议也同时规定：Link Layer必须在1.28s内退出这种狂暴状态。名副其实的短跑冠军啊！

注2：我们可以从上面的时间信息推断出，BLE协议对广播通信的期望，是非常明确的----不在乎速率、只在乎功耗。一般的广播通信（不以连接为目的），最高速率也就是31byte / 100ms = 2.48kbps。如果再算上可扫描的那段数据，也就是double，4.96kbps。

注3：对于连接来说，如果事先不知道连接发起者的设备地址，则最快的连接速度可能是20ms。如果事先知道地址，使用High Duty Cycle Connectable Directed Event的话，则可能在3.75ms内建立连接。由此可以看出，BLE的连接建立时间，比传统蓝牙少了很多，这也是BLE设备之间不需要保持连接的原因。

##### 3.4 Scanning状态

**3.4.1 scanWindow和scanInterval**

Scanning状态扫描、接收广播数据的状态，该状态的扫描行为是由scanWindow和scanInterval两个参数觉得的。scanWindow指示一次扫描的时间（即可以理解为RF RX打开的时间），scanInterval指示两次扫描之间的间隔。如果这两个参数的值相同，表示连续不停地扫描。

BLE协议规定，scanWindow和scanInterval最大不能超过10.24s，并且scanWindow不能大于scanInterval。

**3.4.2 Passive Scanning和Active Scanning**

Passive Scanning之所以称作消极的（Passive），是因为这种扫描模式下，BLE设备只听不问，也就是说，只接收ADV\_DIRECT\_IND、ADV\_IND、ADV\_SCAN\_IND、ADV\_NONCONN\_IND等类型的PDU，并不发送SCAN\_REQ。

而Active Scanning，不只认真听讲，还勤于发问（SCAN\_REQ），并接收后续的 SCAN\_RSP。

这两种Scanning的最终结果，就是把接收到的数据（包括Advertiser地址、Advertiser数据等），反馈给Host。

##### 3.5 Initiating状态

Initiating状态和Scanning状态类似，只不过它的关注点不一样：它不关心广播数据，只关心ADV\_DIRECT\_IND和ADV\_IND两类消息，并在符合条件的时候，发出CONNECT\_REQ，请求建立连接。

##### 3.6 设备过滤机制

从前面的描述可知，BLE的广播功能，除了速率上面不给力之外，还是比较爽的。但有一个问题，需要引起我们的重视：

> 如果周围有很多的BLE设备在广播，对Scanner来说，它的Controller会扫描到很多广播数据，如果这些数据都上报给Host（甚至用户）的话，估计Host（或者用户）会疯掉。换句话说，垃圾信息太多了，我只想看、只想听我感兴趣的？肿么办？

没关系，有办法，基于白名单（White List）机制的设备过滤机制登场了。

**3.6.1 白名单（White List）**

每一个BLE的Controller，可以保存一个设备列表，通过该列表，可以实现设备过滤的功能。这个列表就称作白名单（White List），保存了一些BLE设备地址。

白名单的大小由Controller自行觉得，并在reset的时候为空，后续可以由Host通过HCI接口配置。基于白名单，Link Layer可实现多种设备过滤的策略，包括：

> Advertising Filter Policy；
>
> Scanner Filter Policy；
>
> Initiator Filter Policy。

具体可参考下面的描述。

**3.6.2 Advertising Filter Policy**

Advertising Filter Policy定义了Advertiser（处于Advertising状态）的Link Layer怎么处理SCAN\_REQ（扫描请求）和CONNECT\_REQ（连接请求），包括如下策略（Host可以根据实际情况配置，同一时刻只能配置一种）：

> Link Layer只接受位于白名单中的设备的扫描和连接请求（最严格）；
>
> Link Layer可以接受任何设备的扫描和连接请求（最不严格，Controller reset后的默认状态）；
>
> Link Layer可以接受任何设备的扫描请求，但只接受位于白名单中的设备的连接请求；
>
> Link Layer可以接受任何设备的连接请求，但只接受位于白名单中的设备的扫描请求。

**3.6.3 Scanner Filter Policy**

Scanner Filter Policy定一个Scanner（处于Scanning状态）的Link Layer怎么处理广播数据，包括如下策略：

> Link Layer只处理位于白名单中的设备的广播数据，并且忽略没有包括自身地址的connectable Directed advertising packet；
>
> Link Layer处理所有设备的广播数据，并且忽略没有包括自身地址的connectable Directed advertising packet（Controller reset后的默认状态）。

另外，如果设备支持“Extended Scanner Filter”策略，则可以同时支持如下的策略：

> Link Layer只处理位于白名单中的设备的广播数据，并且不能忽略InitA地址为“resolvable private address”的connectable Directed advertising packet；
>
> Link Layer处理所有设备的广播数据，并且不能忽略InitA地址为“resolvable private address”的connectable Directed advertising packet。

注4：有关resolvable private address，我们会在其它文章中介绍。

**3.6.4 Initiator Filter Policy**

Initiator Filter Policy定一个Initiator （处于Initiating状态）的Link Layer怎么处理可连接的广播数据，包括如下策略：

> Link Layer只处理位于白名单中的设备发送的可连接的广播包，并在收到的时候发起连接请求；
>
> 忽略白名单，Link Layer处理由Host指定的设备所发送的可连接的广播包，并在收到的时候发起连接请求。

#### 4. HCI

Link Layer中广播通信有关的功能介绍完之后，HCI这一层就简单了，因为它仅仅是将Link Layer所提供的功能封装成特定的Command和Event，没有任何逻辑可言。

开始之前，我们先回忆一下“[玩转BLE(1)\_Eddystone beacon](/bluetooth/eddystone_test.html)”中给出的有关hcitool的例子：

> # enable BLE advertising   
> hcitool -i hci0 cmd 0x08 0x000A 01
>
> # set advertising data to Eddystone UUID   
> hcitool -i hci0 cmd 0x08 0x0008 1e 02 01 06 03 03 aa fe 17 16 aa fe 00 -10 00 01 02 03 04 05 06 07 08 09 0a 0b 0e 0f 00 00 00 00

终于可以揭开它们的真面目了！

##### 4.1 HCI Command/Event格式

先简单介绍一下HCI Command和Event的格式（具体可参考“BLUETOOTH SPECIFICATION Version 4.2 [Vol 2, Part E]” 5.4章节）。

HCI Command的格式如下：

|  |  |  |  |  |
| --- | --- | --- | --- | --- |
| OCF(10bit) +OGF(6bit) | Parameter Total Length | Parameter1 | Parameter2 | … |

> OCF和OGF共同组成16bit的操作码（OpCode）；
>
> OGF是OpCode Group Field的简称，长度是6 bits，代码该HCI命令所属的group，对应上面HCI命令中的0x08；
>
> OCF是OpCode Command Field的简称，代码特定的HCI命令，对应上面HCI命令中的0x000A/0x0008；
>
> Parameter Total Length，指示该Command所有参数的长度；
>
> Parameter1、Parameter2、等等，16 bits的参数，由具体的Command决定。

注5：这里所描述的Command格式，我们只需要关注OGF、OCF和Parameter即可，因为后续我们主要使用“hcitool cmd”命令进行演示，而hcitool已经帮我们封装了。

HCI Event的格式如下：

|  |  |  |  |  |
| --- | --- | --- | --- | --- |
| Event code(8 bits) | Parameter Total Length | Parameter1 | Parameter2 | … |

> 具体意义不再详细描述。

##### 4.2 广播通信相关的HCI Command介绍

本节简单介绍一下和广播通信有关的HCI Command，更为详细的信息，可参考“BLUETOOTH SPECIFICATION Version 4.2 [Vol 2, Part E]” 7.8小节的介绍。

注6：所有BLE相关的HCI Command的OGF都是0x08。

**4.2.1 Advertising状态有关的命令**

1）HCI\_LE\_Set\_Advertising\_Parameters

> 设置广播参数，包括Advertising Interval、Advertising Type、本机的地址类型、对端设备的地址类型和地址、所使用的物理Channel的map、Advertising Filter Policy等。

2）HCI\_LE\_Set\_Advertising\_Data

> 设置广播数据，OCF为0x0008，Command参数的格式如下：
>
> Advertising Data Length(8 bits)， Advertising Data
>
> 以上面的例子为例，hcitool -i hci0 cmd 0x080x00081e02 01 06 03 03 aa fe 17 16 aa fe 00 -10 00 01 02 03 04 05 06 07 08 09 0a 0b 0e 0f 00 00 00 00
>
> 不同的颜色，依次代表OGF、OCF、Advertising Data Length、Advertising Data。

3）HCI\_LE\_Set\_Scan\_Response\_Data

> 设置Scan请求时的应答数据，OCF为0x0009，格式和HCI\_LE\_Set\_Advertising\_Data一模一样。

4）HCI\_LE\_Set\_Advertise\_Enable

> 控制Advertising的使能与否，ICF为0x000a，命令参数包括一个8 bits的“Advertising Enable”，如下：
>
> hcitool -i hci0 cmd 0x08 0x000A 01

**4.2.2 Scanning状态有关的命令**

1）HCI\_LE\_Set\_Scan\_Parameters

> 设置scan参数，包括Scan Type、Scan Interval、Scan Window、本机的地址类型、Scanning Filter Policy等。

2）HCI\_LE\_Set\_Scan\_Enable

> Scan动作的开关，其数据格式和HCI\_LE\_Set\_Advertise\_Enable一致。

**4.2.3 Initiating状态有关的命令**

1）HCI\_LE\_Create\_Connection

> 建立连接，可指定Sca Interval、Scan Window、Initiator Filter Policy、Peer Address Type、Peer Address、Own Address Type等Initiating有关的参数，也可以指定连接相关的参数（这里暂不说明）。

2）HCI\_LE\_Create\_Connection\_Cancel

> 取消连接。

**4.2.4 白名单（White List）有关的命令**

包括：

> HCI\_LE\_Read\_White\_List\_Size，获取BLE Controller的白名单大小；
>
> HCI\_LE\_Clear\_White\_List，清空白名单；
>
> HCI\_LE\_Add\_Device\_To\_White\_List，将设备添加到白名单；
>
> HCI\_LE\_Remove\_Device\_From\_White\_List，将设备从白名单移除；

#### 5. GAP

对于广播通信而言，GAP主要完成两个事情：

> 1）将Link Layer的“协议语言”，如Advertising、Scannin、Initiating等，转换为更为直观的“人类语言”（当然，要进行一些封装）。
>
> 2）为广播数据和扫描应答数据，定义一些统一的、规范的格式，以达到互联互通的目的。

下面将分别介绍这两个事情。

##### 5.1 GAP模式定义

上面介绍Link Layer的时候，相信大家对那些术语有些晕晕的了，不过还好，回到Host端之后，熟悉的蓝牙术语又回来了。GAP从用户功能的角度，将Link Layer的各种状态进行了一次映射，抽象出来了如下的4种模式（只有两种和广播通信有关，我们会重点介绍）：

1）Broadcast mode and observation procedure

广播模式，以及对应的解析过程。处于广播模式的设备，可发送non-connectable undirected或者scannable undirected两类advertising events。当然具备相应解析能力的设备，可接收这两类events。

于此同时，GAP为该模式下的设备定义了两个角色（GAP role）：Broadcaster和Observer，Broadcaster必须具有“Broadcast mode”能力，Observer必须具有“observation procedure”能力。

注7：大家可能会觉得这些术语有些混乱，理解它们，需要把握一点：GAP是一个profile，profile的首要目的是互联互通，因此它最擅长的就是角色（role，Broadcaster和Observer）和能力（Broadcast mode 和observation procedure）的定义。任何支持GAP的设备，都要声明自己支持哪些角色，而profile就要规定，哪种角色必须必备哪种能力。后面其它模式的理解，也遵循该原则。

2）Discovery modes and procedures

发现模式，以及对应的发现过程，用于设备的发现（和传统蓝牙保持一致了）。

GAP为该模式下的设备定义了两个角色：Peripheral和Central，Peripheral是被发现的设备，Central是主动发现别人的设备。同时，GAP定义了6种和发现有关的能力（不同角色的设备可以根据协议的规定，选择具备哪些能力）：

> Non-Discoverable mode，不可被发现，设备不会广播任何数据；
>
> Limited Discoverable mode，可被发现（有限的），设备可发送non-connectable、scannable undirected或者connectable undirected三类advertising events。“有限”的意思是，设备只会在有限的一段时间内，广播数据；
>
> General Discoverable mode，可被发现（通用的），和上面的模式类似，不过可以广播很长一段时间；
>
> Limited Discovery procedure ，可执行有限的发现操作，可发现处于“Limited Discoverable mode”的设备；
>
> General Discovery procedure ，可执行通用的发现操作，可发现处于“Limited Discoverable mode”和“General Discoverable mode”的设备；
>
> Name Discovery procedure，可进行Name的发现操作。如果通过Scanning操作（包括Passive和Active两种）没有得到广播设备的名称，使用该过程，可以在建立连接之后，再获取对方的名字。

3）Connection modes and procedures

连接模式，已经对应的连接过程，用于设备的连接（和传统蓝牙保持一致）。

所有四种角色的设备，Peripheral、Central、Broadcaster和Observer，都有可能涉及连接有关的模式，具体可参考蓝牙spec中有关的定义。

连接有关的模式包括：

> Non-connectable mode，不可被连接的模式，设备可发送non-connectable undirected或者scannable undirected两类advertising events；
>
> Directed connectable mode，可被指定的设备连接，设备只发送Connectable Directed advertising events；
>
> Undirected connectable mode，可被连接（不指定设备），设备只发送Connectable undirected advertising events；
>
> Auto connection establishment procedure，可自动连接处于directed connectable mode或者undirected connectable mode的设备。自动是指Controller自动，Host只需要发号施令即可；
>
> General connection establishment procedure，通用的连接过程，Host需要参与。
>
> Selective connection establishment procedure，建立连接的时候，Host可以指定一些连接参数，后续文章再详细分析；
>
> Direct connection establishment procedure，结合设备过滤机制，只连接特定的设备；
>
> Connection parameter update procedure，连接参数的更新，后续在分析；
>
> Terminate connection procedure，连接断开的过程。

##### 5.2 广播数据格式

为了互联互通的目的，BLE协议为31个bytes的广播数据和扫描应答数据，定义了详细的格式，如下：

[![Advertising and Scan Response data format](/content/uploadfile/201605/e7aacb93eaf8dbbf8b62285018567e3e20160527081521.gif "Advertising and Scan Response data format")](/content/uploadfile/201605/6405e58809c2d2dacbc6bfc0f61006e120160527081520.gif)

图片2：广播数据和扫描应答数据的格式

> 首先，广播数据（或者扫描应答数据）由一个一个的AD Structure组成，对于未满31bytes的其它数据，则填充为0；
>
> 每个AD Structure由两部分组成：1byte的长度信息（Data的长度），和剩余的Data信息；
>
> Data信息又由两部分组成：AD Type（长度不定）指示该AD Structure的类型，以及具体的AD Data。

如果仅仅是这些，显示不出蓝牙组织的强大。最关键的还是AD Type，BLE协议根据实际的应用场景，定义了各种各样的AD type，以及相应的数据格式，例如

> Service UUID，指示本设备支持哪些profile；
>
> Local Name，指示本设备的名称；
>
> Flags，指示本设备支持Limited Discoverable Mode/General Discoverable Mode的能力，以及BLE、BR/EDR的支持能力；
>
> 等等；

注8：AD Type的定义，可参考“[https://www.bluetooth.com/specifications/assigned-numbers/generic-access-profile](https://www.bluetooth.com/specifications/assigned-numbers/generic-access-profile "https://www.bluetooth.com/specifications/assigned-numbers/generic-access-profile")”。

注9：AD Data格式的定义，可参考“CSS([Core Specification Supplement)](https://www.bluetooth.org/DocMan/handlers/DownloadDoc.ashx?doc_id=302735&_ga=1.116178308.327753755.1464334668) ”文档。

最后，结合上面的hcitool cmd的例子，加深一下理解：

02 01 06 03 03 aa fe 17 16 aa fe 00 -10 00 01 02 03 04 05 06 07 08 09 0a 0b 0e 0f 00 00 00 00

> 02 01 06，是一个AD Structure：Data的长度是02；Data是01 06；AD Type是01（Flags）；AD Data是06，表明支持General Discoverable Mode、不支持BR/EDR。
>
> 03 03 aa fe，是一个AD Structure：Data的长度是03；Data是03 aa fe；AD Type是03（16 bits的Service UUID）；AD Data是aa fe，是Eddystone profile的Service UUID。
>
> 17 16 aa fe 00 -10 00 01 02 03 04 05 06 07 08 09 0a 0b 0e 0f 00 00 00 00，是一个AD Structure：Data的长度是17（23bytes）；Data是16 aa fe 00 -10 00 01 02 03 04 05 06 07 08 09 0a 0b 0e 0f 00 00 00 00；AD Type是16（Service Data）；AD Data是aa fe 00 -10 00 01 02 03 04 05 06 07 08 09 0a 0b 0e 0f 00 00 00 00，是Eddystone profile具体的Service Data（可参考“[https://github.com/google/eddystone/blob/master/protocol-specification.md](https://github.com/google/eddystone/blob/master/protocol-specification.md "https://github.com/google/eddystone/blob/master/protocol-specification.md")”中相关的介绍）。

#### 6. 总结

啰哩啰唆记了了这么多，恐怕大家不容易看懂，就当自己的一个学习笔记吧，以后遇到相关的问题，来这篇文章查查应该就可以了。

原创文章，转发请注明出处。蜗窝科技，[www.wowotech.net](/bluetooth/ble_broadcast.html)。
