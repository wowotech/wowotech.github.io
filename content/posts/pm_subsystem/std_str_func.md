---
title: "Linux电源管理(5)_Hibernate和Sleep功能介绍"
date: 2014-06-10T16:11:19+08:00
url: "/pm_subsystem/std_str_func.html"
gid: "49"
emlog_type: "blog"
summary: "Hibernate和Sleep两个功能是Linux Generic PM的核心功能，它们的目的是类似的：暂停使用——>保存上下文——>关闭系统以节电········>恢复系统——>恢复上下文——>继续使用。 本文以内核向用户空间提供的接口为突破口，从整体上对这两个功能进行介绍，并会在后续的文章中，分析它们的实现逻辑和执行动作。 顺便感概一下，虽然这些机制在Linux系统中存在很久了（类似的概念也存"
author: "wowo"
category: "电源管理子系统"
category_alias: "pm_subsystem"
tags: ["Linux", "PM", "STD", "STR", "wakeup_count"]
views: 69656
comment_count: 43
aliases:
  - "/pm_subsystem/49.html"
  - "/49.html"
---

#### 1. 前言

Hibernate和Sleep两个功能是Linux Generic PM的核心功能，它们的目的是类似的：暂停使用——>保存上下文——>关闭系统以节电········>恢复系统——>恢复上下文——>继续使用。

本文以内核向用户空间提供的接口为突破口，从整体上对这两个功能进行介绍，并会在后续的文章中，分析它们的实现逻辑和执行动作。

*顺便感概一下，虽然这些机制在Linux系统中存在很久了（类似的概念也存在于Windows系统中），但以蜗蜗的观察，它们被使用的频率并不是很高，特别是在PC上，大多数人在大多数时候选择直接关闭系统。阴错阳差的是，在很多嵌入式设备中，设计者会利用Sleep机制实现热关机功能，以此减少开机的时间。*

#### 2. Hibernate和Sleep相关的术语梳理

蜗蜗在“[Generic PM之基本概念和软件架构](/pm_subsystem/generic_pm_architecture.html)”中提到了Linux Generic PM有关的多个词汇，如Hibernate、Sleep、Suspend、Standby等等，听起来有些乱，因此在介绍Hibernate和Sleep之前，先来理一下这些词汇的关系。

> ▆ Hibernate（冬眠）和Sleep（睡眠）
>
> 是Linux电源管理在用户角度的抽象，是用户可以看到的实实在在的东西。它们的共同点，是保存系统运行的上下文后挂起（suspend）系统，并在系统恢复后接着运行，就像什么事情都没有发生一样。它们的不同点，是上下文保存的位置、系统恢复的触发方式以及具体的实现机制。
>
> ▆ Suspend
>
> 有两个层次的含义。一是Hibernate和Sleep功能在底层实现上的统称，都是指挂起（Suspend）系统，根据上下文的保存位置，可以分为Suspend to Disk（STD，即Hibernate，上下文保存在硬盘/磁盘中）和Suspend to RAM（STR，为Sleep的一种，上下文保存在RAM中）；二是Sleep功能在代码级的实现，表现为“kernel/power/suspend.c”文件。
>
> ▆ Standby，是Sleep功能的一个特例，可以翻译为“**打盹**”。
>
> 正常的Sleep（STR），会在处理完上下文后，由arch-dependent代码将CPU置为低功耗状态（通常为Sleep）。而现实中，根据对功耗和睡眠唤醒时间的不同需求，CPU可能会提供多种低功耗状态，如除Sleep之外，会提供Standby状态，该状态下，CPU处于浅睡眠模式，有任何的风吹草动，就会立即醒来。
>
> ▆ Wakeup
>
> 这是我们第一次正式的提出Wakeup的概念。我们多次提到恢复系统，其实在内核中称为Wakeup。表面上，wakeup很简单，无论是冬眠、睡眠还是打盹，总得有一个刺激让我们回到正常状态。但复杂的就是，什么样的刺激才能让我们醒来？
>
> 动物界，温度回升可能是唯一可以让动物从冬眠状态醒来的刺激。而踢一脚、闹钟响等刺激，则可以让我们从睡眠状态唤醒。对于打盹来说，则任何的风吹草动，都可以唤醒。
>
> 而在计算机界，冬眠（Hibernate）时，会关闭整个系统的供电，因此想醒来，唯有Power按钮可用。而睡眠时，为了缩短Wakeup时间，并不会关闭所有的供电，另外，为了较好的用户体验，通常会保留某些重要设备的供电（如键盘），那样这些设备就可以唤醒系统。
>
> 这些刻意保留下来的、可以唤醒系统的设备，统称为唤醒源（Wakeup source）。而Wakeup source的选择，则是PM设计工作（特别是Sleep、Standby等功能）的重点。

