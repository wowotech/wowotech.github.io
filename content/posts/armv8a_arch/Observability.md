---
title: "ARMv8之Observability"
date: 2016-05-25T18:22:53+08:00
url: "/armv8a_arch/Observability.html"
gid: "302"
emlog_type: "blog"
summary: "在ARMv8关于memory order描述章节中，大量使用了observer、observed、completion等术语，本文主要是澄清这些术语，为后续描述memory order和memory barrier相关指令打下基础。另外，在几个星期前，和codingbelief同学讨论DMB指令的时候，他提出了一个尖锐的问题：什么是PE observes memory access，是指 cpu "
author: "linuxer"
category: "ARMv8A Arch"
category_alias: "armv8a_arch"
tags: ["ARMv8", "observer", "observed"]
views: 13042
comment_count: 8
aliases:
  - "/armv8a_arch/302.html"
  - "/302.html"
---

一、前言

在ARMv8关于memory order描述章节中，大量使用了observer、observed、completion等术语，本文主要是澄清这些术语，为后续描述memory order和memory barrier相关指令打下基础。另外，在几个星期前，和codingbelief同学讨论DMB指令的时候，他提出了一个尖锐的问题：什么是PE observes memory access，是指 cpu 执行了 memory access 指令么？当时我对这些概念也比较模糊，未能回答他的疑问，现在希望这份文档可以解决这个问题。

二、observer

原文定义：

> An observer is a master in the system that is capable of observing memory accesses

从字面的意思看，能够“观察”到内存访问行为的master角色的硬件组件就是observer。这里需要解释两个关键词：一个是master，另外一个是观察（observing）。一个observer首先需要是一个总线master，可以通过总线发出读写操作。而所谓“观察”，实际上也通过read或者write操作来感知其他的内存操作，例如：通过read操作，observer可以感知到内存值的数据变化。当然，observer不仅仅能够读，还可以执行写操作，一个PE中可能的observer包括：

（1）执行load或者store操作的CPU组件（能够对内存发起读或者写操作）

（2）执行取指操作的CPU组件（仅仅能够发起对内存的read操作）

（3）加载页表的CPU组件（仅仅能够发起对内存的read操作）

从上面的描述可知，并非系统中有多少个CPU core（或者称为PE）就有多少个observer，一个PE往往包括多个observer。实际上，系统中的observer的数目是和具体的实现相关，除了PE之外，GPU，DMA controller等都可以发起对memory的read或者write操作，也都是observer。

三、什么是Observability？

可以用下面通俗的语言来描述Observability：

> I have observed your write when I can read what you wrote and I have observed your read when I can no longer change the value you read

这里的I和you都是指的系统中的observer。上面的这句话是针对两个场景：一个是对写动作的观察，I have observed your write when I can read what you wrote，当A observer通过对X地址的读操作获取了另外B observer对X地址的写入数值的时候，那么，可以认为A observer观察到了B observer的写入动作。另外一个场景是对读动作的观察，I have observed your read when I can no longer change the value you read，当A observer无法通过对地址X的值的写入操作来影响B observer的对X地址的read操作结果的时候，我们认为A observer观察到了B observer的read动作。

四、observed write

原文定义：

> A write to a location in memory is said to be observed by an observer when:   
> — A subsequent read of the location by the same observer returns the value written by the observed write, or written by a write to that location by any observer that is sequenced in the Coherence order of the location after the observed write.   
> — A subsequent write of the location by the same observer is sequenced in the Coherence order of the location after the observed write.

什么叫一次写入的内存操作被某个observer观察到（observed）？这事不能从单个写入操作看，还是让我们拉高一些，从一个写入序列来看。我们还是通过一个经典的例子来说明observed write这个概念。假设系统中有四个cpu core，分别执行同样的代码：cpux给一个全局变量A赋值为x，然后不断对A进行观察（即load操作）。在这个例子中A分别被四个CPU设定了1、 2、3、4的值，当然，先赋值的操作结果会被后来赋值操作覆盖，最后那个执行的write操作则决定了A变量最后的赋值。假设一次运行后，cpu 1看到的序列是{1,2}，cpu 2看到的序列是{2}，cpu 3看到的序列是{3,2}，cpu 4看到的序列是{4,2}，具体如下图所示：

