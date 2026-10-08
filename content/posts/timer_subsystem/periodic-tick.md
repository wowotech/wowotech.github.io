---
title: "Linux时间子系统之（十二）：periodic tick"
date: 2014-12-11T18:59:02+08:00
url: "/timer_subsystem/periodic-tick.html"
gid: "121"
emlog_type: "blog"
summary: "tick device layer是clock event core模块的用户，tick device layer利用clock event \r\ncore模块提供的接口实现了各种tick device功能：周期性tick、tickless mode、broadcast \r\ntick等。本文从最简单的周期性tick开始，描述tick device的基本概念以及周期性tick的工作原理。"
author: "linuxer"
category: "时间子系统"
category_alias: "timer_subsystem"
tags: ["周期性tick", "periodic", "tick"]
views: 28324
comment_count: 7
aliases:
  - "/timer_subsystem/121.html"
  - "/121.html"
---

一、tick device概念介绍

1、数据结构

在内核中，使用struct tick\_device来抽象系统中的tick设备，如下：

> struct tick\_device {   
> struct clock\_event\_device \*evtdev;   
> enum tick\_device\_mode mode;   
> };

从上面的定义就可以看出：所谓tick device其实就是工作在某种模式下的clock event设备。工作模式体现在tick device的mode成员，evtdev指向了和该tick device关联的clock event设备。

tick device的工作模式定义如下：

> enum tick\_device\_mode {   
> TICKDEV\_MODE\_PERIODIC,   
> TICKDEV\_MODE\_ONESHOT,   
> };

tick device可以工作在两种模式下，一种是周期性tick模式，另外一种是one shot模式。one shot模式主要和tickless系统以及高精度timer有关，会在另外的文档中描述，本文主要介绍periodic mode。

2、tick device的分类以及和CPU的关系

（1） local tick device。在单核系统中，传统的unix都是在tick驱动下进行任务调度、低精度timer触发等，在多核架构下，系统为每一个cpu建立了一个tick device，如下：

> DEFINE\_PER\_CPU(struct tick\_device, tick\_cpu\_device);

local tick device的clock event device应该具备下面的特点：

（a）该clock event device对应的HW timer必须是和该CPU core是有关联的的（也就是说，该hw timer的中断是可以送达到该CPU core的）。struct clock\_event\_device 有一个cpumask成员，它可以指示该clock event device为哪一个或者哪几个CPU core工作。如果采用ARM generic timer的硬件，其HW timer总是为一个CPU core服务的，我们称之为per cpu timer。

（b）该clock event device支持one shot模式，并且精度最高（rating最大）

（2）global tick device。具体定义如下：

> int tick\_do\_timer\_cpu \_\_read\_mostly = TICK\_DO\_TIMER\_BOOT;

有些任务不适合在local tick device中处理，例如更新jiffies，更新系统的wall time，更新系统的平均负载（不是单一CPU core的负载），这些都是系统级别的任务，只需要在local tick device中选择一个作为global tick device就OK了。tick\_do\_timer\_cpu指明哪一个cpu上的local tick作为global tick。

（3）broadcast tick device，定义如下：

> static struct tick\_device tick\_broadcast\_device;

我们会单独一份文档描述它，这里就不再描述了。

二、初始化tick device

1、注册一个新的clock event device的时候，tick device layer要做什么？

在[clock event device](/timer_subsystem/clock-event.html)的文章中，我们知道：底层的timer硬件驱动在初始化的时候会注册clock event device，在注册过程中就会调用tick\_check\_new\_device函数来看看是否需要进行tick device的初始化，如果已经已经初始化OK的tick device是否有更换更高精度clock event device的需求。代码如下：

