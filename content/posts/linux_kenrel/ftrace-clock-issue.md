---
title: "ftrace时间精度issue修复"
date: 2018-04-16T19:07:32+08:00
url: "/linux_kenrel/ftrace-clock-issue.html"
gid: "430"
emlog_type: "blog"
summary: "在调试ATMEL SAMA5D3 上的ftrace功能的时候，发现了一个时间精度的问题，本文主要记录这个issue修复的过程，方便后续查阅。linux内核版本是4.4.19，当然，最新的内核中仍然存在这个issue。"
author: "linuxer"
category: "Linux内核分析"
category_alias: "linux_kenrel"
tags: ["ftrace", "sched_clock"]
views: 20095
comment_count: 0
aliases:
  - "/linux_kenrel/430.html"
  - "/430.html"
---

一、前言

在调试ATMEL SAMA5D3 上的ftrace功能的时候，发现了一个时间精度的问题，本文主要记录这个issue修复的过程，方便后续查阅。linux内核版本是4.4.19，当然，最新的内核中仍然存在这个issue。

二、操作步骤

在通过irqsoff tracer跟踪最大中断延迟的时候发现了这个问题，具体操作步骤如下：

（1）挂载debugfs

|  |
| --- |
| # mount -t debugfs nodev /sys/kernel/debug |

（2）查看目前系统中已经内嵌的tracer

|  |
| --- |
| # cat /sys/kernel/debug/tracing/available\_tracers |

可能的输出是：wakeup wakeup\_rt preemptirqsoff preemptoff irqsoff function nop，这个和系统配置有关。这里我们将使用irqsoff这个tracer。

（3）查看当前的tracer

|  |
| --- |
| # cat /sys/kernel/debug/tracing/current\_tracer |

如果没有执行trace任务，那么一般是nop

（4）设定irqsoff是当前的tracer

|  |
| --- |
| # echo irqsoff > /sys/kernel/debug/tracing/current\_tracer |

当然可以通过step （3）中的命令来确定tracer设定情况。

（5）清除上次的max latency

|  |
| --- |
| # echo 0 > /sys/kernel/debug/tracing/tracing\_max\_latency |

（6）随后我们需要打开跟踪，将跟踪信息输入到ring buffer中：

|  |
| --- |
| # echo 1 > /sys/kernel/debug/tracing/tracing\_on |

这时候需要给系统一些负载，以便让最大中断延迟场景出现。

（7）关闭输出

|  |
| --- |
| # echo 0 > /sys/kernel/debug/tracing/tracing\_on |

（8）保存跟踪结果

|  |
| --- |
| # cat /sys/kernel/debug/tracing/trace > /tmp/trace.txt |

查阅/tmp/trace.txt文件并分析

（9）设定nop是当前的tracer

|  |
| --- |
| # echo nop > /sys/kernel/debug/tracing/current\_tracer |

三、问题的发现

/tmp/trace.txt文件如下：

> # tracer: irqsoff   
> #   
> # irqsoff latency trace v1.1.5 on 4.4.19   
> # --------------------------------------------------------------------   
> # latency: 10000 us, #441/441, CPU#0 | (M:server VP:0, KP:0, SP:0 HP:0)   
> # -----------------   
> # | task: swapper-0 (uid:0 nice:0 policy:0 rt\_prio:0)   
> # -----------------   
> # => started at: \_\_irq\_svc   
> # => ended at: \_\_do\_softirq   
> #   
> #   
> # \_------=> CPU#   
> # / \_-----=> irqs-off   
> # | / \_----=> need-resched   
> # || / \_---=> hardirq/softirq   
> # ||| / \_--=> preempt-depth   
> # |||| / delay   
> # cmd pid ||||| time | caller   
> # \ / ||||| \ | /   
> <...>-593 0d... 0us : do\_work\_pending   
> <...>-593 0d... 0us : do\_work\_pending   
> <...>-593 0d... 0us : trace\_hardirqs\_on <-do\_work\_pending
>
> ……
>
> -0 0d.h. 0us : tick\_handle\_periodic <-ch2\_irq   
> -0 0d.h. 0us : tick\_periodic.constprop.5 <-tick\_handle\_periodic   
> **-0 0d.h. 0us#: do\_timer <-tick\_periodic.constprop.5   
> -0 0d.h. 10000us : calc\_global\_load <-do\_timer**   
> -0 0d.h. 10000us : update\_wall\_time <-tick\_periodic.constprop.5   
> -0 0d.h. 10000us : tc\_get\_cycles32 <-update\_wall\_time
>
> ……

