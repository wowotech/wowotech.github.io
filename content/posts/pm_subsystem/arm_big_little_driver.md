---
title: "linux cpufreq framework(5)_ARM big Little driver"
date: 2015-11-10T22:04:33+08:00
url: "/pm_subsystem/arm_big_little_driver.html"
gid: "232"
emlog_type: "blog"
summary: "\r\n\t也许大家会觉得奇怪：为什么Linux kernel把对ARM big·Lttile的支持放到了cpufreq的框架中？\r\n\r\n\r\n\t众所周知，ARM的big·Little架构，也称作HMP（具体可参考“Linux CPU \r\ncore的电源管理(2)_cpu topology”中相关的介绍），通过在一个chip中封装两种不同类型的ARM \r\ncore的方式，达到性能和功耗的平衡。这两类ARM"
author: "wowo"
category: "电源管理子系统"
category_alias: "pm_subsystem"
tags: ["Linux", "ARM", "cpufreq", "hmp", "big", "little"]
views: 22745
comment_count: 35
aliases:
  - "/pm_subsystem/232.html"
  - "/232.html"
---

#### 1. 前言

也许大家会觉得奇怪：为什么Linux kernel把对ARM big·Lttile的支持放到了cpufreq的框架中？

众所周知，ARM的big·Little架构，也称作HMP（具体可参考“[Linux CPU core的电源管理(2)\_cpu topology](/pm_subsystem/cpu_topology.html)”中相关的介绍），通过在一个chip中封装两种不同类型的ARM core的方式，达到性能和功耗的平衡。这两类ARM Core，以cluster为单位，一类为高性能Core（即big core），一类为低性能Core（即Little core），通过它们的组合，可以满足不同应用场景下的性能和功耗要求，例如：非交互式的后台任务、或者流式多媒体的解码，可以使用低功耗的Little core处理；突发性的屏幕刷新，可以使用高性能的big core处理。

那么问题来了，Linux kernel怎么支持这种框架呢？