> void tick\_check\_new\_device(struct clock\_event\_device \*newdev)   
> {   
> struct clock\_event\_device \*curdev;   
> struct tick\_device \*td;   
> int cpu;
>
> cpu = smp\_processor\_id();－－－－－－－－－－－－－－－－－－－－－－－－－－－（1）   
> if (!cpumask\_test\_cpu(cpu, newdev->cpumask)) goto out\_bc;
>
> td = &per\_cpu(tick\_cpu\_device, cpu);－－－获取当前cpu的tick device   
> curdev = td->evtdev; －－－目前tick device正在使用的clock event device
>
> if (!tick\_check\_percpu(curdev, newdev, cpu))－－－－－－－－－－－－－－－－－－－（2）   
> goto out\_bc;
>
> if (!tick\_check\_preferred(curdev, newdev))－－－－－－－－－－－－－－－－－－－－（3）   
> goto out\_bc;
>
> if (!try\_module\_get(newdev->owner)) －－－－－增加新设备的reference count   
> return;
>
> if (tick\_is\_broadcast\_device(curdev)) { －－－－－－－－－－－－－－－－－－－－－－（4）   
> clockevents\_shutdown(curdev);   
> curdev = NULL;   
> }   
> clockevents\_exchange\_device(curdev, newdev); －－－通知clockevent layer   
> tick\_setup\_device(td, newdev, cpu, cpumask\_of(cpu)); －－－－－－－－－－－－－－－（5）   
> if (newdev->features & CLOCK\_EVT\_FEAT\_ONESHOT) －－－其他文档中描述   
> tick\_oneshot\_notify();   
> return;
>
> out\_bc:   
> tick\_install\_broadcast\_device(newdev); －－－－其他文档中描述   
> }

（1）是否是为本CPU服务的clock event device？如果不是，那么不需要考虑per cpu tick device的初始化或者更换该cpu tick device的clock event device。当然，这是还是可以考虑用在broadcast tick device的。

（2）第二个关卡是per cpu的检查。如果检查不通过，那么说明这个新注册的clock event device和该CPU不来电，不能用于该cpu的local tick。如果注册的hw timer都是cpu local的（仅仅属于一个cpu，这时候该clock event device的cpumask只有一个bit被set），那么事情会比较简单。然而，事情往往没有那么简单，一个hw timer可以服务多个cpu。我们这里说HW timer服务于某个cpu其实最重要的是irq是否可以分发到指定的cpu上。我们可以看看tick\_check\_percpu的实现：

> static bool tick\_check\_percpu(struct clock\_event\_device \*curdev,   
> struct clock\_event\_device \*newdev, int cpu)   
> {   
> if (!cpumask\_test\_cpu(cpu, newdev->cpumask))－－－－－－－－－－－－－－－－－－－（a）   
> return false;   
> if (cpumask\_equal(newdev->cpumask, cpumask\_of(cpu)))－－－－－－－－－－－－－－－（b）   
> return true;   
> if (newdev->irq >= 0 && !irq\_can\_set\_affinity(newdev->irq))－－－－－－－－－－－－－－（c）   
> return false;   
> if (curdev && cpumask\_equal(curdev->cpumask, cpumask\_of(cpu)))－－－－－－－－－－（d）   
> return false;   
> return true;   
> }

（a）判断这个新注册的clock event device是否可以服务该CPU，如果它根本不鸟这个cpu那么不用浪费时间了。

（b）判断这个新注册的clock event device是否只服务该CPU。如果这个clock event device就是服务该cpu的，那么别想三想四了，这个clock event device就是你这个CPU的人了。

（c）如果能走到这里，说明该clock event device可以服务多个CPU，指定的cpu（作为参数传递进来）只是其中之一而已，这时候，可以通过设定irq affinity将该clock event device的irq定向到该cpu。当前，前提是可以进行irq affinity的设定，这里就是进行这样的检查。

（d）走到这里，说明该新注册的clock event device是可以进行irq affinity设定的。我们可以通过修改irq affinity让该hw timer服务于这个指定的CPU。恩，听起来有些麻烦，的确如此，如果当前CPU的tick device正在使用的clock event device就是special for当前CPU的（根本不鸟其他CPU），有如此专情的clock event device，夫复何求，果断拒绝新注册的设备。

（3）程序来到这里，说明tick\_check\_percpu返回true，CPU和该clock event device之间的已经是眉目传情了，不过是否可以入主，就看该cpu的原配是否有足够强大的能力（精度和特性）。tick\_check\_preferred代码如下：

> static bool tick\_check\_preferred(struct clock\_event\_device \*curdev,   
> struct clock\_event\_device \*newdev)   
> {   
> if (!(newdev->features & CLOCK\_EVT\_FEAT\_ONESHOT)) {－－－－－－－－－－－－－－（a）   
> if (curdev && (curdev->features & CLOCK\_EVT\_FEAT\_ONESHOT))   
> return false;   
> if (tick\_oneshot\_mode\_active())   
> return false;   
> }
>
> return !curdev ||   
> newdev->rating > curdev->rating ||   
> !cpumask\_equal(curdev->cpumask, newdev->cpumask);－－－－－－－－－－－－－（b）   
> }

