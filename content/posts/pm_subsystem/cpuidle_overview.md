---
title: "Linux cpuidle framework(1)_概述和软件架构"
date: 2014-12-17T23:04:23+08:00
url: "/pm_subsystem/cpuidle_overview.html"
gid: "125"
emlog_type: "blog"
summary: "\r\n\t在计算机系统中，CPU的功能是执行程序，总结起来就是我们在教科书上学到的：取指、译码、执行。那么问题来了，如果没有程序要执行，CPU要怎么办？也许您会说，停掉就是了啊。确实，是要停掉，但何时停、怎么停，却要仔细斟酌，因为实际的软硬件环境是非常复杂的。\r\n\r\n\r\n\t我们回到Linux kernel上，Linux系统中，CPU被两类程序占用：一类是进程（或线程），也称进程上下文；另一类是各种中断"
author: "wowo"
category: "电源管理子系统"
category_alias: "pm_subsystem"
tags: ["Linux", "framework", "cpuidle"]
views: 69168
comment_count: 42
aliases:
  - "/pm_subsystem/125.html"
  - "/125.html"
---

#### 1. 前言

在计算机系统中，CPU的功能是执行程序，总结起来就是我们在教科书上学到的：取指、译码、执行。那么问题来了，如果没有程序要执行，CPU要怎么办？也许您会说，停掉就是了啊。确实，是要停掉，但何时停、怎么停，却要仔细斟酌，因为实际的软硬件环境是非常复杂的。

我们回到Linux kernel上，Linux系统中，CPU被两类程序占用：一类是进程（或线程），也称进程上下文；另一类是各种中断、异常的处理程序，也称中断上下文。

进程的存在，是用来处理事务的，如读取用户输入并显示在屏幕上。而事务总有处理完的时候，如用户不再输入，也没有新的内容需要在屏幕上显示。此时这个进程就可以让出CPU，但会随时准备回来（如用户突然有按键动作）。同理，如果系统没有中断、异常事件，CPU就不会花时间在中断上下文。

在Linux kernel中，这种CPU的无所事事的状态，被称作idle状态，而cpuidle framework，就是为了管理这种状态。

