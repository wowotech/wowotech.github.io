---
title: "Linux CPU core的电源管理(3)_cpu ops"
date: 2015-07-17T22:15:06+08:00
url: "/pm_subsystem/cpu_ops.html"
gid: "200"
emlog_type: "blog"
summary: "\r\n\t由“ARMv8-a架构简介”中有关的介绍可知，ARMv8（包括ARMv7的一些扩展）引入了Virtualization、Security等概念。在这些概念之下，传统的CPU boot、shutdown、reset、suspend/resume等操作，不再那么简单和单纯。因此，ARM将这些底层操作抽象为一些operations，在以统一的方式向上层软件提供API的同时，可以根据不同的场景，有不"
author: "wowo"
category: "电源管理子系统"
category_alias: "pm_subsystem"
tags: ["Linux", "SMP", "cpu", "operations", "spin_table", "psci"]
views: 36219
comment_count: 20
aliases:
  - "/pm_subsystem/200.html"
  - "/200.html"
---

#### 1. 前言

由“[ARMv8-a架构简介](/armv8a_arch/armv8-a_overview.html)”中有关的介绍可知，ARMv8（包括ARMv7的一些扩展）引入了Virtualization、Security等概念。在这些概念之下，传统的CPU boot、shutdown、reset、suspend/resume等操作，不再那么简单和单纯。因此，ARM将这些底层操作抽象为一些operations，在以统一的方式向上层软件提供API的同时，可以根据不同的场景，有不同的实现。这就是本文要描述的cpu ops。

注1：由“[Linux CPU core的电源管理(1)\_概述](/pm_subsystem/cpu_core_pm_overview.html)”的描述可知，cpu ops属于arch-dependent的部分，本文基于ARM64平台。

#### 2. cpu ops的功能

要弄明白cpu ops真正意义，我们需要回忆两个知识点：“[Linux CPU core的电源管理(2)\_cpu topology](/pm_subsystem/cpu_topology.html)”中描述的ARM CPU的拓扑结构，主要包括Cluster、Core、Thread等概念；“[ARMv8-a架构简介](/armv8a_arch/armv8-a_overview.html)”中提到的Exception level的概念，如下：

[![7ffa71881f6356c740ef254b01cecf1520150707143059[1]](/content/uploadfile/201507/4aee3f10eadca0ea070fabba987b602120150717141504.gif "7ffa71881f6356c740ef254b01cecf1520150707143059[1]")](/content/uploadfile/201507/20184bf83cbf4915032568c751575d4120150717141503.gif)

基于上面两个知识点，我们来理解一下cpu ops现实意义，以及它所提供的功能。

**2.1 secondary CPU boot**

ARM64是一个SMP系统，可能包含多个cluster、多核CPU core（注2：目前为止，ARM没有明显提出多线程的概念）。在SMP系统中，Linux kernel会在一个CPU（primary CPU）上完成启动操作。primary CPU启动完成后，再启动其它的CPU（secondary CPUs），这称作secondary CPU boot。

继续secondary CPU boot的话题之前，我们先理解一下“boot”的意义。接触过单片机的人都知道，所谓的CPU boot，就是让CPU执行（取指译码/执行）代码（这里为linux kernel），有如下的表现方式：

> 1）所有的CPU，一上电，就会从固定的地址（一般为0）取指、执行。
>
> 2）最简单的嵌入式系统，会将代码保存在ROM中，并把ROM映射到0地址，因此CPU上电后，会自动执行代码。
>
> 3）稍微复杂一点的系统，CPU（或SOC）中会集成一个ROM，ROM上有CPU厂商在出厂时固化的代码，这些代码会进行一些必要的初始化后，将CPU跳转到其它地址（例如0x20000000），这些地址一般是RAM或者NOR flash，用户代码可以存放在这些位置。
>
> 4）更复杂的系统，例如基于ARM64的SOC，可能包含多个CPU core，不同的CPU core可能有着不同的power domain，因而有可能单独上电。
>
> 5）再复杂一些，例如实现了virtualization功能的ARM64，linux kernel（上面图片中的Guest OS）运行在虚拟CPU上，此时的boot，需要依赖下层的Hypervisor。
>
> 6）等等。

因此，不同的SOC，可能有着不同的secondary CPU boot的方法，OS（如linux kernel）必须能够应付这种差异。至于应付的方法，无非就是封装、抽象：将boot相关的功能抽象为标准接口，上层软件（arch/arm64/kernel/smp.c）以统一的方式调用，下层软件（arch/arm64/kernel/psci.c等）根据具体的架构，实现这些功能。

