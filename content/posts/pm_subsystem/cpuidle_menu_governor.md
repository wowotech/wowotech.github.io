---
title: "Linux cpuidle framework(4)_menu governor"
date: 2015-01-18T23:14:50+08:00
url: "/pm_subsystem/cpuidle_menu_governor.html"
gid: "139"
emlog_type: "blog"
summary: "本文以menu governor为例，进一步理解cpuidle framework中governor的概念，并学习governor的实现方法。 在当前的kernel中，有2个governor，分别为ladder和menu（蜗蜗试图理解和查找，为什么会叫这两个名字，暂时还没有答案）。ladder在periodic timer tick system中使用，menu在tickless system中使"
author: "wowo"
category: "电源管理子系统"
category_alias: "pm_subsystem"
tags: ["Linux", "cpuidle", "menu", "governor", "pm_qos"]
views: 26253
comment_count: 22
aliases:
  - "/pm_subsystem/139.html"
  - "/139.html"
---

#### 1. 前言

本文以menu governor为例，进一步理解cpuidle framework中governor的概念，并学习governor的实现方法。

在当前的kernel中，有2个governor，分别为ladder和menu（蜗蜗试图理解和查找，为什么会叫这两个名字，暂时还没有答案）。ladder在periodic timer tick system中使用，menu在tickless system中使用。

现在主流的系统，出于电源管理的考量，大多都是tickless system。另外，menu governor会利用pm qos framework（蜗蜗会在后续的文章中分析），在选择策略中加入延迟容忍度（Latency tolerance）的考量。因此本文选取menu governor作为分析对象，至于ladder，就不再分析了。

注：有关periodic timer tick和tickless的知识，可参考本站[**时间子系统**](/sort/timer_subsystem)的系列文章。

#### 2. 背后的思考

本节的内容，主要来源于drivers/cpuidle/governors/menu.c中的注释。

governor的主要职责，是根据系统的运行情况，选择一个合适idle state（在kernel的标准术语中，也称作C state）。具体的算法，需要基于下面两点考虑：

1）切换的代价

> 进入C state的目的，是节省功耗，但CPU在C state和normal state之间切换，是要付出功耗上面的代价的。这最终会体现在idle state的target\_residency字段上。
>
> idle driver在注册idle state时，要非常明确state切换的代价，基于该代价，CPU必须在idle state中停留超过一定的时间（target\_residency）才是划算的。
>
> 因此governor在选择C state时，需要预测出CPU将要在C state中的停留时间，并和备选idle state的target\_residency字段比较，选取满足“停留时间 > target\_residency”的state。

2）系统的延迟容忍程度

> 备选的的C state中，功耗和退出延迟是一对不可调和的矛盾，电源管理的目标，是在保证延迟在系统可接受的范围内的情况下，尽可能的节省功耗。
>
> idle driver在注册idle state时，会提供两个信息：CPU在某个state下的功耗（power\_usage）和退出该state的延迟（exit\_latency）。那么如果知道系统当前所能容忍的延迟（简称latency\_req），就可以在所有exit\_latency小于latency\_req的state中，选取功耗最小的那个。
>
> 因此，governor算法就转换为获取系统当前的latency\_req，而这正是pm qos的特长。

基于上面的考量，menu governor的主要任务就转化为两个：1. 根据系统的运行情况，预测CPU将在C state中停留的时间（简称predicted\_us）；2. 借助pm qos framework，获取系统当前的延迟容忍度（简称latency\_req）。

任务1，menu governor从如下几个方面去达成：

