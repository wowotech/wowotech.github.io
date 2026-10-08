---
title: "Linux PM domain framework(1)_概述和使用流程"
date: 2014-11-13T22:09:12+08:00
url: "/pm_subsystem/pm_domain_overview.html"
gid: "107"
emlog_type: "blog"
summary: "\r\n\t在复杂的片上系统（SOC）中，设计者一般会将系统的供电分为多个独立的block，这称作电源域（Power Domain），这样做有很多好处，例如：\r\n\r\n\r\n\t1）将不同功能模块的供电分开，减小相互之间的干扰（如模拟和数字分开）。\r\n\r\n\r\n\t2）不同功能所需的电压大小不同：小电压能量损耗低，但对信号质量的要求较高；大电压能量损耗高，对信号质量的要求较低。因此可以根据实际情况，使用不同的电压"
author: "wowo"
category: "电源管理子系统"
category_alias: "pm_subsystem"
tags: ["Linux", "PM", "电源管理", "framework", "domain"]
views: 36313
comment_count: 32
aliases:
  - "/pm_subsystem/107.html"
  - "/107.html"
---

#### 1. 前言

在复杂的片上系统（SOC）中，设计者一般会将系统的供电分为多个独立的block，这称作电源域（Power Domain），这样做有很多好处，例如：

1）将不同功能模块的供电分开，减小相互之间的干扰（如模拟和数字分开）。

2）不同功能所需的电压大小不同：小电压能量损耗低，但对信号质量的要求较高；大电压能量损耗高，对信号质量的要求较低。因此可以根据实际情况，使用不同的电压供电，例如CPU core只需1.2v左右即可，而大部分的I/O则需要3.3v左右。

3）系统运行的大部分时间，并不需要所有模块都处于power on状态，因此可以通过关闭不工作模块的供电，将它们的耗电降为最低。

4）等等

虽然电源域的好处多多，却不是越多越好，因为划分电源域是需要成本的（需要在PMU中使用模拟电路完成，包括金钱成本和空间成本）。因此，大多数系统会根据功能，设置有限的几个电源域，例如：CPU core（1、2、3…）；GPU；NAND；DDR；USB；Display；Codec；等等。

这种设计引出一个问题：存在多个模块共用一个电源域的情况。因而要求在对模块power on/off的时候，考虑power共用的情况：只要一个模块工作，就要power on；直到所有模块停止工作，才能power off。

Kernel的PM domain framework（位于drivers/base/power/domain.c中），提供了管理和使用系统power domain的统一方法，在解决上面提到的问题的同时，结合kernel的[suspend](/pm_subsystem/suspend_and_resume.html)、[runtime pm](/pm_subsystem/rpm_overview.html)、[clock framework](/pm_subsystem/clk_overview.html)等机制，以非常巧妙、灵活的方式，管理系统供电，以达到高效、节能的目的。

同样，作为一个framework，我们可以从三个角度分析：使用者（consumer）的角度；提供者（provider）的角度；内部实现。具体如下。

