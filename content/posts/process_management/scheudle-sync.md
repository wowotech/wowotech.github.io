---
title: "进程切换分析（3）：同步处理"
date: 2017-12-11T17:59:34+08:00
url: "/process_management/scheudle-sync.html"
gid: "416"
emlog_type: "blog"
summary: "本文主要描述了主调度器（schedule函数）中的同步处理。"
author: "linuxer"
category: "进程管理"
category_alias: "process_management"
tags: ["schedule"]
views: 19040
comment_count: 7
aliases:
  - "/process_management/416.html"
  - "/416.html"
---

一、前言

本文主要描述了主调度器（schedule函数）中的同步处理。

二、进程调度简介

进程切换有两种，一种是当进程由于需要等待某种资源而无法继续执行下去，这时候只能是主动将自己挂起（调用schedule函数），引发一次任务调度过程。另外一种是进程被抢占。所谓抢占（preempt）就是在当前进程欢快执行的时候，终止其对CPU资源的占用，切换到另外一个更高优先级的进程执行。进程被抢占往往是由于各种调度事件的发生：

1、 时间片用完

2、 在中断上下文中唤醒其他优先级更高的进程

3、 在其他进程上下文中唤醒其他优先级更高的进程。

4、 在其他进程上下文中修改了其他进程的调度参数

5、 ……

在当前进程被抢占的场景下，调度并不是立刻发生，而是延迟执行，具体的方法是设定当前进程的need\_resched等于1，然后静静的等待最近一个调度点的来临，当调度点到来的时候，内核会调用schedule函数，抢占当前task的执行。

此外，我们还需要了解基本的抢占控制的知识。在一个进程的thread info中有一个preempt\_count的成员用来控制抢占，当该成员等于0的时候表示允许抢占，在本文中，我们分别用preempt counter、hardirq counter和softirq counter分别表示其中的bit field。更详细的描述可以参考[相关文档](/irq_subsystem/soft-irq.html)的描述

三、schedule函数使用了哪些同步机制

schedule函数的代码框架如下：

> asmlinkage \_\_visible void \_\_sched schedule(void)   
> {   
> do {   
> preempt\_disable();－－－－－－－－－－－－－－－－－a
>
> **raw\_spin\_lock\_irq(&rq->lock);－－－－－－－－b**
>
> 选择next task
>
> 切到next task执行
>
> **raw\_spin\_unlock\_irq(&rq->lock);** －－－－－－－c   
> sched\_preempt\_enable\_no\_resched(); －－－－－－－－d   
> } while (need\_resched()); －－－－－－－－－－－－－－－e   
> }

我们以X进程切换到Y进程为例，描述schedule函数中同步机制的使用情况。在X进程上下文中，a点首先关闭了抢占，X task的preempt counter会加1。然后在b点会持有该CPU runqueue的spinlock，当然在这个过程中会disable CPU中断处理，同时将X task的preempt counter再次加1，这时候X task的preempt counter应该等于2。

打开X task的抢占的时候是在重新调度X在某个CPU上执行的时候，这时候，在上面代码中的c和d点来递减preempt counter，当进入e点的时候，preempt counter已经等于0。

由于在切换过长设计runqueue队列的操作，因此需要spin lock来保护。不过在进程切换过程中，runqueue spin lock是不同进程来协同处理的。我们仍然以X进程切换到Y进程为例。在X进程中，在b点持锁并disable了本地中断，而spin lock的释放是在Y进程中完成的（c点），在释放spin lock的同时，也会打开cpu中断。

四、可不可以禁止抢占的时候调用schedule函数

在进程上下文中，下面的调用序列是否可以呢？

> preempt\_disable
>
> ……schedule……
>
> preempt\_enable

无论什么场景，disable preempt然后调用schedule都是很奇怪的一件事情：本来你已经禁止抢占了，但是又显示的调用schedule函数，你这不是精神分裂吗？schedule函数怎么处理这个精神分裂的task呢？在调用schedule函数之前，它毫无疑问是期待preempt count等于0的，只有当前task的preempt count等于0才说明抢占的合理性。不过在整个进程切换的过程中，首先会在a点禁止抢占，这样可以确保CPU和当前task之间的关系不变（cpu不变、current task不变，runqueue不变）。这样，在a和b之间的对caller的调用检查就比较好开展了，具体如下：

> static inline void schedule\_debug(struct task\_struct \*prev)   
> {
>
> if (unlikely(in\_atomic\_preempt\_off())) {   
> \_\_schedule\_bug(prev);   
> preempt\_count\_set(PREEMPT\_DISABLED);   
> }   
> }

in\_atomic\_preempt\_off这个宏就是对当前preempt count进行测试，这时候正确的preempt counter应该是等于1，其他的bit field，例如softirq counter、hardirq count等都是0。具体关于preempt count的位域描述可以参考本站[软中断的文档](/irq_subsystem/soft-irq.html)。如果没有设定正确的preempt\_count就调用schedule函数，那么说明在atomic上下文中错误的进行了调度，\_\_schedule\_bug会打印出相关信息，方便调试。

虽然在错误的场景中调用了schedule函数，但是内核还是要艰难前行啊，因此这里会修改preempt count的值为PREEMPT\_DISABLED，而这才是进入schedule函数正确的姿势。

五、可不可以关闭中断调用schedule函数？

在进程上下文中，下面的调用序列是否可以呢？

> local\_irq\_disable
>
> ……schedule……
>
> local\_irq\_enable

当然这里也许不是直接调用schedule函数，很多内核接口API会隐含调用schedule函数，因此也许你会有意无意的写出上面形态的代码。

首先需要明确一点：从X进程切换到Y进程的时候，如果在X进程中关闭中断，然后切换到Y进程，如果中断不恢复的话，那么Y进程会一直执行，直到Y自己良心发现，让出CPU。这当然是不被允许的。因此，在调用schedule进行进程切换的时候，无论调用者是否关闭中断，在b点都会关闭中断（注意，这时候并没有记录之前的中断状态）。而在切入到Y进程之后，在c点都会显式的打开CPU中断。因此，上面的代码虽然不推荐，但是也不会对调度产生太大的影响。

六、禁止中断是否可以禁止抢占？

禁止了中断的确等于了禁止抢占，但是并不意味着它们两个完全等同，因为在preempt disable－－－preempt enable这个的调用过程中，在打开抢占的时候有一个抢占点，内核控制路径会在这里检查抢占，如果满足抢占条件，那么会立刻调度schedule函数进行进程切换，但是local irq disable－－－local irq enable的调用中，并没有显示的抢占检查点，当然，中断有点特殊，因为一旦打开中断，那么pending的中断会进来，并且在返回中断点的时候会检查抢占，但是也许下面的这个场景就无能为力了。进程上下文中调用如下序列：

（1）local irq disable

（2）wake up high level priority task

（3）local irq enable

当唤醒的高优先级进程被调度到本CPU执行的时候，按理说这个高优先级进程应该立刻抢占当前进程，但是这个场景无法做到。在调用try\_to\_wake\_up的时候会设定need resched flag并检查抢占，但是由于中断disable，因此不会立刻调用schedule，但是在step （3）的时候，由于没有检查抢占，这时候本应立刻抢占的高优先级进程会发生严重的调度延迟.....直到下一个抢占点到来。

*原创文章，转发请注明出处。蜗窝科技*
