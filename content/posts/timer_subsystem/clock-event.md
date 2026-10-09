---
title: "Linux时间子系统之（十六）：clockevent"
date: 2014-12-09T19:56:16+08:00
url: "/timer_subsystem/clock-event.html"
gid: "118"
emlog_type: "blog"
summary: "clockevent模块的代码位于linux/kernel/time/clockevents.c，是用来管理系统中的能够触发中断的timer硬件资源的一个模块，该模块的功能分成四个部分： 1）向上层的其它driver（我们称之clock event user）提供操作clock event的通用API。 2） 实现clock event控制的通用逻辑，这部分和硬件无关，我们也称之clock eve"
author: "linuxer"
category: "时间子系统"
category_alias: "timer_subsystem"
tags: ["clockevent"]
views: 32405
comment_count: 31
aliases:
  - "/timer_subsystem/118.html"
  - "/118.html"
---

一、clock event控制的通用逻辑

1、产生clock event的设备

各种系统的timer硬件形形色色，不过在general clock event device layer，struct clock\_event\_device被来抽象一个可以产生clock event的timer硬件设备，如下：

> struct clock\_event\_device {   
> void (\*event\_handler)(struct clock\_event\_device \*);   
> int (\*set\_next\_event)(unsigned long evt, struct clock\_event\_device \*);   
> int (\*set\_next\_ktime)(ktime\_t expires, struct clock\_event\_device \*);   
> ktime\_t next\_event;   
> u64 max\_delta\_ns;   
> u64 min\_delta\_ns;   
> u32 mult;   
> u32 shift;   
> enum clock\_event\_mode mode;   
> unsigned int features;   
> unsigned long retries;
>
> void (\*broadcast)(const struct cpumask \*mask);   
> void (\*set\_mode)(enum clock\_event\_mode mode, struct clock\_event\_device \*);   
> void (\*suspend)(struct clock\_event\_device \*);   
> void (\*resume)(struct clock\_event\_device \*);   
> unsigned long min\_delta\_ticks;   
> unsigned long max\_delta\_ticks;
>
> const char \*name;   
> int rating;   
> int irq; －－－－－－－－－－－－－使用的IRQ number   
> const struct cpumask \*cpumask; －－－－该clock event device附着在哪一个CPU core上   
> struct list\_head list;   
> struct module \*owner;   
> } \_\_\_\_cacheline\_aligned;

在把目光投向每一个成员之前，我们先聊一聊\_\_\_\_cacheline\_aligned，其实最开始定义这个数据结构的时候没有这个属性，而且struct clock\_event\_device的各个成员也不是这样排列的。为了提高cacheline hit radio，内核工程师对这个数据结构进行的改造，一方面对齐了cache line，另外一方面重排了那些有密切关系的成员（所谓密切关系就是指在代码执行上下文中，如果访问了A成员，有非常大的概率访问B成员）。

event\_handler顾名思义就是产生了clock event的时候调用的handler。一般而言，底层的clock event chip driver会注册中断处理函数，在硬件timer中断到来的时候调用该timer中断handler，而在这个中断handler中再调用event\_handler。

既然是产生clock event的device，那么总是要控制下一次event产生的时间点，我们有两个成员函数完成这个功能：set\_next\_event和set\_next\_ktime。set\_next\_ktime函数可以直接接收ktime作为参数，而set\_next\_event设定的counter的cycle数值。一般的timer硬件都是用cycle值设定会比较方便，当然，不排除有些奇葩可以直接使用ktime（秒、纳秒），这时候clock event device的features成员要打上CLOCK\_EVT\_FEAT\_KTIME的标记。

features成员是描述底层硬件的功能feature的，包括：

> #define CLOCK\_EVT\_FEAT\_PERIODIC 0x000001－－－－－－具备产生周期性event的能力   
> #define CLOCK\_EVT\_FEAT\_ONESHOT 0x000002－－－－－具备产生oneshot类型event的能力   
> #define CLOCK\_EVT\_FEAT\_KTIME 0x000004－－－－－－－上面已经描述了
>
> #define CLOCK\_EVT\_FEAT\_C3STOP 0x000008   
> #define CLOCK\_EVT\_FEAT\_DUMMY 0x000010

