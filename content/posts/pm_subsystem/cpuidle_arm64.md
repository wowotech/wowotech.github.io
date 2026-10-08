---
title: "Linux cpuidle framework(3)_ARM64 generic CPU idle driver"
date: 2015-01-06T23:13:03+08:00
url: "/pm_subsystem/cpuidle_arm64.html"
gid: "138"
emlog_type: "blog"
summary: "本文以ARM64平台下的cpuidle driver为例，说明怎样在cpuidle framework的框架下，编写cpuidle driver。另外，本文在描述cpuidle driver的同时，会涉及到CPU hotplug的概念，因此也可作为CPU hotplug的引子。"
author: "wowo"
category: "电源管理子系统"
category_alias: "pm_subsystem"
tags: ["driver", "arm64", "dts", "cpuidle"]
views: 25119
comment_count: 13
aliases:
  - "/pm_subsystem/138.html"
  - "/138.html"
---

#### 1. 前言

本文以ARM64平台下的cpuidle driver为例，说明怎样在cpuidle framework的框架下，编写cpuidle driver。另外，本文在描述cpuidle driver的同时，会涉及到CPU hotplug的概念，因此也可作为CPU hotplug的引子。

#### 2. arm64\_idle\_init

ARM64 generic CPU idle driver的代码位于“drivers/cpuidle/cpuidle-arm64.c”中，它的入口函数是arm64\_idle\_init，如下：

```
   1: static int __init arm64_idle_init(void)
```

```
   2: {
```

```
   3:         int cpu, ret;
```

```
   4:         struct cpuidle_driver *drv = &arm64_idle_driver;
```

```
   5:  
```

```
   6:         /*
```

```
   7:          * Initialize idle states data, starting at index 1.
```

```
   8:          * This driver is DT only, if no DT idle states are detected (ret == 0)
```

```
   9:          * let the driver initialization fail accordingly since there is no
```

```
  10:          * reason to initialize the idle driver if only wfi is supported.
```

```
  11:          */
```

```
  12:         ret = dt_init_idle_driver(drv, arm64_idle_state_match, 1);
```

```
  13:         if (ret <= 0) {
```

```
  14:                 if (ret)
```

```
  15:                         pr_err("failed to initialize idle states\n");
```

```
  16:                 return ret ? : -ENODEV;
```

```
  17:         }
```

```
  18:  
```

```
  19:         /*
```

```
  20:          * Call arch CPU operations in order to initialize
```

```
  21:          * idle states suspend back-end specific data
```

```
  22:          */
```

```
  23:         for_each_possible_cpu(cpu) {
```

```
  24:                 ret = cpu_init_idle(cpu);
```

```
  25:                 if (ret) {
```

```
  26:                         pr_err("CPU %d failed to init idle CPU ops\n", cpu);
```

```
  27:                         return ret;
```

```
  28:                 }
```

```
  29:         }
```

```
  30:  
```

```
  31:         ret = cpuidle_register(drv, NULL);
```

```
  32:         if (ret) {
```

```
  33:                 pr_err("failed to register cpuidle driver\n");
```

```
  34:                 return ret;
```

```
  35:         }
```

```
  36:  
```

```
  37:         return 0;
```

```
  38: }
```

```
  39: device_initcall(arm64_idle_init);
```

由该函数的执行过程，可以看出cpuidle driver的实现过程，包括：

1）静态定义一个struct cpuidle\_driver变量（这里为arm64\_idle\_driver）并填充必要的字段，如下

```
   1: static struct cpuidle_driver arm64_idle_driver = {
```

```
   2:         .name = "arm64_idle",
```

```
   3:         .owner = THIS_MODULE,
```

```
   4:         /*
```

```
   5:          * State at index 0 is standby wfi and considered standard
```

```
   6:          * on all ARM platforms. If in some platforms simple wfi
```

```
   7:          * can't be used as "state 0", DT bindings must be implemented
```

```
   8:          * to work around this issue and allow installing a special
```

```
   9:          * handler for idle state index 0.
```

```
  10:          */
```

```
  11:         .states[0] = {
```

```
  12:                 .enter                  = arm64_enter_idle_state,
```

```
  13:                 .exit_latency           = 1,
```

```
  14:                 .target_residency       = 1,
```

```
  15:                 .power_usage            = UINT_MAX,
```

```
  16:                 .flags                  = CPUIDLE_FLAG_TIME_VALID,
```

```
  17:                 .name                   = "WFI",
```

