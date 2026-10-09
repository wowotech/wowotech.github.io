---
title: "linux内核中的GPIO系统之（5）：gpio subsysem和pinctrl subsystem之间的耦合"
date: 2017-08-10T22:17:49+08:00
url: "/gpio_subsystem/pinctrl-and-gpio.html"
gid: "405"
emlog_type: "blog"
summary: "按理说，kernel中gpio subsystem和pinctrl subsystem的关系应该非常清楚： pinctrl subsystem管理系统的所有管脚，GPIO是这些管脚的用途之一，因此gpio subsystem应该是pinctrl subsystem的client（也可叫做backend、consumer），基于pinctrl subsystem提供的功能，处理GPIO有关的逻辑。 "
author: "wowo"
category: "GPIO子系统"
category_alias: "gpio_subsystem"
tags: ["GPIO", "subsystem", "pinctrl", "range"]
views: 28850
comment_count: 5
aliases:
  - "/gpio_subsystem/405.html"
  - "/405.html"
---

## 1. 前言

按理说，kernel中gpio subsystem和pinctrl subsystem的关系应该非常清楚：

> pinctrl subsystem管理系统的所有管脚，GPIO是这些管脚的用途之一，因此gpio subsystem应该是pinctrl subsystem的client（也可叫做backend、consumer），基于pinctrl subsystem提供的功能，处理GPIO有关的逻辑。

不过，实际情况却不是这么简单，它们之间有着较为紧密的耦合（看一看kernel中pinctrl和gpio相关的实现就知道了）。本文将对这种耦合进行一个简单的分析，解释为什么要这样设计。

## 2. Why

首先，无论硬件的架构如何（可参考[[2]](/gpio_subsystem/pin-control-subsystem.html/)中“五、和GPIO subsystem交互”），从逻辑上讲，有一点是很明确的（这一点和linuxer同学在[2]中的说明有出入，待讨论）：

> gpio subsystem永远是pinctrl的backend（或client，或consumer）。

基于这一点，规范的做法，任何一个gpio chip（相关的概念可参考本站GPIO子系统的文章[5]），在使用GPIO的时候（通常是gpio subsystem的consumer申请GPIO资源的时候），都需要向系统的pinctrl subsystem申请管脚，并将管脚配置为GPIO功能。

思路是简单、直接的，但实际操作起来，却有点棘手，下面以一个最简单的例子说明：

> 假设某一个gpio chip只包括2个gpio，这两个gpio分别和uart进行功能复用。
>
> 如果这两个管脚是同时控制的，要么是gpio，要么是uart，就很好处理了，按照pinctrl subsystem的精神，抽象出两个function：gpio和uart，gpio chip在使用gpio功能的时候，调用pinctrl set state，将它们切换为gpio即可。
>
> 但是，如果这两个gpio可以分开控制（很多硬件都是这样的设计的），麻烦就出现了，每个gpio要单独抽象为一个function，因此我们可以抽象出3个function：gpio1、gpio2和uart。
>
> 然后考虑一下一个包含32个gpio的chip（一般硬件的gpio bank都是32个），如果它们都可以单独控制，则会出现32个function。而系统又不止有一个chip，灾难就发生了，我们的device tree文件将会被一坨坨的gpio functions撑爆！

规范是我们追求的目标，但有限度，不能让上面的事情发生，怎么办呢？在pinctrl subsystem的标准框架上打个洞，只要碰到这种情况，直接就走后门就是了。

## 3. pinctrl中和gpio有关的后门

后门是什么呢？其实很简单，参考下面的API：

|  |
| --- |
| static inline int pinctrl\_request\_gpio(unsigned gpio) ;    static inline void pinctrl\_free\_gpio(unsigned gpio) ;    static inline int pinctrl\_gpio\_direction\_input(unsigned gpio);    static inline int pinctrl\_gpio\_direction\_output(unsigned gpio); |

> 当gpio driver需要使用某个管脚的时候，直接调用pinctrl\_request\_gpio，向pinctrl subsystem申请。
>
> pinctrl subsystem会维护一个gpio number到pin number的map，将gpio subsystem传来的gpio number转换为pin number之后，调用struct pinmux\_ops中有关的回调函数即可：
>
> struct pinmux\_ops {   
> ...   
> int (\*gpio\_request\_enable) (struct pinctrl\_dev \*pctldev,   
> struct pinctrl\_gpio\_range \*range,   
> unsigned offset);   
> void (\*gpio\_disable\_free) (struct pinctrl\_dev \*pctldev,   
> struct pinctrl\_gpio\_range \*range,   
> unsigned offset);   
> int (\*gpio\_set\_direction) (struct pinctrl\_dev \*pctldev,   
> struct pinctrl\_gpio\_range \*range,   
> unsigned offset,   
> bool input);   
> };
>
> 对gpio driver来说，要做的事情就是提供gpio number到pin number的map。
>
> 而pinctrl subsystem呢，做自己分内的事情即可：管理系统的pin资源，并根据gpio subsystem的请求，将某些pin设置为GPIO功能。