通过这个文件，我们可以看成跟踪到的最大中断延迟（最长的关闭中断的时间）是10000us，高达10ms的关中断时间，这有点离谱啊。不过还好后面有更详细的信息：header中的started at和ended at给出了关中断的函数区间，后面给出了详细的栈的回溯信息。这里有一个很奇怪的地方（上面黑色粗体的两行），时间戳在这两行中有一个跳变，从0之间跳变到了10000us，很显然，ftrace给出的时间戳精度不足。

四、寻找问题原因

ftrace中的时间戳信息是通过sched\_clock实现的，从名字也能看出来，这是调度器模块相关的函数，在调度器代码中（kernel/sched/clock.c）有一个弱符号定义：

> unsigned long long \_\_weak sched\_clock(void)   
> {   
> return (unsigned long long)(jiffies - INITIAL\_JIFFIES)   
> \* (NSEC\_PER\_SEC / HZ);   
> }

显然这是一个基于jiffies的clock，其精度和tick相关。在我们的系统中，HZ=100，每10ms产生一次tick，符合上面的观察：ftrace的时间戳精度是10ms。

当然，如果你嫌弃上面这个sched\_clock时间精度差，arch相关的代码可以自定义一个sched\_clock来代替上面这个调度器中的弱符号，显然，在ATMEL SAMA5D3的timer驱动中没有实现这个功能，从而使用了调度器模块中的那个弱符号的schec clock，从而导致了ftrace的时间精度问题。

五、问题的解决

既然如此，看来我们需要修改一下ATMEL SAMA5D3的timer驱动代码。这里我们还需要了解一件事情：在内核时间子系统的代码中（kernel/time/sched\_clock.c）有通用sched clock的支持。本身sched clock需要是64bit（不容易溢出），ns为单位、单调上升，更重要的是要快。当然未必所有平台都支持64 bit的一个HW counter，因此时间子系统提供了这样一个通用模块，当你的平台的counter不足64 bit的时候，你可以借用它来扩展成64 bit的sched clock。

ATMEL SAMA5D3的timer驱动代码位于drivers/clocksource/tcb\_clksrc.c中，首先在头文中中增加一行：

> #include <linux/sched\_clock.h>

之所以要包含这个头文件是因为下面我们要调用时间子系统的通用sched clock模块的sched\_clock\_register接口。

时间子系统的通用sched clock模块仍然需要底层HW counter（不足64bit）的支持，在ATMEL SAMA5D3平台中，我们有3个32bit的Time Counter channel，我们选择其一作为sched clock，并定义如下函数获取这个32 bit counter的cycle值：

> static cycle\_t tc\_read\_cycles(void)   
> {   
> return \_\_raw\_readl(tcaddr + ATMEL\_TC\_REG(0, CV));   
> }

最后一步就是注册了，在注册完clocksource之后增加注册sched clock的代码：

> /\* register sched clock \*/   
> sched\_clock\_register(tc\_read\_cycles, 32, divided\_rate);

OK，一切大功告成。

六、问题验证

重复第二节中的步骤，观察输出的跟踪文件，发现所有的时间戳都不再是10ms这样粗糙粒度的了，至此问题解决。

*原创文章，转发请注明出处。蜗窝科技*
