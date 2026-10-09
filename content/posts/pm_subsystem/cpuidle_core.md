---
title: "Linux cpuidle framework(2)_cpuidle core"
date: 2014-12-30T22:38:33+08:00
url: "/pm_subsystem/cpuidle_core.html"
gid: "133"
emlog_type: "blog"
summary: "cpuidle core是cpuidle framework的核心模块，负责抽象出cpuidle device、cpuidle driver和cpuidle governor三个实体，并提供如下功能（可参考“ Linux cpuidle framework(1)_概述和软件架构 ”中的软件架构）： 1）向底层的cpuidle driver模块提供cpudile device和cpuidle dri"
author: "wowo"
category: "电源管理子系统"
category_alias: "pm_subsystem"
tags: ["Linux", "framework", "core", "cpuidle"]
views: 35841
comment_count: 27
aliases:
  - "/pm_subsystem/133.html"
  - "/133.html"
---

#### 1. 前言

cpuidle core是cpuidle framework的核心模块，负责抽象出cpuidle device、cpuidle driver和cpuidle governor三个实体，并提供如下功能（可参考“[Linux cpuidle framework(1)\_概述和软件架构](/pm_subsystem/cpuidle_overview.html)”中的软件架构）：

1）向底层的cpuidle driver模块提供cpudile device和cpuidle driver的注册/注销接口。

2）向cpuidle governors提供governor的注册接口。

3）提供全局的cpuidle机制的开、关、暂停、恢复等功能。

4）向用户空间程序提供governor选择的接口。

5）向kernel sched中的cpuidle entry提供cpuidle的级别选择、进入等接口，以方便调用。

本文会以这些功能为线索，逐一展开，分析cpuidle framework的实现思路和实现原理。

#### 2.主要数据结构

cpuidle core抽象出了cpuidle device、cpuidle driver和cpuidle governor三个数据结构，cpuidle driver和cpuidle governor比较容易理解，但cpuidle device的实际意义是什么呢？我们来一一梳理一下。

##### 2.1 cpuidle\_state

蜗蜗在“[Linux cpuidle framework(1)\_概述和软件架构](/pm_subsystem/cpuidle_overview.html)”中提到过，cpuidle framework提出的主要背景是，很多复杂的CPU，有多种不同的idle级别。这些idle级别有不同的功耗和延迟，从而可以在不同的场景下使用。Linux kernel使用struct cpuidle\_state结构抽象idle级别（后面将会统称为idle state），如下：

```
   1: /* include/linux/cpuidle.h */
```

```
   2: struct cpuidle_state {
```

```
   3:         char            name[CPUIDLE_NAME_LEN];
```

```
   4:         char            desc[CPUIDLE_DESC_LEN];
```

```
   5:  
```

```
   6:         unsigned int    flags;
```

```
   7:         unsigned int    exit_latency; /* in US */
```

```
   8:         int             power_usage; /* in mW */
```

```
   9:         unsigned int    target_residency; /* in US */
```

```
  10:         bool            disabled; /* disabled on all CPUs */
```

```
  11:  
```

```
  12:         int (*enter)    (struct cpuidle_device *dev,
```

```
  13:                         struct cpuidle_driver *drv,
```

```
  14:                         int index);
```

```
  15:  
```

```
  16:         int (*enter_dead) (struct cpuidle_device *dev, int index);
```

```
  17: };
```

> name、desc，该idle state的名称和简介；
>
> exit\_latency，CPU从该idle state下返回运行状态的延迟，单位为us。它决定了CPU在idle状态和run状态之间切换的效率，如果延迟过大，将会影响系统性能；
>
> power\_usage，CPU在该idle state下的功耗，单位为mW；
>
> target\_residency，期望的停留时间，单位为us。进入和退出idle state是需要消耗额外的能量的，如果在idle状态停留的时间过短，节省的功耗少于额外的消耗，则得不偿失。governor会根据该字段，结合当前的系统情况（如可以idle多久），选择idle level；
>
> disabled，表示该idle state在所有CPU上都不可用；
>
> flags，idle state的特性标志，当前支持如下三个：
>   
>  CPUIDLE\_FLAG\_TIME\_VALID，表明CPU停留于该idle state下的时间是可测量的，具体的使用场景，会在介绍governor时详细说明；
>   
>  CPUIDLE\_FLAG\_COUPLED，表明该idle state会同时在多个CPU上起作用，软件需要特殊处理；
>   
>  CPUIDLE\_FLAG\_TIMER\_STOP，表明在该idle state下，timer会停止；
>
> enter，进入该state的回调函数；
>
> enter\_dead，CPU长时间不需要工作时（称作offline），可调用该回调函数。