CLOCK\_EVT\_FEAT\_C3STOP是一个很有意思的feature：内核中有一个模块叫做cpuidle framework，当没有任务做的时候，cpu会进入idle状态。这种CPU的sleep state叫做C-states，有C1/C2…Cn种states（具体多少种和CPU设计相关），当然不同的状态是在功耗和唤醒时间上进行平衡，CPU睡的越浅，功耗越大，但是能够很快的唤醒。一般而言，在sleep state的CPU可以被local timer唤醒，但是，当CPU进入某个深度睡眠状态的时候，停止了local timer的运作，这时候，local timer将无法唤醒CPU了。

kernel的注释说这是一个x86（64）的功能设计失误（misfeature），不过，在嵌入式平台上，这也可以认为是对功耗的极致追求（ARM 的generic timer也有这个misfeature，呵呵～～）。为了让系统可以继续运作，传说中tick broadcast framework粉墨登场了。struct clock\_event\_device中的broadcast这个callback函数是和clock event广播有关。在per CPU 的local timer硬件无法正常运作的时候，需要一个独立于各个CPU的timer硬件来作为broadcast clock event device。在这种情况下，它可以将clock event广播到所有的CPU core，以此推动各个CPU core上的tick device的运作。当然它不是本文的主要内容，如果有兴趣可以参考本站其他文档。

clock event mode的定义如下：

> enum clock\_event\_mode {   
> CLOCK\_EVT\_MODE\_UNUSED = 0, －－－－－－未使用   
> CLOCK\_EVT\_MODE\_SHUTDOWN, －－－－－－被软件shutdown   
> CLOCK\_EVT\_MODE\_PERIODIC, －－－－－－－工作状态，处于periodic模式，周期性产生event   
> CLOCK\_EVT\_MODE\_ONESHOT, －－－－－－－工作状态，处于one shot模式，event是一次性的   
> CLOCK\_EVT\_MODE\_RESUME, －－－－－－－处于系统resume中   
> };

具体的mode设定是由set\_mode这个callback函数来完成的，毫无疑问，这是需要底层的clock event chip driver需要设定的。虽然定义了这么多mode，实际上底层的硬件未必支持，有些HW timer硬件支持oneshot和periodic的设定，不过有些就不支持（例如：ARM general timer）。具体clock event device如何在各个mode中切换会在tick device的文档中描述。

rating、mult和shift的概念和clocksource中的类似，这里就不描述了。此外很多成员这里也不细述了，在后面的逻辑分析中自然就清晰了。

2、如何组织系统中的clock event device？

相关的全局变量定义如下：

> static LIST\_HEAD(clockevent\_devices);   
> static LIST\_HEAD(clockevents\_released);

clock event device core模块使用两个链表来管理系统中的clock event device，一个是clockevent\_devices链表，该链表中的clock event device都是当前active的device。active的clock device有两种情况，一种是cpu core的current clockevent device，这些device是各个cpu上产生tick的那个clock event device，还有一些active的device由于优先级比较低，当前没有使用，不过可以作为backup的device。另外一个是clockevents\_released链表，这个链表中clock event device都是由于种种原因，无法进入active list，从而挂入了该队列。

二、向上层的其它driver提供操作clock event的通用API

1、设定clock event device的触发event的时间参数

> int clockevents\_program\_event(struct clock\_event\_device \*dev, ktime\_t expires, bool force)   
> {   
> unsigned long long clc;   
> int64\_t delta;   
> int rc;
>
> dev->next\_event = expires; －－－－－－－设定下一次触发clock event的时间   
> if (dev->features & CLOCK\_EVT\_FEAT\_KTIME)－－－－－ －－－－－－－－－－－－－（1）   
> return dev->set\_next\_ktime(expires, dev);
>
> delta = ktime\_to\_ns(ktime\_sub(expires, ktime\_get()));－－－－－ －－－－－－－－－－（2）   
> if (delta <= 0)   
> return force ? clockevents\_program\_min\_delta(dev) : -ETIME; －－－－－－－－－－－（3）
>
> delta = min(delta, (int64\_t) dev->max\_delta\_ns);   
> delta = max(delta, (int64\_t) dev->min\_delta\_ns); －－－－－－－－－－－－－－－－－－（4）
>
> clc = ((unsigned long long) delta \* dev->mult) >> dev->shift; －－－－－－－－－转换成cycle值
>
> rc = dev->set\_next\_event((unsigned long) clc, dev); －－－调用底层driver callback函数进行设定
>
> return (rc && force) ? clockevents\_program\_min\_delta(dev) : rc; －－－－－－－－－－－（5）   
> }

