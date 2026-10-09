---
title: "Linux电源管理(7)_Wakeup events framework"
date: 2014-09-09T22:43:55+08:00
url: "/pm_subsystem/wakeup_events_framework.html"
gid: "86"
emlog_type: "blog"
summary: "本文继续“ Linux电源管理(6)_Generic PM之Suspend功能 ”中有关suspend同步以及PM wakeup的话题。这个话题，是近几年Linux kernel最具争议的话题之一，在国外Linux开发论坛，经常可以看到围绕该话题的辩论。辩论的时间跨度和空间跨度可以持续很长，且无法达成一致。 wakeup events framework是这个话题的一个临时性的解决方案，包括wak"
author: "wowo"
category: "电源管理子系统"
category_alias: "pm_subsystem"
tags: ["Linux", "电源管理", "wakeup", "events", "framework"]
views: 94346
comment_count: 94
aliases:
  - "/pm_subsystem/86.html"
  - "/86.html"
---

#### 1. 前言

本文继续“[Linux电源管理(6)\_Generic PM之Suspend功能](/pm_subsystem/suspend_and_resume.html)”中有关suspend同步以及PM wakeup的话题。这个话题，是近几年Linux kernel最具争议的话题之一，在国外Linux开发论坛，经常可以看到围绕该话题的辩论。辩论的时间跨度和空间跨度可以持续很长，且无法达成一致。

wakeup events framework是这个话题的一个临时性的解决方案，包括wake lock、wakeup count、autosleep等机制。它们就是本文的话题。

#### 2. wakeup events framework要解决的问题

我们知道，系统处于suspend状态，可通过wakeup events唤醒。具体的wakeup events可以是按键按下，可以是充电器插入，等等。但是，如果在suspend的过程中，产生了wakeup events，怎么办？答案很肯定，"wakeup"系统。由于此时系统没有真正suspend，所以这的"wakeup"是个假动作，实际上只是终止suspend。

但由于系统在suspend的过程中，会进行process freeze、 device suspend等操作，而这些操作可能导致内核或用户空间程序不能及时获取wakeup events，从而使系统不能正确wakeup，这就是wakeup events framework要解决的问题：system suspend和system wakeup events之间的同步问题。

#### 3. wakeup events framework的功能总结

仔细推敲一下，上面所讲的同步问题包括两种情况：

情况1：内核空间的同步

> wakeup events产生后，通常是以中断的形式通知device driver。driver会处理events，处理的过程中，系统不能suspend。
>
> 注1：同步问题只存在于中断开启的情况，因为若中断关闭，就不会产生wakeup events，也就不存在同步的概念。

情况2：用户空间的同步

> 一般情况下，driver对wakeup events处理后，会交给用户空间程序继续处理，处理的过程，也不允许suspend。这又可以分为两种情况：
>
> 1）进行后续处理的用户进程，根本没有机会被调度，即该wakeup events无法上报到用户空间。
>
> 2）进行后续处理的用户进程被调度，处理的过程中（以及处理结束后，决定终止suspend操作），系统不能suspend。

因此，wakeup events framework就包括3大功能：

> 解决内核空间同步问题（framework的核心功能）；
>
> 解决用户空间同步问题的情景1（wakeup count功能）；
>
> 解决用户空间同步问题的情景2（wake lock功能） 。

注2：

用户空间同步的两种情况，咋一看，非常合乎情理，kernel你得好好处理！但事实上，该同步问题牵涉到了另外一个比较有争议的话题：日常的电源管理机制。是否要基于suspend实现？系统何时进入低功耗状态，应该由谁决定？kernel还是用户空间程序？

这最终会决定是否存在用空间同步问题。但是，在当前这个时间点，对这个话题，Linux kernel developers和Android developers持相反的观点。这也造成了wakeup events framework在实现上的撕裂。Kernel的本意是不愿处理用户空间同步问题的，但为了兼容Android平台，不得不增加相关的功能（Wakeup count和Wake lock）。

蜗蜗会在下一篇文章和大家探讨该话题，本文就先focus在wakeup events framework上。

#### 4. wakeup events framework architecture

下面图片描述了wakeup events framework的architecture：

[![Wakeup events framework architecture](/content/uploadfile/201409/c0fbbea723f580a533337288b70d499b20140909151758.gif "Wakeup events framework architecture")](/content/uploadfile/201409/3131285c936326032617b4226ec49bdc20140909151756.gif)

图片中红色边框的block是wakeup events相关的block：

1）wakeup events framework core，在drivers/base/power/wakeup.c中实现，提供了wakeup events framework的核心功能，包括：

