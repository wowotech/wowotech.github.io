---
title: "Linux时间子系统之（二）：软件架构"
date: 2015-03-07T18:37:48+08:00
url: "/timer_subsystem/time-subsyste-architecture.html"
gid: "151"
emlog_type: "blog"
summary: "本文的主要内容是描述内核时间子系统的软件框架。首先介绍了从旧的时间子系统迁移到新的时间子系统的源由，介绍新的时间子系统的优势。第三章汇整了时间子系统的相关文件以及内核配置。最后描述各种内核配置下的时间子系统的数据流和控制流。"
author: "linuxer"
category: "时间子系统"
category_alias: "timer_subsystem"
tags: ["软件框架", "时间子系统"]
views: 61125
comment_count: 34
aliases:
  - "/timer_subsystem/151.html"
  - "/151.html"
---

一、前言

本文的主要内容是描述内核时间子系统的软件框架。首先介绍了从旧的时间子系统迁移到新的时间子系统的源由，介绍新的时间子系统的优势。第三章汇整了时间子系统的相关文件以及内核配置。最后描述各种内核配置下的时间子系统的数据流和控制流。

二、背景介绍

1、传统内核时间子系统的软件架构

让我们先回到远古的2.4内核时代，其内核的时间子系统的软件框架如下：

[![old time](/content/uploadfile/201503/747216fbc17ec06dc03f51d2be4ff47e20150307103444.gif "old time")](/content/uploadfile/201503/e7d0070cea441d7af85c4f11787b05b620150307103110.gif)

首先，在每个architecture相关的代码中要有实现clock event和clock source模块。这里听起来名字是高大上，实际上，这里仅仅是借用了新时间子系统的名词，对于旧的内核，clock event就是通过timer硬件的中断处理函数完成的，在此基础上可以构建tick模块，tick模块维护了系统的tick，例如系统存在10ms的tick，每次tick到来的时候，timekeeping模块就增加系统时间，如果timekeeping完全是tick驱动，那么它精度只能是10ms，为了更高精度，clock source模块就是一个提供tick之间的offset时间信息的接口函数。

最初的linux kernel中只支持低精度的timer，也就是基于tick的timer。如果内核采用10ms的tick，那么低精度的timer的最高的精度也只有10ms，想要取得us甚至ns级别的精度是不可能的。各个内核的驱动模块都可以使用低精度timer实现自己的定时功能。各个进程的时间统计也是基于tick的，内核的调度器根据这些信息进行调度。System Load和Kernel Profiling模块也是基于tick的，用于计算系统负荷和进行内核性能剖析。

从用户空间空间来看，有两种需求，一种是获取或者设定当前的系统时间的接口函数：例如time，stime，gettimeofday等。另外一种是timer相关的接口函数：例如setitimer、alarm等，当timer到期后会向该进程发送signal。

2、为何会引入新的时间子系统软件架构？

但是随着技术发展，出现了下面两种新的需求：

（1）嵌入式设备需要较好的电源管理策略。传统的linux会有一个周期性的时钟，即便是系统无事可做的时候也要醒来，这样导致系统不断的从低功耗（idle）状态进入高功耗的状态。这样的设计不符合电源管理的需求。

（2）多媒体的应用程序需要非常精确的timer，例如为了避免视频的跳帧、音频回放中的跳动，这些需要系统提供足够精度的timer

和低精度timer不同，高精度timer使用了人类的最直观的时间单位ns（低精度timer使用的tick是和内核配置相关，不够直接）。本质上linux kernel提供了高精度timer之后，其实不必提供低精度timer了，不过由于低精度timer存在了很长的历史，并且在渗入到内核各个部分，如果去掉低精度timer很容易引起linux kernel稳定性和健壮性的问题，因此目前的linux kernel保持了低精度timer和高精度timer并存。

在新的需求的推动下，内核开发者对linux的时间子系统的软件框架进行修改，让代码层次更清晰，同时又是灵活可配置的，一个示意性的block图如下所示：

[![timehl](/content/uploadfile/201503/9285257f74afdad0d1f5e604c1c60d7f20150307103645.gif "timehl")](/content/uploadfile/201503/2b777e4e50bc7dfec1c153d44904859620150307103544.gif)

在引入multi-core之后，过去HW timer的功能被分成两个部分，一个是free running的system counter，是全局的，不属于任何一个CPU。另外一部分就是产生定时事件的HW block，我们称之timer，timer硬件被嵌入到各个cpu core中，因此，我们更准确的称之为CPU local Timer，这些timer都是基于一个Global counter运作的。在驱动层，我们提供一个clock source chip driver的模块来驱动硬件，这是模块是和硬件体系结构有关的。如果系统内存在多个HW timer和counter block，那么系统中可能会存在多个clock source chip driver。