```
  18:                 .desc                   = "ARM64 WFI",
```

```
  19:         }
```

```
  20: };
```

> 该driver的名称为“arm64\_idle”，会体现在sysfs（如/sys/devices/system/cpu/cpuidle/current\_driver）中；
>
> 稍微留意一下上面的注释，所有的ARM平台，都应提供默认的WFI standby状态，作为idle state 0，如果有例外，则需要在DTS中另行处理；
>
> 对于state0，driver将其初始化为：exit latency和target residency均为1（最小值），power usage为整数中的最大值。由此可以看出，这些信息不是实际信息（因为driver不可能知道所有ARM平台的WFI相关的信息），而是相对信息，其中的含义是：所有其它的state，exit latency和target residency都会比state0大，power usage都会比state0小，够用了！多么巧妙地设计！

2）初始化其它的idle states（从state1开始），必须通过DTS操作，否则返回失败。具体可参考后续的描述。

3）对每一个cpu，调用cpu\_init\_idle接口，初始化用于支持cpuidle的、和cpu suspend有关的后端数据。后面会详细介绍。

4）调用cpuidle\_register，将cpuidle driver注册到cpuidle core中（具体可参考“[Linux cpuidle framework(2)\_cpuidle core](/pm_subsystem/cpuidle_core.html)”）。

#### 3. dt\_init\_idle\_driver

dt\_init\_idle\_driver函数用于从DTS中解析出cpuidle states的信息，并初始化arm64\_idle\_driver中的states数组。在分析这个函数之前，我们先来看一下cpuidle相关的DTS源文件是怎么写的：