> 抽象wakeup source和wakeup event的概念；
>
> 向各个device driver提供wakeup source的注册、使能等接口；
>
> 向各个device driver提供wakeup event的上报、停止等接口；
>
> 向上层的PM core（包括wakeup count、auto sleep、suspend、hibernate等模块）提供wakeup event的查询接口，以判断是否可以suspend、是否需要终止正在进行的suspend。

2）wakeup events framework sysfs，将设备的wakeup信息，以sysfs的形式提供到用户空间，供用户空间程序查询、配置。在drivers/base/power/sysfs.c中实现。

3）wake lock/unlock，为了兼容Android旧的wakeup lock机制而留下的一个后门，扩展wakeup events framework的功能，允许用户空间程序报告/停止wakeup events。换句话说，该后门允许用户空间的任一程序决定系统是否可以休眠。

4）wakeup count，基于wakeup events framework，解决用户空间同步的问题。

5）auto sleep，允许系统在没有活动时（即一段时间内，没有产生wakeup event），自动休眠。

注3：在Linux kernel看来，power是系统的核心资源，不应开放给用户程序随意访问（wake lock机制违背了这个原则）。而在运行时的电源管理过程中，系统何时进入低功耗状态，也不是用户空间程序能决定的（auto sleep中枪了）。因此，kernel对上述功能的支持，非常的不乐意，我们可以从kernel/power/main.c中sysfs attribute文件窥见一斑（只要定义了PM\_SLEEP，就一定支持wakeup count功能，但autosleep和wake lock功能，由另外的宏定义控制）：

```
   1: static struct attribute * g[] = {
```

```
   2:         &state_attr.attr,
```

```
   3: #ifdef CONFIG_PM_TRACE
```

```
   4:         &pm_trace_attr.attr,
```

```
   5:         &pm_trace_dev_match_attr.attr,
```

```
   6: #endif
```

```
   7: #ifdef CONFIG_PM_SLEEP
```

```
   8:         &pm_async_attr.attr,
```

```
   9:         &wakeup_count_attr.attr,
```

```
  10: #ifdef CONFIG_PM_AUTOSLEEP
```

```
  11:         &autosleep_attr.attr,
```

```
  12: #endif
```

```
  13: #ifdef CONFIG_PM_WAKELOCKS
```

```
  14:         &wake_lock_attr.attr,
```

```
  15:         &wake_unlock_attr.attr,
```

```
  16: #endif
```

```
  17: #ifdef CONFIG_PM_DEBUG
```

```
  18:         &pm_test_attr.attr,
```

```
  19: #endif
```

```
  20: #ifdef CONFIG_PM_SLEEP_DEBUG
```

```
  21:         &pm_print_times_attr.attr,
```

```
  22: #endif
```

```
  23: #endif
```

```
  24: #ifdef CONFIG_FREEZER
```

```
  25:         &pm_freeze_timeout_attr.attr,
```

```
  26: #endif
```

```
  27:         NULL,
```

```
  28: };
```

#### 5. 代码分析

##### 5.1  wakeup source和wakeup event

在kernel中，可以唤醒系统的只有设备(struct device)，但并不是每个设备都具备唤醒功能，那些具有唤醒功能的设备称作wakeup source。是时候回到这篇文章中了（[Linux设备模型(5)\_device和device driver](/device_model/device_and_driver.html)），在那里，介绍struct device结构时，涉及到一个struct dev\_pm\_info类型的power变量，蜗蜗说留待后面的专题讲解。我们再回忆一下struct device结构：

```
   1: struct device {
```

```
   2:         ...
```

```
   3:         struct dev_pm_info      power;
```

```
   4:         ...
```

```
   5: };
```

该结构中有一个power变量，保存了和wakeup event相关的信息，让我们接着看一下struct dev\_pm\_info数据结构（只保留和本文有关的内容）：

```
   1: struct dev_pm_info {
```

```
   2:         ...
```

```
   3:         unsigned int            can_wakeup:1;
```

```
   4:         ...
```

```
   5: #ifdef CONFIG_PM_SLEEP
```

```
   6:         ...
```

```
   7:         struct wakeup_source    *wakeup;
```

```
   8:         ...
```

```
   9: #else
```

```
  10:         unsigned int            should_wakeup:1;
```

```
  11: #endif
```

```
  12: };
```

can\_wakeup，标识本设备是否具有唤醒能力。只有具备唤醒能力的设备，才会在sysfs中有一个power目录，用于提供所有的wakeup信息，这些信息是以struct wakeup\_source的形式组织起来的。也就是上面wakeup指针。具体有哪些信息呢？让我们看看struct wakeup\_source的定义。