经过上面的解释后，为了统一，蜗蜗会把表述从用户角度（Hibernate和Sleep）切换为底层实现上（STD、STR和Standby）。

#### 3. 软件架构及模块汇整

##### 3.1 软件架构

内核中该部分的软件架构大概可以分为三个层次，如下图：

[![Hibernate & Sleep Architecture](/content/uploadfile/201406/436e97bb08d0bb83e6940cfe1bc3a74320140610081117.gif "Hibernate & Sleep Architecture")](/content/uploadfile/201406/7c4055529e1ae140ce2573ef7de42bfd20140610081115.gif)

1）API Layer，描述用户空间API的一个抽象层。

这里的API有两类，一类涉及Hibernate和Sleep两个功能（global APIs），包括实际功能、测试用功能、Debug用功能等，通过sysfs和debugfs两种形式提供；另一类是Hibernate特有的（STD APIs），通过sysfs和字符设备两种形式提供。

2）PM Core，电源管理的核心逻辑层，位于kernel/power/目录下，包括主功能（main）、STD、STR&Standby以及辅助功能（assistant）等多个子模块。

主功能，主要负责实现global APIs相关的逻辑，为用户空间提供相应的API；

STD，包括hibernate、snapshot、swap、block\_io等子模块，负责实现STD功能和硬件无关的逻辑；

STR&Stanby，包括suspend和suspend\_test两个子模块，负责实现STR、Standby等功能和硬件无关的逻辑。

3）PM Driver，电源管理驱动层，涉及体系结构无关驱动、体系结构有关驱动、设备模型以及各个设备驱动等多个软件模块。

##### 3.2 用户空间接口

**3.2.1 /sys/power/state**

state是sysfs中一个文件，为Generic PM的核心接口，在“kernel/power/main.c”中实现，用于将系统置于指定的Power State（供电模式，如Hibernate、Sleep、Standby等）。不同的电源管理功能，在底层的实现，就是在不同Power State之间切换。

读取该文件，返回当前系统支持的Power State，形式为字符串。在内核中，有两种类型的Power State，一种是Hibernate相关的，名称为“disk”，除“disk”之外，内核在"kernel/power/suspend.c"中通过数组的形式定义了另外3个state，如下：

```
   1: const char *const pm_states[PM_SUSPEND_MAX] = {
```

```
   2:         [PM_SUSPEND_FREEZE]     = "freeze",
```

```
   3:         [PM_SUSPEND_STANDBY]    = "standby",
```

```
   4:         [PM_SUSPEND_MEM]        = "mem",
```

```
   5: };
```

> 这些Power State的解释如下：
>
> ▆ freeze
>
> 这种Power State，并不涉及具体的Hardware或Driver，只是冻结所有的进程，包括用户空间进程及内核线程。和我们熟知的“冬眠”和“睡眠”相比，就称为“**闭目养神**”吧（可想而知，能节省的能量是有限的）。
>
> 【注：我们在之前的描述中，并没有特别描述该State，因为它在较早的内核中，只是Sleep、Hibernate等功能的一部分，只是在近期才独立出来。另外一个原因是，该state的省电效果不是很理想，所以其引用场景也是有限的。】
>
> ▆ standby，即第2章所描述的Standby状态。
>
> ▆ mem，即通常所讲的Sleep功能，也是第2章所描述的STR，Suspend to RAM。
>
> ▆ disk，即Hibernate功能，也是第2章所描述的STD，Suspend to Disk。

