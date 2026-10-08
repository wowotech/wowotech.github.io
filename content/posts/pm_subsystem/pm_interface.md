---
title: "Linux电源管理(4)_Power Management Interface"
date: 2014-05-29T15:55:36+08:00
url: "/pm_subsystem/pm_interface.html"
gid: "46"
emlog_type: "blog"
summary: "\r\n\tLinux电源管理中，相当多的部分是在处理Hibernate、Suspend、Runtime PM等功能。而这些功能都基于一套相似的逻辑，即“Power \r\nmanagement \r\ninterface”。该Interface的代码实现于“include/linux/pm.h”、“drivers/base/power/main.c”等文件中。主要功能是：对下，定义Device \r\nPM相关的"
author: "wowo"
category: "电源管理子系统"
category_alias: "pm_subsystem"
tags: ["Linux", "PM", "电源管理", "dev_pm_ops", "dpm"]
views: 65977
comment_count: 19
aliases:
  - "/pm_subsystem/46.html"
  - "/46.html"
---

#### 1. 前言

Linux电源管理中，相当多的部分是在处理Hibernate、Suspend、Runtime PM等功能。而这些功能都基于一套相似的逻辑，即“Power management interface”。该Interface的代码实现于“include/linux/pm.h”、“drivers/base/power/main.c”等文件中。主要功能是：对下，定义Device PM相关的回调函数，让各个Driver实现；对上，实现统一的PM操作函数，供PM核心逻辑调用。

因此在对Hibernate、Suspend、Runtime PM等功能解析之前，有必要先熟悉一下PM Interface，这就是本文的主要目的。

#### 2. device PM callbacks

在一个系统中，数量最多的是设备，耗电最多的也是设备，因此设备的电源管理是Linux电源管理的核心内容。而设备电源管理最核心的操作就是：在合适的时机（如不再使用，如暂停使用），将设备置为合理的状态（如关闭，如睡眠）。这就是device PM callbacks的目的：定义一套统一的方式，让设备在特定的时机，步调一致的进入类似的状态（可以想象一下军训时的“一二一”口令）。

在旧版本的内核中，这些PM callbacks分布在设备模型的大型数据结构中，如struct bus\_type中的suspend、suspend\_late、resume、resume\_late，如struct device\_driver/struct class/struct device\_type中的suspend、resume。很显然这样不具备良好的封装特性，因为随着设备复杂度的增加，简单的suspend、resume已经不能满足电源管理的需求，就需要扩充PM callbacks，就会不可避免的改动这些数据结构。

于是新版本的内核，就将这些Callbacks统一封装为一个数据结构----struct dev\_pm\_ops，上层的数据结构只需要包含这个结构即可。这样如果需要增加或者修改PM callbacks，就不用改动上层结构了（这就是软件设计中抽象和封装的生动体现，像艺术一样优雅）。当然，内核为了兼容旧的设计，也保留了上述的suspend/resume类型的callbacks，只是已不建议使用，本文就不再介绍它们了。

相信每一个熟悉了旧版本内核的Linux工程师，看到struct dev\_pm\_ops时都会虎躯一震，这玩意也太复杂了吧！不信您请看：

```
   1: /* include/linux/pm.h, line 276 in linux-3.10.29 */
```

```
   2: struct dev_pm_ops {
```

```
   3:         int (*prepare)(struct device *dev);
```

```
   4:         void (*complete)(struct device *dev);
```

```
   5:         int (*suspend)(struct device *dev);
```

```
   6:         int (*resume)(struct device *dev);
```

```
   7:         int (*freeze)(struct device *dev);
```

```
   8:         int (*thaw)(struct device *dev);
```

```
   9:         int (*poweroff)(struct device *dev);
```

```
  10:         int (*restore)(struct device *dev);
```

```
  11:         int (*suspend_late)(struct device *dev);
```

```
  12:         int (*resume_early)(struct device *dev);
```

