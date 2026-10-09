---
title: "Linux电源管理(10)_autosleep"
date: 2014-09-18T23:42:27+08:00
url: "/pm_subsystem/autosleep.html"
gid: "90"
emlog_type: "blog"
summary: "Autosleep也是从Android wakelocks补丁集中演化而来的（ Linux电源管理(9)_wakelocks ），用于取代Android wakelocks中的自动休眠功能。它基于wakeup source实现，从代码逻辑上讲，autosleep是一个简单的功能，但背后却埋藏着一个值得深思的话题： 计算机的休眠（通常是STR、Standby、Hibernate等suspend操作）"
author: "wowo"
category: "电源管理子系统"
category_alias: "pm_subsystem"
tags: ["Linux", "PM", "电源管理", "autosleep"]
views: 58600
comment_count: 54
aliases:
  - "/pm_subsystem/90.html"
  - "/90.html"
---

#### 1. 前言

Autosleep也是从Android wakelocks补丁集中演化而来的（[Linux电源管理(9)\_wakelocks](/pm_subsystem/wakelocks.html)），用于取代Android wakelocks中的自动休眠功能。它基于wakeup source实现，从代码逻辑上讲，autosleep是一个简单的功能，但背后却埋藏着一个值得深思的话题：

计算机的休眠（通常是STR、Standby、Hibernate等suspend操作），应当在什么时候、由谁触发？

蜗蜗在“[Linux电源管理(2)\_Generic PM之基本概念和软件架构](/pm_subsystem/generic_pm_architecture.html)”中有提过，在传统的操作场景下，如PC、笔记本电脑，这个问题很好回答：由用户、在其不想或不再使用时。

但在移动互联时代，用户随时随地都可能使用设备，上面的回答就不再成立，怎么办？这时，Android提出了“Opportunistic suspend（这个词汇太传神了，很难用简洁的中文去翻译，就不翻译了）”的理论，通俗的讲，就是“逮到机会就睡”。而autosleep功能，无论是基于Android wakelocks的autosleep，还是基于wakeup source的autosleep，都是为了实现“Opportunistic suspend”。

相比较“对多样的系统组件单独控制”的电源管理方案（如Linux kernel的Dynamic PM），“Opportunistic suspend”是非常简单的，只要检测到系统没有事情在做（逮到机会），就suspend整个系统。这对系统的开发人员（特别是driver开发者）来说，很容易实现，几乎不需要特别处理。

但困难的是，“系统没有事情在做”的判断依据是什么？能判断准确吗？会不会浪费过多的资源在"susend->resume-supsend…”的无聊动作上？如果只有一个设备在做事情，其它设备岂不是也得陪着耗电？等等…

所以，实现“Opportunistic suspend”机制的autosleep功能，是充满争议的。说实话，也是不优雅的。但它可以解燃眉之急，因而虽然受非议，却在Android设备中广泛使用。

其实Android中很多机制都是这样的（如wakelocks，如binder，等等），可以这样比方：Android是设计中的现实主义，Linux kernel是设计中的理想主义，当理想和现实冲突时，怎么调和？不只是Linux kernel，其它的诸如设计、工作和生活，都会遇到类似的冲突，怎么对待？没有答案，但有一个原则：不要偏执，不要试图追求非黑即白的真理！

我们应该庆幸有Android这样的开源软件，让我们可以对比，可以思考。偏题有点远，言归正传吧，去看看autosleep的实现。

#### 2. 功能总结和实现原理

经过前言的瞎聊，Autosleep的功能很已经很直白了，“系统没有事情在做”的时候，就将系统切换到低功耗状态。

根据使用场景，低功耗状态可以是Freeze、[Standby、Suspend to RAM（STR）](/pm_subsystem/suspend_and_resume.html)和Suspend to disk（STD）中的任意一种。而怎么判断系统没有事情在做呢？依赖[wakeup events framework](/pm_subsystem/wakeup_events_framework.html)。只要系统没有正在处理和新增的wakeup events，就尝试suspend，如果suspend的过程中有events产生，再resume就是了。

由于suspend/resume的操作如此频繁，解决同步问题就越发重要，这也要依赖[wakeup events framework](/pm_subsystem/wakeup_events_framework.html)及其[wakeup count](/pm_subsystem/wakeup_count.html)功能。

#### 3. 在电源管理中的位置

autosleep的实现位于kernel/power/autosleep.c中，基于wakeup count和suspend & hibernate功能，并通过PM core的main模块向用户空间提供sysfs文件（/sys/power/autosleep）

