---
title: "USB-C(USB Type-C)规范的简单介绍和分析"
date: 2017-12-18T16:18:25+08:00
url: "/usb/usb_type_c_overview.html"
gid: "417"
emlog_type: "blog"
summary: "从1996年1月USB1.0正式发布至今（2017年9月 USB3.2发布），USB已经走过了21个年头。在这21年的时间了，USB标准化组织（ USB Implementers Forum，USB-IF）折腾出来了各式各样、五花八门的接口形态：Type A、Type A SuperSpeed、Type B、Type B SuperSpeed、Mini-A、Mini-B、Micro-A、Micro"
author: "wowo"
category: "USB"
category_alias: "usb"
tags: ["Power", "USB", "typec", "type-c", "3.1", "pd"]
views: 64786
comment_count: 17
aliases:
  - "/usb/417.html"
  - "/417.html"
---

## 1. 前言

从1996年1月USB1.0正式发布至今（2017年9月 USB3.2发布），USB已经走过了21个年头。在这21年的时间了，USB标准化组织（*USB* Implementers Forum，USB-IF）折腾出来了各式各样、五花八门的接口形态：Type A、Type A SuperSpeed、Type B、Type B SuperSpeed、Mini-A、Mini-B、Micro-A、Micro-B、Micro-B SuperSpeed、Type C等等。

另外，USB接口主要由插座（Receptacle）、插头（Plug）和线缆（Cable）三部分组成，再叠加上这些奇奇怪怪的规范，灾难就发生了：

> A产品喜欢用Type A的插座，B产品偏偏喜欢Type B，连接它们的线缆就悲剧了，只能变成A-to-B的了。以此类推，A-to-A、B-to-B、A-to-MicroA、等等，于是我们的抽屉就挤满了各种不明用途的USB线……

好吧，吐槽时间结束，因为本文的主角不是过去的那些奇奇怪怪的接口，而是最新的、红到发紫的USB-C（也称作USB Type C）规范。提起typec，它还真和它的A、B前辈们不太一样：

> 因为它有自己独立的、自行演化的规范文件----USB Type-C Specification（2014年发8月布1.0版本，2017年7月发布1.3版本）。而前辈们就没有这样的待遇了，它们都依附于具体的USB规范（USB 1.0、USB 1.1、USB 2.0、等等）。

为什么会这样的呢？当然是因为它有独特之处了，具体请参考本文后续的描述。

## 2. 概述

我们接着上面的问题讲。

Type C之前的规范（Type A、Type B、等等），偏重于USB接口的“硬”的特性，如信号的个数、接口的形态、电气特性、等等，这些特性一旦固定，就没有更改的需求了，这就导致了：

> 1）这些接口规范不需要单独存在（因为没有更新、演化的要求），“随便”在USB规范的哪个章节交代一下就行了。
>
> 2）同时存在五花八门、种类繁多的接口（因为不能更新、演化啊，一旦新需求出现，只能再搞一个新的了）。

到USB Type C的时候，USB标准化组织的这些家伙突然开窍了（管他主动开窍还是被动开窍，反正是开窍了），在定义USB接口“硬”的特性的基础上，增加了一些“软”的内容，一下子就海阔天空了。至此，USB接口（仅仅指Type C）摆脱了和USB的从属关系，变成了一个可以和USB规范平起平坐的新规范。

大家估计会很好奇，这家伙到底Get了什么新技能，从而成功上位了呢？让我们简单总结一下（注意其中黄色高亮部分）：