**2.2 CPU hotplug**

hotplug功能，是在处理性能需求不高的情况下，从物理上关闭不需要的CPU core，并在需要的时候，将它们切换为online状态的一种手段。

和cpuidle类似，cpu hotplug也是根据系统负荷，动态调整处理器性能，从而达到节省功耗的目的。其区别在于：

> 处于idle状态的CPU，对调度器来说是可见的，换句话说，调度器并不知道某个CPU是否处于idle状态，因此不需要对它们做特殊处理。
>
> 而处于un-hotplugged状态CPU，对调度器是不可见，因此调度器必须做一些额外的处理，包括：负荷较低时，主动移除CPU，并将该CPU上的中断等资源迁移到其它CPU上，同时进行必要的负载均衡；反之亦然。

同样的道理，不同的架构，CPU hotplug的方式也不一样，嗯，封装抽象嘛！

**2.3 idle、shutdown、reset、suspend/resume、big·LITTLE等电源管理操作**

同理，不同的架构，这些电源管理操作的实现方式也不一样，例如：

> 1）假设一个SOC，有多个cluster、多个core，且这些cluster和core都可以单独供电。那么shutdown操作就比较复杂，例如，每一个core掉电后，都要检查该core的sibling core是否都已掉电，如果是，则关闭cluster的供电。
>
> 2）再假如，在实现了virtualization的系统上，某一个Guest OS要求reset、suspend系统，必须经过Hypervisor处理，否则就会影响其它OS的正常工作。
>
> 3）等等

接着封装抽象吧。

最后总结一下，cpu ops存在的本质意义是什么？我的理解是：

> 在SMP、Virtualization、Security等大背景下，OS对CPU core及其power等资源的使用，可能存在独占、共享等多种方式。这就要求OS能抽象出一个友好、实用的框架，去管理、使用这些资源。具体请参考后面的描述。

#### 3. ARM64 cpu ops在kernel中的实现

**3.1 struct cpu\_operations结构**

对ARM64平台来说，kernel使用struct cpu\_operations来抽象cpu ops，如下：

```
   1: /* arch/arm64/include/asm/cpu_ops.h */
```

```
   2: /**
```

```
   3:  * struct cpu_operations - Callback operations for hotplugging CPUs.
```

```
   4:  *
```

```
   5:  * @name:       Name of the property as appears in a devicetree cpu node's
```

```
   6:  *              enable-method property.
```

```
   7:  * @cpu_init:   Reads any data necessary for a specific enable-method from the
```

```
   8:  *              devicetree, for a given cpu node and proposed logical id.
```

```
   9:  * @cpu_init_idle: Reads any data necessary to initialize CPU idle states from
```

```
  10:  *              devicetree, for a given cpu node and proposed logical id.
```

```
  11:  * @cpu_prepare: Early one-time preparation step for a cpu. If there is a
```

```
  12:  *              mechanism for doing so, tests whether it is possible to boot
```

```
  13:  *              the given CPU.
```

```
  14:  * @cpu_boot:   Boots a cpu into the kernel.
```

```
  15:  * @cpu_postboot: Optionally, perform any post-boot cleanup or necesary
```

```
  16:  *              synchronisation. Called from the cpu being booted.
```

```
  17:  * @cpu_disable: Prepares a cpu to die. May fail for some mechanism-specific
```

```
  18:  *              reason, which will cause the hot unplug to be aborted. Called
```

```
  19:  *              from the cpu to be killed.
```

```
  20:  * @cpu_die:    Makes a cpu leave the kernel. Must not fail. Called from the
```

```
  21:  *              cpu being killed.
```

```
  22:  * @cpu_kill:  Ensures a cpu has left the kernel. Called from another cpu.
```

```
  23:  * @cpu_suspend: Suspends a cpu and saves the required context. May fail owing
```

```
  24:  *               to wrong parameters or error conditions. Called from the
```

```
  25:  *               CPU being suspended. Must be called with IRQs disabled.
```

```
  26:  */
```

```
  27: struct cpu_operations {
```

```
  28:         const char      *name;
```

```
  29:         int             (*cpu_init)(struct device_node *, unsigned int);
```

```
  30:         int             (*cpu_init_idle)(struct device_node *, unsigned int);
```

```
  31:         int             (*cpu_prepare)(unsigned int);
```

```
  32:         int             (*cpu_boot)(unsigned int);
```