我们先看看该接口函数的参数值：dev指向具体的clock event device，expires参数是设定下一次产生event的时间点，force参数控制在expires设定异常的时候（例如设定在一个过去的时间点上产生event）该函数 的行为，一种是出错返回，另外一种还是进行event的产生，只是设定一个最小的delta。

（1）如果chip driver支持使用ktime的设定（这需要硬件支持，设定了CLOCK\_EVT\_FEAT\_KTIME flag的那些clock event device才支持哦），事情会比较简单，直接调用set\_next\_ktime就搞定了。

（2）对于一个“正常”的clock event device，需要转换成cycle这样的单位。不过在转换成cycle之前，需要先将ktime格式的时间（传入的expires参数就是这样的格式）转换成纳秒这样的时间单位。

（3）delta小于0意味着用户设定的时间点已经是过去的一个时间点，如果强制产生event的话，那么事不宜迟，要立刻产生event，这需要调用clockevents\_program\_min\_delta函数，代码如下：

> static int clockevents\_program\_min\_delta(struct clock\_event\_device \*dev)   
> {   
> unsigned long long clc;   
> int64\_t delta;
>
> delta = dev->min\_delta\_ns; －－－－－－－－－－－－－－－－－－－－－－－－－－－（a）   
> dev->next\_event = ktime\_add\_ns(ktime\_get(), delta); －－－－－－－－－－－－－－－－（b）
>
> if (dev->mode == CLOCK\_EVT\_MODE\_SHUTDOWN)   
> return 0;
>
> dev->retries++; －－－－－－－记录retry的次数   
> clc = ((unsigned long long) delta \* dev->mult) >> dev->shift; －－－－－－转换成cycle值   
> return dev->set\_next\_event((unsigned long) clc, dev); －－－－调用底层driver callback函数进行设定   
> }

（a）在逻辑思维的世界里，你可以想像任意小的时间片段，但是在实现面，这个要收到timer硬件能力的限制。一个输入频率是1Hz的timer硬件，其最小时间粒度就是1秒，如何产生0.1秒的clock event呢？因此，所谓立刻产出也就是在硬件允许的最小的时间点上产生event。在注册clock event device的时候已经设定这个参数了，就是struct clock\_event\_device的min\_delta\_ns这个成员。

（b）ktime\_get函数获取当前的时间点，加上min\_delta\_ns就是下一次要触发event的时间点，struct clock\_event\_device的next\_event 这个成员就是用来记录下一次要触发event的时间点信息的。

（4）有最小值就有最大值，struct clock\_event\_device的max\_delta\_ns这个成员就是设定next event触发的最大时间值。这个最大值是和硬件counter的bit数目有关：如果一个硬件timer最大能表示60秒的时间长度，那么设定65秒后触发clock event是没有意义的，因为这时候counter会溢出，如果强行设定那么硬件实际会在5秒后触发event。同样的，max\_delta\_ns也是在注册clock event device的时候设定了这个参数。

（5）如果调用底层driver callback函数进行实际的cycle设定的时候出错（例如：由于种种原因，在实际设定的时候发现时间点是过去值，如果仍然设定，那么上层软件实际上要等到硬件counter 溢出后在下一个round中才会触发event，实际这时候黄花菜都凉了），并且是强制产生event的话，那么也需要调用clockevents\_program\_min\_delta函数在最小时间点上产生clock event。

2、更换clock event设备

