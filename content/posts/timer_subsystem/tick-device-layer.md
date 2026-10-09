---
title: "Linux时间子系统之（十三）：Tick Device layer综述"
date: 2015-03-26T18:50:55+08:00
url: "/timer_subsystem/tick-device-layer.html"
gid: "158"
emlog_type: "blog"
summary: "时间子系统中的tick device layer主要涉及kernel/time/tick-*相关的文件，本文的主要内容就是从high level层次（不纠缠在具体的每行代码）描述tick device layer的运作逻辑。 如 果说每个.c文件是一个模块的话，我们可以首先简单描述tick device layer的各个模块。tick-common.c描述了tick device的一些通用操作，此"
author: "linuxer"
category: "时间子系统"
category_alias: "timer_subsystem"
tags: ["Device", "tick", "tickless", "NO_HZ"]
views: 36153
comment_count: 45
aliases:
  - "/timer_subsystem/158.html"
  - "/158.html"
---

一、前言

时间子系统中的tick device layer主要涉及kernel/time/tick-\*相关的文件，本文的主要内容就是从high level层次（不纠缠在具体的每行代码）描述tick device layer的运作逻辑。

如果说每个.c文件是一个模块的话，我们可以首先简单描述tick device layer的各个模块。tick-common.c描述了tick device的一些通用操作，此外，该文件还包括了周期性tick的代码。想要让系统工作在tickless mode（更准确应该是Dynamic tick模块，也就是说根据系统的当前运行状况，动态的启停周期性tick）需要两个模块的支持，分别是tick-oneshot.c和tick-sched.c。tick-oneshot.c主要是提供和tick device的one shot mode相关的操作接口函数。从字面上看，tick-sched.c是和tick的调度相关，所谓tick的调度包括两个方面，一方面是在系统正常运行过程中，如何产生周期性的tick event，另一方面是在系统没有任务执行，进入idle状态的时候，如何停止周期性的tick，以及恢复的时候如何更新系统状态（例如：jiffies等）。tick-broadcast.c和tick-broadcast-hrtimer.c是和tick broadcast相关，本文不会涉及这部分的内容，会有专门的文档描述它。

本文的第二章描述了关于tick device概述性的内容，随后在第三章描述了tick device layer是如何初始化的，由于tick device开始总是工作在periodic mode，因此，本章也就顺便描述了周期性tick的运作。如果硬件以及系统配置允许，系统中的tick device会切换one shot mode，从而进入tickless mode，因此第四章描述了在配置了高精度timer的情况下，dynamic tick如何运作之机理，第五章和第四章类似，只不过描述的是没有配置高精度timer的情况。

二、tick device概述以及软件结构

虽然在[periodic tick](/timer_subsystem/periodic-tick.html)文档中对tick device有一些描述，不过这里再复习一次，这次不再细述数据结构而是从较高的层面来描述tick device的软件结构。

1、什么是tick

想要理解什么是tick device，什么是tickless kernel，首先当然要理解什么是tick？要理解什么是tick，首先要理解OS kernel是如何运作的。系统中有很多日常性的事情需要处理，例如：

－－－更新系统时间

－－－处理低精度timer

－－－处理正在运行进程的时间片信息

系统在处理这些事情的时候使用了轮询的方式，也就是说按照固定的频率去做这些操作。这时候就需要HW的协助，一般而言，硬件会有HW timer（称之system timer）可以周期性的trigger interrupt，让系统去处理上述的日常性事务。每次timer中断到来的时候，内核的各个模块就知道，一个固定的时间片已经过去。对于日常生活，tick这个概念是和钟表关联的：钟表会发出周期性的滴答的声音，这个声音被称为tick。CPU和OS kernel扩展了这个概念：周期性产生的timer中断事件被称为tick，而能够产生tick的设备就称为tick device。

