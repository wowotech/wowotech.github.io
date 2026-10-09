---
title: "linux cpufreq framework(4)_cpufreq governor"
date: 2015-08-23T21:15:39+08:00
url: "/pm_subsystem/cpufreq_governor.html"
gid: "208"
emlog_type: "blog"
summary: "由“ linux cpufreq framework(3)_cpufreq core ”的描述可知，cpufreq policy负责设定cpu调频的一个大致范围，而cpu的具体运行频率，则需要由相应的cufreq governor决定（可自行调节频率的CPU除外，后面会再详细介绍）。那到底什么是cpufreq governor？它的运行机制是什么？这就是本文要描述的内容。"
author: "wowo"
category: "电源管理子系统"
category_alias: "pm_subsystem"
tags: ["Linux", "governor", "cpufreq"]
views: 23627
comment_count: 33
aliases:
  - "/pm_subsystem/208.html"
  - "/208.html"
---

## 1. 前言

由“[linux cpufreq framework(3)\_cpufreq core](/pm_subsystem/cpufreq_core.html)”的描述可知，cpufreq policy负责设定cpu调频的一个大致范围，而cpu的具体运行频率，则需要由相应的cufreq governor决定（可自行调节频率的CPU除外，后面会再详细介绍）。那到底什么是cpufreq governor？它的运行机制是什么？这就是本文要描述的内容。

## 2. cpufreq governor的实现

### 2.1 struct cpufreq\_governor

kernel通过struct cpufreq\_governor抽象cpufreq governor，如下：

```
  1: /* include/linux/cpufreq.h */
  2: struct cpufreq_governor {
  3:         char    name[CPUFREQ_NAME_LEN];
  4:         int     initialized;
  5:         int     (*governor)     (struct cpufreq_policy *policy,
  6:                                  unsigned int event);
  7:         ssize_t (*show_setspeed)        (struct cpufreq_policy *policy,
  8:                                          char *buf);
  9:         int     (*store_setspeed)       (struct cpufreq_policy *policy,
 10:                                          unsigned int freq);
 11:         unsigned int max_transition_latency; /* HW must be able to switch to
 12:                         next freq faster than this value in nano secs or we
 13:                         will fallback to performance governor */
 14:         struct list_head        governor_list;
 15:         struct module           *owner;
 16: };
```

> name，该governor的名称，唯一标识某个governor。
>
> initialized，记录governor是否已经初始化okay。
>
> max\_transition\_latency，容许的最大频率切换延迟，硬件频率的切换必须小于这个值，才能满足需求。
>
> governor\_list，用于将该governor挂到一个全局的governor链表（cpufreq\_governor\_list）上。
>
> show\_setspeed和store\_setspeed，回忆一下“[linux cpufreq framework(3)\_cpufreq core](/pm_subsystem/cpufreq_core.html)”所描述的“scaling\_setspeed ”，有些governor支持从用户空间修改频率值，此时该governor必须提供show\_setspeed和store\_setspeed两个回调函数，用于响应用户空间的scaling\_setspeed请求。
>
> governor，cpufreq governor的主要功能都是通过该回调函数实现，该函数借助不同的event，以状态机的形式，实现governor的启动、停止等操作，具体请参考后续的描述。

### 2.2 governor event

kernel将governor的控制方式抽象为下面的5个event，cpufreq core在合适的时机（具体参考下面第3章的介绍），以event的形式（.governor回调），控制governor完成相应的调频动作。

```
  1: /* include/linux/cpufreq.h */
  2: 
  3: /* Governor Events */
  4: #define CPUFREQ_GOV_START       1
  5: #define CPUFREQ_GOV_STOP        2
  6: #define CPUFREQ_GOV_LIMITS      3
  7: #define CPUFREQ_GOV_POLICY_INIT 4
  8: #define CPUFREQ_GOV_POLICY_EXIT 5
```

> CPUFREQ\_GOV\_POLICY\_INIT，policy启动新的governor之前（通常在cpufreq policy刚创建或者governor改变时）发送。governor接收到这个event之后，会进行前期的准备工作，例如初始化一些必要的数据结构（如timer）等。并不是所有governor都需要这个event，后面如果有时间，我们以ondemand governor为例，再介绍它的意义。
>
> CPUFREQ\_GOV\_START启动governor。
>
> CPUFREQ\_GOV\_STOP、CPUFREQ\_GOV\_POLICY\_EXIT，和前面两个event的意义相反。
>
> CPUFREQ\_GOV\_LIMITS，通常在governor启动后发送，要求governor检查并修改频率值，使其在policy规定的有效范围内。