上层的tick device驱动层会根据情况（clock event的精度，是否local cpu的）调用clockevents\_exchange\_device 进行clock event设备的更换，具体代码如下：

> void clockevents\_exchange\_device(struct clock\_event\_device \*old, struct clock\_event\_device \*new)   
> {   
> unsigned long flags;
>
> local\_irq\_save(flags);   
>   
> if (old) { －－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－（1）   
> module\_put(old->owner);   
> clockevents\_set\_mode(old, CLOCK\_EVT\_MODE\_UNUSED);   
> list\_del(&old->list);   
> list\_add(&old->list, &clockevents\_released);   
> }
>
> if (new) { －－－－－－－－－－－－－－－－－－－－－－－－－－－－－－（2）   
> BUG\_ON(new->mode != CLOCK\_EVT\_MODE\_UNUSED);   
> clockevents\_shutdown(new);   
> }   
> local\_irq\_restore(flags);   
> }

（1）旧的clock event device要被替换掉，因此将其模式设定为CLOCK\_EVT\_MODE\_UNUSED，并且从全局clock event device链表中摘下来，挂入clockevents\_released链表

（2）我们要确保新的clock event设备没有被使用，如果新的clock event设备不是CLOCK\_EVT\_MODE\_UNUSED状态，说明其目前被其他的上层软件使用，因此要kernel panic，并且shutdown该clock event device。这是该设备状态是CLOCK\_EVT\_MODE\_SHUTDOWN状态。这里没有插入clockevent\_devices全局链表的动作，主要是因为在调用该函数之前，新的clock event device已经挂入队列了。

三、向底层clockevent chip driver提供的接口

1、配置clock event device

底层的clock event chip driver可以调用clockevents\_config对该设备进行配置。这里的操作类似clocksource中的内容，也就是说调用者输入频率参数，在clockevents\_config中计算struct clock\_event\_device中一些类似mult、shift等成员的配置值：

> void clockevents\_config(struct clock\_event\_device \*dev, u32 freq)   
> {   
> u64 sec;
>
> if (!(dev->features & CLOCK\_EVT\_FEAT\_ONESHOT))－－－－－－－－－－－－－－（1）   
> return;
>
> sec = dev->max\_delta\_ticks;－－－－－－－－－－－－－－－－－－－－－－－－－（2）   
> do\_div(sec, freq);   
> if (!sec)   
> sec = 1;－－－－－限制最小值   
> else if (sec > 600 && dev->max\_delta\_ticks > UINT\_MAX)   
> sec = 600; －－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－（3）
>
> clockevents\_calc\_mult\_shift(dev, freq, sec);－－－－－－－－－－－－－－－－－－（4）   
> dev->min\_delta\_ns = cev\_delta2ns(dev->min\_delta\_ticks, dev, false);－－－－－－－（5）   
> dev->max\_delta\_ns = cev\_delta2ns(dev->max\_delta\_ticks, dev, true);   
> }

（1）底层的硬件驱动知道自己的能力，可以通过struct clock\_event\_device中的features成员宣称自己的功能：CLOCK\_EVT\_FEAT\_PERIODIC说明该硬件timer可以产生周期性的clock event，CLOCK\_EVT\_FEAT\_ONESHOT说明自己只能产生one shot类型的clock event。如果能产生one shot类型的event，那么即便是硬件不支持周期性的clock event，其实上层的软件可以通过不断设定next event的方法来模拟周期性的clock event。但是如果只是支持周期性的clock event就有些麻烦了，这时候是无法模拟one shot类型的event。也就是说，在这种情况下，整个系统必须有周期性tick，同时，系统无法支持高精度timer和dynamic tick的情况。在这样的硬件条件下，后续的配置是没有意义的，因此直接return。

（2）底层的硬件驱动需要设定max\_delta\_ticks和min\_delta\_ticks。需要注意的是这里的tick不是system tick，而是输入硬件timer的clock tick，其实就是可以设定最大和最小cycle数目。这个cycle数目除以freq就是时间值，单位是秒。

（3）又是600秒，是否似曾相识。我们在clock source那篇文档中已经介绍过了，这里就不再赘述

