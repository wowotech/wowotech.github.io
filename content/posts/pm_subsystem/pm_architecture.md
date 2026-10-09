---
title: "Linux电源管理(1)_整体架构"
date: 2014-05-07T19:21:03+08:00
url: "/pm_subsystem/pm_architecture.html"
gid: "39"
emlog_type: "blog"
summary: "在这个世界中，任何系统的运转都需要能量。如树木依靠光能生长，如马儿依靠食物奔跑，如计算机系统依靠电能运行。而能量的获取是有成本的，因此如果能在保证系统运转的基础上，尽量节省对能量的消耗，就会大大提升该系统的生存竞争力。这方面，大自然已经做的很好了，如植物的落叶，如动物的冬眠，等等。而在计算机的世界里（这里以运行Linux OS的嵌入式系统为例），称作电源管理（Power Management）。 "
author: "wowo"
category: "电源管理子系统"
category_alias: "pm_subsystem"
tags: ["Kernel", "management", "PM", "Power", "Architecture"]
views: 98233
comment_count: 48
aliases:
  - "/pm_subsystem/39.html"
  - "/39.html"
---

#### 1. 前言

在这个世界中，任何系统的运转都需要能量。如树木依靠光能生长，如马儿依靠食物奔跑，如计算机系统依靠电能运行。而能量的获取是有成本的，因此如果能在保证系统运转的基础上，尽量节省对能量的消耗，就会大大提升该系统的生存竞争力。这方面，大自然已经做的很好了，如植物的落叶，如动物的冬眠，等等。而在计算机的世界里（这里以运行Linux OS的嵌入式系统为例），称作电源管理（Power Management）。

通俗的讲，电源管理就是：“想让马儿跑，不想马吃草”。不过，从能量守恒的角度，想让马儿跑多快、跑多久，就一定要让它吃相应数量的草。那么我们就退而求其次：“只在需要马儿跑时，才让它吃草”。这就是电源管理的核心思想。那方法呢？可以这样：

方法1：不需要马儿跑时，把它杀掉，这样就不吃草了。需要马儿跑时，再养一匹。

在现实世界中，除了傻瓜，应该没人使用这种方法。因为重新养一匹马需要时间----我哪里等得及，需要草----有可能比养一匹闲马需要的更多。

方法2：不需要马儿跑时，让它睡觉，不能睁眼，不能动，不能叫。

先不讲马儿是否愿意一直睡觉，这种方法只能减少马儿吃草的数量，因为它的心脏还在跳动、血液还在流通，这些也消耗能量。不过还好，需要马儿跑时，应该不需要等太久了。

方法3：不是说心脏跳动、血液流通也消耗能量吗？那把这些也停下来好了，能省多少是多少嘛。

确实是好方法，不多得先去问问兽医，能不能搞定。不过以现在的医学水平，估计实现不了啊。

在计算机世界中，上面的方法是再平常不过的了，而且控制的远比这些精细。因为计算机是人类设计出来的，而马儿却是经上帝之手。不过通过马儿的例子，我们可以总结出电源管理的基本行为：

a, 实时的关闭暂时不使用的部分（可称作“工作状态到非工作状态的转移”）。例如手机在口袋时，屏幕没必要亮。

b, 当需要重新使用那些已关闭部分时（可称作“非工作状态到工作状态的转移”），不能有太长时间的等待，且转移过程不能消耗太多的能量。上面的方法1就是一个反面教材，但在计算机的世界里，情况会好很多。

#### 2. Linux电源管理的组成

电源管理（Power Management）在Linux Kernel中，是一个比较庞大的子系统，涉及到供电（Power Supply）、充电（Charger）、时钟（Clock）、频率（Frequency）、电压（Voltage）、睡眠/唤醒（Suspend/Resume）等方方面面（如下图），蜗蜗会在Linux电源管理系列文章中，对它们一一讲述。