![](/content/uploadfile/201512/133813bd99a9d17a3c4ecd41982a305420151225041816.gif)

我们先选定一个观察对象：cpu4的写入操作。怎么观察呢？通过read或者write来观察（英文原文的两段解释就是分别针对read和write的）。我们先看read吧，这是最直观的感受（或者称为观察）cpu4的写入动作的方法。有两种情况都可以认为本observer已经观察到了cpu4的写入操作：

（1）该observer的read操作返回了“4”。例如在cpu4上，read返回了之前write的数值“4”

（2）该observer的read操作没有返回“4”，但是返回了Coherence order 排在4之后的数值。例如，对于cpu1而言，刚开始，其read操作返回“1”（红色条带），大概在300ns的时间左右，read操作返回了“2”，我们知道，对于全局变量A，其coherent order是{3,1,4,2}，只要返回了coherent order序列中，4之后的数值，我们就认为该observer已经观察到了cpu4的对全局变量A写入数值4的操作。

通过write来“观察”另外一个write操作有点不是那么符合人类的逻辑思维，但是可以慢慢适应的，毕竟我们的目标是理解multiprocessing environment。对于write而言，只有一种情况认为本observer已经观察到了cpu4的写入操作：即做为观察者的那个observer的写入动作在coherent order序列中排在“4”之后。对于cpu 2而言，当执行写入2的操作的时候，我们认为，cpu 2已经观察到了cpu4的写入操作。

需要强调的是，本节描述的observed write都是以一个特定的observer为视角的，不是全局的概念。

五、globally observed write

原文定义：

> A write to a location in memory is said to be globally observed for a shareability domain or set of observers when:   
> — A subsequent read of the location by any observer in that shareability domain returns the value written by the globally observed write, or written by a write to that location by any observer that is sequenced in the Coherence order of the location after the globally observed write.   
> — A subsequent write of the location by any observer in that shareability domain is sequenced in the   
> Coherence order of the location after the globally observed write.

理解了上一节的内容，这里几乎不需要过多的解释，只需要强调两点：

（1）globally observed write是限定在一个shareability domain内部，或者指定的一个observer的集合。

（2）当一个shareability domain（observer集合）内所有的observer都观察到了一次write操作，那么就是globally observed write。

六、observed read和globally observed read

原文定义：

> • A read of a location in memory is said to be observed by an observer when a subsequent write to the location by the same observer has no effect on the value returned by the read.   
> • A read of a location in memory is said to be globally observed for a shareability domain when a subsequent write to the location by any observer in that shareability domain has no effect on the value returned by the read.

怎么观察（感知）其他observer的读操作的确是一个技术活，通过read毫无疑问是不可能感知的，唯有通过write来感知。当某个observer无法通过write操作来影响被观察者的read操作的时候，我们就认为该observer已经感知到了该read操作。类似的，globally observed read就是一个shareability domain内所有的observer们都观察到了该read操作。

七、内存访问指令的执行完成（completion）

原文定义：

> A read or write is complete for a shareability domain when all of the following are true:   
> — The read or write is globally observed for that shareability domain.   
> — Any translation table walks associated with the read or write are complete for that shareability domain.

内存访问指令被观察到和内存访问指令执行完毕是两个不同的概念，对于内存访问指令执行完毕，需要满足下面的两个条件：

（1）该内存访问操作被特定的shareability domain内的所有的observer globally observed

（2）和该内存访问指令相关的translation table walks（也会引发内存访问操作）必须执行完毕。

这里又牵扯出另外一个问题：什么叫做translation table walks执行完毕？原文定义如下：

> A translation table walk is complete for a shareability domain when the memory accesses associated with the translation table walk are globally observed for that shareability domain, and the TLB is updated.

需要满足两个条件：

（1）这个translation table walks而引起的内存访问操作被该shareability domain内的所有的observer globally observed

（2）TLB已经完成更新

八、参考文献

1、Computer Architecture, A Quantitative Approach 5th

2、Programmer’s Guide for ARMv8-A

原创文章，转发请注明出处。蜗窝科技，[www.wowotech.net](/)。