总结说来，cpuidle state的功能有2：
  
一是描述该idle state的特性，主要包括exit\_latency、power\_usage、target\_residency。这些特性是governor制定idle策略的依据；
  
二是提供进入该idle state的具体方法。

##### 2.2 cpuidle\_device

现实中，并没有“cpuidle device”这样一个真实的设备，因此cpuidle device是一个虚拟设备，我们可以把它类比为“cpu idle controller”，负责实现cpuidle相关的逻辑。在多核CPU中，每个CPU core，都会对应一个cpuidle device。Linux kernel使用struct cpuidle\_device抽象cpuidle device，如下：

```
   1: struct cpuidle_device {
```

```
   2:         unsigned int            registered:1;
```

```
   3:         unsigned int            enabled:1;
```

```
   4:         unsigned int            cpu;
```

```
   5:  
```

```
   6:         int                     last_residency;
```

```
   7:         int                     state_count;
```

```
   8:         struct cpuidle_state_usage      states_usage[CPUIDLE_STATE_MAX];
```

```
   9:         struct cpuidle_state_kobj *kobjs[CPUIDLE_STATE_MAX];
```

```
  10:         struct cpuidle_driver_kobj *kobj_driver;
```

```
  11:         struct cpuidle_device_kobj *kobj_dev;
```

```
  12:         struct list_head        device_list;
```

```
  13:  
```

```
  14: #ifdef CONFIG_ARCH_NEEDS_CPU_IDLE_COUPLED
```

```
  15:         int                     safe_state_index;
```

```
  16:         cpumask_t               coupled_cpus;
```

```
  17:         struct cpuidle_coupled  *coupled;
```

```
  18: #endif
```

```
  19: };
```

> registered，表示设备是否已经注册到kernel中；
>
> enabled，表示设备是否已经使能；
>
> cpu，该cpuidle device所对应的cpu number；
>
> last\_residency，该设备上一次停留在idle状态的时间，单位为us；
>
> state\_count，该设备具备的idle state（对应struct cpuidle\_state结构）的个数；
>
> states\_usage，一个struct cpuidle\_state\_usage类型的数组，记录了该设备的每个idle state的统计信息，包括是否使能（enable）、设备进入该state的次数（usage）和设备停留在该state的总时间（time，单位为us）；
>
> kobjs、kobj\_driver、kobj\_dev，用于组织sysfs，具体可参考**TODO**；
>
> device\_list，用于将该设备添加到一个全局的链表中（cpuidle\_detected\_devices）；
>
> safe\_state\_index、coupled\_cpus、coupled，和coupled cpu idle有关，后面会单独介绍。

由上面的描述可知，cpuidle device和常见device不同，struct cpuidle\_device中保存的信息，都是运行时动态创建的信息，不需要driver提供任何额外信息。

##### 2.3 cpuidle\_driver

cpuidle core使用struct cpuidle\_driver抽象cpuidle驱动，如下：

```
   1: struct cpuidle_driver {
```

```
   2:         const char              *name;
```

```
   3:         struct module           *owner;
```

```
   4:         int                     refcnt;
```

```
   5:  
```

```
   6:         /* used by the cpuidle framework to setup the broadcast timer */
```

```
   7:         unsigned int            bctimer:1;
```

```
   8:         /* states array must be ordered in decreasing power consumption */
```

```
   9:         struct cpuidle_state    states[CPUIDLE_STATE_MAX];
```

```
  10:         int                     state_count;
```

```
  11:         int                     safe_state_index;
```

```
  12:  
```

```
  13:         /* the driver handles the cpus in cpumask */
```

```
  14:         struct cpumask          *cpumask;
```

```
  15: };
```

> bctimer，一个标志，用于指示在cpuidle driver注册和注销时，是否需要设置一个broadcast timer，有关broadcast timer后面再详细介绍；
>
> states、state\_count，该driver支持的cpuidle state及其个数。由于struct cpuidle\_device中包含了某个state在该设备上是否enable的信息，这里的state应该是所有cpuidle device所支持的state的公倍数。另外，上面的注释很明确，这些states，需要以功耗大小的降序排列；
>
> safe\_state\_index，和coupled cpu idle有关，后面会单独介绍；
>
> cpumask，一个struct cpumask结构的bit map指针，用于说明该driver支持哪些cpu core。

struct cpuidle\_driver结构比较简单，由此可知编写cpuidle driver的主要工作量，是定义所支持的cpuidle state，以及state的enter接口。

##### 2.4 cpuidle\_governor

cpuidle core使用struct cpuidle\_governor结构抽象cpuidle governor，如下：

