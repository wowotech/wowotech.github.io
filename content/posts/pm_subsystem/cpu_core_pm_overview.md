---
title: "Linux CPU core的电源管理(1)_概述"
date: 2015-04-30T21:20:49+08:00
url: "/pm_subsystem/cpu_core_pm_overview.html"
gid: "181"
emlog_type: "blog"
summary: "在SMP（Symmetric Multi-Processing）流行起来之前的很长一段时间，Linux kernel的电源管理工作主要集中在外部设备上，和CPU core相关的，顶多就是 CPU idle 。但随着SMP的普及，一个系统中可用的CPU core越来越多，这些core的频率越来越高，处理能力越来越强，功耗也越来越大。因此，CPU core有关的电源管理，在系统设计中就成为必不可少的一"
author: "wowo"
category: "电源管理子系统"
category_alias: "pm_subsystem"
tags: ["Linux", "PM", "core", "cpu"]
views: 45175
comment_count: 22
aliases:
  - "/pm_subsystem/181.html"
  - "/181.html"
---

#### 1. 前言

在SMP（Symmetric Multi-Processing）流行起来之前的很长一段时间，Linux kernel的电源管理工作主要集中在外部设备上，和CPU core相关的，顶多就是[CPU idle](/tag/cpuidle)。但随着SMP的普及，一个系统中可用的CPU core越来越多，这些core的频率越来越高，处理能力越来越强，功耗也越来越大。因此，CPU core有关的电源管理，在系统设计中就成为必不可少的一环，与此有关的思考包括：

> 对消费者（一些专业应用除外）而言，这种暴增的处理能力，是一种极大的浪费，他们很少（或者从不）有如此高的性能需求。但商家对此却永远乐此不疲，原因无外乎：
>
> 1）硬件成本越来越低。
>
> 2）营销的噱头。
>
> 3）软件设计者的不思进取（臃肿的Android就是典型的例子），导致软件效率低下，硬件资源浪费严重。以至于优化几行代码的难度，甚至比增加几个cpu核还困难。

在这种背景下，CPU core的电源管理逻辑，就非常直接了：根据系统的负荷，关闭“多余的CPU性能”，在满足用户需求的前提下，尽可能的降低CPU的功耗。但CPU的控制粒度不可能无限小，目前主要从两个角度实现CPU core的电源管理功能：

1）在SMP系统中，动态的关闭或者打开CPU core（本文重点介绍的功能）。

2）CPU运行过程中，动态的调整CPU core的电压和频率（将在其它文章中单独分析）。

本文将以ARM64为例，介绍linux kernel CPU core相关的电源管理设计。

#### 2. 功能说明

在linux kernel中，CPU core相关的电源管理实现，并不是单纯的电源管理行为，它会涉及到系统初始化、CPU拓扑结构、进程调度、CPU hotplug、memory hotplug等知识点。总的来说，它主要完成如下功能：

> 1）系统启动时，CPU core的初始化、信息获取等。
>
> 2）系统启动时，CPU core的启动（enable）。
>
> 3）系统运行过程中，根据当前负荷，动态的enable/disable某些CPU core，以便在性能和功耗之间平衡。
>
> 4）CPU core的hotplug支持。所谓的hotplug，是指可以在系统运行的过程中，动态的增加或者减少CPU core（可以是物理上，也可以是逻辑上）。
>
> 5）系统运行过程中的CPU idle管理（具体可参考“[Linux cpuidle framework系列文章](/tag/cpuidle)”）。
>
> 6）系统运行过程中，根据当前负荷，动态的调整CPU core的电压和频率，以便在性能和功耗之间平衡。

#### 3. 软件架构

为了实现上面的功能，linux kernel抽象出了下面的软件框架：

[![linux cpu core pm](/content/uploadfile/201504/23077f45145799ce4673cf8feb217c5720150430132045.gif "linux cpu core pm")](/content/uploadfile/201504/6cb8fb196fda5e0d6389a2afe1e5f73020150430132045.gif)

软件框架包括arch-dependent和arch-independent两部分。

