---
title: "Linux电源管理(14)_从设备驱动的角度看电源管理"
date: 2015-03-02T22:53:52+08:00
url: "/pm_subsystem/device_driver_pm.html"
gid: "149"
emlog_type: "blog"
summary: "\r\n\t相信工作稍微久一点的linux驱动工程师都深有体会：\r\n\r\n\r\n\t在旧时光里，实现某一个设备的电源管理功能，是非常简单的一件事情。大多数设备都被抽象为platform设备，driver只需要提供suspend/resume/shutdown等回调函数，并注册到kernel即可。kernel会在系统电源状态切换的过程中，调用driver提供的回调函数，切换设备的电源状态。\r\n\r\n\r\n\t但是在新"
author: "wowo"
category: "电源管理子系统"
category_alias: "pm_subsystem"
tags: ["Device", "driver", "PM"]
views: 34580
comment_count: 20
aliases:
  - "/pm_subsystem/149.html"
  - "/149.html"
---

#### 1. 前言

相信工作稍微久一点的linux驱动工程师都深有体会：

在旧时光里，实现某一个设备的电源管理功能，是非常简单的一件事情。大多数设备都被抽象为platform设备，driver只需要提供suspend/resume/shutdown等回调函数，并注册到kernel即可。kernel会在系统电源状态切换的过程中，调用driver提供的回调函数，切换设备的电源状态。

但是在新时代中，设备电源管理有关的操作，被统一封装在struct dev\_pm\_ops结构中了。该结构包含20多个回调函数，再加上复杂的电源管理机制（常规的suspend/resume、runtime PM等等），使设备驱动的电源管理工作不再那么单纯，工程师（如蜗蜗自己）的思路也不再特别清晰。

因此本文希望能以单一设备的电源管理为出发点，结合kernel的电源管理机制，介绍怎样在设备驱动中添加电源管理功能，并分析设备电源状态切换和系统电源状态切换的关系。

另外，我们在[电源管理系列文章](/sort/pm_subsystem)中，介绍了很多的电源管理机制，如generic PM、wakeup event framework、wakelock、autosleep、runtime PM、PM domain、等等，本文也算是对它们的梳理和总结。

#### 2. 功能描述

设备的电源状态切换，和系统电源状态切换基本保持一致（runtime PM除外），切换的场景如下：

1）系统reboot的过程，包括halt、power off、restart等（可参考“[Linux电源管理(3)\_Generic PM之Reboot过程](/pm_subsystem/reboot.html)”），要求设备进入shutdown状态，以避免意外产生。

2）系统suspend/resume的过程（可参考“[Linux电源管理(6)\_Generic PM之Suspend功能](/pm_subsystem/suspend_and_resume.html)”），要求设备也同步suspend/resume。

3）系统hibernate及恢复的过程，要求设备在suspend/resume的基础上，增加poweroff的动作。

4）runtime PM过程（可参考“[Linux电源管理(11)\_Runtime PM之功能描述](/pm_subsystem/rpm_overview.html)”），要求设备在引用计数为0时suspend甚至power off，并在引用计数大于0时power on以及resume。

旧有的电源管理框架中，通过bus、class、device\_driver等结构体中的shutdown、suspend、resume三个回调函数，就可以实现上面处runtime PM之外的所有功能。但是在新框架中，特别是引入struct dev\_pm\_ops结构之后，其中的suspend/resume就不再推荐使用了。

不过，对有些设备来说，例如platform device，如果电源管理需求不是很复杂，driver工程师仍然可以使用旧的方法实现，kernel会自动帮忙转换为新的方式。但是，如果有更多需求，就不得不面对struct dev\_pm\_ops了。下面将会详细说明。

#### 3. 数据结构回顾

正式开始之前，我们先回顾一下设备电源管理有关的数据结构。它们大多都在之前的文章中介绍过了，本文放在一起，权当一个总结。

**3.1 .shutdown回调函数以及使用方法**

由于reboot过程是相对独立和稳定的，且该过程依赖于设备的.shutdown回调函数，这里把它独立出来，单独描述，后面就不再涉及了。

.shutdown回调函数存在于两个数据结构中：struct device\_driver和struct bus\_type，在系统reboot的过程中被调用，负责关闭设备。设备驱动可以根据需要，实现其中的一个。我们以一个普通的platform设备为例，介绍这个过程。

1）定义一个platform\_driver，并实现其.shutdown回调，然后调用platform\_driver\_register将它注册到kernel中