面对形形色色的timer和counter硬件，linux kernel抽象出了通用clock event layer和通用clock source模块，这两个模块和硬件无关。底层的clock source chip driver会调用通用clock event和clock source模块的接口函数，注册clock source和clock event设备。clock source设备对应硬件的system free running counter，提供了一个基础的timeline。当然了，实际的timeline象一条直线，无限延伸。对于kernel而言，其timeline是构建在system free running counter之上的，因此clocksource 对应的timeline存在溢出问题。如果选用64bit的HW counter，并且输入频率不那么高，那么溢出时间可能会长达50年甚至更多，那么从应用的角度来看，能维持50年左右的timeline也可以接受。如果说clock source是一个time line，那么clock event是在timeline上指定的点产生clock event的设备，之所以能产生异步事件，当然是基于中断子系统了，clock source chip driver会申请中断并调用通用clock event模块的callback函数来通知这样的异步事件。

tick device layer基于clock event设备进行工作的：一般而言，每个CPU形成自己的一个小系统，有自己的调度、有自己的进程统计等，这个小系统都是拥有自己的tick设备，而且是唯一的。对于clock event设备而言就不是这样了，硬件有多少个timer硬件就注册多少个clock event device，各个cpu的tick device会选择自己适合的那个clock event设备。tick device可以工作在periodic mode或者one shot mode，当然，这是和系统配置有关。因此，在tick device layer，有多少个cpu，就会有多少个tick device，我们称之local tick device。当然，有些事情（例如整个系统的负荷计算）不适合在local tick驱动下进行，因此，所有的local tick device中会有一个被选择做global tick device，该device负责维护整个系统的jiffies，更新wall clock，计算全局负荷什么的。

高精度的timer需要高精度的clock event，工作在one shot mode的tick device工提供高精度的clock event。因此，基于one shot mode下的tick device，系统实现了高精度timer，系统的各个模块可以使用高精度timer的接口来完成定时服务。虽然有了高精度timer的出现, 内核并没有抛弃老的低精度timer机制(内核开发人员试图整合高精度timer和低精度的timer，不过失败了，所以目前内核中，两种timer是同时存在的)。当系统处于高精度timer的时候（tick device处于one shot mode），系统会setup一个特别的高精度timer（可以称之sched timer），该高精度timer会周期性的触发，从而模拟的传统的periodic tick，从而推动了传统低精度timer的运转。因此，一些传统的内核模块仍然可以调用经典的低精度timer模块的接口。

三、时间子系统的文件整理

1、文件汇整

linux kernel 时间子系统的源文件位于linux/kernel/time/目录下，我们整理如下：

|  |  |
| --- | --- |
| 文件名 | 描述 |
| time.c    timeconv.c | time.c文件是一个向用户空间提供时间接口的模块。具体包括：time, stime, gettimeofday, settimeofday,adjtime。除此之外，该文件还提供一些时间格式转换的接口函数（其他内核模块使用），例如jiffes和微秒之间的转换，日历时间（Gregorian date）和xtime时间的转换。xtime的时间格式就是到linux epoch的秒以及纳秒值。    timeconv.c中包含了从calendar time到broken-down time之间的转换函数接口。 |
| timer.c | 传统的低精度timer模块，基本tick的。 |
| time\_list.c    timer\_status.c | 向用户空间提供的调试接口。在用户空间，可以通过/proc/timer\_list接口可以获得内核中的时间子系统的相关信息。例如：系统中的当前正在使用的clock source设备、clock event设备和tick device的信息。通过/proc/timer\_stats可以获取timer的统计信息。 |
| hrtimer.c | 高精度timer模块 |
| itimer.c | interval timer模块 |
| posix-timers.c    posix-cpu-timers.c    posix-clock.c | POSIX timer模块和POSIX clock模块 |
| alarmtimer.c | alarmtimer模块 |
| clocksource.c    jiffies.c | clocksource.c是通用clocksource driver。其实也可以把system tick也看成一个特定的clocksource，其代码在jiffies.c文件中 |
| timekeeping.c    timekeeping\_debug.c | timekeeping模块 |
| ntp.c | NTP模块 |
| clockevent.c | clockevent模块 |
| tick-common.c    tick-oneshot.c    tick-sched.c | 这三个文件属于tick device layer。    tick-common.c文件是periodic tick模块，用于管理周期性tick事件。    tick-oneshot.c文件是for高精度timer的，用于管理高精度tick时间。    tick-sched.c是用于dynamic tick的。 |
| tick-broadcast.c    tick-broadcast-hrtimer.c | broadcast tick模块。 |
| sched\_clock.c | 通用sched clock模块。这个模块主要是提供一个sched\_clock的接口函数，调用该函数可以获取当前时间点到系统启动之间的纳秒值。    底层的HW counter其实是千差万别的，有些平台可以提供64-bit的HW counter，因此，在那样的平台中，我们可以不使用这个通用sched clock模块（不配置CONFIG\_GENERIC\_SCHED\_CLOCK这个内核选项），而在自己的clock source chip driver中直接提供sched\_clock接口。    使用通用sched clock模块的好处是：该模块扩展了64-bit的counter，即使底层的HW counter比特数目不足（有些平台HW counter只有32个bit）。 |