## 4. gpio range----gpio number到pin number的map

那么，怎么提供gpio number和pin number的map呢？是通过一个名称为gpio range的数据结构(pinctrl subsystem提供的），如下：

|  |
| --- |
| /\* include/linux/pinctrl/pinctrl.h \*/       /\*\*    \* struct pinctrl\_gpio\_range - each pin controller can provide subranges of    \* the GPIO number space to be handled by the controller    \* @node: list node for internal use    \* @name: a name for the chip in this range    \* @id: an ID number for the chip in this range    \* @base: base offset of the GPIO range    \* @pin\_base: base pin number of the GPIO range if pins == NULL    \* @pins: enumeration of pins in GPIO range or NULL    \* @npins: number of pins in the GPIO range, including the base number    \* @gc: an optional pointer to a gpio\_chip    \*/    struct pinctrl\_gpio\_range {    struct list\_head node;    const char \*name;    unsigned int id;    unsigned int base;    unsigned int pin\_base;    unsigned const \*pins;    unsigned int npins;    struct gpio\_chip \*gc;    }; |

> 该数据结构很容易理解，总结来说，就是：gpio controller(gc)中的gpio(base)到gpio(base + npins - 1)，和pin controller中的pin(pin\_base)到pin(pin\_base + npins - 1)是一一对应的。
>
> 有了这个对应关系之后，pinctrl subsystem就可以将任意一个gpio controller中的gpio number转换为相应的pin controller中的pin number。

最后，gpio subsystem为了方便gpio driver的开发，提供了一种简单的、可以通过device tree提供gpio range信息的方法，总结如下：

1）gpio range的dts格式示例（可参考[6]中的介绍）

> qe\_pio\_e: gpio-controller@1460 {   
> #gpio-cells = <2>;   
> compatible = "fsl,qe-pario-bank-e", "fsl,qe-pario-bank";   
> reg = <0x1460 0x18="">;   
> gpio-controller;   
> gpio-ranges = <&pinctrl1 0 20 10>, <&pinctrl2 10 50 20>;  
> };

上面dts节点中的gpio-ranges关键字指定了两个gpio range：gpio controller(qe\_pio\_e)中的gpio0~9和pinctrl1中的pin20~29对应；gpio controller(qe\_pio\_e)中的gpio10~29和pinctrl2中的pin50~69对应。

2）gpio range dts node的解析

解析的过程如下（具体不再详细介绍了，大家可参考相应的代码）：

> devm\_gpiochip\_add\_data(drivers/gpio/gpiolib.c)   
> gpiochip\_add\_data   
> of\_gpiochip\_add(drivers/gpio/gpiolib-of.c)   
> of\_gpiochip\_add\_pin\_range   
> gpiochip\_add\_pin\_range(drivers/gpio/gpiolib.c)   
> pinctrl\_find\_and\_add\_gpio\_range(drivers/pinctrl/core.c)   
> pinctrl\_add\_gpio\_range

以上过程的结果，就是在相应的pin controller device的数据结构中生成了一个gpio range的链表，如下：

> struct pinctrl\_dev {   
> struct list\_head node;   
> struct pinctrl\_desc \*desc;   
> struct radix\_tree\_root pin\_desc\_tree;   
> struct list\_head gpio\_ranges;  
> ...   
> };

3）gpio range的使用

当gpio driver需要使用某一个gpio的时候，可以在gpiochip的request函数中，调用pinctrl core提供的pinctrl\_request\_gpio接口（参数是gpio编号），然后pinctrl core会查寻gpio ranges链表，将gpio编号转换成pin编号，然后调用pinctrl的相应接口（参数是pin编号），申请该pin的使用。

至此，gpio subsystem和pinctrl subsystem的耦合，就真相大白了。

## 5. 参考文档

[1] [https://github.com/wowotechX/linux/blob/x\_integration/Documentation/pinctrl.txt](https://github.com/wowotechX/linux/blob/x_integration/Documentation/pinctrl.txt "https://github.com/wowotechX/linux/blob/x_integration/Documentation/pinctrl.txt")

[2] [linux内核中的GPIO系统之（2）：pin control subsystem](/gpio_subsystem/pin-control-subsystem.html)

[3] [linux内核中的GPIO系统之（4）：pinctrl驱动的理解和总结](/gpio_subsystem/pinctrl-driver-summary.html)

[4] [X-023-KERNEL-Linux pinctrl driver的移植](/x_project/kernel_pinctrl_driver_porting.html)

[5] [/sort/gpio_subsystem](/sort/gpio_subsystem "/sort/gpio_subsystem")

[6] Documentation/devicetree/bindings/gpio/gpio.txt

原创文章，转发请注明出处。蜗窝科技，[www.wowotech.net](/gpio_subsystem/pinctrl-and-gpio.html)。
