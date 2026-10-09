---
title: "ARMv8之Atomicity"
date: 2016-05-13T19:18:37+08:00
url: "/armv8a_arch/atomicity.html"
gid: "295"
emlog_type: "blog"
summary: "本文主要解析ARMv8手册中的Atomicity这个概念。首先给出为何定义这样的概念，定义这个概念的作用为何？然后介绍Atomicity相关的概 念，很多时候我们引用了手册的原文，但是由于这些原文象天书一样难懂（可读性比较差），因此，我们使用程序员可理解的一些语言来描述这些概念。最后给出 ARMv8上，各种内存操作指令，针对各种memory type，其Atomicity的特性为何。"
author: "linuxer"
category: "ARMv8A Arch"
category_alias: "armv8a_arch"
tags: ["Coherent", "Single-copy", "atomicity", "Multi-copy"]
views: 22067
comment_count: 8
aliases:
  - "/armv8a_arch/295.html"
  - "/295.html"
---

一、前言

本文主要解析ARMv8手册中的Atomicity这个概念。首先给出为何定义这样的概念，定义这个概念的作用为何？然后介绍Atomicity相关的概念，很多时候我们引用了手册的原文，但是由于这些原文象天书一样难懂（可读性比较差），因此，我们使用程序员可理解的一些语言来描述这些概念。最后给出ARMv8上，各种内存操作指令，针对各种memory type，其Atomicity的特性为何。

二、Atomicity概述

1、什么是Atomicity？

Atomicity是用来描述系统中的memory access的特性的一个术语。在单核系统上，我们用Single-copy atomicity这个术语来描述，也就是说该内存访问操作是否是原子的，是否是可以被打断的。在多核系统中，用Single-copy atomicity来描述一次内存访问的原子性是不够的，因为即便是在执行该内存访问指令的CPU CORE上是Single-copy atomicity的，也只不过说明该指令不会被本CPU CORE的异常或者中断之类的异步事件打断，它并不能阻止其他CPU core上的内存访问操作对同一地址上的memory location进行操作，这时候，我们使用Multi-copy atomicity来描述多个CPU CORE发起对同一个地址进行写入的时候，这些内存访问表现出来的特性是怎样的。

2、为何定义Atomicity？

无它，主要是为了软件和硬件能够和谐工作在一起。对于软件工程师而言，我们必须了解硬件和软件的“接口”，即那些是HW完成，那些是需要软件完成的，只有这样，软件和CPU的硬件才能愉快的一起玩耍。对于硬件，其architecture reference maual需要定义这些接口。对于ARM处理器而言（并非SOC，主要指CPU core），接口分成两个大类，第一类是指CPU定义的各种通用寄存器、状态寄存器、各种协处理器寄存器，CPU支持的指令集等，这些是属于比较好理解的那一部分，另外一类是关于行为或者说是操作的定义，这部分的接口不是那么明显，但是也是非常重要的。Atomicity即属于第二类接口定义。

三、基本概念解释

1、Coherent order

由于在Atomicity的定义中大量引用了该术语，因此我们这里需要先解释一下，关于coherent order，原文定义如下：

> Data accesses from a set of observers to a byte in memory are coherent if accesses to that byte in memory by the members of that set of observers are consistent with there being a single total order of all writes to that byte in memory by all members of the set of observers. This single total order of all to writes to that memory location is the coherence order for that byte in memory.

从这里的英文原文，我们可以得出下面的结论：

（1）coherent不是漫无边际的，而是受限于“a set of observers”，用ARMv8的术语就是shareability domain。属于同一个shareability domain的observers共享memory space，并且能够对同一个地址的memory进行操作。

（2）是否coherent这里是从shareability domain中的一个或者多个observers的视角来观察的。观察什么？观察的是写入的动作，具体的说就是该shareability domain中的多个observers对某个内存位置进行写入的动作。观察的结果是什么？如果是coherent的，那么shareability domain中的各个observers看到的是一个一致的、全局写入顺序。

（3）强调一下，这里的write serialization有一个前提条件就是写入的是同一个memory location。

（4）下面我们用一个具体的例子来说明什么是“single total order”。假设系统中有四个cpu
core，分别执行同样的代码：cpux给一个全局变量A赋值为x，然后不断对A进行观察（即load操作）。在这个例子中A分别被四个CPU设定了1、
2、3、4的值，当然，先赋值的操作结果会被后来赋值操作覆盖，最后那个执行的write操作则决定了A变量最后的赋值。假设一次运行后，cpu
1看到的序列是{1,2}，cpu 2看到的序列是{2}，cpu 3看到的序列是{3,2}，cpu
4看到的序列是{4,2}，那么所有的cpu看到的顺序都是符合一个全局的顺序{3,1,4,2}，而各个CPU并没有能够观察到全部的中间过程，但是没
有关系，至少各个cpu观察的结果和那个全局顺序是一致的（consistent）。如果cpu
1看到的序列是{2,1}，那么就不存在一个一致性的全局顺序了，也就不是coherent order了。

（5）原文定义使用了“byte in memory”，实际上我的理解是要求内存访问是原子操作的，对于ARM体系，只有byte的访问是always保证是原子性的（single-copy atomicity），因此使用了byte这样的内存操作特例。

2、Single-copy atomicity

Single-copy atomicity英文原文定义如下：

