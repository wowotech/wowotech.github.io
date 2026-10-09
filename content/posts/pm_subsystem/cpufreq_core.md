---
title: "linux cpufreq framework(3)_cpufreq core"
date: 2015-07-30T20:58:12+08:00
url: "/pm_subsystem/cpufreq_core.html"
gid: "202"
emlog_type: "blog"
summary: "前文（ Linux cpufreq framework(2)_cpufreq driver ）从平台驱动工程师的角度，简单的介绍了编写一个cpufreq driver的大概步骤。但要更深入理解、更灵活的使用，必须理解其内部的实现逻辑。 因此，本文将从cpufreq framework core的角度，对cpufreq framework的内部实现做一个简单的分析。"
author: "wowo"
category: "电源管理子系统"
category_alias: "pm_subsystem"
tags: ["Linux", "core", "cpufreq"]
views: 25357
comment_count: 10
aliases:
  - "/pm_subsystem/202.html"
  - "/202.html"
---

#### 1. 前言

前文（[Linux cpufreq framework(2)\_cpufreq driver](/pm_subsystem/cpufreq_driver.html)）从平台驱动工程师的角度，简单的介绍了编写一个cpufreq driver的大概步骤。但要更深入理解、更灵活的使用，必须理解其内部的实现逻辑。

因此，本文将从cpufreq framework core的角度，对cpufreq framework的内部实现做一个简单的分析。

#### 2. 提供给用户空间的接口

cpufreq core的内部实现，比较繁杂，因此我们需要一个分析的突破口，而cpufreq framework提供的API是一个不错的选择。因为API抽象了cpufreq的功能，而所有的cpufreq core、cpufreq driver等模块，都是为这些功能服务的。

由“[linux cpufreq framework(1)\_概述](/pm_subsystem/cpufreq_overview.html)”的介绍可知，cpufreq framework通过sysfs向用户空间提供接口，具体如下：

> /sys/devices/system/cpu/cpu0/cpufreq/   
> |-- affected\_cpus   
> |-- cpuinfo\_cur\_freq   
> |-- cpuinfo\_max\_freq   
> |-- cpuinfo\_min\_freq   
> |-- cpuinfo\_transition\_latency   
> |-- related\_cpus   
> |-- scaling\_available\_frequencies   
> |-- scaling\_available\_governors   
> |-- scaling\_cur\_freq   
> |-- scaling\_driver   
> |-- scaling\_governor   
> |-- scaling\_max\_freq   
> |-- scaling\_min\_freq   
> |-- scaling\_setspeed   
> `—stats   
>  |-- time\_in\_state   
>  |-- total\_trans   
>  `-- trans\_table

1）“cpufreq”目录

在kernel的模型中，cpufreq被抽象为cpu device的一个interface，因此它位于对应的cpu目录（/sys/devices/system/cpu/cpuX）下面。

有些平台，所有cpu core的频率和电压时统一控制的，即改变某个core上的频率，其它core同样受影响。此时只需要实现其中一个core（通常为cpu0）的cpufreq即可，其它core的cpufreq直接是cpu0的符号链接。因此，使用这些API时，随便进入某一个cpu下面的cpufreq目录即可。

而另一些些平台，不同core可以单独控制，这时不同cpu目录下的cpufreq就不一样了。

到底某一个cpufreq可以控制多少cpu core呢？可以通过cpufreq/affected\_cpus和cpufreq/related\_cpus两个文件查看，其中的区别是：affected\_cpus表示该cpufreq影响到哪些cpu core（没有显示处于offline状态的cpu），related\_cpus则包括了online+offline的所有core。

2）cpuinfo相关的信息

由“[Linux cpufreq framework(2)\_cpufreq driver](/pm_subsystem/cpufreq_driver.html)”的描述可知，cpufreq driver初始化时，会根据frequency table等信息，填充struct cpufreq\_policy变量中的struct cpufreq\_cpuinfo变量，该变量保存了CPU调频有关的固定信息（不可以在运行过程中修改，主要包括：最大频率（cpuinfo\_max\_freq）、最小频率（cpuinfo\_min\_freq）、频率转换延迟（cpuinfo\_transition\_latency ）。