```
  33:         void            (*cpu_postboot)(void);
```

```
  34: #ifdef CONFIG_HOTPLUG_CPU
```

```
  35:         int             (*cpu_disable)(unsigned int cpu);
```

```
  36:         void            (*cpu_die)(unsigned int cpu);
```

```
  37:         int             (*cpu_kill)(unsigned int cpu);
```

```
  38: #endif
```

```
  39: #ifdef CONFIG_ARM64_CPU_SUSPEND
```

```
  40:         int             (*cpu_suspend)(unsigned long);
```

```
  41: #endif
```

```
  42: };
```

> 该接口提供了一些CPU操作相关的回调函数，由底层代码（可以称作cpu ops driver）根据实际情况实现，并由ARM64的SMP模块（可参考“[Linux CPU core的电源管理(1)\_概述](/pm_subsystem/cpu_core_pm_overview.html)”中的相关描述）调用：
>
> name，该operations的名字，需要唯一。
>
> cpu\_init，该cpu operations的初始化接口，会在SMP初始化时调用，cpu ops driver可以在这个接口中，完成一些必须的初始化动作，如读取寄存器值、从DTS中获取配置等。
>
> cpu\_init\_idle，CPU idle有关的初始化接口，会由cpuidle driver在初始化时调用（可参考“[Linux *cpuidle* framework(3)\_ARM64 generic *CPU* *idle* driver](/pm_subsystem/cpuidle_arm64.html)”）。cpu ops driver可以在这个接口中实现和idle有关的初始化操作，我们会在后续将PSCI ops的时候再介绍。
>
> cpu\_prepare、cpu\_boot、cpu\_postboot，CPU boot有关的接口，分别在boot前、boot时、boot后调用。
>
> 如果使能了hotplug功能，除了boot接口之外，需要额外实现用于关闭CPU（和 boot相对）的接口，包括cpu\_disable、cpu\_die、cpu\_kill，后面介绍hotplug流程中，会重点介绍这几个接口。
>
> 如果使能了CPU suspend功能，则由cpu\_suspend完成相应的suspend动作。

**3.2 cpu ops driver**

kernel中ARM64的核心代码（arch/arm64/kernel）通过struct cpu\_operations结构规定了cpu ops的基本框架，不同的硬件实现，则可使用不同的operations。针对ARM64，kernel提供了两种可选的方法，smp spin table和psci，如下：

```
   1: /* arch/arm64/kernel/cpu_ops.c */
```

```
   2:  
```

```
   3: static const struct cpu_operations *supported_cpu_ops[] __initconst = {
```

```
   4: #ifdef CONFIG_SMP
```

```
   5:         &smp_spin_table_ops,
```

```
   6: #endif
```

```
   7:         &cpu_psci_ops,
```

```
   8:         NULL,
```

```
   9: };
```

具体使用哪一个operation，是通过DTS指定的，DTS格式如下：

```
   1: /* spin-table: arch/arm64/boot/dts/apm-storm.dtsi */
```

```
   2: cpus {
```

```
   3:         ...
```

```
   4:         cpu@000 {
```

```
   5:                 ...
```

```
   6:                 enable-method = "spin-table";
```

```
   7:                 cpu-release-addr = <0x1 0x0000fff8>;
```

```
   8:         };
```

```
   9:         ...
```

```
  10: };
```

```
  11:  
```

```
  12: /* or psci: arch/arm64/boot/dts/thunder-88xx.dtsi */
```

```
  13: cpus {
```

```
  14:         ...
```

```
  15:         cpu@000 {
```

```
  16:                 ...
```

```
  17:                 enable-method = "psci";
```

```
  18:         };
```

```
  19:         ...
```

```
  20: };
```

> 即，在每一个cpu子节点中，使用“enable-method”指定是使用“spin-table”还是“psci”。

系统初始化的时候，会根据DTS信息，获取使用的operations（setup\_arch-->cpu\_read\_bootcpu\_ops-->cpu\_read\_ops），最终保存在一个operation数组（每个CPU一个）中，供SMP（arch/arm64/kernel/smp.c）使用，如下：

```
   1: /* arch/arm64/kernel/cpu_ops.c */
```

```
   2: const struct cpu_operations *cpu_ops[NR_CPUS];
```

相关的流程比较简单，具体可参考代码。

#### 4. spin-table operations

spin-table是一种简单的、可支持SMP操作的cpu operations，在“arch/arm64/kernel/smp\_spin\_table.c”中实现：

```
   1: const struct cpu_operations smp_spin_table_ops = {
```

