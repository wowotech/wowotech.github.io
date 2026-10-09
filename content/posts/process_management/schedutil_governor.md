---
title: "schedutil governor情景分析"
date: 2022-04-26T06:29:07+08:00
url: "/process_management/schedutil_governor.html"
gid: "503"
emlog_type: "blog"
summary: "这是一篇分析schedutil governor（后文称之sugov）代码逻辑的文章。通过详细的代码级别的分析，希望能够帮助读者理解sugov的代码精妙之处。本文主要分四个章节：第一章简单重复了sugov相关的软件结构和基本算法，让读者对整个sugov在系统所处的位置和基本的逻辑控制有所了解。第二章对sugov使用的数据结构给出了详细的解释。第三章对sugov和cpufreq core的基本数据流"
author: "OPPO内核团队"
category: "进程管理"
category_alias: "process_management"
tags: ["governor", "schedutil"]
views: 19643
comment_count: 3
aliases:
  - "/process_management/503.html"
  - "/503.html"
---

前言

这是一篇分析schedutil governor（后文称之sugov）代码逻辑的文章。通过详细的代码级别的分析，希望能够帮助读者理解sugov的代码精妙之处。本文主要分四个章节：第一章简单重复了sugov相关的软件结构和基本算法，让读者对整个sugov在系统所处的位置和基本的逻辑控制有所了解。第二章对sugov使用的数据结构给出了详细的解释。第三章对sugov和cpufreq core的基本数据流和控制流进行分析。第四章描述了sugov本身的调频逻辑。

本文出现的内核代码来自Linux5.10.61，为了减少篇幅，我们会引用缩减版本的代码（仅包含主要逻辑），如果有兴趣，读者可以配合原始代码阅读本文。

一、Sugov概述

1、sugov相关软件模块

Sugov在整个调频软件的位置如下所示：

![](/content/uploadfile/202204/64be1650926074.png)

Sugov作为一种内核调频策略模块，它主要是根据当前CPU的利用率进行调频。因此，sugov会注册一个callback函数（sugov\_update\_shared/sugov\_update\_single）到调度器负载跟踪模块，当CPU util发生变化的时候就会调用该callback函数，检查一下当前CPU频率是否和当前的CPU util匹配，如果不匹配，那么就进行提频或者降频。

为了适配各种场景，sugov还提供了可调参数，用户空间可以检测当前的场景，并根据不同的场景设定不同的参数，以便满足用户性能/功耗的需求。

Sugov选定target frequency之后，需要通过cpufreq core（cpufreq framework）、cpufreq driver，cpu调频硬件完成频率的调整。cpufreq core是一个硬件无关的调频框架，集中管理了cpufreq governor、cpufreq driver、cpufreq device对象，同时提供了简单方便使用的接口API，让工程师很轻松的就能完成特定governor或者driver的撰写。

2、Sugov的基本算法描述

Sugov的基本算法如下：

![](/content/uploadfile/202204/0ff01650926152.png)

和基于采样的governor不同的是sugov是基于调度器调度事件的。每当发生调度事件的时候，负载跟踪模块会及时更新各个level的调度实体和cfs\_rq的平均调度负载（sched\_avg），直到顶层cfs rq（即CPU的平均调度负载） 。每当CPU利用率发生变化的时候，调度器都会调用cpufreq\_update\_util通知sugov，由sugov判断是否需要进行调频操作。基于采样的governor是governor定期去采样负载信息，而sugov是调度事件（进程切换、入队、出队、tick等）驱动调频的，因此调频会更及时。具体驱动调频的时机包括：

（1）实时线程（rt或者deadline）的入队出队

（2）Cpu上的cfs util发生变化

（3）处于Iowait的任务被唤醒

调度事件的发生还是非常密集的，特别是在重载的情况下，很多任务可能执行若干个us就切换出去了。如果每次都计算CPU util看看是否需要调整频率，那么本身sugov就给系统带来较重的负荷，因此并非每次调频时机都会真正执行调频检查，sugov设置了一个最小调频间隔，小于这个间隔的调频请求会被过滤掉。当然，这个最小调频间隔规定也不是永远强制执行，在特定情况下（例如cpufreq core修改了sugov可以动态调整的范围的时候），调频间隔判断可以略过。

由于调频的最小粒度是cluster，当一个cpu上的util发生变化而发起调频操作的时候，实际上sugov会遍历cluster中的所有CPU（如果cluster中只有一个cpu，那么不需要这么复杂，我们这里以cluster中包含多个cpu的sugov\_update\_shared场景为例来进行说明），找到util最大的那个，用这个最大的util来驱动调频。在计算cpu util要从多个视角考量：

（1）cfs、rt、dl、irq的load avg。这些都是从执行时间的视角来看util，由于PELT窗口是同步的，因此这些load avg可以对比和运算

（2）任务属性视角。对于deadline类型的任务，我们需要根据当前dl任务的参数来计算满足该任务deadline的最小utility。