```
   1: struct cpuidle_governor {
```

```
   2:         char                    name[CPUIDLE_NAME_LEN];
```

```
   3:         struct list_head        governor_list;
```

```
   4:         unsigned int            rating;
```

```
   5:  
```

```
   6:         int  (*enable)          (struct cpuidle_driver *drv,
```

```
   7:                                         struct cpuidle_device *dev);
```

```
   8:         void (*disable)         (struct cpuidle_driver *drv,
```

```
   9:                                         struct cpuidle_device *dev);
```

```
  10:  
```

```
  11:         int  (*select)          (struct cpuidle_driver *drv,
```

```
  12:                                         struct cpuidle_device *dev);
```

```
  13:         void (*reflect)         (struct cpuidle_device *dev, int index);
```

```
  14:  
```

```
  15:         struct module           *owner;
```

```
  16: };
```

> name，该governor的名称；
>
> governor\_list，用于将该governor添加到一个全局的governors列表中（cpuidle\_governors），由此可见系统允许存在多个governor；
>
> rating，governor的级别，正常情况下，kernel会选择系统中rating值最大的governor作为当前governor（除非用于主动修改，后面会介绍）；
>
> enable/disable，governor的enable/disable回调函数，一般会在enable中进行一些初始化操作，在disable中进行反操作；
>
> select，根据当前系统的运行状况，以及各个idle state的特性，选择一个state（即决策）；
>
> reflect，通过该回调函数，可以告知governor，系统上一次所处的idle state是哪个（即系统从哪一个state回来），具体的用处，后面再分析。

#### 3. 功能说明

##### 3.1 cpuidle\_device管理

cpuidle\_device管理主要负责cpuidle device注册/注销、使能/禁止，位于drivers/cpuidle/cpuidle.c中，由下面的四个接口实现：

```
   1: extern int cpuidle_register_device(struct cpuidle_device *dev); 
```

```
   2: extern void 
```

```
   3: cpuidle_unregister_device(struct cpuidle_device *dev); 
```

```
   4: extern int 
```

```
   5: cpuidle_enable_device(struct cpuidle_device *dev); 
```

```
   6: extern void 
```

```
   7: cpuidle_disable_device(struct cpuidle_device *dev); 
```

1）cpuidle\_register\_device

该接口的内部动作如下：

> 调用\_\_cpuidle\_device\_init接口，初始化struct cpuidle\_device变量，主要是将dev->states\_usage、dev->last\_residency等状态信息清零；
>
> 调用\_\_cpuidle\_register\_device接口，将struct cpuidle\_device指针保存在一个全局的per cpu的指针中（cpuidle\_devices），同时将它添加到一个全局的列表中（cpuidle\_detected\_devices）；
>
> 调用cpuidle\_add\_sysfs接口，添加该设备有关的sysfs文件（3.6小节会详细介绍）；
>
> 调用cpuidle\_enable\_device接口，使能该该设备（由此可知，新注册的设备默认是使能的）；
>
> 调用cpuidle\_install\_idle\_handler接口，install idle handler。所谓的idle handler，其实就是一个内部的全局变量（initialized），后面讲到cpuidle的核心功能时，会再说明。

2）cpuidle\_enable\_device

我们通过cpuidle\_enable\_device接口，来理解一下何为idle device的enable？

> 调用cpuidle\_get\_cpu\_driver接口，获取该设备对应的driver，如果设备没有绑定driver，或者当前没有governor（cpuidle\_curr\_governor为NULL），则不能enable，返回错误；
>
> 依据driver提供的idle state的个数（drv->state\_count），初始化设备的state\_count变量（dev->state\_count）；
>
> 调用cpuidle\_add\_device\_sysfs接口注册cpuidle device的sysfs文件，注意和前面的cpuidle\_add\_sysfs不同，会在3.6小节一并介绍；
>
> 如果current governor提供了enable接口（cpuidle\_curr\_governor->enable），调用之；
>
> 置位设备的enabled标志（dev->enabled = 1），同时将全局变量enabled\_devices加1，cpuidle\_install\_idle\_handler/cpuidle\_uninstall\_idle\_handler就是利用该全局变量设置或者清零initialized标志的。

cpuidle\_unregister\_device和cpuidle\_disable\_device为相反动作，不再细说。

注1：有关per-CPU变量

由前面的描述可知，在多核系统中，每个CPU会对应一个cpuidle device，因此cpuidle\_register\_device每被执行一次，就会注册一个不同的设备。如果cpuidle需要将它们分别记录下来，就要借助per-CPU变量，以cpuidle\_devices指针为例，其声明和定义分别如下：

