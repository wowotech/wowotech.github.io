---
title: "系统休眠（System Suspend）和设备中断处理"
date: 2017-04-21T12:02:24+08:00
url: "/pm_subsystem/suspend-irq.html"
gid: "390"
emlog_type: "blog"
summary: "本文主要描述系统休眠过程是如何和中断子系统交互的，全文的结构保持和内核文档中的power/suspend-and-interrupts.txt一致，当然，本质上也可以说这份文档是对suspend-and-interrupts.txt的翻译。"
author: "linuxer"
category: "电源管理子系统"
category_alias: "pm_subsystem"
tags: ["suspend", "irq"]
views: 44169
comment_count: 31
aliases:
  - "/pm_subsystem/390.html"
  - "/390.html"
---

一、设备IRQ的suspend和resume

本小节主要解决这样一个问题：在系统休眠过程中，如何suspend设备中断（IRQ）？在从休眠中唤醒的过程中，如何resume设备IRQ？

一般而言，在系统suspend过程的后期，各个设备的IRQ (interrupt request line)会被disable掉。具体的时间点是在各个设备的late suspend阶段之后。代码如下（删除了部分无关代码）：

> static int suspend\_enter(suspend\_state\_t state, bool \*wakeup)
>
> {……
>
> error = dpm\_suspend\_late(PMSG\_SUSPEND);－－－－－late suspend阶段
>
> error = platform\_suspend\_prepare\_late(state);
>
> 下面的代码中会disable各个设备的irq
>
> error = dpm\_suspend\_noirq(PMSG\_SUSPEND);－－－－进入noirq的阶段
>
> error = platform\_suspend\_prepare\_noirq(state);
>
> ……
>
> }

在dpm\_suspend\_noirq函数中，会针对系统中的每一个device，依次调用device\_suspend\_noirq来执行该设备noirq情况下的suspend callback函数，当然，在此之前会调用suspend\_device\_irqs函数来disable所有设备的irq。

之所以这么做，其思路是这样的：在各个设备驱动完成了late suspend之后，按理说这些已经被suspend的设备不应该再触发中断了。如果还有一些设备没有被正确的suspend，那么我们最好的策略是mask该设备的irq，从而阻止中断的递交。此外，在过去的代码中（指interrupt handler），我们对设备共享IRQ的情况处理的不是很好，存在这样的问题：在共享IRQ的设备们完成suspend之后，如果有中断触发，这时候设备驱动的interrupt handler并没有准备好。在有些场景下，interrupt handler会访问已经suspend设备的IO地址空间，从而导致不可预知的issue。这些issue很难debug，因此，我们引入了suspend\_device\_irqs()以及设备noirq阶段的callback函数。

系统resume过程中，在各个设备的early resume过程之前，各个设备的IRQ会被重新打开，具体代码如下（删除了部分无关代码）：

> static int suspend\_enter(suspend\_state\_t state, bool \*wakeup)
>
> {……
>
> platform\_resume\_noirq(state);－－－－首先执行noirq阶段的resume
>
> dpm\_resume\_noirq(PMSG\_RESUME);－－－－－－在这里会恢复irq，然后进入early resume阶段
>
> platform\_resume\_early(state);
>
> dpm\_resume\_early(PMSG\_RESUME);
>
> ……}

在dpm\_resume\_noirq函数中，会调用各个设备驱动的noirq callback，在此之后，调用resume\_device\_irqs函数，完成各个设备irq的enable。

二、关于IRQF\_NO\_SUSPEND Flag

当然，有些中断需要在整个系统的suspend-resume过程中（包括在noirq阶段，包括将nonboot CPU推送到offline状态以及系统resume后，将其重新设置为online的阶段）保持能够触发的状态。一个简单的例子就是timer中断，此外IPI以及一些特殊目的设备中断也需要如此。