```
   1: /* include\linux\pm_wakeup.h */
```

```
   2: struct wakeup_source {
```

```
   3:         const char              *name;
```

```
   4:         struct list_head        entry;
```

```
   5:         spinlock_t              lock;
```

```
   6:         struct timer_list       timer;
```

```
   7:         unsigned long           timer_expires;
```

```
   8:         ktime_t total_time;
```

```
   9:         ktime_t max_time;
```

```
  10:         ktime_t last_time;
```

```
  11:         ktime_t start_prevent_time;
```

```
  12:         ktime_t prevent_sleep_time;
```

```
  13:         unsigned long           event_count;
```

```
  14:         unsigned long           active_count;
```

```
  15:         unsigned long           relax_count;
```

```
  16:         unsigned long           expire_count;
```

```
  17:         unsigned long           wakeup_count;
```

```
  18:         bool                    active:1;
```

```
  19:         bool                    autosleep_enabled:1;
```

```
  20: };
```

因此，一个wakeup source代表了一个具有唤醒能力的设备，也称该设备为一个wakeup source。该结构中各个字段的意义如下：

> name，该wakeup source的名称，一般为对应的device name（有个例外，就是wakelock）；
>
> entery，用于将所有的wakeup source挂在一个链表中；
>
> timer、timer\_expires，一个wakeup source产生了wakeup event，称作wakeup source activate，wakeup event处理完毕后（不再需要系统为此保持active），称作deactivate。activate和deactivate的操作可以由driver亲自设置，也可以在activate时，指定一个timeout时间，时间到达后，由wakeup events framework自动将其设置为deactivate状态。这里的timer以及expires时间，就是用来实现该功能；
>
> total\_time，该wakeup source处于activate状态的总时间（可以指示该wakeup source对应的设备的繁忙程度、耗电等级）；
>
> max\_time，该wakeup source持续处于activate状态的最大时间（越长越不合理）；
>
> last\_time，该wakeup source上次active的开始时间；
>
> start\_prevent\_time，该wakeup source开始阻止系统自动睡眠（auto sleep）的时间点；
>
> prevent\_sleep\_time，该wakeup source阻止系统自动睡眠的总时间；
>
> event\_count，wakeup source上报的event个数；
>
> active\_count，wakeup source activate的次数；
>
> relax\_count， wakeup source deactivate的次数；
>
> expire\_count，wakeup source timeout到达的次数；
>
> wakeup\_count，wakeup source终止suspend过程的次数；
>
> active，wakeup source的activate状态；
>
> autosleep\_enabled，记录系统auto sleep的使能状态（每个wakeup source都重复记录这样一个状态，这种设计真实不敢恭维！）。

wakeup source代表一个具有唤醒能力的设备，该设备产生的可以唤醒系统的事件，就称作wakeup event。当wakeup source产生wakeup event时，需要将wakeup source切换为activate状态；当wakeup event处理完毕后，要切换为deactivate状态。因此，我们再来理解一下几个wakeup source比较混淆的变量：event\_count, active\_count和wakeup\_count：

> event\_count，wakeup source产生的wakeup event的个数；
>
> active\_count，产生wakeup event时，wakeup source需要切换到activate状态。但并不是每次都要切换，因此有可能已经处于activate状态了。因此active\_count可能小于event\_count，换句话说，很有可能在前一个wakeup event没被处理完时，又产生了一个。这从一定程度上反映了wakeup source所代表的设备的繁忙程度；
>
> wakeup\_count，wakeup source在suspend过程中产生wakeup event的话，就会终止suspend过程，该变量记录了wakeup source终止suspend过程的次数（如果发现系统总是suspend失败，检查一下各个wakeup source的该变量，就可以知道问题出在谁身上了）。

##### 5.2 几个counters

在drivers\base\power\wakeup.c中，有几个比较重要的计数器，是wakeup events framework的实现基础，包括：

1）registered wakeup events和saved\_count

记录了系统运行以来产生的所有wakeup event的个数，在wakeup source上报event时加1。

这个counter对解决用户空间同步问题很有帮助，因为一般情况下（无论是用户程序主动suspend，还是auto sleep），由专门的进程（或线程）触发suspend。当这个进程判断系统满足suspend条件，决定suspend时，会记录一个counter值(saved\_count)。在后面suspend的过程中，如果系统发现counter有变，则说明系统产生了新的wakeup event，这样就可以终止suspend。

该功能即是wakeup count功能，会在后面更详细的说明。

2）wakeup events in progress

记录正在处理的event个数。