```
   2:         .name           = "spin-table",
```

```
   3:         .cpu_init       = smp_spin_table_cpu_init,
```

```
   4:         .cpu_prepare    = smp_spin_table_cpu_prepare,
```

```
   5:         .cpu_boot       = smp_spin_table_cpu_boot,
```

```
   6: };
```

由上面的实现可知，spin-table operations只支持cpu\_init、cpu\_prepare和cpu\_boot三个回调函数，因此，它只能实现secondary cpu boot的功能，其他功能，如cpu hotplug、cpuidle、电源管理等，均不支持。

**4.1 secondary cpu boot流程**

它的名字（spin）就可以看出secondary cpu boot的实现逻辑，即：

SOC上电后，每个CPU都启动（开始执行ROM代码），除了boot CPU正常执行外，其它的secondary CPUs，都等待在一个地方（例如使用WFE指令），直到boot CPU启动完成后，再发消息通知其它CPU执行。示意图如下。

[![secondary cpu boot](/content/uploadfile/201507/ecfdf657820437c44db7467cb80b5d3720150723140402.gif "secondary cpu boot")](/content/uploadfile/201507/df853077a2540cbe6314ca6a5f48d34e20150723140350.gif)

1）系统上电后，每个CPU都开始执行bootloader（这里以u-boot为例），boot CPU在进行必要的初始化后，继续执行。其它CPU（secondary CPU），则等待在一个地方，直到一个地址（由CPU\_RELEASE\_ADDR指定，因此该地址就为spin table）变为非零值，就会跳到改地址所指定的位置继续执行。为了节省power，这里的等待可以通过WFE指令，使CPU进入idle状态。

2）boot CPU进入kernel，在初始化的过程中，依次执行.cpu\_init()，.cpu\_prepare()，.cpu\_boot()三个回调函数，boot secondary CPUs。以本节所描述的spin-table operations为例，这三个回调函数分别完成如下功能：

```
   1: static int smp_spin_table_cpu_init(struct device_node *dn, unsigned int cpu)
```

```
   2: {
```

```
   3:         /*
```

```
   4:          * Determine the address from which the CPU is polling.
```

```
   5:          */
```

```
   6:         if (of_property_read_u64(dn, "cpu-release-addr",
```

```
   7:                                  &cpu_release_addr[cpu])) {
```

```
   8:                 pr_err("CPU %d: missing or invalid cpu-release-addr property\n",
```

```
   9:                        cpu);
```

```
  10:  
```

```
  11:                 return -1;
```

```
  12:         }
```

```
  13:  
```

```
  14:         return 0;
```

```
  15: }
```

> .cpu\_init()接口，负责从DTS中解析出每个secondary CPU的“cpu-release-addr”，其实就是上面所说的CPU\_RELEASE\_ADDR。

```
   1: static int smp_spin_table_cpu_prepare(unsigned int cpu)
```

```
   2: {
```

```
   3:         __le64 __iomem *release_addr;
```

```
   4:  
```

```
   5:         if (!cpu_release_addr[cpu])
```

```
   6:                 return -ENODEV;
```

```
   7:  
```

```
   8:         /*
```

```
   9:          * The cpu-release-addr may or may not be inside the linear mapping.
```

```
  10:          * As ioremap_cache will either give us a new mapping or reuse the
```

```
  11:          * existing linear mapping, we can use it to cover both cases. In
```

```
  12:          * either case the memory will be MT_NORMAL.
```

```
  13:          */
```

```
  14:         release_addr = ioremap_cache(cpu_release_addr[cpu],
```

```
  15:                                      sizeof(*release_addr));
```

```
  16:         if (!release_addr)
```

```
  17:                 return -ENOMEM;
```

```
  18:  
```

```
  19:         /*
```

```
  20:          * We write the release address as LE regardless of the native
```

```
  21:          * endianess of the kernel. Therefore, any boot-loaders that
```

```
  22:          * read this address need to convert this address to the
```

```
  23:          * boot-loader's endianess before jumping. This is mandated by
```

```
  24:          * the boot protocol.
```

```
  25:          */
```

```
  26:         writeq_relaxed(__pa(secondary_holding_pen), release_addr);
```

```
  27:         __flush_dcache_area((__force void *)release_addr,
```

```
  28:                             sizeof(*release_addr));
```

```
  29:  
```

```
  30:         /*
```

```
  31:          * Send an event to wake up the secondary CPU.
```

```
  32:          */
```

```
  33:         sev();
```