> A read or write operation is single-copy atomic only if it meets the following conditions:   
> 1. For a single-copy atomic store, if the store overlaps another single-copy atomic store, then all of the writes from one of the stores are inserted into the Coherence order of each overlapping byte before any of the writes of the other store are inserted into the Coherence orders of the overlapping bytes.   
> 2. If a single-copy atomic load overlaps a single-copy atomic store and for any of the overlapping bytes the load returns the data written by the write inserted into the Coherence order of that byte by the single-copy atomic store then the load must return data from a point in the Coherence order no earlier than the writes inserted into the Coherence order by the single-copy atomic store of all of the overlapping bytes.

基本上来说，工程师可以知道上面这段话的每一个单词的含义，但是组合起来就是不知道这段话表达什么意思，为了方便理解，我们首先对几个单词进行解析：

（1）首先解释Coherence order ，就是上一章描述coherent时候的那个被所有observer观察到的全局的，一致的写入动作序列。

（2）对overlap的解释。基本上一个指令overlap另外一个指令其实就是说这两条指令被同时执行的意思。而“overlapping byte”则指内存操作有重叠的部分。例如加载0x000地址的4-Byte到寄存器和加载0x02地址2-Byte有2个字节的重叠。

（3）single-copy中copy到底是什么意思呢？我的理解是这样的：当PE访问内存的时候，例如load指令，这时候会有数据从memory copy到寄存器的动作，如果该指令的内存访问只会触发一次copy的动作，那么就是single-copy。对于加载奇数地址开始的2Byte load指令，其实该指令实际在执行的时候会触发两次的copy动作，那么就不是single-copy，而是multi-copy的（注意：这里的multi-copy并非Multi-copy atomicity中的Multi-copy，后文会描述）。

（4）“all of the writes from one of the stores ”这里all of the writes是指本次store操作中所涉及的每一个bit，这些bits是一个不可分隔的整体，插入到Coherence order操作序列中

理解了上面的几个英文单词之后，我们来看看整段的英文表述。整段表述分成两个部分，第一部分描述store overlap store，第二部分描述的是load overlap store。对于store overlap store而言，每一个store操作的bits都是不可分割的整体，而这个store连同其操作的所有bits做为一个原子的、不可被打断的操作，插入到Coherence order操作序列中。当然，插入时机也很重要，不能随便插入，不能在其他store中的中间过程中插入。如果操作的bits有交叠，例如有8个bit在A B两个store操作中都有涉及，那么这8个比特要么是A store的结果，要么是B store的结果，不能是一个综合A B store操作的结果。

理解了store overlap store之后，load overlap store就很容易了。它主要是从其他观察者的角度看：如果load和store操作的memory区域有交叠，那么那些交叠区域的返回值（对load操作而言）要么是全部bit被store写入，要么没有任何写入，不会是一个中间结果。

3、Multi-copy atomicity

Multi-copy atomicity英文原文定义如下：

> In a multiprocessing system, writes to a memory location are multi-copy atomic if the following conditions are both true:   
> 1、All writes to the same location are serialized, meaning they are observed in the same order by all observers, although some observers might not observe all of the writes.   
> 2、A read of a location does not return the value of a write until all observers observe that write.

Single-copy atomicity描述的是内存访问指令操作的原子性，而Multi-copy atomicity定义的是multiprocessing 环境下，多个store操作的顺序问题以及多个observer之间的交互问题，因此Single-copy atomicity和Multi-copy atomicity定义的内容是不一样的，或者说Multi-copy atomicity并不是站在Single-copy atomicity的对立面，它们就是不同的东西而已。那么，你可能会问：到底Multi-copy atomicity中的Multi-copy是什么意思呢？我理解是这样的：系统中有多个CPU core，每一个core都可以对内存系统中的某个特定的地址发起写入操作，系统中有n个CORE，那么就有可能有n个寄存器到memory的copy动作。

对Multi-copy atomicity的定义解释倒是比较简单：

（1）系统中对同一个地址的memory的store操作是串行化的，也就是说，对于所有的observer而言，它们观察到的写入操作顺序就是相同的一个序列。这个串行化要求比较狠，高于coherent的要求，也就是说，如果系统中的write操作不是coherent的，那么也就是不是Multi-copy atomicity的。

（2）对一个地址进行的load操作会被block，直到该地址的值对所有的observer都是可见的。

显然，根据定义，Multi-copy atomicity要求比较严格，对cpu performance伤害很大。

四、ARMv8的规则

1、Single-copy atomicity

显示内存访问（通过load或者store指令进行的内存访问）的规则如下：

（1）对齐的load或者store操作是Single-copy atomicity的。针对byte的内存操作总是Single-copy atomicity的，2B的load或者store操作如果地址对齐在2上，那么也是Single-copy atomicity的。其他的可以以此类推。

（2）Load Pair和Store Pair指令不是Single-copy atomicity的，但是可以被分拆成2个Single-copy atomicity指令。

（3）Load-Exclusive Pair（加载2个32-bit）指令和Store-Exclusive Pair（写入2个32-bit数据）指令是Single-copy atomicity的

（4）……更多的规则可以参考ARM ARM，这里不再描述。

2、Multi-copy atomicity规则如下：

（1）对于normal memory，写入操作不需要具备Multi-copy atomicity的特性。

（2）如果是Device类型的memory，并且具备non-Gathering的属性，所有符合Single-copy atomicity要求的write操作指令也都是Multi-copy atomicity的

（3）如果是Device类型的memory，并且具备Gathering的属性，写入操作不需要具备Multi-copy atomicity的特性。

五、参考文献

[1] ARMv8 Architecture Reference Manual

原创文章，转发请注明出处。蜗窝科技，[www.wowotech.net](/)。

Changelog：

2016-5-18：自己重新review了整份文档，让文档的表述更合理一些。
