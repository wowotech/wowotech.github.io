---
title: "蓝牙协议分析(1)_基本概念"
date: 2014-05-23T18:15:02+08:00
url: "/bluetooth/bt_overview.html"
gid: "45"
emlog_type: "blog"
summary: "自1994年由爱立信推出至今，蓝牙技术已经走过了20个岁月。从最初的Bluetooth V1.0，到Bluetooth V4.0（最新的为V4.1，2013年底发布），经历了近9个版本的修订后，发展为当前的状况。 说实话，如今的蓝牙4.1，简直是一个大杂烩：BR/EDR沿用旧的蓝牙规范；LE抄袭802.15.4；AMP直接使用802.11。而这一切的目的，就是以兼容性和易用性为基础，在功耗和传输速"
author: "wowo"
category: "蓝牙"
category_alias: "bluetooth"
tags: ["Bluetooth", "BR", "EDR", "BLE", "AMP"]
views: 106457
comment_count: 50
aliases:
  - "/bluetooth/45.html"
  - "/45.html"
---

#### 1. 前言

自1994年由爱立信推出至今，蓝牙技术已经走过了20个岁月。从最初的Bluetooth V1.0，到Bluetooth V4.0（最新的为V4.1，2013年底发布），经历了近9个版本的修订后，发展为当前的状况。

说实话，如今的蓝牙4.1，简直是一个大杂烩：BR/EDR沿用旧的蓝牙规范；LE抄袭802.15.4；AMP直接使用802.11。而这一切的目的，就是以兼容性和易用性为基础，在功耗和传输速率之间左右为难。蜗蜗以为，这并不是优雅的设计。

不过没关系，存在即合理。因此蜗蜗就开出了这样一个专题，希望能够将蓝牙技术上上下下的知识，整理出来，以便在加深自己对蓝牙技术的理解的同时，能够给从事蓝牙相关工作的读者一点启发。