注：本文的linux kernel版本为[3.18-rc4](https://www.kernel.org/pub/linux/kernel/v3.x/testing/linux-3.18-rc4.tar.xz)。一般情况下，对于那些相对稳定的framework，蜗蜗不会说明文章所使用的kernel版本，但本文是个例外，因为PM domain很多方便、易用的patch，只能在最新版本（当前为3.18-rc4）kernel上才能看到。

#### 2. 怎么使用（从consumer的角度看）

借助device tree，pm domain的使用很简单（非常类似clock的使用，详见“[clock framework的分析文章](/tag/clock)”），步骤如下：

1）检查pm domain provider提供的DTS的node名（下面的红色字体）：

> powergate: power-domain@e012e000 {
>
> compatible = "xxx,xxx-pm-domains";
>
> reg = <0 0xe012e000 0 0x1000>;
>
> #power-domain-cells = <1>;
>
> };

各个字段和clock framework类似，也可参考“Documentation/devicetree/bindings/power/power\_domain.txt”，这里不再详细描述。

2）大部分情况下，power-domain-cells为1，因此需要得到所需使用的power domain的编号（可能会在include/dt-bindings/\*中定义），如POWER\_DOMAIN\_USB。

3）在模块自己的DTS中，添加对power domian的引用描述，如下面红色字体：

> power-domain-example@e028e000 {
>
> compatible = "xxx,xxx-dummy";
>
> reg = <0 0xe0280000 0 0x1000>;
>
> power-domains = <&powergate POWER\_DOMAIN\_USB>;
>
> };

其中：“power-domains”为pm domain framework的关键字，由framework core负责解析（由名称可知，可以指定多个power domain）；“&powergate”为provider提供的DTS node名；“POWER\_DOMAIN\_USB”具体的domain标识，也是由provider提供。

4）借助[runtime pm](/pm_subsystem/rpm_overview.html)，在需要使用模块时，增加引用计数（可调用pm\_runtime\_get），不需要使用时，减少引用计数（可调用pm\_runtime\_put）。剩下的事情，就交给PM core了。

注2：PM core会在设备的引用计数为0时，自动调用PM domain的接口，尝试power off设备。同理，会在引用计数从0到1时，尝试power on设备。整个过程不需要设备的driver关心任何细节。同时，runtime pm也会处理idle、suspend、resume等相关的电源状态切换，如果driver只想使用PM domain功能，可以在probe中get一次，在remove中put一次，其效果和常规的power on/power off类似。

#### 3. 怎么编写PM domain驱动（从provider的角度看）

从接口层面看，编写PM domain driver相当简单，只需要三个步骤：

1）将所有的domain，以struct generic\_pm\_domain（PM domain framework提供的）形式抽象出来，并填充数据结构中需要由provider提供的内容。

2）调用pm\_genpd\_init，初始化struct generic\_pm\_domain变量中其余的内容。

3）调用\_\_of\_genpd\_add\_provider接口，将所有的domain（由struct generic\_pm\_domain变量抽象）添加到kernel中，同时提供一个根据DTS node获得对应的domain指针的回调函数（类似clock framework）。

很显然，这三个步骤对我们编写pm domain driver没有任何帮助，因为其复杂度都被掩盖在struct generic\_pm\_domain结构体中了。让我们分析完内部逻辑后，再回来。

#### 4. 基本流程分析

##### 4.1 一些数据结构

1）我们先回到“[Linux设备模型(5)\_device和device driver](/device_model/device_and_driver.html)”中，那篇文章我们留下了很多“未解之谜”，其中之一就是pm\_domain指针，如下：

```
   1:  
```

```
   2: struct device {
```

```
   3:     ...
```

```
   4:     struct dev_pm_domain    *pm_domain;
```

```
   5:     ...
```

```
   6: };
```

> struct dev\_pm\_domain结构很简单，只有一个struct dev\_pm\_ops类型的变量，该结构在“[Linux电源管理(4)\_Power Management Interface](/pm_subsystem/pm_interface.html)”中已有详细描述，是设备电源管理相关的操作函数集，包括idle、suspend/resume、runtime pm等有关的回调函数。
>
> 那这个结构和PM domain有什么关系呢？不着急，先看看struct generic\_pm\_domain结构。

2）struct generic\_pm\_domain

struct generic\_pm\_domain结构用于抽象PM domain，在include/linux/pm\_domain.h中定义，如下：

```
   1: /* include/linux/pm_domain.h */
```

```
   2: struct generic_pm_domain {
```

```
   3:         struct dev_pm_domain domain;    /* PM domain operations */
```

```
   4:         struct list_head gpd_list_node; /* Node in the global PM domains list */
```

```
   5:         struct list_head master_links;  /* Links with PM domain as a master */
```

```
   6:         struct list_head slave_links;   /* Links with PM domain as a slave */
```

```
   7:         struct list_head dev_list;      /* List of devices */
```

```
   8:         struct mutex lock;
```

```
   9:         struct dev_power_governor *gov;
```

```
  10:         struct work_struct power_off_work;
```

```
  11:         const char *name;
```

```
  12:         unsigned int in_progress;       /* Number of devices being suspended now */
```

```
  13:         atomic_t sd_count;      /* Number of subdomains with power "on" */
```

```
  14:         enum gpd_status status; /* Current state of the domain */
```

```
  15:         wait_queue_head_t status_wait_queue;
```

```
  16:         struct task_struct *poweroff_task;      /* Powering off task */
```

```
  17:         unsigned int resume_count;      /* Number of devices being resumed */
```

```
  18:         unsigned int device_count;      /* Number of devices */
```

```
  19:         unsigned int suspended_count;   /* System suspend device counter */
```

```
  20:         unsigned int prepared_count;    /* Suspend counter of prepared devices */
```

```
  21:         bool suspend_power_off; /* Power status before system suspend */
```

```
  22:         int (*power_off)(struct generic_pm_domain *domain);
```

```
  23:         s64 power_off_latency_ns;
```

```
  24:         int (*power_on)(struct generic_pm_domain *domain);
```

```
  25:         s64 power_on_latency_ns;
```

```
  26:         struct gpd_dev_ops dev_ops;
```

```
  27:         s64 max_off_time_ns;    /* Maximum allowed "suspended" time. */
```

```
  28:         bool max_off_time_changed;
```

```
  29:         bool cached_power_down_ok;
```

```
  30:         struct gpd_cpuidle_data *cpuidle_data;
```

```
  31:         void (*attach_dev)(struct device *dev);
```

```
  32:         void (*detach_dev)(struct device *dev);
```

```
  33: };
```

> 这个结构很复杂，包括很多参数，不过：对consumer来说，不需要关心该结构；对provider而言，只需要关心有限的参数；大部分参数，framework内部使用。
>
> 对provider来说，需要为每个power domain定义一个struct generic\_pm\_domain变量，并至少提供如下字段：
>
> name，该power domain的名称；
>
> power\_off/power\_on，该power domain的on/off接口；
>
> 其它的字段，这里做一个大概的介绍（后续代码逻辑分析时会更为细致的说明）：
>
> domain，struct dev\_pm\_domain类型的变量，再回忆一下struct device中的pm\_domain指针，这二者一定有些关系，后面再详细描述；
>
> gpd\_list\_node，用于将该domain添加到一个全局的domain链表（gpd\_list）中；
>
> master\_links/slave\_links，power domain可以有从属关系，例如一个power domain，通过一些器件，分出另外几个power domain，那么这个domain称作master domain，分出来的domain称作slave domain（也成subdomain）。这两个list用于组成master link和slave link，后面再详细描述；
>
> dev\_list，该domain下所有device的列表；
>
> gov，struct dev\_power\_governor指针，后面再解释；
>
> power\_off\_work，用于执行power off的wrok queue；
>
> in\_progress，该domain下正在suspend的device个数；
>
> sd\_count，记录处于power on状态的subdomain的个数；
>
> status/status\_wait\_queue，power domain的状态，以及用于等待状态切换的wait queue；
>
> power\_off\_task，
>
> resume\_count/device\_count/suspended\_count/prepared\_count，
>
> suspend\_power\_off，一个struct task\_struct指针，记录正在执行power off操作的任务；
>
> power\_on\_latency\_ns/power\_off\_latency\_ns，执行power on和power off操作时需要等待的时间，一般由provider提供；
>
> dev\_ops，struct gpd\_dev\_ops类型的变量，提供一些回调函数，后面再详细解释；
>
> max\_off\_time\_ns/max\_off\_timer\_changed，和PM domain governor有关的变量，后面再详细解释；
>
> cached\_power\_down\_ok，同上；
>
> cpuidle\_data，可以把cpuidle和PM domain连接起来，这个指针用于保存CPU idle相关的数据；
>
> attach\_dev/detach\_dev，当device和pm domain关联/去关联时，调用这两个回调函数。如果provider需要做一些处理，可以提供。

我相信读者一定被这个数据结构搞晕了，不要着急，太复杂的话，我们先放一下，去看一些简单的。下面一节我们先从整体流程上，看一下power domain framework怎么工作的（最简单的case），然后再回到这些细节上。

##### 4.2 PM domain的工作流程

结合第二章、第三章的说明，PM domain的工作流程包括：

1）Provider在DTS中定义power domain有关的device tree node，并在provider的初始化接口（可以是一个platform driver的probe，也可以是其它形式）中，定义、初始化并注册所有的power domain。

2）PM domain的初始化和注册

provider需要为每个domain定义一个struct generic\_pm\_domain变量，并初始化必要的字段和回调函数，然后调用pm\_genpd\_init接口，初始化其余的字段，如下：

```
   1: /**
```

```
   2:  * pm_genpd_init - Initialize a generic I/O PM domain object.
```

```
   3:  * @genpd: PM domain object to initialize.
```

```
   4:  * @gov: PM domain governor to associate with the domain (may be NULL).
```

```
   5:  * @is_off: Initial value of the domain's power_is_off field.
```

```
   6:  */
```

```
   7: void pm_genpd_init(struct generic_pm_domain *genpd,
```

```
   8:            struct dev_power_governor *gov, bool is_off)
```

```
   9: {
```

```
  10:     if (IS_ERR_OR_NULL(genpd))
```

```
  11:         return;
```

```
  12:  
```

```
  13:     INIT_LIST_HEAD(&genpd->master_links);
```

```
  14:     INIT_LIST_HEAD(&genpd->slave_links);
```

```
  15:     INIT_LIST_HEAD(&genpd->dev_list);
```

```
  16:     mutex_init(&genpd->lock);
```

```
  17:     genpd->gov = gov;
```

```
  18:     INIT_WORK(&genpd->power_off_work, genpd_power_off_work_fn);
```

```
  19:     genpd->in_progress = 0;
```

```
  20:     atomic_set(&genpd->sd_count, 0);
```

```
  21:     genpd->status = is_off ? GPD_STATE_POWER_OFF : GPD_STATE_ACTIVE;
```

```
  22:     init_waitqueue_head(&genpd->status_wait_queue);
```

```
  23:     genpd->poweroff_task = NULL;
```

```
  24:     genpd->resume_count = 0;
```

```
  25:     genpd->device_count = 0;
```

```
  26:     genpd->max_off_time_ns = -1;
```

```
  27:     genpd->max_off_time_changed = true;
```

```
  28:     genpd->domain.ops.runtime_suspend = pm_genpd_runtime_suspend;
```

```
  29:     genpd->domain.ops.runtime_resume = pm_genpd_runtime_resume;
```

```
  30:     genpd->domain.ops.prepare = pm_genpd_prepare;
```

```
  31:     genpd->domain.ops.suspend = pm_genpd_suspend;
```

```
  32:     genpd->domain.ops.suspend_late = pm_genpd_suspend_late;
```

```
  33:     genpd->domain.ops.suspend_noirq = pm_genpd_suspend_noirq;
```

```
  34:     genpd->domain.ops.resume_noirq = pm_genpd_resume_noirq;
```

```
  35:     genpd->domain.ops.resume_early = pm_genpd_resume_early;
```

```
  36:     genpd->domain.ops.resume = pm_genpd_resume;
```

```
  37:     genpd->domain.ops.freeze = pm_genpd_freeze;
```

```
  38:     genpd->domain.ops.freeze_late = pm_genpd_freeze_late;
```

```
  39:     genpd->domain.ops.freeze_noirq = pm_genpd_freeze_noirq;
```

```
  40:     genpd->domain.ops.thaw_noirq = pm_genpd_thaw_noirq;
```

```
  41:     genpd->domain.ops.thaw_early = pm_genpd_thaw_early;
```

```
  42:     genpd->domain.ops.thaw = pm_genpd_thaw;
```

```
  43:     genpd->domain.ops.poweroff = pm_genpd_suspend;
```

```
  44:     genpd->domain.ops.poweroff_late = pm_genpd_suspend_late;
```

```
  45:     genpd->domain.ops.poweroff_noirq = pm_genpd_suspend_noirq;
```

```
  46:     genpd->domain.ops.restore_noirq = pm_genpd_restore_noirq;
```

```
  47:     genpd->domain.ops.restore_early = pm_genpd_resume_early;
```

```
  48:     genpd->domain.ops.restore = pm_genpd_resume;
```

```
  49:     genpd->domain.ops.complete = pm_genpd_complete;
```

```
  50:     genpd->dev_ops.save_state = pm_genpd_default_save_state;
```

```
  51:     genpd->dev_ops.restore_state = pm_genpd_default_restore_state;
```

```
  52:     mutex_lock(&gpd_list_lock);
```

```
  53:     list_add(&genpd->gpd_list_node, &gpd_list);
```

```
  54:     mutex_unlock(&gpd_list_lock);
```

```
  55: }
```

> 该接口可接受三个参数：genpd为需要初始化的power domain指针；gov为governor，可以留空，我们先不考虑它；is\_off，指明该power domain在注册时的状态，是on还是off，以便framework正确设置该domain的status字段。
>
> 它的逻辑比较简单，值得注意的是genpd->domain.ops中各个回调函数的初始化，这些以”pm\_genqd\_”为前缀的函数，都是pm domain framework提供的帮助函数，用于power domain级别的电源管理，包括power on/off、suspend/resume、runtime pm等。
>
> 回忆一下“[Linux电源管理(4)\_Power Management Interface](/pm_subsystem/pm_interface.html)”中有关struct dev\_pm\_ops的描述，bus\_type、device\_driver、class、device\_type、device等结构，都可以包括dev pm ops，而PM core进行相关的电源状态切换时，只会调用其中的一个。选择哪个，是有优先顺序的，其中优先级最高的，就是device结构中pm\_domain指针的。
>
> 那么，我们再思考一下，device中可是一个指针哦，具体的变量哪来的？你一定猜到了，来自struct generic\_pm\_domain变量，就是这个函数初始化的内容。后面再详细介绍。

3）完成所有domain的初始化后，调用\_\_of\_genpd\_add\_provider接口，将它们添加到kernel中。从该接口的命名上，我们可以猜到，它和DTS有关（of是Open Firmware的缩写），定义如下：

```
   1: /**
```

```
   2:  * __of_genpd_add_provider() - Register a PM domain provider for a node
```

```
   3:  * @np: Device node pointer associated with the PM domain provider.
```

```
   4:  * @xlate: Callback for decoding PM domain from phandle arguments.
```

```
   5:  * @data: Context pointer for @xlate callback.
```

```
   6:  */
```

```
   7: int __of_genpd_add_provider(struct device_node *np, genpd_xlate_t xlate,
```

```
   8:                         void *data)
```

```
   9: {
```

```
  10:         struct of_genpd_provider *cp;
```

```
  11:  
```

```
  12:         cp = kzalloc(sizeof(*cp), GFP_KERNEL);
```

```
  13:         if (!cp)
```

```
  14:                 return -ENOMEM;
```

```
  15:  
```

```
  16:         cp->node = of_node_get(np);
```

```
  17:         cp->data = data;
```

```
  18:         cp->xlate = xlate;
```

```
  19:  
```

```
  20:         mutex_lock(&of_genpd_mutex);
```

```
  21:         list_add(&cp->link, &of_genpd_providers);
```

```
  22:         mutex_unlock(&of_genpd_mutex);
```

```
  23:         pr_debug("Added domain provider from %s\n", np->full_name);
```

```
  24:  
```

```
  25:         return 0;
```

```
  26: }
```

也许您会奇怪，该接口的三个参数没有一个和struct generic\_pm\_domain所代表的power domain有关啊！不着急，我们慢慢分析。

> 参数1，np，是一个device node指针，哪来的？想一下第2章pm domain provider提供的DTS，就是它生成的指针；
>
> 参数2，xlate，一个用于解析power domain的回调函数，定义如下：
>
> typedef struct generic\_pm\_domain \*(\*genpd\_xlate\_t)(struct of\_phandle\_args \*args, void \*data);
>
> 该回调函数的第二个参数，就是\_\_of\_genpd\_add\_provider接口的参数3。它会返回一个power domain指针；
>
> 参数3，data，一个包含了所有power domain信息的指针，具体的形式，由provider自行定义，反正最终会传给同样由provider提供的回调函数中，provider根据实际情况，获得对应的power domain指针，并返回给调用者。

注3：这是device tree的惯用伎俩，consumer在DTS中对所使用的资源（这里为power domain，如power-domains = <&powergate POWER\_DOMAIN\_USB>;）的声明，最终会由对应的framework（这里为pm domain framework）解析，并调用provider提供的回调函数，最终返回给consumer该资源的句柄（这里为一个struct generic\_pm\_domain指针）。所有的framework都是这样做的，包括前面所讲的clock framework，这里的pm domain framework，等等。具体的解析过程，后面会详细描述。

4）pm domain framework对consumer DTS中的power domain的解析

先把第2章的例子搬过来：

> power-domain-example@e028e000 {
>
> …
>
> power-domains = <&powergate POWER\_DOMAIN\_USB>;
>
> };

怎么解析呢？让我们从设备模型的platform\_drv\_probe接口开始。

由[Linux设备模型相关的文章](/sort/device_model)可知，platform设备的枚举从platform\_drv\_probe开始。而所有在DTS中描述的设备，最终会生成一个platform设备，这个设备的driver的执行，也会从platform\_drv\_probe开始，该接口进而会调用platform driver的probe。如下：

```
   1: static int platform_drv_probe(struct device *_dev)
```

```
   2: {
```

```
   3:         struct platform_driver *drv = to_platform_driver(_dev->driver);
```

```
   4:         struct platform_device *dev = to_platform_device(_dev);
```

```
   5:         int ret;
```

```
   6:  
```

```
   7:         ret = of_clk_set_defaults(_dev->of_node, false);
```

```
   8:         if (ret < 0)
```

```
   9:                 return ret;
```

```
  10:  
```

```
  11:         ret = dev_pm_domain_attach(_dev, true);
```

```
  12:         if (ret != -EPROBE_DEFER) {
```

```
  13:                 ret = drv->probe(dev);
```

```
  14:                 if (ret)
```

```
  15:                         dev_pm_domain_detach(_dev, true);
```

```
  16:         }
```

```
  17:  
```

```
  18:         if (drv->prevent_deferred_probe && ret == -EPROBE_DEFER) {
```

```
  19:                 dev_warn(_dev, "probe deferral not supported\n");
```

```
  20:                 ret = -ENXIO;
```

```
  21:         }
```

```
  22:  
```

```
  23:         return ret;
```

```
  24: }
```

在执行driver的probe之前，会先调用dev\_pm\_domain\_attach接口，将该设备attach到指定的power domain上（如果有的话）。该接口位于drivers/base/power/common.c中，实现如下：

```
   1: int dev_pm_domain_attach(struct device *dev, bool power_on)
```

```
   2: {
```

```
   3:         int ret;
```

```
   4:  
```

```
   5:         ret = acpi_dev_pm_attach(dev, power_on);
```

```
   6:         if (ret)
```

```
   7:                 ret = genpd_dev_pm_attach(dev);
```

```
   8:  
```

```
   9:         return ret;
```

```
  10: }
```

```
  11: EXPORT_SYMBOL_GPL(dev_pm_domain_attach);
```

先不考虑ACPI设备，会直接调用genpd\_dev\_pm\_attach接口（呵呵，回到pm domain framework了），该接口位于drivers/base/power/domain.c，如下：

```
   1: /**
```

```
   2:  * genpd_dev_pm_attach - Attach a device to its PM domain using DT.
```

```
   3:  * @dev: Device to attach.
```

```
   4:  *
```

```
   5:  * Parse device's OF node to find a PM domain specifier. If such is found,
```

```
   6:  * attaches the device to retrieved pm_domain ops.
```

```
   7:  *
```

```
   8:  * Both generic and legacy Samsung-specific DT bindings are supported to keep
```

```
   9:  * backwards compatibility with existing DTBs.
```

```
  10:  *
```

```
  11:  * Returns 0 on successfully attached PM domain or negative error code.
```

```
  12:  */
```

```
  13: int genpd_dev_pm_attach(struct device *dev)
```

```
  14: {
```

```
  15:     struct of_phandle_args pd_args;
```

```
  16:     struct generic_pm_domain *pd;
```

```
  17:     int ret;
```

```
  18:  
```

```
  19:     if (!dev->of_node)
```

```
  20:         return -ENODEV;
```

```
  21:  
```

```
  22:     if (dev->pm_domain)
```

```
  23:         return -EEXIST;
```

```
  24:  
```

```
  25:     ret = of_parse_phandle_with_args(dev->of_node, "power-domains",
```

```
  26:                     "#power-domain-cells", 0, &pd_args);
```

```
  27:     if (ret < 0) {
```

```
  28:         if (ret != -ENOENT)
```

```
  29:             return ret;
```

```
  30:  
```

```
  31:         /*
```

```
  32:          * Try legacy Samsung-specific bindings
```

```
  33:          * (for backwards compatibility of DT ABI)
```

```
  34:          */
```

```
  35:         pd_args.args_count = 0;
```

```
  36:         pd_args.np = of_parse_phandle(dev->of_node,
```

```
  37:                         "samsung,power-domain", 0);
```

```
  38:         if (!pd_args.np)
```

```
  39:             return -ENOENT;
```

```
  40:     }
```

```
  41:  
```

```
  42:     pd = of_genpd_get_from_provider(&pd_args);
```

```
  43:     if (IS_ERR(pd)) {
```

```
  44:         dev_dbg(dev, "%s() failed to find PM domain: %ld\n",
```

```
  45:             __func__, PTR_ERR(pd));
```

```
  46:         of_node_put(dev->of_node);
```

```
  47:         return PTR_ERR(pd);
```

```
  48:     }
```

```
  49:  
```

```
  50:     dev_dbg(dev, "adding to PM domain %s\n", pd->name);
```

```
  51:  
```

```
  52:     while (1) {
```

```
  53:         ret = pm_genpd_add_device(pd, dev);
```

```
  54:         if (ret != -EAGAIN)
```

```
  55:             break;
```

```
  56:         cond_resched();
```

```
  57:     }
```

```
  58:  
```

```
  59:     if (ret < 0) {
```

```
  60:         dev_err(dev, "failed to add to PM domain %s: %d",
```

```
  61:             pd->name, ret);
```

```
  62:         of_node_put(dev->of_node);
```

```
  63:         return ret;
```

```
  64:     }
```

```
  65:  
```

```
  66:     dev->pm_domain->detach = genpd_dev_pm_detach;
```

```
  67:  
```

```
  68:     return 0;
```

```
  69: }
```

```
  70: EXPORT_SYMBOL_GPL(genpd_dev_pm_attach);
```

还蛮复杂，我们先不管细节，看一个大概的过程：

> a）of\_parse\_phandle\_with\_args负责从device\_node指针中，解析指定名称的字段，其中”power-domains”是consumer DTS中的关键字，最终会解出一个struct of\_phandle\_args类型的变量（回忆一下上面的genpd\_xlate\_t函数指针，第一个参数就是该类型指针）。
>
> b）解析完成后，调用of\_genpd\_get\_from\_provider接口，获取power domain指针。
>
> c）最后调用pm\_genpd\_add\_device接口，将该设备添加到该power domain相应的链表中。

of\_genpd\_get\_from\_provider负责最终的domain解析，实现如下：

```
   1: static struct generic_pm_domain *of_genpd_get_from_provider(
```

```
   2:                                         struct of_phandle_args *genpdspec)
```

```
   3: {
```

```
   4:         struct generic_pm_domain *genpd = ERR_PTR(-ENOENT);
```

```
   5:         struct of_genpd_provider *provider;
```

```
   6:  
```

```
   7:         mutex_lock(&of_genpd_mutex);
```

```
   8:  
```

```
   9:         /* Check if we have such a provider in our array */
```

```
  10:         list_for_each_entry(provider, &of_genpd_providers, link) {
```

```
  11:                 if (provider->node == genpdspec->np)
```

```
  12:                         genpd = provider->xlate(genpdspec, provider->data);
```

```
  13:                 if (!IS_ERR(genpd))
```

```
  14:                         break;
```

```
  15:         }
```

```
  16:  
```

```
  17:         mutex_unlock(&of_genpd_mutex);
```

```
  18:  
```

```
  19:         return genpd;
```

```
  20: }
```

找到一个provider，以data指针为参数，调用xlate回调，剩下的事情，就交给provider自己了。

5）power domain的使用

device获得自己的power domain后，可以利用pm\_runtime\_get\_xxx/pm\_runtime\_put\_xxx接口，增加或减少引用计数，runtime pm core会在合适的时机，调用pm domain提供的power on/off提供的接口，power on或者power off设备。

当然，如果不想使用runtime pm接口，pm domain也提供了其它直接调用的形式，不过不建议使用。

具体的on/off流程，会在下一篇文章继续分析，本文就先到这里了。

*原创文章，转发请注明出处。蜗窝科技*，[www.wowotech.net](/pm_subsystem/pm_domain_overview.html)。