2、通用clock source和clock event的内核配置

（1）CONFIG\_GENERIC\_CLOCKEVENTS和CONFIG\_GENERIC\_CLOCKEVENTS\_BUILD：使用新的时间子系统的构架，如果不配置，那么将使用第二节描述的旧的时间子系统架构。

（2）曾经有一个CONFIG\_ GENERIC\_TIME的配置项对应clocksource的配置，不过在某个版本中删除了，也就是说目前的内核都是使用通用clocksource模块的，无法再退回到过去使用arch相关的clocksource的时代。为了兼容旧风格的timekeeping接口，kernel仍然提供了CONFIG\_ARCH\_USES\_GETTIMEOFFSET这个配置项。由此可见，在软件框架在演化的过程中，如果这是一个被其他模块使用的基础组件，我们不可能是完全推到重来，必须考虑对旧的软件的兼容性，虽然是一个沉重的负担，但是必须这么做。

3、tick device的配置

如果选择了新的时间子系统的软件架构（配置了CONFIG\_GENERIC\_CLOCKEVENTS），那么内核会打开Timers subsystem的配置选项，主要是和tick以及高精度timer配置相关。和tick相关的配置有三种，包括：

（1）无论何时，都启用用周期性的tick，即便是在系统idle的时候。这时候要配置CONFIG\_HZ\_PERIODIC选项。

（2）在系统idle的时候，停掉周期性tick。对应的配置项是CONFIG\_NO\_HZ\_IDLE。配置tickless idle system也会同时enable NO\_HZ\_COMMON的选项。

（3）Full dynticks system。即便在非idle的状态下，也就是说cpu上还运行在task，也可能会停掉tick。这个选项和实时应用相关。对应的配置项是CONFIG\_NO\_HZ\_FULL。配置Full dynticks system也会同时enable NO\_HZ\_COMMON的选项。本文不描述该系统，有兴趣的同学可以自行阅读。

上面的三个选项只能是配置其一。上面描述的是新的内核配置方法，对于旧的内核，CONFIG\_NO\_HZ用来配置dynamic tick或者叫做tickless idle system（非idle时有周期性tick，idle状态，timer中断不再周期性触发，只会按照需要触发），为了兼容旧的系统，新的内核仍然支持了这个选项。

4、timer模块的配置

和高精度timer相关的配置比较简单，只有一个CONFIG\_HIGH\_RES\_TIMERS的配置项。如果配置了高精度timer，或者配置了NO\_HZ\_COMMON的选项，那么一定需要配置CONFIG\_TICK\_ONESHOT，表示系统支持支持one-shot类型的tick device。

5、 如何进行时间子系统的内核配置

根据上一节的描述，linux内核可以有下面的两种时间子系统的构架：

（1）新的通用时间子系统软件框架（配置了CONFIG\_GENERIC\_CLOCKEVENTS）

（2）传统时间子系统软件框架（不配置CONFIG\_GENERIC\_CLOCKEVENTS，配置CONFIG\_ARCH\_USES\_GETTIMEOFFSET）

对于我们工程人员，除非你是维护一个旧的系统，否则当然使用新的通用时间子系统软件框架了，这时候可能的配置包括：

（1）使用低精度timer和周期tick。传统的linuxer应该会喜欢这个配置，保持和传统的unix的一致性。

（2）使用低精度timer和Dynamic tick

（3）使用高精度timer和周期tick

（4）使用高精度timer和Dynamic tick。新潮的linux应该会喜欢这个配置，一个字，cool……

注：本文主要描述普通的dynamic tick系统（tickless idle system），后续会有专门的文章描述full dynamic tick系统。

四、时间子系统的数据流和控制流

1、使用低精度timer + 周期tick