（a）首先进行one shot能力比拼。如果新的clock event device没有one shot能力而原配有，新欢失败。如果都没有one shot的能力，那么要看看当前系统是否启用了高精度timer或者tickless。本质上，如果clock event device没有oneshot功能，那么高精度timer或者tickless都是处于委曲求全的状态，如果这样，还是维持原配的委曲求全的状态，新欢失败

（b）如果current是NULL的话，事情变得非常简单，当然是新来的这个clock event device胜出了（这时候，后面的比较都没有意义了）。如果原配存在的话，那么可以看rating，如果新来的精度高，那也选择新来的clock event device。是否精度低就一定不选新的呢？也不是，新设备还是有机会力挽狂澜的：如果新来的是local timer，而原配是非local timer，这时候，也可以考虑选择新的，毕竟新来的clock event device是local timer，精度低一些也没有关系。

当tick\_check\_percpu返回true的时候有两种情况：一种是不管current是什么状态，新设备是CPU的local timer（只为这个cpu服务）。另外一种情况是新设备不是CPU的local timer，当然原配也没有那么专一。

我们先看看第一种情况：如果cpumask\_equal返回true，那么说明原配也是local timer，那么没有办法了，谁的rating高就选谁。如果cpumask\_equal返回false，那么说明原配不是local timer，那么即便新来的rating低一些也还是优先选择local timer。

我们再看看第二种情况：这里我绝对逻辑有问题，不知道是代码的问题还是我还没有考虑清楚，先TODO吧。

（4）OK，经过复杂的检查，我们终于决定要用这个新注册的clock event device来替代current了（当然，也有可能current根本不存在）。在进行替换之前，我们还有检查一下current是否是broadcast tick device，如果是的话，还不能将其退回clockevents layer，仅仅是设定其状态为shutdown。curdev = NULL这一句很重要，在clockevents\_exchange\_device函数中，如果curdev == NULL的话，old device将不会从全局链表中摘下，挂入clockevents\_released链表。

（5）setup tick device，参考下一节描述。

2、如何Setup 一个 tick device？

所谓setup一个tick device就是对tick device心仪的clock event设备进行设置，并将该tick device的evtdev指向新注册的这个clock event device，具体代码如下：

> static void tick\_setup\_device(struct tick\_device \*td,   
> struct clock\_event\_device \*newdev, int cpu,   
> const struct cpumask \*cpumask)   
> {   
> ktime\_t next\_event;   
> void (\*handler)(struct clock\_event\_device \*) = NULL;
>
> if (!td->evtdev) {   
> if (tick\_do\_timer\_cpu == TICK\_DO\_TIMER\_BOOT) {－－－－－－－－－－－－－－（1）   
> ……   
> }
>
> td->mode = TICKDEV\_MODE\_PERIODIC;－－－－－－－－－－－－－－－－－－（2）   
> } else {   
> handler = td->evtdev->event\_handler;   
> next\_event = td->evtdev->next\_event;   
> td->evtdev->event\_handler = clockevents\_handle\_noop; －－－－－－－－－－－－（3）   
> }
>
> td->evtdev = newdev; －－－－－终于修成正果了，呵呵
>
> if (!cpumask\_equal(newdev->cpumask, cpumask)) －－－－－－－－－－－－－－－（4）   
> irq\_set\_affinity(newdev->irq, cpumask);
>
> if (tick\_device\_uses\_broadcast(newdev, cpu)) －－－－－－－留给broadcast tick文档吧   
> return;
>
> if (td->mode == TICKDEV\_MODE\_PERIODIC)   
> tick\_setup\_periodic(newdev, 0); －－－－－－－－－－－－－－－－－－－－－－（5）   
> else   
> tick\_setup\_oneshot(newdev, handler, next\_event); －－－－－其他文档描述   
> }

（1）在multi core的环境下，每一个CPU core都自己的tick device（可以称之local tick device），这些tick device中有一个被选择做global tick device，负责维护整个系统的jiffies。如果该tick device的是第一次设定，并且目前系统中没有global tick设备，那么可以考虑选择该tick设备作为global设备，进行系统时间和jiffies的更新。更细节的内容请参考timekeeping文档。

（2）在最初设定tick device的时候，缺省被设定为周期性的tick。当然，这仅仅是初始设定，实际上在满足一定的条件下，在适当的时间，tick device是可以切换到其他模式的，下面会具体描述。

（3）旧的clockevent设备就要退居二线了，将其handler修改为clockevents\_handle\_noop。

（4）如果不是local timer，那么还需要调用irq\_set\_affinity函数，将该clockevent的中断，定向到本CPU。