找到cluster中最大的cpu utility之后，通过将其映射到一个具体的CPU frequency上来（具体参考map\_util\_freq函数）。目前sugov采用的映射公式如下：

next\_freq = C \* max\_freq \* util / max

其中C = 1.25，表示CPU需要调整的next freq需要提供1.25倍的算力，这样CPU在next freq上运行当前的任务还有20%的算力余量。这里计算出来的next\_freq未必是最终设定的频率，因为底层硬件支持的调频是一系列的档位频率，因此，还需要底层硬件驱动进一步根据next\_freq来选择一个它支持的频率，最后设定下去。

二、sugov使用的数据结构

1、struct sugov\_tunables

这个数据结构用来描述sugov的可调参数：

|  |  |
| --- | --- |
| 成员 | 描述 |
| struct gov\_attr\_set attr\_set | Sugov所属的attribute set。这个数据结构中最重要的就是policy\_list成员，它是所有使用该tunalbe参数的sugov policy对象链表。如果每个policy都有自己的tunable参数，那么该链表只有一个节点。如果多个policy共享一个tunable参数，那么共享该tunable参数的sugov policy会被挂入该链表。 |
| unsigned int rate\_limit\_us | 目前sugov只有一个可调参数rate\_limit\_us，该参数用来限制连续调频的间隔（单位是us）。当用户空间修改这个参数之后，tunalbe参数链表的所有sugov policy对象的freq\_update\_delay\_ns成员也随之改变。 |

2、struct sugov\_cpu

Sugov为每一个cpu构建了该数据结构，记录per-cpu的调频数据信息：

|  |  |
| --- | --- |
| 成员 | 描述 |
| Struct update\_util\_data update\_util | 这个成员保存了cpu util发生变化之后的callback函数。 |
| struct sugov\_policy \*sg\_policy | 该sugov cpu对应的sugov policy对象。一个cluster中的sugov cpu指向同一个sugov policy对象。 |
| unsigned int cpu | 该sugov cpu对应的CPU id |
| bool iowait\_boost\_pending | 当前是否有pending的iowait boost，当这个iowait boost应用到cpu调频之后，pending标记被清除，下一次iowait boost可以继续发起请求，进入pending状态。 |
| unsigned int iowait\_boost | Iowait boost值，即根据当前io状态设定的util（可能比实际的util要大）。最初被设定为128，后续会随着iowait的情况而变化，如果短期内发起请求大量的iowait boost，那么这个boost会double，如果长期（一个tick）没有更新，那么该值会被reset。 |
| u64 last\_update | 上一次cpu负载变化驱动调频的时间点。这里的update指的是util update，不是指上一次的频率更新时间点。  这个成员是配合iowait boost，为了过滤一些零零星星偶发的io操作引起的boost。 |
| unsigned long bw\_dl | 我们可以通过deadline任务对CPU带宽的需求来定义cpu utility。bw\_dl成员就是该CPU上来自dl任务属性的utility |
| unsigned long max | 该cpu的最大算力（归一化到1024），和当前运行频率无关，对齐到该cpu的最大频率上的算力。 |
| unsigned long saved\_idle\_calls | 这个成员仅在single cpu cluster的调频中有效。在这样的场景中，由于任务迁移会导致该CPU的utility下降，从而引发降频，然而实际上CPU可能有其他任务还在持续执行，这时候降频还为时过早。因此，saved\_idle\_calls保存了上次轮询的idle call的计数。如果这个计数没有变化，说明当前CPU还是繁忙，暂时不适合降频。在multi cpu cluster中不存在这样的问题，因为在调频的时候选择的是所有CPU中utility最大的那个。 |

3、struct sugov\_policy

Sugov为每一个cluster构建了该数据结构，记录per-cluster的调频数据信息：

