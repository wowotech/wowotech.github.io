---
title: "linux cpufreq framework(1)_概述"
date: 2015-06-13T22:20:37+08:00
url: "/pm_subsystem/cpufreq_overview.html"
gid: "194"
emlog_type: "blog"
summary: "\r\n\tlinux kernel主要通过三类机制实现SMP系统CPU core的电源管理功能：\r\n\r\n\r\n\t\r\n\t\t1）cpu hotplug。根据应用场景，enable/disable CPU core，具体可参考“Linux CPU core的电源管理(4)_cpu control”。\r\n\t\r\n\t\r\n\t\t2） cpuidle framework。在没有进程调度的时候，让CPU core进入idl"
author: "wowo"
category: "电源管理子系统"
category_alias: "pm_subsystem"
tags: ["Linux", "cpufreq", "dvfs", "hmp"]
views: 37836
comment_count: 16
aliases:
  - "/pm_subsystem/194.html"
  - "/194.html"
---

#### 1. 前言

linux kernel主要通过三类机制实现SMP系统CPU core的电源管理功能：

> 1）cpu hotplug。根据应用场景，enable/disable CPU core，具体可参考“Linux CPU core的电源管理(4)\_cpu control”。
>
> 2） cpuidle framework。在没有进程调度的时候，让CPU core进入idle状态，具体可参考“[cpuidle framework系列文章](/tag/cpuidle)”。
>
> 3） cpufreq framework。根据使用场景和系统负荷，调整CPU core的电压（voltage）和频率（frequency），具体可参考本文以及后续cpufreq相关的。

对CPU core来说，功耗和性能是一对不可调和的矛盾，通过调整CPU的电压和频率，可以在功耗和性能之间找一个平衡点。由于调整是在系统运行的过程中，因此cpufreq framework的功能也称作动态电压/频率调整（Dynamic Voltage/Frequency Scaling，DVFS）。

本文主要从功能说明和软件架构两个角度介绍cpufreq framework。

#### 2. 功能说明

cpufreq framework的核心功能，是通过调整CPU core的电压和频率，兼顾系统的性能和功耗。在不需要高性能时，降低电压和频率，以降低功耗；在需要高性能时，提高电压和频率，以提高性能。要达到此目的，有两个关键点：

> 1）如果控制CPU core的电压和频率。
>
> 2）何时改变CPU core的电压和频率。

针对这两个关键点，CPU core有两种实现。

实现1：CPU core根据自身的负荷，自动调整电压和频率，不需要OS级别的软件参与。

> 这种实现，软件复杂度非常低，通常情况下，只需要告诉CPU core电压和频率的调整范围（通过频率表示，scaling\_min\_freq和scaling\_max\_freq，也称作policy），CPU core即可自行调整。因此：
>
> 关键点1，由CPU core自行处理；
>
> 关键点2，OS需要根据大致的应用场景（例如，是高性能场景，还是低性能场景），设定一个频率范围，改变时机，由CPU core自行决定。
>
> 注1：由于软件参与度小，该实现的省电效率可能较低。

实现2：CPU core不参与任何的逻辑动作，由OS软件根据系统运行情况，调整电压和频率。

> 这种实现，几乎完全由软件掌控DVFS行为：
>
> 关键点1，基于[clock framework](/pm_subsystem/clk_overview.html)和[regulator framework](/pm_subsystem/regulator_framework_overview.html)提供的接口，控制CPU core的频率和电压；
>
> 关键点2，根据应用场景，手动（用户发起，例如省电模式）或者自动（软件自动调整，例如HMP）的调整。
>
> 注2：对关键点2来说，如果调整比较频繁，则需要CPU core在不同频率之间转换的速度足够快，后面会详细介绍。

为了实现上述功能需求，cpufreq framework抽象出cpufreq driver、cpufreq policy（策略）、cpufreq governor等多个软件实体，具体请参考下面的说明。