我们首先看周期性tick的实现。起始点一定是底层的clock source chip driver，该driver会调用注册clock event的接口函数（clockevents\_config\_and\_register或者clockevents\_register\_device），一旦增加了一个clock event device，需要通知上层的tick device layer，毕竟有可能新注册的这个device更好、更适合某个tick device呢（通过调用tick\_check\_new\_device函数实现）。要是这个clock event device被某个tick device收留了（要么该tick device之前没有匹配的clock event device，要么新的clock event device更适合该tick device），那么就启动对该tick device的配置（参考tick\_setup\_device）。根据当前系统的配置情况（周期性tick），会调用tick\_setup\_periodic函数，这时候，该tick device对应的clock event device的clock event handler被设置为tick\_handle\_periodic。底层硬件会周期性的产生中断，从而会周期性的调用tick\_handle\_periodic从而驱动整个系统的运转。需要注意的是：即便是配置了CONFIG\_NO\_HZ和CONFIG\_TICK\_ONESHOT，系统中没有提供one shot的clock event device，这种情况下，整个系统仍然是运行在周期tick的模式下。

下面来到低精度timer模块了，其实即便没有使能高精度timer，内核也会把高精度timer模块的代码编译进kernel的image中，这一点可以从Makefile文件中看出：

> obj-y += time.o timer.o **hrtimer.o** itimer.o posix-timers.o posix-cpu-timers.o

高精度timer总是会被编入最后的kernel中。在这种构架下，各个内核模块也可以调用linux kernel中的高精度timer模块的接口函数来实现高精度timer，但是，这时候高精度timer模块是运行在低精度的模式，也就是说这些hrtimer虽然是按照高精度timer的红黑树进行组织，但是系统只是在每一周期性tick到来的时候调用hrtimer\_run\_queues函数，来检查是否有expire的hrtimer。毫无疑问，这里的高精度timer也就是没有意义了。

由于存在周期性tick，低精度timer的运作毫无压力，和过去一样。

2、低精度timer + Dynamic Tick

系统开始的时候并不是直接进入Dynamic tick mode的，而是经历一个切换过程。开始的时候，系统运行在周期tick的模式下，各个cpu对应的tick device的（clock event device的）event handler是tick\_handle\_periodic。在timer的软中断上下文中，会调用tick\_check\_oneshot\_change进行是否切换到one shot模式的检查，如果系统中有支持one-shot的clock event device，并且没有配置高精度timer的话，那么就会发生tick mode的切换（调用tick\_nohz\_switch\_to\_nohz），这时候，tick device会切换到one shot模式，而event handler被设置为tick\_nohz\_handler。由于这时候的clock event device工作在one shot模式，因此当系统正常运行的时候，在event handler中每次都要reprogram clock event，以便正常产生tick。当cpu运行idle进程的时候，clock event device不再reprogram产生下次的tick信号，这样，整个系统的周期性的tick就停下来。

高精度timer和低精度timer的工作原理同上。

3、高精度timer + Dynamic Tick

同样的，系统开始的时候并不是直接进入Dynamic tick mode的，而是经历一个切换过程。系统开始的时候是运行在周期tick的模式下，event handler是tick\_handle\_periodic。在周期tick的软中断上下文中（参考run\_timer\_softirq），如果满足条件，会调用hrtimer\_switch\_to\_hres将hrtimer从低精度模式切换到高精度模式上。这时候，系统会有下面的动作：

（1）Tick device的clock event设备切换到oneshot mode（参考tick\_init\_highres函数）

（2）Tick device的clock event设备的event handler会更新为hrtimer\_interrupt（参考tick\_init\_highres函数）

（3）设定sched timer（也就是模拟周期tick那个高精度timer，参考tick\_setup\_sched\_timer函数）

这样，当下一次tick到来的时候，系统会调用hrtimer\_interrupt来处理这个tick（该tick是通过sched timer产生的）。

在Dynamic tick的模式下，各个cpu的tick device工作在one shot模式，该tick device对应的clock event设备也工作在one shot的模式，这时候，硬件Timer的中断不会周期性的产生，但是linux kernel中很多的模块是依赖于周期性的tick的，因此，在这种情况下，系统使用hrtime模拟了一个周期性的tick。在切换到dynamic tick模式的时候会初始化这个高精度timer，该高精度timer的回调函数是tick\_sched\_timer。这个函数执行的函数类似周期性tick中event handler执行的内容。不过在最后会reprogram该高精度timer，以便可以周期性的产生clock event。当系统进入idle的时候，就会stop这个高精度timer，这样，当没有用户事件的时候，CPU可以持续在idle状态，从而减少功耗。

4、高精度timer + 周期性Tick

这种配置不多见，多半是由于硬件无法支持one shot的clock event device，这种情况下，整个系统仍然是运行在周期tick的模式下。

*原创文章，转发请注明出处。蜗窝科技*

[/timer_subsystem/time-subsyste-architecture.html](/timer_subsystem/time-subsyste-architecture.html)