在中断申请的时候，IRQF\_NO\_SUSPEND flag可以用来告知IRQ subsystem，这个中断就是上一段文字中描述的那种中断：需要在系统的suspend-resume过程中保持enable状态。有了这个flag，suspend\_device\_irqs并不会disable该IRQ，从而让该中断在随后的suspend和resume过程中，保持中断开启。当然，这并不能保证该中断可以将系统唤醒。如果想要达到唤醒的目的，请调用enable\_irq\_wake。

需要注意的是：IRQF\_NO\_SUSPEND flag影响使用该IRQ的所有外设（一个IRQ可以被多个外设共享，不过ARM中不会这么用）。如果一个IRQ被多个外设共享，并且各个外设都注册了对应的interrupt handler，如果其一在申请中断的时候使用了IRQF\_NO\_SUSPEND flag，那么在系统suspend的时候（指suspend\_device\_irqs之后，按理说各个IRQ已经被disable了），所有该IRQ上的各个设备的interrupt handler都可以被正常的被触发执行，即便是有些设备在调用request\_irq(或者其他中断注册函数)的时候没有设定IRQF\_NO\_SUSPEND flag。正因为如此，我们应该尽可能的避免同时使用IRQF\_NO\_SUSPEND 和IRQF\_SHARED这两个flag。

三、系统中断唤醒接口：enable\_irq\_wake() 和 disable\_irq\_wake()

有些中断可以将系统从睡眠状态中唤醒，我们称之“可以唤醒系统的中断”，当然，“可以唤醒系统的中断”需要配置才能启动唤醒系统这样的功能。这样的中断一般在工作状态的时候就是作为普通I/O interrupt出现，只要在准备使能唤醒系统功能的时候，才会发起一些特别的配置和设定。

这样的配置和设定有可能是和硬件系统（例如SOC）上的信号处理逻辑相关的，我们可以考虑下面的HW block图：

[![irq-suspend](/content/uploadfile/201704/d77ad10fce03b9d181a2be9351c6113420170421040223.gif "irq-suspend")](/content/uploadfile/201704/6a651c54519aab85c314f0af79b75e3820170421040222.gif)

外设的中断信号被送到“通用的中断信号处理模块”和“特定中断信号接收模块”。正常工作的时候，我们会turn on“通用的中断信号处理模块”的处理逻辑，而turn off“特定中断信号接收模块” 的处理逻辑。但是，在系统进入睡眠状态的时候，有可能“通用的中断信号处理模块”已经off了，这时候，我们需要启动“特定中断信号接收模块”来接收中断信号，从而让系统suspend-resume模块（它往往是suspend状态时候唯一能够工作的HW block了）可以正常的被该中断信号唤醒。一旦唤醒，我们最好是turn off“特定中断信号接收模块”，让外设的中断处理回到正常的工作模式，同时，也避免了系统suspend-resume模块收到不必要的干扰。

IRQ子系统提供了两个接口函数来完成这个功能：enable\_irq\_wake()函数用来打开该外设中断线通往系统电源管理模块（也就是上面的suspend-resume模块）之路，另外一个接口是disable\_irq\_wake()，用来关闭该外设中断线通往系统电源管理模块路径上的各种HW block。

调用了enable\_irq\_wake会影响系统suspend过程中的suspend\_device\_irqs处理，代码如下：

> static bool suspend\_device\_irq(struct irq\_desc \*desc)
>
> {
>
> ……
>
> if (irqd\_is\_wakeup\_set(&desc->irq\_data)) {
>
> irqd\_set(&desc->irq\_data, IRQD\_WAKEUP\_ARMED);
>
> return true;
>
> }
>
> 省略Disable 中断的代码
>
> }

也就是说，一旦调用enable\_irq\_wake设定了该设备的中断作为系统suspend的唤醒源，那么在该外设的中断不会被disable，只是被标记一个IRQD\_WAKEUP\_ARMED的标记。对于那些不是wakeup source的中断，在suspend\_device\_irq 函数中会标记IRQS\_SUSPENDED并disable该设备的irq。在系统唤醒过程中（resume\_device\_irqs），被diable的中断会重新enable。