> ▲ 定义一套新的接口形态（Receptacle/Plug/Cable）
>
> ▲ 插座（Receptacle）可以用在很薄的电子设备上，因为它的高度只有3mm
>
> ▲ 插头（Plug）更容易使用了，可以正着插、反着插、随便插、想怎么插怎么插，终于不再反人类了（想想之前，插一个U盘到电脑中：哦，好像插不进去，反过来试试；嗯？还是插不进去，再反过来试试；噢！终于插进去了……流汗中……）
>
> ▲ 线缆（Cable）也更容易使用了，两端一模一样（当然，为了兼容、转接旧有规范的除外），也是想怎么插就怎么插
>
> ▲ 插头（Plug）和线缆（Cable）的改进，并不是一个空手套白狼的买卖，是要付出代价的，因为需要一个称作“Configuration Process”的过程解决如下的两个问题：   
>  □ 插头可以随便插，因而需要一套检测插入方向的机制，并可以通过插入方向动态的map管脚信号以便进行后续的通信   
>  □ 线缆的两端一模一样，就无法区分所连接的两个USB设备的角色（Host or Device、等等），因而需要一套协商机制，以便让两端的USB设备进行角色的沟通
>
> ▲ 以上的“Configuration Process”是使用两个称作CC（CC1和CC2）的管脚进行的，利用不同电压，传递一些简单的信息，以满足上面的需求。   
>  □ 后来，一个称作USB PD（Power Delivery）[3]的规范出现了，它在这两个管脚上实现了一种简单的、半双工的通信协议，以完成USB power供给有关协商（有关USB PD，可参考相应的规范[3]以及本站后续的文章）。可以说，这个通信协议就是打开新世界的钥匙。基于它，更多有意义的事情出现了（因此，USB Type C可以单独存在了），例如   
>  □ 支持扩展功能。通过扩展功能，USB Type C接口拥有了无线的想象空间，可以摇身变成任意其它协议的物理接口，例如配件接口、音频接口、视频接口、debug接口等等，大有一统天下之势。从这个角度看，USB Type C不仅仅是成功上位（从USB规范中独立出来），而是成功逆袭（凌驾于USB规范之上），格局啊！！

对USB Type C有个基本的了解之后，我们再简单分析一下它的主要特性（主要从软件的角度，纯电气方面的内容直接插规范就行了，这里不再罗嗦）。

## 3. 主要特性

#### 3.1 接口形态（Receptacle/Plug/Cable）

为了实现自己的理想和抱负，USB Type C定义了新的接口形态。另外，为了兼容旧的接口以及一些特殊功能，它定义了不同形态的插座、插头、线缆。主要包括：

1）定义了2种Type-C的插座

> a）全功能的Type-C插座，可以用于支持USB2.0、USB3.1、等特性的平台和设备。   
> b）USB 2.0 Type-C插座，只可以用在支持USB2.0的平台和设备上。

2）定义了3种Type-C插头

> a）全功能的Type-C插头，可以用于支持USB2.0、USB3.1、等特性的平台和设备。   
> b）USB 2.0 Type-C插头，只可以用在支持USB2.0的平台和设备上。   
> c）USB Type-C Power-Only插头，用在那些只需要供电设备上（如充电器）。

3）定义了3种标准的Type-C线缆

> a）两端都是全功能Type-C插头的全功能Type-C线缆。   
> b）两端都是USB 2.0 Type-C插头的USB 2.0 Type-C线缆。   
> c）只有一端是Type-C插头（全功能Type-C插头或者USB 2.0 Type-C插头）的线缆。

4）为兼容旧设备而定义的线缆或者适配器

> a）一种线缆，一端是全功能的Type-C插头，另一端是USB 3.1 Type-A插头。   
> b）一种线缆，一端是USB 2.0 Type-C插头，另一端是USB 2.0 Type-A插头。   
> c）一种线缆，一端是全功能的Type-C插头，另一端是USB 3.1 Type-B插头。   
> d）一种线缆，一端是USB 2.0 Type-C插头，另一端是USB 2.0 Type-B插头。   
> e）一种线缆，一端是USB 2.0 Type-C插头，另一端是USB 2.0 Mini-B插头。   
> f）一种线缆，一端是全功能的Type-C插头，另一端是USB 3.1 Micro-B插头。   
> g）一种线缆，一端是USB 2.0 Type-C插头，另一端是USB 2.0 Micro-B插头。   
> h）一种适配器，一端是全功能的Type-C插头，另一端是USB 3.1 Type-A插座。   
> i）一种适配器，一端是USB 2.0 Type-C插头，另一端是USB 2.0 Micro-B插座。

注1：再吐槽一下，看了上面的a-i，应该能感受到之前的USB接口规范是多么的能折腾了吧？

#### 3.2 管脚及信号的定义

USB Type-C接口有24个管脚，插座和插头在管脚信号的定义上有一点点的不同，分别如下：

|  |  |  |  |  |  |  |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A1 | A2 | A3 | A4 | A5 | A6 | A7 | A8 | A9 | A10 | A11 | A12 |

|  |  |  |  |  |  |  |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| GND | TX1+ | TX1- | VBUS | CC1 | D+ | D- | SBU1 | VBUS | RX2- | RX2+ | GND |

|  |
| --- |
|  |