对ARM64而言，arch-dependent部分位于“arch\arm64\kernel”，负责提供平台相关的控制操作，包括：

> CPU信息的获取（cpuinfo）；
>
> CPU拓扑结构的获取（cpu topology）；
>
> 底层的CPU操作（init、disable等）的实现，cpu ops（在ARM32中是以smp ops的形式存在的）；
>
> SMP相关的初始化（smp）；
>
> 等等。

arch-independent负责实现平台无关的抽象，包括：

> CPU control模块，屏蔽底层平台相关的实现细节，提供控制CPU（enable、disable等）的统一API，供系统启动、进程调度等模块调用；
>
> CPU subsystem driver，向用户空间提供CPU hotplug有关的功能；
>
> cpuidle，处理CPU idle有关的逻辑，具体可参考“[cpuidle framework](/tag/cpuidle)”相关的文章；
>
> cpufreq，处理CPU frequency调整有关的逻辑，具体可参考后续的文章；
>
> 等等。

#### 4. 软件模块的功能及API描述

**4.1 kernel cpu control**

kernel cpu control位于“.\kernel\cpu.c”中，是一个承上启下的模块，负责屏蔽arch-dependent的实现细节，向上层软件提供CPU core控制的统一API。主要功能包括：

1）将CPU core抽象为possible、present、online和active四种状态，并以bitmap的形式，在模块内部维护所有CPU core的状态，同时以cpumask的形式向其它模块提供状态查询、状态修改的API。相关的API如下：

```
   1: /* kernel/cpu.c */
```

```
   2:  
```

```
   3: #ifdef CONFIG_INIT_ALL_POSSIBLE
```

```
   4: static DECLARE_BITMAP(cpu_possible_bits, CONFIG_NR_CPUS) __read_mostly
```

```
   5:         = CPU_BITS_ALL;
```

```
   6: #else
```

```
   7: static DECLARE_BITMAP(cpu_possible_bits, CONFIG_NR_CPUS) __read_mostly;
```

```
   8: #endif
```

```
   9: const struct cpumask *const cpu_possible_mask = to_cpumask(cpu_possible_bits);
```

```
  10: EXPORT_SYMBOL(cpu_possible_mask);
```

```
  11:  
```

```
  12: static DECLARE_BITMAP(cpu_online_bits, CONFIG_NR_CPUS) __read_mostly;
```

```
  13: const struct cpumask *const cpu_online_mask = to_cpumask(cpu_online_bits);
```

```
  14: EXPORT_SYMBOL(cpu_online_mask);
```

```
  15:  
```

```
  16: static DECLARE_BITMAP(cpu_present_bits, CONFIG_NR_CPUS) __read_mostly;
```

```
  17: const struct cpumask *const cpu_present_mask = to_cpumask(cpu_present_bits);
```

```
  18: EXPORT_SYMBOL(cpu_present_mask);
```

```
  19:  
```

```
  20: static DECLARE_BITMAP(cpu_active_bits, CONFIG_NR_CPUS) __read_mostly;
```

```
  21: const struct cpumask *const cpu_active_mask = to_cpumask(cpu_active_bits);
```

```
  22: EXPORT_SYMBOL(cpu_active_mask);
```