|  |  |
| --- | --- |
| 成员 | 描述 |
| struct cpufreq\_policy \*policy | 指向cpufreq framework层的policy对象 |
| struct sugov\_tunables \*tunables | Sugov的可调参数 |
| struct list\_head tunables\_hook | Sugov的可调参数可以是per-cluster的，也可以是全系统的。在sugov tunable是global的情况下，共享一套参数的sugov会挂入sugov tunable的链表，这个成员就是链入sugov tunable链表的节点。在per-cluster场景下，sugov tunable和sugov对象是一一对应的，sugov tunable链表只有一个节点。 |
| raw\_spinlock\_t update\_lock | 保护sugov对象的自旋锁，一旦要修改sugov对象必须要持有该锁。 |
| s64 freq\_update\_delay\_ns | 太快的调整CPU也不是好事情，花费太多的CPU资源。调频间隔最好有一个门限，距离上一次频率调整的时间要大于这个成员给出的门限值，sugover才会真正的发起调频操作。这个值跟随sugov tunable中的rate\_limit\_us。 |
| unsigned int next\_freq  u64 last\_freq\_update\_time | next\_freq记录了上次调整的CPU频点值  last\_freq\_update\_time记录了上一次进行频率调整的时间点 |
| unsigned int cached\_raw\_freq | 这个频率是上次根据utility计算出来的原始频率（或者叫做target frequency），这个频率不是最终设定的cpu频率（上面的next\_freq才是），通过一定的算法（例如向上靠近cpu硬件支持的一个频点）可以将其转换成对应的CPU频点值。 |
| struct irq\_work irq\_work  bool work\_in\_progress | 在不支持fast switch的场景下，我们不能直接发起调频，而是通过irq work机制来提交请求。  work\_in\_progress用来控制irq work入队的频次，防止queue过多的irq work。 |
| struct kthread\_work work  struct kthread\_worker worker  struct task\_struct \*thread | 由于非fast switch场景下需要找一个可以阻塞的上下文来完成频率切换，这里采用了通用的kthread机制。Worker是kthread worker线程，用来处理调频的请求。具体的调频请求封装在work中，在irq work中通过kthread work完成调频请求的递交。 |
| struct mutex work\_lock | 用来控制并发的调频操作，只允许一个调频请求下发。 |
| bool limits\_changed | Cpufreq core的max或者min发生了修改，需要立刻开启频率调整，不需要估计调频间隔限制。有些其他的模块也利用这个标记来忽略调频间隔，例如dl模块 |
| bool need\_freq\_update | 当need\_freq\_update等于true的时候，sugov不会忽略任何一次调频请求，都会忠实的下发给驱动进行频率调整。一般而言，sugov不需要每次下发频率调整请求（例如变化的cpu util不足以引起CPU频点的变化），但是在某些特殊场景下，我们需要sugov忠实下发。具体场景下面会具体分析。 |

三、Sugov和cpufreq core之间的接口和流程分析

1、Sugov的注册

如果想要自己实现一个cpufreq governor，那么就需要定义一个struct cpufreq\_governor的数据对象并向cpufreq framwork（或者叫cpufreq core）系统注册它。对于sugov而言，这个数据对象定义如下：

|  |
| --- |
| struct cpufreq\_governor schedutil\_gov = {  .name = "schedutil",  .owner = THIS\_MODULE,  .flags = CPUFREQ\_GOV\_DYNAMIC\_SWITCHING,  .init = sugov\_init,  .exit = sugov\_exit,  .start = sugov\_start,  .stop = sugov\_stop,  .limits = sugov\_limits,  }; |

然后调用cpufreq\_governor\_init(schedutil\_gov)即可向系统注册sugov。完成注册之后，仅仅是系统可以看到这个governor，它还不一定会起作用，在将sugov设置为当前的governor之后（通过/sys/devices/system/cpu/cpufreq/policyx/scaling\_governor），sugov的功能才会启用，根据调度器的利用率信息对CPU频率进行控制。当sugov切换成当前governor的时候，cpufreq framework会依次调用sugov\_init、sugov\_start完成sugov的初始化和启动。当sugov被其他governor替换的时候，cpufreq framework会依次调用sugov\_stop、sugov\_exit函数。具体请参考cpufreq\_set\_policy函数。

除了人为的切换cpufreq gover，在cpu hotplug场景也会有governor的启停操作。例如当CPU offline的时候，如果cluster中的所有CPU都被offline，那么cpufreq framework会依次调用sugov\_stop、sugov\_exit函数让sugov停止工作。如果仅仅是cluster中的一个cpu被offline，cluster中还有其他oneline的cpu core，那么我们仅仅是调用sugov\_stop来暂停sugov的运作，然后在cpufreq policy中清除该cpu的bit，最后调用sugov\_start来确保其他active cpu可以通过sugov来继续开展频率调整工作。Cpufreq online的操作类似，当online的cpu core所在的cluster还有active的cpu的时候，那么我们仅仅需要调用sugov\_stop暂停该policy的运作，在把当前online的cpu core加入cpufreq policy的cpu mask后，重新调用sugov\_start来恢复该cluster的调频运作就OK了。如果该oneline的cpu是cluster的第一个cpu core，那么逻辑要复杂一些，需要重新初始化整个cpufreq policy（cpufreq\_init\_policy），也就会依次调用sugov\_init、sugov\_start完成sugov的初始化和启动。

当cpufreq policy（位于cpufreq framework）中的频率调整范围发生变化之后（例如由于发热而引起的CPU限频），需要通知到cpufreq governor layer，这时候会调用sugov\_limits来通知频率受限事件。

Cpufreq governor有很多种，并不是每一种governor都是普适的。例如：有些特定的的硬件平台根本就不希望上层的governor自动调整频率，而是自己完全掌控，这时候sugov类似的governor就不适合了。为了解决这个问题，struct cpufreq\_governor和struct cpufreq\_driver都提供了flags成员，报告给cpufreq core，由它来判断一个cpufreq governor是否匹配当前硬件驱动。由于sugov会自己根据CPU利用率动态的调整频率，因此需要标记CPUFREQ\_GOV\_DYNAMIC\_SWITCHING。

