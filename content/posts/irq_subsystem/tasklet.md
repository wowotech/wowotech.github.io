---
title: "linux kernel的中断子系统之（九）：tasklet"
date: 2015-07-02T18:10:49+08:00
url: "/irq_subsystem/tasklet.html"
gid: "197"
emlog_type: "blog"
summary: "对于中断处理而言，linux将其分成了两个部分，一个叫做中断handler（top half），属于不那么紧急需要处理的事情被推迟执行，我们称之deferable task，或者叫做bottom half，。具体如何推迟执行分成下面几种情况： 1、推迟到top half执行完毕 2、推迟到某个指定的时间片（例如40ms）之后执行 3、推迟到某个内核线程被调度的时候执行 对于第一种情况，内核中的机制"
author: "linuxer"
category: "中断子系统"
category_alias: "irq_subsystem"
tags: ["tasklet"]
views: 46129
comment_count: 12
aliases:
  - "/irq_subsystem/197.html"
  - "/197.html"
---

一、前言

对于中断处理而言，linux将其分成了两个部分，一个叫做中断handler（top half），属于不那么紧急需要处理的事情被推迟执行，我们称之deferable task，或者叫做bottom half，。具体如何推迟执行分成下面几种情况：

1、推迟到top half执行完毕

2、推迟到某个指定的时间片（例如40ms）之后执行

3、推迟到某个内核线程被调度的时候执行

