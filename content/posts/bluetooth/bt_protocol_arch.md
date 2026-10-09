---
title: "蓝牙协议分析(2)_协议架构"
date: 2016-01-14T22:20:28+08:00
url: "/bluetooth/bt_protocol_arch.html"
gid: "257"
emlog_type: "blog"
summary: "本文是 蓝牙协议分析 的第二篇文章，在“ 蓝牙协议分析(1)_基本概念 ”的基础上，从整体架构的角度，了解蓝牙协议的组成，以便加深对蓝牙的理解。"
author: "wowo"
category: "蓝牙"
category_alias: "bluetooth"
tags: ["Bluetooth", "l2cap", "profile", "hci", "gap"]
views: 97782
comment_count: 54
aliases:
  - "/bluetooth/257.html"
  - "/257.html"
---

#### 1. 前言

本文是[蓝牙协议分析](/sort/bluetooth)的第二篇文章，在“[蓝牙协议分析(1)\_基本概念](/bluetooth/bt_overview.html)”的基础上，从整体架构的角度，了解蓝牙协议的组成，以便加深对蓝牙的理解。

#### 2. 协议层次

蓝牙协议是通信协议的一种，为了把复杂问题简单化，任何通信协议都具有层次性，特点如下：

> 从下到上分层，通过层层封装，每一层只需要关心特定的、独立的功能，易于实现和维护；
>
> 在通信实体内部，下层向上层提供服务，上层是下层的用户；
>
> 在通信实体之间，协议仅针对每一层，实体之间的通信，就像每一层之间的通信一样，这样有利于交流、理解、标准化。

蓝牙协议也不例外，其协议层次如下：

[![bluetooth_stack_layer](/content/uploadfile/201601/3e7103be90acfd5ffeeea6c3d040eaab20160114142019.gif "bluetooth_stack_layer")](/content/uploadfile/201601/55182faff2cc9b359b52f6001d239d7720160114142019.gif)

从OSI（Open System Interconnection）模型的角度看，蓝牙是一个比较简单的协议，它仅仅提供了物理层（Physical Layer）和数据链路层（Data Link Layer ）两个OSI层次。但由于蓝牙协议的特殊性、历史演化因素等原因，其协议层次又显的不简单，甚至晦涩难懂（如上面图片所示的Physical Link、Logical Transport等）。

蓝牙协议分为四个层次：物理层（Physical Layer）、逻辑层（Logical Layer）、L2CAP Layer和应用层（APP Layer）。

> 物理层，负责提供数据传输的物理通道（通常称为信道）。通常情况下，一个通信系统中存在几种不同类型的信道，如控制信道、数据信道、语音信道等等。
>
> 逻辑层，在物理层的基础上，提供两个或多个设备之间、和物理无关的逻辑传输通道（也称作逻辑链路）。
>
> L2CAP层，L2CAP是逻辑链路控制和适配协议（Logical Link Control and Adaptation Protocol）的缩写，负责管理逻辑层提供的逻辑链路。基于该协议，不同Application可共享同一个逻辑链路。类似TCP/IP中端口（port）的概念。
>
> APP层，理解蓝牙协议中的应用层，基于L2CAP提供的channel，实现各种各样的应用功能。Profile是蓝牙协议的特有概念，为了实现不同平台下的不同设备的互联互通，蓝牙协议不止规定了核心规范（称作Bluetooth core），也为各种不同的应用场景，定义了各种Application规范，这些应用层规范称作蓝牙profile。

在以上四个层次的基础上，蓝牙协议又将物理层和逻辑层划分了子层，分别是Physical Channel/Physical Links和Logical Transports/Logical Links，这一划分，相当使人崩溃，要多花费大量的脑细胞去理解它们，具体请参考下面的分析。

##### 2.1 物理层

物理层负责提供数据传输的物理信道，蓝牙的物理层分为Physical Channel和Physical Links两个子层。我们先介绍Physical Channel。

###### 2.1.1 Physical Channel（物理信道）

一个通信系统中通常存在多种类型的物理信道，蓝牙也不例外。另外，由“[蓝牙协议分析(1)\_基本概念](/bluetooth/bt_overview.html)”的介绍可知，蓝牙存在BR/EDR、LE和AMP三种技术，这三种技术在物理层的实现就有很大的差异，下面让我们一一介绍。

首先是相同点，BR/EDR、LE和AMP的RF都使用2.4GHz ISM(Industrial Scientific Medical) 频段，频率范围是2.400-2.4835 GHz。