2、sugov的初始化

我们分两段来解析sugov的初始化过程。sugov\_init的第一段执行逻辑大致如下：

|  |
| --- |
| if (policy->governor\_data)-------------------------A  return -EBUSY;  cpufreq\_enable\_fast\_switch(policy);-----------B  sg\_policy = sugov\_policy\_alloc(policy);--------C  ret = sugov\_kthread\_create(sg\_policy);-------D |

A、struct cpufreq\_policy的governor\_data会指向当前governor policy对象，要把sugov设置为当前governor，那么旧的governor应该完成stop和exit动作，确保governor\_data为空，否则返回-EBUSY

B、调用cpufreq\_enable\_fast\_switch来使能fast switch功能。所谓fast switch是指在频率切换过程中不涉及阻塞的行为，可以直接在中断上下文执行频率切换动作。当然，这里只是sugov policy层enable fast switch，具体是否支持还要看底层cpufreq驱动。为了调和cpufreq governor和cpufreq driver的行为，cpufreq policy数据结构提供了两个成员：fast\_switch\_possible和fast\_switch\_enabled。如果底层驱动支持快速切频功能，那么cpufreq driver必须提供fast\_switch的回调函数，这时候cpufreq policy的fast\_switch\_possible等于true，表示驱动支持任何上下文（包括中断上下文）的频率切换。只有上下打通（上指governor，下指driver），CPU频率切换才走fast switch路径。

此外，fast switch和cpufreq transition notifier是互斥的，如果有驱动已经注册了cpufreq transition notifier，那么fast switch将无法enable，反之亦然。那么为何会有这样的限制呢？其实在fasts witch出现之前就已经有了cpufreq transition notifier机制：即当CPU频率发生变化的时候，cpufreq驱动将通过notifier机制向注册的模块发送PRECHANGE和POSTCHANGE消息。收到消息的模块会调用callback来回应这个频率切换事件。然而在fasts witch机制下，我们不能调用这些callback，除非保证调用callback的过程是非阻塞的。为了保证频率切换是串行执行的，驱动模块一般会执行下面的逻辑：

|  |
| --- |
| cpufreq\_freq\_transition\_begin---通知CPUFREQ\_PRECHANGE事件  操作硬件寄存器，完成CPU频率切换  cpufreq\_freq\_transition\_end---通知CPUFREQ\_POSTCHANGE事件 |

对于fast switch，我们无法实现类似的notifiy操作，因为cpufreq\_freq\_transition\_begin函数中有阻塞操作wait\_event（为了串行化多个上下文的频率切换动作，transition\_begin和transition\_end顺便也完成了同步功能）。当然，我们也可以设计atomic版本的cpufreq notifier机制，但是这样要改造所有callback函数，这几乎是不现实的，所以做成fast switch和cpufreq transition notifier互斥是最简单的方案。

顺便说一句，虽然fast switch没有了频率切换通知机制，但是串行化仍然是需要的，因此，调用cpufreq\_driver\_fast\_switch（一般是governor）完成cpu频率快速切换的时候，调用者需要使用适当的同步机制。

C、调用sugov\_policy\_alloc分配sugov policy对象，通过其policy成员建立和cpufreq framework的关联。

D、当不支持fast switch的时候，我们需要一个可以阻塞的线程上下文来发起调频操作。在早期的版本，这是通过workqueue机制来实现的。不过考虑到普通线程在RT/DL负载重或者整机负载非常重的情况下，cpu频率切换会由于调度延迟的加大而delay。因此，slow switch修改为优先级为50的rt内核线程（SCHED\_FIFO）来替代workqueue。后来，考虑到频率切换确实非常重要，需要尽快完成，因此最终将该内核线程修改为deadline类型，即一人之下（stop class），万人之上。具体请参考sugov\_kthread\_create函数。当policy是fast switch模式的时候，这个deadline的内核线程是不需要的。

一般手机系统中有多个调频域，因此有多个cpufreq policy（对应cluster，cluster内的cpu统一调频），每个policy都可以有自己的可调节参数，当然也可以所有policy共同使用一组可调参数（global\_tunables全局变量）。具体是使用统一的可调参数还是per-cluster可调参数是底层驱动决定的（CPUFREQ\_HAVE\_GOVERNOR\_PER\_POLICY）。目前手机场景，大部分是per-cluster的可调参数。因此我们这里略过global tunables的场景，sugov\_init的第二段执行逻辑大致如下：

|  |
| --- |
| tunables = sugov\_tunables\_alloc(sg\_policy);-----------A  sg\_policy->tunables = tunables;  tunables->rate\_limit\_us = cpufreq\_policy\_transition\_delay\_us(policy);------B  policy->governor\_data = sg\_policy;----------C  ret = kobject\_init\_and\_add(&tunables->attr\_set.kobj, &sugov\_tunables\_ktype,  get\_governor\_parent\_kobj(policy), "%s",  schedutil\_gov.name);---------D |