```
   1: static void foo_shutdown(struct platform_device *pdev)
```

```
   2: {
```

```
   3:         ...
```

```
   4: } 
```

```
   5: static platform_driver foo_pdrv = 
```

```
   6: {
```

```
   7:         .shutdown = foo_shutdown,
```

```
   8:         ...
```

```
   9: };
```

2）platform\_driver\_register时，会把struct device\_driver变量的shutdown函数，替换为platform设备特有的shutdown函数（platform\_drv\_shutdown），并调用driver\_register将device\_driver注册到kernel

```
   1: int __platform_driver_register(struct platform_driver *drv,
```

```
   2:                                 struct module *owner)
```

```
   3: {
```

```
   4:         …
```

```
   5:  
```

```
   6:         if (drv->shutdown)
```

```
   7:                 drv->driver.shutdown = platform_drv_shutdown; 
```

```
   8:  
```

```
   9:         return driver_register(&drv->driver);
```

```
  10: }
```

3）系统reboot的过程中，会调用每个设备的shutdown函数。对这里的foo\_pdrv而言，会先调用platform\_drv\_shutdown，它继续调用foo\_shutdown。

**3.2 legacy的不再使用的.suspend/.resume**

旧的suspend/resume操作，主要依赖struct device\_driver、struct class、struct bus\_type等结构中的suspend和resume回调函数，其使用方式和上面的.shutdown几乎完全一样。以platform设备为例，只需多定义两个函数即可，如下：

```
   1: static int foo_suspend(struct platform_device *pdev, pm_message_t state)
```

```
   2: {
```

```
   3:         ...
```

```
   4: }
```

```
   5:  
```

```
   6: static int foo_resume(struct platform_device *pdev)
```

```
   7: {
```

```
   8:         ...
```

```
   9: }
```

```
  10:  
```

```
  11: static void foo_shutdown(struct platform_device *pdev)
```

```
  12: {
```

```
  13:         ...
```

```
  14: }
```

```
  15:  
```

```
  16: static platform_driver foo_pdrv = {
```

```
  17:         .suspend = foo_suspend,
```

```
  18:         .resume = foo_resume,
```

```
  19:         .shutdown = foo_shutdown,
```

```
  20:         ...
```

```
  21: };
```

> 在较新的kernel中，已经不再建议使用这些回调函数了，但对platform设备来说，如果场景比较简单，可以照旧使用上面的实现方法，platform.c会自动帮忙转换为`struct dev_pm_ops回调，具体请参考后面描述。`

**3.3 `struct dev_pm_ops`结构**

struct dev\_pm\_ops是设备电源管理的核心数据结构，用于封装和设备电源管理有关的所有操作`。`

```
   1: struct dev_pm_ops {
```

```
   2:         int (*prepare)(struct device *dev);
```

```
   3:         void (*complete)(struct device *dev);
```

```
   4:         int (*suspend)(struct device *dev);
```

```
   5:         int (*resume)(struct device *dev);
```

```
   6:         int (*freeze)(struct device *dev);
```

```
   7:         int (*thaw)(struct device *dev);
```

```
   8:         int (*poweroff)(struct device *dev);
```

```
   9:         int (*restore)(struct device *dev);
```

```
  10:         int (*suspend_late)(struct device *dev);
```

```
  11:         int (*resume_early)(struct device *dev);
```

```
  12:         int (*freeze_late)(struct device *dev);
```

```
  13:         int (*thaw_early)(struct device *dev);
```

```
  14:         int (*poweroff_late)(struct device *dev);
```

```
  15:         int (*restore_early)(struct device *dev);
```

```
  16:         int (*suspend_noirq)(struct device *dev);
```

```
  17:         int (*resume_noirq)(struct device *dev);
```

```
  18:         int (*freeze_noirq)(struct device *dev);
```

```
  19:         int (*thaw_noirq)(struct device *dev);
```

```
  20:         int (*poweroff_noirq)(struct device *dev);
```

```
  21:         int (*restore_noirq)(struct device *dev);
```

```
  22:         int (*runtime_suspend)(struct device *dev);
```

```
  23:         int (*runtime_resume)(struct device *dev);
```

```
  24:         int (*runtime_idle)(struct device *dev);
```

```
  25: };
```

> 该结构基本上是个大杀器了，该有的东西都有，主要分为几类：
>
> 传统suspend的常规路径，prepare/complete、suspend/resume、freeze/thaw、poweroff、restore；
>
> 传统suspend的特殊路径，early/late、noirq；
>
> runtime PM，suspend/resume/idle。