> bitmap的定义是：
>   
> #define DECLARE\_BITMAP(name,bits) unsigned long name[BITS\_TO\_LONGS(bits)]
>
> 其本质上是一个long型的数组，数组中每一个bit，代表一个CPU core的状态。例如long的长度为64位的系统中，如果有8个CPU core，则可以使用长度为1的数组的前8个bit，代表这个8个core的状态。
>
> 这里一共有4种状态需要表示：
>
> cpu\_possible\_bits，系统中包含的所有的可能的CPU core，在系统初始化的时候就已经确定。对于ARM64来说，DTS中所有格式正确的CPU core，都属于possible的core；
>
> cpu\_present\_bits，系统中所有可用的CPU core（具备online的条件，具体由底层代码决定），并不是所有possible的core都是present的。对于支持CPU hotplug的形态，present core可以动态改变；
>
> cpu\_online\_bits，系统中所有运行状态的CPU core（后面会详细说明这个状态的意义）；
>
> cpu\_active\_bits，有active的进程正在运行的CPU core。
>
> 另外，在使用bitmap表示这4种状态的同时，还提供了4个cpumask，用于对外提供接口。cpumask的本质也是bitmap（多一层封装而已），只是kernel提供了一些方便的API，可以以CPU编号为单位，操作cpumask（具体可参考include/linux/cpumask.h）。
>
> 注1：这里有一个关于constant变量的经典例子，大家可以学习一下。
>   
> 毫无疑问，CPU core的这些状态，是相当重要的一些状态，因此kernel希望它们对外（除cpu control外）是read only的，对内又是writeable的。怎么办呢？
>   
> 这里的设计很巧妙，对内使用4个static的bitmap变量，因此是writeable的。而对外呢，使用4个constant类型的cpumask指针（指针readonly，值readonly），因此是readonly的。
>   
> 外部模块read时，通过一层转换，从static的bitmap中获取实际的值。是不是很有意思？

下面是这几个变量有关的操作函数：

```
   1: /* include/linux/cpumask.h */
```

```
   2:  
```

```
   3: #define num_online_cpus()       cpumask_weight(cpu_online_mask)
```

```
   4: #define num_possible_cpus()     cpumask_weight(cpu_possible_mask)
```

```
   5: #define num_present_cpus()      cpumask_weight(cpu_present_mask)
```

```
   6: #define num_active_cpus()       cpumask_weight(cpu_active_mask)
```

```
   7: #define cpu_online(cpu)         cpumask_test_cpu((cpu), cpu_online_mask)
```

```
   8: #define cpu_possible(cpu)       cpumask_test_cpu((cpu), cpu_possible_mask)
```

```
   9: #define cpu_present(cpu)        cpumask_test_cpu((cpu), cpu_present_mask)
```

```
  10: #define cpu_active(cpu)         cpumask_test_cpu((cpu), cpu_active_mask)
```

```
  11:  
```

```
  12:  
```

```
  13: #define for_each_possible_cpu(cpu) for_each_cpu((cpu), cpu_possible_mask)
```

```
  14: #define for_each_online_cpu(cpu)   for_each_cpu((cpu), cpu_online_mask)
```

```
  15: #define for_each_present_cpu(cpu)  for_each_cpu((cpu), cpu_present_mask)
```

```
  16:  
```

```
  17: /* Wrappers for arch boot code to manipulate normally-constant masks */
```

```
  18: void set_cpu_possible(unsigned int cpu, bool possible);
```

```
  19: void set_cpu_present(unsigned int cpu, bool present);
```

```
  20: void set_cpu_online(unsigned int cpu, bool online);
```

```
  21: void set_cpu_active(unsigned int cpu, bool active);
```

```
  22: void init_cpu_present(const struct cpumask *src);
```

```
  23: void init_cpu_possible(const struct cpumask *src);
```

```
  24: void init_cpu_online(const struct cpumask *src);
```

2）提供CPU core的up/down操作，以及up/down时的notifier机制

通俗地讲，所谓的CPU core up，就是将某一个CPU core“运行”起来。何为运行呢？回忆一下单核CPU的启动，就是让该CPU core在指定的memory地址处取指执行。因此该功能只对SMP系统有效（使能了CONFIG\_SMP）。而CPU core down，就是让CPU core保存现场（后面可以继续执行）后，停止取指，只有在CPU hotplug功能使能（CONFIG\_HOTPLUG\_CPU）时有效。这两个功能对应的API为：

```
   1: /* include/linux/cpu.h */
```

```
   2:  
```

```
   3: int cpu_up(unsigned int cpu);
```

```
   4:  
```

```
   5: int cpu_down(unsigned int cpu);
```

同时，提供了CPU up/down时的通知API，具体请参考“include/linux/cpu.h"。

3）提供SMP PM有关的操作

系统休眠过程中，将noboot的CPU禁用，并在系统恢复时恢复（可参考“[Linux电源管理(6)\_Generic PM之*Suspend*功能](/pm_subsystem/suspend_and_resume.html)”中的有关描述）。