A、调用sugov\_tunables\_alloc函数分配该policy（或者说cluster）的struct sugov\_tunables数据对象，并建立sugov和tunable对象之间的关联（即把sugov的tunables成员指向这个分配的数据对象，同时也会把sugov挂入tunables 的链表）。

B、关于调频间隔有三个控制参数。一个是来自CPU调频硬件能力的，即硬件需要从F1频率切换到F2频率并且稳定下来的时间间隔。保存在cpufreq policy数据结构的cpuinfo成员的transition\_latency中。另外两个来自软件，一个是上层sugov的设定，保存在tunables数据结构的rate\_limit\_us成员中（也可以说是sugov policy的freq\_update\_delay\_ns的成员）。另外一个是底层cpufreq driver对上层governor的间隔需求，保存在cpufreq policy数据结构的transition\_delay\_us中。在初始化的时候，rate\_limit\_us应该跟随policy->transition\_delay\_us，如果driver没有设定该值，那么考虑硬件transition\_latency乘上一个合理的倍数（缺省是1000）。对于一些硬件transition\_latency比较慢的平台，这样的调频间隔设定的太大，因此clamp min到10ms。

C、建立cpufreq framework和sugov的关联（初始化governor\_data）

D、初始化可调参数的sysfs接口

3、Sugov的启动

sugov\_start首先执行sugov policy各个成员的初始化，逻辑大致如下：

|  |
| --- |
| sg\_policy->freq\_update\_delay\_ns = sg\_policy->tunables->rate\_limit\_us \* NSEC\_PER\_USEC;  sg\_policy->last\_freq\_update\_time = 0;  sg\_policy->next\_freq = 0;  sg\_policy->work\_in\_progress = false;  sg\_policy->limits\_changed = false;  sg\_policy->cached\_raw\_freq = 0;  sg\_policy->need\_freq\_update = cpufreq\_driver\_test\_flags(CPUFREQ\_NEED\_UPDATE\_LIMITS); |

在cpufreq governor layer，sugov是否发起频率切换是由freq\_update\_delay\_ns参数确定的，因此在启动sugov的时候需要根据tunable参数中的rate\_limit\_us来完成其初始化。need\_freq\_update的初始化和底层驱动相关，如果底层驱动需要在policy更新min或者max frequency的时候，无脑下发调频请求（参考\_\_cpufreq\_driver\_target），那么need\_freq\_update是always true的（即驱动是标记CPUFREQ\_NEED\_UPDATE\_LIMITS，目前只有intel CPU的驱动是这样设定的）。其他的成员初始化非常简单，不再赘述。

随后，sugov\_start会遍历该sugov policy（cluster）中的所有cpu，建立sugov cpu和sugov policy之间的关联，代码逻辑如下：

|  |
| --- |
| for\_each\_cpu(cpu, policy->cpus) {  struct sugov\_cpu \*sg\_cpu = &per\_cpu(sugov\_cpu, cpu);  memset(sg\_cpu, 0, sizeof(\*sg\_cpu));  sg\_cpu->cpu = cpu;  sg\_cpu->sg\_policy = sg\_policy;  } |

最后，sugov\_start会遍历该sugov policy（cluster）中的所有cpu，调用cpufreq\_add\_update\_util\_hook为sugov cpu注册调频回调函数，代码逻辑如下：

|  |
| --- |
| for\_each\_cpu(cpu, policy->cpus) {  struct sugov\_cpu \*sg\_cpu = &per\_cpu(sugov\_cpu, cpu);  cpufreq\_add\_update\_util\_hook(cpu, &sg\_cpu->update\_util,  policy\_is\_shared(policy) ?  sugov\_update\_shared :  sugov\_update\_single);  } |

至此，sugov和调度器打通了，一旦调度器判断CPU util发生变化，那么将调用相应的回调函数，由sugov进一步判断是否需要进行频率调整。

4、Sugov的停止

sugov\_stop执行逻辑大致如下：

|  |
| --- |
| for\_each\_cpu(cpu, policy->cpus)  cpufreq\_remove\_update\_util\_hook(cpu);-------A  synchronize\_rcu();---------------B  if (!policy->fast\_switch\_enabled) {---------------C  irq\_work\_sync(&sg\_policy->irq\_work);  kthread\_cancel\_work\_sync(&sg\_policy->work);  } |

A、遍历该sugov policy（cluster）中的所有cpu，调用cpufreq\_remove\_update\_util\_hook注销sugov cpu的调频回调函数

B、sugov\_stop之后可能会调用sugov\_exit来释放该governor所持有的资源，包括update\_util\_data对象。通过synchronize\_rcu函数可以确保之前对update\_util\_data对象的并发访问都已经离开了临界区，从而后续可以安全释放。

C、在不支持fast switch模式的时候，我们需要把pending状态状态的irq work和kthread work处理完毕，为后续销毁线程做准备

5、Sugov的退出