各类driver需要做的事情很单纯，实现这些回调函数，并保存在合适的位置，我们接着往下看。

**3.4 struct dev\_pm\_ops的位置**

```
   1: struct device {
```

```
   2:         ...
```

```
   3:         struct dev_pm_domain    *pm_domain;
```

```
   4:         const struct device_type *type;
```

```
   5:         struct class            *class;
```

```
   6:         struct bus_type *bus;
```

```
   7:         struct device_driver *driver; 
```

```
   8:         ...
```

```
   9: };
```

```
  10:  
```

```
  11:  
```

```
  12:  
```

```
  13: struct dev_pm_domain {
```

```
  14:         struct dev_pm_ops       ops; 
```

```
  15:         ...
```

```
  16: };
```

```
  17:  
```

```
  18: struct device_type {
```

```
  19:         ...
```

```
  20:         const struct dev_pm_ops *pm;
```

```
  21: };
```

```
  22:  
```

```
  23: struct class {
```

```
  24:         ...
```

```
  25:         const struct dev_pm_ops *pm;
```

```
  26:         ...
```

```
  27: };
```

```
  28:  
```

```
  29: struct bus_type {
```

```
  30:         ...
```

```
  31:         const struct dev_pm_ops *pm;
```

```
  32:         ...
```

```
  33: };
```

```
  34:  
```

```
  35: struct device_driver {
```

```
  36:         ...
```

```
  37:         const struct dev_pm_ops *pm;
```

```
  38:         ...
```

```
  39: };
```

> 可谓是狡兔多窟，struct dev\_pm\_ops存在于`struct device、``struct device_type、``struct class、``struct bus_type、``struct device_driver`等所有和设备模型有关的实体中`。`
>
> 由之前的文章可知，kernel在电源管理的过程中，会按照如下优先级调用dev\_pm\_ops中的回调函数，以命令设备实现相应的状态切换`：`
>
> `dev->pm_domain->ops、dev->type->pm、dev->class->pm、dev->bus->pm、dev->driver->pm。`
>
> 因此，设备driver需要做的事情也很单纯，实现这些回调函数，并保存在合适的位置。但这么多位置，到底怎么实现呢？我们接着分析。

#### 4. `struct dev_pm_ops`的实现

由之前的描述可知，系统在电源状态切换时，会按照一定的优先顺序，调用设备的pm ops。所谓的优先顺序，是指：只要存在优先级高的ops（如dev->pm\_domain->ops），则调用该ops，否则继续查找下一个优先级。因此，设备驱动可以根据该设备的实际情况，在指定层次上，实现dev pm ops，以达到电源管理的目的。

dev pm ops可以存在于pm domain、device type、class、bus、device driver任何一个地方，本章以pm domain、bus和device driver三个典型场景为例，介绍设备电源管理的实现思路。

注1：为了方便，我会以`struct dev_pm_ops`中的.suspend函数为例，其它类似。

**4.1 pm domain**

当一个设备属于某个pm domain时（具体可参考“[Linux PM domain framework(1)\_概述和使用流程](/pm_subsystem/pm_domain_overview.html)”），系统suspend的过程中，会直接调用pm\_domain->ops.suspend。而由pm\_genpd\_init可知，pm\_domain->ops.suspend由pm\_genpd\_suspend实现：

> genpd->domain.ops.suspend = pm\_genpd\_suspend;

该接口的实现为：

```
   1: static int pm_genpd_suspend(struct device *dev)
```

```
   2: {
```

```
   3:         struct generic_pm_domain *genpd;
```

```
   4:  
```

```
   5:         dev_dbg(dev, "%s()\n", __func__);
```

```
   6:  
```

```
   7:         genpd = dev_to_genpd(dev);
```

```
   8:         if (IS_ERR(genpd))
```

```
   9:                 return -EINVAL;
```

```
  10:  
```

```
  11:         return genpd->suspend_power_off ? 0 : pm_generic_suspend(dev);
```

```
  12: }
```

> 最终会调用pm\_generic\_suspend，由“[Linux电源管理(4)\_Power Management Interface](/pm_subsystem/pm_interface.html)”的描述可知，该接口最终会调用该设备驱动的suspend接口（如果有的话），即：dev->driver->pm->suspend。