另外，通过cpuinfo\_cur\_freq ，可以获取cpu core的当前频率（真实的、cpu的当前运行频率，会通过cpufreq\_driver->get回调读取）。

当前，这四个“cpuinfo\_”开头的sysfs API，都是只读的。

3）scaling\_available\_frequencies，获取当前可以配置的频率列表，从frequency table直接读取。readonly。

4） scaling\_driver，当前加载的cpufreq driver名称，readonly。

5）scaling\_available\_governors和scaling\_governor，系统中可用的governor列表，以及当前使用的governor。governor相关的内容会在后续详细描述。readonly。

6）scaling\_cur\_freq，从cpufreq core或者governor的角度，看到的当前频率，和cpuinfo\_cur\_freq的意义不相同，后面的分析中根据实例在描述。readonly。

7）scaling\_max\_freq、scaling\_min\_freq和scaling\_setspeed

scaling\_max\_freq和scaling\_min\_freq表示调频策略所允许的最大和最小频率，对于可以自动调整频率的cpu，修改它们，就是最终的频率调整。

对不能自动调整频率的cpu，则需要通过其它方式，主动的设置cpu频率，这些都是由具体的governor完成。其中有一个特例：

如果使用的governor是“userspace” governor，则可以通过scaling\_setspeed节点，直接修改cpu频率。

#### 3. 频率调整的步骤

开始分析之前，我们先以“userspace” governor为例，介绍一下频率调整的步骤。“userspace”governor是所有governor中最简单的一个，同时又是驱动工程师比较常用的一个，借助它，可以从用户空间修改cpu的频率，操作方法如下（为了简单，以shell脚本的形式给出）：

> cd /sys/devices/system/cpu/cpu0/cpufreq/
>
> cat cpuinfo\_max\_freq; cat cpuinfo\_min\_freq            #获取“物理”上的频率范围
>
> cat scaling\_available\_frequencies #获取可用的频率列表   
> cat scaling\_available\_governors #获取可用的governors   
> cat scaling\_governor #当前的governor   
> cat cpuinfo\_cur\_freq; cat scaling\_cur\_freq #获取当前的频率信息，可以比较一下是否不同
>
> cat scaling\_max\_freq; cat scaling\_min\_freq #获取当前调频策略所限定的频率范围
>
> #假设CPU不可以自动调整频率   
> echo userspace > scaling\_governor #governor切换为userspace
>
> #如果需要切换的频率值在scaling\_available\_frequencies内，且在cpuinfo\_max\_freq/cpuinfo\_min\_freq的范围内。
>
> #如果需要切换的频率不在scaling\_max\_freq/scaling\_min\_freq的范围内，修改这两个值   
> echo xxx > scaling\_max\_freq; echo xxx > scaling\_min\_freq
>
> #最后，设置频率值   
> echo xxx > scaling\_setspeed

#### 4. 内部逻辑分析

**4.1 初始化**

基于linux设备模型的思想，kernel会使用device和driver两个实体，抽象设备及其驱动，当这两个实体同时存在时，则执行driver的初始化接口（即driver开始运行）。cpufreq也不例外，基本遵循了上面的思路。但由于cpufreq是一类比较特殊的设备（它只是cpu device的一个功能，本身并不以任何形式存在），在实现上，就有点迂回。

首先，driver的抽象比较容易理解，就是我们在“[Linux cpufreq framework(2)\_cpufreq driver](/pm_subsystem/cpufreq_driver.html)”中描述的struct cpufreq\_driver结构。那device呢？先看看下面的图片：

注1：该图片不包括CPU hotplug的情况，hotplug时，会走两外一个流程，大概原理类似，本文就不详细介绍这种情况了。

