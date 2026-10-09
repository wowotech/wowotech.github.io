---
title: "Linux PM QoS framework(1)_概述和软件架构"
date: 2015-02-04T23:06:09+08:00
url: "/pm_subsystem/pm_qos_overview.html"
gid: "142"
emlog_type: "blog"
summary: "QOS为Quality Of Service（服务质量）的简称，对PM QoS而言，表示Linux kernel电源管理相关的服务质量。那到底什么是服务质量呢？ 我们知道，Linux PM的主要功能，是节省功耗，但同时，会付出一定的性能代价，例如延迟（latency）增加、吞吐量（throughput）下降。可以把PM当作一种服务，把它对性能的影响，类比为服务的质量（QoS）。对性能的影响越大，Q"
author: "wowo"
category: "电源管理子系统"
category_alias: "pm_subsystem"
tags: ["Linux", "PM", "电源管理", "pm_qos", "qos"]
views: 27624
comment_count: 5
aliases:
  - "/pm_subsystem/142.html"
  - "/142.html"
---

#### 1. 前言

QOS为Quality Of Service（服务质量）的简称，对PM QoS而言，表示Linux kernel电源管理相关的服务质量。那到底什么是服务质量呢？

我们知道，Linux PM的主要功能，是节省功耗，但同时，会付出一定的性能代价，例如延迟（latency）增加、吞吐量（throughput）下降。可以把PM当作一种服务，把它对性能的影响，类比为服务的质量（QoS）。对性能的影响越大，QoS越低，反之越高。

不过，PM QoS framework的存在，并不是为了定义并测量系统的服务质量（Linux系统对实际的qos没有任何兴趣），而是为了定义一套框架，以满足系统各个实体（如进程、设备驱动等等）对QoS的期望为终极目标。根据实际的场景，这些期望可描述为：xxx不大于某个值；xxx不小于某个值；等等。

这个终极目标，是基于这样的事实：机器是极端的实用主义者。最理想的状况，是刚刚满足系统各个实体对QoS的期望，因而可以在满足需求的同时，最大化的省电。粗俗一点，就是“我能考60分，为什么要多花一点力气去考61分？”。这样的思路，值得我们深思。

本文将基于PM QoS framework整体的软件架构，介绍它的功能、应用场景、使用方式等。

#### 2. 工作原理

kernel将“系统各个实体对QoS的期望”抽象为一个一个的constraint（可以理解为约束），围绕这些constraint，可以将系统的实体分为三类：requestor、pm qos framework和requestee。示意图如下：

[![pm qos](/content/uploadfile/201502/a622bc475db2c2c83a065dcef3262c1520150204150547.gif "pm qos")](/content/uploadfile/201502/9ab4e929592f4c65d5efced9d2515e1120150204150546.gif)

requestors提出对QoS的constraint。常见的requestor包括应用进程、GPU device、net device、flash device等等，它们基于自身的实际特性，需要系统的QoS满足一定的条件，才能正常工作。

pm qos core负责汇整、整理这些constraint，并根据实际情况，计算出它们的极值（最大或者最小）。

requestee在需要的时候，从pm qos core处获取constraint的极值，并确保自身的行为，可以满足这些constraints。一般情况下，requestee都是电源管理有关的service，包括[cpuidle](/tag/cpuidle)、[runtime pm](/tag/rpm)、[pm domain](/pm_subsystem/pm_domain_overview.html)等等。

注：requestor和requestee这两个词汇，是蜗蜗自己造出来的，只是为了理解方便。实际上，Linux kernel使用“QoS dependencies”的概念，分别用“Dependents on a QoS value”和“Watchers of QoS value”表述这两个实体，具体可参考kernel/power/qos.c和drivers/base/power/qos.c的文件header。

介绍完requestor和requestee之后，还要再回答一个问题：系统中到底有哪些constraint？这决定了request的对象。截至到目前，PM QoS framework将constraint分为2类，每一类包括若干个constraint，具体如下。

1）系统级的constraint，包括cpu&dma latency、network latency、network throughput和memory bandwidth 4个constraint。

2）设备级别的constraint，包括从低功耗状态resume的latency、active状态的latency和一些QoS flag（如是否允许power off）。

蜗蜗会在后续的文章中详细描述这些constraints的意义，这里先有个大概的认识即可。

#### 3. 软件架构

根据上面2类constraint，Linux kernel提供了2个不同的QoS framework：

一个是系统级别的，用于cpu&dma latency、network latency、network throughput、memory bandwidth等场合，称作PM QoS classes framework。

另一个是device级别的，用于per-device场合，称作per-device PM QoS framework。

这2个framework有着共同的目标，即：向requestors提供request的add、modify、remove等接口，用于管理QoS requests；将QoS requests分门别类，计算出极值（简称value）；向requestee提供request value的查询接口。其软件架构(非常简单）如下：

[![pm qos framework](/content/uploadfile/201502/28eb475f046873d9d896183ce16b3ca820150204150548.gif "pm qos framework")](/content/uploadfile/201502/e8dc5e97858441963954722089e1d7a420150204150547.gif)

PM QoS classes framework位于kernel/power/qos.c中，负责系统级别的PM QoS管理。per-device PM QoS framework位于drivers/base/power/qos.c中，负责per-device的PM QoS管理。Common header位于include/linux/pm\_qos.h中，负责通用数据结构的抽象、函数声明等工作。

需要说明的是，PM QoS classes framework会通过misc设备，向用户空间程序提供PM QoS的request、modify、remove功能，以便照顾到它们对PM QoS的需求。

接下来的文章中，将分别从PM QoS classes framework和per-device PM QoS framework两个角度描述PM QoS framework，本文就不再详细描述了。

*原创文章，转发请注明出处。蜗窝科技*，[www.wowotech.net](/pm_subsystem/pm_qos_overview.html)。