> 前面讲过，menu governor用于tickless system，简化处理，menu将“距离下一个tick来临的时间（由next timer event测量，简称next\_timer\_us）”作为基础的predicted\_us。
>
> 当然，这个基础的predicted\_us是不准确的，因为在这段时间内，随时都可能产生除next timer event之外的其它wakeup event。为了使预测更准确，有必要加入一个校正因子（correction factor），该校正因子基于过去的实际predicted\_us和next\_timer\_us之间的比率，例如，如果wakeup event都是在预测的next timer event时间的一半时产生，则factor为0.5。另外，为了更精确，menu使用动态平均的factor。
>
> 另外，对不同范围的next\_timer\_us，correction factor的影响程度是不一样的。例如期望50ms和500ms的next timer event时，都是在10ms时产生了wakeup event，显然对500ms的影响比较大。如果计算平均值时将它们混在一起，就会对预测的准确性产生影响，所以计算correction factor的数据时，需要区分不同级别的next\_timer\_us。同时，系统是否存在io wait，对factor的敏感度也不同。基于这些考虑，menu使用了一组factor（12个），分别用于不同next\_timer\_us、不同io wait的场景下的的校正。
>
> 最后，在有些场合下，next\_timer\_us的预测是完全不正确的，如存在固定周期的中断时（音频等）。这时menu采用另一种不同的预测方式：统计过去8次停留时间的标准差（stand deviation），如果小于一定的门限值，则使用这8个停留时间的平均值，作为预测值。

任务2，延迟容忍度（latency\_req）的估算，menu综合考虑了两种因素，如下：

> 1）由pm qos获得的，系统期望的，CPU和DMA的延迟需求。这是一个硬性指标。
>
> 2）基于这样一个经验法则：越忙的系统，对系统延迟的要求越高，结合任务1中预测到的停留时间（predicted\_us），以及当前系统的CPU平均负荷和iowaiters的个数（get\_iowait\_load函数获得），算出另一个延迟容忍度，计算公式（这是一个经验公式）为：   
>  predicted\_us / (1 + 2 \* loadavg +10 \* iowaiters)   
> 这个公式反映的是退出延迟和预期停留时间之间的比例，loadavg和iowaiters越大，对退出延迟的要求就越高奥。
>
> 最后，latency\_req的值取上面两个估值的最小值。

#### 3. 代码分析

理解menu governor背后的思考之后，再去看代码，就比较简单了。

##### 3.1 初始化

首先，在init代码中，调用cpuidle\_register\_governor，注册menu\_governor，如下：

```
   1: static struct cpuidle_governor menu_governor = {
```

```
   2:         .name =         "menu",
```

```
   3:         .rating =       20,
```

```
   4:         .enable =       menu_enable_device,
```

```
   5:         .select =       menu_select,
```

```
   6:         .reflect =      menu_reflect,
```

```
   7:         .owner =        THIS_MODULE,
```

```
   8: };
```

```
   9:  
```

```
  10: /**
```

```
  11:  * init_menu - initializes the governor
```

```
  12:  */
```

```
  13: static int __init init_menu(void)
```

```
  14: {
```

```
  15:         return cpuidle_register_governor(&menu_governor);
```

```
  16: }
```

```
  17:  
```

```
  18: postcore_initcall(init_menu);
```

由menu\_governor变量可知，该governor的名字为“menu”，rating为20，共提供了enable、select、reflect三个API。

##### 3.2 enable API

enable API负责governor运行前的准备动作，由menu\_enable\_device实现：

```
   1: static int menu_enable_device(struct cpuidle_driver *drv,
```

```
   2:                                 struct cpuidle_device *dev)
```

```
   3: {
```

```
   4:         struct menu_device *data = &per_cpu(menu_devices, dev->cpu);
```

```
   5:         int i;
```

```
   6:  
```

```
   7:         memset(data, 0, sizeof(struct menu_device));
```

```
   8:  
```

```
   9:         /*
```

```
  10:          * if the correction factor is 0 (eg first time init or cpu hotplug
```

```
  11:          * etc), we actually want to start out with a unity factor.
```

```
  12:          */
```

```
  13:         for(i = 0; i < BUCKETS; i++)
```

```
  14:                 data->correction_factor[i] = RESOLUTION * DECAY;
```

```
  15:  
```

```
  16:         return 0;
```

