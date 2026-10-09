---
title: "load_balance函数代码详解"
date: 2022-02-16T07:29:28+08:00
url: "/process_management/load_balance_function.html"
gid: "500"
emlog_type: "blog"
summary: "我们描述CFS任务负载均衡的系列文章一共三篇，第一篇是框架部分，第二篇描述了task placement和active upmigration两个典型的负载均衡场景，第三篇是负载均衡的情景分析，包括tick balance、nohz idle balance和new idle balance。在负载均衡情景分析文档最后，我们给出了结论：tick balancing、nohz idle balanc"
author: "OPPO内核团队"
category: "进程管理"
category_alias: "process_management"
tags: ["load_balance"]
views: 13343
comment_count: 1
aliases:
  - "/process_management/500.html"
  - "/500.html"
---

前言

我们描述CFS任务负载均衡的系列文章一共三篇，第一篇是框架部分，第二篇描述了task placement和active upmigration两个典型的负载均衡场景，第三篇是负载均衡的情景分析，包括tick balance、nohz idle balance和new idle balance。在负载均衡情景分析文档最后，我们给出了结论：tick balancing、nohz idle balancing、new idle balancing都是万法归宗，汇聚到load\_balance函数来完成具体的负载均衡工作。本文就是第三篇负载均衡情景分析的附加篇，重点给大家展示load\_balance函数的精妙。

本文出现的内核代码来自Linux5.10.61，为了减少篇幅，我们对引用的代码进行了删减（例如去掉了NUMA的代码，毕竟手机平台上我们暂时不关注这个特性），如果有兴趣，读者可以配合完整的源代码代码阅读本文。

一、概述

本文主要分成三个部分，第一个部分就是本章，简单的描述了本文的结构和阅读前提条件。第二章是对load\_balance函数设计的数据结构进行描述。这一章不需要阅读，只是在有需要的时候可以查阅几个主要数据结构的各个成员的具体功能。随后的若干个章节是以load\_balance函数为主线，对各个逻辑过程进行逐行分析。

需要强调的是本文不是独立成文的，很多负载均衡的基础知识（例如sched domain、sched group，什么是负载、运行负载、利用率utility，什么是均衡......）在CFS任务负载均衡系列文章的第一篇已经描述，如果没有阅读过，强烈建议提前阅读。如果已经具体负载均衡的基础概念，那么希望本文能够给你带来研读代码的快乐。

二、load\_balance函数使用的数据结构

1、struct lb\_env

在负载均衡的时候，通过 lb\_env数据结构来表示本次负载均衡的上下文：

|  |  |
| --- | --- |
| 成员 | 描述 |
| struct sched\_domain \*sd | 要进行负载均衡的sched domain |
| struct rq \*dst\_rq  int dst\_cpu | 本次均衡的目标CPU。均衡操作试图从该sched domain的busiest cpu的runqueue拉取任务到 dest CPU rq，从而完成本次sched domain的均衡动作。第一轮均衡的dst cpu和dst rq一般设置为发起均衡的cpu及其runqueue，后续如果需要，可以重新设定为local group中的其他cpu，具体可以参考后文的描述。 |
| struct cpumask \*dst\_grpmask | Dst\_cpu所在sched group的cpu mask，即本次均衡dest cpu所在的范围。 |
| struct rq \*src\_rq  int src\_cpu | 该sched domain中最繁忙的那个cpu及其runqueue，均衡的目标就是从该cpu的runqueue拉取任务出来 |
| int new\_dst\_cpu | 一般而言，均衡的dst cpu是发起均衡的cpu，但是，如果因为affinity的原因，src上有任务无法迁移到dst cpu，从而不能完成均衡操作的时候，我们会选择一个新的（仍然在local group内）CPU作为dst cpu，发起第二轮均衡。 |
| enum cpu\_idle\_type idle | 在进行均衡的时候，dst\_cpu的idle状态，这个状态会影响均衡的走向 |
| long imbalance | 对这个成员的解释需要结合migration\_type：  migrate\_load---表示要迁移的负载量  migrate\_util----表示要迁移的utility  migrate\_task---表示要迁移的任务个数  migrate\_misfit---设定为1 |
| struct cpumask \*cpus | Load\_balance的过程中会有多轮的均衡操作，不同轮次的均衡会涉及不同的cpus，这个成员指明了本次均衡有哪些CPUs参与。 |
| unsigned int flags | 标记负载均衡的标志。LBF\_NOHZ\_STATS和LBF\_NOHZ\_AGAIN主要用于负载均衡过程中更新nohz状态使用。当选中的busiest cpu上的所有任务都因为affinity无法进行迁移，这时会设置LBF\_ALL\_PINNED，负载均衡会寻找次忙CPU进行下一轮的均衡。LBF\_NEED\_BREAK主要用来减少均衡过程中关中断时间的。其他的flag的含义可以参考下面对代码的具体解释。 |
| unsigned int loop | 如果确定需要通过迁移任务来保持负载均衡，那么load\_balance函数会通过循环遍历src rq上的cfs task链表来确定迁移的任务数量。Loop会跟踪循环的次数，其值不能大于Loop\_max。 |
| unsigned int loop\_break | 如果一次迁移任务数量比较多，那么每迁移sched\_nr\_migrate\_break个任务就休息一下，让关中断的临界区小一点。 |
| unsigned int loop\_max | 扫描dest cpu运行队列的最大次数。 |
| enum migration\_type migration\_type | 为了达到sched domain负载均衡的目标，本次迁移的类型为何？有四种迁移类型：  migrate\_load---迁移一定量的负载  migrate\_util----迁移一定量的utility  migrate\_task---迁移一定数量的任务  migrate\_misfit---迁移misfit task |
| struct list\_head tasks | 需要进行迁移的任务链表 |

2、struct sd\_lb\_stats

在负载均衡的时候，通过sd\_lb\_stats数据结构来表示sched domain的负载统计信息：

