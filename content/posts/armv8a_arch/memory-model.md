---
title: "ARMv8之memory model"
date: 2016-05-18T12:09:13+08:00
url: "/armv8a_arch/memory-model.html"
gid: "296"
emlog_type: "blog"
summary: "从阅读ARMv8手册的第一天起，我就饱受memory order、memory barrier、coherent、consistency等概念的残害，各种痛苦，各种迷茫，各种试图放弃，各种欲罢不能……，现在，终于收拾心情，再 次出发，希望这次能把近期关于ARMv8上的memory model相关的知识点整理出来，让自己更清楚一些，也顺便希望能够和大家一起探讨。 本文主要关注shared-memor"
author: "linuxer"
category: "ARMv8A Arch"
category_alias: "armv8a_arch"
tags: ["Model", "ARMv8", "sequential", "consistency", "relaxed"]
views: 21870
comment_count: 7
aliases:
  - "/armv8a_arch/296.html"
  - "/296.html"
---

一、前言

从阅读ARMv8手册的第一天起，我就饱受memory order、memory barrier、coherent、consistency等概念的残害，各种痛苦，各种迷茫，各种试图放弃，各种欲罢不能……，现在，终于收拾心情，再次出发，希望这次能把近期关于ARMv8上的memory model相关的知识点整理出来，让自己更清楚一些，也顺便希望能够和大家一起探讨。

本文主要关注shared-memory system，其他的系统不在本文的考虑范围。

二、什么是memory model？

想要理解ARMv8的memory model，首先需要知道什么是memory model，或者说memory consistency model。

当cpu从memory中的某个位置发起一次读操作的时候，该操作的返回值应该是什么样子的呢？对于程序员，直觉就是当然返回上次写入的数值了。不过，怎么定义“上次”呢？对于单核的执行环境，“上次”比较容易定义，从program order中可以轻易的得出上一次对该地址的写入操作。对于share-memory的多核环境而言，如何定义“上次”呢？那么多Hardware Thread在并发执行程序（每个cpu core上都有自己的指令流，都有自己的program order），想找出“上次”还不是一个显而易见的事情啊（当从两个不同CPU core上发起了对同一个memory location的访问，谁先谁后是无法通过program order来定义的）。为了搞清楚这个问题，我们必须要引入memory consistency model这个概念。所谓memory consistency model，其实就是就是定义系统中对内存访问需要遵守的规则（本质上就是read操作返回什么样的值），了解了这些规则，软件和硬件才能和谐工作，软件工程师才能写出逻辑正确的程序。

memory consistency model的规则影响了一大票人：使用高级语言的程序员、写编译器的软件工程师、CPU设计人员。做为一个程序员，一个有情怀的c程序员，我期望的memory model符合c语言的基本逻辑，内存操作是按照c程序中的program order进行的，而且是有序的进行，符合c程序的逻辑推导的，一言以蔽之，程序员当然希望能够编程简单，不要考虑什么memory order啊，memory barrier什么的。不过，从系统设计人员的角度看呢，需要找到一个各方面都OK的memory model。你看，系统设计人员就是高瞻远瞩啊，可以从多方面考虑，在性能和编程易用性方面平衡。

三、什么是sequential consistency？

我们从ARMv8的手册中知道它的memory consistency model是属于Relaxed Memory Consistency Models，这里的“Relaxed”是针对sequential consistency而言的，因此我们先解释什么是sequential consistency，定义如下：

> “the result of any execution is the same as if the operations of all the processors were executed in some sequential order, and the operations of each individual processor appear in this sequence in the order specified by its program”.

通俗的讲，如果shared memory multicore系统符合sequential consistency模型，那么在多个cpu core上执行的程序就好象在一个单一cpu core上顺序执行一样。例如如果系统有两个cpu，分别是core 0和core 1，core 0执行了A B C D内存访问指令，core 1执行了a b c d内存访问指令，对于程序员而言，sequential consistency的系统上执行这8条指令的效果就好象在一个core上顺序执行了A a B b C c D d的指令流。当然，上面只是给出一个示例的程序执行流，实际上也可以是A B a b C c D d，也可以是A B C D a b c d，也可以是……只要你熟悉排列组合的原理，就能把所有可能的顺序罗列出来。当然，也不是任意的排组合都OK，因为这个综合效果的指令流必须符合core 0的program order（即单独从core 0的角度看，其program order必须是A->B->C->D），必须符合core 1的program order（即单独从core 1的角度看，其program order必须是a->b->c->d）。我们可以总结sequential consistency模型的两条规则：