写入特定的Power State字符串，将会把系统置为该模式。

**3.2.2 /sys/power/pm\_trace**

PM Trace用于提供电源管理过程中的Trace记录，由“CONFIG\_PM\_TRACE”宏定义（kernel/power/Kconfig）控制是否编译进内核，并由“/sys/power/pm\_trace”文件在运行时控制是否使能该功能。

该功能的具体实现是“平台相关”的，我们这里暂不描述。

**3.2.3 /sys/power/pm\_test**

PM test用于对电源管理功能的测试，由“CONFIG\_PM\_DEBUG”宏定义（kernel/power/Kconfig）控制是否编译进内核。其核心思想是：

> ▆ 将电源管理过程按照先后顺序，划分为多个步骤，如core、platform、devices等。这些步骤称作PM Test Level。
>
> ▆ 系统通过一个全局变量（pm\_test\_level），保存系统当前的PM Test Level。该变量的值可以通过”/sys/power/pm\_test“文件获取及修改。
>
> ▆ 在每一个电源管理步骤结束后，插入PM test代码，该代码以当前执行步骤为参数，会判断当前的PM Test Level和执行步骤是否一致，如果一致，则说明该步骤执行成功。出于Test考量，执行成功后，系统会打印Test信息，并在等待一段时间后，退出PM过程。
>
> ▆ 开发人员可以通过修改全局的Test Level，有目的测试所关心的步骤是否执行成功。

上面已经讲了，该文件用于获取及修改PM Test Level，具体的Level信息在“kernel/power/main.c”中定义，格式如下（具体的意义，比较简单，对着相关的代码看，非常清晰，这里就不啰嗦了）：

```
   1: static const char * const pm_tests[__TEST_AFTER_LAST] = {
```

```
   2:         [TEST_NONE] = "none",
```

```
   3:         [TEST_CORE] = "core",
```

```
   4:         [TEST_CPUS] = "processors",
```

```
   5:         [TEST_PLATFORM] = "platform",
```

```
   6:         [TEST_DEVICES] = "devices",
```

```
   7:         [TEST_FREEZER] = "freezer",
```

```
   8: };
```

**3.2.4 /sys/power/wakeup\_count**

该接口只和Sleep功能有关，因此由“CONFIG\_PM\_SLEEP”宏定义（kernel/power/Kconfig）控制。它的存在，是为了解决Sleep和Wakeup之间的同步问题。

我们知道，系统睡眠后，可以通过保留的Wakeup source唤醒系统。而在当今的CPU体系中，唤醒系统就是唤醒CPU，而唤醒CPU的唯一途径，就是Wakeup source产生中断（内核称作Wakeup event）。而内核要保证在多种状态下，Sleep/Wakeup的行为都能正常，如下：

> ▆ 系统处于sleep状态时，产生了Wakeup event。此时应该直接唤醒系统。这一点没有问题。
>
> ▆ 系统在进入sleep的过程中，产生了Wakeup event。此时应该放弃进入sleep。
>
> 这一点就不那么容易做到了。例如，当Wakeup event发生在“/sys/power/state”被写之后、内核执行freeze操作之前。此时用户空间程序依旧可以处理Wakeup event，或者只是部分处理。而内核却以为该Event已经被处理，因此并不会放弃此次sleep动作。
>
> 这就会造成，Wakeup event发生后，用户空间程序已经后悔了，不想睡了，但最终还是睡下去了。直到下一个Wakeup event到来。