```
   1: /* include/linux/cpuidle.h */
```

```
   2: DECLARE_PER_CPU(struct cpuidle_device *, cpuidle_devices);
```

```
   3:  
```

```
   4:  
```

```
   5: /* include/linux/cpuidle.h */
```

```
   6: DEFINE_PER_CPU(struct cpuidle_device *, cpuidle_devices);
```

使用方法如下：per\_cpu(cpuidle\_devices, dev->cpu) = dev。

##### 3.2 cpuidle driver管理

cpuidle driver管理位于drivers/cpuidle/driver.c中，主要负责cpuidle driver的注册、获取等逻辑的实现。

cpuidle\_register\_driver用于注册一个cpuidle driver，它主要完成如下内容：

> 注册之前，调用者需要提供详细的states信息（drv->states\drv->state\_count）；
>
> 进行一些合法性检查，包括idle state的个数是否大于零、cpuidle功能是否使能等等；
>
> 调用\_\_cpuidle\_driver\_init初始化driver的内部数据，包括drv->refcnt、drv->cpumask、drv->bctimer等，下面会对这几个内部数据进行较为详细的说明；
>
> 调用\_\_cpuidle\_set\_driver，将该driver“注册”到系统。**何为“注册”**呢？下面会详细解释；
>
> 如果drv->bctimer为1，则调用on\_each\_cpu\_mask，在每个CPU上，执行一次cpuidle\_setup\_broadcast\_timer，设置broadcast timer；
>
> 最后，调用poll\_idle\_init，为那些具有POLL idle state的平台，注册默认的poll idle state。

1）cpuidle driver注册的意义

从本质上将，cpuidle driver是一个“driver”，它驱动的对象是cpuidle device，也即CPU。在多核系统（SMP）中，会有多个CPU，也就有多个cpuidle device。如果这些device的idle功能相同（最关键的是idle state的个数、参数相同），那么一个cpuidle driver就可以驱动这些device。否则，则需要多个driver才能驱动。

基于上面的事实，cpuidle core提供一个名称为“CONFIG\_CPU\_IDLE\_MULTIPLE\_DRIVERS”的配置项，用于设置是否需要多个cpuidle driver。

如果没有使能这个配置项，说明所有CPU的idle功能相同，一个cpuidle driver即可。此时cpuidle driver的注册，就是将driver保存在一个名称为cpuidle\_curr\_driver的全局指针中，且只能注册一次。同理，cpuidle driver的获取，就是返回这个指针的值。如下：

```
   1: static struct cpuidle_driver *cpuidle_curr_driver;
```

```
   2:  
```

```
   3: /**
```

```
   4:  * __cpuidle_get_cpu_driver - return the global cpuidle driver pointer.
```

```
   5:  * @cpu: ignored without the multiple driver support
```

```
   6:  *
```

```
   7:  * Return a pointer to a struct cpuidle_driver object or NULL if no driver was
```

```
   8:  * previously registered.
```

```
   9:  */
```

```
  10: static inline struct cpuidle_driver *__cpuidle_get_cpu_driver(int cpu)
```

```
  11: {
```

```
  12:         return cpuidle_curr_driver;
```

```
  13: }
```

```
  14:  
```

```
  15: /**
```

```
  16:  * __cpuidle_set_driver - assign the global cpuidle driver variable.
```

```
  17:  * @drv: pointer to a struct cpuidle_driver object
```

```
  18:  *
```

```
  19:  * Returns 0 on success, -EBUSY if the driver is already registered.
```

```
  20:  */
```

```
  21: static inline int __cpuidle_set_driver(struct cpuidle_driver *drv)
```

```
  22: {
```

```
  23:         if (cpuidle_curr_driver)
```

```
  24:                 return -EBUSY;
```

```
  25:  
```

```
  26:         cpuidle_curr_driver = drv;
```

```
  27:  
```

```
  28:         return 0;
```

```
  29: }
```

另外，如果使能这个配置项，说明不同CPU的idle功能不同，每个CPU都要有一个driver。此时cpuidle idle的注册，又要依赖per cpu变量，就是将当前的注册的driver，保存在对应cpu的per cpu指针中。同理，cpuidle driver的获取，就是返回per cpu指针的值。如下：

```
   1: static DEFINE_PER_CPU(struct cpuidle_driver *, cpuidle_drivers);
```

```
   2:  
```

```
   3: /**
```

```
   4:  * __cpuidle_get_cpu_driver - return the cpuidle driver tied to a CPU.
```

```
   5:  * @cpu: the CPU handled by the driver
```

```
   6:  *
```

```
   7:  * Returns a pointer to struct cpuidle_driver or NULL if no driver has been
```