[![cpufreq init flow](/content/uploadfile/201507/0de6805816b4e770c67f13c65b26134220150730125809.gif "cpufreq init flow")](/content/uploadfile/201507/b4fe5ff46aa4f9c3ec019dbc7c3538a120150730125808.gif)1）cpufreq\_interface

前面讲过，cpufreq driver注册时，会调用subsys\_interface\_register接口，注册一个subsystem interface，该interface的定义如下：

```
  1: /* drivers/cpufreq/cpufreq.c */
  2: static struct subsys_interface cpufreq_interface = {
  3: 	.name		= "cpufreq",
  4: 	.subsys		= &cpu_subsys,
  5: 	.add_dev	= cpufreq_add_dev,
  6: 	.remove_dev	= cpufreq_remove_dev,
  7: };
```

> 该interface的subsys是“cpu\_subsys”，就是cpu bus（struct bus\_type cpu\_subsys），提供了add\_dev和remove\_dev两个回调函数。

由“[Linux设备模型(6)\_Bus](/device_model/bus.html)”中的描述可知，当bus下有设备probe的时候（此处为cpu device的probe），会调用其下所有interface的add\_dev回调函数。物理意义是什么呢？

> cpufreq是cpu device的一个功能，当cpu device开始枚举时，当然要创建代表该功能（cpufreq）的设备。而这个设备的具体形态，只有该功能相关的代码（cpufreq core）知道，因此就只能交给它了。

2）\_\_cpufreq\_add\_dev

由上面图片所示的流程可知，cpufreq设备的添加，最终是由\_\_cpufreq\_add\_dev接口完成的，该接口的主要功能，是创建一个代表该cpufreq的设备（struct cpufreq\_policy类型的变量），并以它为参数，调用cpufreq\_driver的init接口（可参考“[Linux cpufreq framework(2)\_cpufreq driver](/pm_subsystem/cpufreq_driver.html)”），对它进行初始化。如下：

