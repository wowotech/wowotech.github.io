---
title: "蓝牙协议分析(3)_蓝牙低功耗(BLE)协议栈介绍"
date: 2016-03-12T22:32:44+08:00
url: "/bluetooth/ble_stack_overview.html"
gid: "271"
emlog_type: "blog"
summary: "\r\n\t通过“蓝牙协议分析(2)_协议架构”的介绍，大家对蓝牙协议栈应该有了简单的了解，但是，肯定还有“似懂非懂、欲说还休”的感觉。有这种感觉太正常了，毕竟蓝牙协议是一个历史悠久又比较庞大的协议，没那么容易理解。\r\n\r\n\r\n\t因此，本文将换个视角，从协议栈设计者的角度，思考如下问题：\r\n\r\n\r\n\t\r\n\t\t为什么会有蓝牙协议栈（Why）？\r\n\t\r\n\t\r\n\t\t怎样实现蓝牙协议栈（How）？\r\n\t\r\n\t\r"
author: "wowo"
category: "蓝牙"
category_alias: "bluetooth"
tags: ["Bluetooth", "BLE", "l2cap", "gap", "蓝牙低功耗", "att", "gatt"]
views: 103400
comment_count: 51
aliases:
  - "/bluetooth/271.html"
  - "/271.html"
---

#### 1. 前言

通过“[蓝牙协议分析(2)\_协议架构](/bluetooth/bt_protocol_arch.html)”的介绍，大家对蓝牙协议栈应该有了简单的了解，但是，肯定还有“似懂非懂、欲说还休”的感觉。有这种感觉太正常了，毕竟蓝牙协议是一个历史悠久又比较庞大的协议，没那么容易理解。

因此，本文将换个视角，从协议栈设计者的角度，思考如下问题：

> 为什么会有蓝牙协议栈（Why）？
>
> 怎样实现蓝牙协议栈（How）？
>
> 蓝牙协议栈的最终样子是什么（What）？

另外，我们知道，当前的蓝牙协议包含BR/EDR、AMP、LE三种技术，为了降低复杂度，本文将focus在现在比较热门的BLE（Bluetooth Low Energy）技术上（物联网嘛！），至于BR/EDR和AMP，触类旁通即可。

#### 2. Why

“Why”要回答的其实是需求问题，对BLE（蓝牙低功耗）来说，其需求包含两个部分：和传统蓝牙重叠的部分；BLE特有的低功耗部分。大致总结如下：

> 基于2.4GHz ISM频段的无线通信；
>
> 通信速率要求不高，但对功耗极为敏感；
>
> 尽量复用已有的BR/EDR技术；
>
> 组网方式自由灵活，既可以使用传统蓝牙所使用的“基于连接的星形网络（由1个master和多个slave组成）”，也可以使用“无连接的网状网络（由多个advertiser和多个scanner组成）；
>
> 参与通信的设备的数量和种类众多，要从应用的角度考虑易于实现、互联互通等特性；
>
> 有强烈的安全（security）需求；
>
> 等等。

#### 3. How和What

“How”要回答的是设计思路，“What”是基于该思路设计出来的最终产品的样子。

按理说，需要先介绍“How”，后介绍所产出的“What”。但以蜗蜗对蓝牙的理解，显然无法抛开“What”单独回答“How”。所以，基于现有的协议框架（What），去理解背后的“How”，才是明智之举。

开始之前，我们先总结一下BLE的协议框架，后面章节会根据该框架，采用自下向上的方法逐层分析介绍。

如下面图片1所示，BLE的协议可分为Bluetooth Application和Bluetooth Core两大部分，而Bluetooth Core又包含BLE Controller和BLE Host两部分（有关概念可参考“[蓝牙协议分析(1)\_基本概念](/bluetooth/bt_overview.html)”）。

[![ble_stack](/content/uploadfile/201603/572c1f6e9ab5a5855251ac38ca3890be20160319143211.gif "ble_stack")](/content/uploadfile/201603/b29fce02b9d5b05c56e72a36d9bd20ba20160319143211.gif)

图片1 BLE协议框架

#### 4. Physical Layer