注1：本文很多理论性的表述，或多或少的理解并翻译自：“[http://lwn.net/Articles/481055/](http://lwn.net/Articles/481055/ "http://lwn.net/Articles/481055/")”，感兴趣的读者可以自行阅读。

注2：本文基于[linux-3.18-rc4](https://www.kernel.org/pub/linux/kernel/v3.x/testing/linux-3.18-rc4.tar.xz)内核，其它版本内核可能会稍有不同。

#### 2. Linux kernel支持ARM big·Lttile框架的思路

以一个包含两个cluster，cluster0有4个A15 core，cluster1有4个A7 core为例，我们会很自然的想到，可以把这8个core统统开放给kernel，让kernel的调度器（scheduler）根据系统的实际情况，决定哪些任务应该在哪些core上执行。但这存在一个问题：

> 当前linux kernel的scheduler，都是针对SMP系统设计的，而SMP系统中所有CPU core的性能和功耗都是相同的。

换句话说：kernel中还没有适用于big·Little架构的scheduler。怎么办？等待这样的一个scheduler出现？芯片厂商当然等不及，市场上已经出现了很多这种架构的芯片。为了应对这种软件滞后于硬件的现象（当前这种现象比比皆是，可能是硬件的成本比软件的人力成本低吧），ARM公司提出了这样一种软件解决方案（这只是ARM提出的解决方案的一种，后续我们介绍PSCI时，还会接触其它方案，这里就不再提及）：

> 使用一个hypervisor（可以参考“[ARMv8-a架构简介](/armv8a_arch/armv8-a_overview.html)”中有关hypervisor的介绍），利用虚拟化扩展，将8个A15+A7 core虚拟为4个A15 core，这样OS kernel就可以以SMP的方式，和这4个虚拟的core交互。当OS需要的时候，可以通过一个hypervisor指令，让某一个虚拟的core在A15和A7两种模式下切换，所有的切换动作，包括IRQ、timer等的迁移，都由hypervisor负责，对OS是透明的。

上面的方法有两个缺点：

> 1）这8个core不能任意的组合使用
>
> 2）必须存在hypervisor，会增加系统的复杂度

linux 借鉴了这个思路，将ARM hypervisor相关的实现逻辑，移植到kernel中，借助cpufreq framework，来实现上面的功能。之所以将hypervisor移植到kernel，是为了降低对ARM hypervisor code的耦合要求（解决上面的缺点2，当然，缺点1暂时无法解决）。而之所以使用cpufreq的框架，其中的思考如下：

> 1）抛开在big core和Little core之间切换的代价不谈，对scheduler来说，big core和Little core的区别仅仅在core的性能和功耗上，这恰恰和cpufreq framework的关注点一致：频率降低，性能降低，功耗降低；频率增大，性能增强，功耗增大。因此，可以将big、Little的切换，嵌入到CPU的频率调整中，低范围的频率段，对应Little core，高范围的频率段，对应big core。
>
> 2）对kernel scheduler而言，上面的8个core只有4个可见，这4个可见的core具有较宽的频率范围，并在big·Little switcher使能的情况下，根据频率需求的情况，自动在big和Little之间切换。
>
> 3）因此，使用cpufreq框架，巧妙的将不对称HMP架构，转化为了SMP架构，这样，kernel现有的scheduler就派上用场了。

#### 3. ARM big·Little driver的软件框架

基于上面的思考，linux kernel使用如下的软件框架实现ARM big·Little切换功能：

[![linux_arm_big_little](/content/uploadfile/201511/1f8e84ccbacfb1e0514b058fe7eb97e620151110140421.gif "linux_arm_big_little")](/content/uploadfile/201511/ab5b3f0dc3b533097f3c0e7766d2874620151110140410.gif)

arm big little cpufreq driver，位于drivers/cpufreq/目录中，负责和cpufreq framework对接，以CPU调频的形式，实现ARM big·Little的切换。

arm bL switcher，是一个arch-dependent的driver，提供实际的切换操作。

##### 3.1 arm big little cpufreq driver

arm big little cpufreq driver位于drivers/cpufreq目录下，由三个文件组成：

> arm\_big\_little.c   
> arm\_big\_little.h   
> arm\_big\_little\_dt.c

主要提供如下的功能（以本文参考的“[linux-3.18-rc4](https://www.kernel.org/pub/linux/kernel/v3.x/testing/linux-3.18-rc4.tar.xz)” kernel为准）：

1）支持A15和A7两个cluster。

2）当bL switching处于disable状态（bL switching的状态由arm bL switcher driver控制，3.2节会介绍）时，该driver就是一个普通的cpufreq driver，并为每个cluster提供一个frequency table（保存在freq\_table[0]、freq\_table[1]中）。

> 此时所有的big、Little core对系统都可见，每个core都可以基于cpufreq framework调整频率。

3）当bL switching处于enable状态时，该driver变成一个特殊的cpufreq driver，在调整频率的时候，可以根据情况，切换core的cluster。以第2章所描述的8个core为例：

> 此时只有4个虚拟的core对系统可见（由arm bL switcher driver控制，3.2节会介绍），系统不关心这些core属于哪个cluster、是big core还是Little core；
>
> 确切的说，每一个虚拟的core，代表了属于两个cluster的CPU对，可以想象为big+Little组合，只是同一时刻，只有一个core处于enable状态（big or Little）；
>
> 该driver会搜集2个cluster的frequency table，并合并成一个（保存在freq\_table[2]中）。合并后，找出这些frequency中big core最小的那个（clk\_big\_min）以及Little core最大的那个（clk\_little\_max）；
>
> 基于cpufreq framework进行频率调整时，如果所要求的频率小于clk\_big\_min，则将该虚拟core所对应的Little core使能，如果所要求得频率大于clk\_little\_max，则将该虚拟core所对应的big core使能。

4）基于上面的描述，ARM big·Little driver会把big·Little架构下的8个CPU core，以“big+Little”的形式组合成4对，同一时刻，每对组合的core只有一个处于运行状态，这就是Linux kernel ARM big·Little架构的核心思路。

##### 3.2 arm bL switcher driver

arm bL switcher driver是一个arch-dependent的driver，以ARM平台为例，其source code包括：

> arch/arm/common/bL\_switcher.c   
> arch/arm/common/bL\_switcher\_dummy\_if.c

该driver的功能如下：

1）提供bL switcher功能的enable和disable控制

2）通过sysfs，允许用户空间软件控制bL switcher的使能与否

接口文件位于：

> /sys/kernel/bL\_switcher/active

读取可以获取当前的使能情况，写1 enable，写0 disable。

3）为每个虚拟的CPU core（big+Little组合），创建一个线程，实现最终的cluster切换。该部分是平台相关的，后面将会以ARM平台为例介绍具体的过程。

#### 4. 代码分析

本章以ARM平台为例，结合kernel source code，从初始化以及cluster切换两个角度，介绍ARM big·Little driver的核心功能。

##### 4.1 初始化

和ARM big·Little driver有关的初始化过程主要分为三个部分：

> 1）CPU core的枚举和初始化，具体可参考“[Linux CPU core的电源管理(5)\_cpu control及cpu hotplug](/pm_subsystem/cpu_hotplug.html)”中有关possible CPU、present CPU的描述。
>
> 2）arm big little cpufreq driver的初始化，为每个cluster创建一个frequency table，并主持相应的cpufreq driver。
>
> 3）arm bL switcher driver，初始化bL switcher，并使能bL switcher。
>
> 下面我们重点介绍步骤2和步骤3。

###### 4.1.1 arm big little cpufreq driver的初始化

还是以包含两个cluster，每个cluster有4个CPU core（A15和A7）的系统为例，由“[Linux CPU core的电源管理(5)\_cpu control及cpu hotplug](/pm_subsystem/cpu_hotplug.html)”得描述可知，start\_kernel之后，系统的possible CPU包含所有的8个core。

然后arm big little cpufreq driver出场了，其init接口位于“drivers/cpufreq/arm\_big\_little\_dt.c”中，如下：

```
  1: static int generic_bL_probe(struct platform_device *pdev)
  2: {
  3:         struct device_node *np;
  4: 
  5:         np = get_cpu_node_with_valid_op(0);
  6:         if (!np)
  7:                 return -ENODEV;
  8: 
  9:         of_node_put(np);
 10:         return bL_cpufreq_register(&dt_bL_ops);
 11: }
 12: 
 13: static int generic_bL_remove(struct platform_device *pdev)
 14: {
 15:         bL_cpufreq_unregister(&dt_bL_ops);
 16:         return 0;
 17: }
 18: 
 19: static struct platform_driver generic_bL_platdrv = {
 20:         .driver = {
 21:                 .name   = "arm-bL-cpufreq-dt",
 22:                 .owner  = THIS_MODULE,
 23:         },
 24:         .probe          = generic_bL_probe,
 25:         .remove         = generic_bL_remove,
 26: };
 27: module_platform_driver(generic_bL_platdrv);
```

> kernel将arm big little cpufreq driver注册成了一个简单的platform driver，因此driver的入口就是其probe函数：generic\_bL\_probe。
>
> 注3：这里之所以把代码贴出，主要是看到“module\_platform\_driver”这个接口比较有趣。平时的经验，注册一个platform driver的固定格式是：定义一个platform driver变量，包含.probe()、.remove()等回调函数；定义两个函数，init和exit，在init函数中，调用platform\_driver\_register接口，注册该driver；使用module\_init和module\_exit声明init和exit函数。是不是很啰嗦？那就用这个接口吧，很省事！

1）generic\_bL\_probe

generic\_bL\_probe接口很简单，以dt\_bL\_ops为参数，调用bL\_cpufreq\_register接口，注册cpufreq driver。dt\_bL\_ops是一个struct cpufreq\_arm\_bL\_ops类型的变量，提供两个回调函数，分别用于获取cluster切换之间的延迟，以及初始化opp table，后面用到的时候再介绍。

2）bL\_cpufreq\_register

bL\_cpufreq\_register位于“drivers/cpufreq/arm\_big\_little.c”中，主要负责如下事情：

> a）执行一些初始化动作。
>
> b）调用cpufreq\_register\_driver接口，注册名称为bL\_cpufreq\_driver的cpufreq driver。有关cpufreq driver以及cpufreq\_register\_driver的描述可参考“[Linux cpufreq framework(2)\_cpufreq driver](/pm_subsystem/cpufreq_driver.html)”。
>
> c）调用arm bL switcher driver提供的bL\_switcher\_register\_notifier接口，向该driver注册一个notify，当bL switcher enable或者disable的时候，该driver会通知arm big little cpufreq driver，以完成相应的动作。

3）bL\_cpufreq\_driver

bL\_cpufreq\_driver代表了具体的cpufreq driver，提供了.init()、.verify()、.target\_index()等回调函数，如下：

```
  1: static struct cpufreq_driver bL_cpufreq_driver = {
  2:         .name                   = "arm-big-little",
  3:         .flags                  = CPUFREQ_STICKY |
  4:                                         CPUFREQ_HAVE_GOVERNOR_PER_POLICY |
  5:                                         CPUFREQ_NEED_INITIAL_FREQ_CHECK,
  6:         .verify                 = cpufreq_generic_frequency_table_verify,
  7:         .target_index           = bL_cpufreq_set_target,
  8:         .get                    = bL_cpufreq_get_rate,
  9:         .init                   = bL_cpufreq_init,
 10:         .exit                   = bL_cpufreq_exit,
 11:         .attr                   = cpufreq_generic_attr,
 12: };
```

有关cpufreq driver以及相关的回调函数已经在“[Linux cpufreq framework(2)\_cpufreq driver](/pm_subsystem/cpufreq_driver.html)”中有详细介绍，这里再稍作说明一下：

> .init()是cpufreq driver的入口函数，当该driver被注册到kernel中后，cpufreq core就会调用该回调函数，一般在init函数中初始化CPU core有关的frequency table，并依据该table填充相应的cpufreq policy变量。
>
> .verify()可用于校验某个频率是否有效。
>
> .target\_index()可将CPU core设置为某一个频率，在本文的场景中，可以在修改频率是进行cluster切换，后面会详细介绍。

4）bL\_cpufreq\_init

bL\_cpufreq\_driver被注册后，cpufreq core就会调用bL\_cpufreq\_init接口，完成后续的初始化任务，该接口比较重要，是arm big little cpufreq driver的精髓，其定义如下：

```
  1: /* Per-CPU initialization */
  2: static int bL_cpufreq_init(struct cpufreq_policy *policy)
  3: {
  4:         u32 cur_cluster = cpu_to_cluster(policy->cpu);
  5:         struct device *cpu_dev;
  6:         int ret;
  7: 
  8:         cpu_dev = get_cpu_device(policy->cpu);
  9:         if (!cpu_dev) {
 10:                 pr_err("%s: failed to get cpu%d device\n", __func__,
 11:                                 policy->cpu);
 12:                 return -ENODEV;
 13:         }
 14: 
 15:         ret = get_cluster_clk_and_freq_table(cpu_dev);
 16:         if (ret)
 17:                 return ret;
 18: 
 19:         ret = cpufreq_table_validate_and_show(policy, freq_table[cur_cluster]);
 20:         if (ret) {
 21:                 dev_err(cpu_dev, "CPU %d, cluster: %d invalid freq table\n",
 22:                                 policy->cpu, cur_cluster);
 23:                 put_cluster_clk_and_freq_table(cpu_dev);
 24:                 return ret;
 25:         }
 26: 
 27:         if (cur_cluster < MAX_CLUSTERS) {
 28:                 int cpu;
 29: 
 30:                 cpumask_copy(policy->cpus, topology_core_cpumask(policy->cpu));
 31: 
 32:                 for_each_cpu(cpu, policy->cpus)
 33:                         per_cpu(physical_cluster, cpu) = cur_cluster;
 34:         } else {
 35:                 /* Assumption: during init, we are always running on A15 */
 36:                 per_cpu(physical_cluster, policy->cpu) = A15_CLUSTER;
 37:         }
 38: 
 39:         if (arm_bL_ops->get_transition_latency)
 40:                 policy->cpuinfo.transition_latency =
 41:                         arm_bL_ops->get_transition_latency(cpu_dev);
 42:         else
 43:                 policy->cpuinfo.transition_latency = CPUFREQ_ETERNAL;
 44: 
 45:         if (is_bL_switching_enabled())
 46:                 per_cpu(cpu_last_req_freq, policy->cpu) = clk_get_cpu_rate(policy->cpu);
 47: 
 48:         dev_info(cpu_dev, "%s: CPU %d initialized\n", __func__, policy->cpu);
 49:         return 0;
 50: }
```

> 该接口根据当前bL switcher的使能情况（由cpu\_to\_cluster的返回值判断，如果等于MAX\_CLUSTERS，bL switcher处于enable状态，否则，为disable状态），有两种截然不同行为。
>
> bL switcher disable时（由于arm big little cpufreq driver先于arm bL switcher driver初始化，它初始化时，bL switcher处于disable状态）：
>
> - 15行，调用get\_cluster\_clk\_and\_freq\_table接口，为当前CPU所在的cluster创建frequency table，结果保存在freq\_table[cluster]中
> - 27~33行，将和当前cpu以及同属于一个cluster的所有其它CPU都保存在policy->cpus中（具体意义请参考““[Linux cpufreq framework(2)\_cpufreq driver](/pm_subsystem/cpufreq_driver.html)””），并将它们的physical\_cluster设置为当前CPU的cluster
> - 以上逻辑的背后思路是：如果bL switcher没有enable，arm big little cpufreq driver就是一个普通的cpufreq driver，此时每个cluster的所有CPU（如4个A15 core，或者4个A7 core），共享同一个frequency table、cpufreq policy，也就是说，一个cluster下的所有CPU core，共享同一个调频策略
>
> bL switcher enable时（会复杂一些）：
>
> - 15行，调用get\_cluster\_clk\_and\_freq\_table接口，搜集两个cluster下CPU的frequency信息，并以升序的形式合并到一个frequency table中（freq\_table[MAX\_CLUSTERS]），找出这些frequency中big core最小的那个（clk\_big\_min）以及Little core最大的那（clk\_little\_max）
> - 36行，将当前CPU的physical\_cluster变量设置为当前A15\_cluster，默认初始化时为big core模式
> - 以上逻辑背后的思路是：如果bL switcher enable，则所有的CPU core共用一个合并后的frequency table，并由一个调频策略统一调度，具体方法后面再详细介绍

bL\_cpufreq\_init的核心实现是get\_cluster\_clk\_and\_freq\_table接口，该接口会根据bL switcher的使能情况，初始化不同的frequency table，并在bL switcher enable的时候，将不同cluster的frequency合并到一起。具体代码就不再详细分析，这里强调一下里面的一个小技巧：

> 为了让bL switcher逻辑顺利执行，有必要尽量准确的区分big core和Little core的频率，get\_cluster\_clk\_and\_freq\_table使用了一个简单的方法：
>
> 对Little core来说，统一把frequency除以2，使用的时候再乘回来，这就基本上可以保证Little core的frequency位于合并后的频率表的前面位置，big core位于后面位置。

###### 4.1.2 arm bL switcher driver的初始化

以ARM平台为例，arm bL switcher driver的初始化接口是bL\_switcher\_init，由于它使用late\_init宏声明，因此会在靠后的时机初始化，该接口主要完成两个事情：

> 1）如果no\_bL\_switcher参数不为1（默认为0），则调用bL\_switcher\_enable接口，使能bL switcher。
>
> 2）调用bL\_switcher\_sysfs\_init接口，初始化bL switcher模块提供的sysfs API，具体可参考3.2章节的介绍。

因此，arm bL switcher driver的初始化，就转移到bL\_switcher\_enable上面了。

##### 4.2 enable/disable

bL switcher的使能与否，是由arm bL switcher driver控制的，以enable为例，enable的时机有两个：

> 1）arm bL switcher driver初始化的时候，调用bL\_switcher\_enable。
>
> 2）通过sysfs（/sys/kernel/bL\_switcher/active）使能

###### 4.2.1 bL\_switcher\_enable

bL\_switcher\_enable的实现如下：

```
  1: /* arch/arm/common/bL_switcher.c */
  2: static int bL_switcher_enable(void)
  3: {
  4:         int cpu, ret;
  5: 
  6:         mutex_lock(&bL_switcher_activation_lock);
  7:         lock_device_hotplug();
  8:         if (bL_switcher_active) {
  9:                 unlock_device_hotplug();
 10:                 mutex_unlock(&bL_switcher_activation_lock);
 11:                 return 0;
 12:         }
 13: 
 14:         pr_info("big.LITTLE switcher initializing\n");
 15: 
 16:         ret = bL_activation_notify(BL_NOTIFY_PRE_ENABLE);
 17:         if (ret)
 18:                 goto error;
 19: 
 20:         ret = bL_switcher_halve_cpus();
 21:         if (ret)
 22:                 goto error;
 23: 
 24:         bL_switcher_trace_trigger();
 25: 
 26:         for_each_online_cpu(cpu) {
 27:                 struct bL_thread *t = &bL_threads[cpu];
 28:                 spin_lock_init(&t->lock);
 29:                 init_waitqueue_head(&t->wq);
 30:                 init_completion(&t->started);
 31:                 t->wanted_cluster = -1;
 32:                 t->task = bL_switcher_thread_create(cpu, t);
 33:         }
 34: 
 35:         bL_switcher_active = 1;
 36:         bL_activation_notify(BL_NOTIFY_POST_ENABLE);
 37:         pr_info("big.LITTLE switcher initialized\n");
 38:         goto out;
 39: 
 40: error:
 41:         pr_warn("big.LITTLE switcher initialization failed\n");
 42:         bL_activation_notify(BL_NOTIFY_POST_DISABLE);
 43: 
 44: out:
 45:         unlock_device_hotplug();
 46:         mutex_unlock(&bL_switcher_activation_lock);
 47:         return ret;
 48: }
```

> 主要完成如下事情：
>
> 16行，调用bL\_activation\_notify，向arm big little cpufreq driver发送BL\_NOTIFY\_PRE\_ENABLE通知，cpufreq driver收到该通知后，会调用cpufreq\_unregister\_driver，将bL\_cpufreq\_driver注销（具体可参考drivers/cpufreq/arm\_big\_little.c中的bL\_cpufreq\_switcher\_notifier接口）。
>
> 20行，调用bL\_switcher\_halve\_cpus接口，将系统所有possible的CPU core配对，并关闭不需要的core。该接口是本文的精髓，后面会稍微详细的介绍。
>
> 26~33行，为每个处于online状态的CPU core（此处已经是虚拟的core了，该core是一个big/Little对，同一时刻只有一个core开启），初始化用于cluster switch的线程。
>
> 35~36行，将bL\_switcher\_active置1，此时bL switcher正式enable了，向arm big little cpufreq driver发送BL\_NOTIFY\_POST\_ENABLE通知，cpufreq driver会重新注册bL\_cpufreq\_driver。

###### 4.2.2 bL\_switcher\_halve\_cpus

bL\_switcher\_halve\_cpus是ARM big·Little driver灵魂式的存在，它负责把系统8个big+Little core转化成4个虚拟的CPU core，例如，这8个core是这样排布的（以cpu的逻辑ID为索引）：

|  |  |  |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 |
| Little | Little | Little | Little | big | big | big | big |

bL\_switcher\_halve\_cpus会将不同cluster的core组成一对，最终的结果保存在bL\_switcher\_cpu\_pairing数组中，形式如下：

> bL\_switcher\_cpu\_pairing[0] = 7
>
> bL\_switcher\_cpu\_pairing[1] = 6
>
> bL\_switcher\_cpu\_pairing[2] = 5
>
> bL\_switcher\_cpu\_pairing[3] = 4

配对之后，把core 4~7 disable掉，就保证系统当前只有4个虚拟的CPU core了。

###### 4.2.3 bL\_cpufreq\_switcher\_notifier

bL\_switcher\_enable前后，会通知arm big little cpufreq driver，该driver会把bL\_cpufreq\_driver注销之后再重新注册，整个过程又回到了“arm big little cpufreq driver的初始化”过程，具体可参考4.1.1。

##### 4.3 cluster切换

最后，我们来看一下big core和Little core到底是怎么切换的。切换是由arm big little cpufreq driver的bL\_cpufreq\_set\_target发起的，该接口的实现如下：

```
  1: static int bL_cpufreq_set_target(struct cpufreq_policy *policy,
  2:                 unsigned int index)
  3: {
  4:         u32 cpu = policy->cpu, cur_cluster, new_cluster, actual_cluster;
  5:         unsigned int freqs_new;
  6: 
  7:         cur_cluster = cpu_to_cluster(cpu);
  8:         new_cluster = actual_cluster = per_cpu(physical_cluster, cpu);
  9: 
 10:         freqs_new = freq_table[cur_cluster][index].frequency;
 11: 
 12:         if (is_bL_switching_enabled()) {
 13:                 if ((actual_cluster == A15_CLUSTER) &&
 14:                                 (freqs_new < clk_big_min)) {
 15:                         new_cluster = A7_CLUSTER;
 16:                 } else if ((actual_cluster == A7_CLUSTER) &&
 17:                                 (freqs_new > clk_little_max)) {
 18:                         new_cluster = A15_CLUSTER;
 19:                 }
 20:         }
 21: 
 22:         return bL_cpufreq_set_rate(cpu, actual_cluster, new_cluster, freqs_new);
 23: }
```

> 切换的要点包括：
>
> 1）由4.2.2的描述可知，在bL switcher处于enable状态时，对调度器而言，只有4个core可见，而且这4个core的logical map是不变的，例如都是0、1、2、3。每一个core在物理上和2个属于不同cluster的core对应，同一时刻只有一个物理core运行
>
> 2）这4个core所处的“状态”（哪个物理core处于运行状态，big or Little），记录在“physical\_cluster”中。
>
> 3）当经由cpufreq framework进行频率调整的时候，根据当前的“状态”，以及要调整的目的频率，计算是否需要切换cluster（也即disable当前正在运行的物理core，enable另外一个物理core）。
>
> 4）最终，以当前“状态”（actual\_cluster）、新“状态”（new\_cluster）等为参数，调用bL\_cpufreq\_set\_rate接口，设置频率。

bL\_cpufreq\_set\_rate接口经过一番处理后，得到真实的频率值，调用clock framework提供的接口（clk\_set\_rate）修改频率。之后，如果old\_cluster和new\_cluster不同，则调用arm bL switcher driver提供的bL\_switch\_request接口，进行cluster切换。该接口会启动一个线程，完成切换动作。该线程的处理函数是bL\_switcher\_thread，它会以目的cluster为参数，调用bL\_switch\_to接口，完成最终的切换操作。

bL\_switch\_to接口的实现比较复杂，需要迁移当前物理core的中断、timer，并disable当前物理core，然后enable目的cluster所代表的物理core，具体过程就不再详细分析了。

*原创文章，转发请注明出处。蜗窝科技*，[www.wowotech.net](/pm_subsystem/arm_big_little_driver.html)。