注：cpuidle framework系列文章会以ARM64作为示例平台，由于ARM64刚刚发布不久，较早版本的kernel没有相关的代码，因此选用了最新的[3.18-rc4](https://www.kernel.org/pub/linux/kernel/v3.x/testing/linux-3.18-rc4.tar.xz)版本的kernel。

#### 2. 功能概述

曾经有过一段时间，Linux kernel的cpu idle框架是非常简单的，简单到driver工程师只需要在“include\asm-arm\arch-xxx\system.h”中定义一个名字为arch\_idle的inline函数，并在该函数中调用kernel提供的cpu\_do\_idle接口，就Okay了，剩下的实现kernel全部帮我们做了，如下：

```
   1: static inline void arch_idle(void)
```

```
   2: {
```

```
   3:         cpu_do_idle();
```

```
   4: }
```

> 以蜗蜗之前使用过的一个ARM926的单核CPU为例(内核版本为Linux2.6.23)，cpuidle的处理过程是：
>   
> B start\_kernel(arch\arm\kernel\head-common.S)
>   
>  start\_kernel->rest\_init(init\main.c)
>   
> ;系统初始化完成后，将第一个进程（init）变为idle进程，
>   
>  ;以下都是在进程的循环中，周而复始…  
>  cpu\_idle->default\_idle(arch\arm\kernel\process.c)
>   
>  arch\_idle(include\asm-arm\arch-xxx\system.h)
>   
>  cpu\_do\_idle(include/asm-arm/cpu-single.h)
>   
>  cpu\_arm926\_do\_idle(arch/arm/mm/proc-arm926.S)
>   
>  mcr p15, 0, r0, c7, c0, 4 @ Wait for interrupt ;WFI指令

虽然简单，却包含了idle处理的两个重点：

1）idle进程

idle进程的存在，是为了解决“何时idle”的问题。

我们知道，Linux系统运行的基础是进程调度，而所有进程都不再运行时，称作cpu idle。但是，怎么判断这种状态呢？kernel采用了一个比较简单的方法：在init进程（系统的第一个进程）完成初始化任务之后，将其转变为idle进程，由于该进程的优先级是最低的，所以当idle进程被调度到时，则说明系统的其它进程不再运行了，也即CPU idle了。最终，由idle进程调用idle指令（这里为WFI），让CPU进入idle状态。

“[ARM WFI和WFE指令](/armv8a_arch/wfe_wfi.html)”中介绍过，WFI Wakeup events会把CPU从WFI状态唤醒，通常情况下，这些events是一些中断事件，因此CPU唤醒后会执行中断handler，在handler中会wakeup某些进程，在handler返回的时候进行调度，当没有其他进程需要调度执行的时候，调度器会恢复idle进程的执行，当然，idle进程不做什么，继续进入idle状态，等待下一次的wakeup。

2）WFI

WFI用于解决“怎么idle”的问题。

一般情况下，ARM CPU idle时，可以使用WFI指令，把CPU置为Wait for interrupt状态。该状态下，至少（和具体ARM core的实现有关，可参考“[ARM WFI和WFE指令](/armv8a_arch/wfe_wfi.html)”）会把ARM core的clock关闭，以节省功耗。

也许您会觉得，上面的过程挺好了，为什么还要开发cpuide framework？蜗蜗的理解是：

> ARM CPU的设计越来越复杂，对省电的要求也越来越苛刻，因而很多CPU会从“退出时的延迟”和“idle状态下的功耗”两个方面考虑，设计多种idle级别。对延迟较敏感的场合，可以使用低延迟、高功耗的idle；对延迟不敏感的场合，可以使用高延迟、低功耗的idle。
>
> 而软件则需要根据应用场景，在恰当的时候，选择一个合适的idle状态。而选择的策略是什么，就不是那么简单了。这就是cpuidle framework的存在意义（我们可以根据下面cpuidle framework的软件架构，佐证这一点）。

#### 3. 软件架构

Linux kernel中，cpuidle framework位于“drivers/cpuidle”文件夹中，包含cpuidle core、cpuidle governors和cpuidle drivers三个模块，再结合位于kernel sched中的cpuidle entry，共同完成cpu的idle管理。软件架构如下图：![cpuidle framework](/content/uploadfile/201412/2e0daa969175b05f7038639a16df13fe20141217150419.gif "cpuidle framework")

1）kernel schedule模块

位于kernel\sched\idle.c中，负责实现idle线程的通用入口（cpuidle entry）逻辑，包括idle模式的选择、idle的进入等等。

2）cpuidle core

cpuidle core负责实现cpuidle framework的整体框架，主要功能包括：

> 根据cpuidle的应用场景，抽象出cpuidle device、cpuidle driver、cpuidle governor三个实体；
>
> 以函数调用的形式，向上层sched模块提供接口；
>
> 以sysfs的形式，向用户空间提供接口；
>
> 向下层的cpuidle drivers模块，提供统一的driver注册和管理接口；
>
> 向下层的governors模块，提供统一的governor注册和管理接口。

cpuidle core的代码主要包括：cpuidle.c、driver.c、governor.c、sysfs.c。

3）cpuidle drivers

负责idle机制的实现，即：如何进入idle状态，什么条件下会退出，等等。

不同的architecture、不同的CPU core，会有不同的cpuidle driver，平台驱动的开发者，可以在cpuidle core提供的框架之下，开发自己的cpuidle driver。代码主要包括：cpuidle-xxx.c。

4）cpuidle governors

Linux kernel的framework有两种比较固定的抽象模式：

> 模式1，provider/consumer模式，interrupt、clock、timer、regulator等大多数的framework是这种模式。它的特点是，这个硬件模块是为其它一个或多个模块服务的，因而framework需要从对上（consumer）和对下（provider）两个角度进行软件抽象；
>
> 模式2，driver/governor模式，本文所描述的cpuidle framework即是这种模式。它的特点是：硬件（或者该硬件所对应的驱动软件）可以提供多种可选“方案”（这里即idle level），“方案”的实现（即机制），由driver负责，但是到底选择哪一种“方案”（即策略），则由另一个模块负责（即这里所说的governor）。

模式2的解释可能有点抽象，把它放到cpuidle的场景里面，就很容易理解了：

前面讲过，很多CPU提供了多种idle级别（即上面所说的“方案”），这些idle 级别的主要区别是“idle时的功耗”和“退出时延迟”。cpuidle driver（机制）负责定义这些idle状态（每一个状态的功耗和延迟分别是多少），并实现进入和退出相关的操作。最终，cpuidle driver会把这些信息告诉governor，由governor根据具体的应用场景，决定要选用哪种idle状态（策略）。

kernel中，cpuidle governor都位于governors/目录下。

#### 4. 软件流程

在阅读本章之前，还请读者先阅读如下三篇文章：

> “[Linux cpuidle framework(2)\_cpuidle core](/pm_subsystem/cpuidle_core.html)”
>
> “[Linux cpuidle framework(3)\_ARM64 generic CPU idle driver](/pm_subsystem/cpuidle_arm64.html)”
>
> “[Linux cpuidle framework(4)\_menu governor](/pm_subsystem/cpuidle_menu_governor.html)”

前面提到过，kernel会在系统启动完成后，在init进程（或线程）中，处理cpuidle相关的事情。大致的过程是这样的（kernel启动相关的分析，会在其它文章中详细介绍）：

> 首先需要说明的是，在SMP（多核）系统中，CPU启动的过程是：
>
> 1）先启动主CPU，启动过程和传统的单核系统类似：stext-->start\_kernel-->rest\_init-->cpu\_startup\_entry
>
> 2）启动其它CPU，可以有多种方式，例如CPU hotplug等，启动过程为：secondary\_startup-->\_\_secondary\_switched-->secondary\_start\_kernel-->cpu\_startup\_entry
>
> 上面的代码位于./arch/arm64/kernel/head.S、init/main.c等等，感兴趣的读者可以自行参考。最终都会殊途同归，运行至cpu\_startup\_entry接口，该接口位于kernel/sched/idle.c中，负责处理CPU idle的事情，流程如下（暂时忽略一些比较难理解的分支，如cpu idle poll等）。

cpu\_startup\_entry流程：

> cpu\_startup\_entry
>   
>  arch\_cpu\_idle\_prepare，进行idle前的准备工作，ARM64中没有实现
>   
>  cpu\_idle\_loop，进入cpuidle的主循环
>   
>  如果系统当前不需要调度（!need\_resched()），执行后续的动作
>   
> local\_irq\_disable，关闭irq中断  
>  arch\_cpu\_idle\_enter，arch相关的cpuidle enter，ARM64中没有实现
>   
>  cpuidle\_idle\_call，main idle function
>   
>  cpuidle\_select，通过cpuidle governor，选择一个cpuidle state
>   
>  cpuidle\_enter，通过cpuidle state，进入该idle状态
>   
>  …
>   
> 中断产生，idle返回（注意，此时irq是被禁止的，因此CPU不能响应产生中断的事件）  
>  cpuidle\_reflect，通知cpuidle governor，更新状态
>   
> local\_irq\_enable，使能中断，响应中断事件，跳转到对应的中断处理函数  
>  …   
>  arch\_cpu\_idle\_exit，和enter类似，ARM64没有实现

具体的代码比较简单，不再分析了，但有一点，还需要着重说明一下：

使用cpuidle framework进入idle状态时，本地irq是处于关闭的状态，因此从idle返回时，只能接着往下执行，直到irq被打开，才能执行相应的中断handler，这和之前传统的cpuidle不同。同时也间接证实了“[Linux cpuidle framework(4)\_menu governor](/pm_subsystem/cpuidle_menu_governor.html)”中所提及的，为什么menu governor在reflect接口中只是简单的置一个标志。因为reflect是在关中断时被调用的，需要尽快返回，以便处理中断事件。

*原创文章，转发请注明出处。蜗窝科技*，[www.wowotech.net](/pm_subsystem/cpuidle_overview.html)。