```
  1: static int __cpufreq_add_dev(struct device *dev, struct subsys_interface *sif)
  2: {
  3: 	unsigned int j, cpu = dev->id;
  4: 	int ret = -ENOMEM;
  5: 	struct cpufreq_policy *policy;
  6: 	unsigned long flags;
  7: 	bool recover_policy = cpufreq_suspended;
  8: #ifdef CONFIG_HOTPLUG_CPU
  9: 	struct cpufreq_policy *tpolicy;
 10: #endif
 11: 
 12: 	if (cpu_is_offline(cpu))
 13: 		return 0;
 14: 
 15: 	pr_debug("adding CPU %u\n", cpu);
 16: 
 17: #ifdef CONFIG_SMP
 18: 	/* check whether a different CPU already registered this
 19: 	 * CPU because it is in the same boat. */
 20: 	policy = cpufreq_cpu_get(cpu);
 21: 	if (unlikely(policy)) {
 22: 		cpufreq_cpu_put(policy);
 23: 		return 0;
 24: 	}
 25: #endif
 26: 
 27: 	if (!down_read_trylock(&cpufreq_rwsem))
 28: 		return 0;
 29: 
 30: #ifdef CONFIG_HOTPLUG_CPU
 31: 	/* Check if this cpu was hot-unplugged earlier and has siblings */
 32: 	read_lock_irqsave(&cpufreq_driver_lock, flags);
 33: 	list_for_each_entry(tpolicy, &cpufreq_policy_list, policy_list) {
 34: 		if (cpumask_test_cpu(cpu, tpolicy->related_cpus)) {
 35: 			read_unlock_irqrestore(&cpufreq_driver_lock, flags);
 36: 			ret = cpufreq_add_policy_cpu(tpolicy, cpu, dev);
 37: 			up_read(&cpufreq_rwsem);
 38: 			return ret;
 39: 		}
 40: 	}
 41: 	read_unlock_irqrestore(&cpufreq_driver_lock, flags);
 42: #endif
 43: 
 44: 	/*
 45: 	 * Restore the saved policy when doing light-weight init and fall back
 46: 	 * to the full init if that fails.
 47: 	 */
 48: 	policy = recover_policy ? cpufreq_policy_restore(cpu) : NULL;
 49: 	if (!policy) {
 50: 		recover_policy = false;
 51: 		policy = cpufreq_policy_alloc();
 52: 		if (!policy)
 53: 			goto nomem_out;
 54: 	}
 55: 
 56: 	/*
 57: 	 * In the resume path, since we restore a saved policy, the assignment
 58: 	 * to policy->cpu is like an update of the existing policy, rather than
 59: 	 * the creation of a brand new one. So we need to perform this update
 60: 	 * by invoking update_policy_cpu().
 61: 	 */
 62: 	if (recover_policy && cpu != policy->cpu)
 63: 		WARN_ON(update_policy_cpu(policy, cpu, dev));
 64: 	else
 65: 		policy->cpu = cpu;
 66: 
 67: 	cpumask_copy(policy->cpus, cpumask_of(cpu));
 68: 
 69: 	init_completion(&policy->kobj_unregister);
 70: 	INIT_WORK(&policy->update, handle_update);
 71: 
 72: 	/* call driver. From then on the cpufreq must be able
 73: 	 * to accept all calls to ->verify and ->setpolicy for this CPU
 74: 	 */
 75: 	ret = cpufreq_driver->init(policy);
 76: 	if (ret) {
 77: 		pr_debug("initialization failed\n");
 78: 		goto err_set_policy_cpu;
 79: 	}
 80: 
 81: 	/* related cpus should atleast have policy->cpus */
 82: 	cpumask_or(policy->related_cpus, policy->related_cpus, policy->cpus);
 83: 
 84: 	/*
 85: 	 * affected cpus must always be the one, which are online. We aren't
 86: 	 * managing offline cpus here.
 87: 	 */
 88: 	cpumask_and(policy->cpus, policy->cpus, cpu_online_mask);
 89: 
 90: 	if (!recover_policy) {
 91: 		policy->user_policy.min = policy->min;
 92: 		policy->user_policy.max = policy->max;
 93: 	}
 94: 
 95: 	down_write(&policy->rwsem);
 96: 	write_lock_irqsave(&cpufreq_driver_lock, flags);
 97: 	for_each_cpu(j, policy->cpus)
 98: 		per_cpu(cpufreq_cpu_data, j) = policy;
 99: 	write_unlock_irqrestore(&cpufreq_driver_lock, flags);
100: 
101: 	if (cpufreq_driver->get && !cpufreq_driver->setpolicy) {
102: 		policy->cur = cpufreq_driver->get(policy->cpu);
103: 		if (!policy->cur) {
104: 			pr_err("%s: ->get() failed\n", __func__);
105: 			goto err_get_freq;
106: 		}
107: 	}
108: 
109: 	/*
110: 	 * Sometimes boot loaders set CPU frequency to a value outside of
111: 	 * frequency table present with cpufreq core. In such cases CPU might be
112: 	 * unstable if it has to run on that frequency for long duration of time
113: 	 * and so its better to set it to a frequency which is specified in
114: 	 * freq-table. This also makes cpufreq stats inconsistent as
115: 	 * cpufreq-stats would fail to register because current frequency of CPU
116: 	 * isn't found in freq-table.
117: 	 *
118: 	 * Because we don't want this change to effect boot process badly, we go
119: 	 * for the next freq which is >= policy->cur ('cur' must be set by now,
120: 	 * otherwise we will end up setting freq to lowest of the table as 'cur'
121: 	 * is initialized to zero).
122: 	 *
123: 	 * We are passing target-freq as "policy->cur - 1" otherwise
124: 	 * __cpufreq_driver_target() would simply fail, as policy->cur will be
125: 	 * equal to target-freq.
126: 	 */
127: 	if ((cpufreq_driver->flags & CPUFREQ_NEED_INITIAL_FREQ_CHECK)
128: 	    && has_target()) {
129: 		/* Are we running at unknown frequency ? */
130: 		ret = cpufreq_frequency_table_get_index(policy, policy->cur);
131: 		if (ret == -EINVAL) {
132: 			/* Warn user and fix it */
133: 			pr_warn("%s: CPU%d: Running at unlisted freq: %u KHz\n",
134: 				__func__, policy->cpu, policy->cur);
135: 			ret = __cpufreq_driver_target(policy, policy->cur - 1,
136: 				CPUFREQ_RELATION_L);
137: 
138: 			/*
139: 			 * Reaching here after boot in a few seconds may not
140: 			 * mean that system will remain stable at "unknown"
141: 			 * frequency for longer duration. Hence, a BUG_ON().
142: 			 */
143: 			BUG_ON(ret);
144: 			pr_warn("%s: CPU%d: Unlisted initial frequency changed to: %u KHz\n",
145: 				__func__, policy->cpu, policy->cur);
146: 		}
147: 	}
148: 
149: 	blocking_notifier_call_chain(&cpufreq_policy_notifier_list,
150: 				     CPUFREQ_START, policy);
151: 
152: 	if (!recover_policy) {
153: 		ret = cpufreq_add_dev_interface(policy, dev);
154: 		if (ret)
155: 			goto err_out_unregister;
156: 		blocking_notifier_call_chain(&cpufreq_policy_notifier_list,
157: 				CPUFREQ_CREATE_POLICY, policy);
158: 	}
159: 
160: 	write_lock_irqsave(&cpufreq_driver_lock, flags);
161: 	list_add(&policy->policy_list, &cpufreq_policy_list);
162: 	write_unlock_irqrestore(&cpufreq_driver_lock, flags);
163: 
164: 	cpufreq_init_policy(policy);
165: 
166: 	if (!recover_policy) {
167: 		policy->user_policy.policy = policy->policy;
168: 		policy->user_policy.governor = policy->governor;
169: 	}
170: 	up_write(&policy->rwsem);
171: 
172: 	kobject_uevent(&policy->kobj, KOBJ_ADD);
173: 	up_read(&cpufreq_rwsem);
174: 
175: 	pr_debug("initialization complete\n");
176: 
177: 	return 0;
178: 
179: err_out_unregister:
180: err_get_freq:
181: 	write_lock_irqsave(&cpufreq_driver_lock, flags);
182: 	for_each_cpu(j, policy->cpus)
183: 		per_cpu(cpufreq_cpu_data, j) = NULL;
184: 	write_unlock_irqrestore(&cpufreq_driver_lock, flags);
185: 
186: 	up_write(&policy->rwsem);
187: 
188: 	if (cpufreq_driver->exit)
189: 		cpufreq_driver->exit(policy);
190: err_set_policy_cpu:
191: 	if (recover_policy) {
192: 		/* Do not leave stale fallback data behind. */
193: 		per_cpu(cpufreq_cpu_data_fallback, cpu) = NULL;
194: 		cpufreq_policy_put_kobj(policy);
195: 	}
196: 	cpufreq_policy_free(policy);
197: 
198: nomem_out:
199: 	up_read(&cpufreq_rwsem);
200: 
201: 	return ret;
202: }
```