注1：该图片只是一个示意图，并没有划分软件层次，因此模块之间的关系不一定是真正的关系。

[![整体架构](/content/uploadfile/201405/b27925dba594fa41703fe6a17124dc4c20140507085112.gif "整体架构")](/content/uploadfile/201405/f9d621af413cd7ebe7928d3dbcd6590120140507085110.gif)

在对图片中的这些组件（也可以称作Framework）进行详细描述之前，先在这里了解一下基本概念。

注2：Framework是一个中间层的软件，提供软件开发的框架。其目有三：一是屏蔽具体的实现细节，固定对上的接口，这样可以方便上层软件的开发和维护；二是尽可能抽象公共逻辑，并在Framework内实现，以提高重用性、减少开发量；三是向下层提供一系列的回调函数（callback function），下层软件可能面对差别较大的现实，但只要填充这些回调函数，即可完成所有逻辑，减小了开发的难度。

- Power Supply，是一个供用户空间程序监控系统的供电状态（电池供电、USB供电、AC供电等等）的class。通俗的讲，它是一个Battery&Charger驱动的Framework
- Clock Framework，Clock驱动的Framework，用于统一管理系统的时钟资源
- Regulator Framework，Voltage/Current Regulator驱动的Framework。该驱动用于调节CPU等模块的电压和电流值
- Dynamic Tick/Clock Event，在传统的Linux Kernel中，系统Tick是固定周期（如10ms）的，因此每隔一个Tick，就会产生一个Timer中断。这会唤醒处于Idle或者Sleep状态的CPU，而很多时候这种唤醒是没有意义的。因此新的Kernel就提出了Dynamic Tick的概念，Tick不再是周期性的，而是根据系统中定时器的情况，不规律的产生，这样可以减少很多无用的Timer中断
- CPU Idle，用于控制CPU Idle状态的Framework
- Generic PM，传统意义上的Power Management，如Power Off、Suspend to RAM、Suspend to Disk、Hibernate等
- Runtime PM and Wakelock，运行时的Power Management，不再需要用户程序的干涉，由Kernel统一调度，实时的关闭或打开设备，以便在使用性能和省电性能之间找到最佳的平衡   
  注3：Runtime PM是Linux Kernel亲生的运行时电源管理机制，Wakelock是由Android提出的机制。这两种机制的目的是一样的，因此只需要支持一种即可。另外，由于Wakelock机制路子太野了，饱受Linux社区的鄙视，因此我们不会对该机制进行太多的描述。
- CPU Freq/Device Freq，用于实现CPU以及Device频率调整的Framework
- OPP（Operating Performance Point），是指可以使SOCs或者Devices正常工作的电压和频率组合。内核提供这一个Layer，是为了在众多的电压和频率组合中，筛选出一些相对固定的组合，从而使事情变得更为简单一些
- PM QOS，所谓的PM QOS，是指系统在指定的运行状态下（不同电压、频率，不同模式之间切换，等等）的工作质量，包括latency、timeout、throughput三个参数，单位分别为us、us和kb/s。通过QOS参数，可以分析、改善系统的性能

##### 3.  Kernel中电源管理相关的Source code汇整

在蜗蜗使用的Linux 3.10.29版本的内核中，电源管理有关的Source code分别位于：

- kernel/power/ \*
- drivers/power/
- drivers/base/power/\*
- drivers/cpuidle/\*
- drivers/cpufreq/\*
- drivers/devfreq/\*
- include/linux/power\_supply.h
- include/linux/cpuidle.h
- include/linux/cpufreq.h
- include/linux/cpu\_pm.h
- include/linux/device.h
- include/linux/pm.h
- include/linux/pm domain.h
- include/linux/pm runtime.h
- include/linux/pm wakeup.h
- include/linux/suspend.h
- Documentation/power/\*.txt

*原创文章，转发请注明出处。蜗窝科技，[www.wowotech.net](/pm_subsystem/pm_architecture.html)。*