当wakeup source产生wakeup event时，会通过wakeup events framework提供的接口将wakeup source设置为activate状态。当该event处理结束后，设置为deactivate状态。activate到deactivate的区间，表示该event正在被处理。

当系统中有任何正在被处理的wakeup event时，则不允许suspend。如果suspend正在进行，则要终止。

思考一个问题：registered wakeup events在什么时候增加？答案是在wakeup events in progress减小时，因为已经完整的处理完一个event了，可以记录在案了。

基于这种特性，kernel将它俩合并成一个32位的整型数，以原子操作的形式，一起更新。这种设计巧妙的让人叫绝，值得我们学习。具体如下：

```
   1: /*
```

```
   2:  * Combined counters of registered wakeup events and wakeup events in progress.
```

```
   3:  * They need to be modified together atomically, so it's better to use one
```

```
   4:  * atomic variable to hold them both.
```

```
   5:  */
```

```
   6: static atomic_t combined_event_count = ATOMIC_INIT(0);
```

```
   7:  
```

```
   8: #define IN_PROGRESS_BITS        (sizeof(int) * 4)
```

```
   9: #define MAX_IN_PROGRESS         ((1 << IN_PROGRESS_BITS) - 1)
```

```
  10:  
```

```
  11: static void split_counters(unsigned int *cnt, unsigned int *inpr)
```

```
  12: {
```

```
  13:         unsigned int comb = atomic_read(&combined_event_count);
```

```
  14:  
```

```
  15:         *cnt = (comb >> IN_PROGRESS_BITS);
```

```
  16:         *inpr = comb & MAX_IN_PROGRESS;
```

```
  17: }
```

定义和读取。

```
   1: cec = atomic_add_return(MAX_IN_PROGRESS, &combined_event_count);
```

**wakeup events in progress减1，registered wakeup events加1，这个语句简直是美轮美奂，读者可以仔细品味一下，绝对比看xxx片还过瘾，哈哈。**

```
   1: cec = atomic_inc_return(&combined_event_count);
```

wakeup events in progress加1。

##### 5.3 wakeup events framework的核心功能

wakeup events framework的核心功能体现在它向底层的设备驱动所提供的用于上报wakeup event的接口，这些接口根据操作对象可分为两类，具体如下。

类型一（操作对象为wakeup source，编写设备驱动时，一般不会直接使用）：

```
   1: /* include/linux/pm_wakeup.h */
```

```
   2: extern void __pm_stay_awake(struct wakeup_source *ws);
```

```
   3: extern void __pm_relax(struct wakeup_source *ws);
```

```
   4: extern void __pm_wakeup_event(struct wakeup_source *ws, unsigned int msec);
```

> \_\_pm\_stay\_awake，通知PM core，ws产生了wakeup event，且正在处理，因此不允许系统suspend（stay awake）；
>
> \_\_pm\_relax，通知PM core，ws没有正在处理的wakeup event，允许系统suspend（relax）；
>
> \_\_pm\_wakeup\_event，为上边两个接口的功能组合，通知PM core，ws产生了wakeup event，会在msec毫秒内处理结束（wakeup events framework自动relax）。
>
> 注4：\_\_pm\_stay\_awake和\_\_pm\_relax应成对调用。
>   
> 注5：上面3个接口，均可以在中断上下文调用。

类型二（操作对象为device，为设备驱动的常用接口）：

```
   1: /* include/linux/pm_wakeup.h */
```

```
   2: extern int device_wakeup_enable(struct device *dev);
```

```
   3: extern int device_wakeup_disable(struct device *dev);
```

```
   4: extern void device_set_wakeup_capable(struct device *dev, bool capable);
```

```
   5: extern int device_init_wakeup(struct device *dev, bool val);
```

```
   6: extern int device_set_wakeup_enable(struct device *dev, bool enable);
```

```
   7: extern void pm_stay_awake(struct device *dev);
```

```
   8: extern void pm_relax(struct device *dev);
```

```
   9: extern void pm_wakeup_event(struct device *dev, unsigned int msec);
```

> device\_set\_wakeup\_capable，设置dev的can\_wakeup标志（enable或disable，可参考5.1小节），并增加或移除该设备在sysfs相关的power文件；
>
> device\_wakeup\_enable/device\_wakeup\_disable/device\_set\_wakeup\_enable，对于can\_wakeup的设备，使能或者禁止wakeup功能。主要是对struct wakeup\_source结构的相关操作；
>
> device\_init\_wakeup，设置dev的can\_wakeup标志，若是enable，同时调用device\_wakeup\_enable使能wakeup功能；
>
> pm\_stay\_awake、pm\_relax、pm\_wakeup\_event，直接调用上面的wakeup source操作接口，操作device的struct wakeup\_source变量，处理wakeup events。