注1：不同国家和地区蓝牙的频率和信道分配情况是不同，本文所有的描述都以中国采用的“欧洲和美国”标准为准。

除了相同点，剩下的都是不同点了。

BR/EDR是传统的蓝牙技术，它这样定义物理信道：

> 1）ISM频率范围内被分成79个channel，每一个channel占用1M的带宽，在0 channel和78 channel之外设立guard band（保护带宽，Lower Guard Band为2MHz，Upper Guard Band为3.5MHz）。
>
> 2）采用跳频技术（hopping），也就是说，某一个物理信道，并不是固定的占用79个channel中的某一个，而是以一定的规律在跳动（该规律在技术上叫做"伪随机码"，就是"假"的随机码）。因此蓝牙的物理信道，也可以称作跳频信道（hopping channel）。
>
> 3）BR/EDR技术定义了5种物理信道（跳频信道），BR/EDR Basic Piconet Physical Channel、BR/EDR Adapted Piconet Physical Channel、BR/EDR Page Scan Physical Channel、BR/EDR Inquiry Scan Physical Channel和BR/EDR Synchronization Scan Channel。
>
> 4）BR/EDR Inquiry Scan Physical Channel用于蓝牙设备的发现操作（discovery），即我们常用的搜索其它蓝牙设备（discover）以及被其它蓝牙设备搜索（discoverable）。
>
> 5）BR/EDR Page Scan Physical Channel用于蓝牙设备的连接操作（connect），即我们常用的连接其它蓝牙设备（connect）以及被其它蓝牙设备连接（connectable）。
>
> 6）BR/EDR Basic Piconet Physical Channel和BR/EDR Adapted Piconet Physical Channel主要用在处于连接状态的蓝牙设备之间的通信。它们的区别是，BR/EDR Adapted Piconet Physical Channel使用较少的RF跳频点。BR/EDR Basic Piconet Physical Channel使用全部79个跳频点，而BR/EDR Adapted Piconet Physical Channel是根据当前的信道情况使用79个跳频点中的子集，但是跳频数目也不能少于20个。这个主要是因为蓝牙使用ISM频段，当蓝牙和WIFI共存的时候，部分跳频点被WIFI设备占用而使得蓝牙设备在这些跳频点上的通信总是失败，因此，需要避过那些WIFI设备占用的频点。
>
> 7）BR/EDR Synchronization Scan Channel可用于无连接的广播通信，后续文章会详细介绍。
>
> 8）同一时刻，BT 设备只能在其中一个物理信道上通信，为了支持多个并行的操作，蓝牙系统采用时分方式，即不同的时间点采用不同的信道。

LE是为蓝牙低功耗而生的技术，为了实现低功耗的目标，其物理信道的定义与BR/EDR有些差异：

> 1）ISM频率范围内被分成40个channel，每一个channel占用2M的带宽，在0 channel和39 channel之外设立guard band（保护带宽，Lower Guard Band为2MHz，Upper Guard Band为3.5MHz）。
>
> 2）LE技术定义了2种物理信道，LE Piconet channel和LE Advertisement Broadcast Channel。
>
> 3）LE Piconet Channel用在处于连接状态的蓝牙设备之间的通信，和BR/EDR一样，采用调频技术。和BR/EDR不一样的地方是，只会在40个频率channel中的37个上面跳频。
>
> 4）LE Advertisement Broadcast Channel用于在设备间进行无连接的广播通信，这些广播通信可用于蓝牙的设备的发现、连接（和BR/EDR类似）操作，也可用于无连接的数据传输。
>
> 8）和BR/EDR一样，同一时刻，BT 设备只能在其中一个物理信道上通信，为了支持多个并行的操作，蓝牙系统采用时分方式，即不同的时间点采用不同的信道。

AMP是为高速数据传输设计的技术，其物理层规范直接采用802.11（WIFI）的PHY规范，主要有如下特点：

> AMP物理信道只有一种，即AMP Physical Channel，主要用于已连接设备之间的数据通信，和BR/EDR技术中的BR/EDR Adapted Piconet Physical Channel位于一个级别，可以互相切换使用。

###### 2.1.2 Physical Links（物理链路）

由2.1.1的描述可知，蓝牙协议为BR/EDR、LE和AMP三种技术定义了8种类型的物理信道，包括：