[![Autosleep architecture](/content/uploadfile/201409/0130d03a1c50db886306fc8ef117845c20140918154225.gif "Autosleep architecture")](/content/uploadfile/201409/8c2a922ba16e543e769f0607a3fc86fb20140918154224.gif)

注1：我们在“[Linux电源管理(8)\_Wakeup count功能](/pm_subsystem/wakeup_count.html)”中，讨论过wakeup count功能，本文的autosleep，就是使用wakeup count的一个实例。

#### 4. 代码分析

**4.1 /sys/power/autosleep**

/sys/power/autosleep是在kernel/power/main.c中实现的，如下：

```
   1: #ifdef CONFIG_PM_AUTOSLEEP
```

```
   2: static ssize_t autosleep_show(struct kobject *kobj,
```

```
   3:                               struct kobj_attribute *attr,
```

```
   4:                               char *buf)
```

```
   5: {
```

```
   6:         suspend_state_t state = pm_autosleep_state();
```

```
   7:  
```

```
   8:         if (state == PM_SUSPEND_ON)
```

```
   9:                 return sprintf(buf, "off\n");
```

```
  10:  
```

```
  11: #ifdef CONFIG_SUSPEND
```

```
  12:         if (state < PM_SUSPEND_MAX)
```

```
  13:                 return sprintf(buf, "%s\n", valid_state(state) ?
```

```
  14:                                                 pm_states[state] : "error");
```

```
  15: #endif
```

```
  16: #ifdef CONFIG_HIBERNATION
```

```
  17:         return sprintf(buf, "disk\n");
```

```
  18: #else
```

```
  19:         return sprintf(buf, "error");
```

```
  20: #endif
```

```
  21: }
```

```
  22:  
```

```
  23: static ssize_t autosleep_store(struct kobject *kobj,
```

```
  24:                                struct kobj_attribute *attr,
```

```
  25:                                const char *buf, size_t n)
```

```
  26: {
```

```
  27:         suspend_state_t state = decode_state(buf, n);
```

```
  28:         int error;
```

```
  29:  
```

```
  30:         if (state == PM_SUSPEND_ON
```

```
  31:             && strcmp(buf, "off") && strcmp(buf, "off\n"))
```

```
  32:                 return -EINVAL;
```

```
  33:  
```

```
  34:         error = pm_autosleep_set_state(state);
```

```
  35:         return error ? error : n;
```

```
  36: }
```

```
  37:  
```

```
  38: power_attr(autosleep);
```

```
  39: #endif /* CONFIG_PM_AUTOSLEEP */
```

> a）autosleep不是一个必须的功能，可以通过CONFIG\_PM\_AUTOSLEEP打开或关闭该功能。
>
> b）autosleep文件和state文件类似：
>
> 读取，返回“freeze”，“standby”，“mem”，“disk”， “off”，“error”等6个字符串中的一个，表示当前autosleep的状态，分别是auto freeze、auto standby、auto STR、auto STD、autosleep功能关闭和当前系统不支持该autosleep的错误指示；
>
> 写入freeze”，“standby”，“mem”，“disk”， “off”等5个字符串中的一个，代表将autosleep切换到指定状态。
>
> c）autosleep的读取，由pm\_autosleep\_state实现；autosleep的写入，由pm\_autosleep\_set\_state实现。这两个接口为autosleep模块提供的核心接口，位于kernel/power/autosleep.c中。

**4.2 pm\_autosleep\_init**

开始之前，先介绍一下autosleep的初始化函数，该函数在kernel PM初始化时（.\kernel\power\main.c:pm\_init）被调用，负责初始化autosleep所需的2个全局参数：

1）一个名称为“autosleep”的wakeup source（autosleep\_ws），在autosleep执行关键操作时，阻止系统休眠（我们可以从中理解wakeup source的应用场景和使用方法）。

2）一个名称为“autosleep”的有序workqueue，用于触发实际的休眠动作（休眠应由经常或者线程触发）。这里我们要提出2个问题：什么是有序workqueue？为什么要使用有序workqueue？后面分析代码时会有答案。

如下：

```
   1: int __init pm_autosleep_init(void)
```

```
   2: {
```

```
   3:         autosleep_ws = wakeup_source_register("autosleep");
```

```
   4:         if (!autosleep_ws)
```

```
   5:                 return -ENOMEM;
```

```
   6:  
```

```
   7:         autosleep_wq = alloc_ordered_workqueue("autosleep", 0);
```

```
   8:         if (autosleep_wq)
```

```
   9:                 return 0;
```

```
  10:  
```

```
  11:         wakeup_source_unregister(autosleep_ws);
```