sugov\_exit主要功能是释放申请的资源，具体执行逻辑大致如下：

A、断开cpufreq framework中的cpufreq policy和sugover的关联（即将其governor\_data设置为NULL）

B、调用sugov\_tunables\_free释放可调参数的内存（如果是多个policy共用一个可调参数对象，那么需要通过引用计数来判断是否还有sugov policy引用该对象）

C、调用sugov\_kthread\_stop来消耗用于sugov调频的内核线程（仅用在不支持fast switch场景）

D、调用sugov\_policy\_free释放sugov policy的内存

E、调用cpufreq\_disable\_fast\_switch来禁止本policy上的fast switch。

6、限频处理

从系统角度看，整个限频路径如下：

![](/content/uploadfile/202204/2d5a1650926313.png)

想要发起限频的内核模块A（例如检测到触摸事件后，将min freq拉升到1.2GHz）通过PM Qos模块提供的接口API向指定的cpufreq policy发起限频请求操作（例如freq\_qos\_add\_request、freq\_qos\_update\_request接口）。PM Qos模块会根据这个新的限频请求，并综合之前的所有的限频请求计算当前实际的限频值，如果限频值发生了变化，那么就通知cpufreq core模块frequency limits已经更新（具体的接口形态是notifier\_block）。收到这个通知之后，cpufreq core模块会调用refresh\_frequency\_limits，最后通知到sugov模块调用sugov\_limits。sugov\_limits执行逻辑大致如下：

|  |
| --- |
| if (!policy->fast\_switch\_enabled) {---------------------A  mutex\_lock(&sg\_policy->work\_lock);  cpufreq\_policy\_apply\_limits(policy);  mutex\_unlock(&sg\_policy->work\_lock);  }  sg\_policy->limits\_changed = true;----------------B |

A、对于不支持fast switch的情况下，立刻调用cpufreq\_policy\_apply\_limits函数使用最新的max和min来修正当前cpu频率，同时标记sugov policy中的limits\_changed成员。

B、对于支持fast switch的情况下，仅仅标记sugov policy中的limits\_changed成员即可，并不立刻进行频率修正。后续在调用cpufreq\_update\_util函数进行调频的时候会强制进行一次频率调整。

四、sugov如何进行调频

1、Sugov的频率调整间隔

虽然在调度器中有很多点都会触发cpu utility change的时间，从而会调用governor的callback函数，但是为了避免多度频繁的进行cpu频率调整（例如底层cpufreq驱动最多1ms完成频率切换，那么上次0.5ms连续下发的频率调整命令其实是没有意义的），sugov模块通过sugov\_should\_update\_freq函数来过滤调度器密集下发的频率调整请求：

|  |
| --- |
| if (!cpufreq\_this\_cpu\_can\_update(sg\_policy->policy))----------------A  return false;  if (unlikely(sg\_policy->limits\_changed)) {----------------------B  sg\_policy->limits\_changed = false;  sg\_policy->need\_freq\_update = true;  return true;  }  delta\_ns = time - sg\_policy->last\_freq\_update\_time;  return delta\_ns >= sg\_policy->freq\_update\_delay\_ns;--------------------C |

A、CPU a能否调整不在一个cluster中另外一个CPU b的频率？不同的硬件平台是不一样的，有些平台上调整CPU频率的寄存器是per CPU的，因此只能调整自己CPU（cluster）的频率。这时候就需要判断一下当前发起的cpu是否在当前准备进行频率调整的policy之中，如果不在，那么就没有必要继续下去了，毕竟到了底层也无法完成频率调整，还不如一开始就结束，节省后续相关的计算。对于ARM平台不存在这样的限制，因此其cpufreq policy的dvfs\_possible\_from\_any\_cpu成员都是true的，用来标记任何的cpu都可以修改其他cpu的频率。这种情况下，也不是全部长驱直入的，需要看看当前CPU是否处于offline的过程中，如果是那么也不能进行频率调整。

B、调度器有可能会以非常密集的间隔来上报cpu util change事件，为防止没有意义的调频，sugov会进行拦截。然而还是有一些特殊情况：当该cpufreq policy的频率上下限发生变更的时候，就会忽略时间间隔的限制。此外，当cpu util的变更是由于deadline的带宽需求引发的，那么同样也需要忽略时间间隔的限制，具体参考ignore\_dl\_rate\_limit函数。

C、这里是正常的sugov在调频时间间隔的限制逻辑。

2、计算cpu utility

schedutil\_cpu\_util是计算cpu utility的主函数，大概的逻辑过程如下：

|  |
| --- |
| if (!uclamp\_is\_used() &&----------------A  type == FREQUENCY\_UTIL && rt\_rq\_is\_runnable(&rq->rt)) {  return max;  }  irq = cpu\_util\_irq(rq);-----------------B  if (unlikely(irq >= max))  return max; |