> AMP physical channel
>
> BR/EDR Basic Piconet Physical Channel   
> BR/EDR Adapted Piconet Physical Channel   
> BR/EDR Page Scan Physical Channel   
> BR/EDR Inquiry Scan Physical Channel   
> BR/EDR Synchronization Scan Channel
>
> LE Piconet Channel   
> LE Advertisement Broadcast Channel

而物理链路，则是对这些物理信道（主要是BR/EDR技术中的Basic Piconet Physical Channel和Adapted Piconet Physical Channel）的进一步封装，其主要特征是（可参考2.5中的图片以辅助理解）：

> 1）Physical Link是一个虚拟概念，不对应协议中任何的实体，数据包封包/解包的过程中不被体现。
>
> 2）AMP Physical Channel、LE Piconet Channel、LE Advertisement Broadcast Channel均有一个一一对应的Physical Link，分别是AMP Physical Link、LE Active Physical Link、LE Advertising Physical Channel。
>
> 3）BR/EDR Page Scan Physical Channel、BR/EDR Inquiry Scan Physical Channel、BR/EDR Synchronization Scan Channel只在特定时间段使用，且无法控制任何属性，因此不需要再Physical Link中体现。
>
> 4）BR/EDR Basic Piconet Physical Channel和BR/EDR Adapted Piconet Physical Channel是BR/EDR技术中已连接设备之间进行数据通信的通道，且同一时刻只能根据应用场景选择一种channel进行数据传输。因此这两个channel被map到BR/EDR Active Physical Link、BR/EDR Parked Physical Link和BR/EDR Connectionless Slave Broadcast Physical Link三个物理链路上。
>
> 5）BR/EDR Active Physical Link和BR/EDR Parked Physical Link的抽象主要有两个方面的意义：   
> 5-1）屏蔽底层的Basic/Adapted Piconet Physical Channel之间的差异，统一使用Physical Link取代。在需要的时候，可以通过上层的链路管理协议，指定使用哪一种physical channel（Basic or Adapted）。   
> 5-2）可以通过Physical Link的抽象，控制Physical Channel的一些属性（如发射功率、收发周期等），以达到节省功耗的目的。而上面的层次（如逻辑层）不需要对这些动作知情。
>
> 6）BR/EDR Active Physical Link定义了连接状态的蓝牙设备在链路处于active状态时的物理链路，该物理链路对应的设备的发射功率是可修改的。
>
> 7）BR/EDR Parked Physical Link定义了连接状态的蓝牙设备在链路处于parked状态时的物理链路。parked状态是一种特殊的连接状态，连接双方没有正在进行的数据传输，所有的链路消耗，都是为保持连接所做的事情。此时可以通过降低在物理信道上的收发频率而降低功耗。该物理链路和BR/EDR Active Physical Link使用相同的物理信道。
>
> 8）BR/EDR Connectionless Slave Broadcast Physical Link使用BR/EDR Adapted Piconet Physical Channel，用于一点到多点的广播通信。
>
> 9）由上面的描述可知，物理链路这一层抽象，实在是可有可无，希望大家不要纠结，知道怎么回事即可。

##### 2.2 逻辑层

逻辑层的主要功能，是在已连接（LE Advertisement Broadcast可以看做一类特殊的连接）的蓝牙设备之间，基于物理链路，建立逻辑信道。所谓的逻辑信道，和城市道路上的车道类似：

> 一条城市道路可以看做一个物理链路（可能有两个方向，我们只考虑其中一个即可），该物理链路根据行车用途，可以划分为多个逻辑信道，如直行车道、右转车道、左转车道、掉头车道、快速车道、慢速车道等等。

这里的车道（逻辑信道），从物理角度看，并没有什么分别，只是为了方便交通（数据传输），人为的抽象出来的。和车道类似，蓝牙逻辑信道的划分依据是传输类型，主要包括下面3类（即Logical Link）：

> 1）用于管理底层物理链路的控制类传输，包括AMP-C、ACL-C、PSB-C、LE-C、ADVB-C。
>
> 2）传输用户数据的用户类传输，包括AMP-U、ACL-U、PSB-U、LE-U、ADVB-U。
>
> 3）其它比较特殊的传输类型，包括流式传输（stream）、PBD（Profile Broadcast Data）。

以上每种Logic Link都会在下层对应一个Logical Transport，这些Logical Transport具有一些属性值，如流控、应答/重传机制等。如下：