**5.3.1 device\_set\_wakeup\_capable**

该接口位于在drivers/base/power/wakeup.c中，代码如下：

```
   1: void device_set_wakeup_capable(struct device *dev, bool capable)
```

```
   2: {
```

```
   3:         if (!!dev->power.can_wakeup == !!capable)
```

```
   4:                 return;
```

```
   5:  
```

```
   6:         if (device_is_registered(dev) && !list_empty(&dev->power.entry)) {
```

```
   7:                 if (capable) {
```

```
   8:                         if (wakeup_sysfs_add(dev))
```

```
   9:                                 return;
```

```
  10:                 } else {
```

```
  11:                         wakeup_sysfs_remove(dev);
```

```
  12:                 }
```

```
  13:         }
```

```
  14:         dev->power.can_wakeup = capable;
```

```
  15: }
```

该接口的实现很简单，主要包括sysfs的add/remove和can\_wakeup标志的设置两部分。如果设置can\_wakeup标志，则调用wakeup\_sysfs\_add，向该设备的sysfs目录下添加power文件夹，并注册相应的attribute文件。如果清除can\_wakeup标志，执行sysfs的移除操作。

wakeup\_sysfs\_add/wakeup\_sysfs\_remove位于drivers/base/power/sysfs.c中，对wakeup events framework来说，主要包括如下的attribute文件：

```
   1: static struct attribute *wakeup_attrs[] = {
```

```
   2: #ifdef CONFIG_PM_SLEEP
```

```
   3:         &dev_attr_wakeup.attr,
```

```
   4:         &dev_attr_wakeup_count.attr,
```

```
   5:         &dev_attr_wakeup_active_count.attr,
```

```
   6:         &dev_attr_wakeup_abort_count.attr,
```

```
   7:         &dev_attr_wakeup_expire_count.attr,
```

```
   8:         &dev_attr_wakeup_active.attr,
```

```
   9:         &dev_attr_wakeup_total_time_ms.attr,
```

```
  10:         &dev_attr_wakeup_max_time_ms.attr,
```

```
  11:         &dev_attr_wakeup_last_time_ms.attr,
```

```
  12: #ifdef CONFIG_PM_AUTOSLEEP
```

```
  13:         &dev_attr_wakeup_prevent_sleep_time_ms.attr,
```

```
  14: #endif
```

```
  15: #endif
```

```
  16:         NULL,
```

```
  17: };
```

```
  18: static struct attribute_group pm_wakeup_attr_group = {
```

```
  19:         .name   = power_group_name,
```

```
  20:         .attrs  = wakeup_attrs,
```

```
  21: };
```

1）wakeup

读，获得设备wakeup功能的使能状态，返回"enabled"或"disabled"字符串。

写，更改设备wakeup功能的使能状态，根据写入的字符串（"enabled"或"disabled"），调用device\_set\_wakeup\_enable接口完成实际的状态切换。

设备wakeup功能是否使能，取决于设备的can\_wakeup标志，以及设备是否注册有相应的struct wakeup\_source指针。即can wakeup和may wakeup，如下：

```
   1: /*
```

```
   2:  * Changes to device_may_wakeup take effect on the next pm state change.
```

```
   3:  */
```

```
   4:  
```

```
   5: static inline bool device_can_wakeup(struct device *dev)
```

```
   6: {
```

```
   7:         return dev->power.can_wakeup;
```

```
   8: }
```

```
   9:  
```

```
  10: static inline bool device_may_wakeup(struct device *dev)
```

```
  11: {
```

```
  12:         return dev->power.can_wakeup && !!dev->power.wakeup;
```

```
  13: }
```

2）wakeup\_count

只读，获取dev->power.wakeup->event\_count值。有关event\_count的意义，请参考5.1小节，下同。顺便抱怨一下，这个attribute文件的命名简直糟糕透顶了！直接用event\_count就是了，用什么wakeup\_count，会和wakeup source中的同名字段搞混淆的！

3）wakeup\_active\_count，只读，获取dev->power.wakeup->active\_count值。

4）wakeup\_abort\_count，只读，获取dev->power.wakeup->wakeup\_count值。

5）wakeup\_expire\_count，只读，获dev->power.wakeup->expire\_count取值。

6）wakeup\_active，只读，获取dev->power.wakeup->active值。

7）wakeup\_total\_time\_ms，只读，获取dev->power.wakeup->total\_time值，单位为ms。