#### 3. 软件架构

cpufreq framework的软件架构如下面图片所示：

[![cpufreq framework](/content/uploadfile/201506/f613cfd922113b82148afb75eb6edc0f20150613141951.gif "cpufreq framework")](/content/uploadfile/201506/a4cf6b6a89f45ea76d69dcb9ea0738c720150613141951.gif) 对下，cpufreq framework基于cpu subsystem driver、OPP、clock framework、regulator framework等模块，提供对CPU core频率和电压的控制。这一部分主要由cpufreq driver实现。

对上，cpufreq framework会通过cpufreq core、cpufreq governors、cpufreq stats等模块，以sysfs的形式，向用户空间提供cpu frequency的查询、控制等接口。同时，在频率改变的时候，通过notifier通知关心的driver。

内部，cpufreq framework包括cpufreq core、cpufreq driver、cpufreq governors、cpufreq stats等模块，具体功能会在下一章详细分析。

注3：cpufreq driver中有，有一个特别的driver----arm big·little driver，用于实现ARM平台big·little的切换逻辑。虽然arm bit·little和cpufreq不是同一个概念，但它们的目的和逻辑非常类似，因此就放到这里了。后续会有专门的文章介绍该功能，因此分析cpufreq framework其它内容时，会直接把它忽略不表。

#### 4. 软件模块的功能及API描述

**4.1 cpufreq core**

cpufreq core是cpufreq framework的核心模块，和kernel其它framework类似，它主要实现三类功能：

> 对上，以sysfs的形式向用户空间提供统一的接口，以notifier的形式向其它driver提供频率变化的通知；
>
> 对下，提供CPU core频率和电压控制的驱动框架，方便底层driver的开发；同时，提供governor框架，用于实现不同的频率调整机制；
>
> 内部，封装各种逻辑，实现所需功能。这些逻辑主要围绕struct cpufreq\_driver、struct cpufreq\_policy和struct cpufreq\_governor三个数据结构进行，下面会详细分析。

1）struct cpufreq\_driver

struct cpufreq\_driver用于抽象cpufreq驱动，是平台驱动工程师关注最多的结构，其定义如下：

```
   1: /* include/linux/cpufreq.h */
```

```
   2: struct cpufreq_driver {
```

```
   3:     char            name[CPUFREQ_NAME_LEN];
```

```
   4:     u8            flags;
```

```
   5:     void            *driver_data;
```

```
   6:  
```

```
   7:     /* needed by all drivers */
```

```
   8:     int    (*init)        (struct cpufreq_policy *policy);
```

```
   9:     int    (*verify)    (struct cpufreq_policy *policy);
```

```
  10:  
```

```
  11:     /* define one out of two */
```

```
  12:     int    (*setpolicy)    (struct cpufreq_policy *policy);
```

```
  13:  
```

```
  14:     /*
```

```
  15:      * On failure, should always restore frequency to policy->restore_freq
```

```
  16:      * (i.e. old freq).
```

```
  17:      */
```

```
  18:     int    (*target)    (struct cpufreq_policy *policy,    /* Deprecated */
```

```
  19:                  unsigned int target_freq,
```

```
  20:                  unsigned int relation);
```

```
  21:     int    (*target_index)    (struct cpufreq_policy *policy,
```

```
  22:                  unsigned int index);
```

```
  23:     /*
```

```
  24:      * Only for drivers with target_index() and CPUFREQ_ASYNC_NOTIFICATION
```

```
  25:      * unset.
```

```
  26:      *
```

```
  27:      * get_intermediate should return a stable intermediate frequency
```

```
  28:      * platform wants to switch to and target_intermediate() should set CPU
```

```
  29:      * to to that frequency, before jumping to the frequency corresponding
```

```
  30:      * to 'index'. Core will take care of sending notifications and driver
```

```
  31:      * doesn't have to handle them in target_intermediate() or
```

```
  32:      * target_index().
```