```
  17: }
```

由代码可知，主要任务是初始化在私有数据结构（struct menu\_device）中保存的correction\_factor。struct menu\_device的定义如下：

```
   1: struct menu_device {
```

```
   2:         int             last_state_idx;
```

```
   3:         int             needs_update;
```

```
   4:  
```

```
   5:         unsigned int    next_timer_us;
```

```
   6:         unsigned int    predicted_us;
```

```
   7:         unsigned int    bucket;
```

```
   8:         unsigned int    correction_factor[BUCKETS];
```

```
   9:         unsigned int    intervals[INTERVALS];
```

```
  10:         int             interval_ptr;
```

```
  11: };
```

> last\_state\_idx，记录了上一次进入的C state；
>
> needs\_update，每次从C state返回时，kernel（kernel\sched\idle.c）会调用governor的reflect接口，以便有机会让governor考虑这一次state切换的结果（如更新统计信息）。对menu而言，它的reflect接口会设置needs\_update标志，并在下一次select时，更新状态，具体行为可参考后面的描述；
>
> next\_timer\_us、predicted\_us，可参考第2章中的有关说明；
>
> correction\_factor，保存校正因子的数组，因子的个数为BUCKETS（当前代码为12）；
>
> bucket，指明select state时所使用的因子（当前的校正因子）；
>
> intervals、interval\_ptr，可参考第2章中的描述，用于计算停留时间的标准差，当前代码使用了8个停留时间（INTERVALS）。

##### 3.2 select接口

governor的核心API，根据系统的运行情况，选择一个合适的C state。由menu\_select接口实现，逻辑如下：

```
   1: /**
```

```
   2:  * menu_select - selects the next idle state to enter
```

```
   3:  * @drv: cpuidle driver containing state data
```

```
   4:  * @dev: the CPU
```

```
   5:  */
```

```
   6: static int menu_select(struct cpuidle_driver *drv, struct cpuidle_device *dev)
```

```
   7: {
```

```
   8:     struct menu_device *data = this_cpu_ptr(&menu_devices);
```

```
   9:     int latency_req = pm_qos_request(PM_QOS_CPU_DMA_LATENCY);
```

```
  10:     int i;
```

```
  11:     unsigned int interactivity_req;
```

```
  12:     unsigned long nr_iowaiters, cpu_load;
```

```
  13:  
```

```
  14:     if (data->needs_update) {
```

```
  15:         menu_update(drv, dev);
```

```
  16:         data->needs_update = 0;
```

```
  17:     }
```

```
  18:  
```

```
  19:     data->last_state_idx = CPUIDLE_DRIVER_STATE_START - 1;
```

```
  20:  
```

```
  21:     /* Special case when user has set very strict latency requirement */
```

```
  22:     if (unlikely(latency_req == 0))
```

```
  23:         return 0;
```

```
  24:  
```

```
  25:     /* determine the expected residency time, round up */
```

```
  26:     data->next_timer_us = ktime_to_us(tick_nohz_get_sleep_length());
```

```
  27:  
```

```
  28:     get_iowait_load(&nr_iowaiters, &cpu_load);
```

```
  29:     data->bucket = which_bucket(data->next_timer_us, nr_iowaiters);
```

```
  30:  
```

```
  31:     /*
```

```
  32:      * Force the result of multiplication to be 64 bits even if both
```

```
  33:      * operands are 32 bits.
```

```
  34:      * Make sure to round up for half microseconds.
```

```
  35:      */
```

```
  36:     data->predicted_us = div_round64((uint64_t)data->next_timer_us *
```

```
  37:                      data->correction_factor[data->bucket],
```

```
  38:                      RESOLUTION * DECAY);
```

```
  39:  
```

```
  40:     get_typical_interval(data);
```

```
  41:  
```

```
  42:     /*
```

```
  43:      * Performance multiplier defines a minimum predicted idle
```

```
  44:      * duration / latency ratio. Adjust the latency limit if
```