```
   8:  * registered for @cpu.
```

```
   9:  */
```

```
  10: static struct cpuidle_driver *__cpuidle_get_cpu_driver(int cpu)
```

```
  11: {
```

```
  12:         return per_cpu(cpuidle_drivers, cpu);
```

```
  13: }
```

```
  14:  
```

```
  15: /**
```

```
  16:  * __cpuidle_set_driver - set per CPU driver variables for the given driver.
```

```
  17:  * @drv: a valid pointer to a struct cpuidle_driver
```

```
  18:  *
```

```
  19:  * For each CPU in the driver's cpumask, unset the registered driver per CPU
```

```
  20:  * to @drv.
```

```
  21:  *
```

```
  22:  * Returns 0 on success, -EBUSY if the CPUs have driver(s) already.
```

```
  23:  */
```

```
  24: static inline int __cpuidle_set_driver(struct cpuidle_driver *drv)
```

```
  25: {
```

```
  26:         int cpu;
```

```
  27:  
```

```
  28:         for_each_cpu(cpu, drv->cpumask) {
```

```
  29:  
```

```
  30:                 if (__cpuidle_get_cpu_driver(cpu)) {
```

```
  31:                         __cpuidle_unset_driver(drv);
```

```
  32:                         return -EBUSY;
```

```
  33:                 }
```

```
  34:  
```

```
  35:                 per_cpu(cpuidle_drivers, cpu) = drv;
```

```
  36:         }
```

```
  37:  
```

```
  38:         return 0;
```

```
  39: }
```

2）broadcast timer功能

前面2.1小节提供过cpuidle state中的“CPUIDLE\_FLAG\_TIMER\_STOP” flag。当cpuidle driver的idle state中有state设置了这个flag时，说明对应的CPU在进入idle state时，会停掉该CPU的local timer，此时Linux kernel的clock event framework（具体可参考本站“[时间子系统](/sort/timer_subsystem)”相关的文章）便不能再依赖本CPU的local timer。

针对这种情况，设计者会提供一个broadcast timer，该timer独立于所有CPU运行，并可以把tick广播到每个CPU上，因而不受idle state的影响。因此，如果cpuidle state具有STOP TIMER的特性的话，需要在driver注册时，调用clock events提供的notify接口（clockevents\_notify），告知clock events模块，打开broadcast timer。如下：

```
   1: /* cpuidle_register_driver->__cpuidle_register_driver */
```

```
   2: static int __cpuidle_register_driver(struct cpuidle_driver *drv)
```

```
   3: {
```

```
   4:         ...
```

```
   5:         __cpuidle_driver_init(drv);
```

```
   6:         ...
```

```
   7:  
```

```
   8:         if (drv->bctimer)
```

```
   9:                 on_each_cpu_mask(drv->cpumask, cpuidle_setup_broadcast_timer,
```

```
  10:                                  (void *)CLOCK_EVT_NOTIFY_BROADCAST_ON, 1);
```

```
  11:         ...
```

```
  12: }
```

```
  13:  
```

```
  14:  
```

```
  15: static void __cpuidle_driver_init(struct cpuidle_driver *drv)
```

```
  16: {
```

```
  17:         ...
```

```
  18:  
```

```
  19:         /*
```

```
  20:          * Look for the timer stop flag in the different states, so that we know
```

```
  21:          * if the broadcast timer has to be set up.  The loop is in the reverse
```

```
  22:          * order, because usually one of the deeper states have this flag set.
```

```
  23:          */
```

```
  24:         for (i = drv->state_count - 1; i >= 0 ; i--) {
```

```
  25:                 if (drv->states[i].flags & CPUIDLE_FLAG_TIMER_STOP) {
```

```
  26:                         drv->bctimer = 1;
```

```
  27:                         break;
```

```
  28:                 }
```

```
  29:         }
```

```
  30: }
```

```
  31:         
```

> \_\_cpuidle\_driver\_init接口负责检查所有的idle state，如果有state设置了CPUIDLE\_FLAG\_TIMER\_STOP flag，则置位drv->bctimer变量，表示需要开启broadcast timer；
>   
> 注2：这里有一个细节，查找idle state时，用的是倒序，结合2.3小节的描述，idle state是以功耗大小的倒序排列的，意味着功耗比较小的state，最有可能关闭timer，因而倒序可以节省查找次数（虽然不多）。这充分体现了kerne编程人员的细致程度，值得我们学习！
>
> 然后在\_\_cpuidle\_register\_driver中，根据drv->bctimer的状态，调用cpuidle\_setup\_broadcast\_timer接口，打开具体CPU上的broadcat timer。其中on\_each\_cpu\_mask可以在指定的CPU上运行函数（cpuidle\_setup\_broadcast\_timer），这里就不再详细介绍了。