本文是这个专题的第一篇文章，主要基于蓝牙4.1规范（[Core\_V4.1.pdf](https://www.bluetooth.org/DocMan/handlers/DownloadDoc.ashx?doc_id=282159)），描述蓝牙技术的基本概念。

#### 2. 蓝牙技术的概述

##### 2.1 两种蓝牙技术：Basic Rate（BR）和Low Energy（LE）

蓝牙协议包括两种技术：Basic Rate（简称BR）和Low Energy（简称LE）。这两种技术，都包括搜索（discovery）管理、连接（connection）管理等机制，但**它们是不能互通的**！这也是蜗蜗抱怨蓝牙协议不优雅的原因之一。

厂商要么实现这两种技术中的一种，这时就只能和同样实现了这个技术的设备互通，而不能和实现另外一种技术的设备互通。如果厂商要确保能和所有的蓝牙设备互通，那么就只能同时实现两种技术，而不去管是否真的需要，这样就能碰到什么人说什么话了！

**2.1.1 Basic Rate(BR)**

Basic Rate是正宗的蓝牙技术，可以包括**可选（optional）**的EDR（Enhanced Data Rate）技术，以及**交替使用的（Alternate）**的MAC（Media Access Control）层和PHY层扩展（简称AMP）。说着真拗口，不过通过背后的应用场景，就好理解了：

> 蓝牙诞生之初，使用的是BR技术，此时蓝牙的理论传输速率，只能达到721.2Kbps。在那个年代，56Kbps的Modem就是高大上了，这个速度可以说是惊为天人了啊！但是科技变化太快了，BR技术转眼就过时了。那怎么办呢？缝缝补补一下，增强速度呗，Enhanced Data Rate就出现了。
>
> 使用EDR技术的蓝牙，理论速率可以达到2.1Mbps。这一次的升级换代，还算优雅，因为没有改变任何的硬件架构、软件架构和使用方式上的改变。
>
> 也许你也猜到了，EDR又落伍了，看看人家WIFI（WLAN），几十Mbps，上百Mbps，咱们才2.1Mbps，也太寒酸了吧！那怎么办呢？蓝牙组织想了个坏主意：哎，WIFI！把你的物理层和MAC层借我用用呗！这就是AMP（Alternate MAC and PHY layer extension）。艾玛，终于松口气了，我们可以达到54Mbps了。
>
> 不过呢，由于蓝牙自身的物理层和AMP技术差异太明显了，这次扩展只能是交替使用（Alternate）的，也就是说，有我（BR/EDR）没你（AMP）。嗯！不优雅！
>
> 埋个问题：只能交替使用，那它们怎么切换呢？蜗蜗会在后续的内容中，根据主流蓝牙芯片的解决方案，来探讨一下该问题。

【注1：细心的读者可能会注意到，这里特别强调了optional和alternate这两个字眼，这是蓝牙Spec的原话。它意味着，BR和EDR是可以同时存在的，但BR/EDR和AMP只能二选一。】

**2.1.2 Low Energy（LE）**

上面所讲的BR技术的进化路线，就是传输速率的加快、加快、再加快。但能量是守恒的，你想传的更快，代价就是消耗更多的能量。而有很多的应用场景，并不关心传输速率，反而非常关心功耗。这就是Bluetooth LE（称作蓝牙低功耗）产生的背景。

LE技术相比BR技术，差异非常大，或者说就是两种不同的技术，凑巧都加一个“蓝牙”的前缀而已。后面我们会详细的解释这种差异，以及LE的行为特征。

##### 2.2 蓝牙系统的组成

蓝牙系统的组成，涉及到Bluetooth Application、Bluetooth Core、Bluetooth Host、Bluetooth Controller等词汇，不知道是因为对英文理解的歧义，还是因为蓝牙规范本身定义的歧义，蜗蜗理解这些词汇时感觉有点别扭。因此特意在这个章节中，对相关概念及其背后的意义进行说明。

[![蓝牙系统组成](/content/uploadfile/201405/8ef568eb90bdb6aa4e9cff885734fe2620140523101501.gif "蓝牙系统组成")](/content/uploadfile/201405/71efba9ef5feff0b750b94e9162ebd3820140523101500.gif)上图描述了蓝牙系统的组成， 我们需要注意如下特点：

> 1）图中所描述的蓝牙系统的组成部分，如Bluetooth Core和Bluetooth Application，如Host和Controller，都是指“**逻辑实体**”。所谓的“逻辑实体”，需要和日常生活中的“物理实体”区隔开。如在做电路设计时，一个蓝牙芯片、一个主控CPU，就是指物理实体。而蓝牙协议所描述的这些“逻辑实体”，不一定会和物理实体一一对应，如在实际应用中，Host和Bluetooth Application可能会位于同一个物理实体中（主控CPU），而Controller单独位于另一个物理实体中（蓝牙芯片）。
>
> 2）蓝牙协议规定了两个层次的协议，分别为蓝牙核心协议（Bluetooth Core）和蓝牙应用层协议（Bluetooth Application）。蓝牙核心协议关注对蓝牙核心技术的描述和规范，它只提供基础的机制，并不关心如何使用这些机制；蓝牙应用层协议，是在蓝牙核心协议的基础上，根据具体的应用需求，百花齐放，定义出各种各样的策略，如FTP、文件传输、局域网等等。
>
> 3）Bluetooth Core由两部分组成，Host和Controller。这两部分在不同的蓝牙技术中（BR/EDR、AMP、LE），承担角色略有不同，但大致的功能是相同的。Controller负责定义RF、Baseband等偏硬件的规范，并在这之上抽象出用于通信的逻辑链路（Logical Link）；Host负责在逻辑链路的基础上，进行更为友好的封装，这样就可以屏蔽掉蓝牙技术的细节，让Bluetooth Application更为方便的使用。
>
> 4）在一个系统中，Host只有一个，但Controller可以一个，也可以有多个。如：单独的LE Controller；单独的BR/EDR Controller；单独的LE+BR/EDR Controller；在单独的BR/EDR Controller或LE+BR/EDR Controller基础上，增加一个或多个额外的AMP Controller。
>
> 【注2：有关Bluetooth Core的详细描述，蜗蜗会在下一篇文章中描述，本文就不再深入介绍了。】

3. BR/EDR vs LE vs AMP

我们先从下面图片对BR/EDR、AMP和BLE三种技术有些更进一步的认识（点击[这里](/content/uploadfile/201406/eaf01404028766.gif)可以查看放大后的原图）：

![BT_RF_Baseband_Overview.gif](/content/uploadfile/201406/eaf01404028766.gif "点击查看原图")

该图片是对Bluetooth Core的一个Overview，从RF的Physical Channel，到Baseband的Physical Link、Logical Link、LMP、L2CAP等概念，都有一些粗略的介绍。由该图片可以看出，BR/EDR、AMP、BLE等技术有如下的特点：

> 1）BR/EDR技术，过于侧重“点对点”通信，以至于虽然在协议的底层（如Logical Link）有提及多播（Unidirectional）和广播（Broadcast）的概念，但在上层的应用场景中，几乎不存在（也不可能存在）相应的应用。
>
> 2）但随着物联网的发展，业界对简单的、不需要连接的多播或广播通信的需求越来越迫切，因此BLE技术在RF和Baseband的协议中，就做出了修改，以适应这种需求，即：修改原有的79个channel的跳频方式，将channel的个数减少为40个，并保留了不少于3个的固定channel，用于广播通信。为仅仅在剩下的37个data channel上跳频。
>
> 3）正因为这种改变，原有的搜索/连接/配对等概念，在BLE上就不再存在了，取而代之的是Advertisor、Initiator等概念。但在之后的数据通信的层次上，尽量保持了一致。
>
> 4）对于AMP来说，是基于BR/EDR的controller，在完成通常的点对点连接之后，两个蓝牙设备商议，是否需要将后续的数据通信，转移至AMP controller上。这就是Bluetooth 3.0引入的AMP技术。

我们暂时在这篇文章中对蓝牙技术做一个感性认识，在后续的文章中，会基于各个层次的协议，一步一步展开、推进，争取能把蓝牙技术分析透彻。

*原创文章，转发请注明出处。蜗窝科技，[www.wowotech.net](/bluetooth/bt_overview.html)。*