为了解决上面的问题，内核提供wkaeup\_count机制，配合“/sys/power/state”，以实现Sleep过程中的同步。该机制的操作行为如下：

> ▆ wakeup\_count是内核用来保存当前wakeup event发生的计数。
>
> ▆ 用户空间程序在写入state切换状态之前，应先读取wakeup\_count并把获得的count写回给wakeup\_count。
>
> ▆ 内核会比对写回的count和当前的count是否一致，如果不一致，说明在读取/写回操作之间，产生了新的的wakeup event，内核就会返回错误。
>
> ▆ 用户空间程序检测到写入错误之后，不能继续后的动作，需要处理响应的event并伺机再次读取/写回wakeup\_count。
>
> ▆ 如果内核比对一致，会记录write wakeup\_count成功时的event快照，后面继续suspend动作时，会检查是否和快照相符，如果不符，会终止suspend。
>
> ▆ 用户空间程序检测到写入正确后，可以继续对state的写入，以便发起一次状态切换。而此时是安全的。

蜗蜗会在后续的文章中，详细描述该机制在内核中的实现逻辑，这里暂不做进一步说明。

**3.2.5 /sys/power/disk**

该接口是STD特有的。用于设置或获取STD的类型。当前内核支持的STD类型包括：

```
   1: static const char * const hibernation_modes[] = {
```

```
   2:         [HIBERNATION_PLATFORM]  = "platform",
```

```
   3:         [HIBERNATION_SHUTDOWN]  = "shutdown",
```

```
   4:         [HIBERNATION_REBOOT]    = "reboot",
```

```
   5: #ifdef CONFIG_SUSPEND
```

```
   6:         [HIBERNATION_SUSPEND]   = "suspend",
```

```
   7: #endif
```

```
   8: };
```

> ▆ platform，表示使用平台特有的机制，处理STD操作，如使用hibernation\_ops等。
>
> ▆ shutdown，通过关闭系统实现STD，内核会调用kernel\_power\_off接口。
>
> ▆ reboot，通过重启系统实现STD，内核会调用kernel\_restart接口。
>
> 【注：以上两个kernel\_xxx接口的实现，可参考“[Generic PM之Reboot过程](/pm_subsystem/reboot.html)”。】
>
> ▆ suspend，利用STR功能，实现STD。该类型下，STD和STR底层的处理逻辑类似。

**3.2.6 /sys/power/image\_size**

该接口也是STD特有的。我们知道，STD的原理是将当前的运行上下文保存在系统的disk（如NAND Flash，如硬盘），然后选择合适的方式关闭或重启系统。保存上下文是需要存储空间的，不光是disk中的存储空间，也包括位于内存的用于交换或缓冲的空间。

而该接口，就是设置或者获取当前内存中需要分配多少空间，用于缓冲需要写入到disk的数据。单位为byte。

**3.2.6 /sys/power/reserverd\_size**

reserverd\_size用于指示预留多少内存空间，用于在->freeze() 和 ->freeze\_noirq()过程中保存设备驱动分配的空间。以免在STD的过程中丢失。

**3.2.7 /sys/power/resume**

该接口也是STD特有的。正常情况下，在重新开机后，内核会在后期的初始化过程中，读取保存在disk中的image，并恢复系统。而该接口，提供了一种在用户空间手动的读取image并恢复系统的方法。

通常情况下，该操作出现在系统正常运行的过程中，需要加载并执行另外的image。

**3.2.8 debugfs/suspend\_status**

该接口是以debugfs的形式，向用户空间提供suspend过程的统计信息，包括：成功的次数、失败的次数、freeze失败的次数等等。

**3.2.9 /dev/snapshot**

该接口也是STD特有的。它通过字符设备的形式，向用户空间提供software的STD操作。我们会在后续的文章中详细描述。

*原创文章，转发请注明出处。蜗窝科技，[www.wowotech.net](/pm_subsystem/std_str_func.html)。*