|  |  |
| --- | --- |
| 成员 | 描述 |
| struct sched\_group \*busiest | 该sched domain中，最繁忙的那个sched group（非local group） |
| struct sched\_group \*local | 在该sched domain上进行均衡的时候，标记该sd中哪一个group是local group，即dest cpu所在的group |
| unsigned long total\_load | 该sched domain中所有sched group的负载之和。如果没有特别说明，本文说的负载都是指cfs任务的负载。 |
| unsigned long total\_capacity | 该sched domain中所有sched group的CPU算力之和（可以用于cfs task的算力） |
| unsigned long avg\_load | 该sched domain中sched groups的平均负载 |
| struct sg\_lb\_stats busiest\_stat | 本sched domain中最忙的那个sched group的负载统计信息 |
| struct sg\_lb\_stats local\_stat | Dest cpu所在的本地sched group的负载统计 |

3、struct sg\_lb\_stats

在负载均衡的时候，通过sg\_lb\_stats数据结构来表示sched group的负载统计信息：

|  |  |
| --- | --- |
| 成员 | 描述 |
| avg\_load | 该sched group上每个CPU的平均负载。仅在sched group处于group\_overloaded状态下才计算该值，方便计算迁移负载量。 |
| group\_load | 该sched group上所有CPU的负载之和 |
| group\_capacity | 该sched group的所有cpu算力之和。这里的cpu算力是指可以用于cfs任务的算力。 |
| group\_util | 该sched group上所有CPU利用率之和 |
| group\_runnable | 该sched group上所有CPU的运行负载之和。 |
| sum\_nr\_running | 该sched group上所有任务的数量，包括rt、dl任务 |
| sum\_h\_nr\_running | 该sched group上所有cfs任务的数量 |
| idle\_cpus | 该group中idle cpu的数量 |
| group\_weight | 该group中的cpu数量 |
| group\_type | 该group在负载均衡时候所处的状态，下面代码分析过程中会详细解析各种状态。 |
| group\_misfit\_task\_load | 该组内至少有一个cpu上有misfit task，这里记录了该组所有CPU中，misfit task load最大的值。 |

4、struct sched\_group\_capacity

数据结构sched\_group\_capacity用来描述sched group的算力信息：

|  |  |
| --- | --- |
| 成员 | 描述 |
| atomic\_t ref | 有可能多个sched group会共享sched\_group\_capacity，因此需要一个引用计数。 |
| unsigned long capacity | 该group中可以用于cfs任务的总算力（各个CPU算力之和） |
| unsigned long min\_capacity | 该sched group中最小的可用于cfs任务的capacity（对单个CPU而言） |
| unsigned long max\_capacity | 该sched group中最大的可用于cfs任务的capacity（对单个CPU而言） |
| unsigned long next\_update | 下一次更新算力的时间点 |
| int imbalance | 该group中是否有由于affinity原因产生的不均衡问题 |
| unsigned long cpumask[] | Balance mask |

三、load\_balance函数整体逻辑

从本章开始我们进行代码分析，这一章是load\_balance函数的整体逻辑，后面的章节都是对本章中的一些细节内容进行补充。load\_balance函数实在是太长了，我们分段解读。第一段的逻辑如下：