> 12~13行：如果cpu处于offline状态，则直接返回。
>
> 17~25行：对于SMP系统，可能存在所有的CPU core，使用相同的cpufreq policy的情况。此时，当primary CPU枚举时，调用\_\_cpufreq\_add\_dev接口创建cpufreq policy时，会同时将该policy提供给其它CPU使用。当其他CPU枚举时，它需要判断是否已经有人代劳了，如果有，则直接返回。这就是这几行代码的逻辑。
>
> 30~40行：这几行是处理具有hotplug功能的CPU的。有前面的逻辑可知，如果系统中多个CPU共用一个cpufreq policy，primary CPU在枚举时，会帮忙添加其它CPU的cpufreq policy。但这有一个条件：它只帮忙处理那些处于online状态的CPU，而那些offline状态的CPU，则需要在online的时候，自行判断，并将自身的cpufreq policy添加到系统。
>
> 注2：有关上面的两段实现，后面会专门用一个章节介绍。
>
> 44~54行：分配cpufreq policy。根据是否是suspend & resume的过程，会有不同的处理方式，我们先不去纠结这些细节。
>
> 55~65行：将当前cpu保存在policy的cpu字段。
>
> 67行：初始化policy->cpus变量，由“[Linux cpufreq framework(2)\_cpufreq driver](/pm_subsystem/cpufreq_driver.html)”可知，该变量是一个cpumask类型的变量，记录该policy可以控制哪些online的cpu（毫无疑问，至少会包含当前的cpu）。
>
> 75行：调用driver的init接口，相当于设备模型中的driver probe。此时cpufreq deice（policy）和cpufreq driver已经成功会和，driver开始执行。具体行为，请参考“[Linux cpufreq framework(2)\_cpufreq driver](/pm_subsystem/cpufreq_driver.html)”。
>
> 82行：初始化policy->related\_cpus，至少包含所有的online CPUs（policy->cpus，由cpufreq\_driver->init初始化）。
>
> 88行：根据当前CPU online状态，将policy->cpus中处于offline状态的CPU剔除。
>
> 97~98行：初始化所有其它共用cpufreq policy的、处于online状态的CPU（policy->cpus）的cpufreq\_cpu\_data变量，表明它们也都已经有了cpufreq policy（回到17~25行的逻辑，其中的判断，就是依据该变量）。
>
> 109~147行：如果cpufreq driver定义了CPUFREQ\_NEED\_INITIAL\_FREQ\_CHECK flag，则要求cpufreq core在启动时检查当前频率（policy->cur）是否在frequency table范围内，如果不在，调用\_\_cpufreq\_driver\_target重新设置频率。
>
> 152~158行：对于不是suspend&resume的场景，调用cpufreq\_add\_dev\_interface接口，在该cpu的目录下，创建cpufreq的sysfs目录，以及相应的attribute文件（可参考本文第2章的内容），并为其它共用policy的、处于online状态的cpu，创建指向该cpufreq目录的符号链接。
>
> 161行：将新创建的policy，挂到一个全局链表中（cpufreq\_policy\_list）。
>
> 164行：调用cpufreq\_init\_policy，为该policy分配一个governor，并调用cpufreq\_set\_policy接口，为该cpu设置一个默认的cpufreq policy。这一段的逻辑有点纠结，我们后面再细讲。
>
> 166~-169：更新policy->user\_policy，后面再细讲。