```
  45:      * necessary.
```

```
  46:      */
```

```
  47:     interactivity_req = data->predicted_us / performance_multiplier(nr_iowaiters, cpu_load);
```

```
  48:     if (latency_req > interactivity_req)
```

```
  49:         latency_req = interactivity_req;
```

```
  50:  
```

```
  51:     /*
```

```
  52:      * We want to default to C1 (hlt), not to busy polling
```

```
  53:      * unless the timer is happening really really soon.
```

```
  54:      */
```

```
  55:     if (data->next_timer_us > 5 &&
```

```
  56:         !drv->states[CPUIDLE_DRIVER_STATE_START].disabled &&
```

```
  57:         dev->states_usage[CPUIDLE_DRIVER_STATE_START].disable == 0)
```

```
  58:         data->last_state_idx = CPUIDLE_DRIVER_STATE_START;
```

```
  59:  
```

```
  60:     /*
```

```
  61:      * Find the idle state with the lowest power while satisfying
```

```
  62:      * our constraints.
```

```
  63:      */
```

```
  64:     for (i = CPUIDLE_DRIVER_STATE_START; i < drv->state_count; i++) {
```

```
  65:         struct cpuidle_state *s = &drv->states[i];
```

```
  66:         struct cpuidle_state_usage *su = &dev->states_usage[i];
```

```
  67:  
```

```
  68:         if (s->disabled || su->disable)
```

```
  69:             continue;
```

```
  70:         if (s->target_residency > data->predicted_us)
```

```
  71:             continue;
```

```
  72:         if (s->exit_latency > latency_req)
```

```
  73:             continue;
```

```
  74:  
```

```
  75:         data->last_state_idx = i;
```

```
  76:     }
```

```
  77:  
```

```
  78:     return data->last_state_idx;
```

```
  79: }
```

> 8行，取出per cpu的struct menu\_device指针；
>
> 9行，调用pm\_qos\_request接口，获取系统CPU和DMA所能容忍的延迟。因为cpuidle状态下，运行任何的中断事件唤醒，因此这里只考虑了CPU和DMA；
>
> 14~17行，根据needs\_update标志，调用menu\_update，更新统计信息，具体可参考代码；
>
> 19行，last\_state\_idx会在menu\_reflect中设置，并在menu\_update中使用，此时已经没有用处了，初始化为无效值；
>
> 22~23行，如果pm qos要求的latency为0，则当前系统是一个比较苛刻的状态，不能进入idle状态，直接返回零。由此可以看出，software可以通过pm qos，控制系统是否可以进入idle状态，后续分析pm qos时，会再说明；
>
> 26~29行，调用timer子系统的接口，获取next\_timer\_us，调用sched提供de接口，获取iowaiter的个数以及CPU load信息，并利用next\_timer\_us和iowaiters信息，计算出需要使用哪一类校正因子。计算逻辑比较简单，详见代码；
>
> 36~39行，将next\_timer\_us乘以校正因子，得到predicted\_us。计算时考虑了溢出、精度等情况；
>
> 40行，调用get\_typical\_interval接口，检查是否存在固定周期的情况，检查的逻辑就是计算8次停留时间的标准差，如果存在，则利用平均值更新predicted\_us；
>
> 42~48，根据predicted\_us和系统负荷情况（cpu load、iowaiters），估算另一个延迟容忍值，并和latency\_req，取最小值；
>
> 51~78行，根据上面的信息，查找cpuidle device的所有state，选出一个符合条件的state，并返回该state在cpuidle state数组中的index。

##### 3.3 reflect接口

menu的reflect接口比较简单，更新data->last\_state\_idx后，置位data->needs\_update标志。可以多思考一下：为什么不直接在reflect中更新状态，而是到下一次select时再更新？这个问题留给读者吧。

*原创文章，转发请注明出处。蜗窝科技*，[www.wowotech.net](/pm_subsystem/cpuidle_menu_governor.html)。
