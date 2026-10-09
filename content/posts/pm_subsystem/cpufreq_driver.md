---
title: "Linux cpufreq framework(2)_cpufreq driver"
date: 2015-06-19T22:27:34+08:00
url: "/pm_subsystem/cpufreq_driver.html"
gid: "196"
emlog_type: "blog"
summary: "本文从平台驱动工程师的角度，介绍怎么编写cpufreq驱动。 注1：本文基于 linux-3.18-rc4 内核，其它版本内核可能会稍有不同。"
author: "wowo"
category: "电源管理子系统"
category_alias: "pm_subsystem"
tags: ["Linux", "driver", "cpufreq"]
views: 25487
comment_count: 5
aliases:
  - "/pm_subsystem/196.html"
  - "/196.html"
---

#### 1. 前言

本文从平台驱动工程师的角度，介绍怎么编写cpufreq驱动。

注1：本文基于[linux-3.18-rc4](https://www.kernel.org/pub/linux/kernel/v3.x/testing/linux-3.18-rc4.tar.xz)内核，其它版本内核可能会稍有不同。

#### 2. cpufreq driver的编写步骤

cpufreq driver主要完成平台相关的CPU频率/电压的控制，它在cpufreq framework中是非常简单的一个模块，编写步骤包括：

> 1）平台相关的初始化动作，包括CPU core的clock/regulator获取、初始化等。
>
> 2）生成frequency table，即CPU core所支持的频率/电压列表。并在初始化时将该table保存在policy中。
>
> 3）定义一个struct cpufreq\_driver变量，填充必要的字段，并根据平台的特性，实现其中的回调函数。
>
> 4）调用cpufreq\_register\_driver将driver注册到cpufreq framework中。
>
> 5）cpufreq core会在CPU设备添加时，调用driver的init接口。driver需要在该接口中初始化struct cpufreq\_policy变量。
>
> 6）系统运行过程中，cpufreq core会根据实际情况，调用driver的setpolicy或者target/target\_index等接口，设置CPU的调频策略或者频率值。
>
> 7）系统suspend的时中，会将CPU的频率设置为指定的值，或者调用driver的suspend回调函数；系统resume时，调用driver的resume回调函数。

具体请参考后面的分析。

#### 3. cpufreq driver有关的API即功能分析

**3.1 frequency table**

frequency table是CPU core可以正确运行的一组频率/电压组合，一般情况下，会在项目启动的初期，通过“try频点”的方法，确定出稳定性、通用性都符合要求的频点。

frequency table之所以存在的一个思考点是：table是频率和电压之间的一个一一对应的组合，因此cpufreq framework只需要关心频率，所有的策略都称做“调频”策略。而cpufreq driver可以在“调频”的同时，通过table取出和频率对应的电压，进行修改CPU core电压，实现“调压”的功能。这简化了设计。

cpufreq framework以cpufreq\_frequency\_table抽象frequency table，如下：

```
   1: /* Special Values of .frequency field */
```

```
   2: #define CPUFREQ_ENTRY_INVALID   ~0u
```

```
   3: #define CPUFREQ_TABLE_END       ~1u
```

```
   4: /* Special Values of .flags field */
```

```
   5: #define CPUFREQ_BOOST_FREQ      (1 << 0)
```

```
   6:  
```

```
   7: struct cpufreq_frequency_table {
```

```
   8:         unsigned int    flags;
```

```
   9:         unsigned int    driver_data; /* driver specific data, not used by core */
```

```
  10:         unsigned int    frequency; /* kHz - doesn't need to be in ascending
```

```
  11:                                     * order */
```

```
  12: };
```

> frequency，频率值，单位为kHz，不需要特别的排序。这里定义了两个特殊的频率值：CPUFREQ\_ENTRY\_INVALID，用来表示table中的一个无效频率值；CPUFREQ\_TABLE\_END，用于表示table的结束。
>
> driver\_data，由名字就可以知道，这个字段由driver使用，具体意义由driver定义，可以是电压，也可以是其它（如OPP index，后续文章会详细描述）。
>
> flags，现在只有一个----CPUFREQ\_BOOST\_FREQ，表示这个频率值是一个boost频率。
>
> 注2：Boost表示智能超频技术，是一个在x86平台上的功能，具体可参考“[turbo-boost-technology.html](http://www.intel.com/content/www/us/en/architecture-and-technology/turbo-boost/turbo-boost-technology.html "turbo-boost-technology.html")”，本文不做过多描述。

假设CPU device的OPP 列表已经由cpu subsystem driver调用of\_init\_opp\_table解析出来了，cpufreq driver可以借助dev\_pm\_opp\_init\_cpufreq\_table将OPP列表转换为frequency table。

of\_init\_opp\_table接口请参考“[****Linux*****电源管理(15)*\_PM** ****OPP**** **Interface**](/pm_subsystem/pm_opp.html)”，dev\_pm\_opp\_init\_cpufreq\_table接口的声明如下：

```
   1: /* include/linux/cpufreq.h */
```

```
   2: int dev_pm_opp_init_cpufreq_table(struct device *dev,
```

```
   3:                                   struct cpufreq_frequency_table **table);
```

> 该接口的逻辑很简单，根据传入的设备指针，遍历OPP列表，转换为frequency table，并通过table返回给调用者。具体请参考后面的文章。

**3.2 struct cpufreq\_driver**

struct cpufreq\_driver是cpufreq driver的核心数据结构，我们在“[linux cpufreq framework(1)\_概述](/pm_subsystem/cpufreq_overview.html)”中有简单介绍过，这里再详细分析一下：

```
   1: struct cpufreq_driver {
```

```
   2:     char            name[CPUFREQ_NAME_LEN];
```

```
   3:     u8            flags;
```

```
   4:     void            *driver_data;
```

```
   5:  
```

```
   6:     /* needed by all drivers */
```

```
   7:     int    (*init)        (struct cpufreq_policy *policy);
```

```
   8:     int    (*verify)    (struct cpufreq_policy *policy);
```

```
   9:  
```

```
  10:     /* define one out of two */
```

```
  11:     int    (*setpolicy)    (struct cpufreq_policy *policy);
```

```
  12:  
```

```
  13:     /*
```

```
  14:      * On failure, should always restore frequency to policy->restore_freq
```

```
  15:      * (i.e. old freq).
```

```
  16:      */
```

```
  17:     int    (*target)    (struct cpufreq_policy *policy,    /* Deprecated */
```

```
  18:                  unsigned int target_freq,
```

```
  19:                  unsigned int relation);
```

```
  20:     int    (*target_index)    (struct cpufreq_policy *policy,
```

```
  21:                  unsigned int index);
```

```
  22:     /*
```

```
  23:      * Only for drivers with target_index() and CPUFREQ_ASYNC_NOTIFICATION
```

```
  24:      * unset.
```

```
  25:      *
```

```
  26:      * get_intermediate should return a stable intermediate frequency
```

```
  27:      * platform wants to switch to and target_intermediate() should set CPU
```

```
  28:      * to to that frequency, before jumping to the frequency corresponding
```

```
  29:      * to 'index'. Core will take care of sending notifications and driver
```

```
  30:      * doesn't have to handle them in target_intermediate() or
```

```
  31:      * target_index().
```

```
  32:      *
```

```
  33:      * Drivers can return '0' from get_intermediate() in case they don't
```

```
  34:      * wish to switch to intermediate frequency for some target frequency.
```

```
  35:      * In that case core will directly call ->target_index().
```

```
  36:      */
```

```
  37:     unsigned int (*get_intermediate)(struct cpufreq_policy *policy,
```

```
  38:                      unsigned int index);
```

```
  39:     int    (*target_intermediate)(struct cpufreq_policy *policy,
```

```
  40:                        unsigned int index);
```

```
  41:  
```

```
  42:     /* should be defined, if possible */
```

```
  43:     unsigned int    (*get)    (unsigned int cpu);
```

```
  44:  
```

```
  45:     /* optional */
```

```
  46:     int    (*bios_limit)    (int cpu, unsigned int *limit);
```

```
  47:  
```

```
  48:     int    (*exit)        (struct cpufreq_policy *policy);
```

```
  49:     void    (*stop_cpu)    (struct cpufreq_policy *policy);
```

```
  50:     int    (*suspend)    (struct cpufreq_policy *policy);
```

```
  51:     int    (*resume)    (struct cpufreq_policy *policy);
```

```
  52:     struct freq_attr    **attr;
```

```
  53:  
```

```
  54:     /* platform specific boost support code */
```

```
  55:     bool                    boost_supported;
```

```
  56:     bool                    boost_enabled;
```

```
  57:     int     (*set_boost)    (int state);
```

```
  58: };
```

1）init回调函数

init回调函数是cpufreq driver的入口，由cpufreq core在CPU device添加之后调用，其主要功能就是初始化policy变量（把它想象成cpufreq device）。

对driver而言，不需要太关心struct cpufreq\_policy的内部实现（其实cpufreq framework也在努力实现这个目标，包括将相应的初始化过程封装成一个API等），为了分析方便，我们再把这个结构贴一次：

```
   1: struct cpufreq_cpuinfo {
```

```
   2:     unsigned int        max_freq;
```

```
   3:     unsigned int        min_freq;
```

```
   4:  
```

```
   5:     /* in 10^(-9) s = nanoseconds */
```

```
   6:     unsigned int        transition_latency;
```

```
   7: };
```

```
   8:  
```

```
   9: struct cpufreq_real_policy {
```

```
  10:     unsigned int        min;    /* in kHz */
```

```
  11:     unsigned int        max;    /* in kHz */
```

```
  12:     unsigned int        policy; /* see above */
```

```
  13:     struct cpufreq_governor    *governor; /* see below */
```

```
  14: };
```

```
  15:  
```

```
  16: struct cpufreq_policy {
```

```
  17:     /* CPUs sharing clock, require sw coordination */
```

```
  18:     cpumask_var_t        cpus;    /* Online CPUs only */
```

```
  19:     cpumask_var_t        related_cpus; /* Online + Offline CPUs */
```

```
  20:  
```

```
  21:     unsigned int        shared_type; /* ACPI: ANY or ALL affected CPUs
```

```
  22:                         should set cpufreq */
```

```
  23:     unsigned int        cpu;    /* cpu nr of CPU managing this policy */
```

```
  24:     unsigned int        last_cpu; /* cpu nr of previous CPU that managed
```

```
  25:                        * this policy */
```

```
  26:     struct clk        *clk;
```

```
  27:     struct cpufreq_cpuinfo    cpuinfo;/* see above */
```

```
  28:  
```

```
  29:     unsigned int        min;    /* in kHz */
```

```
  30:     unsigned int        max;    /* in kHz */
```

```
  31:     unsigned int        cur;    /* in kHz, only needed if cpufreq
```

```
  32:                      * governors are used */
```

```
  33:     unsigned int        restore_freq; /* = policy->cur before transition */
```

```
  34:     unsigned int        suspend_freq; /* freq to set during suspend */
```

```
  35:  
```

```
  36:     unsigned int        policy; /* see above */
```

```
  37:     struct cpufreq_governor    *governor; /* see below */
```

```
  38:     void            *governor_data;
```

```
  39:     bool            governor_enabled; /* governor start/stop flag */
```

```
  40:  
```

```
  41:     struct work_struct    update; /* if update_policy() needs to be
```

```
  42:                      * called, but you're in IRQ context */
```

```
  43:  
```

```
  44:     struct cpufreq_real_policy    user_policy;
```

```
  45:     struct cpufreq_frequency_table    *freq_table;
```

```
  46:  
```

```
  47:     struct list_head        policy_list;
```

```
  48:     struct kobject        kobj;
```

```
  49:     struct completion    kobj_unregister;
```

```
  50:  
```

```
  51:     /*
```

```
  52:      * The rules for this semaphore:
```

```
  53:      * - Any routine that wants to read from the policy structure will
```

```
  54:      *   do a down_read on this semaphore.
```

```
  55:      * - Any routine that will write to the policy structure and/or may take away
```

```
  56:      *   the policy altogether (eg. CPU hotplug), will hold this lock in write
```

```
  57:      *   mode before doing so.
```

```
  58:      *
```

```
  59:      * Additional rules:
```

```
  60:      * - Lock should not be held across
```

```
  61:      *     __cpufreq_governor(data, CPUFREQ_GOV_POLICY_EXIT);
```

```
  62:      */
```

```
  63:     struct rw_semaphore    rwsem;
```

```
  64:  
```

```
  65:     /* Synchronization for frequency transitions */
```

```
  66:     bool            transition_ongoing; /* Tracks transition status */
```

```
  67:     spinlock_t        transition_lock;
```

```
  68:     wait_queue_head_t    transition_wait;
```

```
  69:     struct task_struct    *transition_task; /* Task which is doing the transition */
```

```
  70:  
```

```
  71:     /* For cpufreq driver's internal use */
```

```
  72:     void            *driver_data;
```

```
  73: };
```

> 对driver而言，需要在init中初始化policy的如下内容：
>
> cpus，告诉cpufreq core，该policy适用于哪些cpu。大多数情况下，系统中所有的cpu core都由相同的硬件逻辑，统一控制cpu frequency，因此只需要一个policy，就可以管理所有的cpu core。“linux cpufreq framework(3)\_cpufreq core”中会重点介绍。
>
> clk，clock指针，cpufreq core可以利用该指针，获取当前实际的frequency值。
>
> cpuinfo，该cpu调频相关的固定信息，包括最大频率、最小频率、切换延迟，其中最大频率、最小频率可以通过frequency table推导得出。
>
> min、max，调频策略所对应的最小频率、最大频率，初始化时，可以和上面的cpuinfo中的min、max相同。
>
> freq\_table，所对应的frequency table。

除了clk指针外，cpuinfo、min、max、freq\_table等都可以通过cpufreq\_generic\_init接口初始化：

```
   1: int cpufreq_generic_init(struct cpufreq_policy *policy,
```

```
   2:                 struct cpufreq_frequency_table *table,
```

```
   3:                 unsigned int transition_latency);
```

> 该接口以需要初始化的policy、frequency table以及切换延迟为参数，从table中解析policy初始化所需的信息，初始化该policy。
>
> 一般情况下，该接口是enough的，因此在init中调用它即可。

2）verify回调函数

当上层软件需要设定一个新的policy的时候，会调用driver的verify回调函数，检查该policy是否合法。cpufreq core封装了下面两个接口，辅助完成这个功能：

```
   1: int cpufreq_frequency_table_verify(struct cpufreq_policy *policy,
```

```
   2:                                    struct cpufreq_frequency_table *table);
```

```
   3: int cpufreq_generic_frequency_table_verify(struct cpufreq_policy *policy);
```

> cpufreq\_frequency\_table\_verify根据指定的frequency table，检查policy是否合法，检查逻辑很简单：policy的频率范围{min,max}，是否超出policy->cpuinfo的频率范围，是否超出frequency table中的频率范围。
>
> cpufreq\_generic\_frequency\_table\_verify更简单，它以policy中保存的frequency table为参数（policy->freq\_table），调用cpufreq\_frequency\_table\_verify接口。

注3：在这里先提一下cpufreq framework中“频率”的几个层次。
  
最底层，是frequency table中定义的频率，有限的离散频率，代表了cpu的调频能力。
  
往上，是policy->cpuinfo中的频率范围，它对cpu调频进行的简单的限制，该限制可以和frequency table一致，也可以小于table中的范围。必须在driver初始化时给定，之后不能再修改。
  
再往上，是policy的频率范围，代表调频策略。对于可以自动调频的CPU，只需要把这个范围告知CPU即可，此时它是调频的基本单位。对于不可以自动调频的CPU，它是软件层面的一个限制。该范围也可以通过sysfs修改。
  
最上面，是policy中的频率值，对那些不可以调频的CPU，该值就是CPU的运行频率。

3）setpolicy回调函数

对于可以自动调频的CPU，driver需要提供该接口，通过该接口，将调频范围告知CPU。

4）target回调函数，不建议使用了，就不讲了。

5）target\_index回调函数

对于不可以自动调频的CPU，该接口用于指定CPU的运行频率。index表示frequency table中的index。

driver需要通过index，将频率值取出，通过[clock framework](/pm_subsystem/clk_overview.html)提供的API，将CPU的频率设置为对应的值。

同时，driver可以调用[OPP interface](/pm_subsystem/pm_opp.html)，获取该频率对应的电压值，通过[regulator framework](/pm_subsystem/regulator_framework_overview.html)提供的API，将CPU的电压设置为对应的值。

6）get\_intermediate、target\_intermediate，在没有提供target接口的时候使用，希望看这篇文章对的工程师不要使用。不详细介绍了。

7）get回调函数

用于获取指定cpu的频率值，如果可以的话，driver应尽可能提供。如果在init接口中给policy->clk赋值的话，则可以使用cpufreq framework提供的通用接口：

```
   1: unsigned int cpufreq_generic_get(unsigned int cpu);
```

> 该接口会直接调用clock framework API，从policy->clk中获取频率值。

8）exit，和init对应，在CPU device被remove时调用。

9）stop\_cpu，在CPU被stop时调用。

10）suspend、resume回调函数

系统给suspend的时候，clock、regulator等driver有可能被suspend，因此需要在这之前将CPU设置为一个确定的频率值。driver可以通过suspend回调设置，也可以通过policy中的suspend\_freq字段设置（cpufreq core会自动切换）。

同理，系统resume后，CPU的运行频率是什么，可以通过resume回调设置，也可以通过policy中的restore\_freq字段设置。

11）freq\_attr

如果cpufreq driver需要提供一些额外的sysfs attribute，可以通过如下的attribute宏设置，然后保存在cpufreq\_driver的attr数组中：

```
   1: struct freq_attr {
```

```
   2:         struct attribute attr;
```

```
   3:         ssize_t (*show)(struct cpufreq_policy *, char *);
```

```
   4:         ssize_t (*store)(struct cpufreq_policy *, const char *, size_t count);
```

```
   5: };
```

```
   6:  
```

```
   7: #define cpufreq_freq_attr_ro(_name)             \
```

```
   8: static struct freq_attr _name =                 \
```

```
   9: __ATTR(_name, 0444, show_##_name, NULL)
```

```
  10:  
```

```
  11: #define cpufreq_freq_attr_ro_perm(_name, _perm) \
```

```
  12: static struct freq_attr _name =                 \
```

```
  13: __ATTR(_name, _perm, show_##_name, NULL)
```

```
  14:  
```

```
  15: #define cpufreq_freq_attr_rw(_name)             \
```

```
  16: static struct freq_attr _name =                 \
```

```
  17: __ATTR(_name, 0644, show_##_name, store_##_name)
```

**3.3 cpufreq\_driver flags**

注册cpufreq driver时，可以通过flag字段指定一些特性，包括：

```
   1: /* flags */
```

```
   2: #define CPUFREQ_STICKY          (1 << 0)        /* driver isn't removed even if
```

```
   3:                                                    all ->init() calls failed */
```

```
   4: #define CPUFREQ_CONST_LOOPS     (1 << 1)        /* loops_per_jiffy or other
```

```
   5:                                                    kernel "constants" aren't
```

```
   6:                                                    affected by frequency
```

```
   7:                                                    transitions */
```

```
   8: #define CPUFREQ_PM_NO_WARN      (1 << 2)        /* don't warn on suspend/resume
```

```
   9:                                                    speed mismatches */
```

```
  10:  
```

```
  11: /*
```

```
  12:  * This should be set by platforms having multiple clock-domains, i.e.
```

```
  13:  * supporting multiple policies. With this sysfs directories of governor would
```

```
  14:  * be created in cpu/cpu/cpufreq/ directory and so they can use the same
```

```
  15:  * governor with different tunables for different clusters.
```

```
  16:  */
```

```
  17: #define CPUFREQ_HAVE_GOVERNOR_PER_POLICY (1 << 3)
```

```
  18:  
```

```
  19: /*
```

```
  20:  * Driver will do POSTCHANGE notifications from outside of their ->target()
```

```
  21:  * routine and so must set cpufreq_driver->flags with this flag, so that core
```

```
  22:  * can handle them specially.
```

```
  23:  */
```

```
  24: #define CPUFREQ_ASYNC_NOTIFICATION  (1 << 4)
```

```
  25:  
```

```
  26: /*
```

```
  27:  * Set by drivers which want cpufreq core to check if CPU is running at a
```

```
  28:  * frequency present in freq-table exposed by the driver. For these drivers if
```

```
  29:  * CPU is found running at an out of table freq, we will try to set it to a freq
```

```
  30:  * from the table. And if that fails, we will stop further boot process by
```

```
  31:  * issuing a BUG_ON().
```

```
  32:  */
```

```
  33: #define CPUFREQ_NEED_INITIAL_FREQ_CHECK (1 << 5)
```

> CPUFREQ\_STICKY，表示就算所有的init调用都失败了，driver也不被remove。具体应用场景不明。
>
> CPUFREQ\_CONST\_LOOPS，表示频率的调整，不影响loops\_per\_jiffy等kernel常来的计算。
>
> CPUFREQ\_PM\_NO\_WARN，suspend/resume过程相关的flag，后面文章如果分析相应的功能的话，再详细描述。
>
> CPUFREQ\_HAVE\_GOVERNOR\_PER\_POLICY，表示不同的CPU，有不同的频率控制方式，因此cpufreq core会为每一个CPU创建一个cpufreq调频接口。否则（也是正常情况下），一个调频接口可以调整所有CPU的频率。
>
> 其它flag用到时再分析。

**3.4 cpufreq\_register\_driver**

driver的注册接口比较简单，进行一些必要的检查后，将driver保存在一个全局指针（cpufreq\_driver）中，如果该指针不为空，则说明已经有driver注册过了，返回错误（-EEXIST）。

最后，会调用subsys\_interface\_register接口，注册一个subsystem interface（struct subsys\_interface cpufreq\_interface），有关subsystem interface的介绍，可参考“[Linux设备模型(6)\_Bus](/device_model/bus.html)”中的描述。cpufreq与此有关的逻辑，会在下一篇文章详细说明（linux cpufreq framework(3)\_cpufreq core）。

*原创文章，转发请注明出处。蜗窝科技*，[www.wowotech.net](/pm_subsystem/cpufreq_driver.html)。