> AMP ACL（Asynchronous Connection-Oriented Link），基于AMP技术的、面前连接的、异步传输链路，为AMP-U提供服务。
>
> BR/EDR ACL，基于BR/EDR技术的ACL链路，为ACL-C、ACL-U提供服务。
>
> SCO/eSCO（Synchronous Connection-Oriented/Extended SCO），基于BR/EDR技术的、面向连接的、同步传输链路，为stream类型的Logical Link提供服务。
>
> ASB（Active Slave Broadcast）、PSB（Parked Slave Broadcast），基于BR/EDR技术的、面向连接的广播传输链路，为ACL-U、PSB-U、PSB-C提供服务。
>
> CSB（Connectionless Slave Broadcast），基于BR/EDR技术的、无连接的广播链路，为PBD提供服务。
>
> LE ACL，基于LE技术的、面前连接的、异步传输链路，为LE-U、LE-C提供服务。
>
> ADVB（Advertising Broadcast），基于LE技术的、广告/广播链路，为ADVB-U、ADVB-C提供服务。

注2：AMP-C没有对应的Logical Transport，而是直接控制AMP Physical Link完成所需功能。

注3：蓝牙逻辑层的抽象也是让人醉了！还是那句话，不要逼自己去理解一个疯子的行为，不然自己也会疯的。

##### 2.3 L2CAP Channels

L2CAP是Logical Link Control and Adaptation Protocol（逻辑链路控制和适配协议）的缩写，蓝牙协议到这个层次的时候，就清爽多了：

> 对下，它在用户类XXX-U Logical Link的基础上，抽象出和具体技术无关的数据传输通道（包括单播和广播两类），至此用户就不再需要关心繁杂的蓝牙技术细节。
>
> 对上，它以L2CAP channel endpoints的概念（类似TCP/IP中的端口），为具体的应用程序（profile）提供独立的数据传输通道（当然，也是一个逻辑通道）。

##### 2.4 Profiles

profile是蓝牙Application的代指，也可以翻译为服务，为了实现不同平台下的不同设备的互联互通，蓝牙协议为各种可能的、有通用意义的应用场景，都制定的了规范，如SPP、HSP、HFP、FTP、IPv6/6LoWPAN等等。

Profiles基于L2CAP提供的L2CAP channel endpoints实现，在它们对应的层次上进行数据通信，以完成所需功能。有关蓝牙profile的介绍，会在后续文章中陆续给出，这里就不再详细说明了。

##### 2.5 总结

下面图片包含上面各个层次（除了APP layer）中涉及到的一些实体、概念以及相互关系，供大家参考。

[![Overview of transport architecture entities and hierarchy](/content/uploadfile/201601/1e6e7ff79f144102829dbddf76bb0f5920160114142023.gif "Overview of transport architecture entities and hierarchy")](/content/uploadfile/201601/e5953490cf8bd92fc5b014f1a0905cb320160114142022.gif)