|  |
| --- |
| static int load\_balance(int this\_cpu, struct rq \*this\_rq,  struct sched\_domain \*sd, enum cpu\_idle\_type idle,  int \*continue\_balancing)---------------------A  {  struct lb\_env env = {---------------------------B  .sd = sd,  .dst\_cpu = this\_cpu,  .dst\_rq = this\_rq,  .dst\_grpmask = sched\_group\_span(sd->groups),  .idle = idle,  .loop\_break = sched\_nr\_migrate\_break,  .cpus = cpus,  .fbq\_type = all,  .tasks = LIST\_HEAD\_INIT(env.tasks),  }; |

A、对load\_balance函数的参数以及返回值解释如下：

|  |  |
| --- | --- |
| 参数及返回值 | 描述 |
| this\_cpu | 本次要进行负载均衡的CPU。需要注意的是：对于new idle balance和tick balance而言，this\_cpu等于current cpu，在nohz idle balance场景中，this\_cpu未必等于current cpu。 |
| this\_rq | 本次负载均衡CPU对应的runqueue |
| sd | 本次均衡的范围，即本次均衡要保证该sched domain上各个group处于负载平衡状态 |
| idle | this\_cpu在发起均衡的时候所处的状态，通过这个状态可以识别new idle load balance和tick balance。 |
| continue\_balancing | 负载均衡是从发起CPU的base domain开始，不断向上，直到顶层的sched domain。continue\_balancing是用来控制是否继续进行上层sched domain的均衡 |
| 返回值 | 本次负载均衡迁移的任务总数 |

B、初始化本次负载均衡的上下文信息。具体可以参考对struct lb\_env的解释。

初始化完第一轮均衡的上下文，下面就看看具体的均衡操作为何。第二段的逻辑如下：

|  |
| --- |
| cpumask\_and(cpus, sched\_domain\_span(sd), cpu\_active\_mask);-------A  redo:  if (!should\_we\_balance(&env)) {  \*continue\_balancing = 0;  goto out\_balanced;-------------------B  }  group = find\_busiest\_group(&env);  if (!group) {  goto out\_balanced;------------------C  }  busiest = find\_busiest\_queue(&env, group);  if (!busiest) {  goto out\_balanced;-----------------D  } |

A、确定本轮负载均衡涉及的cpu，因为是第一轮均衡，所以所有的sched domain中的cpu都参与均衡（cpu\_active\_mask用来剔除无法参与均衡的CPU）。后续如果发现一些异常状况（例如由于affinity原因无法完成任务迁移），那么会清除选定的busiest cpu，跳转到redo进行全新一轮的均衡。

B、判断env->dst\_cpu这个CPU是否适合做指定sched domain的均衡。如果被认定不适合发起balance，那么后续更高层level的均衡也不必进行了（设置continue\_balancing等于0）。在base domain，每个group都只有一个CPU，因此所有的cpu都可以发起均衡。在non-base domain，每个group有多个CPU，如果每一个cpu都可以进行均衡，那么均衡就太密集了，白白消耗CPU资源，所以限制只有第一个idle的cpu可以发起均衡，如果没有idle的CPU，那么group中的第一个CPU可以发起均衡。当然，对于new idle balance没有这样的限制，所以的cpu都可以发起均衡。

C、在该sched domain中寻找最繁忙的sched group。具体逻辑后文会详细描述。如果没有找到busiest group，那么退出本level的均衡

D、在最繁忙的sched group寻找最繁忙的CPU。具体逻辑后文会详细描述。如果没有找到busiest cpu，那么退出本level的均衡

至此已经找到了source CPU，dest cpu就是发起均衡的this cpu，那么就可以开始第一轮的任务迁移了，具体的代码逻辑如下：

|  |
| --- |
| if (busiest->nr\_running > 1) {-------------------A  env.flags |= LBF\_ALL\_PINNED;  env.loop\_max = min(sysctl\_sched\_nr\_migrate, busiest->nr\_running);-----B  more\_balance:-----------------------C  rq\_lock\_irqsave(busiest, &rf);  update\_rq\_clock(busiest);  cur\_ld\_moved = detach\_tasks(&env);----------D  rq\_unlock(busiest, &rf);  if (cur\_ld\_moved) {  attach\_tasks(&env);--------------------E  ld\_moved += cur\_ld\_moved;  }  local\_irq\_restore(rf.flags);  if (env.flags & LBF\_NEED\_BREAK) {  env.flags &= ~LBF\_NEED\_BREAK;  goto more\_balance;-------------------F  }  .......  } |

A、如果要从busiest cpu迁移任务到this cpu，那么至少要有可以拉取的任务。在拉取任务之前，我们先设定all pinned标志。当然后续如果发现不是all pinned的状况就会清除这个标志。

B、为了达到sched domain的负载均衡，我们需要进行任务的迁移，因此我们这里需要遍历busiest rq上的任务，看看哪些任务最适合被迁移到this cpu rq。loop\_max就是扫描src rq上runnable任务的次数。一般而言，任务迁移上限就是busiest runqueue上的任务个数，确保了每一个任务都被扫描到，但是一次均衡操作不适合迁移太多的任务（关中断区间太长），因此，即便busiest runqueue上的任务个数非常多，一次任务迁移不能大于sysctl\_sched\_nr\_migrate个（目前设定是32个）。

C、和redo不同，跳转到more\_balance的新一轮迁移不需要寻找busiest cpu，只是继续扫描busiest rq上的任务列表，寻找适合迁移的任务。之所以这么做主要是为了降低关中断的时长。

D、detach\_tasks函数用来从busiest cpu的rq中摘取适合的任务。具体逻辑后面会详细描述。由于关中断时长的问题，detach\_tasks函数也不会一次性把所有任务迁移到dest cpu上。

E、将detach\_tasks函数摘下的任务挂入到src rq上去。由于detach\_tasks、attach\_tasks会进行多轮，ld\_moved记录了总共迁移的任务数量，cur\_ld\_moved是本轮迁移的任务数

F、在任务迁移过程中，src cpu的中断是关闭的，为了降低这个关中断时间，迁移大量任务的时候需要break一下。

至此已经对dest rq上的任务列表完成了loop\_max次扫描，要看情况是否要发起下一轮次的均衡。具体代码如下：

|  |
| --- |
| if ((env.flags & LBF\_DST\_PINNED) && env.imbalance > 0) {  \_\_cpumask\_clear\_cpu(env.dst\_cpu, env.cpus);  env.dst\_rq = cpu\_rq(env.new\_dst\_cpu);  env.dst\_cpu = env.new\_dst\_cpu;  env.flags &= ~LBF\_DST\_PINNED;  env.loop = 0;  env.loop\_break = sched\_nr\_migrate\_break;  goto more\_balance;-----------------------A  }  if (sd\_parent) {----------------------B  int \*group\_imbalance = &sd\_parent->groups->sgc->imbalance;  if ((env.flags & LBF\_SOME\_PINNED) && env.imbalance > 0)  \*group\_imbalance = 1;  }  if (unlikely(env.flags & LBF\_ALL\_PINNED)) {  \_\_cpumask\_clear\_cpu(cpu\_of(busiest), cpus);  if (!cpumask\_subset(cpus, env.dst\_grpmask)) {  env.loop = 0;  env.loop\_break = sched\_nr\_migrate\_break;  goto redo;-------------C  }  goto out\_all\_pinned;  } |

A、如果sched domain仍然未达均衡均衡状态，并且在之前的均衡过程中，有因为affinity的原因导致任务无法迁移到dest cpu，这时候要继续在src rq上搜索任务，迁移到备选的dest cpu，因此，这里再次发起均衡操作。这里的均衡上下文的dest cpu设定为备选的cpu，loop也被清零，重新开始扫描。

B、本层次的sched domain因为affinity而无法达到均衡状态，我们需要把这个状态标记到上层sched domain的group中去，在上层sched domain进行均衡的时候，该group会被判定为group\_imbalanced，从而有更大的机会选定为busiest group，从而解决该sched domain的均衡问题。

C、如果选中的busiest cpu上的任务全部都是通过affinity锁定在了该cpu上，那么清除该cpu（为了确保下轮均衡不考虑该cpu），再次发起均衡。这种情况下，需要重新搜索source cpu，因此跳转到redo。

至此，source rq上的cfs任务链表已经被遍历（也可能遍历多次），基本上对runnable 任务的扫描已经到位了，如果不行就只能考虑running task了，具体代码逻辑如下：

|  |
| --- |
| if (!ld\_moved) {  if (idle != CPU\_NEWLY\_IDLE)  sd->nr\_balance\_failed++;-----------------------A  if (need\_active\_balance(&env)) {-------------------B  unsigned long flags;  raw\_spin\_lock\_irqsave(&busiest->lock, flags);  if (!cpumask\_test\_cpu(this\_cpu, busiest->curr->cpus\_ptr)) {  raw\_spin\_unlock\_irqrestore(&busiest->lock, flags);  env.flags |= LBF\_ALL\_PINNED;  goto out\_one\_pinned;------------------C  }  if (!busiest->active\_balance) {--------------D  busiest->active\_balance = 1;  busiest->push\_cpu = this\_cpu;  active\_balance = 1;  }  raw\_spin\_unlock\_irqrestore(&busiest->lock, flags);  if (active\_balance) {--------------------E  stop\_one\_cpu\_nowait(cpu\_of(busiest),  active\_load\_balance\_cpu\_stop, busiest,  &busiest->active\_balance\_work);  }  sd->nr\_balance\_failed = sd->cache\_nice\_tries+1;  }  } else  sd->nr\_balance\_failed = 0;-----------F |

A、经过上面的一系列操作，没有完成任何任务的迁移，那么就需要累计sched domain的均衡失败次数。这个失败次数会导致后续进行更激进的均衡，例如迁移cache hot的任务、启动active balance。此外，这里过滤掉了new idle balance的失败，仅统计周期性均衡失败的次数，这是因为系统中new idle balance次数太多，累计其失败次数会导致nr\_balance\_failed过大，容易触发后续激进的均衡。

B、判断是否要启动active balance。所谓active balance就是把当前正在运行的任务迁移到dest cpu上。也就是说经过前面一番折腾，runnable的任务都无法迁移到dest cpu，从而达到均衡，那么就考虑当前正在运行的任务。

C、在启动active balance之前，先看看busiest cpu上当前正在运行的任务是否可以运行在dest cpu上。如果不可以的话，那么不再试图执行均衡操作，跳转到out\_one\_pinned

D、Busiest cpu runqueue上设置active balance的标记

E、发起主动迁移

F、完成了至少一个任务迁移，重置均衡失败计数

Load\_balance最后一段的程序逻辑主要是进行一些清理工作和设定balance\_interval的工作，逻辑比较简单，不再详述，我们会在随后的章节中对load\_balance函数中的一些过程做进一步的描述。

四、寻找sched domain中最繁忙的group

判断当前sched domain是否均衡并返回最忙group的功能是在find\_busiest\_group函数中完成的，我们分段来描述该函数的逻辑，我们先看第一段代码：

|  |
| --- |
| update\_sd\_lb\_stats(env, &sds);--------------A  if (sched\_energy\_enabled()) {  struct root\_domain \*rd = env->dst\_rq->rd;  if (rcu\_dereference(rd->pd) && !READ\_ONCE(rd->overutilized))  goto out\_balanced;-----------------B  } |

A、负载信息都是不断的在变化，在寻找最繁忙group的时候，我们首先要更新sched domain负载均衡信息，以便可以根据最新的负载情况来搜寻。update\_sd\_lb\_stats会更新该sched domain上各个sched group的负载和算力，得到local group以及非local group最忙的那个group的均衡信息，以便后续给出最适合的均衡决策。具体的逻辑后面的章节会详述

B、在系统没有进入overutilized状态之前，EAS起作用。如果EAS起作用，那么负载可能是不均衡的（考虑功耗），因此，这时候不进行负载均衡，依赖task placement的结果。

update\_sd\_lb\_stats函数找到了busiest group，结合local group的状态就可以判断系统的不均衡状态了。当然有一些比较容易判断是否进行均衡的场景，具体代码如下：

|  |
| --- |
| if (!sds.busiest)---------------------------A  goto out\_balanced;  if (busiest->group\_type == group\_misfit\_task)  goto force\_balance;--------------B  if (busiest->group\_type == group\_imbalanced)  goto force\_balance;--------------C  if (local->group\_type > busiest->group\_type)  goto out\_balanced;---------------D |

A、如果没有找到最忙的那个group，说明当前sched domain中，其他的非local的最繁忙的group（后文称之busiest group）没有可以拉取到local group的任务，不需要均衡处理。

B、Busiest group中有misfit task，那么必须要进行均衡，把misfit task拉取到local group中

C、Busiest group是一个由于cpu affinity导致的不均衡，这个不均衡在底层sched domain无法处理，需要在本层domain进行均衡。

D、如果local group比busiest group还要忙，那么不需要进行均衡（目前的均衡只能从其他group拉任务到local group）

其他的复杂场景需要进一步比拼local group和busiest group的情况，group\_overloaded状态下判断是否均衡的代码如下：

|  |
| --- |
| if (local->group\_type == group\_overloaded) {---------A  if (local->avg\_load >= busiest->avg\_load)  goto out\_balanced;----------------------------B  if (local->avg\_load >= sds.avg\_load)  goto out\_balanced;-----------------------------C  if (100 \* busiest->avg\_load <= env->sd->imbalance\_pct \* local->avg\_load)  goto out\_balanced;----------------------------D  } |

A、如果local group和busiest group都比较繁忙（group\_overloaded），那么需要通过avg\_load的比拼来做均衡决策

B、如果local group的平均负载比busiest group还要高，那么不需要进行均衡

C、如果local group的平均负载高于sched domain的平均负载，那么不需要进行均衡

D、虽然busiest group的平均负载高于local group，但是高的不多，那也不需要进行均衡，毕竟均衡需要额外的开销。具体的门限是有sched domain的imbalance\_pct确定的。

非group\_overloaded不看平均负载，主要看idle cpu的情况，具体代码如下：

|  |
| --- |
| if (busiest->group\_type != group\_overloaded) {-----------A  if (env->idle == CPU\_NOT\_IDLE)  goto out\_balanced;-------------------------B  if (busiest->group\_weight > 1 &&  local->idle\_cpus <= (busiest->idle\_cpus + 1))  goto out\_balanced;-------------------------C  if (busiest->sum\_h\_nr\_running == 1)  goto out\_balanced;-------------------------D  }  force\_balance:  calculate\_imbalance(env, &sds);---------------------E  return env->imbalance ? sds.busiest : NULL; |

A、这里处理busiest group没有overload的场景，这时候说明该sched domain中其他的group的算力都是cover当前的任务负载，是否要进行均衡，主要看idle cpu的情况。

B、反正busiest group当前算力能处理其runqueue上的任务，那么在本CPU处于active的情况下没有必要进行均衡，因为这时候关注的是idle cpu，即让更多的idle cpu参与运算，因此，如果本CPU不是idle cpu，那么判断sched domain处于均衡状态。

C、如果busiest group中有更多的idle CPU，那么也没有必要进行均衡

D、如果busiest group中只有一个cfs任务，那么也没有必要进行均衡

E、所有其他情况都是需要进行均衡。calculate\_imbalance用来计算sched domain中不均衡的状态是怎样的。

具体如何进行均衡决策可以参考下面的表格（第一行是local group状态，第一列是busiest group的状态）：

|  |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- |
|  | Has spare | Fully busy | misfit | imbalanced | overloaded |
| Has spare | Nr idle | balanced | N/A | balanced | balanced |
| Fully busy | Nr idle | Nr idle | N/A | balanced | balanced |
| misfit | force | N/A | N/A | force | force |
| imbalanced | force | force | N/A | force | force |
| overloaded | force | force | N/A | force | Avg load |

Balanced：该sched domain处于均衡状态，不需要均衡。

Force：该sched domain处于不均衡状态，通过calculate\_imbalance计算不均衡指数，并有可能通过任务迁移让系统进入均衡状态。

Avg load：通过sched group的平均负载来判断是否需要均衡。尽量不均衡，除非非常的不均衡（通过sched domain的imbalance\_pct参数来设定）

Nr idle：dest cpu处于idle状态，并且local group的idle cpu个数大于busiest group的idle cpu个数，只有在这种情况下才进行均衡。

五、更新sched domain的负载统计

Sched domain的负载统计更新主要在update\_sd\_lb\_stats函数中，其逻辑大致如下：

|  |
| --- |
| do {  local\_group = cpumask\_test\_cpu(env->dst\_cpu, sched\_group\_span(sg));  if (local\_group) {---------------------A  sds->local = sg;  sgs = local;  if (env->idle != CPU\_NEWLY\_IDLE ||  time\_after\_eq(jiffies, sg->sgc->next\_update))  update\_group\_capacity(env->sd, env->dst\_cpu);  }  update\_sg\_lb\_stats(env, sg, sgs, &sg\_status);------------B  if (local\_group)-----------------C  goto next\_group;  if (update\_sd\_pick\_busiest(env, sds, sg, sgs)) {-----------D  sds->busiest = sg;  sds->busiest\_stat = \*sgs;  }  next\_group:  sds->total\_load += sgs->group\_load;--------------E  sds->total\_capacity += sgs->group\_capacity;  sg = sg->next;  } while (sg != env->sd->groups);  if (!env->sd->parent) {----------------------F  struct root\_domain \*rd = env->dst\_rq->rd;  WRITE\_ONCE(rd->overload, sg\_status & SG\_OVERLOAD);  WRITE\_ONCE(rd->overutilized, sg\_status & SG\_OVERUTILIZED);  } else if (sg\_status & SG\_OVERUTILIZED) {  struct root\_domain \*rd = env->dst\_rq->rd;  WRITE\_ONCE(rd->overutilized, SG\_OVERUTILIZED);  } |

这一段主要是遍历该sched domain的所有group，对其负载统计进行更新。更新完负载之后，我们选定两个sched group：其一是local group，另外一个是最繁忙的non local group。具体逻辑过程解释如下：

A、更新sched group的算力。在base domain（在手机平台上就是MC domain）上，我们会更新发起均衡所在CPU的算力。注意：这里说的CPU算力指的是该CPU可以用于cfs任务的算力，即需要去掉由于thermal pressure而损失的算力，去掉RT/DL/IRQ消耗的算力。具体请参考update\_cpu\_capacity函数。在其他non-base domain（在手机平台上就是DIE domain）上，我们需要对本地sched group（包括发起均衡的CPU所在的group）进行算力更新。这个比较简单，就是把child domain（即MC domain）的所有sched group的算力加起来就OK了。更新后的算力保存在sched group中的sgc成员中。

另外，更新算力没有必要更新的太频繁，这里做了两个限制：其一是只有local group才进行算力更新，其二是通过时间间隔来减少new idle频繁的更新算力。

B、更新该sched group的负载统计，下面的章节会详细描述。

C、在sched domain的各个group遍历中，我们需要两个group信息，一个是local group，另外一个就是non local group中的最忙的那个group。显然，如果是local group，不需要下面的比拼最忙的过程。

D、找到non local group中的最忙的那个group。由于涉及各种group type，我们在下一章详述如何判断一个group更忙。

E、更新sched domain上各个sched group总的负载和算力

F、更新root domain的overload和overutil状态。对于顶层的sched domain，我们需要把各个sched group的overload和overutil状态体现到root domain中。

六、更新sched group的负载

更新sched group负载是在update\_sg\_lb\_stats函数中完成的，我们分段来描述该函数的逻辑，我们先看第一段代码：

|  |
| --- |
| for\_each\_cpu\_and(i, sched\_group\_span(group), env->cpus) {  struct rq \*rq = cpu\_rq(i);  sgs->group\_load += cpu\_load(rq);  sgs->group\_util += cpu\_util(i);  sgs->group\_runnable += cpu\_runnable(rq);  sgs->sum\_h\_nr\_running += rq->cfs.h\_nr\_running;  nr\_running = rq->nr\_running;  sgs->sum\_nr\_running += nr\_running;-------------------A  if (nr\_running > 1)  \*sg\_status |= SG\_OVERLOAD;------------------B  if (cpu\_overutilized(i))  \*sg\_status |= SG\_OVERUTILIZED;-------------C  if (!nr\_running && idle\_cpu(i)) {-----------------D  sgs->idle\_cpus++;  continue;  }  if (local\_group)------------E  continue;  if (env->sd->flags & SD\_ASYM\_CPUCAPACITY &&  sgs->group\_misfit\_task\_load < rq->misfit\_task\_load) {  sgs->group\_misfit\_task\_load = rq->misfit\_task\_load;  \*sg\_status |= SG\_OVERLOAD;  }  } |

A、sched group负载有三种，load、runnable load和util，把所有cpu上load、runnable load和util累计起来就是sched group的负载。除了PELT跟踪的load avg信息，我们还统计了sched group中的cfs任务和总任务数量。

B、只要该sched group上有一个CPU上有1个以上的任务，那么就标记该sched group为overload状态。

C、只要该sched group上有一个CPU处于overutilized（该cpu利用率已经达到cpu算力的80%），那么就标记该sched group为overutilized状态。

D、统计该sched group中的idle cpu的个数

E、当sched domain包括了算力不同的CPU（例如DIE domain），那么即便cpu上只有一个任务，但是如果该任务是misfit task那么也标记sched group为overload状态，并记录sched group中最大的misfit task load。需要注意的是：idle cpu不需要检测misfit task，此外，对于local group，也没有必要检测misfit task，毕竟同一个group，算力相同，不可能拉取misfit task到本cpu上。

第二段代码如下：

|  |
| --- |
| sgs->group\_capacity = group->sgc->capacity;--------------A  sgs->group\_weight = group->group\_weight;  sgs->group\_type = group\_classify(env->sd->imbalance\_pct, group, sgs);------B  if (sgs->group\_type == group\_overloaded)-----C  sgs->avg\_load = (sgs->group\_load \* SCHED\_CAPACITY\_SCALE) /  sgs->group\_capacity; |

A、更新sched group的总算力和cpu个数。再次强调一下，这里的capacity是指cpu可以用于cfs任务的算力

B、判定sched group当前的负载状态

C、计算sched group平均负载（仅在group overloaded状态才计算）。在overload的情况下，通过sched group平均负载可以识别更繁忙的group。

sched group负载状态如下（按照负载从重到轻排列），括号中的数字是该group type的值，数值越大，载荷越重：

|  |  |
| --- | --- |
| group\_type | 描述 |
| group\_overloaded（5） | 这个状态说明该group已经过载，无法为其他任务提供算力。Overloaded的Sched group需要同时满足下面的条件：  1、group上总的任务数（不仅仅是cfs任务）大于group中cpu的个数，即至少有一个任务处于runnable状态。  2、Group上总的util或者runnalbe load大于group上cpu总算力。当然，判断过载需要考虑margin，不能等到util/runnable大于capacity才处理。具体margin和sched domain的imbalance\_pct参数相关）  注意：正常运行起来之后，任务的runnable load总是大于util的。Runnable load是记录running+runnable，而util仅计算running time。因此这里util采用了对capacity的margin，而对runnable load采用了对runnable load的margin。 |
| group\_imbalanced（4） | 由于task affinity的原因导致该group处于不均衡状态 |
| group\_misfit\_task（2） | 该group中有misfit task需要迁移到算力更强的CPU上去 |
| group\_fully\_busy（1） | 该group没有空闲算力 |
| group\_has\_spare  （0） | 该group还有空闲算力，可以承载其他group的任务。当sched group满足下面条件之一就处于这种状态：  1、group中总任务量小于group的cpu个数，即至少有一个cpu处于idle状态。  2、group总算力可以承载当前的group中的任务量  注意：这里的“任务量”需要考虑group util和group runnable load |

判断sched group繁忙程度的函数是group\_classify，可以对照代码理解各sched group繁忙状态的含义。

在对比sched group繁忙程度的时候，我们主要是对比group\_type的值，大的值更忙，小的值比较闲，在相等的时候的判断规则如下：

|  |  |
| --- | --- |
| group\_type | group\_type等值时候的判断条件 |
| group\_overloaded | 那个平均负载高则更忙 |
| group\_imbalanced | 第一个找到的group最忙 |
| group\_misfit\_task | 对比misfit task load，大的更忙 |
| group\_fully\_busy | 第一个找到的group最忙 |
| group\_has\_spare | Idle cpu个数少的更忙，如果idle cpu数目相等，看group上的任务数 |

七、如何计算sched domain的不均衡程度

一旦通过local group和busiest group的信息确定sched domain处于不均衡状态，我们就可以调用calculate\_imbalance函数来计算通过什么方式（migrate task还是migrate load/util）来恢复sched domain的负载均衡状态，也就是设定均衡上下文的migration\_type和imbalance 成员，下面我们分段来描述该函数的逻辑，我们先看第一段代码：

|  |
| --- |
| if (busiest->group\_type == group\_misfit\_task) {  env->migration\_type = migrate\_misfit;  env->imbalance = 1;  return;-----------------------------------A  }  if (busiest->group\_type == group\_imbalanced) {  env->migration\_type = migrate\_task;  env->imbalance = 1;  return;----------------------------------B  } |

A、如果busiest group上有misfit task，那么优先对其进行misfit任务迁移，并且一次迁移一个misfit task。

B、如果busiest group是因为cpu affinity而导致的不均衡，那么通过通过迁移任务来达到平衡，并且一次迁移一个任务。

上面的代码主要处理busiest group中的一些特殊情况，后面的代码主要分两段段来根据local group的状态来进行不均衡的计算。我们首先看local group有空闲算力的情况，我们分成两段分析，第一段代码如下：

|  |
| --- |
| if (local->group\_type == group\_has\_spare) {--------------A  if ((busiest->group\_type > group\_fully\_busy) &&  !(env->sd->flags & SD\_SHARE\_PKG\_RESOURCES)) {------B  env->migration\_type = migrate\_util;  env->imbalance = max(local->group\_capacity, local->group\_util) -  local->group\_util;-------------------C  if (env->idle != CPU\_NOT\_IDLE && env->imbalance == 0) {  env->migration\_type = migrate\_task;  env->imbalance = 1;---------------D  }  return;  }  ......  } |

A、如果local group有一些空闲算力，那么我们还是争取把它利用起来，只要迁移的负载量既不overload local group，也不会让busiest group变得无事可做。

B、如果sched domain标记了SD\_SHARE\_PKG\_RESOURCES（MC domain），那么其在task placement的时候会尽量选择idle cpu。这里load balance路径需要和placement对齐：不使用空闲capacity而是使用nr\_running来进行均衡。如果没有设置SD\_SHARE\_PKG\_RESOURCES那么考虑使用migrate\_util方式来达到均衡。

C、如果local group有一些空闲算力，busiest group又处于繁忙状态（大于full busy），同时满足未设定SD\_SHARE\_PKG\_RESOURCES（对于手机场景就是DIE domain，MC domain需要使用nr\_running而不是util来进行均衡）。这种状态下，我们采用util来指导均衡，具体迁的utility设定为local group当前空闲的算力。

D、有些场景下，local group的util大于其group capacity，根据步骤C计算的imbalance等于0（意味着不需要均衡）。然而，在这种场景下，如果local cpu处于idle状态，那么需要从busiest group迁移过来一个runnable task，从而确保了性能。

Local gorup有空闲算力的第二段代码如下：

|  |
| --- |
| if (local->group\_type == group\_has\_spare) {  ......  if (busiest->group\_weight == 1 ) {---------A  unsigned int nr\_diff = busiest->sum\_nr\_running;  env->migration\_type = migrate\_task;  lsub\_positive(&nr\_diff, local->sum\_nr\_running);  env->imbalance = nr\_diff >> 1;  } else {-----------B  env->migration\_type = migrate\_task;  env->imbalance = max\_t(long, 0, (local->idle\_cpus -  busiest->idle\_cpus) >> 1);  }  return;  } |

代码逻辑走到这里，说明busiest group也有空闲算力（local group也一样），这时候主要考虑的是任务的迁移，让sched domain中的idle cpu尽量的均衡。还有一种可能就是busiest group的状态是繁忙（大于fully busy），但是是在MC domain中进行均衡，这时候均衡的逻辑也是一样的看idle cpu。

A、对于base domain（group只有一个CPU）情况，我们还是希望任务散布在各个sched group（cpu）上。因此，这时候需要从busiest group中迁移任务，保证迁移之后，local group和busiest group中的任务数量相等。

B、如果group中有多个CPU，那么我们的目标就是让local group和busiest group中的idle cpu的数量相等

上面处理了local group有空闲算力的情况，下面的代码处理local group处于非group\_has\_spare状态的情况，代码如下：

|  |
| --- |
| if (local->group\_type < group\_overloaded) {  local->avg\_load = (local->group\_load \* SCHED\_CAPACITY\_SCALE) /  local->group\_capacity;  sds->avg\_load = (sds->total\_load \* SCHED\_CAPACITY\_SCALE) /  sds->total\_capacity;  if (local->avg\_load >= busiest->avg\_load) {  env->imbalance = 0;  return;  }  } |

如果local group没有空闲算力，但是也没有overloaded，可以从busiest group迁移一些负载过来，但是这也许会导致local group进入overloaded状态。因此这里使用了avg\_load来进一步确认是否进行负载迁移。具体的判断方法是local group的平均负载是否大于sched domain的平均负载。如果local group和busiest group都overloaded并且走入calculate imbalance，那么早就确认了busiest group的平均负载大于local group的平均负载。当local group或者busiest group都进入（或者即将进入）overloaded状态，这时候采用迁移负载的方式进行均衡，具体代码如下：

|  |
| --- |
| env->migration\_type = migrate\_load;  env->imbalance = min(  (busiest->avg\_load - sds->avg\_load) \* busiest->group\_capacity,  (sds->avg\_load - local->avg\_load) \* local->group\_capacity  ) / SCHED\_CAPACITY\_SCALE; |

具体迁移的负载量是综合考虑local group、busiest group和sched domain的平均负载情况，确保迁移负载之后，local group、busiest group向sched domain的平均负载靠拢。

八、如何寻找busiest group中最忙的CPU

find\_busiest\_queue函数用来寻找busiest group中最繁忙的cpu。代码逻辑比较简单，和buiest group在上面判断的migrate type相关，不同的type使用不同的方法来寻找busiest cpu：

|  |  |
| --- | --- |
| Migrate type | 寻找最忙CPU的方法 |
| migrate\_load | 最忙CPU是（cpu load/cpu capacity）最大的那个CPU |
| migrate\_util | 最忙CPU是utility最大的那个CPU |
| migrate\_task | 最忙CPU是任务最多的那个CPU |
| migrate\_misfit | 最忙CPU是misfit task load最重的那个CPU |

一旦找到最忙的CPU，那么任务迁移的目标和源头都确定了，后续就可以通过detach tasks和attach tasks进行任务迁移了。

九、detach\_tasks和attach\_tasks

至此，我们已经确定了从src cpu runqueue（即最繁忙的group中最繁忙的cpu）搬移若干load/util/task到dest cpu runqueue。不过无论是load还是util，最后还是要转成任务。detach\_tasks就是确定具体从src rq迁移哪些任务，并把这些任务挂入lb\_env->tasks链表中。detach\_tasks函数第一段的代码逻辑如下：

|  |
| --- |
| while (!list\_empty(tasks)) {----------A  if (env->idle != CPU\_NOT\_IDLE && env->src\_rq->nr\_running <= 1)  break;-----------------B  p = list\_last\_entry(tasks, struct task\_struct, se.group\_node);------C  env->loop++;  if (env->loop > env->loop\_max)  break;--------------------------D  if (env->loop > env->loop\_break) {  env->loop\_break += sched\_nr\_migrate\_break;  env->flags |= LBF\_NEED\_BREAK;  break;------------------------E  }  if (!can\_migrate\_task(p, env))-----------F  goto next;  ......  next:  list\_move(&p->se.group\_node, tasks);  } |

A、src rq的cfs\_tasks链表就是该队列上的全部cfs任务，detach\_tasks函数的主要逻辑就是遍历这个cfs\_tasks链表，找到最适合迁移到目标cpu rq的任务，并挂入lb\_env->tasks链表

B、在idle balance的时候，没有必要把src上的唯一的task拉取到本cpu上，否则的话任务可能会在两个CPU上来回拉扯。

C、从cfs\_tasks链表队尾摘下一个任务。这个链表的头部是最近访问的任务。从尾部摘任务可以保证任务是cache cold的。

D、当把dest rq上的任务都遍历过之后，或者当达到循环上限（sysctl\_sched\_nr\_migrate）的时候退出循环。

E、当dest rq上的任务数比较多的时候，并且需要迁移大量的任务才能完成均衡，为了减少关中断的区间，迁移需要分段进行（每sched\_nr\_migrate\_break暂停一下），把大的临界区分成几个小的临界区，确保系统的延迟性能。

F、如果该任务不适合迁移，那么将其移到cfs\_tasks链表头部。

上面对从cfs\_tasks链表摘下的任务进行基本的判断，具体迁移该任务是否能达到均衡是由detach\_tasks函数第二段代码逻辑完成的，具体如下：

|  |
| --- |
| switch (env->migration\_type) {  case migrate\_load:  load = max\_t(unsigned long, task\_h\_load(p), 1);-------A  if (sched\_feat(LB\_MIN) &&  load < 16 && !env->sd->nr\_balance\_failed)  goto next;-------------------B  if (shr\_bound(load, env->sd->nr\_balance\_failed) > env->imbalance)  goto next;  env->imbalance -= load;-----------------------------C  break;  case migrate\_util:  util = task\_util\_est(p);  if (util > env->imbalance)  goto next;  env->imbalance -= util;------------------D  break;  case migrate\_task:  env->imbalance--;------------E  break;  case migrate\_misfit:  if (task\_fits\_capacity(p, capacity\_of(env->src\_cpu)))  goto next;  env->imbalance = 0;----------F  break;  } |

A、计算该任务的负载。这里设定任务的最小负载是1。

B、LB\_MIN特性限制迁移小任务，如果LB\_MIN等于true，那么task load小于16的任务将不参与负载均衡。目前LB\_MIN系统缺省设置为false。

C、不要迁移过多的load，确保迁移的load不大于env->imbalance。随着迁移错误次增加，这个限制可以适当放宽一些。

D、对于migrate\_util类型的迁移，我们通过任务的util和env->imbalance来判断是否迁移了足够的utility。需要注意的是这里使用了任务的estimation utilization。

E、migrate\_task类型的迁移不关注load或者utility，只关心迁移的任务数

F、找到misfit task即完成迁移

detach\_tasks函数最后一段的代码逻辑如下：

|  |
| --- |
| detach\_task(p, env);---------------------------------A  list\_add(&p->se.group\_node, &env->tasks);  detached++;  #ifdef CONFIG\_PREEMPTION  if (env->idle == CPU\_NEWLY\_IDLE)-----B  break;  #endif  if (env->imbalance <= 0)----------C  break;  continue; |

A、程序执行至此，说明任务P需要被迁移（不能迁移的都跳转到next符号了），因此需要从src rq上摘下，挂入env->tasks链表

B、New idle balance是调度延迟的主要来源，所有对于这种balance，我们一次只迁移一个任务

C、如果完成迁移，那么就退出遍历src rq的cfs task链表。

attach\_tasks主要的逻辑就是遍历均衡上下文的tasks链表，摘下一个个的任务，挂入目标cpu的队列。

十、如何判断一个任务是否可以迁移至目标CPU

can\_migrate\_task函数用来判断一个任务是否可以迁移至目标CPU，具体代码逻辑如下：

|  |
| --- |
| if (throttled\_lb\_pair(task\_group(p), env->src\_cpu, env->dst\_cpu))  return 0;----------------------------A  if ((p->flags & PF\_KTHREAD) && kthread\_is\_per\_cpu(p))  return 0;----------------------------B  if (!cpumask\_test\_cpu(env->dst\_cpu, p->cpus\_ptr)) {  int cpu;  env->flags |= LBF\_SOME\_PINNED;------C  if (env->idle == CPU\_NEWLY\_IDLE || (env->flags & LBF\_DST\_PINNED))  return 0;-----------------D  for\_each\_cpu\_and(cpu, env->dst\_grpmask, env->cpus) {  if (cpumask\_test\_cpu(cpu, p->cpus\_ptr)) {  env->flags |= LBF\_DST\_PINNED;  env->new\_dst\_cpu = cpu;  break;------------------E  }  }  return 0;  } |

A、如果任务p所在的task group在src或者dest cpu上被限流了，那么不能迁移该任务，否者限流的逻辑会有问题

B、Percpu的内核线程不能迁移

C、任务由于affinity的原因不能在dest cpu上运行，因此这里设置上LBF\_SOME\_PINNED标志，表示至少有一个任务由于affinity无法迁移

D、下面的逻辑（E段）会设备备选目标CPU，如果是已经设定好了备选CPU那么直接返回，如果是new idle balance那么也不需要备选CPU，它的主要目标就是迁移一个任务到本idle的cpu。

E、设定备选CPU，以便后续第二轮的均衡可以把任务迁移到备选CPU上

can\_migrate\_task函数第二段代码逻辑如下：

|  |
| --- |
| env->flags &= ~LBF\_ALL\_PINNED;--------A  if (task\_running(env->src\_rq, p))  return 0;---------------------------------B  tsk\_cache\_hot = task\_hot(p, env);-------C  if (tsk\_cache\_hot <= 0 ||  env->sd->nr\_balance\_failed > env->sd->cache\_nice\_tries) {  return 1;-------------------------------D  } |

A、至少有一个任务是可以运行在dest cpu上（从affinity角度），因此清除all pinned标记

B、正处于运行状态的任务不参与迁移，迁移running task是后续active migration的逻辑。

C、判断该任务是否是cache-hot的，这主要从近期在src cpu上的执行时间点来判断，如果上次任务在src cpu上开始执行的时间比较久远（sysctl\_sched\_migration\_cost是门限，目前设定0.5ms），那么其在cache中的内容大概率是被刷掉了，可以认为是cache-cold的。此外如果任务p是src cpu上的next buddy或者last buddy，那么任务是cache hot的。

D、一般而言，我们只迁移cache cold的任务。但是如果进行了太多轮的尝试仍然未能让负载达到均衡，那么cache hot的任务也一样迁移。

参考文献：

1、内核源代码

2、linux-5.10.61\Documentation\scheduler\\*

本文首发在“内核工匠”微信公众号，欢迎扫描以下二维码关注公众号获取最新Linux技术分享：

![](/content/uploadfile/202111/b9c21636066902.png)