任何一个通信系统，首先要确定的就是通信介质（物理通道，Physical Channel），BLE也不例外。在BLE协议中，“通信介质”的定义是由Physical Layer（其它通信协议也类似）负责。

Physical Layer是这样描述BLE的通信介质的：

> 由于BLE属于无线通信，则其通信介质是一定频率范围下的频带资源（Frequency Band）；
>
> BLE的市场定位是个体和民用，因此使用免费的ISM频段（频率范围是2.400-2.4835 GHz）；
>
> 为了同时支持多个设备，将整个频带分为40份，每份的带宽为2MHz，称作RF Channel。

经过上面的定义之后，BLE的物理通道已经出来了，即“频点分别是‘f=2402+k\*2 MHz, k=0, … ,39’，带宽为2MHz”的40个RF Channel。

除了物理通道之外，Physical Layer还需要定义RF收发双方的一些其它特性，包括（不影响本文后续的讨论，不用深究）：

> RF发射相关的特性（Transmitter Characteristics），包括发射功率（Transmission power、调制方式（Modulation），高斯频移键控（Gaussian Frequency Shift Keying ，GFSK）、Spurious Emissions、Radio Frequency Tolerance等等。（不影响本文后续的讨论，不用深究）；
>
> RF接收相关的特性（Receiver Characteristics），包括接收灵敏度等。

#### 5. Link Layer

##### 5.1 功能介绍

经过Physical Layer的定义，通信所需的物理通道已经okay了，即40个RF Channel（后面统一使用Physical Channel指代）。此时Link Layer可以粉墨登场了，它主要的功能，就是在这些Physical Channel上收发数据，与此同时，不可避免的需要控制RF收发相关的参数。但仅做这些，还远远不够：

> 首先，Physical Layer仅仅提供了有限的40个Physical Channel，而BLE中参与通信的实体的数量，肯定不是这个数量级。Link Layer需要解决Physical Channel的共享问题；
>
> 其次，通信是两个实体之间的事情，对这两个实体来说，它们希望看到一条为自己独享的传输通道（就是我们所熟悉的逻辑链路，Logical Link）。这也是Link Layer需要解决的；
>
> 再则，Physical Channel是不可靠的，任何数据传输都可能由于干扰等问题二损毁、丢失，这对有些应用来说，是接受不了的。因此Link Layer需要提供校验、重传等机制，确保数据传输的可靠性；
>
> 等等，等等，简直是既当爹又当妈！

##### 5.2 怎么解决Physical Channel的共享问题

BLE系统只有有限的40个Physical Channel，怎么容纳多个通信实体呢？说来也简单，Link Layer将BLE的通信场景分为两类：

1） 数据量比较少、发送不频繁、对时延不是很敏感的场景

例如一个传感器节点（如温度传感器），需要定时（如1s）向处理中心发送传感器数据（如温度）。

针对这种场景，BLE的Link Layer采取了一种比较懒的处理方式----广播通信：

> 从40个Physical Channel中选取3个，作为广播通道（advertising channel）；
>
> 在广播通道上，任何参与者，爱发就发，爱收就收，随便；
>
> 所有参与者，共享同一个逻辑传输通道（广播通道），之间的

当然，这种方法存在很多问题，例如：

> 不可靠，是否会相互干扰？发送是否成功？不知道！接收是否成功？不知道！
>
> 效率不高，如果同一区域有很多节点在广播数据，某一个接收者是不是要接收所有的数据包，不管是不是它关心的？
>
> 安全问题，怎么解决？

确实，问题多多，不过Link Layer定义了一些策略，尽可能的提高了这种通信方式的便利性，后面我们会介绍。至于无法解决的，简单，两种方案：

> a）忍，广播通信需要占用的资源实在太少了，正对物联网中的那些小节点们的胃口啊。
>
> b）使用基于连接的通信方式（就是给你俩建立一个专线），具体可参考下面5.2.2的介绍。

2）数据量较大、发送频率较高、对时延较敏感的场景

BLE的Link Layer会从剩余的37个Physical Channel中，选取一个，为这种场景里面的通信双方建立单独的通道（data channel）。这就是连接（connection）的过程。