```
  12:         return -ENOMEM;
```

```
  13: }
```

**4.3 pm\_autosleep\_set\_state**

pm\_autosleep\_set\_state负责设置autosleep的状态，autosleep状态和“[Linux电源管理(5)\_Hibernate和Sleep功能介绍](/pm_subsystem/std_str_func.html)”所描述的电源管理状态一致，共有freeze、standby、STR、STD和off五种（具体依赖于系统实际支持的电源管理状态）。具体如下：

```
   1: int pm_autosleep_set_state(suspend_state_t state)
```

```
   2: {
```

```
   3:  
```

```
   4: #ifndef CONFIG_HIBERNATION
```

```
   5:         if (state >= PM_SUSPEND_MAX)
```

```
   6:                 return -EINVAL;
```

```
   7: #endif
```

```
   8:  
```

```
   9:         __pm_stay_awake(autosleep_ws);
```

```
  10:  
```

```
  11:         mutex_lock(&autosleep_lock);
```

```
  12:  
```

```
  13:         autosleep_state = state;
```

```
  14:  
```

```
  15:         __pm_relax(autosleep_ws);
```

```
  16:  
```

```
  17:         if (state > PM_SUSPEND_ON) {
```

```
  18:                 pm_wakep_autosleep_enabled(true);
```

```
  19:                 queue_up_suspend_work();
```

```
  20:         } else {
```

```
  21:                 pm_wakep_autosleep_enabled(false);
```

```
  22:         }
```

```
  23:  
```

```
  24:         mutex_unlock(&autosleep_lock);
```

```
  25:         return 0;
```

```
  26: }
```

> a）判断state是否合法。
>
> b）调用[\_\_pm\_stay\_awake](/pm_subsystem/wakeup_events_framework.html)，确保系统不会休眠。
>
> c）将state保存在一个全局变量中（autosleep\_state）。
>
> d）调用[\_\_pm\_relax](/pm_subsystem/wakeup_events_framework.html)，允许系统休眠。
>
> e）根据state的状态off还是其它，调用[wakeup events framework](/pm_subsystem/wakeup_events_framework.html)提供的接口pm\_wakep\_autosleep\_enabled，使能或者禁止autosleep功能。
>
> f）如果是使能状态，调用内部接口queue\_up\_suspend\_work，将suspend work挂到autosleep workqueue中。
>
> 注2：由这里的实例可以看出，此时wakeup source不再是wakeup events的载体，而更像一个lock（呵呵，Android wakelocks的影子）。
>
> 注3：
>   
> 该接口并没有对autosleep state的当前值做判断，也就意味着用户程序可以不停的调用该接口，设置autosleep state，如写“mem”，写“freeze”，写“disk”等等。那么suspend work将会多次queue到wrokqueue上。
>   
> 而在多核CPU上，普通的workqueue是可以在多个CPU上并行执行多个work的。这恰恰是autosleep所不能接受的，因此autosleep workqueue就必须是orderd workqueue。所谓ordered workqueue，就是统一时刻最多执行一个work的worqueue（具体可参考include\linux\workqueue.h中的注释）。
>   
> 那我们再问，为什么不判断一下状态内？首先，orderd workqueue可以节省资源。其次，这样已经够了，何必多费心思呢？简洁就是美。

pm\_wakep\_autosleep\_enabled主要用于更新wakeup source中和autosleep有关的信息，代码和执行逻辑如下：

```
   1: #ifdef CONFIG_PM_AUTOSLEEP
```

```
   2: /**
```

```
   3:  * pm_wakep_autosleep_enabled - Modify autosleep_enabled for all wakeup sources.
```

```
   4:  * @enabled: Whether to set or to clear the autosleep_enabled flags.
```

```
   5:  */
```

```
   6: void pm_wakep_autosleep_enabled(bool set)
```

```
   7: {
```

```
   8:         struct wakeup_source *ws;
```

```
   9:         ktime_t now = ktime_get();
```

```
  10:  
```

```
  11:         rcu_read_lock();
```

```
  12:         list_for_each_entry_rcu(ws, &wakeup_sources, entry) {
```

```
  13:                 spin_lock_irq(&ws->lock);
```

```
  14:                 if (ws->autosleep_enabled != set) {
```

```
  15:                         ws->autosleep_enabled = set;
```

```
  16:                         if (ws->active) {
```

```
  17:                                 if (set)
```

```
  18:                                         ws->start_prevent_time = now;
```

```
  19:                                 else
```

```
  20:                                         update_prevent_sleep_time(ws, now);
```