3）SMP、Hotplug等场景下，多个CPU共用cpufreq policy的情况总结

前面多次提到，在SMP系统中，多个CPU core可能会由相同的调频机制（其实大多数平台都是这样的）控制，也就是说，所有CPU core的频率和电压，是同时调节的。这种情况下，只需要创建一个cpufreq policy即可，涉及到的代码逻辑包括：

> a）primary CPU枚举时，\_\_cpufreq\_add\_dev会调用cpufreq driver的init接口（cpufreq\_driver->init），driver需要根据当前的系统情况，设置policy->cpus，告诉cpufreq core哪些CPU共用同一个cpufreq policy。
>
> b）primary CPU的\_\_cpufreq\_add\_dev继续执行，初始化policy->related\_cpus，并将policy->cpus中处于offline状态的CPU剔除。具体可参考上面的代码分析。
>
> c）primary CPU的\_\_cpufreq\_add\_dev继续执行，创建sysfs接口，同时为policy->cpus中的其它CPU创建相应的符号链接。
>
> d）secondary CPUs枚举，执行\_\_cpufreq\_add\_dev，判断primary CPU已经代劳之后，直接退出。
>
> e）对于hotplugable的CPU，hotplug in时，由于primary CPU没有帮忙创建sysfs的符号链接，或者hotplug out的时候符号链接被删除，因此需要重新创建。