同时，为了增加容量，增大抗干扰能力，连接不会长期使用一个固定的Physical Channel，而是在多个Channel（如37个）之间随机但有规律的切换，这就是BLE的跳频（Hopping）技术。

##### 5.3 状态（state）和角色（role）的定义

基于上面5.2小节的思路，BLE协议在Link Layer抽象出5种状态：

注1：从横向看，协议的每个层次（如这里的Link Layer）都可以当做可相互通信的实体。这里的状态，就是指这每一层实体的状态。因此，在协议的多个层次上，都可能有状态定义，甚至名字也一样，我们阅读协议栈的时候，一定要留意，不要被绕晕了。

> • Standby State   
> • Advertising State   
> • Scanning State   
> • Initiating State   
> • Connection State

并以如下的状态机进行切换（设备在同一时刻只能处于这些状态的一种）：

[![ble_ll_state](/content/uploadfile/201603/0b4e534c15ee5ffb7cb0d24c67fa1a0f20160312143237.gif "ble_ll_state")](/content/uploadfile/201603/c4be4be1904050858ccbd82cd118cba920160312143237.gif)

图片2 Link Layer状态机

Standby状态是初始状态，即不发送数据，也不接收数据。根据上层实体的命令（如位于host软件中GAP），可由其它任何一种状态进入，也可以切换到除Connection状态外的任意一种状态。

Advertising状态是可以通过广播通道发送数据的状态，由Standby状态进入。它广播的数据可以由处于Scanning或者Initiating状态的实体接收。上层实体可通过命令将Advertising状态切换回Standby状态。另外，连接成功后，也可切换为Connection状态。

Scanning状态是可以通过广播通道接收数据的状态，由Standby状态进入。根据Advertiser所广播的数据的类型，有些Scanner还可以主动向Advertiser请求一些额外数据。上层实体可通过命令将Scanning状态切换回Standby状态。

Initiating状态和Scanning状态类似，不过是一种特殊的接收状态，由Standby状态进入，只能接收Advertiser广播的connectable的数据，并在接收到数据后，发送连接请求，以便和Advertiser建立连接。当连接成功后，Initiater和对应的Advertiser都会切换到Connection状态。

Connection状态是和某个实体建立了单独通道的状态，在通道建立之后，由Initiating或者Advertising自动切换而来。通道断开后，会重新回到Standby状态。

通道建立后（通常说“已连接”），处于Connection状态的双方，分别有两种角色Master和Slave：

> Initiater方称作Mater；
>
> Advertiser方称作Slave。

##### 5.4 Air Interface Protocol

状态和角色定义完成后，剩下的事情就简单了，主要包括两类：提供某一状态下，和其它实体对应状态之间的数据交换机制；根据上层实体的指令，以及当前的实际情况，负责状态之间的切换。BLE协议中，这些事情是由一个叫做空中接口协议（Air Interface Protocol）的家伙负责，主要思路如下。

###### 5.4.1 定义在Physical Channel上收发的数据包的格式（packet format）

在BLE中，两种类型的Physical Channel（advertising channel和data channel）统一使用一种packet format，如下：

Preamble(1 octet) Access Address(4 octets) PDU(2 to 257 octets) CRC(3 octets)

> 关于packet format，我们可以关注如下内容：
>
> 1）Access Address，用于识别。
>
> 2）PDU，BLE在Link Layer的PDU长度最大为257 octets（不知道octets是神马意思？当做bytes就行了）。这决定了上层实体，如L2CAP、Application等，需要拆分、重组才能支持更大数据量的传输。
>
> 3）Link Layer总packet长度是9~264bytes。

###### 5.4.2 定义不同类型的PDU及其格式

由5.3小节的描述，Link Layer有5种状态，每种状态下所传输数据的功能不尽相同，基于此，Air Interface Protocol定义出如下的PDU类型（这里只简单列举一下，不深入讨论）：

1）Advertising channel中Advertising有关的PDU