（4）根据输入频率和最大的秒数可以计算出clock event的mult和shift这两个成员的数值，具体计算过程在clock source那篇文档中已经介绍过了，这里就不再赘述。

（5）计算min\_delta\_ticks和max\_delta\_ticks对应的ns值。

2、注册clock event device

底层的timer硬件驱动会调用clockevents\_register\_device函数向系统注册clock event device，代码如下：

> void clockevents\_register\_device(struct clock\_event\_device \*dev)   
> {   
> unsigned long flags;
>
> if (!dev->cpumask) {－－－－－－－－－－－－－－－－－－－－－－－－－－－（1）   
> WARN\_ON(num\_possible\_cpus() > 1);   
> dev->cpumask = cpumask\_of(smp\_processor\_id());   
> }
>
> raw\_spin\_lock\_irqsave(&clockevents\_lock, flags); －－－－－－－－－－－－－－（2）
>
> list\_add(&dev->list, &clockevent\_devices); －－－－加入clock event设备全局列表   
> tick\_check\_new\_device(dev); －－－－－－－－－－－－－－－－－－－－－－－（3）   
> clockevents\_notify\_released(); －－－－－－－－－－－－－－－－－－－－－－（4）
>
> raw\_spin\_unlock\_irqrestore(&clockevents\_lock, flags);   
> }

（1）clock event device的cpumask指明该设备为哪一个CPU工作，如果没有设定并且cpu的个数大于1的时候要给出warning信息并进行设定（设定为当前运行该代码的那个CPU core）。在multi core的环境下，底层driver在调用该接口函数注册clock event设备之前就需要设定cpumask成员，毕竟一个timer硬件附着在哪一个cpu上底层硬件最清楚，这里仅仅是亡羊补牢（毕竟我们还是希望代码不要随随便便就kernel panic了，尽量让代码执行下去）。

（2）考虑到来自多个CPU上的并发，这里使用spin lock进行保护。关闭本地中断，可以防止来自本cpu上的并发操作。

（3）调用tick\_check\_new\_device函数，让上层软件知道底层又注册一个新的clock device，当然，是否上层软件要使用这个新的clock event device是上层软件的事情，clock event device driver这个层次完成描述自己能力这部分代码就OK了。tick device相关内容请参考本站其他文档。

（4）如果上层软件想要使用新的clock event device的话（tick\_check\_new\_device函数中有可能会进行此操作），它会调用clockevents\_exchange\_device函数（可以参考上面的描述）。这时候，旧的clock event会被从clockevent\_devices链表中摘下，挂到clockevents\_released队列中。在clockevents\_notify\_released函数中，会将old clock event device重新挂入clockevent\_devices，并调用tick\_check\_new\_device函数。

3、配置并注册clock event device

是上面两个接口函数的综合体，这里不再详细描述。

四、用户空间接口

1、sysfs接口初始化

在系统初始化的时候会调用clockevents\_init\_sysfs函数（呵呵～～～对于clock source，这个函数名字是init\_clocksource\_sysfs，很显然不是一个人的风格，我喜欢clockevents\_sysfs\_init和clocksource\_sysfs\_init这种函数定义风格）来初始化clock event device layer的sys file system接口，如下：

> static int \_\_init clockevents\_init\_sysfs(void)   
> {   
> int err = subsys\_system\_register(&clockevents\_subsys, NULL); －－注册clock event这种bus type
>
> if (!err)   
> err = tick\_init\_sysfs();   
> return err;   
> }

该说的在[clocksource](/timer_subsystem/clocksource.html)那份文档中都描述了，这里直接不再赘述，重点关注tick\_init\_sysfs函数：