如何选择tick的周期是需要在power comsuption、时间精度以及系统响应时间上进行平衡。我们考虑系统中基于tick的低精度timer模块，选择较高的tick频率会提高时间精度，例如对于，10ms的tick周期意味着低精度timer的时间精度就是10ms，设定3ms的低精度timer没有任何意义。为了提高时间精度，我们可以提高tick的频率，例如可以提升到1ms的tick，但是，这时更多的CPU的时间被花费在timer的中断处理，实际上，当系统不繁忙的时候，并不是每一个tick都是那么有意义，实际上大部分的tick到来的时候，OS kernel往往只是空转，实际上并有什么事情做，这对系统的power consumption是有害的。对于嵌入式设备，周期性的tick对power consumption危害更大，因为对于嵌入式设备，待机时间是一个很重要的指标，而周期性tick则意味着系统不可能真正的进入idle状态，而是会周期性的被wakeup，这些动作会吃掉电池的电量。同理，对于调度器而言亦然。如果设定10ms的tick，分配每个进程的时间片精度只是10ms，调度器计算每个进程占用CPU的时间也只能是以10ms为单位。为了提高进程时间片精度，我们可以提高tick的频率，例如可以提升到1ms的tick，但是，这时更多的CPU的时间被花费在进程上下文的切换上，但是，对应的好处是系统的响应时间会更短。

2、什么是tickless？

tickless本质上上是去掉那个烦恼的滴答声音。我睡觉的时候不怕噪音，但是非常怕有固定周期的滴答声音，因此我需要一块tickless的钟表。对于OS kernel而言，tickless也就是意味着没有那个固定周期的timer interrupt事件，可是，没有那个固定的tick，OS kernel如何运转呢？我们还是选取上一节中的三个主题，进行逐一分析。

首先看看如何处理timer。各种驱动和内核模块（例如网络子系统的TCP模块）都有timer的需求，因此，时间子系统需要管理所有注册到系统的timer。对于有tick的系统，在每个tick中scan所有的timer是一个顺理成章的想法，如果检查到timer超期（或者即将超期）系统会调用该timer的callback函数。当然，由于要在每个tick到来的时候检查timer，因此效率非常重要，内核有一些有意思的设计，有兴趣的读者可以看看低精度timer的的scan过程。没有tick怎么办？这时候需要找到所有timer中最近要超期的timer，将其时间值设定到实际的HW timer中就OK了，当然，这时候需要底层的HW timer支持one shot，也就是说，该timer的中断就来一次，在该timer的的中断处理中除了处理超期函数之外，还需要scan所有timer，找到最近要超期的timer，将其时间值设定到实际的HW timer中就OK了，然后不断的重复上面的过程就OK了。假设系统中注册了1200ns, 1870ns, 2980ns, 4500ns, 5000ns和6250ns的timer，在一个HZ=1000的系统上，timer的超期都是在规则的tick时间点上，对于tickless的系统，timer的中断不是均匀的，具体如下图所示：

[![timerline](/content/uploadfile/201503/e0a38b5df19e4fd16839fb8c00baeb2720150326104709.gif "timerline")](/content/uploadfile/201503/db85b78d6cf7fbf8910f02c7a50ee22c20150326104553.gif)

我们再来看看更新系统时间。对于有tick的系统，非常简单，在每个tick到来的时候调用update\_wall\_time来更新系统时间，当然，由于是周期性tick，这时候每次都是累加相同的时间。对于tickless的系统，我们可以选择在每个timer超期的中断中调用update\_wall\_time来更新系统时间，不过，这种设计不好，一方面，如果系统中的timer数目太多，那么update\_wall\_time调用太频繁，而实际上是否系统需要这么高精度的时间值呢？更重要的是：timer中断到来是不确定的，和系统中的timer设定相关，有的时间段timer中断比较频繁，获取的系统时间精度比较高，有的时间段，timer中断比较稀疏，那么获取的系统时间精度比较低。

最后，我们来看调度器怎么适应tickless。我们知道，除非你是一个完全基于优先级的调度器，否则系统都会给进程分配一个时间片（time slice），当占用CPU的时间片配额使用完了，该进程会挂入队列，等待调度器分配下一个时间片，并调度运行。有tick当然比较简单，在该tick的timer中断中减去当前进程的时间片。没有tick总是比较麻烦，我能想到的方法是：假设我们给进程分配40ms的时间片，那么在调度该进程的时候需要设定一个40ms的timer，timer到期后，调度器选择另外一个进程，然后再次设定timer。当然，如果没有进程优先级的概念（或者说优先级仅仅体现在分配的时间片比较多的情况下），并且系统中处于runnable状态的进程较少，整体的运作还是OK的。如果有优先级概念怎么办？如果进程执行过程中被中断打断，切换到另外的进程怎么办？如果系统内的进程数目很多如何保证调度器的性能？算了，太复杂了，还是有tick比较好，因此实际中，linux kernel在有任务执行的时候还是会启动周期性的tick。当然，世界上没有绝对正确的设计，任何优雅的设计都是适用于一定的应用场景的。其实自然界的规律不也是这样吗？牛顿的定律也不是绝对的正确，仅仅适用于低速的场景，当物体运动的速度接近光速的时候，牛顿的经典力学定律都失效了。