```
  13:         int (*freeze_late)(struct device *dev);
```

```
  14:         int (*thaw_early)(struct device *dev);
```

```
  15:         int (*poweroff_late)(struct device *dev);
```

```
  16:         int (*restore_early)(struct device *dev);
```

```
  17:         int (*suspend_noirq)(struct device *dev);
```

```
  18:         int (*resume_noirq)(struct device *dev);
```

```
  19:         int (*freeze_noirq)(struct device *dev);
```

```
  20:         int (*thaw_noirq)(struct device *dev);
```

```
  21:         int (*poweroff_noirq)(struct device *dev);
```

```
  22:         int (*restore_noirq)(struct device *dev);
```

```
  23:         int (*runtime_suspend)(struct device *dev);
```

```
  24:         int (*runtime_resume)(struct device *dev);
```

```
  25:         int (*runtime_idle)(struct device *dev);
```

```
  26: };
```

从Linux PM Core的角度来说，这些callbacks并不复杂，因为PM Core要做的就是在特定的电源管理阶段，调用相应的callbacks，例如在suspend/resume的过程中，PM Core会依次调用“prepare—>suspend—>suspend\_late—>suspend\_noirq-------wakeup--------->resume\_noirq—>resume\_early—>resume-->complete”。

但由于这些callbacks需要由具体的设备Driver实现，这就要求驱动工程师在设计每个Driver时，清晰的知道这些callbacks的使用场景、是否需要实现、怎么实现，这才是struct dev\_pm\_ops的复杂之处。

Linux kernel对struct dev\_pm\_ops的注释已经非常详细了，但要弄清楚每个callback的使用场景、背后的思考，并不是一件容易的事情。因此蜗蜗不准备在本文对它们进行过多的解释，而打算结合具体的电源管理行为，基于具体的场景，再进行解释。

#### 3. device PM callbacks在设备模型中的体现

我们在介绍“[Linux设备模型](/tag/%E8%AE%BE%E5%A4%87%E6%A8%A1%E5%9E%8B)”时，曾多次提及电源管理相关的内容，那时蜗蜗采取忽略的方式，暂不说明。现在是时候回过头再去看看了。

Linux设备模型中的很多数据结构，都会包含struct dev\_pm\_ops变量，具体如下：

```
   1: struct bus_type {
```

```
   2:         ...
```

```
   3:         const struct dev_pm_ops *pm;
```

```
   4:         ...
```

```
   5: };
```

```
   6:  
```

```
   7: struct device_driver {
```

```
   8:         ...
```

```
   9:         const struct dev_pm_ops *pm;
```

```
  10:         ...
```

```
  11: };
```

```
  12:  
```

```
  13: struct class {
```

```
  14:         ...
```

```
  15:         const struct dev_pm_ops *pm;
```

```
  16:         ...
```

```
  17: };
```

```
  18:  
```

```
  19: struct device_type {
```

```
  20:         ...
```

```
  21:         const struct dev_pm_ops *pm;
```

```
  22: };
```

```
  23:  
```

```
  24: struct device {
```

```
  25:         ...
```

```
  26:         struct dev_pm_info      power;
```

```
  27:         struct dev_pm_domain    *pm_domain;
```

```
  28:         ...
```

```
  29: };
```

bus\_type、device\_driver、class、device\_type等结构中的pm指针，比较容易理解，和旧的suspend/resume callbacks类似。我们重点关注一下device结构中的power和pm\_domain变量。

◆power变量

power是一个struct dev\_pm\_info类型的变量，也在“include/linux/pm.h”中定义。从蜗蜗一直工作于的Linux-2.6.23内核，到写这篇文章所用的Linux-3.10.29内核，这个数据结构可是一路发展壮大，从那时的只有4个字段，到现在有40多个字段，简直是想起来什么就放什么啊！

power变量主要保存PM相关的状态，如当前的power\_state、是否可以被唤醒、是否已经prepare完成、是否已经suspend完成等等。由于涉及的内容非常多，我们在具体使用的时候，顺便说明。