8）wakeup\_max\_time\_ms，只读，获dev->power.wakeup->max\_time取值，单位为ms。

9）wakeup\_last\_time\_ms，只读，获dev->power.wakeup->last\_time取值，单位为ms。

10）wakeup\_prevent\_sleep\_time\_ms，只读，获取dev->power.wakeup->prevent\_sleep\_time值，单位为ms。

注6：阅读上述代码时，我们可以看到很多类似“!!dev->power.can\_wakeup == !!capable”的、带有两个“！”操作符的语句，是为了保证最后的操作对象非0即1。这从侧面反映了内核开发者的严谨程度，值得我们学习。

**5.3.2 device\_wakeup\_enable/device\_wakeup\_disable/device\_set\_wakeup\_enable**

以device\_wakeup\_enable为例（其它类似，就不浪费屏幕了）：

```
   1: int device_wakeup_enable(struct device *dev)
```

```
   2: {
```

```
   3:         struct wakeup_source *ws;
```

```
   4:         int ret;
```

```
   5:  
```

```
   6:         if (!dev || !dev->power.can_wakeup)
```

```
   7:                 return -EINVAL;
```

```
   8:  
```

```
   9:         ws = wakeup_source_register(dev_name(dev));
```

```
  10:         if (!ws)
```

```
  11:                 return -ENOMEM;
```

```
  12:  
```

```
  13:         ret = device_wakeup_attach(dev, ws);
```

```
  14:         if (ret)
```

```
  15:                 wakeup_source_unregister(ws);
```

```
  16:  
```

```
  17:         return ret;
```

```
  18: }
```

也很简单：

> a）若设备指针为空，或者设备不具备wakeup能力，免谈，报错退出。
>
> b）调用wakeup\_source\_register接口，以设备名为参数，创建并注册一个wakeup source。
>
> c）调用device\_wakeup\_attach接口，将新建的wakeup source保存在dev->power.wakeup指针中。
>
> wakeup\_source\_register接口的实现也比较简单，会先后调用wakeup\_source\_create、wakeup\_source\_prepare、wakeup\_source\_add等接口，所做的工作包括分配struct wakeup\_source变量所需的内存空间、初始化内部变量、将新建的wakeup source添加到名称为wakeup\_sources的全局链表中、等等。
>
> device\_wakeup\_attach接口更为直观，不过有一点我们要关注，如果设备的dev->power.wakeup非空，也就是说之前已经有一个wakeup source了，是不允许再enable了的，会报错返回。

**5.3.3 pm\_stay\_awake**

当设备有wakeup event正在处理时，需要调用该接口通知PM core，该接口的实现如下：

```
   1: void pm_stay_awake(struct device *dev)
```

```
   2: {
```

```
   3:         unsigned long flags;
```

```
   4:  
```

```
   5:         if (!dev)
```

```
   6:                 return;
```

```
   7:  
```

```
   8:         spin_lock_irqsave(&dev->power.lock, flags);
```

```
   9:         __pm_stay_awake(dev->power.wakeup);
```

```
  10:         spin_unlock_irqrestore(&dev->power.lock, flags);
```

```
  11: }
```

呵呵，直接调用\_\_pm\_stay\_awake，这也是本文的index里没有该接口的原因。接着看代码。

```
   1: void __pm_stay_awake(struct wakeup_source *ws)
```

```
   2: {
```

```
   3:         unsigned long flags;
```

```
   4:  
```

```
   5:         if (!ws)
```

```
   6:                 return;
```

```
   7:  
```

```
   8:         spin_lock_irqsave(&ws->lock, flags);
```

```
   9:  
```

```
  10:         wakeup_source_report_event(ws);
```

```
  11:         del_timer(&ws->timer);
```

```
  12:         ws->timer_expires = 0;
```

```
  13:  
```

```
  14:         spin_unlock_irqrestore(&ws->lock, flags);
```

```
  15: }
```

由于pm\_stay\_awake报告的event需要经过pm\_relax主动停止，因此就不再需要timer，所以\_\_pm\_stay\_awake实现是直接调用wakeup\_source\_report\_event，然后停止timer。接着看代码：

```
   1: static void wakeup_source_report_event(struct wakeup_source *ws)
```

```
   2: {
```

```
   3:         ws->event_count++;
```

```
   4:         /* This is racy, but the counter is approximate anyway. */
```

```
   5:         if (events_check_enabled)
```

```
   6:                 ws->wakeup_count++;
```

```
   7:  
```

```
   8:         if (!ws->active)
```

```
   9:                 wakeup_source_activate(ws);
```

```
  10: }
```