A、Cpu utility应该是综合考虑CPU上各个调度类（cfs、rt、dl）以及irq的utility。然而为了平衡性能和功耗，在某些场景下（例如手机场景），用户空间会通过uclamp机制对用户体验相关的线程进行boost，或者对后台线程进行频率限制。这样，CPU频率的选择并不能完全从负载跟踪模块得到的utility去换算，而是要综合考虑用户空间的uclamp限制。在过去，没有uclamp功能，在计算调频utility的场景下（FREQUENCY\_UTIL），只要rq上有rt任务，那么就上报该CPU的最大可能的utility。如果系统使能了uclamp功能并且的确对cfs或者rt任务进行了uclamp，那么我们将采用更精细的频率控制方法（下面会讲）。

B、如果该CPU处理了过多的中断handler（包括软中断），irq负载已经高过CPU的最大算力，那么直接提满频。

|  |
| --- |
| util = util\_cfs + cpu\_util\_rt(rq);----------------------A  if (type == FREQUENCY\_UTIL)  util = uclamp\_rq\_util\_with(rq, util, p);  dl\_util = cpu\_util\_dl(rq);-----------------B  if (util + dl\_util >= max)  return max;  if (type == ENERGY\_UTIL)  util += dl\_util; |

A、这里累加了cfs和rt任务的utility，并通根据当前的设置进行clamp。关于uclamp机制，后续我们会其他的文章详细描述，敬请期待。

B、Deadline类型的任务可以从两个不同的层面输出utility，一种是PELT算法下的utility，另外一个是带宽视角下的utility。一般而言，PELT dl utility不应该算入来提频，但这里只是为了判断是否cfs rt和dl已经耗尽了所有的CPU算力，如果是这样，那么直接返回cpu utility的最大值。如果本次调用schedutil\_cpu\_util是为了计算能耗（ENERGY\_UTIL），那么utility需要累计deadline类型的任务，毕竟只要运行就会消耗CPU的能量。

|  |
| --- |
| util = scale\_irq\_capacity(util, irq, max);----------A  util += irq;  if (type == FREQUENCY\_UTIL)----------------B  util += cpu\_bw\_dl(rq);  return min(max, util); |

A、各种类型任务的PELT跟踪下的utility是在一个timeline下（基于pelt clock），并且窗口也是对齐的，因此它们可以相加起来。Irq utility的计算和这些task utility的计算形式是类似的，但是timeline和窗口并不是对齐的，因此不能直接相加。Irq time并没有计算进入task clock，因此task utility计算值会稍微大一些。这个概念有点类似irq会偷走一部分的cpu算力，从而让其capacity没有那么大。这里通过scale\_irq\_capacity对任务的utility进行调整。

B、至此，util变量保存了cfs和rt的利用率信息（经过clamp和irq的调整），这里再累加上dl任务的utility。对于频率调整的util，dl任务采用了带宽视角的utility，作为CPU输出算力的最小值，毕竟CPU算力至少要满足dl任务的带宽需要。

3、iowait boost

在sugov中内嵌了iowait boost算法，主要是为了解决轻载下的io吞吐量下降的问题：

![](/content/uploadfile/202204/ad191650926389.png)

在轻载场景下，CPU上往往只有一个重载io的任务在运行。假设目前处于较高的CPU频率状态，这时候CPU的busy的时间比较短，utility比较轻，因此sugov就会将CPU频率降低，从而拉长了任务运行时间，这样，单位时间内下发的io command数量就会降低，从而拉低了io吞吐量。

iowait boost算法过程如下：

（1）当enqueue一个处于iowait状态任务的时候，通过cpufreq\_update\_util来通知sugov模块发生了一次SCHED\_CPUFREQ\_IOWAIT类型的cpu utility变化。

（2）在sugov callback函数中调用sugov\_iowait\_boost来更新该CPU的io wait boost状态。具体更新的规则如下表所示：

|  |  |
| --- | --- |
| 条件 | Iowait boost的utility |
| 第一次从io wait状态唤醒中唤醒 | Iowait boost值设定为IOWAIT\_BOOST\_MIN，目前设定为128 |
| 已经处于io wait boost状态，但是随后的io wait wakeup并没有连续到来，而是超过了一个tick（即io操作没有那么频繁）才来 | 重置Iowait boost值设定为IOWAIT\_BOOST\_MIN |
| 已经处于io wait boost状态，但是随后没有新的io wait wakeup到来（即停止了io操作） | 一个tick之后，将Iowait boost值设定为0，结束iowait boost |
| 已经处于io wait boost状态，并且随后的io wait wakeup密集的出现（即短期内有大量的io操作发生） | 把Iowait boost值翻倍，直到1024（即SCHED\_CAPACITY\_SCALE） |

（3）在调用sugov\_get\_util函数获取cpu utility之后，通过调用sugov\_iowait\_apply来应用iowait boost的utility值。如果Iowait boost之后的utility比较大的话，那么用iowait boost utility来替代之前计算的cpu utility。顺便说一句，如果在一个tick内没有联系的pending的iowait boost，那么Iowait boost值会衰减，也就是说，只有在大量io下发的场景中，CPU频率才会维持较高的boost值。