◆pm\_domain指针

在当前的内核中，struct dev\_pm\_domain结构只包含了一个struct dev\_pm\_ops ops。蜗蜗猜测这是从可扩展性方面考虑的，后续随着内核的进化，可能会在该结构中添加其他内容。

所谓的PM Domain（电源域），是针对“device”来说的。bus\_type、device\_driver、class、device\_type等结构，本质上代表的是设备驱动，电源管理的操作，由设备驱动负责，是理所应当的。但在内核中，由于各种原因，是允许没有driver的device存在的，那么怎么处理这些设备的电源管理呢？就是通过设备的电源域实现的。

#### 4. device PM callbacks的操作函数

内核在定义device PM callbacks数据结构的同时，为了方便使用该数据结构，也定义了大量的操作API，这些API分为两类。

◆通用的辅助性质的API，直接调用指定设备所绑定的driver的、pm指针的、相应的callback，如下

```
   1: extern int pm_generic_prepare(struct device *dev);
```

```
   2: extern int pm_generic_suspend_late(struct device *dev);
```

```
   3: extern int pm_generic_suspend_noirq(struct device *dev);
```

```
   4: extern int pm_generic_suspend(struct device *dev);
```

```
   5: extern int pm_generic_resume_early(struct device *dev);
```

```
   6: extern int pm_generic_resume_noirq(struct device *dev);
```

```
   7: extern int pm_generic_resume(struct device *dev); 
```

```
   8: extern int pm_generic_freeze_noirq(struct device *dev);
```

```
   9: extern int pm_generic_freeze_late(struct device *dev);
```

```
  10: extern int pm_generic_freeze(struct device *dev);
```

```
  11: extern int pm_generic_thaw_noirq(struct device *dev);
```

```
  12: extern int pm_generic_thaw_early(struct device *dev);
```

```
  13: extern int pm_generic_thaw(struct device *dev);
```

```
  14: extern int pm_generic_restore_noirq(struct device *dev);
```

```
  15: extern int pm_generic_restore_early(struct device *dev);
```

```
  16: extern int pm_generic_restore(struct device *dev);
```

```
  17: extern int pm_generic_poweroff_noirq(struct device *dev);
```

```
  18: extern int pm_generic_poweroff_late(struct device *dev);
```

```
  19: extern int pm_generic_poweroff(struct device *dev); 
```

```
  20: extern void pm_generic_complete(struct device *dev);
```

以pm\_generic\_prepare为例，就是查看dev->driver->pm->prepare接口是否存在，如果存在，直接调用并返回结果。

◆和整体电源管理行为相关的API，目的是将各个独立的电源管理行为组合起来，组成一个较为简单的功能，如下

```
   1: #ifdef CONFIG_PM_SLEEP
```

```
   2: extern void device_pm_lock(void);
```

```
   3: extern void dpm_resume_start(pm_message_t state);
```

```
   4: extern void dpm_resume_end(pm_message_t state);
```

```
   5: extern void dpm_resume(pm_message_t state);
```

```
   6: extern void dpm_complete(pm_message_t state);
```

```
   7:  
```

```
   8: extern void device_pm_unlock(void);
```

```
   9: extern int dpm_suspend_end(pm_message_t state);
```

```
  10: extern int dpm_suspend_start(pm_message_t state);
```

```
  11: extern int dpm_suspend(pm_message_t state);
```

```
  12: extern int dpm_prepare(pm_message_t state);
```

```
  13:  
```

```
  14: extern void __suspend_report_result(const char *function, void *fn, int ret);
```

```
  15:  
```

```
  16: #define suspend_report_result(fn, ret)                                  \
```

```
  17:         do {                                                            \
```

```
  18:                 __suspend_report_result(__func__, fn, ret);             \
```

```
  19:         } while (0)
```

```
  20:  
```

```
  21: extern int device_pm_wait_for_dev(struct device *sub, struct device *dev);
```