```
  21:                         }
```

```
  22:                 }
```

```
  23:                 spin_unlock_irq(&ws->lock);
```

```
  24:         }
```

```
  25:         rcu_read_unlock();
```

```
  26: }
```

```
  27: #endif /* CONFIG_PM_AUTOSLEEP */
```

> a）更新系统所有wakeup souce的autosleep\_enabled标志（太浪费了！！）。
>
> b）如果wakeup source处于active状态（意味着它会阻止autosleep），且当前autosleep为enable，将start\_prevent\_time设置为当前实现（开始阻止）。
>
> c）如果wakeup source处于active状态，且autosleep为disable（说明这个wakeup source一直坚持到autosleep被禁止），调用update\_prevent\_sleep\_time接口，更新wakeup source的prevent\_sleep\_time。

queue\_up\_suspend\_work比较简单，就是把suspend\_work挂到workqueue，等待被执行。而suspend\_work的处理函数为try\_to\_suspend，如下：

```
   1: static DECLARE_WORK(suspend_work, try_to_suspend);
```

```
   2:  
```

```
   3: void queue_up_suspend_work(void)
```

```
   4: {
```

```
   5:         if (autosleep_state > PM_SUSPEND_ON)
```

```
   6:                 queue_work(autosleep_wq, &suspend_work);
```

```
   7: }
```

**4.4 try\_to\_suspend**

try\_to\_suspend是suspend的实际触发者，代码如下：

```
   1: static void try_to_suspend(struct work_struct *work)
```

```
   2: {
```

```
   3:         unsigned int initial_count, final_count;
```

```
   4:  
```

```
   5:         if (!pm_get_wakeup_count(&initial_count, true))
```

```
   6:                 goto out;
```

```
   7:  
```

```
   8:         mutex_lock(&autosleep_lock);
```

```
   9:  
```

```
  10:         if (!pm_save_wakeup_count(initial_count) ||
```

```
  11:                 system_state != SYSTEM_RUNNING) {
```

```
  12:                 mutex_unlock(&autosleep_lock);
```

```
  13:                 goto out;
```

```
  14:         }
```

```
  15:  
```

```
  16:         if (autosleep_state == PM_SUSPEND_ON) {
```

```
  17:                 mutex_unlock(&autosleep_lock);
```

```
  18:                 return;
```

```
  19:         }
```

```
  20:         if (autosleep_state >= PM_SUSPEND_MAX)
```

```
  21:                 hibernate();
```

```
  22:         else
```

```
  23:                 pm_suspend(autosleep_state);
```

```
  24:  
```

```
  25:         mutex_unlock(&autosleep_lock);
```

```
  26:  
```

```
  27:         if (!pm_get_wakeup_count(&final_count, false))
```

```
  28:                 goto out;
```

```
  29:  
```

```
  30:         /*
```

```
  31:          * If the wakeup occured for an unknown reason, wait to prevent the
```

```
  32:          * system from trying to suspend and waking up in a tight loop.
```

```
  33:          */
```

```
  34:         if (final_count == initial_count)
```

```
  35:                 schedule_timeout_uninterruptible(HZ / 2);
```

```
  36:  
```

```
  37:  out:
```

```
  38:         queue_up_suspend_work();
```

```
  39: }
```

> 该接口是wakeup count的一个例子，根据我们在“[Linux电源管理(8)\_Wakeup count功能](/pm_subsystem/wakeup_count.html)”的分析，就是read wakeup count，write wakeup count，suspend，具体为：
>
> a）调用pm\_get\_wakeup\_count（block为true），获取wakeup count，保存在initial\_count中。如果有wakeup events正在处理，阻塞等待。
>
> b）将读取的count，写入。如果成功，且当前系统状态为running，根据autosleep状态，调用hibernate或者pm\_suspend，suspend系统。
>
> d）如果写count失败，说明读写的过程有events产生，退出，进行下一次尝试。
>
> e）如果suspend的过程中，或者是suspend之后，产生了events，醒来，再读一次wakeup count（此时不再阻塞），保存在final\_count中。
>
> f）如果final\_count和initial\_count相同，发生怪事了，没有产生events，竟然醒了。可能有异常，不能再立即启动autosleep（恐怕陷入sleep->wakeup->sleep->wakeup的快速loop中），等待0.5s，再尝试autosleep。

**4.5 pm\_autosleep\_state**

该接口比较简单，获取autosleep\_state的值返回即可。

*原创文章，转发请注明出处。蜗窝科技，[www.wowotech.net](/pm_subsystem/autosleep.html)。*
