---
title: "ARM WFI和WFE指令"
date: 2014-12-10T22:43:43+08:00
url: "/armv8a_arch/wfe_wfi.html"
gid: "120"
emlog_type: "blog"
summary: "\r\n\t蜗蜗很早以前就知道有WFI和WFE这两个指令存在，但一直似懂非懂。最近准备研究CPU idle framework，由于WFI是让CPU进入idle状态的一种方法，就下决心把它们弄清楚。\r\n\r\n\r\n\tWFI(Wait for interrupt)和WFE(Wait for event)是两个让ARM核进入low-power standby模式的指令，由ARM architecture定义，由"
author: "wowo"
category: "ARMv8A Arch"
category_alias: "armv8a_arch"
tags: ["Architecture", "aarch64", "ARM", "wfe", "wfi"]
views: 114940
comment_count: 44
aliases:
  - "/armv8a_arch/120.html"
  - "/120.html"
---

#### 1. 前言

蜗蜗很早以前就知道有WFI和WFE这两个指令存在，但一直似懂非懂。最近准备研究CPU idle framework，由于WFI是让CPU进入idle状态的一种方法，就下决心把它们弄清楚。

WFI(Wait for interrupt)和WFE(Wait for event)是两个让ARM核进入low-power standby模式的指令，由ARM architecture定义，由ARM core实现。听着挺简单，但怎么会有两个指令？它们的区别是什么？使用场景是什么？深究起来，还挺有意思，例如：能想象WFE和spinlock的关系吗？

#### 2. WFI和WFE

1）共同点

WFI和WFE的功能非常类似，以ARMv8-A为例（参考DDI0487A\_d\_armv8\_arm.pdf的描述），主要是“将ARMv8-A PE(Processing Element, 处理单元)设置为low-power standby state”。

需要说明的是，ARM architecture并没有规定“low-power standby state”的具体形式，因而可以由ARM core自行发挥，根据ARM的建议，一般可以实现为standby（关闭clock、保持供电）、dormant、shutdown等等。但有个原则，不能造成内存一致性的问题。以[Cortex-A57](http://infocenter.arm.com/help/topic/com.arm.doc.ddi0488g/DDI0488G_cortex_a57_mpcore_trm.pdf) ARM core为例，它把WFI和WFE实现为“put the core in a low-power state by disabling the clocks in the core while keeping the core powered up”，即我们通常所说的standby模式，保持供电，关闭clock。

2）不同点

那它们的区别体现在哪呢？主要体现进入和退出的方式上。

对WFI来说，执行WFI指令后，ARM core会立即进入low-power standby state，直到有WFI Wakeup events发生。

而WFE则稍微不同，执行WFE指令后，根据Event Register（一个单bit的寄存器，每个PE一个）的状态，有两种情况：如果Event Register为1，该指令会把它清零，然后执行完成（不会standby）；如果Event Register为0，和WFI类似，进入low-power standby state，直到有WFE Wakeup events发生。

WFI wakeup event和WFE wakeup event可以分别让Core从WFI和WFE状态唤醒，这两类Event大部分相同，如任何的IRQ中断、FIQ中断等等，一些细微的差别，可以参考“DDI0487A\_d\_armv8\_arm.pdf“的描述。而最大的不同是，WFE可以被任何PE上执行的SEV指令唤醒。

所谓的SEV指令，就是一个用来改变Event Register的指令，有两个：SEV会修改所有PE上的寄存器；SEVL，只修改本PE的寄存器值。下面让我们看看WFE这种特殊设计的使用场景。

#### 3. 使用场景

1）WFI

WFI一般用于cpuidle。

2）WFE

WFE的一个典型使用场景，是用在spinlock中（可参考arch\_spin\_lock，对arm64来说，位于arm64/include/asm/spinlock.h中）。spinlock的功能，是在不同CPU core之间，保护共享资源。使用WFE的流程是：

> a）资源空闲
>
> b）Core1访问资源，acquire lock，获得资源
>
> c）Core2访问资源，此时资源不空闲，执行WFE指令，让core进入low-power state
>
> d）Core1释放资源，release lock，释放资源，同时执行SEV指令，唤醒Core2
>
> e）Core2获得资源

以往的spinlock，在获得不到资源时，让Core进入busy loop，而通过插入WFE指令，可以节省功耗，也算是因祸（损失了性能）得福（降低了功耗）吧。

*原创文章，转发请注明出处。蜗窝科技，[www.wowotech.net](/armv8a_arch/wfe_wfi.html)。*