|  |  |  |  |  |  |  |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| GND | RX1+ | RX1- | VBUS | SBU2 | D- | D+ | CC2 | VBUS | TX2- | TX2+ | GND |

|  |  |  |  |  |  |  |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| B12 | B11 | B10 | B9 | B8 | B7 | B6 | B5 | B4 | B3 | B2 | B1 |

表格1：USB Type-C Receptacle Interface (Front View)

|  |  |  |  |  |  |  |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A12 | A11 | A10 | A9 | A8 | A7 | A6 | A5 | A4 | A3 | A2 | A1 |

|  |  |  |  |  |  |  |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| GND | RX2+ | RX2- | VBUS | SBU1 | D- | D+ | CC | VBUS | TX1- | TX1+ | GND |

|  |
| --- |
|  |

|  |  |  |  |  |  |  |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| GND | TX2+ | TX2- | VBUS | VCONN |  |  | SBU2 | VBUS | RX1- | RX1+ | GND |

|  |  |  |  |  |  |  |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| B1 | B2 | B3 | B4 | B5 | B6 | B7 | B8 | B9 | B10 | B11 | B12 |

表格2：USB Full-Featured Type-C Plug Interface (Front View)

以上信号按照功能可以分为5类：

> 1）Power有关的信号，包括   
>  a）VBUS，USB线缆的bus power（和我们通常意义上VBUS保持一致）。   
>  b）VCONN（只有在插头上才会有该信号），用于向插头供电（由此可以推测出有些插头中可能会有电路）。   
>  c）GND，接地。
>
> 2）USB 2.0数据线，D+/D-。它们在插头端只有一对，和旧的USB 2.0规范一致。但为了支持正反随意插。在插座端定义了两组，这样插座端可以根据实际情况进行合适的mapping。
>
> 3）USB3.1数据线，TX+/-和RX+/-，用于高速的数据传输。插头和插座端都有两组，用于支持正反随意插。
>
> 4）用于Configuration的信号，对插头来说，只有一个CC，对插座来说，有两个CC1和CC2。
>
> 5）扩展功能所需的信号，具体使用场景由相应的扩展功能决定。
>
> 注2：对于3.1中所描述的不同类型的插座和插头，这24个管脚以及信号不一定全部使用，具体可参考USB Type-C的规范[2]。

注3：大家可能注意到了，USB Type-C 24个管脚信号中，Power类（GND/VBUS）和数据类（D+/D-/TX/RX）是完全对称的（对Power来说，无论怎么插，都是一样；对数据线来说，简单的路由一下，就可以工作）。剩下的，包括CC、SBU和VCONN，用于方向、线类型等检测，具体可参考后面的介绍。

#### 3.3 USB port的Data Role

在USB 2.0及以前的时代，根据功能的不同，USB端口分为Host、Device、OTG（Host和Device二者皆可）、Hub等。在Type C时代，事情的本质还在，不过名字稍微有些调整，分别称作：

> DFP（Downstream Facing Port），一般作为Host或者Hub，在初始配置下通过VBUS或者VCONN向device供电。
>
> UFP（Upstream Facing Port），一般作为Device或者Hub，连接到Host上，初始配置下通过VBUS或者VCONN由Host供电。
>
> DRD(Dual-Role-Data)，类似于以前的OTG，既可以作为DFP，也可以作为UFP。设备刚连接时作为哪一种角色，由端口的Power Role（参考后面的介绍）决定；后续也可以通过data role switch过程更改（如果支持USB PD协议的话）。

#### 3.4 USB port的Power Role

根据USB port的供电（或者受电）情况，USB type c将port划分为Source、Sink等power角色，具体如下：

> Source，通过VBUS或者VCONN供电。
>
> Sink，通过VBUS或者VCONN接受供电。
>
> DRP(Dual-Role-Power)，既可以作为Source，也可以作为Sink。到底作为Source还是Sink，由设备连接后的Configuration Process（具体可参考后面的介绍）以及后续的power role switch过程决定。

#### 3.5 连接检测

USB Type-C的连接检测包括3部分的内容：

> 连接检测；
>
> 连接方向检测；
>
> Power Role检测。

这三部分都是通过USB Type-C接口的CC（CC1和CC2）管脚进行的，原理总结如下（具体细节请参考[2]中的说明，本文不详细罗列了）：

1）参考3.2小节的说明，USB Type-C的插座有两个CC（CC1和CC2），而插头（或者说USB cable），有两种情况：