> static int \_\_init tick\_init\_sysfs(void)   
> {   
> int cpu;
>
> for\_each\_possible\_cpu(cpu) {－－－－－－－－－－遍历各个CPU的clock event device   
> struct device \*dev = &per\_cpu(tick\_percpu\_dev, cpu);－－－－－－－－－－－－－－（1）   
> int err;
>
> dev->id = cpu;   
> dev->bus = &clockevents\_subsys;   
> err = device\_register(dev);－－－－－－－－－－－－－－－－－－－－－－－－－－（2）   
> if (!err)   
> err = device\_create\_file(dev, &dev\_attr\_current\_device);－－－－－－－－－－－－（3）   
> if (!err)   
> err = device\_create\_file(dev, &dev\_attr\_unbind\_device);   
> if (err)   
> return err;   
> }   
> return tick\_broadcast\_init\_sysfs(); －－－－－－－－－－－－－－－－－－－－－－－（4）   
> }

（1）我们始终还是要回归统一模型的三件套，bus type，device和driver。现在有了clock event bus type，还缺少device。在clock source中，由于它是全局的，属于所有CPU core的，因此我们定义了一个device就OK了。对于clock event，我们需要为每一个CPU定义一个device，如下：

> static DEFINE\_PER\_CPU(struct device, tick\_percpu\_dev);

是否需要定义clock event device对应的driver呢？本来定义device和driver的目的是让它们在适当的时机（bus type的match函数）相遇，相知（调用driver的probe函数）。对于clock event device而言，是不需要定义driver的，因为设备树提供了其他的方法来进行具体底层chip级别的初始化（具体可以参考[ARM generic timer驱动](/timer_subsystem/armgeneraltimer.html)中的描述）。

还有一点需要注意，实际上，每一个硬件设备都是设备模型中的一个device，不过，在clock event device这个场景下，实际上系统并不是为每一个timer硬件定义一个device，而仅仅是为每一个当前active（作为tick device那个clock event device）的clockevent设备定义了一个device数据结构，有空的时候大家可以思考一下这个问题。

（2）调用device\_register就可以把所有的clock event device注册到系统中，统一设备模型会帮我们做一切事情。

（3）device\_register之后，每个clock event device体现为一个sysfs中的目录，我们还需要为这个目录增加一些属性文件。定义如下：

> static DEVICE\_ATTR(current\_device, 0444, sysfs\_show\_current\_tick\_dev, NULL);
>
> static DEVICE\_ATTR(unbind\_device, 0200, NULL, sysfs\_unbind\_tick\_dev);

（4）除了per cpu的device，还有一个broadcast device，定义如下：

> static struct device tick\_bc\_dev = {   
> .init\_name = "broadcast",   
> .id = 0,   
> .bus = &clockevents\_subsys,   
> };

这个device在tick\_broadcast\_init\_sysfs函数中调用device\_register注册到系统，并创建了dev\_attr\_current\_device的属性。和per cpu device不同的是：没有提供用户空间的unbind操作，也就是说，userspace无法unbind当前的broadcast clock event device。

2、属性文件操作：显示current tick device

读clock event device的current\_device属性文件

> static ssize\_t sysfs\_show\_current\_tick\_dev(struct device \*dev, struct device\_attribute \*attr, char \*buf)   
> {   
> struct tick\_device \*td;   
> ssize\_t count = 0;
>
> raw\_spin\_lock\_irq(&clockevents\_lock);   
> td = tick\_get\_tick\_dev(dev); －－－－获取tick device   
> if (td && td->evtdev)   
> count = snprintf(buf, PAGE\_SIZE, "%s\n", td->evtdev->name);   
> raw\_spin\_unlock\_irq(&clockevents\_lock);   
> return count;   
> }

一个active的clock event device对应的tick device有两种情况，一种是per cpu的tick device，驱动系统运作。另外一种是broadcast tick device，这些内容留在在tick device部分描述吧。

3、属性文件操作：unbind tick device

一个tick device总是绑定一个属于该cpu core并且精度最高的那个clock event device。通过sysfs的接口可以解除这个绑定。如果解除绑定的那个clock event device是unused，可以直接从clockevent\_devices全局链表中删除。如果该设备当前使用中，那么需要找到一个替代的clock event device。如果找不到一个替代的clock event device，那么不能unbind当前的device，返回EBUSY。具体的代码逻辑就不分析，大家可以自己阅读代码理解。

*原创文章，转发请注明出处。蜗窝科技*

/timer_subsystem/clock-event.html