摘录自：[Core\_v4.2.pdf](https://www.bluetooth.org/DocMan/handlers/DownloadDoc.ashx?doc_id=286439&_ga=1.139498554.805272089.1452604944)---->Vol1: Architecture & Terminology Overview---->Part A: Architecture---->3 DATA TRANSPORT ARCHITECTURE---->3.2 TRANSPORT ARCHITECTURE ENTITIES

#### 3. 蓝牙核心框架

蓝牙规范有两类：一类是蓝牙核心规范，由[Bluetooth Core Specification](https://www.bluetooth.com/specifications/bluetooth-core-specification)定义，囊括到L2CAP层，以及相关的核心profile；另一类是蓝牙Application规范，包含了各种各样的profile规范（具体可参考“[https://www.bluetooth.com/specifications/adopted-specifications](https://www.bluetooth.com/specifications/adopted-specifications "https://www.bluetooth.com/specifications/adopted-specifications")”中的列表）。

蓝牙核心规范所定义的框架如下：

[![Bluetooth core system architecture](/content/uploadfile/201601/70f6af8e1a1f608a6635c6312f641e5520160114142028.gif "Bluetooth core system architecture")摘录自：](/content/uploadfile/201601/6dc67a1dce48e839916bd974208a7fea20160114142023.gif)[Core\_v4.2.pdf](https://www.bluetooth.org/DocMan/handlers/DownloadDoc.ashx?doc_id=286439&_ga=1.139498554.805272089.1452604944) ---->Vol1: Architecture & Terminology Overview---->Part A: Architecture---->2 CORE SYSTEM ARCHITECTURE

经过第2章协议层次的介绍，蓝牙核心框架已经比较容易理解了，这里对层次中各个模块做一个简单的说明，更为详细的分析，请参考后续的文章。

1）BR/EDR Radio & LE Radio & AMP PHY

> 蓝牙RF层（物理层），包括BR/EDR、LE以及AMP三种。负责在物理channel上收发蓝牙packet。
>
> 对BR/EDR和LE RF来说，还会接收来自Baseband的控制命令来控制RF频率的选择和timing。
>
> AMP PHY使用802.11（WIFI）的规范，本文不再详细介绍，后续有关AMP的内容，也不过多涉及。

2）Link Controller & Baseband resource management

> Link Controller和Baseband resource management组成了蓝牙的基带（baseband）。
>
> Link Controller负责链路控制，主要是根据当前物理channel的参数、逻辑channel的参数、逻辑transport的参数将数据payload组装成bluetooth packet。另外，通过Link Control Protocol（对LE来说是LL Layer Protocol），可以实现流控、ack、重传等机制。
>
> Baseband resource management，主要用于管理RF资源。

3）Link Manager

> Link Manager主要负责创建、修改、释放蓝牙逻辑连接（Logical Link），同时也负责维护蓝牙设备之间物理连接（Physical Link）的参数。它的功能主要是通过Link Management Protocol（LMP，for BR/EDR）和Link Layer Protocol（LL，for LE）完成。

4）Device Manager

Device Manager主要负责控制蓝牙设备的通用行为（蓝牙数据传输除外的行为），主要是：

> 搜索附近的蓝牙设备
>
> 连接到其他的蓝牙设备
>
> 使得本地的蓝牙设备connectable和discoverable
>
> 控制本地蓝牙设备的属性（例如本地蓝牙设备的名字、link key等）

5）HCI（Host Controller Interface）

我们在“[蓝牙协议分析(1)\_基本概念](/bluetooth/bt_overview.html)”介绍过，蓝牙系统分为Bluetooth Controller和Bluetooth Host两个大的block。它们之间通过HCI接口以HCI协议进行通信。

6）L2CAP

L2CAP位于Bluetooth Host中，包括两个子模块：

Channel Manager主要负责创建、管理、释放L2CAP channel。

L2CAP Resource Manager负责统一管理、调度L2CAP channel上传递的PDU（Packet Data Unit），以确保那些高QoS的packet可以获得对物理信道的控制权。

7）SMP（Security Manager Protocol）

SMP是一个点对点的协议，基于专用的L2CAP channel，用于生成加密（encryption）和识别（identity）用的密匙（keys）。

8）SDP（Service Discover Protocol）

SDP也是一个点对点的协议，基于专用的L2CAP channel，用于发现其它蓝牙设备能提供哪些profile以及这些profile有何特性。在了解清楚了其他蓝牙设备的profile以及特性之后，本蓝牙设备可以发起对自己感兴趣的蓝牙profile的连接动作。

9）AMP Manager

基于L2CAP channel，和对端的AMP manager交互，用于发现对方是否具备AMP功能，以及收集用于建立AMP物理链路的信息。

10）GAP（Generic Access Profile）

GAP是一个基础的蓝牙profile，用于提供蓝牙设备的通用访问功能，包括设备发现、连接、鉴权、服务发现等等。

GAP 是所有其它应用模型的基础，它定义了在 Bluetooth 设备间建立基带链路的通用方法。还定义了一些通用的操作，这些操作可供引用 GAP 的应用模型以及实施多个应用模型的设备使用。GAP 确保了两个 蓝牙设备（不管制造商和应用程序）可以通过 Bluetooth 技术交换信息，以发现彼此支持的应用程序。

4. 参考文档

[1]: [Core\_v4.2.pdf](https://www.bluetooth.org/DocMan/handlers/DownloadDoc.ashx?doc_id=286439&_ga=1.139498554.805272089.1452604944)

[2]: <https://www.bluetooth.org/en-us/Documents/Bluetooth4-2FAQ.pdf>

[3]: [https://www.bluetooth.com/specifications/adopted-specifications](https://www.bluetooth.com/specifications/adopted-specifications "https://www.bluetooth.com/specifications/adopted-specifications")

*原创文章，转发请注明出处。蜗窝科技，[www.wowotech.net](/bluetooth/bt_protocol_arch.html)。*