注：写这篇文章所参考的kernel（[3.18-rc4](https://www.kernel.org/pub/linux/kernel/v3.x/testing/linux-3.18-rc4.tar.xz)）中，没有ARM64平台使用了cpuidle功能，因此这里给不出ARM64平台下的参考文件。好在ARM和ARM64在cpuidle dts解析上面的流程是一样的，我们可以借用ARM中的例子。

```
   1: /* arch/arm/boot/dts/vexpress-v2p-ca15_a7.dts */
```

```
   2: cpus {
```

```
   3:         #address-cells = <1>;
```

```
   4:         #size-cells = <0>;
```

```
   5:  
```

```
   6:         cpu0: cpu@0 {
```

```
   7:                 device_type = "cpu";
```

```
   8:                 compatible = "arm,cortex-a15";
```

```
   9:                 reg = <0>;
```

```
  10:                 cci-control-port = <&cci_control1>;
```

```
  11:                 cpu-idle-states = <&CLUSTER_SLEEP_BIG>;
```

```
  12:         };
```

```
  13:  
```

```
  14:         cpu1: cpu@1 {
```

```
  15:                 device_type = "cpu";
```

```
  16:                 compatible = "arm,cortex-a15";
```

```
  17:                 reg = <1>;
```

```
  18:                 cci-control-port = <&cci_control1>;
```

```
  19:                 cpu-idle-states = <&CLUSTER_SLEEP_BIG>;
```

```
  20:         };
```

```
  21:  
```

```
  22:         cpu2: cpu@2 {
```

```
  23:                 device_type = "cpu";
```

```
  24:                 compatible = "arm,cortex-a7";
```

```
  25:                 reg = <0x100>;
```

```
  26:                 cci-control-port = <&cci_control2>;
```

```
  27:                 cpu-idle-states = <&CLUSTER_SLEEP_LITTLE>;
```

```
  28:         };
```

```
  29:  
```

```
  30:         cpu3: cpu@3 {
```

```
  31:                 device_type = "cpu";
```

```
  32:                 compatible = "arm,cortex-a7";
```

```
  33:                 reg = <0x101>;
```

```
  34:                 cci-control-port = <&cci_control2>;
```

```
  35:                 cpu-idle-states = <&CLUSTER_SLEEP_LITTLE>;
```

```
  36:         };
```

```
  37:  
```

```
  38:         cpu4: cpu@4 {
```

```
  39:                 device_type = "cpu";
```

```
  40:                 compatible = "arm,cortex-a7";
```

```
  41:                 reg = <0x102>;
```

```
  42:                 cci-control-port = <&cci_control2>;
```

```
  43:                 cpu-idle-states = <&CLUSTER_SLEEP_LITTLE>;
```

```
  44:         };
```

```
  45:         idle-states {
```

```
  46:             CLUSTER_SLEEP_BIG: cluster-sleep-big {
```

```
  47:                 compatible = "arm,idle-state";
```

```
  48:                 local-timer-stop;
```

```
  49:                 entry-latency-us = <1000>;
```

```
  50:                 exit-latency-us = <700>;
```

```
  51:                 min-residency-us = <2000>;
```

```
  52:             };
```

```
  53:  
```

```
  54:             CLUSTER_SLEEP_LITTLE: cluster-sleep-little {
```

```
  55:                 compatible = "arm,idle-state";
```

```
  56:                 local-timer-stop;
```

```
  57:                 entry-latency-us = <1000>;
```

```
  58:                 exit-latency-us = <500>;
```

```
  59:                 min-residency-us = <2500>;
```

```
  60:             };
```

```
  61: };
```

> cpuidle有关的DTS信息，从属于cpus node中，先看最后面的idle-states node，它负责定义该ARM平台支持的所有的idle states，每个子node就是一个state：
>   
>  各个state定义都以“arm,idle-state”标识；
>   
>  entry-latency-us、exit-latency-us、min-residency-us分别定义了改idle state的几个重要参数，local-timer-stop对应CPUIDLE\_FLAG\_TIMER\_STOP flag（具体含义可参考“[Linux cpuidle framework(2)\_cpuidle core](/pm_subsystem/cpuidle_core.html)”中的描述）；
>   
>  这些信息会被dt\_init\_idle\_driver解析出来，并保存在arm64\_idle\_driver的state数组中。
>
> 在每个cpu的node中，通过cpu-idle-states字段，指明该CPU支持的idle states，可以有多个。

结合上面的DTS信息，dt\_init\_idle\_driver函数的执行过程如下。

```
   1: /* drivers/cpuidle/dt_idle_states.c */
```

```
   2: int dt_init_idle_driver(struct cpuidle_driver *drv,
```

```
   3:             const struct of_device_id *matches,
```

```
   4:             unsigned int start_idx)
```

```
   5: {
```

```
   6:     struct cpuidle_state *idle_state;
```

```
   7:     struct device_node *state_node, *cpu_node;
```

```
   8:     int i, err = 0;
```

```
   9:     const cpumask_t *cpumask;
```

```
  10:     unsigned int state_idx = start_idx;
```

```
  11:  
```

```
  12:     if (state_idx >= CPUIDLE_STATE_MAX)
```

```
  13:         return -EINVAL;
```

```
  14:     /*
```

```
  15:      * We get the idle states for the first logical cpu in the
```

```
  16:      * driver mask (or cpu_possible_mask if the driver cpumask is not set)
```

```
  17:      * and we check through idle_state_valid() if they are uniform
```

```
  18:      * across CPUs, otherwise we hit a firmware misconfiguration.
```

```
  19:      */
```

```
  20:     cpumask = drv->cpumask ? : cpu_possible_mask;
```

```
  21:     cpu_node = of_cpu_device_node_get(cpumask_first(cpumask));
```

```
  22:  
```

```
  23:     for (i = 0; ; i++) {
```

```
  24:         state_node = of_parse_phandle(cpu_node, "cpu-idle-states", i);
```

```
  25:         if (!state_node)
```

```
  26:             break;
```

```
  27:  
```

```
  28:         if (!idle_state_valid(state_node, i, cpumask)) {
```

```
  29:             pr_warn("%s idle state not valid, bailing out\n",
```

```
  30:                 state_node->full_name);
```

```
  31:             err = -EINVAL;
```

```
  32:             break;
```

```
  33:         }
```

```
  34:  
```

```
  35:         if (state_idx == CPUIDLE_STATE_MAX) {
```

```
  36:             pr_warn("State index reached static CPU idle driver states array size\n");
```

```
  37:             break;
```

```
  38:         }
```

```
  39:  
```

```
  40:         idle_state = &drv->states[state_idx++];
```

```
  41:         err = init_state_node(idle_state, matches, state_node);
```

```
  42:         if (err) {
```

```
  43:             pr_err("Parsing idle state node %s failed with err %d\n",
```

```
  44:                    state_node->full_name, err);
```

```
  45:             err = -EINVAL;
```

```
  46:             break;
```

```
  47:         }
```

```
  48:         of_node_put(state_node);
```

```
  49:     }
```

```
  50:  
```

```
  51:     of_node_put(state_node);
```

```
  52:     of_node_put(cpu_node);
```

```
  53:     if (err)
```

```
  54:         return err;
```

```
  55:     /*
```

```
  56:      * Update the driver state count only if some valid DT idle states
```

```
  57:      * were detected
```

```
  58:      */
```

```
  59:     if (i)
```

```
  60:         drv->state_count = state_idx;
```

```
  61:  
```

```
  62:     /*
```

```
  63:      * Return the number of present and valid DT idle states, which can
```

```
  64:      * also be 0 on platforms with missing DT idle states or legacy DT
```

```
  65:      * configuration predating the DT idle states bindings.
```

```
  66:      */
```

```
  67:     return i;
```

```
  68: }
```

```
  69: EXPORT_SYMBOL_GPL(dt_init_idle_driver);
```

1）14~21、28~33行，获取第一个cpu的node，通过其中的“cpu-idle-states”字段，解析出该cpu支持的cpuidle states。同时通过idle\_state\_valid接口，检查其它CPU是否同样支持这些states，如果不支持，返回错误。也就是说，ARM64 generic CPU idle driver，只支持那些所有cpuidle state都相同的ARM64平台。

2）40~47行，针对每一个支持的state，调用init\_state\_node接口，解析cpuidle state相关的信息，并保存在drv->state数组的指定index中。解析的过程中，会为每个state指定enter回调函数，对ARM64而言，统一使用arm64\_enter\_idle\_state接口。其它的解析过程，比较简单，不再详细说明了。

#### 4. cpu\_init\_idle

cpuidle功能的支持，需要依赖CPU的、和电源管理有关的底层代码实现。对ARM64来说，kernel将这些底层代码抽象为一系列的操作函数集（struct cpu\_operations，具体可参考arch/arm64/kernel/cpu\_ops.c）。对同一个ARM平台，可能有多种类型的操作函数集，设计者可以根据需要选择一种使用（具体可参考本站后续的文档）。

以ARM64为例，ARM document规定了一种PSCI（Power State Coordination Interface）接口，它由firmware实现，用于电源管理有关的操作，如IDLE相关的、SMP相关的、Hotplug相关的、等等。

对cpuidle来说，需要在cpuidle driver注册之前，调用cpu\_init\_idle，该函数会根据当前使用的操作函数集，调用其中的cpu\_init\_idle回调函数，进行idle相关的初始化操作。具体的内容，蜗蜗会在其它文章中说明，这里就暂停了。

#### 5. arm64\_enter\_idle\_state

idle state的enter函数用于使CPU进入指定的idle state，如下：

```
   1: static int arm64_enter_idle_state(struct cpuidle_device *dev,
```

```
   2:                                   struct cpuidle_driver *drv, int idx)
```

```
   3: {
```

```
   4:         int ret;
```

```
   5:  
```

```
   6:         if (!idx) {
```

```
   7:                 cpu_do_idle();
```

```
   8:                 return idx;
```

```
   9:         }
```

```
  10:  
```

```
  11:         ret = cpu_pm_enter();
```

```
  12:         if (!ret) {
```

```
  13:                 /*
```

```
  14:                  * Pass idle state index to cpu_suspend which in turn will
```

```
  15:                  * call the CPU ops suspend protocol with idle index as a
```

```
  16:                  * parameter.
```

```
  17:                  */
```

```
  18:                 ret = cpu_suspend(idx);
```

```
  19:  
```

```
  20:                 cpu_pm_exit();
```

```
  21:         }
```

```
  22:  
```

```
  23:         return ret ? -1 : idx;
```

```
  24: }
```

> 如果是idle state0（即WFI），调用传统cpu\_do\_idle接口，该接口的实现，可参照“[Linux cpuidle framework(1)\_概述和软件架构](/pm_subsystem/cpuidle_overview.html)”中第2章ARM9的例子，在kernel source code中跟踪；
>
> 对于其它的state，首先调用cpu\_pm\_enter，发出CPU即将进入low power state的通知。如果成功，则调用cpu\_suspend接口，让cpu进入指定的idle状态。最后，从idle返回时，发送退出low power state的通知；
>
> cpu\_pm\_enter/cpu\_pm\_exit位于kernel/cpu\_pm.c中，会在其它文章介绍；
>
> cpu\_suspend位于arch/arm64/kernel/suspend.c中，直接调用操作函数集（struct cpu\_operations，如PSCI）中的cpu\_suspend回调函数。具体会在其它文章中描述。

*原创文章，转发请注明出处。蜗窝科技*，[www.wowotech.net](/pm_subsystem/cpuidle_arm64.html)。