> a）增加wakeup source的event\_count，表示该source又产生了一个event。
>
> b）根据events\_check\_enabled变量的状态，决定是否增加wakeup\_count。这和wakeup count的功能有关，到时再详细描述。
>
> c）如果wakeup source没有active，则调用wakeup\_source\_activate，activate之。这也是5.1小节所描述的，event\_count和active\_count的区别所在。wakeup\_source\_activate的代码如下。

```
   1: static void wakeup_source_activate(struct wakeup_source *ws)
```

```
   2: {
```

```
   3:         unsigned int cec;
```

```
   4:  
```

```
   5:         /*
```

```
   6:          * active wakeup source should bring the system
```

```
   7:          * out of PM_SUSPEND_FREEZE state
```

```
   8:          */
```

```
   9:         freeze_wake();
```

```
  10:  
```

```
  11:         ws->active = true;
```

```
  12:         ws->active_count++;
```

```
  13:         ws->last_time = ktime_get();
```

```
  14:         if (ws->autosleep_enabled)
```

```
  15:                 ws->start_prevent_time = ws->last_time;
```

```
  16:  
```

```
  17:         /* Increment the counter of events in progress. */
```

```
  18:         cec = atomic_inc_return(&combined_event_count);
```

```
  19:  
```

```
  20:         trace_wakeup_source_activate(ws->name, cec);
```

```
  21: }
```

> a）调用freeze\_wake，将系统从suspend to freeze状态下唤醒。有关freeze功能，请参考相关的文章。
>
> b）设置active标志，增加active\_count，更新last\_time。
>
> c）如果使能了autosleep，更新start\_prevent\_time，因为此刻该wakeup source会开始阻止系统auto sleep。具体可参考auto sleep的功能描述。
>
> d）增加“wakeup events in progress”计数（5.2小节有描述）。该操作是wakeup events framework的灵魂，增加该计数，意味着系统正在处理的wakeup event数目不为零，则系统不能suspend。

到此，pm\_stay\_awake执行结束，意味着系统至少正在处理一个wakeup event，因此不能suspend。那处理完成后呢？driver要调用pm\_relax通知PM core。

**5.3.4 pm\_relax**

pm\_relax和pm\_stay\_awake成对出现，用于在event处理结束后通知PM core，其实现如下：

```
   1: /**
```

```
   2:  * pm_relax - Notify the PM core that processing of a wakeup event has ended.
```

```
   3:  * @dev: Device that signaled the event.
```

```
   4:  *
```

```
   5:  * Execute __pm_relax() for the @dev's wakeup source object.
```

```
   6:  */
```

```
   7: void pm_relax(struct device *dev)
```

```
   8: {
```

```
   9:         unsigned long flags;
```

```
  10:  
```

```
  11:         if (!dev)
```

```
  12:                 return;
```

```
  13:  
```

```
  14:         spin_lock_irqsave(&dev->power.lock, flags);
```

```
  15:         __pm_relax(dev->power.wakeup);
```

```
  16:         spin_unlock_irqrestore(&dev->power.lock, flags);
```

```
  17: }
```

直接调用\_\_pm\_relax，如下：

```
   1: void __pm_relax(struct wakeup_source *ws)
```

```
   2: {
```

```
   3:         unsigned long flags;
```

```
   4:  
```

```
   5:         if (!ws)
```

```
   6:                 return;
```

```
   7:  
```

```
   8:         spin_lock_irqsave(&ws->lock, flags);
```

```
   9:         if (ws->active)
```

```
  10:                 wakeup_source_deactivate(ws);
```

```
  11:         spin_unlock_irqrestore(&ws->lock, flags);
```

```
  12: }
```

如果该wakeup source处于active状态，调用wakeup\_source\_deactivate接口，deactivate之。deactivate接口和activate接口一样，是wakeup events framework的核心逻辑，如下：

```
   1: static void wakeup_source_deactivate(struct wakeup_source *ws)
```

```
   2: {
```

```
   3:         unsigned int cnt, inpr, cec;
```

```
   4:         ktime_t duration;
```

```
   5:         ktime_t now;
```

```
   6:  
```

```
   7:         ws->relax_count++;
```

```
   8:         /*
```

```
   9:          * __pm_relax() may be called directly or from a timer function.
```

```
  10:          * If it is called directly right after the timer function has been
```

```
  11:          * started, but before the timer function calls __pm_relax(), it is
```

```
  12:          * possible that __pm_stay_awake() will be called in the meantime and
```

```
  13:          * will set ws->active.  Then, ws->active may be cleared immediately
```

```
  14:          * by the __pm_relax() called from the timer function, but in such a
```