```
  34:  
```

```
  35:         iounmap(release_addr);
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

> .cpu\_prepare()接口，将secondary\_holding\_pen的物理地址写入“cpu-release-addr”，并调用sev()指令，唤醒那些处于WFE状态的secondary CPUs，它们开始执行secondary\_holding\_pen函数。

.cpu\_boot()的功能后面再介绍。

3）secondary CPUs开始执行secondary\_holding\_pen，该接口的主要共功能是：

```
   1: /* arch/arm64/kernel/head.S */
```

```
   2:  
```

```
   3:         .align  3
```

```
   4: 1:      .quad   .
```

```
   5:         .quad   secondary_holding_pen_release
```

```
   6:  
```

```
   7:         /*
```

```
   8:          * This provides a "holding pen" for platforms to hold all secondary
```

```
   9:          * cores are held until we're ready for them to initialise.
```

```
  10:          */
```

```
  11: ENTRY(secondary_holding_pen)
```

```
  12:         bl      el2_setup                       // Drop to EL1, w20=cpu_boot_mode
```

```
  13:         bl      __calc_phys_offset              // x24=PHYS_OFFSET, x28=PHYS_OFFSET-PAGE_OFFSET
```

```
  14:         bl      set_cpu_boot_mode_flag
```

```
  15:         mrs     x0, mpidr_el1
```

```
  16:         ldr     x1, =MPIDR_HWID_BITMASK
```

```
  17:         and     x0, x0, x1
```

```
  18:         adr     x1, 1b
```

```
  19:         ldp     x2, x3, [x1]
```

```
  20:         sub     x1, x1, x2
```

```
  21:         add     x3, x3, x1
```

```
  22:         ldr     x4, [x3]
```

```
  23: pen:    cmp     x4, x0
```

```
  24:         b.eq    secondary_startup
```

```
  25:         wfe
```

```
  26:         b       pen
```

```
  27: ENDPROC(secondary_holding_pen)
```

> 首先，执行secondary\_holding\_pen，就意味着secondary CPUs们已经进入了kernel。
>
> 在这里，CPU继续等到，直到secondary\_holding\_pen\_release变量和该CPU的ID（由寄存器mpidr\_el1读取）相同，才继续执行后续操作（secondary\_startup）。
>
> 那什么时候secondary\_startup变量和CPU ID相同呢？看一下.cpu\_boot()就知道了。

```
   1: /*
```

```
   2:  * Write secondary_holding_pen_release in a way that is guaranteed to be
```

```
   3:  * visible to all observers, irrespective of whether they're taking part
```

```
   4:  * in coherency or not.  This is necessary for the hotplug code to work
```

```
   5:  * reliably.
```

```
   6:  */
```

```
   7: static void write_pen_release(u64 val)
```

```
   8: {
```

```
   9:         void *start = (void *)&secondary_holding_pen_release;
```

```
  10:         unsigned long size = sizeof(secondary_holding_pen_release);
```

```
  11:  
```

```
  12:         secondary_holding_pen_release = val;
```

```
  13:         __flush_dcache_area(start, size);
```

```
  14: }
```

```
  15:  
```

```
  16: static int smp_spin_table_cpu_boot(unsigned int cpu)
```

```
  17: {
```

```
  18:         /*
```

```
  19:          * Update the pen release flag.
```

```
  20:          */
```

```
  21:         write_pen_release(cpu_logical_map(cpu));
```

```
  22:  
```

```
  23:         /*
```

```
  24:          * Send an event, causing the secondaries to read pen_release.
```

```
  25:          */
```

```
  26:         sev();
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

> 原来是.cpu\_boot()向secondary\_holding\_pen\_release中写了自己的CPU ID。为什么要这样呢？
>
> .cpu\_prepare()只是尽快让secondary CPUs进入kernel（以便释放bootloader占用的资源）。但是，要继续执行，必须在boot CPU执行完必要的初始化之后，那就等待咯。

注3：smp spin table operations是非常简单的一种cpu ops，不支持其它的电源管理功能，不支持cpu hotplug，不支持virtualization和security。因此，在ARMv8处理器中，几乎很少使用它作为CPU操作的底层实现。

#### 5. psci operations

PSCI是Power State Coordination Interface的简称，鉴于它的复杂度和篇幅问题，我们放到另一篇文章中单独描述。本文就到此结束了。

*原创文章，转发请注明出处。蜗窝科技*，[www.wowotech.net](/pm_subsystem/cpu_ops.html)。