3、内核中的tickless

本节我们主要来看看内核中的tickless的情况。传统的unix和旧的linux（2000年初之前的）都是有tick的（对于新的内核，配置CONFIG\_HZ\_PERIODIC的情况下也是有tick的），新的linux kernel中增加了tickless的选项：

－－－CONFIG\_NO\_HZ\_IDLE

－－－CONFIG\_NO\_HZ\_FULL

CONFIG\_NO\_HZ\_IDLE是说在系统dile的时候是没有tick的，当然，在系统运行的时候还是有tick的，因此，我们也称之dynamic tick或者NO HZ mode。3.10版本之后，引入一个full tickless mode，听起来好象任何情况下都是没有tick的，不过实际上也没有那么强，除了CPU处于idle的时候可以停下tick，当CPU上有且只有一个进程运行的时候，也可以停下周期性tick，其他的情况下，例如有多个进程等待调度执行，都还是有tick的。这个配置实际上只是对High-performance computing (HPC)有意义的，因此不是本文的重点。

4、tick device概述

Tick device是能够提供连续的tick event的设备。目前linux kernel中有periodic tick和one-shot tick两种tick device。periodic tick可以按照固定的时间间隔产生tick event。one-shot tick则是设定后只能产生一次tick event，如果要连续产生tick event，那么需要每次都进行设定。

每一个cpu都有属于自己的tick device。定义为tick\_cpu\_device。每一个tick device都有自己的类型（periodic或者one-shot），每一个tick device其实就是一个clock event device（增加了表示mode的member），不同类型的tick device有不同的event handler。对于periodic类型的tick设备，其clock event device的event handler是tick\_handle\_periodic（没有配置高精度timer）或者hrtimer\_interrupt（配置了高精度timer）。对于one-shot类型的tick设备，其clock event device的event handler是hrtimer\_interrupt（配置了高精度timer）或者tick\_nohz\_handler（没有配置高精度timer）。

Tick Device模块负责管理系统中的所有的tick设备，在SMP环境下，每一个CPU都自己的tick device，这些tick device中有一个被选择做global tick device，该device负责维护整个系统的jiffies以及更新哪些基于jiffies进行的全系统统计信息。

三、kernel如何初始化tick device layer以及周期性tick的运作？

如果把tick device的逻辑当初一个故事，那么故事的开始来自clockevent device layer。每当底层有新的clockevent device加入到系统中的时候，会调用clockevents\_register\_device或者clockevents\_config\_and\_register向通用clockevent layer注册一个新的clockevent设备，这时候，会调用tick\_check\_new\_device通知tick device layer有新货到来。如果tick device和clockevent device你情我愿，那么就会调用tick\_setup\_device函数setup这个tick device了。一般而言，刚系统初始化的时候，所有cpu的tick device都没有匹配clock event device，因此，该cpu的local tick device也就是global tick device了。而且，如果tick device是新婚（匹配之前，tick device的clock event device等于NULL），那么tick device的模式将被设定为TICKDEV\_MODE\_PERIODIC，即便clock event有one shot能力，即便系统配置了NO HZ。好吧，反正无论如何都需要从周期性tick开始，那么看看如何进行周期性tick的初始化的。

tick\_setup\_periodic函数用来设定一个periodic tick device。当然，最重要的设定event handler，对于周期性tick device，其clock event device的handler被设定为tick\_handle\_periodic。光有handler也不行，还得kick off底层的硬件，让其周期性的产生clock event，这样才能推动系统的运作（这是通过调用clockevent device layer的接口函数完成的）。

最后，我们思考一个问题：系统启动过程中，什么时候开始有tick？多核系统，BSP首先启动，在其初始化过程中会调用time\_init，这里会启动clocksource的初始化过程。这时候，周期性的tick就会开始了。在某个阶段，其他的processor会启动，然后会注册其自己的local timer，这样，各个cpu上的tick就都启动了。

四、设置了高精度timer的情况下，dynamic tick如何运作？

1、软件层次

下面的这幅图是以tick device为核心，描述了该模块和其他时间子系统模块的交互过程（配置高精度timer和dynamic tick的情况）：