> ADV\_IND，Advertiser发送的、可被连接的、无方向的广播数据（connectable undirected advertising event）。
>
> ADV\_DIRECT\_IND，Advertiser发送的、可被连接的、单向广播数据（connectable directed advertising event）。
>
> ADV\_NONCONN\_IND，Advertiser发送的、不可被连接的、无方向的广播数据（non-connectable undirected advertising event）。
>
> ADV\_SCAN\_IND，Advertiser发送的、可接受SCAN\_REQ请求的、无方向的广播数据（scannable undirected advertising event）。

2）Advertising channel中Scanning有关的PDU

> SCAN\_REQ，Scanner发送的、向Advertiser请求额外信息的数据包（一般需要在收到ADV\_SCAN\_IND后才可发送）。
>
> SCAN\_RSP，Advertiser发送的、响应SCAN\_REQ请求的数据包。

3）Advertising channel中Initialing有关的PDU

> CONNECT\_REQ，Initiater发起的、请求建立连接的数据包。

4）Data channel中LL data有关的PDU

> 已连接的双方进行数据通信所用的PDU，有效的payload长度为0~251bytes。

5）Data channel中LL control有关的PDU

> 用于管理、维护、更新已连接的数据通道的PDU，包括：
>
> LL\_CHANNEL\_MAP\_REQ，请求更改所使用的Physical Channel的数据包；
>
> LL\_TERMINATE\_IND，告知对方此次连接即将结束，以及结束的原因；
>
> 等等。

###### 5.4.3 以白名单（White List）的形式定义Link Layer的数据过滤机制

主要针对广播通道，因为随着通信设备的增多，空中的广播数据将会呈几何级的增长，为了避免资源的浪费（特别是BLE Host），有必要在Link Layer过滤掉一些数据包，例如根据蓝牙地址，过滤掉不是给自己的packet。

###### 5.4.4 执行广播通道上实际的packet收发操作

上层软件只需要定义一些参数，例如：

> Advertising State下的Advertising Channel的选择、Advertising的间隔、Advertising PDU的类型等；
>
> Scanning State/Initialing State下的scanWindow、scanInterval等。

Link Layer将会自动发送或者接收数据包。

###### 5.4.5 定义连接建立的方式及过之后的应答、流控等机制

具体不再详细描述。

##### 5.5 Link Layer Control

经过Air Interface Protocol的抽象，BLE实体已经具备广播通信、点对点连接的建立和释放、点对点通信等基本的能力。除此之外，Link Layer又抽象出来一个链路控制协议（Link Layer Control），用于管理、控制两个Link Layer实体之间所建立的这个Connection，主要功能包括：

> 更新Connection相关的参数，如transmitWindowSize、transmitWindowOffset、connInterval等等（具体意义这里不再详述）；
>
> 更新该连接所使用的跳频图谱（使用哪些Physical Channels）；
>
> 执行链路加密（Encryption）有关的过程。

#### 6. HCI

定义Host和Controller（通常是两颗IC）之间的通信协议，可基于Uart、USB等物理介质，对理解蓝牙协议来说，是无关紧要的，这里暂不介绍。

#### 7. L2CAP Protocol

##### 7.1 功能介绍

经过Link Layer的抽象之后，两个BLE设备之间可存在两条逻辑上的数据通道：一条是无连接的广播通道，天高任鸟飞；另一条是基于连接的数据通道，是一个点对点（Master对Slave）的逻辑通道。

广播通道暂且不表，这个数据通道（后面简称逻辑通道，Logical Channel），要怎么使用，还需要一番思索，例如：

> Logical Channel只有一条，而要利用它传输数据的上层应用却不止一个（例如图片1中的ATT和SMP），怎么复用？
>
> Logical Channel所能传输的有效payload长度最大只有251bytes，怎是否意味着上层应用每次只能传输少于这个长度的数据？（显然不能！）
>
> Logical Channel仅提供了简单的应答和流控机制，如果传输的数据出错怎么办？
>
> 等等…

以上问题，都是由L2CAP，一个介于应用程序（Profile、Application等）和Link Layer之间的protocol，负责回答，这也是它的缩写（Logical Link Control and Adaptation Protocol）的意义所在。它提供的功能主要包括：