```
  33:      *
```

```
  34:      * Drivers can return '0' from get_intermediate() in case they don't
```

```
  35:      * wish to switch to intermediate frequency for some target frequency.
```

```
  36:      * In that case core will directly call ->target_index().
```

```
  37:      */
```

```
  38:     unsigned int (*get_intermediate)(struct cpufreq_policy *policy,
```

```
  39:                      unsigned int index);
```

```
  40:     int    (*target_intermediate)(struct cpufreq_policy *policy,
```

```
  41:                        unsigned int index);
```

```
  42:  
```

```
  43:     /* should be defined, if possible */
```

```
  44:     unsigned int    (*get)    (unsigned int cpu);
```

```
  45:  
```

```
  46:     /* optional */
```

```
  47:     int    (*bios_limit)    (int cpu, unsigned int *limit);
```

```
  48:  
```

```
  49:     int    (*exit)        (struct cpufreq_policy *policy);
```

```
  50:     void    (*stop_cpu)    (struct cpufreq_policy *policy);
```

```
  51:     int    (*suspend)    (struct cpufreq_policy *policy);
```

```
  52:     int    (*resume)    (struct cpufreq_policy *policy);
```

```
  53:     struct freq_attr    **attr;
```

```
  54:  
```

```
  55:     /* platform specific boost support code */
```

```
  56:     bool                    boost_supported;
```

```
  57:     bool                    boost_enabled;
```

```
  58:     int     (*set_boost)    (int state);
```

```
  59: };
```

> 介绍该结构之前，我们先思考一个问题：由[设备模型](/sort/device_model)可知，driver是用来驱动设备的，那么struct cpufreq\_driver所对应的设备是什么？也许从该结构中回调函数的参数可以猜到，是struct cpufreq\_policy。但这相当难以理解，后面再分析。
>
> name，该driver的名字，需要唯一，因为cpufreq framework允许同时注册多个driver，用户可以根据实际情况选择使用哪个driver。driver的标识，就是name。
>
> flags，一些flag，具体会在后续的文章中介绍。
>
> init，driver的入口，由cpufreq core在设备枚举的时候调用，driver需要根据硬件情况，填充policy的内容。
>
> verify，验证policy中的内容是否符合硬件要求。它和init接口都是必须实现的接口。
>
> setpolicy，对于第2章所讲的“实现一”，driver需要提供这个接口，用于设置CPU core动态频率调整的范围（即policy）。
>
> target、target\_index，对于第2章所讲的“实现二”，driver需要实现这两个接口中的一个（target为旧接口，不推荐使用），用于设置CPU core为指定频率（同时修改为对应的电压）。
>
> 后面的接口都是可选的，会在后续的章节中再分析。

有关struct cpufreq\_driver的API包括：

```
   1: int cpufreq_register_driver(struct cpufreq_driver *driver_data);
```

```
   2: int cpufreq_unregister_driver(struct cpufreq_driver *driver_data);
```

```
   3:  
```

```
   4: const char *cpufreq_get_current_driver(void);
```

```
   5: void *cpufreq_get_driver_data(void);
```

> 分别为driver的注册、注销。获取当前所使用的driver名称，以及该driver的私有数据结构（driver\_data字段）。

2）struct cpufreq\_policy

struct cpufreq\_policy是比较抽象的一个数据结构（蜗蜗觉得，是cpufreq framework中最难理解的地方），我们需要借助cpufreq core中的一些实现逻辑，去分析、理解它。

前面我们提到过一个问题，cpufreq driver对应的设备是什么？kernel是这样抽象cpufreq的：