```
  15:          * case ws->relax_count will be different from ws->active_count.
```

```
  16:          */
```

```
  17:         if (ws->relax_count != ws->active_count) {
```

```
  18:                 ws->relax_count--;
```

```
  19:                 return;
```

```
  20:         }
```

```
  21:  
```

```
  22:         ws->active = false;
```

```
  23:  
```

```
  24:         now = ktime_get();
```

```
  25:         duration = ktime_sub(now, ws->last_time);
```

```
  26:         ws->total_time = ktime_add(ws->total_time, duration);
```

```
  27:         if (ktime_to_ns(duration) > ktime_to_ns(ws->max_time))
```

```
  28:                 ws->max_time = duration;
```

```
  29:  
```

```
  30:         ws->last_time = now;
```

```
  31:         del_timer(&ws->timer);
```

```
  32:         ws->timer_expires = 0;
```

```
  33:  
```

```
  34:         if (ws->autosleep_enabled)
```

```
  35:                 update_prevent_sleep_time(ws, now);
```

```
  36:  
```

```
  37:         /*
```

```
  38:          * Increment the counter of registered wakeup events and decrement the
```

```
  39:          * couter of wakeup events in progress simultaneously.
```

```
  40:          */
```

```
  41:         cec = atomic_add_return(MAX_IN_PROGRESS, &combined_event_count);
```

```
  42:         trace_wakeup_source_deactivate(ws->name, cec);
```

```
  43:  
```

```
  44:  
```

```
  45:         split_counters(&cnt, &inpr);
```

```
  46:         if (!inpr && waitqueue_active(&wakeup_count_wait_queue))
```

```
  47:                 wake_up(&wakeup_count_wait_queue);
```

```
  48: }
```

> a）relax\_count加1（如果relax\_count和active\_count不等，则说明有重复调用，要退出）。
>
> b）清除active标记。
>
> c）更新total\_time、max\_time、last\_time等变量。
>
> d）如果使能auto sleep，更新相关的变量（后面再详细描述）。
>
> e）再欣赏一下艺术，wakeup events in progress减1，registered wakeup events加1。
>
> f）wakeup count相关的处理，后面再详细说明。

**5.3.5 pm\_wakeup\_event**

pm\_wakeup\_event是pm\_stay\_awake和pm\_relax的组合版，在上报event时，指定一个timeout时间，timeout后，自动relax，一般用于不知道何时能处理完成的场景。该接口比较简单，就不一一描述了。

**5.3.6 pm\_wakeup\_pending**

drivers产生的wakeup events，最终要上报到PM core，PM core会根据这些events，决定是否要终止suspend过程。这表现在suspend过程中频繁调用pm\_wakeup\_pending接口上（可参考“[Linux电源管理(6)\_Generic PM之Suspend功能](/pm_subsystem/suspend_and_resume.html)”）。该接口的实现如下：

```
   1: /**
```

```
   2:  * pm_wakeup_pending - Check if power transition in progress should be aborted.
```

```
   3:  *
```

```
   4:  * Compare the current number of registered wakeup events with its preserved
```

```
   5:  * value from the past and return true if new wakeup events have been registered
```

```
   6:  * since the old value was stored.  Also return true if the current number of
```

```
   7:  * wakeup events being processed is different from zero.
```

```
   8:  */
```

```
   9: bool pm_wakeup_pending(void)
```

```
  10: {
```

```
  11:         unsigned long flags;
```

```
  12:         bool ret = false;
```

```
  13:  
```

```
  14:         spin_lock_irqsave(&events_lock, flags);
```

```
  15:         if (events_check_enabled) {
```

```
  16:                 unsigned int cnt, inpr;
```

```
  17:  
```

```
  18:                 split_counters(&cnt, &inpr);
```

```
  19:                 ret = (cnt != saved_count || inpr > 0);
```

```
  20:                 events_check_enabled = !ret;
```

```
  21:         }
```

```
  22:         spin_unlock_irqrestore(&events_lock, flags);
```

```
  23:  
```

```
  24:         if (ret)
```

```
  25:                 print_active_wakeup_sources();
```

```
  26:  
```

```
  27:         return ret;
```

```
  28: }
```

该接口的逻辑比较直观，先抛开wakeup count的逻辑不谈（后面会重点说明），只要正在处理的events不为0，就返回true，调用者就会终止suspend。

**5.4 wakeup count、wake lock和auto sleep**

这篇文章写的有点长了，不能继续了，这几个功能，会接下来的文章中继续分析。

*原创文章，转发请注明出处。蜗窝科技，[www.wowotech.net](/)。*