看来是空欢喜一场，本以为pm domain帮忙做了，设备驱动就可以偷一点懒，谁知道绕来绕去，又把球踢给了设备驱动！让我们思考一下其中的原因：

1）suspend时，设备的动作到底是什么，只有设备驱动最清楚，所以，把事情交给driver做，是合理的。

2）那么，为什么要经过pm domain这一层呢？直接调用driver的suspend不就可以了吗？因为需要在suspend前，由pm domain做一些处理，例如判断该设备是否已经掉电（如果掉电了，就不能再suspend了，否则可能有非预期的结果），等等。

**4.2 dev->bus->pm**

来看另一个例子，如果该设备所在的bus提供了dev\_pm\_ops呢？开始之前，我们再强调一下这个事实：suspend时，设备的动作到底是什么，只有设备驱动最清楚，所以，把事情交给driver做，是合理的。所以相信大家猜到了，就算bus有suspend回调，最终还是要绕到设备驱动的suspend接口上。

我们以platform bus为例，原因是这个bus很简单，而且我们平时需要面对的大多数设备都是platform设备。

在drivers/base/platform.c中，platform bus是这样定义的：

```
   1: struct bus_type platform_bus_type = {
```

```
   2:         .name           = "platform",
```

```
   3:         .dev_groups     = platform_dev_groups,
```

```
   4:         .match          = platform_match,
```

```
   5:         .uevent         = platform_uevent,
```

```
   6:         .pm             = &platform_dev_pm_ops,
```

```
   7: };
```

接着看一下platform\_dev\_pm\_ops：

```
   1: static const struct dev_pm_ops platform_dev_pm_ops = {
```

```
   2:         .runtime_suspend = pm_generic_runtime_suspend,
```

```
   3:         .runtime_resume = pm_generic_runtime_resume,
```

```
   4:         USE_PLATFORM_PM_SLEEP_OPS
```

```
   5: };
```

> 哦，有runtime PM相关的两个回调，有一个宏定义：USE\_PLATFORM\_PM\_SLEEP\_OPS，该宏定义指定了dev\_pm\_ops的suspend回调为platform\_pm\_suspend（其它的类似）。该接口的实现如下：

```
   1: int platform_pm_suspend(struct device *dev)
```

```
   2: {
```

```
   3:         struct device_driver *drv = dev->driver;
```

```
   4:         int ret = 0;
```

```
   5:  
```

```
   6:         if (!drv)
```

```
   7:                 return 0;
```

```
   8:  
```

```
   9:         if (drv->pm) {
```

```
  10:                 if (drv->pm->suspend)
```

```
  11:                         ret = drv->pm->suspend(dev);
```

```
  12:         } else {
```

```
  13:                 ret = platform_legacy_suspend(dev, PMSG_SUSPEND);
```

```
  14:         }
```

```
  15:  
```

```
  16:         return ret;
```

```
  17: }
```

> 原来如此，如果该设备的驱动提供了dev\_pm\_ops指针，调用相应的suspend接口。否则，调用legacy的接口（即pdrv->suspend）。再对比3.1，3.2小节的描述，是不是豁然开朗了？
>
> 另外，由于platform bus是一个虚拟的bus，不需要其它的动作。对于一些物理bus，可以在bus的suspend接口中，实现bus有关的suspend操作。这就是设备模型的魅力所在。

**4.3 dev->driver->pm**

无论怎样，如果一个设备需要在suspend时有一些动作，就一定要在设备驱动中实现suspend，那样怎么实现呢？定义一个struct dev\_pm\_ops变量，并实现设备所需的回调函数，在driver注册之前，保存在driver->pm指针中即可。

那有什么变化？大多数的设备是platform设备，我们也可以用旧的方式（3.1，3.2小节），实现platform driver的suspend/resume。但是，在新时代，不建议这样做了，注意platform\_legacy\_suspend中的legacy字样哦，遗产、遗留下来的，只是为了兼容。如果我们新写driver，就用新的方式好了。

#### 5. 设备电源状态的切换过程

本来还想梳理一下系统电源切换的过程中，driver是怎么处理的。但经过上面的分析，传统的suspend/resume已经很明确了，无非是按照pm\_domain—>device driver或者class—>device driver或者bus—>device driver的顺序，调用相应的回调函数。而runtime PM，还是放到runtime PM的分析文章里比较好。所以本文就结束好了。

*原创文章，转发请注明出处。蜗窝科技*，[www.wowotech.net](/pm_subsystem/device_driver_pm.html)。