4、计算cluster的utility

对于只有一个cpu的cluster，cpu utility就是cluster的utility，对于cluster内有多个cpu的情况，我们需要遍历cluster中的cpu，找到cluster utility（用来映射cluster频率的utility），具体的代码实现在sugov\_next\_freq\_shared函数中，如下：

|  |
| --- |
| for\_each\_cpu(j, policy->cpus) {  j\_util = sugov\_get\_util(j\_sg\_cpu);------------A  j\_max = j\_sg\_cpu->max;  if (j\_util \* max > j\_max \* util) {-------------B  util = j\_util;  max = j\_max;  }  } |

A、获取该CPU的utility和CPU的最大算力

B、大部分的情况下，一个cluster中的CPU其微架构是一样的，因此其最大算力也是一样的，这时候就是选择cpu utility最大的那个就OK了。如果cluster中的CPU微架构不同，那么需要对比的是（utility/capacity）

5、如何将cluster utility映射到具体的频率？

通过get\_next\_freq函数，我们可以将cluster上指定的utility映射到具体的频率上去：

|  |
| --- |
| freq = map\_util\_freq(util, freq, max);---------A  if (freq == sg\_policy->cached\_raw\_freq && !sg\_policy->need\_freq\_update)  return sg\_policy->next\_freq;-----------B  sg\_policy->cached\_raw\_freq = freq;  return cpufreq\_driver\_resolve\_freq(policy, freq);-----C |

A、我们期望utility能够匹配当前算力，什么叫匹配？我们这里采用了20%的余量，即当前utility耗尽80%的目标算力即可（目标算力就是调整到目标频率CPU输出的算力）

B、这里通过map\_util\_freq映射出来的目标频率并不是最终CPU调整到的频率，不过如果这里计算的频率如果和上次缓存的目标频率一样的话，那么其底层驱动实际调整的频率应该也是一样的，因此这里不会再调用cpufreq\_driver\_resolve\_freq函数来确定实际的CPU频率，直接返回sg\_policy->next\_freq。

C、底层驱动（硬件）不能支持“无级变速”，因此CPU频率是一张表格，有固定的档位，每一档对应一个CPU频率。在计算得到目标频率之后，还需要将其解析为底层驱动支持的频点。具体的方式有很多种，例如取大于目标频率的最小频点、取小于该目标频率的最大频点，或者最靠近的频点。

6、发起调频

至此，我们已经获得了需要调频的频点，下面就是通知底层驱动软件进行实际的频率调整了。对于单cpu的cluster而言，调频代码如下：

|  |
| --- |
| if (sugov\_cpu\_is\_busy(sg\_cpu) && next\_f < sg\_policy->next\_freq) {-----A  next\_f = sg\_policy->next\_freq;  sg\_policy->cached\_raw\_freq = cached\_freq;  }  if (sg\_policy->policy->fast\_switch\_enabled) {------B  sugov\_fast\_switch(sg\_policy, time, next\_f);  } else {  raw\_spin\_lock(&sg\_policy->update\_lock);  sugov\_deferred\_update(sg\_policy, time, next\_f);-------C  raw\_spin\_unlock(&sg\_policy->update\_lock);  } |

A、如果本次是想要调降频率，但是最近该CPU并没有进入idle状态（runqueue上仍然有任务），这时候立刻调降频率有点为时过早，我们先保持频率不变

B、快速切换频率路径。由于cluster只有一个cpu，而且调用sugov\_update\_single已经获取了rq lock，因此sugov\_fast\_switch不需要其他手段来控制并发。

C、慢速切换频率路径。在这个场景下，仅仅rq lock不足以保护并发，因为慢速切换频率需要在sugov kthread上下文进行实际的调频动作，因此需要使用sg\_policy->update\_lock。

对于sugov\_update\_shared，其频率切换的逻辑和sugov\_update\_single类似，只不过sugov policy数据会在多个cpu上并发（无论是快速还是慢速切换频率路径），因此统一使用了update\_lock来控制并发。

五、小结

Schedutil governor是标准linux缺省的cpufreq governor，它主要是hook在调度器的负载跟踪模块，当cpu的负载发生变化的时候就会驱动一次调频流程。通过遍历cluster中所有CPU，找到最大的负载来映射到target frequency。底层驱动会根据这个target frequency并结合CPU频率表选择一个最适合的频率设定下去。Schedutil governor虽然是一个优秀的governor，但是在移动平台上它还是有各种各样的缺点。目前各大厂商的工程师也正在优化cpufreq governor，也欢迎热爱技术的你积极参与。

参考文献：

1、内核源代码

2、linux-5.10.61\Documentation\scheduler\\*

本文首发在“内核工匠”微信公众号，欢迎扫描以下二维码关注公众号获取最新Linux技术分享：

![](/content/uploadfile/202111/b9c21636066902.png)