[![cpufreq model](/content/uploadfile/201506/307fbd1939ef06122b2966690621247920150613141952.gif "cpufreq model")](/content/uploadfile/201506/ba749969acb9cd50413848c30e45e14b20150613141952.gif) 抽象出一个CPU bus（对应的sysfs目录为/sys/devices/system/cpu/，具体可参考[cpu subsystem driver](/pm_subsystem/cpu_core_pm_overview.html)相关的描述），所有的CPU device都挂在这个bus上。cpufreq是CPU device的一类特定功能，被抽象为一个subsys interface（有关subsys interface的概念，请参考“[Linux设备模型(6)\_*Bus*](/device_model/bus.html)”）。

当CPU device和CPU driver匹配时，bus core会调用subsys interface的add\_dev回调函数，相当于为该特定功能添加一个“device”，进而和该特定功能的“driver”（这里为cpufreq driver）匹配，执行driver的初始化（probe，或者其它）接口。

那么该“特定功能”应该用什么样的“device”表示呢？应具体功能具体对待。kernel使用cpufreq policy（即“调频策略”）来抽象cpufreq。所谓的调频策略，即频率调整的范围，它从一定程度上，代表了cpufreq的属性。这就是struct cpufreq\_policy结构的现实意义：

```
   1: struct cpufreq_policy {
```

```
   2:     /* CPUs sharing clock, require sw coordination */
```

```
   3:     cpumask_var_t        cpus;    /* Online CPUs only */
```

```
   4:     cpumask_var_t        related_cpus; /* Online + Offline CPUs */
```

```
   5:  
```

```
   6:     unsigned int        shared_type; /* ACPI: ANY or ALL affected CPUs
```

```
   7:                         should set cpufreq */
```

```
   8:     unsigned int        cpu;    /* cpu nr of CPU managing this policy */
```

```
   9:     unsigned int        last_cpu; /* cpu nr of previous CPU that managed
```

```
  10:                        * this policy */
```

```
  11:     struct clk        *clk;
```

```
  12:     struct cpufreq_cpuinfo    cpuinfo;/* see above */
```

```
  13:  
```

```
  14:     unsigned int        min;    /* in kHz */
```

```
  15:     unsigned int        max;    /* in kHz */
```

```
  16:     unsigned int        cur;    /* in kHz, only needed if cpufreq
```

```
  17:                      * governors are used */
```

```
  18:     unsigned int        restore_freq; /* = policy->cur before transition */
```

```
  19:     unsigned int        suspend_freq; /* freq to set during suspend */
```

```
  20:  
```

```
  21:     unsigned int        policy; /* see above */
```

```
  22:     struct cpufreq_governor    *governor; /* see below */
```

```
  23:     void            *governor_data;
```

```
  24:     bool            governor_enabled; /* governor start/stop flag */
```

```
  25:  
```

```
  26:     struct work_struct    update; /* if update_policy() needs to be
```

```
  27:                      * called, but you're in IRQ context */
```

```
  28:  
```

```
  29:     struct cpufreq_real_policy    user_policy;
```

```
  30:     struct cpufreq_frequency_table    *freq_table;
```

```
  31:  
```

```
  32:     struct list_head        policy_list;
```

```
  33:     struct kobject        kobj;
```

```
  34:     struct completion    kobj_unregister;
```

```
  35:  
```

```
  36:     /*
```

```
  37:      * The rules for this semaphore:
```

```
  38:      * - Any routine that wants to read from the policy structure will
```

```
  39:      *   do a down_read on this semaphore.
```

```
  40:      * - Any routine that will write to the policy structure and/or may take away
```

```
  41:      *   the policy altogether (eg. CPU hotplug), will hold this lock in write
```

```
  42:      *   mode before doing so.
```

```
  43:      *
```

```
  44:      * Additional rules:
```

```
  45:      * - Lock should not be held across
```

```
  46:      *     __cpufreq_governor(data, CPUFREQ_GOV_POLICY_EXIT);
```

```
  47:      */
```

```
  48:     struct rw_semaphore    rwsem;
```

```
  49:  
```

```
  50:     /* Synchronization for frequency transitions */
```

```
  51:     bool            transition_ongoing; /* Tracks transition status */
```