4.2 频率调整

cpufreq framework的频率调整逻辑，总结如下：

> 通过调整policy（struct cpufreq\_policy），确定CPU频率调整的一个大方向，主要是由min\_freq和max\_freq组成的频率范围；
>
> 通过cpufreq governor，确定最终的频率值。
>
> 下面结合代码，做进一步的阐述。

1）cpufreq\_set\_policy

cpufreq\_set\_policy用来设置一个新的cpufreq policy，调用的时机包括：

> a）初始化时（\_\_cpufreq\_add\_dev->cpufreq\_init\_policy->cpufreq\_set\_policy），将cpufreq\_driver->init时提供的基础policy，设置生效。
>
> b）修改scaling\_max\_freq或scaling\_min\_freq时（store\_one->cpufreq\_set\_policy），将用户空间设置的新的频率范围，设置生效。
>
> c）修改cpufreq governor时（scaling\_governor->store\_scaling\_governor->cpufreq\_set\_policy），更新governor。

来看一下cpufreq\_set\_policy都做了什么事情。

```
  1: static int cpufreq_set_policy(struct cpufreq_policy *policy,
  2: 				struct cpufreq_policy *new_policy)
  3: {
  4: 	struct cpufreq_governor *old_gov;
  5: 	int ret;
  6: 
  7: 	pr_debug("setting new policy for CPU %u: %u - %u kHz\n",
  8: 		 new_policy->cpu, new_policy->min, new_policy->max);
  9: 
 10: 	memcpy(&new_policy->cpuinfo, &policy->cpuinfo, sizeof(policy->cpuinfo));
 11: 
 12: 	if (new_policy->min > policy->max || new_policy->max < policy->min)
 13: 		return -EINVAL;
 14: 
 15: 	/* verify the cpu speed can be set within this limit */
 16: 	ret = cpufreq_driver->verify(new_policy);
 17: 	if (ret)
 18: 		return ret;
 19: 
 20: 	/* adjust if necessary - all reasons */
 21: 	blocking_notifier_call_chain(&cpufreq_policy_notifier_list,
 22: 			CPUFREQ_ADJUST, new_policy);
 23: 
 24: 	/* adjust if necessary - hardware incompatibility*/
 25: 	blocking_notifier_call_chain(&cpufreq_policy_notifier_list,
 26: 			CPUFREQ_INCOMPATIBLE, new_policy);
 27: 
 28: 	/*
 29: 	 * verify the cpu speed can be set within this limit, which might be
 30: 	 * different to the first one
 31: 	 */
 32: 	ret = cpufreq_driver->verify(new_policy);
 33: 	if (ret)
 34: 		return ret;
 35: 
 36: 	/* notification of the new policy */
 37: 	blocking_notifier_call_chain(&cpufreq_policy_notifier_list,
 38: 			CPUFREQ_NOTIFY, new_policy);
 39: 
 40: 	policy->min = new_policy->min;
 41: 	policy->max = new_policy->max;
 42: 
 43: 	pr_debug("new min and max freqs are %u - %u kHz\n",
 44: 		 policy->min, policy->max);
 45: 
 46: 	if (cpufreq_driver->setpolicy) {
 47: 		policy->policy = new_policy->policy;
 48: 		pr_debug("setting range\n");
 49: 		return cpufreq_driver->setpolicy(new_policy);
 50: 	}
 51: 
 52: 	if (new_policy->governor == policy->governor)
 53: 		goto out;
 54: 
 55: 	pr_debug("governor switch\n");
 56: 
 57: 	/* save old, working values */
 58: 	old_gov = policy->governor;
 59: 	/* end old governor */
 60: 	if (old_gov) {
 61: 		__cpufreq_governor(policy, CPUFREQ_GOV_STOP);
 62: 		up_write(&policy->rwsem);
 63: 		__cpufreq_governor(policy, CPUFREQ_GOV_POLICY_EXIT);
 64: 		down_write(&policy->rwsem);
 65: 	}
 66: 
 67: 	/* start new governor */
 68: 	policy->governor = new_policy->governor;
 69: 	if (!__cpufreq_governor(policy, CPUFREQ_GOV_POLICY_INIT)) {
 70: 		if (!__cpufreq_governor(policy, CPUFREQ_GOV_START))
 71: 			goto out;
 72: 
 73: 		up_write(&policy->rwsem);
 74: 		__cpufreq_governor(policy, CPUFREQ_GOV_POLICY_EXIT);
 75: 		down_write(&policy->rwsem);
 76: 	}
 77: 
 78: 	/* new governor failed, so re-start old one */
 79: 	pr_debug("starting governor %s failed\n", policy->governor->name);
 80: 	if (old_gov) {
 81: 		policy->governor = old_gov;
 82: 		__cpufreq_governor(policy, CPUFREQ_GOV_POLICY_INIT);
 83: 		__cpufreq_governor(policy, CPUFREQ_GOV_START);
 84: 	}
 85: 
 86: 	return -EINVAL;
 87: 
 88:  out:
 89: 	pr_debug("governor: change or update limits\n");
 90: 	return __cpufreq_governor(policy, CPUFREQ_GOV_LIMITS);
 91: }
```