（1）各个cpu core按照其program order来执行程序，执行完一条，然后启动下一条指令的执行，不会有local reordering。为了理解这条规则，我们来看看著名的Dekker algorithm，代码如下：

|  |  |
| --- | --- |
| core 0 | core 1 |
| flag0 = 1;    if (flag1 == 0)    enter critical section | flag1 = 1;    if (flag0 == 0)    enter critical section |

上面代码的初始条件是flag0 = flag1 = 0。在core 0上，当想要进入临界区的时候，会设定flag0等于1，并且判断flag1的值是否等于0，如果等于0，则说明core 1没有进入临界区，还没有执行flag1＝1这一条指令，同时也就隐含了flag0=1的赋值已经执行完毕。对于sequential consistency模型，各个CPU core能够保证自己的local program order被严格执行，从而保证了不会有多个thread同时进入临界区。

（2）从全局来看，每一个写的操作，都被系统中的所有cpu core同时感知到。注意上面句子中的“同时”，这也就意味着cpu 系统（包括所有的cpu core们）和存储系统之间有一个开关，一次只会连接一个CPU core和存储系统，因此对memory的访问都是原子的、串行化的。例如：某个cpu core对某个内存操作进行write操作，该操作完成之后，那个开关才会放下一个内存操作进入存储系统。我们用下面的代码示例来解释这一条规则：

|  |  |  |
| --- | --- | --- |
| core 0 | core 1 | core 2 |
| A = 1; | if (A == 1)    B = 1; | if (B == 1)    load A |

上面代码的初始条件是A = B = 0。对于sequential consistency模型，我们可以进行下面的推导：对于core 1，如果该处理器执行了B=1的赋值语句的时候，说明core 1已经感知到了core 0上对A变量的write操作，因此core 2必须也知道了A等于1这个事实。因此，在core 2上执行load A操作的时候，这时候A值必须要等于1。

程序员当然喜欢简单、直观的sequential consistency模型，但是，这也限制了CPU硬件和编译器的优化，从而影响了整个系统的性能。怎么办？答案是显而易见的，云计算、大数据等等这些真实用户的需求（要求更好的performance）无情的碾压了程序员的“小确幸”，因此，骚年们，直面“惨淡的人生”吧，这也就是relaxed consistency model。

四、什么是relaxed consistency model?

通过上一节，我们了解到sequential consistency模型中的各种要求，这些对内存操作顺序的要求实际上是对性能的限制和束缚，为了性能，能不能放松（relax）这些要求呢？当然没有问题，否则也就不会有relaxed consistency model的商业化应用了。这些发送内存操作的要求可以被分成两个类别：

（1）CPU core是否可以不按照program order的顺序来执行代码？进一步又可以分成RAW（Read after Write），WAW（write after write）和WAR（write after read）三种情况。需要特别强调的是这些内存操作对（RW，WR或者WW）必须操作不同的memory location，否则，这些操作是有数据依赖关系，CPU必须保证起操作顺序，否则在单CPU core上的程序逻辑就不对了。对于ARMv8而言，如果没有memory barrier指令，program order中的RAW，WAW和WAR的内存操作对都可以被reorder。

（2）CPU core的write操作是否必须是全局原子性的。对于sequential consistency，一个写的动作，会被其他CPU core同时观察到，即要么全部观察到新值，要么全部观察到旧值，不会有中间情况的存在。有的内存模型可以允许某个cpu core的read操作返回其他cpu core写入的新值，而其他的cpu core仍然观察到旧值。这里实际上说的是Multi-copy atomicity，对于ARMv8而言，normal memory的写入操作不具备Multi-copy atomicity的特性。

当然，无论如何的放松要求，下面的要求不能放松：

（1）在单核上，程序中的数据依赖和控制依赖必须保证，即有依赖关系的内存操作必须保证操作顺序，不能out of order。

（2）对同一地址的memory location的写入操作必须是串行化的。如果系统中有cache，那么需要cache coherence protocol来保证这一点。

五、参考文献

1、Computer Architecture, A Quantitative Approach 5th

2、Shared Memory Consistency Models: A Tutorial

3、Memory Consistency Models for Shared-Memory Multiprocessors

4、ARMv8 ARM

原创文章，转发请注明出处。蜗窝科技，[www.wowotech.net](/)。