> Protocol/channel multiplexing，协议/通道的多路复用；
>
> Segmentation and reassembly，上层应用数据（L2CAP Service Data Units，SDUs）的分割（和重组），生成协议数据单元（L2CAP Packet Data Units，PDUs），以满足用户数据传输对延时的要求，并便于后续的重传、流控等机制的实现；
>
> Flow control per L2CAP channel，基于L2CAP Channel的流控机制；
>
> Error control and retransmissions，错误控制和重传机制；
>
> Support for Streaming，支持流式传输（如音频、视频等，不需要重传或者只需要有限重传）；
>
> Fragmentation and Recombination，协议数据单元（PDUs）的分片（和重组），生成符合Link Layer传输要求的数据片（长度不超过251，具体可参考5.4.1中有关的介绍）；
>
> Quality of Service，QoS的支持。

鉴于篇幅问题，本文重点介绍有利用理解上层协议（ATT、GATT等）的“Protocol/channel multiplexing”功能，其它部分会在后续L2CAP的分析文章中重点说明。

##### 7.2 Protocol/channel multiplexing

所谓的multiplexing（多路复用），还是很好理解的：

> 可用于传输用户数据的逻辑链路只有一条，而L2CAP需要服务的上层Profile和Application的数目，肯定远不止这个数量。因此，需要使用多路复用的手段，将这些用户数据map到有限的链路资源上去。

至于multiplexing的手段，简单又直接（称的上“协议”的标配）：

> 数据发送时，将用户数据分割为一定长度的数据包（L2CAP Packet Data Units，PDUs），加上一个包含特定“ID”的header后，通过逻辑链路发送出去。
>
> 数据接收时，从逻辑链路接收数据，解析其中的“ID”，并以此判断需要将数据转发给哪个应用。

这里所说的ID，就是多路复用的手段，L2CAP提供两种复用手段：

###### 7.2.1 基于连接的方法（这里的连接为L2CAP connection，不要和Link Layer的connection混淆了）

这里的连接，是指基于L2CAP的应用程序，在通信之前，先建立一个基于Logical Channel的虚拟通道（称作L2CAP channel，和TCP/IP中的端口类似）。L2CAP会为这个通道分配一个编号，称作channel ID（简称CID）。

L2CAP channel建立之后，就可以把CID放到数据包的header中，以达到multiplexing的目的。这些基于CID实现的多路复用，就称作channel multiplexing（基于通道的多路复用）。

那CID是怎么确定的呢？有一些固定用途的L2CAP Channel，其CID是固定值，另外一些则是动态分配的，具体如下：

[![CID name space on LE-U logical link](/content/uploadfile/201603/4fa817627f2063fab370a8333db7350220160312143244.gif "CID name space on LE-U logical link")](/content/uploadfile/201603/71aaf224eacfe7636162f9bd7aa6e07220160312143241.gif)

图片3 BLE CID分配

