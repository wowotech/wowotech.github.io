---
title: "Linux reset framework"
date: 2017-09-01T10:46:14+08:00
url: "/pm_subsystem/reset_framework.html"
gid: "408"
emlog_type: "blog"
summary: "大家都知道，复杂IC内部有很多具有独立功能的硬件模块，例如CPU cores、GPU cores、USB控制器、MMC控制器、等等，出于功耗、稳定性等方面的考虑，有些IC在内部为这些硬件模块设计了复位信号（reset signals），软件可通过寄存器（一般1个bit控制1个硬件）控制这些硬件模块的复位状态。 Linux kernel为了方便设备驱动的编写，抽象出一个简单的软件框架----rese"
author: "wowo"
category: "电源管理子系统"
category_alias: "pm_subsystem"
tags: ["Linux", "Kernel", "内核", "framework", "reset"]
views: 19397
comment_count: 1
aliases:
  - "/pm_subsystem/408.html"
  - "/408.html"
---

## 1. 前言

大家都知道，复杂IC内部有很多具有独立功能的硬件模块，例如CPU cores、GPU cores、USB控制器、MMC控制器、等等，出于功耗、稳定性等方面的考虑，有些IC在内部为这些硬件模块设计了复位信号（reset signals），软件可通过寄存器（一般1个bit控制1个硬件）控制这些硬件模块的复位状态。

Linux kernel为了方便设备驱动的编写，抽象出一个简单的软件框架----reset framework，为reset的provider提供统一的reset资源管理手段，并为reset的consumer（各个硬件模块）提供便捷、统一的复位控制API。

reset framework的思路、实现和使用都非常简单、易懂（参考kernel有关的API--include/linux/reset-controller.h、include/linux/reset.h可知），不过麻雀虽小，五脏俱全，通过它可以加深对Linux kernel的设备模型、驱动框架、分层设计、provider/consumer等设计思想的理解，因此本文将对其进行一个简单的罗列和总结。

## 2. 从consumer的角度看

从某一个硬件模块的驱动设计者来看，他的要求很简单：我只是想复位我的硬件，而不想知道到底用什么手段才能复位（例如控制哪个寄存器的哪个bit位，等等）。

> 这个要求其实体现了软件设计（甚至是任何设计）中的一个最最质朴的设计理念：封装和抽象。对设备驱动来说，它期望看到是“reset”这个通用概念，用这个通用概念去发号施令的话，这个驱动就具备了通用性和可移植性（无论在周围的环境如何变化，“reset”本身不会变化）。而至于怎么reset，是通过寄存器A的bit m，还是寄存器B的bit n，则是平台维护者需要关心的事情（就是本文的reset provider）。

看到这样的要求，Linux kernel说：OK，于是reset framework出场，提供了如下的机制（基于device tree）：

1）首先，提供描述系统中reset资源的方法（参考下面第3章的介绍），这样consumer可以基于这种描述在自己的dts node中引用所需的reset信号。

2）然后，consumer设备在自己的dts node中使用“resets”、“reset-names”等关键字声明所需的reset的资源，例如[1]（“resets”字段的具体格式由reset provider决定”）：

> device {   
> resets = <&rst 20>;   
> reset-names = "reset";   
> };

3）最后，consumer driver在需要的时候，可以调用下面的API复位自己（具体可参考“include/linux/reset.h“）：

3-a）只有一个reset信号的话，可以使用最简单的device\_reset API

> int device\_reset(struct device \*dev);

3-b）如果需要更为复杂的控制（例如有多个reset信号、需要控制处于reset状态的长度的等），可以使用稍微复杂的API

> /\* 通过reset\_control\_get或者devm\_reset\_control\_get获得reset句柄 \*/   
> struct reset\_control \*reset\_control\_get(struct device \*dev, const char \*id);   
> void reset\_control\_put(struct reset\_control \*rstc);   
> struct reset\_control \*devm\_reset\_control\_get(struct device \*dev, const char \*id);
>
> /\* 通过reset\_control\_reset进行复位，或者通过reset\_control\_assert使设备处于复位生效状态，通过reset\_control\_deassert使复位失效 \*/   
> int reset\_control\_reset(struct reset\_control \*rstc);   
> int reset\_control\_assert(struct reset\_control \*rstc);   
> int reset\_control\_deassert(struct reset\_control \*rstc);

## 3. 从provider的角度看

kernel为reset provider提供的API位于“include/linux/reset-controller.h”中，很简单，无非就是：创建并填充reset controller设备（struct reset\_controller\_dev），并调用相应的接口（reset\_controller\_register/reset\_controller\_unregister）注册或者注销之。

reset controller的抽象也很简单：

|  |
| --- |
| struct reset\_controller\_dev {    struct reset\_control\_ops \*ops;    struct module \*owner;    struct list\_head list;    struct device\_node \*of\_node;    int of\_reset\_n\_cells;    int (\*of\_xlate)(struct reset\_controller\_dev \*rcdev,    const struct of\_phandle\_args \*reset\_spec);    unsigned int nr\_resets;    }; |

> ops提供reset操作的实现，基本上是reset provider的所有工作量。
>
> of\_xlate和of\_reset\_n\_cells用于解析consumer device dts node中的“resets = ; ”节点，如果reset controller比较简单（仅仅是线性的索引），可以不实现，使用reset framework提供的简单版本----of\_reset\_simple\_xlate即可。
>
> nr\_resets，该reset controller所控制的reset信号的个数。
>
> 其它字段内部使用，provider不需要关心。

struct reset\_control\_ops也比较单纯，如下：

|  |
| --- |
| struct reset\_control\_ops {    int (\*reset)(struct reset\_controller\_dev \*rcdev, unsigned long id);    int (\*assert)(struct reset\_controller\_dev \*rcdev, unsigned long id);    int (\*deassert)(struct reset\_controller\_dev \*rcdev, unsigned long id);    }; |

> reset可控制设备完成一次完整的复位过程。
>
> assert和deassert分别控制设备reset状态的生效和失效。

## 4. 参考文档

[1] Documentation/devicetree/bindings/reset/reset.txt

*原创文章，转发请注明出处。蜗窝科技*，[www.wowotech.net](/pm_subsystem/reset_framework.html)。