> 15~18行：调用driver的verify接口，判断新的policy是否有效。
>
> 20~26行：notifier接口用于policy的调整，如果有其它模块对新的policy不满意，可以通过这样的机制修正，具体不再描述，感兴趣的读者可以自行研究。
>
> 28~34行：修正后，再交给driver进行verify。
>
> 46~50行：如果driver提供了setpolicy回调（回忆一下“[Linux cpufreq framework(2)\_cpufreq driver](/pm_subsystem/cpufreq_driver.html)”），则说明硬件有能力根据policy所指定的范围，自行调节频率，其它机制就不需要了，调用该回调，将新的policy配置给硬件后，退出。
>
> 否则（后面的代码），则需要由governor执行具体的频率调整动作，调用governor的接口，切换governor。有关cpufreq governor的描述，请参考下一篇文章。

2）scaling\_setspeed

上面提到了，policy只规定了频率调整的一个范围，如果driver不支持setpolicy操作，则需要由cpufreq governor确定具体的频率值，并调用driver的target或者target\_index接口，修改CPU的频率值。

有关cpufreq governor的介绍，请参考后续的文章（“linux cpufreq framework(4)\_cpufreq governor”）。不过这其中有一个例外，就是当governor为“userspace”时（参考第3章的描述），可以直接通过scaling\_setspeed文件，从用户空间修改频率值，代码如下：

```
  1: static ssize_t store_scaling_setspeed(struct cpufreq_policy *policy,
  2:                                         const char *buf, size_t count)
  3: {
  4:         unsigned int freq = 0;
  5:         unsigned int ret;
  6: 
  7:         if (!policy->governor || !policy->governor->store_setspeed)
  8:                 return -EINVAL;
  9: 
 10:         ret = sscanf(buf, "%u", &freq);
 11:         if (ret != 1)
 12:                 return -EINVAL;
 13: 
 14:         policy->governor->store_setspeed(policy, freq);
 15: 
 16:         return count;
 17: }
```

> 由此可以猜到，“userspace” governor具有store\_setspeed函数，该函数应该可以直接修改频率值。留到（“linux cpufreq framework(4)\_cpufreq governor”）再欣赏吧。

*原创文章，转发请注明出处。蜗窝科技*，[www.wowotech.net](/pm_subsystem/cpufreq_core.html)。