### 2.3 governor register

所有governor都是通过cpufreq\_register\_governor注册到kernel中的，该接口比较简单，查找是否有相同名称的governor已经注册，如果没有，将这个governor挂到全局的链表即可，如下：

```
  1: int cpufreq_register_governor(struct cpufreq_governor *governor)
  2: {
  3:         int err;
  4: 
  5:         if (!governor)
  6:                 return -EINVAL;
  7: 
  8:         if (cpufreq_disabled())
  9:                 return -ENODEV;
 10: 
 11:         mutex_lock(&cpufreq_governor_mutex);
 12: 
 13:         governor->initialized = 0;
 14:         err = -EBUSY;
 15:         if (__find_governor(governor->name) == NULL) {
 16:                 err = 0;
 17:                 list_add(&governor->governor_list, &cpufreq_governor_list);
 18:         }
 19: 
 20:         mutex_unlock(&cpufreq_governor_mutex);
 21:         return err;
 22: }
 23: EXPORT_SYMBOL_GPL(cpufreq_register_governor);
```

## 3 governor相关的调用流程

### 3.1 启动流程

“[linux cpufreq framework(3)\_cpufreq core](/pm_subsystem/cpufreq_core.html)”中介绍过，添加cpufreq设备时，会调用cpufreq\_init\_policy，该接口的主要功能是为当前的cpufreq policy分配并启动一个cpufreq governor，如下：

```
  1: static void cpufreq_init_policy(struct cpufreq_policy *policy)
  2: {
  3:         struct cpufreq_governor *gov = NULL;
  4:         struct cpufreq_policy new_policy;
  5:         int ret = 0;
  6: 
  7:         memcpy(&new_policy, policy, sizeof(*policy));
  8: 
  9:         /* Update governor of new_policy to the governor used before hotplug */
 10:         gov = __find_governor(per_cpu(cpufreq_cpu_governor, policy->cpu));
 11:         if (gov)
 12:                 pr_debug("Restoring governor %s for cpu %d\n",
 13:                                 policy->governor->name, policy->cpu);
 14:         else
 15:                 gov = CPUFREQ_DEFAULT_GOVERNOR;
 16: 
 17:         new_policy.governor = gov;
 18: 
 19:         /* Use the default policy if its valid. */
 20:         if (cpufreq_driver->setpolicy)
 21:                 cpufreq_parse_governor(gov->name, &new_policy.policy, NULL);
 22: 
 23:         /* set default policy */
 24:         ret = cpufreq_set_policy(policy, &new_policy);
 25:         if (ret) {
 26:                 pr_debug("setting policy failed\n");
 27:                 if (cpufreq_driver->exit)
 28:                         cpufreq_driver->exit(policy);
 29:         }
 30: }
```

> 9~13行：首先查看是否在hotplug之前最后使用的governor（保存在per cpu的全局变量cpufreq\_cpu\_governor中），如果有，则直接使用这个governor。
>
> 14~15行：如果没有，则使用默认的governor----CPUFREQ\_DEFAULT\_GOVERNOR，该governor在include/linux/cpufreq.h中定义，可以通过kernel配置项选择，可选的governor包括performace、powersave、userspace、ondmand和conservative五种。
>
> 20~21行：如果cpufreq driver提供了setpolicy接口，则说明CPU可以在policy指定的有效范围内，确定具体的运行频率，因此不再需要governor确定运行频率。但如果此时的governor是performace和powersave两种，则有必要通知到cpufreq driver，以便它的setpolicy接口可以根据实际情况正确设置频率范围。怎么通知呢？通过struct cpufreq\_policy结构中的policy变量（名字很费解啊！），可选的值有两个，CPUFREQ\_POLICY\_PERFORMANCE和CPUFREQ\_POLICY\_POWERSAVE。
>
> 24行：调用cpufreq\_set\_policy，启动governor，代码如下。