```
   1: #ifdef CONFIG_PM_SLEEP_SMP
```

```
   2: extern int disable_nonboot_cpus(void);
```

```
   3: extern void enable_nonboot_cpus(void);
```

```
   4: #else /* !CONFIG_PM_SLEEP_SMP */
```

```
   5: static inline int disable_nonboot_cpus(void) { return 0; }
```

```
   6: static inline void enable_nonboot_cpus(void) {}
```

```
   7: #endif /* !CONFIG_PM_SLEEP_SMP */
```

**4.2 cpu subsystem driver**

cpu subsystem driver位于“drivers/base/cpu.c”中，从设备模型的角度，抽象CPU core设备，并通过sysfs提供CPU core状态查询、hotplug控制等接口。具体如下：

1）注册一个名称为“bus”的subsystem（在sysfs中目录为“/sys/devices/system/cpu/”，有关subsystem的描述，可参考“[Linux设备模型(6)\_Bus](/device_model/bus.html)”）。

2）使用struct cpu抽象CPU core device（见“include/linux/cpu.h”）。

4）从设备模型的角度，提供CPU core device的register/unregister等接口，并在系统初始化的时候根据CPU core的个数，将这些device注册到kernel中。同时根据kernel配置，注册相关的CPU attribute。

```
   1: extern int register_cpu(struct cpu *cpu, int num);
```

```
   2: extern struct device *get_cpu_device(unsigned cpu);
```

```
   3: extern bool cpu_is_hotpluggable(unsigned cpu);
```

```
   4: extern bool arch_match_cpu_phys_id(int cpu, u64 phys_id);
```

```
   5: extern bool arch_find_n_match_cpu_physical_id(struct device_node *cpun,
```

```
   6:                                               int cpu, unsigned int *thread);
```

```
   7:  
```

```
   8: extern int cpu_add_dev_attr(struct device_attribute *attr);
```

```
   9: extern void cpu_remove_dev_attr(struct device_attribute *attr);
```

```
  10:  
```

```
  11: extern int cpu_add_dev_attr_group(struct attribute_group *attrs);
```

```
  12: extern void cpu_remove_dev_attr_group(struct attribute_group *attrs);
```

```
  13:  
```

```
  14: #ifdef CONFIG_HOTPLUG_CPU
```

```
  15: extern void unregister_cpu(struct cpu *cpu);
```

```
  16: extern ssize_t arch_cpu_probe(const char *, size_t);
```

```
  17: extern ssize_t arch_cpu_release(const char *, size_t);
```

```
  18: #endif
```

> 最终在sysfs中的目录结构如下：
>
> # ls /sys/devices/system/cpu/
>
> autoplug/ cpu2/ cpuidle/ offline power/
>
> cpu0/ cpu3/ kernel\_max online present
>
> 具体会在后续的文章中详细说明。

**4.3 smp**

smp位于“arch/arm64/kernel/smp.c”，在arch-dependent代码中，承担承上启下的角色，主要提供两类功能：

1）arch-dependent的SMP初始化、CPU core控制等操作（本文需要关注的功能）。

2）IPI（Inter-Processor Interrupts）相关的支持（具体可参考本站“[中断子系统](/sort/irq_subsystem)”有关的文章）。

SMP初始化操作，主要负责从DTS中解析CPU core信息，并获取必要的信息以及操作函数集，由smp\_init\_cpus接口实现，并在setup\_arch（arch\arm64\kernel\setup.c）中调用。

CPU core控制相关的接口包括：

```
   1: /* arch/arm64/include/asm/smp.h */
```

```
   2:  
```

```
   3: /*
```

```
   4:  * Called from the secondary holding pen, this is the secondary CPU entry point.
```

```
   5:  */
```

```
   6: asmlinkage void secondary_start_kernel(void);
```

```
   7:  
```

```
   8: /*
```

```
   9:  * Initial data for bringing up a secondary CPU.
```

```
  10:  */
```

```
  11: struct secondary_data {
```

```
  12:         void *stack;
```

```
  13: };
```

```
  14: extern struct secondary_data secondary_data;
```