有关clock event的描述，可以参考“[Linux时间子系统之（十六）：clockevent](/timer_subsystem/clock-event.html)”。

3）POLL idle state

POLL idle又称作CPU relax，是一种相对标准的idle state，在诸如64位Power PC等体系结构上，会提供这种state。如定义了CONFIG\_ARCH\_HAS\_CPU\_RELAX，cpuidle core会在注册cpuidle driver时，自动将driver的state[0]注册为POLL idle state，如下：

```
   1: static int poll_idle(struct cpuidle_device *dev,
```

```
   2:                 struct cpuidle_driver *drv, int index)
```

```
   3: {
```

```
   4:         local_irq_enable();
```

```
   5:         if (!current_set_polling_and_test()) {
```

```
   6:                 while (!need_resched())
```

```
   7:                         cpu_relax();
```

```
   8:         }
```

```
   9:         current_clr_polling();
```

```
  10:  
```

```
  11:         return index;
```

```
  12: }
```

```
  13:  
```

```
  14: static void poll_idle_init(struct cpuidle_driver *drv)
```

```
  15: {
```

```
  16:         struct cpuidle_state *state = &drv->states[0];
```

```
  17:  
```

```
  18:         snprintf(state->name, CPUIDLE_NAME_LEN, "POLL");
```

```
  19:         snprintf(state->desc, CPUIDLE_DESC_LEN, "CPUIDLE CORE POLL IDLE");
```

```
  20:         state->exit_latency = 0;
```

```
  21:         state->target_residency = 0;
```

```
  22:         state->power_usage = -1;
```

```
  23:         state->flags = CPUIDLE_FLAG_TIME_VALID;
```

```
  24:         state->enter = poll_idle;
```

```
  25:         state->disabled = false;
```

```
  26: }
```

##### 3.3 cpuidle governor管理

governor管理位于drivers/cpuidle/governor.c中，包括governor的注册、获取和切换功能，分别由下面三个接口实现：

```
   1: /**
```

```
   2:  * cpuidle_switch_governor - changes the governor
```

```
   3:  * @gov: the new target governor
```

```
   4:  *
```

```
   5:  * NOTE: "gov" can be NULL to specify disabled
```

```
   6:  * Must be called with cpuidle_lock acquired.
```

```
   7:  */
```

```
   8: int cpuidle_switch_governor(struct cpuidle_governor *gov)
```

```
   9: {
```

```
  10:         struct cpuidle_device *dev;
```

```
  11:  
```

```
  12:         if (gov == cpuidle_curr_governor)
```

```
  13:                 return 0;
```

```
  14:  
```

```
  15:         cpuidle_uninstall_idle_handler();
```

```
  16:  
```

```
  17:         if (cpuidle_curr_governor) {
```

```
  18:                 list_for_each_entry(dev, &cpuidle_detected_devices, device_list)
```

```
  19:                         cpuidle_disable_device(dev);
```

```
  20:                 module_put(cpuidle_curr_governor->owner);
```

```
  21:         }
```

```
  22:  
```

```
  23:         cpuidle_curr_governor = gov;
```

```
  24:  
```

```
  25:         if (gov) {
```

```
  26:                 if (!try_module_get(cpuidle_curr_governor->owner))
```

```
  27:                         return -EINVAL;
```

```
  28:                 list_for_each_entry(dev, &cpuidle_detected_devices, device_list)
```

```
  29:                         cpuidle_enable_device(dev);
```

```
  30:                 cpuidle_install_idle_handler();
```

```
  31:                 printk(KERN_INFO "cpuidle: using governor %s\n", gov->name);
```

```
  32:         }
```

```
  33:  
```

```
  34:         return 0;
```

```
  35: }
```

```
  36:  
```

```
  37: /**
```

```
  38:  * cpuidle_register_governor - registers a governor
```

```
  39:  * @gov: the governor
```

```
  40:  */
```

```
  41: int cpuidle_register_governor(struct cpuidle_governor *gov)
```

```
  42: {
```

```
  43:         int ret = -EEXIST;
```

```
  44:  
```

```
  45:         if (!gov || !gov->select)
```

```
  46:                 return -EINVAL;
```

```
  47:  
```

```
  48:         if (cpuidle_disabled())
```

```
  49:                 return -ENODEV;
```

```
  50:  
```

```
  51:         mutex_lock(&cpuidle_lock);
```

```
  52:         if (__cpuidle_find_governor(gov->name) == NULL) {
```