```
  1: static int cpufreq_set_policy(struct cpufreq_policy *policy,
  2:                                 struct cpufreq_policy *new_policy)
  3: {
  4:         ...
  5:         if (cpufreq_driver->setpolicy) {
  6:                 policy->policy = new_policy->policy;
  7:                 pr_debug("setting range\n");
  8:                 return cpufreq_driver->setpolicy(new_policy);
  9:         }
 10: 
 11:         if (new_policy->governor == policy->governor)
 12:                 goto out;
 13: 
 14:         pr_debug("governor switch\n");
 15: 
 16:         /* save old, working values */
 17:         old_gov = policy->governor;
 18:         /* end old governor */
 19:         if (old_gov) {
 20:                 __cpufreq_governor(policy, CPUFREQ_GOV_STOP);
 21:                 up_write(&policy->rwsem);
 22:                 __cpufreq_governor(policy, CPUFREQ_GOV_POLICY_EXIT);
 23:                 down_write(&policy->rwsem);
 24:         }
 25: 
 26:         /* start new governor */
 27:         policy->governor = new_policy->governor;
 28:         if (!__cpufreq_governor(policy, CPUFREQ_GOV_POLICY_INIT)) {
 29:                 if (!__cpufreq_governor(policy, CPUFREQ_GOV_START))
 30:                         goto out;
 31: 
 32:                 up_write(&policy->rwsem);
 33:                 __cpufreq_governor(policy, CPUFREQ_GOV_POLICY_EXIT);
 34:                 down_write(&policy->rwsem);
 35:         }
 36: 
 37:         /* new governor failed, so re-start old one */
 38:         pr_debug("starting governor %s failed\n", policy->governor->name);
 39:         if (old_gov) {
 40:                 policy->governor = old_gov;
 41:                 __cpufreq_governor(policy, CPUFREQ_GOV_POLICY_INIT);
 42:                 __cpufreq_governor(policy, CPUFREQ_GOV_START);
 43:         }
 44: 
 45:         return -EINVAL;
 46: 
 47:  out:
 48:         pr_debug("governor: change or update limits\n");
 49:         return __cpufreq_governor(policy, CPUFREQ_GOV_LIMITS);
 50: }
```

> 5~9行，对应上面20~21行的逻辑，如果有setpolicy接口，则直接调用，不再进行后续的governor操作，因此使用CPUFREQ\_POLICY\_PERFORMANCE和CPUFREQ\_POLICY\_POWERSAVE两个值，变相的传递governor的信息。
>
> 11~12行，如果新旧governor相同，直接返回。
>
> 19~24行，如果存在旧的governor，停止它，流程是：
>   
> CPUFREQ\_GOV\_STOP---->CPUFREQ\_GOV\_POLICY\_EXIT
>
> 剩余的代码：启动新的governor，流程是：CPUFREQ\_GOV\_POLICY\_INIT---->CPUFREQ\_GOV\_START---->CPUFREQ\_GOV\_LIMITS

### 3.2 调频流程

前面已经多次提到基于cpufreq governor的调频思路，这里再总结一下：

1）有两种类型的cpu：一种只需要给定调频范围，cpu会在该范围内自行确定运行频率；另一种需要软件指定具体的运行频率。

2）对第一种cpu，cpufreq policy中会指定频率范围policy->{min, max}，之后通过setpolicy接口，使其生效即可。

3）对第二种cpu，cpufreq policy在指定频率范围的同时，会指明使用的governor。governor在启动后，会动态的（例如启动一个timer，监测系统运行情况，并根据负荷调整频率），或者静态的（直接设置为某一个合适的频率值），设定cpu运行频率。

kernel document对这个过程有详细的解释，如下：

> Documentation\cpu-freq\governors.txt
>
> CPU can be set to switch independently | CPU can only be set   
>  within specific "limits" | to specific frequencies
>
> "CPUfreq policy"
>   
>  consists of frequency limits (policy->{min,max})
>   
>  and CPUfreq governor to be used
>   
>  / \
>   
>  / \
>   
>  / the cpufreq governor decides
>   
>  / (dynamically or statically)
>   
>  / what target\_freq to set within
>   
>  / the limits of policy->{min,max}
>   
>  / \
>   
>  / \
>   
>  Using the ->setpolicy call, Using the ->target/target\_index call,
>   
>  the limits and the the frequency closest
>   
>  "policy" is set. to target\_freq is set.
>   
>  It is assured that it
>   
>  is within policy->{min,max}

## 4 常用的governor介绍

最后，我们介绍一下kernel中常见的cpufreq governor。

1）Performance

性能优先的governor，直接将cpu频率设置为policy->{min,max}中的最大值。

2）Powersave

功耗优先的governor，直接将cpu频率设置为policy->{min,max}中的最小值。

3）Userspace

由用户空间程序通过scaling\_setspeed文件修改频率。

4）Ondemand

根据CPU的当前使用率，动态的调节CPU频率。

5）Conservative

类似Ondemand，不过频率调节的会平滑一下，不会忽然调整为最大值，又忽然调整为最小值。

*原创文章，转发请注明出处。蜗窝科技*，[www.wowotech.net](/pm_subsystem/cpufreq_governor.html)。