当然，如果在suspend的过程中发生了某些事件（例如wakeup source产生了有效信号），从而导致本次suspend abort，那么这个abort事件也会通知到PM core模块。事件并不需要被立刻通知到PM core模块，一般而言，suspend thread会在某些点上去检查pending的wakeup event。

在系统suspend的过程中，每一个来自wakeup source的中断都会终止suspend过程或者将系统唤醒（如果系统已经进入suspend状态）。但是，在执行了suspend\_device\_irqs之后，普通的中断被屏蔽了，这时候，即便HW触发了中断信号也无法执行其interrupt handler。作为wakeup source的IRQ会怎样呢？虽然它的中断没有被mask掉，但是其interrupt handler也不会执行（这时候的HW Signal只是用来唤醒系统）。唯一有机会执行的interrupt handler是那些标记IRQF\_NO\_SUSPEND flag的IRQ，因为它们的中断始终是enable的。当然，这些中断不应该调用enable\_irq\_wake进行唤醒源的设定。

四、Interrupts and Suspend-to-Idle

Suspend-to-idle (也被称为"freeze" 状态)是一个相对比较新的系统电源管理状态，相关代码如下：

> static int suspend\_enter(suspend\_state\_t state, bool \*wakeup)
>
> {
>
> ……
>
> 各个设备的late suspend阶段
>
> 各个设备的noirq suspend阶段
>
> if (state == PM\_SUSPEND\_FREEZE) {
>
> freeze\_enter();
>
> goto Platform\_wake;
>
> }
>
> ……
>
> }

Freeze和suspend的前面的操作基本是一样的：首先冻结系统中的进程，然后是suspend系统中的形形色色的device，不一样的地方在noirq suspend完成之后，freeze不会disable那些non-BSP的处理器和syscore suspend阶段，而是调用freeze\_enter函数，把所有的处理器推送到idle状态。这时候，任何的enable的中断都可以将系统唤醒。而这也就意味着那些标记IRQF\_NO\_SUSPEND（其IRQ没有在suspend\_device\_irqs过程中被mask掉）是有能力将处理器从idle状态中唤醒（不过，需要注意的是：这种信号并不会触发一个系统唤醒信号），而普通中断由于其IRQ被disable了，因此无法唤醒idle状态中的处理器。

那些能够唤醒系统的wakeup interrupt呢？由于其中断没有被mask掉，因此也可以将系统从suspend-to-idle状态中唤醒。整个过程和将系统从suspend状态中唤醒一样，唯一不同的是：将系统从freeze状态唤醒走的中断处理路径，而将系统从suspend状态唤醒走的唤醒处理路径，需要电源管理HW BLOCK中特别的中断处理逻辑的参与。

五、IRQF\_NO\_SUSPEND 标志和enable\_irq\_wake函数不能同时使用

针对一个设备，在申请中断的时候使用IRQF\_NO\_SUSPEND flag，又同时调用enable\_irq\_wake设定唤醒源是不合理的，主要原因如下：

1、如果IRQ没有共享，使用IRQF\_NO\_SUSPEND flag说明你想要在整个系统的suspend-resume过程中（包括suspend\_device\_irqs之后的阶段）保持中断打开以便正常的调用其interrupt handler。而调用enable\_irq\_wake函数则说明你想要将该设备的irq信号设定为中断源，因此并不期望调用其interrupt handler。而这两个需求明显是互斥的。

2、IRQF\_NO\_SUSPEND 标志和enable\_irq\_wake函数都不是针对一个interrupt handler的，而是针对该IRQ上的所有注册的handler的。在一个IRQ上共享唤醒源以及no suspend中断源是比较荒谬的。

不过，在非常特殊的场合下，一个IRQ可以被设定为wakeup source，同时也设定IRQF\_NO\_SUSPEND 标志。为了代码逻辑正确，该设备的驱动代码需要满足一些特别的需求。

参考文献

1、内核文档power/suspend-and-interrupts.txt

*原创文章，转发请注明出处。蜗窝科技*