```
  52:     spinlock_t        transition_lock;
```

```
  53:     wait_queue_head_t    transition_wait;
```

```
  54:     struct task_struct    *transition_task; /* Task which is doing the transition */
```

```
  55:  
```

```
  56:     /* For cpufreq driver's internal use */
```

```
  57:     void            *driver_data;
```

```
  58: };
```

> 该结构看着很复杂，现在只需要关心几个事情：
>
> min/max frequency，调频范围，对于可以自动调频的CPU而言，只需要这两个参数就够了。
>
> current frequency和governor，对于不能自动调频的CPU，需要governor设置具体的频率值。下面介绍一下governor。

struct cpufreq\_policy不会直接对外提供API。

3） cpufreq governors

governor的概念可参考“[Linux cpuidle framework(1)\_概述和软件架构](/pm_subsystem/cpuidle_overview.html)”中相关的描述。对于不能自动调频的CPU core，必须由软件设定具体的频率值。根据使用场景的不同，会有不同的调整方案，这是由governor模块负责的，如下：

```
   1: struct cpufreq_governor {
```

```
   2:     char    name[CPUFREQ_NAME_LEN];
```

```
   3:     int    initialized;
```

```
   4:     int    (*governor)    (struct cpufreq_policy *policy,
```

```
   5:                  unsigned int event);
```

```
   6:     ssize_t    (*show_setspeed)    (struct cpufreq_policy *policy,
```

```
   7:                      char *buf);
```

```
   8:     int    (*store_setspeed)    (struct cpufreq_policy *policy,
```

```
   9:                      unsigned int freq);
```

```
  10:     unsigned int max_transition_latency; /* HW must be able to switch to
```

```
  11:             next freq faster than this value in nano secs or we
```

```
  12:             will fallback to performance governor */
```

```
  13:     struct list_head    governor_list;
```

```
  14:     struct module        *owner;
```

```
  15: };
```

> name，该governor的名称。
>
> governor，用于governor状态切换的回调函数。
>
> show\_setspeed、store\_setspeed，用于提供sysfs “setspeed” attribute文件的回调函数。
>
> max\_transition\_latency，该governor所能容忍的最大频率切换延迟。

cpufreq governors主要向具体的governor模块提供governor的注册和注销接口，具体会在后续的文章中详细描述。

4）通过sysfs向用户空间提供的接口

请参考“linux cpufreq framework(3)\_cpufreq core”。

**4.3 cpufreq drivers**

各个driver模块会基于cpufreq core实现具体的driver，请参考“[linux cpufreq framework(2)\_cpufreq driver](/pm_subsystem/cpufreq_driver.html)”。

**4.4 cpufreq stats**

提供cpufreq有关的统计信息，请参考“[linux cpufreq framework(3)\_cpufreq core](/pm_subsystem/cpufreq_core.html)”。

#### 5. 总结

本文介绍了cpufreq framework的基本情况，后面通过以下的文章，分析其它内容：

[linux cpufreq framework(2)\_cpufreq driver](/pm_subsystem/cpufreq_driver.html)，从平台驱动工程师的角度，介绍怎么编写cpufreq驱动；

[linux cpufreq framework(3)\_cpufreq core](/pm_subsystem/cpufreq_core.html)，分析cpufreq的内部实现，并总结cpufreq提供的sysfs接口，介绍怎么通过sysfs，控制系统的调频行为；

[linux cpufreq framework(4)\_cpufreq governor](/pm_subsystem/cpufreq_governor.html)，分析cpufreq governor的实现逻辑，并介绍几种常用的governor；

[linux cpufreq framework(5)\_ARM big·little driver](/pm_subsystem/arm_big_little_driver.html)及HMP，认识ARM平台HMP功能。

*原创文章，转发请注明出处。蜗窝科技*，[www.wowotech.net](/pm_subsystem/cpufreq_overview.html)。