（5）tick\_setup\_periodic的代码如下（注：下面的代码分析中暂不考虑broadcast tick的情况）：

> void tick\_setup\_periodic(struct clock\_event\_device \*dev, int broadcast)   
> {   
> tick\_set\_periodic\_handler(dev, broadcast); －－－－设定event handler为tick\_handle\_periodic
>
> if ((dev->features & CLOCK\_EVT\_FEAT\_PERIODIC) && !tick\_broadcast\_oneshot\_active()) {   
> clockevents\_set\_mode(dev, CLOCK\_EVT\_MODE\_PERIODIC);－－－－－－－－－（a）   
> } else {   
> unsigned long seq;   
> ktime\_t next;
>
> do {   
> seq = read\_seqbegin(&jiffies\_lock);   
> next = tick\_next\_period; －－－－－获取下一个周期性tick触发的时间   
> } while (read\_seqretry(&jiffies\_lock, seq));
>
> clockevents\_set\_mode(dev, CLOCK\_EVT\_MODE\_ONESHOT); －－－模式设定
>
> for (;;) {   
> if (!clockevents\_program\_event(dev, next, false)) －－－－program next clock event   
> return;   
> next = ktime\_add(next, tick\_period); －－－－－－计算下一个周期性tick触发的时间   
> }   
> }   
> }

（a）如果底层的clock event device支持periodic模式，那么直接调用clockevents\_set\_mode设定模式就OK了

（b）如果底层的clock event device不支持periodic模式，而tick device目前是周期性tick mode，那么要稍微复杂一些，需要用clock event device的one shot模式来实现周期性tick。

三、周期性tick的运作

1、从中断到clock event handler

一般而言，底层的clock event chip driver会注册中断，我们用ARM generic timer驱动为例，注册的代码如下：

> …
>
> err = request\_percpu\_irq(ppi, arch\_timer\_handler\_phys, "arch\_timer", arch\_timer\_evt);
>
> ……

具体的timer的中断handler如下：

> static irqreturn\_t arch\_timer\_handler\_phys\_mem(int irq, void \*dev\_id)   
> {
>
>       ……   
>         evt->event\_handler(evt);   
>    ……
>
> }

也就是说，在timer interrupt handler中会调用clock event device的event handler，而在周期性tick的场景下，这个event handler被设定为tick\_handle\_periodic。

2、周期性tick的clock event handler的执行分析

由于每个cpu都有自己的tick device，因此，在每个cpu上，每个tick到了的时候，都会调用tick\_handle\_periodic函数进行周期性tick中要处理的task，具体如下：

> void tick\_handle\_periodic(struct clock\_event\_device \*dev)   
> {   
> int cpu = smp\_processor\_id();   
> ktime\_t next;
>
> tick\_periodic(cpu); －－－－周期性tick中要处理的内容，参考下节描述
>
> if (dev->mode != CLOCK\_EVT\_MODE\_ONESHOT)   
> return;   
>   
> next = ktime\_add(dev->next\_event, tick\_period);－－－－计算下一个周期性tick触发的时间   
> for (;;) {   
> if (!clockevents\_program\_event(dev, next, false))－－－设定下一个clock event触发的时间   
> return;   
>   
> if (timekeeping\_valid\_for\_hres())－－－－－－在其他文档中描述   
> tick\_periodic(cpu);   
> next = ktime\_add(next, tick\_period);   
> }   
> }

如果该tick device所属的clock event device工作在one shot mode，那么还需要为产生周期性tick而进行一些额外处理。

2、周期性tick中要处理的内容

代码如下：

> static void tick\_periodic(int cpu)   
> {   
> if (tick\_do\_timer\_cpu == cpu) {－－－－global tick需要进行一些额外处理   
> write\_seqlock(&jiffies\_lock);   
> tick\_next\_period = ktime\_add(tick\_next\_period, tick\_period);
>
> do\_timer(1);－－－－－－－－－－－－－更新jiffies，计算平均负载   
> write\_sequnlock(&jiffies\_lock);   
> update\_wall\_time();－－－－－－－－－－更新wall time   
> }
>
> update\_process\_times(user\_mode(get\_irq\_regs()));－－－－更新和当前进程相关的内容   
> profile\_tick(CPU\_PROFILING);－－－－－－和性能剖析相关，不详述了   
> }

*原创文章，转发请注明出处。蜗窝科技*

*/timer_subsystem/periodic-tick.html*