> ▲ 正常情况下，只有一个CC，两个Type-C端口连接到一起之后，只会存在一个CC连接。通过检测哪一个CC有连接，就可以判断连接的方向。
>
> ▲ 如果是可供电的USB cable（Powered cable），一个用做CC，另一个用作Vconn，检测方式参考后面的介绍。

2）不同功能的USB port，需要在CC1和CC2管脚上接不同的上拉或者下拉电阻，规则如下：

> Source需要在CC1和CC2管脚接上拉电阻Rp（也可以使用电流源取代，本文就不介绍了），Rp的值可参考[2]中“Table 4-20 Source CC Termination (Rp) Requirements”的介绍。
>
> Sink需要在CC1和CC2管脚接下拉电阻Rd，Rd的值可参考[2]中“Table 4-21 Sink CC Termination (Rd) Requirements”的介绍。
>
> 可以通过VCONN供电的USB电缆（Powered cable）为了让Source检测到（以便通过VCONN为它供电），需要在CC脚接下拉电阻Rd，并在Vconn串接一个电阻Ra（代表Vconn的负载）。
>
> 其它配件的规则，不再介绍了（可参考[2]中有关的章节）。

3）基于上面的规则，Source需要根据CC1和CC2的状态（阻值）检测Sink的连接及方向，规则如下：

> 如果CC1和CC2均为Open状态，表示没有Sink连接。
>
> 如果CC1和CC2中的一个的阻值为Rd（除去自己的Rp或者电流源的阻值）、另一个为Open，表示有Sink连接，连接的方向由哪一个CC为Rd决定。
>
> 如果CC1和CC2中的一个的阻值为Ra（除去自己的Rp或者电流源的阻值）、另一个为Open，表示有不带Sink的Powered cable连接，连接的方向由哪一个CC为Ra决定。
>
> 如果一个CC的阻值为Ra，另一个为Rd，则表示有带SInk的Powered cable连接，连接方向由哪个CC为Ra（Rd）决定。

4）Source检测到Sink的连接（及方向）后，会向Vbus和Vconn供电。之后：

> Sink通过检测Vbus来确定Source的连接。
>
> Sink检测到连接后，同样根据CC管脚的状态检测连接方向。

5）Source检测到不带Sink的Powered cable的连接后，不会向Vbus或者Vconn供电。

6）Source检测到带Sink的Powered cable的连接（及方向）后，会向Vbus和Vconn供电，Sink的行为后上面4)类似。

#### 3.6 Power role检测

上面的过程，是基于某个port作为Source，另一个port作为Sink为假设的。实际上，某一个Type-C port可能是DRP port，怎么办呢？简单：

> 它可以在Source和Sink两个状态来回切换，在某一个状态下的检测逻辑，和上面3.5描述的完全一样。
>
> 当在Source状态下，成功的检测到Sink的连接时，则自己作为Source；当在Sink状态下成功检测到Source的连接时，则自己作为Sink。

另外，Type-C规范也提供了一个后悔药，虽然我是DRP（Source或者Sink都可以支持），但我更倾向于作为Source（或Sink）怎么办？好办：

> 当在动态检测的过程中，自己变成了一个自己不喜欢的角色，还可以执行一个Try.SRC或者Try.SNK的过程，尝试变成自己喜欢的角色。如果碰巧对方认可你作为这个角色，OK，万事大吉。

注4：到目前为止（在没有USB PD协议参与的情况下），USB Type-C port的data role必须和power role保持一致（因为Type-C规范没有提供多余的机制去单独的协商data role）。

#### 3.7 USB PD协议

正确连接后，双方通过CC管脚，使用USB PD（Power Delivery）协议，可以进行后续配置和操作，包括：

> Data Role的切换（类似USB OTG的切换）；
>
> Power Role的切换；
>
> Vconn role的切换（谁通过Vconn向Powered cable供电）；
>
> 供电的调整；
>
> 等等（具体可参考[3]以及后续有关USB PD协议的介绍）。

## 4. 参考文档

[1] [https://en.wikipedia.org/wiki/USB#2.0](https://en.wikipedia.org/wiki/USB#2.0 "https://en.wikipedia.org/wiki/USB#2.0")

[2] USB Type-C Specification Release 1.3.pdf

[3] USB\_PD\_R3\_0 V1.1 20170112.pdf

原创文章，转发请注明出处。蜗窝科技，[www.wowotech.net](/usb/usb_type_c_overview.html)。