```
  15: extern void secondary_entry(void);
```

```
  16:  
```

```
  17: extern void arch_send_call_function_single_ipi(int cpu);
```

```
  18: extern void arch_send_call_function_ipi_mask(const struct cpumask *mask);
```

```
  19:  
```

```
  20: extern int __cpu_disable(void);
```

```
  21:  
```

```
  22: extern void __cpu_die(unsigned int cpu);
```

```
  23: extern void cpu_die(void);
```

> secondary\_start\_kernel、secondary\_entry，是那些 noboot CPU的入口，具体后面再详细介绍；
>
> \_\_cpu\_disable、\_\_cpu\_die、cpu\_die等函数负责disable某个CPU core，它们不会直接操作硬件，而是通过下层的cpu\_ops控制具体的CPU core，具体请参考4.4小节的说明。

**4.4 cpu ops**

由于SMP架构比较复杂，特别是对ARM64而言，又涉及到虚拟化等安全特性，ARM便将CPU core的up/down等电源管理操作，封装起来（例如封装到secure mode下，特权级别的OS代码通过一些指令码与其交互，具体请参考后续的文章）。在ARM64中，这种封装便是通过cpu os结构（struct cpu\_operations）体现的，如下：

```
   1: /* arch/arm64/include/asm/cpu_ops.h */
```

```
   2:  
```

```
   3: /**
```

```
   4:  * struct cpu_operations - Callback operations for hotplugging CPUs.
```

```
   5:  *
```

```
   6:  * @name:       Name of the property as appears in a devicetree cpu node's
```

```
   7:  *              enable-method property.
```

```
   8:  * @cpu_init:   Reads any data necessary for a specific enable-method from the
```

```
   9:  *              devicetree, for a given cpu node and proposed logical id.
```

```
  10:  * @cpu_init_idle: Reads any data necessary to initialize CPU idle states from
```

```
  11:  *              devicetree, for a given cpu node and proposed logical id.
```

```
  12:  * @cpu_prepare: Early one-time preparation step for a cpu. If there is a
```

```
  13:  *              mechanism for doing so, tests whether it is possible to boot
```

```
  14:  *              the given CPU.
```

```
  15:  * @cpu_boot:   Boots a cpu into the kernel.
```

```
  16:  * @cpu_postboot: Optionally, perform any post-boot cleanup or necesary
```

```
  17:  *              synchronisation. Called from the cpu being booted.
```

```
  18:  * @cpu_disable: Prepares a cpu to die. May fail for some mechanism-specific
```

```
  19:  *              reason, which will cause the hot unplug to be aborted. Called
```

```
  20:  *              from the cpu to be killed.
```

```
  21:  * @cpu_die:    Makes a cpu leave the kernel. Must not fail. Called from the
```

```
  22:  *              cpu being killed.
```

```
  23:  * @cpu_kill:  Ensures a cpu has left the kernel. Called from another cpu.
```

```
  24:  * @cpu_suspend: Suspends a cpu and saves the required context. May fail owing
```

```
  25:  *               to wrong parameters or error conditions. Called from the
```

```
  26:  *               CPU being suspended. Must be called with IRQs disabled.
```

```
  27:  */
```

```
  28: struct cpu_operations {
```

```
  29:         const char      *name;
```

```
  30:         int             (*cpu_init)(struct device_node *, unsigned int);
```

```
  31:         int             (*cpu_init_idle)(struct device_node *, unsigned int);
```

```
  32:         int             (*cpu_prepare)(unsigned int);
```

```
  33:         int             (*cpu_boot)(unsigned int);
```

```
  34:         void            (*cpu_postboot)(void);
```

```
  35: #ifdef CONFIG_HOTPLUG_CPU
```

```
  36:         int             (*cpu_disable)(unsigned int cpu);
```

```
  37:         void            (*cpu_die)(unsigned int cpu);
```

```
  38:         int             (*cpu_kill)(unsigned int cpu);
```

```
  39: #endif
```

```
  40: #ifdef CONFIG_ARM64_CPU_SUSPEND
```

```
  41:         int             (*cpu_suspend)(unsigned long);
```