[![dtick](/content/uploadfile/201503/3b26b3d2f252a48ccb4624ee4966c74b20150326104939.gif "dtick")](/content/uploadfile/201503/e624b8d32665be23a9ec26c813a1efcf20150326104812.gif)

上图中，红色边框的模块是per cpu的模块，所谓per cpu就是说每个cpu都会维护属于一个自己的对象。例如，对于tick device，每个CPU都会维护自己的tick device，不过，为了不让图片变得太大，上图只画了一个CPU的情况，其他CPU的动作是类似。为何clock event没有被涂上红色的边框呢？实际上clock event device并不是per cpu的，有些per cpu的local timer，也有global timer，如果硬件设计人员愿意的话，一个CPU可以有多个local timer，系统中所有的timer硬件被抽象成一个个的clock event device进行系统级别的管理，每个CPU并不会特别维护一个属于自己的clock event device。弱水三千，只取一瓢。每个CPU只会在众多clock event device中选取那个最适合自己的clock event device构建CPU local tick device。

tick device系统的驱动力来自中断子系统，当HW timer（tick device使用的那个）超期会触发中断，因此会调用hrtimer\_interrupt来驱动高精度timer的运转（执行超期timer的call back函数）。而在hrtimer\_interrupt中会扫描保存高精度timer的红黑树，找到下一个超期需要设定的时间，调用tick\_program\_event来设定下一次的超期事件，你知道的，这是我们的tick device工作在one shot mode，需要不断的set next expire time，才能驱动整个系统才会不断的向前。

传统的低精度timer是周期性tick驱动的，但是，目前tick 处于one shot mode，怎么办？只能是模拟了，Tick device layer需要设定一个周期性触发的高精度timer，在这个timer的超期函数中（tick\_sched\_timer）执行进行原来周期性tick的工作，例如触发TIMER\_SOFTIRQ以便推动系统低精度timer的运作，更新timekeeping模块中的real clock。

2、如何切换到tickless

我们知道，开始tick device总是工作在周期性tick的mode，一切就像过去一样，无论何时，系统总是有那个周期性的tick到来。这个周期性的tick是由于硬件timer的中断推动，该HW Timer的中断会注册soft irq，因此，HW timer总会周期性的触发soft irq的执行，也就是run\_timer\_softirq函数。在该函数中会根据情况将hrtimer切换到高精度模式（hrtimer也有两种mode，一种高精度mode，一种是低精度mode，系统总是从低精度mode开始）。在系统切换到高精度timer mode的时候（hrtimer\_switch\_to\_hres），由于高精度timer必须需要底层的tick device运行在one shot mode，因此，这时会调用tick\_switch\_to\_oneshot函数将该CPU上的tick device的mode切换置one shot（Note：这时候event handler设定为hrtimer\_interrupt）。同样的，底层的clock event device也会被设定为one shot mode。一旦进入one shot mode，那个周期性到来的timer中断就会消失了，从此系统只会根据系统中的hrtimer的设定情况来一次性的设定底层HW timer的触发。

3、如何产生周期性tick

虽然tick device以及底层的HW timer都工作在one shot mode，看起来系统的HW timer中断都是按需产生，多么美妙。但是，由于各种原因（此处省略3000字），在系统运行过程中，那个周期性的tick还需要保持，因此，在切换到one shot mode的同时，也会调用tick\_setup\_sched\_timer函数创建一个sched timer（一个普通的hrtimer而已），该timer的特点就是每次超期后还会调用hrtimer\_forward，不断的将自己挂回hrtimer的红黑树，于是乎，tick\_sched\_do\_timer接口按照tick的周期不断的被调用，从而模拟了周期性的tick。

4、在idle的时候如何停掉tick

我们知道，各个cpu上的swapper进程（0号进程，又叫idle进程）最后都是会执行cpu\_idle\_loop函数，该函数在真正执行cpu idle指令之前会调用tick\_nohz\_idle\_enter，在该函数中，sched timer会被停掉，因此，周期性的HW timer不会再来，这时候将cpu从idle中唤醒的只能是和实际上系统中的hrtimer中的那个最近的超期时间有关。

5、如何恢复tick

概念同上，当从idle中醒来，tick\_nohz\_idle\_exit函数被调用，重建sched timer，一切恢复了原状。

五、没有设置高精度timer的情况下，dynamic tick如何运作？

这部分留给有兴趣的读者自己学习吧。

*原创文章，转发请注明出处。蜗窝科技*

[/timer_subsystem/tick-device-layer.html](/timer_subsystem/tick-device-layer.html)