```
  53:                 ret = 0;
```

```
  54:                 list_add_tail(&gov->governor_list, &cpuidle_governors);
```

```
  55:                 if (!cpuidle_curr_governor ||
```

```
  56:                     cpuidle_curr_governor->rating < gov->rating)
```

```
  57:                         cpuidle_switch_governor(gov);
```

```
  58:         }
```

```
  59:         mutex_unlock(&cpuidle_lock);
```

```
  60:  
```

```
  61:         return ret;
```

```
  62: }
```

> cpuidle\_register\_governor接口的逻辑非常简单，将governor保存到一个全局链表（cpuidle\_governors）中，并判断新注册governor的rating是否大于当前governor（保存在cpuidle\_curr\_governor指针中），如果大于，则将新注册governor切换为当前governor；
>
> cpuidle\_switch\_governor用于切换当前的governor，需要注意的是，切换之前，要disable所有的device（cpuidle\_disable\_device），并在切换之后打开。

##### 3.4 cpuidle整体的管理功能

整体的管理功能位于drivers/cpuidle/cpuidle.c中，负责如下事项：

1）cpuidle framework的初始化，由cpuidle\_init实现

```
   1: /**
```

```
   2:  * cpuidle_init - core initializer
```

```
   3:  */
```

```
   4: static int __init cpuidle_init(void)
```

```
   5: {
```

```
   6:         int ret;
```

```
   7:  
```

```
   8:         if (cpuidle_disabled())
```

```
   9:                 return -ENODEV;
```

```
  10:  
```

```
  11:         ret = cpuidle_add_interface(cpu_subsys.dev_root);
```

```
  12:         if (ret)
```

```
  13:                 return ret;
```

```
  14:  
```

```
  15:         latency_notifier_init(&cpuidle_latency_notifier);
```

```
  16:  
```

```
  17:         return 0;
```

```
  18: }
```

```
  19: core_initcall(cpuidle_init);
```

> 主要完成：
>
> 调用cpuidle\_add\_interface接口，添加CPU global sysfs attributes；
>
> 调用latency\_notifier\_init接口，添加一个pm qos notifier，以便当系统有新的latency需求时，通知到cpuidle framework。有关PM QOS，会在另外idea文章中介绍，这里不再详细说明。

2）系统cpuidle功能的disable、pause、resume等功能，由如下接口实现（比较简单，不再详细说明）

```
   1: extern void disable_cpuidle(void); 
```

```
   2: extern void cpuidle_pause_and_lock(void); 
```

```
   3: extern void cpuidle_resume_and_unlock(void); 
```

```
   4: extern void cpuidle_pause(void); 
```

```
   5: extern void cpuidle_resume(void); 
```

3）idle state的select和enter

由下面两个接口实现：

```
   1: extern int cpuidle_select(struct cpuidle_driver *drv, struct cpuidle_device *dev); 
```

```
   2: extern int cpuidle_enter(struct cpuidle_driver *drv, struct cpuidle_device *dev, int index); 
```

> cpuidle\_select的实现非常简单，首先判断一个“use\_deepest\_state”变量，如果为1，选一个最低功耗的state即可。如果为0，调用当前governor的select函数，让governor选择。use\_deepest\_state的状态可以通过cpuidle\_use\_deepest\_state接口设置；
>
> cpuidle\_enter接口根据state index，进入指定的state，调用state的enter函数，并记录相关的统计信息即可。

4）cpuidle driver注册的简单接口

由cpuidle\_register接口实现，主要目的是在简单的平台上（所有cpuidle device的功能一样），省去cpuidle device的注册过程（由cpuidle core帮忙实现）。driver只需要定义各个idle state，并通过cpuidle\_register注册cpuidle driver即可。arm64平台就是使用这个方式。

##### 3.5 coupled idle

coupled idle功能是一个比较有意思的功能，设计者在该功能的源代码中（drivers\cpuidle\coupled.c）写了将近70行的注释，说明这个功能的缘由目的。因此在这里不能三言两语说明白，蜗蜗会单独开一篇文章，介绍该功能。

##### 3.6 sysfs

cpuidle core通过sysfs，向用户控件提供了状态统计、governor选择等信息。先看一个例子，了解一下cpuidle有关的sysfs目录结构：

> /sys/devices/system/cpu/cpuidle
>   
> |—current\_driver
>   
> |—current\_governor\_ro(or available\_governors & current\_governor)
>   
> |—cpu0
>   
> | |—cpuidle
>   
> | | |—state0
>   
> | | | |—name
>   
> | | | |—desc
>   
> | | | |—disable
>   
> | | | |—latency
>   
> | | | |—power
>   
> | | | |—time
>   
> | | | |—usage
>   
> | | |—state1
>   
> …
>   
> |—cpu1
>   
> | |—cpuidle
>   
> …