```
  22: extern void dpm_for_each_dev(void *data, void (*fn)(struct device *, void *));
```

这些API的功能和动作解析如下。

dpm\_prepare，执行所有设备的“->prepare() callback(s)”，内部动作为：

> 1）遍历dpm\_list，依次取出挂在该list中的device指针。
>   
>  【注1：设备模型在添加设备（device\_add）时，会调用device\_pm\_add接口，将该设备添加到全局链表dpm\_list中，以方便后续的遍历操作。】
>
> 2）调用内部接口device\_prepare，执行实际的prepare动作。该接口会返回执行的结果。
>
> 3）如果执行失败，打印错误信息。
>
> 4）如果执行成功，将dev->power.is\_prepared(就是上面我们提到的struct dev\_pm\_info类型的变量）设为TRUE，表示设备已经prepared了。同时，将该设备添加到dpm\_prepared\_list中（该链表保存了所有已经处于prepared状态的设备）。
>
> 内部接口device\_prepare的执行动作为：
>
> 1）根据dev->power.syscore，断该设备是否为syscore设备。如果是，则直接返回（因为syscore设备会单独处理）。
>
> 2）在prepare时期，调用pm\_runtime\_get\_noresume接口，关闭Runtime suspend功能。以避免由Runtime suspend造成的不能正常唤醒的Issue。该功能会在complete时被重新开启。
>   
>  【注2：pm\_runtime\_get\_noresume的实现很简单，就是增加该设备power变量的引用计数（dev->power.usage\_count），Runtime PM会根据该计数是否大于零，判断是否开启Runtime PM功能。】
>
> 3）调用device\_may\_wakeup接口，根据当前设备是否有wakeup source（dev->power.wakeup）以及是否允许wakeup（dev->power.can\_wakeup），判定该设备是否是一个wakeup path（记录在dev->power.wakeup\_path中）。
>   
>  【注3：设备的wake up功能，是指系统在低功耗状态下（如suspend、hibernate），某些设备具备唤醒系统的功能。这是电源管理过程的一部分。】
>
> 4）根据优先顺序，获得用于prepare的callback函数。由于设备模型有bus、driver、device等多个层级，而prepare接口可能由任意一个层级实现。这里的优先顺序是指，只要优先级高的层级注册了prepare，就会优先使用它，而不会使用优先级低的prepare。优先顺序为：dev->pm\_domain->ops、dev->type->pm、dev->class->pm、dev->bus->pm、dev->driver->pm（这个优先顺序同样适用于其它callbacks）。
>
> 5）如果得到有限的prepare函数，调用并返回结果。

dpm\_suspend，执行所有设备的“->suspend() callback(s)”，其内部动作和dpm\_prepare类似：

> 1）遍历dpm\_list，依次取出挂在该list中的device指针。
>
> 2）调用内部接口device\_suspend，执行实际的prepare动作。该接口会返回执行的结果。
>
> 3）如果suspend失败，将该设备的信息记录在一个struct suspend\_stats类型的数组中，并打印错误错误信息。
>
> 4）最后将设备从其它链表（如dpm\_prepared\_list），转移到dpm\_suspended\_list链表中。
>
> 内部接口device\_suspend的动作和device\_prepare类似，这里不再描述了。

dpm\_suspend\_start，依次执行dpm\_prepare和dpm\_suspend两个动作。

dpm\_suspend\_end，依次执行所有设备的“->suspend\_late() callback(s)”以及所有设备的“->suspend\_noirq() callback(s)”。动作和上面描述的类似，这里不再说明了。

dpm\_resume、dpm\_complete、dpm\_resume\_start、dpm\_resume\_end，是电源管理过程的唤醒动作，和dpm\_suspend\_xxx系列的接口类似。不再说明了。

*原创文章，转发请注明出处。蜗窝科技，[www.wowotech.net](/pm_subsystem/pm_interface.html)。*