有关CID的具体数值可参考：[Core\_v4.2.pdf](https://www.bluetooth.org/DocMan/handlers/DownloadDoc.ashx?doc_id=286439&_ga=1.139498554.805272089.1452604944), Volume 3, Part A - Logical Link Control and Adaptation Protocol Specification

###### 7.2.2 无连接的方法

另外，为了提高数据传输的效率，方便广播通信等应用场景，L2CAP在提供基于连接的通信机制之外，也提供了无连接的数据传输方法。基于这种方法，CID不存在了，取而代之的是一个称作Protocol/Service Multiplexer(PSM)的字段。

这种多路复用的手段则成为Protocol multiplexing（基于协议的多路复用）。

由于Protocol multiplexing只允许在BR/EDR controller中使用，本文就不再详细介绍了。

#### 8. Attribute Protocol

由上面章节的描述可知，在BLE协议栈中：Physical Layer负责提供一系列的Physical Channel；基于这些Physical Channel，Link Layer可在两个设备之间建立用于点对点通信的Logical Channel；而L2CAP则将这个Logical Channel换分为一个个的L2CAP Channel，以便提供应用程序级别的通道复用。到此之后，基本协议栈已经构建完毕，应用程序已经可以基于L2CAP欢快的run起来了。

谈起应用程序，就不得不说BLE的初衷----物联网。物联网中传输的数据和传统的互联网有什么区别呢？抛开其它不谈，物联网中最重要、最广泛的一类应用是：信息的采集。

> 这些信息往往都很简单，如温度、湿度、速度、位置信息、电量、水压、等等。
>
> 采集的过程也很简单，节点设备定时的向中心设备汇报信息数据，或者，中心设备在需要的时候主动查询。

基于信息采集的需求，BLE抽象出一个协议：Attribute protocol，该协议将这些“信息”以“Attribute（属性）”的形式抽象出来，并提供一些方法，供远端设备（remote device）读取、修改这些属性的值（Attribute value）。

Attribute Protocol的主要思路包括：

1）基于L2CAP，使用固定的Channel ID（0x004，具体可参考“图片3”）。

2）采用client-server的形式。提供信息（以后都称作Attribute）的一方称作ATT server（一般是那些传感器节点），访问信息的一方称作ATT client。

3）一个Attribute由Attribute Type、Attribute Handle和Attribute Value组成。

> Attribute Type用于标示Attribute的类型，类似于我们常说的“温度”、“湿度”等人类可识别的术语，不过与人类术语不同的是，Attribute Type使用UUID（Universally Unique IDentifier，16-bit、32-bit或者128-bit的数值）区分。
>
> Attribute Handle是一个16-bit的数值，用作唯一识别Attribute server上的所有Attribute。Attribute Handle的存在有如下意义：   
>  a）一个server上可能存在多个相同type的Attribute，显然，client有区分这些Attribute的需要。   
>  b）同一类型的多个Attribute，可以组成一个Group，client可以通过这个Group中的起、始handle访问所有的Attributes。
>
> Attribute Value代表Attribute的值，可以是任何固定长度或者可变长度的octet array（理解为字节类型的数组即可）。

4）Attribute可以定义一些权限（Permissions），以便server控制client的访问行为，包括：

> 访问有关的权限（access permissions），Readable、Writeable以及Readable and writable；
>
> 加密有关的权限（encryption permissions），Encryption required和No encryption required；
>
> 认证有关的权限（authentication permissions），Authentication Required和No Authentication Required；
>
> 授权有关的权限（authorization permissions），Authorization Required和No Authorization Required。

5）根据所定义的Attribute PDU的不同，client可以对server有多种访问方式，包括：

> Find Information，获取Attribute type和Attribute Handle的对应关系；
>
> Reading Attributes，有Read by type、Read by handle、Read by blob（只读取部分信息）、Read Multiple（读取多个handle的value）等方式；
>
> Writing Attributes，包括需要应答的writing、不需要应答的writing等。

#### 9. Generic Attribute Profile

##### 9.1 功能介绍

ATT之所以称作“protocol”，是因为它还比较抽象，仅仅定义了一套机制，允许client和server通过Attribute的形式共享信息。而具体共享哪些信息，ATT并不关心，这是GATT（Generic Attribute Profile）的主场。

GATT相对ATT只多了一个‘G‘，但含义却大不同，因为GATT是一个profile（更准确的说是profile framework）。

在蓝牙协议中，profile一直是一个比较抽象的概念，我们可以将其理解为“应用场景、功能、使用方式”都被规定好的Application。传统的BR/EDR如此，BLE更甚。上面我们讲过，BLE很大一部分的应用场景是信息（Attribute）的共享，因此，BLE协议栈基于Attribute Protocol，定义了一个称作GATT（Generic Attribute）的profile framework（它本身也是一个profile），用于提供通用的、信息的存储和共享等功能。

##### 9.2 层次结构

作为一个Profile framework，GATT profile提出了如下的层次结构：

[![GATT Profile hierarchy](/content/uploadfile/201603/9a8230841a3068452877b8b0c3ab3c9320160317144850.gif "GATT Profile hierarchy")](/content/uploadfile/201603/c30a59962849cad4ab665c0532ea6c3520160317144849.gif)

图片4 GATT Profile hierarchy

由上面图片可知，GATT profile的层次结构依次是：Profile—>Service—>characteristic。

“Profile”是基于GATT所派生出的真正的Profile，位于GATT Profile hierarchy的最顶层，由一个或者多个和某一应用场景有关的Service组成。

一个Service包含一个或者多个Characteristic（特征），也可以通过Include的方式，包含其它Service。

Characteristic则是GATT profile中最基本的数据单位，由一个Properties、一个Value、一个或者多个Descriptor组成。

Characteristic Properties定义了characteristic的Value如何被使用，以及characteristic的Descriptor如何被访问。

Characteristic Value是特征的实际值，例如一个温度特征，其Characteristic Value就是温度值就。

Characteristic Descriptor则保存了一些和Characteristic Value相关的信息（比较抽象，后续文章会根据实例做进一步的理解）。

以上除“Profile”外的每一个定义，Service、Characteristic、Characteristic Properties、Characteristic Value、Characteristic Descriptor等等，都是作为一个Attribute存在的，具备第8章所描述的Attribute的所有特征：Attribute   
Handle、Attribute Types、Attribute Value和AttributePermissions。

##### 9.3 重要的思考

蓝牙4.0之后所引入的GATT profile，是一个非常有“心计”的profile，其中有三点，需要我们重点关注：

> 1）基于GATT架构，Application的存在形式，不再是单一的Profile，很多简单的应用场景，可以直接以Service的形式存在（profile的概念隐藏在了GATT中），这大大简化了一些传感器节点的设计复杂度。
>
> 2）仔细瞅一下图片4中的Service，然后回忆一下蓝牙BR/EDR中的服务发现协议（Service Discover Protocol，SDP）中的“Service”，是否有什么关联？你猜对了，非常有关联，在存在GATT的实现中，SDP就没有存在的必要了。Service也是一个普通的Generic Attribute。也正是因为这样的抽象，才使得以往蓝牙协议中的“Service”实例化了。
>
> 3）所谓的“Service”实例化，指的是，任何一个profile，都是由service和对应的profile功能组成。

#### 10. Security Manager（SM）

Security Manager负责BLE通信中有关安全的内容（毫无疑问，在物联网时代，安全变得更重要，谁也不想卧室的灯在深夜的时候会无缘无故的亮吧），包括配对（pairing,）、认证（authentication）和加密（encryption）等过程。

该部分的内容比较独立，这里先不过多介绍，后面会有单独的分析文章。

#### 11. Generic Access Profile（GAP）

上面7到10章的内容，都是和基于连接的data channel有关，至于无连接的advertising channel，以及连接建立的过程，好像被我们忽略了。虽然Link Layer已经做出了定义（具体可参考第5章的介绍），但它们并没有体现到Application（或者Profile）层面，毕竟Link layer太底层了。

因此，BLE协议栈定义了一个称作Generic Access（通用访问）的profile，以实现如下功能：

1）定义GAP层的蓝牙设备角色（role）

> 和5.3中的Link Layer的role类似，只不过GAP层的role更接近用户（可以等同于从用户的角度看到的蓝牙设备的role），包括：
>
> Broadcaster Role，设备正在发送advertising events；
>
> Observer Role，设备正在接收advertising events；
>
> Peripheral Role，设备接受Link Layer连接（对应Link Layer的slave角色）；
>
> Central Role，设备发起Link Layer连接（对应Link Layer的master角色）。

2）定义GAP层的、用于实现各种通信的操作模式（Operational Mode）和过程（Procedures），包括：

> Broadcast mode and observation procedure，实现单向的、无连接的通信方式；
>
> Discovery modes and procedures，实现蓝牙设备的发现操作；
>
> Connection modes and procedures，实现蓝牙设备的连接操作；
>
> Bonding modes and procedures，实现蓝牙设备的配对操作。

3）定义User Interface有关的蓝牙参数，包括：

> 蓝牙地址（Bluetooth Device Address）；
>
> 蓝牙名称（Bluetooth Device Name）；
>
> 蓝牙的pincode（Bluetooth Passkey）；
>
> 蓝牙的class（Class of Device，和发射功率有关）；
>
> 等等。

4）Security有关的定义，暂不介绍

#### 12. Applications

暂不介绍了，后续其它文章会结合某些Profile及应用场景的室例，作进一步分析。

*原创文章，转发请注明出处。蜗窝科技，[www.wowotech.net](/bluetooth/ble_stack_overview.html)。*