1）”/sys/devices/system/cpu/cpuidle"为cpuidle sysfs的顶级目录，由cpuidle\_init注册，我们来看一下注册过程，顺便复习一下设备模型的知识。

```
   1: static int __init cpuidle_init(void)
```

```
   2: {
```

```
   3:         ...
```

```
   4:         ret = cpuidle_add_interface(cpu_subsys.dev_root);
```

```
   5:         ...
```

```
   6: }
```

> 上面代码以“cpu\_subsys.dev\_root”为参数，调用cpuidle\_add\_interface接口，注册sysfs interface；
>
> “cpu\_subsys”在drivers/base/cpu.c中定义，实际上是一个struct bus\_type类型的变量，由cpu\_dev\_init调用subsys\_system\_register注册，结合“[Linux设备模型(6)\_Bus](/device_model/bus.html)”中有关subsystem的描述，它会创建/sys/devices/system/cpu目录；
>
> cpuidle\_add\_interface位于drivers/cpuidle/sysfs.c中，会调用sysfs\_create\_group，创建cpuidle的子目录以及default attribute，如下。

```
   1: static DEVICE_ATTR(current_driver, 0444, show_current_driver, NULL);
```

```
   2: static DEVICE_ATTR(current_governor_ro, 0444, show_current_governor, NULL);
```

```
   3:  
```

```
   4: static struct attribute *cpuidle_default_attrs[] = {
```

```
   5:         &dev_attr_current_driver.attr,
```

```
   6:         &dev_attr_current_governor_ro.attr,
```

```
   7:         NULL
```

```
   8: };
```

```
   9:  
```

```
  10: static DEVICE_ATTR(available_governors, 0444, show_available_governors, NULL);
```

```
  11: static DEVICE_ATTR(current_governor, 0644, show_current_governor,
```

```
  12:                    store_current_governor);
```

```
  13:  
```

```
  14: static struct attribute *cpuidle_switch_attrs[] = {
```

```
  15:         &dev_attr_available_governors.attr,
```

```
  16:         &dev_attr_current_driver.attr,
```

```
  17:         &dev_attr_current_governor.attr,
```

```
  18:         NULL
```

```
  19: };
```

```
  20:  
```

```
  21: int cpuidle_add_interface(struct device *dev)
```

```
  22: {
```

```
  23:         if (sysfs_switch)
```

```
  24:                 cpuidle_attr_group.attrs = cpuidle_switch_attrs;
```

```
  25:  
```

```
  26:         return sysfs_create_group(&dev->kobj, &cpuidle_attr_group);
```

```
  27: }
```

> 默认情况下，sysfs\_create\_group会使用cpuidle\_default\_attrs，该attribute只有两个文件：current\_driver和current\_governor\_ro。如果使能了sysfs\_switch（由bootloader传入），则允许通过sysfs改变当前的governor，使用cpuidle\_switch\_attrs，提供current\_driver、available\_governors和 current\_governor三个attribute文件。

2）current\_driver、current\_governor\_ro/available\_governors、current\_governor

通过current\_driver attribute文件，可以获取当前的cpuidle driver名字；

如果没有使能sysfs switch，通过current\_governor\_ro，可以获取当前的governor名字；

如果使能sysfs switch，通过available\_governors，可以获取可供使用的governors；通过current\_governor，可以读取或者设置当前的governor。

上面attribute文件的注册，已经在上面1）中说明。

3）/sys/devices/system/cpu/cpuidle/cpuX/cpuidle/stateX

这个目录下的attribute文件提供了指定cpuidle device下指定state的统计信息，包括：

> name，名称；
>
> desc，较为详细的描述；
>
> disable，cpuidle使能状态的读取和设置；
>
> latency，退出该state所需的时间，单位为us；
>
> power，该state下的功耗，单位为mW；
>
> time，停留在改状态的总时间，单位为us
>
> usage，进入该状态的次数。

这些attribute文件的注册过程，这里就不再描述，感兴趣的同学可以参考drivers/cpuidle/sysfs.c的实现。下面贴一个统计信息的实例，供大家参考：

> [xxx@cs state0]# cat name; cat desc; cat latency; cat power; cat time; cat usage
>
> POLL
>
> CPUIDLE CORE POLL IDLE
>
> 0
>
> 4294967295
>
> 6777250341
>
> 563407

*原创文章，转发请注明出处。蜗窝科技*，[www.wowotech.net](/pm_subsystem/cpuidle_core.html)。