对于第一种情况，内核中的机制包括[softirq机制](/irq_subsystem/soft-irq.html#2107)和tasklet机制。第二种情况是属于softirq机制的一种应用场景（timer类型的softirq），在本站的时间子系统的系列文档中会描述。第三种情况主要包括threaded irq handler以及通用的workqueue机制，当然也包括自己创建该驱动专属kernel thread（不推荐使用）。本文主要描述tasklet这种机制，第二章描述一些背景知识和和tasklet的思考，第三章结合代码描述tasklet的原理。

注：本文中的linux kernel的版本是4.0

二、为什么需要tasklet？

1、基本的思考

我们的驱动程序或者内核模块真的需要tasklet吗？每个人都有自己的看法。我们先抛开linux kernel中的机制，首先进行一番逻辑思考。

将中断处理分成top half（cpu和外设之间的交互，获取状态，ack状态，收发数据等）和bottom half（后段的数据处理）已经深入人心，对于任何的OS都一样，将不那么紧急的事情推迟到bottom half中执行是OK的，具体如何推迟执行分成两种类型：有具体时间要求的（对应linux kernel中的低精度timer和高精度timer）和没有具体时间要求的。对于没有具体时间要求的又可以分成两种：

（1）越快越好型，这种实际上是有性能要求的，除了中断top half可以抢占其执行，其他的进程上下文（无论该进程的优先级多么的高）是不会影响其执行的，一言以蔽之，在不影响中断延迟的情况下，OS会尽快处理。

（2）随遇而安型。这种属于那种没有性能需求的，其调度执行依赖系统的调度器。

本质上讲，越快越好型的bottom half不应该太多，而且tasklet的callback函数不能执行时间过长，否则会产生进程调度延迟过大的现象，甚至是非常长而且不确定的延迟，对real time的系统会产生很坏的影响。

2、对linux中的bottom half机制的思考

在linux kernel中，“越快越好型”有两种，softirq和tasklet，“随遇而安型”也有两种，workqueue和threaded irq handler。“越快越好型”能否只留下一个softirq呢？对于崇尚简单就是美的程序员当然希望如此。为了回答这个问题，我们先看看tasklet对于softirq而言有哪些好处：

（1）tasklet可以动态分配，也可以静态分配，数量不限。

（2）同一种tasklet在多个cpu上也不会并行执行，这使得程序员在撰写tasklet function的时候比较方便，减少了对并发的考虑（当然损失了性能）。

对于第一种好处，其实也就是为乱用tasklet打开了方便之门，很多撰写驱动的软件工程师不会仔细考量其driver是否有性能需求就直接使用了tasklet机制。对于第二种好处，本身考虑并发就是软件工程师的职责。因此，看起来tasklet并没有引入特别的好处，而且和softirq一样，都不能sleep，限制了handler撰写的方便性，看起来其实并没有存在的必要。在4.0 kernel的代码中，grep一下tasklet的使用，实际上是一个很长的列表，只要对这些使用进行简单的归类就可以删除对tasklet的使用。对于那些有性能需求的，可以考虑并入softirq，其他的可以考虑使用workqueue来取代。Steven Rostedt试图进行这方面的尝试（[http://lwn.net/Articles/239484/](http://lwn.net/Articles/239484/ "http://lwn.net/Articles/239484/")），不过这个patch始终未能进入main line。

三、tasklet的基本原理

1、如何抽象一个tasklet

内核中用下面的数据结构来表示tasklet：

> struct tasklet\_struct   
> {   
> struct tasklet\_struct \*next;   
> unsigned long state;   
> atomic\_t count;   
> void (\*func)(unsigned long);   
> unsigned long data;   
> };

每个cpu都会维护一个链表，将本cpu需要处理的tasklet管理起来，next这个成员指向了该链表中的下一个tasklet。func和data成员描述了该tasklet的callback函数，func是调用函数，data是传递给func的参数。state成员表示该tasklet的状态，TASKLET\_STATE\_SCHED表示该tasklet以及被调度到某个CPU上执行，TASKLET\_STATE\_RUN表示该tasklet正在某个cpu上执行。count成员是和enable或者disable该tasklet的状态相关，如果count等于0那么该tasklet是处于enable的，如果大于0，表示该tasklet是disable的。在[softirq文档](/irq_subsystem/soft-irq.html#2117)中，我们知道local\_bh\_disable/enable函数就是用来disable/enable bottom half的，这里就包括softirq和tasklet。但是，有的时候内核同步的场景不需disable所有的softirq和tasklet，而仅仅是disable该tasklet，这时候，tasklet\_disable和tasklet\_enable就派上用场了。

> static inline void tasklet\_disable(struct tasklet\_struct \*t)   
> {   
> tasklet\_disable\_nosync(t);－－－－－－－给tasklet的count加一   
> tasklet\_unlock\_wait(t);－－－－－如果该tasklet处于running状态，那么需要等到该tasklet执行完毕   
> smp\_mb();   
> }
>
> static inline void tasklet\_enable(struct tasklet\_struct \*t)   
> {   
> smp\_mb\_\_before\_atomic();   
> atomic\_dec(&t->count);－－－－－－－给tasklet的count减一   
> }

tasklet\_disable和tasklet\_enable支持嵌套，但是需要成对使用。

2、系统如何管理tasklet？

系统中的每个cpu都会维护一个tasklet的链表，定义如下：

> static DEFINE\_PER\_CPU(struct tasklet\_head, tasklet\_vec);   
> static DEFINE\_PER\_CPU(struct tasklet\_head, tasklet\_hi\_vec);

linux kernel中，和tasklet相关的softirq有两项，HI\_SOFTIRQ用于高优先级的tasklet，TASKLET\_SOFTIRQ用于普通的tasklet。对于softirq而言，优先级就是出现在softirq pending register（\_\_softirq\_pending）中的先后顺序，位于bit 0拥有最高的优先级，也就是说，如果有多个不同类型的softirq同时触发，那么执行的先后顺序依赖在softirq pending register的位置，kernel总是从右向左依次判断是否置位，如果置位则执行。HI\_SOFTIRQ占据了bit 0，其优先级甚至高过timer，需要慎用（实际上，我grep了内核代码，似乎没有发现对HI\_SOFTIRQ的使用）。当然HI\_SOFTIRQ和TASKLET\_SOFTIRQ的机理是一样的，因此本文只讨论TASKLET\_SOFTIRQ，大家可以举一反三。

3、如何定义一个tasklet？

你可以用下面的宏定义来静态定义tasklet：

> #define DECLARE\_TASKLET(name, func, data) \   
> struct tasklet\_struct name = { NULL, 0, ATOMIC\_INIT(0), func, data }
>
> #define DECLARE\_TASKLET\_DISABLED(name, func, data) \   
> struct tasklet\_struct name = { NULL, 0, ATOMIC\_INIT(1), func, data }

这两个宏都可以静态定义一个struct tasklet\_struct的变量，只不过初始化后的tasklet一个是处于eable状态，一个处于disable状态的。当然，也可以动态分配tasklet，然后调用tasklet\_init来初始化该tasklet。

4、如何调度一个tasklet

为了调度一个tasklet执行，我们可以使用tasklet\_schedule这个接口：

> static inline void tasklet\_schedule(struct tasklet\_struct \*t)   
> {   
> if (!test\_and\_set\_bit(TASKLET\_STATE\_SCHED, &t->state))   
> \_\_tasklet\_schedule(t);   
> }

程序在多个上下文中可以多次调度同一个tasklet执行（也可能来自多个cpu core），不过实际上该tasklet只会一次挂入首次调度到的那个cpu的tasklet链表，也就是说，即便是多次调用tasklet\_schedule，实际上tasklet只会挂入一个指定CPU的tasklet队列中（而且只会挂入一次），也就是说只会调度一次执行。这是通过TASKLET\_STATE\_SCHED这个flag来完成的，我们可以用下面的图片来描述：

[![tasklet](/content/uploadfile/201507/2f814e61e193b5a0a694ef3673b4f60620150702100946.gif "tasklet")](/content/uploadfile/201507/06299a79874281afa05198f9d72a87da20150702100845.gif)

我们假设HW block A的驱动使用的tasklet机制并且在中断handler（top half）中将静态定义的tasklet（这个tasklet是各个cpu共享的，不是per cpu的）调度执行（也就是调用tasklet\_schedule函数）。当HW block A检测到硬件的动作（例如接收FIFO中数据达到半满）就会触发IRQ line上的电平或者边缘信号，GIC检测到该信号会将该中断分发给某个CPU执行其top half handler，我们假设这次是cpu0，因此该driver的tasklet被挂入CPU0对应的tasklet链表（tasklet\_vec）并将state的状态设定为TASKLET\_STATE\_SCHED。HW block A的驱动中的tasklet虽已调度，但是没有执行，如果这时候，硬件又一次触发中断并在cpu1上执行，虽然tasklet\_schedule函数被再次调用，但是由于TASKLET\_STATE\_SCHED已经设定，因此不会将HW block A的驱动中的这个tasklet挂入cpu1的tasklet链表中。

下面我们再仔细研究一下底层的\_\_tasklet\_schedule函数：

> void \_\_tasklet\_schedule(struct tasklet\_struct \*t)   
> {   
> unsigned long flags;
>
> local\_irq\_save(flags);－－－－－－－－－－－－－－－－－－－（1）   
> t->next = NULL;－－－－－－－－－－－－－－－－－－－－－（2）   
> \*\_\_this\_cpu\_read(tasklet\_vec.tail) = t;   
> \_\_this\_cpu\_write(tasklet\_vec.tail, &(t->next));   
> raise\_softirq\_irqoff(TASKLET\_SOFTIRQ);－－－－－－－－－－（3）   
> local\_irq\_restore(flags);   
> }

（1）下面的链表操作是per-cpu的，因此这里禁止本地中断就可以拦截所有的并发。

（2）这里的三行代码就是将一个tasklet挂入链表的尾部

（3）raise TASKLET\_SOFTIRQ类型的softirq。

5、在什么时机会执行tasklet？

上面描述了tasklet的调度，当然调度tasklet不等于执行tasklet，系统会在适合的时间点执行tasklet callback function。由于tasklet是基于softirq的，因此，我们首先总结一下softirq的执行场景：

（1）在中断返回用户空间（进程上下文）的时候，如果有pending的softirq，那么将执行该softirq的处理函数。这里限定了中断返回用户空间也就是意味着限制了下面两个场景的softirq被触发执行：

（a）中断返回hard interrupt context，也就是中断嵌套的场景

（b）中断返回software interrupt context，也就是中断抢占软中断上下文的场景

（2）上面的描述缺少了一种场景：中断返回内核态的进程上下文的场景，这里我们需要详细说明。进程上下文中调用local\_bh\_enable的时候，如果有pending的softirq，那么将执行该softirq的处理函数。由于内核同步的要求，进程上下文中有可能会调用local\_bh\_enable/disable来保护临界区。在临界区代码执行过程中，中断随时会到来，抢占该进程（内核态）的执行（注意：这里只是disable了bottom half，没有禁止中断）。在这种情况下，中断返回的时候是否会执行softirq handler呢？当然不会，我们disable了bottom half的执行，也就是意味着不能执行softirq handler，但是本质上bottom half应该比进程上下文有更高的优先级，一旦条件允许，要立刻抢占进程上下文的执行，因此，当立刻离开临界区，调用local\_bh\_enable的时候，会检查softirq pending，如果bottom half处于enable的状态，pending的softirq handler会被执行。

（3）系统太繁忙了，不过的产生中断，raise softirq，由于bottom half的优先级高，从而导致进程无法调度执行。这种情况下，softirq会推迟到softirqd这个内核线程中去执行。

对于TASKLET\_SOFTIRQ类型的softirq，其handler是tasklet\_action，我们来看看各个tasklet是如何执行的：

> static void tasklet\_action(struct softirq\_action \*a)   
> {   
> struct tasklet\_struct \*list;
>
> local\_irq\_disable();－－－－－－－－－－－－－－－－－－－－－－－－－－（1）   
> list = \_\_this\_cpu\_read(tasklet\_vec.head);   
> \_\_this\_cpu\_write(tasklet\_vec.head, NULL);   
> \_\_this\_cpu\_write(tasklet\_vec.tail, this\_cpu\_ptr(&tasklet\_vec.head));   
> local\_irq\_enable();
>
> while (list) {－－－－－－－－－遍历tasklet链表   
> struct tasklet\_struct \*t = list;
>
> list = list->next;
>
> if (tasklet\_trylock(t)) {－－－－－－－－－－－－－－－－－－－－－－－（2）   
> if (!atomic\_read(&t->count)) {－－－－－－－－－－－－－－－－－－（3）   
> if (!test\_and\_clear\_bit(TASKLET\_STATE\_SCHED, &t->state))   
> BUG();   
> t->func(t->data);   
> tasklet\_unlock(t);   
> continue;－－－－－处理下一个tasklet   
> }   
> tasklet\_unlock(t);－－－－清除TASKLET\_STATE\_RUN标记   
> }
>
> local\_irq\_disable();－－－－－－－－－－－－－－－－－－－－－－－（4）   
> t->next = NULL;   
> \*\_\_this\_cpu\_read(tasklet\_vec.tail) = t;   
> \_\_this\_cpu\_write(tasklet\_vec.tail, &(t->next));   
> \_\_raise\_softirq\_irqoff(TASKLET\_SOFTIRQ); －－－－－－再次触发softirq，等待下一个执行时机   
> local\_irq\_enable();   
> }   
> }

（1）从本cpu的tasklet链表中取出全部的tasklet，保存在list这个临时变量中，同时重新初始化本cpu的tasklet链表，使该链表为空。由于bottom half是开中断执行的，因此在操作tasklet链表的时候需要使用关中断保护

（2）tasklet\_trylock主要是用来设定该tasklet的state为TASKLET\_STATE\_RUN，同时判断该tasklet是否已经处于执行状态，这个状态很重要，它决定了后续的代码逻辑。

> static inline int tasklet\_trylock(struct tasklet\_struct \*t)   
> {   
> return !test\_and\_set\_bit(TASKLET\_STATE\_RUN, &(t)->state);   
> }

你也许会奇怪：为何这里从tasklet的链表中摘下一个本cpu要处理的tasklet list，而这个list中的tasklet已经处于running状态了，会有这种情况吗？会的，我们再次回到上面的那个软硬件结构图。同样的，HW block A的驱动使用的tasklet机制并且在中断handler（top half）中将静态定义的tasklet 调度执行。HW block A的硬件中断首先送达cpu0处理，因此该driver的tasklet被挂入CPU0对应的tasklet链表并在适当的时间点上开始执行该tasklet。这时候，cpu0的硬件中断又来了，该driver的tasklet callback function被抢占，虽然tasklet仍然处于running状态。与此同时，HW block A硬件又一次触发中断并在cpu1上执行，这时候，该driver的tasklet处于running状态，并且TASKLET\_STATE\_SCHED已经被清除，因此，调用tasklet\_schedule函数将会使得该driver的tasklet挂入cpu1的tasklet链表中。由于cpu0在处理其他硬件中断，因此，cpu1的tasklet后发先至，进入tasklet\_action函数调用，这时候，当从cpu1的tasklet摘取所有需要处理的tasklet链表中，HW block A对应的tasklet实际上已经是在cpu0上处于执行状态了。

我们在设计tasklet的时候就规定，同一种类型的tasklet只能在一个cpu上执行，因此tasklet\_trylock就是起这个作用的。

（3）检查该tasklet是否处于enable状态，如果是，说明该tasklet可以真正进入执行状态了。主要的动作就是清除TASKLET\_STATE\_SCHED状态，执行tasklet callback function。

（4）如果该tasklet已经在别的cpu上执行了，那么我们将其挂入该cpu的tasklet链表的尾部，这样，在下一个tasklet执行时机到来的时候，kernel会再次尝试执行该tasklet，在这个时间点，也许其他cpu上的该tasklet已经执行完毕了。通过这样代码逻辑，保证了特定的tasklet只会在一个cpu上执行，不会在多个cpu上并发。

*原创文章，转发请注明出处。蜗窝科技*