```
  42: #endif
```

```
  43: };
```

ARM architecture提供多种可选的cpu ops实现，如spin-table、PSCI（Power State Coordination Interface）等（具体会在后续的文章中详细描述），开发者可以根据需求，选择一种。4.3节所描述的smp初始化时，会解析DTS，并填充cpu ops变量。

这里以PSCI为例，简单了解一下这些接口的含义（具体说明请参考后续的文章）。

> cpu\_boot: Boots a cpu into the kernel. 其实就是将启动函数（secondary\_entry）的物理地址，给到CPU core执行，具体要看spec
>
> cpu\_disable: Prepares a cpu to die.
>
> cpu\_die: Makes a cpu leave the kernel.
>
> cpu\_suspend: Suspends a cpu and saves the required context.

**4.5 cpu topology**

本文提到了很多诸如SMP、CPU core之类的字眼，相应读者可能看的不太明白，这和CPU的拓扑结构有关。进程调度、cpufreq等模块，可能需要根据具体的拓扑结构，制定相应的策略。

ARM64的topology在“./arch/arm64/include/asm/topology.h”中定义，如下：

```
   1: struct cpu_topology {
```

```
   2:         int thread_id;
```

```
   3:         int core_id;
```

```
   4:         int cluster_id;
```

```
   5:         cpumask_t thread_sibling;
```

```
   6:         cpumask_t core_sibling;
```

```
   7: };
```

```
   8:  
```

```
   9: extern struct cpu_topology cpu_topology[NR_CPUS];
```

```
  10:  
```

```
  11: #define topology_physical_package_id(cpu)       (cpu_topology[cpu].cluster_id)
```

```
  12: #define topology_core_id(cpu)           (cpu_topology[cpu].core_id)
```

```
  13: #define topology_core_cpumask(cpu)      (&cpu_topology[cpu].core_sibling)
```

```
  14: #define topology_thread_cpumask(cpu)    (&cpu_topology[cpu].thread_sibling)
```

```
  15:  
```

```
  16: void init_cpu_topology(void);
```

```
  17: void store_cpu_topology(unsigned int cpuid);
```

```
  18: const struct cpumask *cpu_coregroup_mask(int cpu);
```

> topology的实现位于“arch/arm64/kernel/topology.c ”中，负责在系统初始化的时候，由boot cpu读取DTS，填充每个CPU core的struct cpu\_topology变量。同时，该文件提供一些通用的宏定义，用于获取执行CPU core的信息，例如该CPU core的package id、core id等。
>
> topology的具体描述，请参考下一篇文章。

**4.6 cpu info及其它**

cpu info位于“arch/arm64/kernel/cpuinfo.c”，负责在初始化的时候将ARM CPU core有关的信息，从寄存器中读出，缓存在struct cpuinfo\_arm64类型的变量中，以便后面使用。具体不再详细描述。

#### 5. 结束语

本文简单的介绍了CPU core电源管理相关的软件组成，并认识了cpu ops、cpu topology等概念，后续将通过以下的文章进行更为详细的分析：

> [Linux CPU core的电源管理(2)\_cpu topology](/pm_subsystem/cpu_topology.html)，认识并理解ARM处理器的拓扑结构，以及cluster（socket）、core、thread等处理器结构相关的概念；
>
> [Linux CPU core的电源管理(3)\_cpu ops](/pm_subsystem/cpu_ops.html)，分析cpu operations抽象和物理意义；
>
> Linux CPU core的电源管理(4)\_PSCI，分析ARM PSCI（Power State Coordination Interface）接口；
>
> [Linux CPU core的电源管理(5)\_cpu control](/pm_subsystem/cpu_hotplug.html)，从系统的角度，分析系统初始化、进程调度、CPU hotplug等场景下，CPU up/down等操作的流程；
>
> [Linux cpufreq framework](/tag/cpufreq)系列文章，分析CPU动态频率/电压调整相关的实现。

*原创文章，转发请注明出处。蜗窝科技*，[www.wowotech.net](/pm_subsystem/cpu_core_pm_overview.html)。
