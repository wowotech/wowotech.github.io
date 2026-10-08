---
title: "linux kernel的中断子系统之（四）：High level irq event handler"
date: 2014-08-28T20:00:50+08:00
url: "/irq_subsystem/High_level_irq_event_handler.html"
gid: "83"
emlog_type: "blog"
summary: "\r\n\t当外设触发一次中断后，一个大概的处理过程是：\r\n\r\n\r\n\t1、具体CPU architecture相关的模块会进行现场保护，然后调用machine driver对应的中断处理handler\r\n\r\n\r\n\t2、machine driver对应的中断处理handler中会根据硬件的信息获取HW interrupt ID，并且通过irq domain模块翻译成IRQ number\r\n\r\n\r\n\t3、\r"
author: "linuxer"
category: "中断子系统"
category_alias: "irq_subsystem"
tags: ["中断处理"]
views: 71912
comment_count: 51
aliases:
  - "/irq_subsystem/83.html"
  - "/83.html"
---

一、前言

当外设触发一次中断后，一个大概的处理过程是：

1、具体CPU architecture相关的模块会进行现场保护，然后调用machine driver对应的中断处理handler

2、machine driver对应的中断处理handler中会根据硬件的信息获取HW interrupt ID，并且通过irq domain模块翻译成IRQ number

3、调用该IRQ number对应的high level irq event handler，在这个high level的handler中，会通过和interupt controller交互，进行中断处理的flow control（处理中断的嵌套、抢占等），当然最终会遍历该中断描述符的IRQ action list，调用外设的specific handler来处理该中断

4、具体CPU architecture相关的模块会进行现场恢复。

上面的1、4这两个步骤在[linux kernel的中断子系统之（六）：ARM中断处理过程](/irq_subsystem/irq_handler.html)中已经有了较为细致的描述，步骤2在[linux kernel的中断子系统之（二）：irq domain介绍](/irq_subsystem/irq-domain.html)中介绍，本文主要描述步骤3，也就是linux中断子系统的high level irq event handler。

注：这份文档充满了猜测和空想，很多地方描述可能是有问题的，不过我还是把它发出来，抛砖引玉，希望可以引发大家讨论。

一、如何进入high level irq event handler

1、从具体CPU architecture的中断处理到machine相关的处理模块

说到具体的CPU，我们还是用ARM为例好了。对于ARM，我们在[ARM中断处理](/irq_subsystem/irq_handler.html)文档中已经有了较为细致的描述。这里我们看看如何从从具体CPU的中断处理到machine相关的处理模块 ，其具体代码如下：

> .macro irq\_handler   
> #ifdef CONFIG\_MULTI\_IRQ\_HANDLER   
> ldr r1, =handle\_arch\_irq   
> mov r0, sp   
> adr lr, BSYM(9997f)   
> ldr pc, [r1]   
> #else   
> arch\_irq\_handler\_default   
> #endif   
> 9997:   
> .endm

其实，直接从CPU的中断处理跳转到通用中断处理模块是不可能的，中断处理不可能越过interrupt controller这个层次。一般而言，通用中断处理模块会提供一些通用的中断代码处理库，然后由interrupt controller这个层次的代码调用这些通用中断处理的完成整个的中断处理过程。“interrupt controller这个层次的代码”是和硬件中断系统设计相关的，例如：系统中有多少个interrupt contrller，每个interrupt controller是如何控制的？它们是如何级联的？我们称这些相关的驱动模块为machine interrupt driver。

在上面的代码中，如果配置了MULTI\_IRQ\_HANDLER的话，ARM中断处理则直接跳转到一个叫做handle\_arch\_irq函数，如果系统中只有一个类型的interrupt controller（可能是多个interrupt controller，例如使用两个级联的GIC），那么handle\_arch\_irq可以在interrupt controller初始化的时候设定。代码如下：

> ……
>
> if (gic\_nr == 0) {   
> set\_handle\_irq(gic\_handle\_irq);   
> }
>
> ……

gic\_nr是GIC的编号，linux kernel初始化过程中，每发现一个GIC，都是会指向GIC driver的初始化函数的，不过对于第一个GIC，gic\_nr等于0，对于第二个GIC，gic\_nr等于1。当然handle\_arch\_irq这个函数指针不是per CPU的变量，是全部CPU共享的，因此，初始化一次就OK了。

当使用多种类型的interrupt controller的时候（例如HW 系统使用了S3C2451这样的SOC，这时候，系统有两种interrupt controller，一种是GPIO type，另外一种是SOC上的interrupt controller），则不适合在interrupt controller中进行设定，这时候，可以考虑在machine driver中设定。在这种情况下，handle\_arch\_irq 这个函数是在setup\_arch函数中根据machine driver设定，具体如下：

> handle\_arch\_irq = mdesc->handle\_irq;

关于MULTI\_IRQ\_HANDLER这个配置项，我们可以再多说几句。当然，其实这个配置项的名字已经出卖它了。multi irq handler就是说系统中有多个irq handler，可以在run time的时候指定。为何要run time的时候，从多个handler中选择一个呢？HW interrupt block难道不是固定的吗？我的理解（猜想）是：一个kernel的image支持多个HW platform，对于不同的HW platform，在运行时检查HW platform的类型，设定不同的irq handler。

2、interrupt controller相关的代码

我们还是以2个级联的GIC为例来描述interrupt controller相关的代码。代码如下：

> static asmlinkage void \_\_exception\_irq\_entry gic\_handle\_irq(struct pt\_regs \*regs)   
> {   
> u32 irqstat, irqnr;   
> struct gic\_chip\_data \*gic = &gic\_data[0];－－－－－获取root GIC的硬件描述符   
> void \_\_iomem \*cpu\_base = gic\_data\_cpu\_base(gic); 获取root GIC mapping到CPU地址空间的信息
>
> do {   
> irqstat = readl\_relaxed(cpu\_base + GIC\_CPU\_INTACK);－－－获取HW interrupt ID   
> irqnr = irqstat & ~0x1c00;
>
> if (likely(irqnr > 15 && irqnr < 1021)) {－－－－SPI和PPI的处理   
> irqnr = irq\_find\_mapping(gic->domain, irqnr);－－－将HW interrupt ID转成IRQ number   
> handle\_IRQ(irqnr, regs);－－－－处理该IRQ number   
> continue;   
> }   
> if (irqnr < 16) {－－－－－IPI类型的中断处理   
> writel\_relaxed(irqstat, cpu\_base + GIC\_CPU\_EOI);   
> #ifdef CONFIG\_SMP   
> handle\_IPI(irqnr, regs);   
> #endif   
> continue;   
> }   
> break;   
> } while (1);   
> }

更多关于GIC相关的信息，请参考linux kernel的中断子系统之（七）：GIC代码分析。对于ARM处理器，handle\_IRQ代码如下：

> void handle\_IRQ(unsigned int irq, struct pt\_regs \*regs)   
> {
>
> ……   
> generic\_handle\_irq(irq);
>
> ……   
> }

3、调用high level handler

调用high level handler的代码逻辑非常简单，如下：

> int generic\_handle\_irq(unsigned int irq)   
> {   
> struct irq\_desc \*desc = irq\_to\_desc(irq); －－－通过IRQ number获取该irq的描述符
>
> if (!desc)   
> return -EINVAL;   
> generic\_handle\_irq\_desc(irq, desc);－－－－调用high level的irq handler来处理该IRQ   
> return 0;   
> }
>
> static inline void generic\_handle\_irq\_desc(unsigned int irq, struct irq\_desc \*desc)   
> {   
> desc->handle\_irq(irq, desc);   
> }

二、理解high level irq event handler需要的知识准备

1、自动探测IRQ

一个硬件驱动可以通过下面的方法进行自动探测它使用的IRQ：

> unsigned long irqs;   
> int irq;
>
> irqs = probe\_irq\_on();－－－－－－－－启动IRQ自动探测   
> 驱动那个打算自动探测IRQ的硬件产生中断   
> irq = probe\_irq\_off(irqs);－－－－－－－结束IRQ自动探测

如果能够自动探测到IRQ，上面程序中的irq(probe\_irq\_off的返回值)就是自动探测的结果。后续程序可以通过request\_threaded\_irq申请该IRQ。probe\_irq\_on函数主要的目的是返回一个32 bit的掩码，通过该掩码可以知道可能使用的IRQ number有哪些，具体代码如下：

> unsigned long probe\_irq\_on(void)   
> {
>
> ……   
> for\_each\_irq\_desc\_reverse(i, desc) { －－－－scan 从nr\_irqs-1 到0 的中断描述符   
> raw\_spin\_lock\_irq(&desc->lock);   
> if (!desc->action && irq\_settings\_can\_probe(desc)) {－－－－－－－－（1）   
> desc->istate |= IRQS\_AUTODETECT | IRQS\_WAITING;－－－－－（2）   
> if (irq\_startup(desc, false))   
> desc->istate |= IRQS\_PENDING;   
> }   
> raw\_spin\_unlock\_irq(&desc->lock);   
> }   
> msleep(100); －－－－－－－－－－－－－－－－－－－－－－－－－－（3）
>
> for\_each\_irq\_desc(i, desc) {   
> raw\_spin\_lock\_irq(&desc->lock);
>
> if (desc->istate & IRQS\_AUTODETECT) {－－－－－－－－－－－－（4）   
> if (!(desc->istate & IRQS\_WAITING)) {   
> desc->istate &= ~IRQS\_AUTODETECT;   
> irq\_shutdown(desc);   
> } else   
> if (i < 32)－－－－－－－－－－－－－－－－－－－－－－－－（5）   
> mask |= 1 << i;   
> }   
> raw\_spin\_unlock\_irq(&desc->lock);   
> }
>
> return mask;   
> }

（1）那些能自动探测IRQ的中断描述符需要具体两个条件：

a、该中断描述符还没有通过request\_threaded\_irq或者其他方式申请该IRQ的specific handler（也就是irqaction数据结构）

b、该中断描述符允许自动探测（不能设定IRQ\_NOPROBE）

（2）如果满足上面的条件，那么该中断描述符属于备选描述符。设定其internal state为IRQS\_AUTODETECT | IRQS\_WAITING。IRQS\_AUTODETECT表示本IRQ正处于自动探测中。

（3）在等待过程中，系统仍然允许，各种中断依然会触发。在各种high level irq event handler中，总会有如下的代码：

> desc->istate &= ~(IRQS\_REPLAY | IRQS\_WAITING);

这里会清除IRQS\_WAITING状态。

（4）这时候，我们还没有控制那个想要自动探测IRQ的硬件产生中断，因此处于自动探测中，并且IRQS\_WAITING并清除的一定不是我们期待的IRQ（可能是spurious interrupts导致的），这时候，clear IRQS\_AUTODETECT，shutdown该IRQ。

（5）最大探测的IRQ是31（mask是一个32 bit的value），mask返回的是可能的irq掩码。

我们再来看看probe\_irq\_off的代码：

> int probe\_irq\_off(unsigned long val)   
> {   
> int i, irq\_found = 0, nr\_of\_irqs = 0;   
> struct irq\_desc \*desc;
>
> for\_each\_irq\_desc(i, desc) {   
> raw\_spin\_lock\_irq(&desc->lock);
>
> if (desc->istate & IRQS\_AUTODETECT) {－－－－只有处于IRQ自动探测中的描述符才会被处理   
> if (!(desc->istate & IRQS\_WAITING)) {－－－－找到一个潜在的中断描述符   
> if (!nr\_of\_irqs)   
> irq\_found = i;   
> nr\_of\_irqs++;   
> }   
> desc->istate &= ~IRQS\_AUTODETECT; －－－－IRQS\_WAITING没有被清除，说明该描述符   
> irq\_shutdown(desc); 不是自动探测的那个，shutdown之   
> }   
> raw\_spin\_unlock\_irq(&desc->lock);   
> }   
> mutex\_unlock(&probing\_active);
>
> if (nr\_of\_irqs > 1) －－－－－－如果找到多于1个的IRQ，说明探测失败，返回负的IRQ个数信息   
> irq\_found = -irq\_found;
>
> return irq\_found;   
> }

因为在调用probe\_irq\_off已经触发了自动探测IRQ的那个硬件中断，因此在该中断的high level handler的执行过程中，该硬件对应的中断描述符的IRQS\_WAITING标致应该已经被清除，因此probe\_irq\_off函数scan中断描述符DB，找到处于auto probe中，而且IRQS\_WAITING标致被清除的那个IRQ。如果找到一个，那么探测OK，返回该IRQ number，如果找到多个，说明探测失败，返回负的IRQ个数信息，没有找到的话，返回0。

2、resend一个中断

一个ARM SOC总是有很多的GPIO，有些GPIO可以提供中断功能，这些GPIO的中断可以配置成level trigger或者edge trigger。一般而言，大家都更喜欢用level trigger的中断。有的SOC只能是有限个数的GPIO可以配置成电平中断，因此，在项目初期进行pin define的时候，大家都在争抢电平触发的GPIO。

电平触发的中断有什么好处呢？电平触发的中断很简单、直接，只要硬件检测到硬件事件（例如有数据到来），其assert指定的电平信号，CPU ack该中断后，电平信号消失。但是对于边缘触发的中断，它是用一个上升沿或者下降沿告知硬件的状态，这个状态不是一个持续的状态，如果软件处理不好，容易丢失中断。

什么时候会resend一个中断呢？我们考虑一个简单的例子：

（1）CPU A上正在处理x外设的中断

（2）x外设的中断再次到来（CPU A已经ack该IRQ，因此x外设的中断可以再次触发），这时候其他CPU会处理它（mask and ack），并设置该中断描述符是pending状态，并委托CPU A处理该pending状态的中断。需要注意的是CPU已经ack了该中断，因此该中断的硬件状态已经不是pending状态，无法触发中断了，这里的pending状态是指中断描述符的软件状态。

（3）CPU B上由于同步的需求，disable了x外设的IRQ，这时候，CPU A没有处理pending状态的x外设中断就离开了中断处理过程。

（4）当enable x外设的IRQ的时候，需要检测pending状态以便resend该中断，否则，该中断会丢失的

具体代码如下：

> void check\_irq\_resend(struct irq\_desc \*desc, unsigned int irq)   
> {   
>   
> if (irq\_settings\_is\_level(desc)) {－－－－－－－电平中断不存在resend的问题   
> desc->istate &= ~IRQS\_PENDING;   
> return;   
> }   
> if (desc->istate & IRQS\_REPLAY)－－－－如果已经设定resend的flag，退出就OK了，这个应该   
> return; 和irq的enable disable能多层嵌套相关   
> if (desc->istate & IRQS\_PENDING) {－－－－－－－如果有pending的flag则进行处理   
> desc->istate &= ~IRQS\_PENDING;   
> desc->istate |= IRQS\_REPLAY; －－－－－－设置retrigger标志
>
> if (!desc->irq\_data.chip->irq\_retrigger ||   
> !desc->irq\_data.chip->irq\_retrigger(&desc->irq\_data)) {－－－－调用底层irq chip的callback   
> #ifdef CONFIG\_HARDIRQS\_SW\_RESEND   
> 也可以使用软件手段来完成resend一个中断，具体代码省略，有兴趣大家可以自己看看   
> #endif   
> }   
> }   
> }

在各种high level irq event handler中，总会有如下的代码：

> desc->istate &= ~(IRQS\_REPLAY | IRQS\_WAITING);

这里会清除IRQS\_REPLAY状态，表示该中断已经被retrigger，一次resend interrupt的过程结束。

3、unhandled interrupt和spurious interrupt

在中断处理的最后，总会有一段代码如下：

> irqreturn\_t   
> handle\_irq\_event\_percpu(struct irq\_desc \*desc, struct irqaction \*action)   
> {
>
> ……
>
> if (!noirqdebug)   
> note\_interrupt(irq, desc, retval);   
> return retval;   
> }

note\_interrupt就是进行unhandled interrupt和spurious interrupt处理的。对于这类中断，linux kernel有一套复杂的机制来处理，你可以通过command line参数（noirqdebug）来控制开关该功能。

当发生了一个中断，但是没有被处理（有两种可能，一种是根本没有注册的specific handler，第二种是有handler，但是handler否认是自己对应的设备触发的中断），怎么办？毫无疑问这是一个异常状况，那么kernel是否要立刻采取措施将该IRQ disable呢？也不太合适，毕竟interrupt request信号线是允许共享的，直接disable该IRQ有可能会下手太狠，kernel采取了这样的策略：如果该IRQ触发了100,000次，但是99,900次没有处理，在这种条件下，我们就是disable这个interrupt request line。多么有情有义的策略啊！相关的控制数据在中断描述符中，如下：

> struct irq\_desc {   
> ……   
> unsigned int irq\_count;－－－－－－－－记录发生的中断的次数，每100,000则回滚   
> unsigned long last\_unhandled;－－－－－上一次没有处理的IRQ的时间点   
> unsigned int irqs\_unhandled;－－－－－－没有处理的次数   
> ……   
> }

irq\_count和irqs\_unhandled都是比较直观的，为何要记录unhandled interrupt发生的时间呢？我们来看具体的代码。具体的相关代码位于note\_interrupt中，如下：

> void note\_interrupt(unsigned int irq, struct irq\_desc \*desc, irqreturn\_t action\_ret)   
> {   
> if (desc->istate & IRQS\_POLL\_INPROGRESS || irq\_settings\_is\_polled(desc))   
> return;
>
> if (action\_ret == IRQ\_WAKE\_THREAD)－－－－handler返回IRQ\_WAKE\_THREAD是正常情况   
> return;
>
> if (bad\_action\_ret(action\_ret)) {－－－－－报告错误，这些是由于specific handler的返回错误导致的   
> report\_bad\_irq(irq, desc, action\_ret);   
> return;   
> }
>
> if (unlikely(action\_ret == IRQ\_NONE)) {－－－－－－－是unhandled interrupt   
> if (time\_after(jiffies, desc->last\_unhandled + HZ/10))－－－（1）   
> desc->irqs\_unhandled = 1;－－－重新开始计数   
> else   
> desc->irqs\_unhandled++;－－－判定为unhandled interrupt，计数加一   
> desc->last\_unhandled = jiffies;－－－－－－－保存本次unhandled interrupt对应的jiffies时间   
> }
>
> if (unlikely(try\_misrouted\_irq(irq, desc, action\_ret))) {－－－是否启动Misrouted IRQ fixup   
> int ok = misrouted\_irq(irq);   
> if (action\_ret == IRQ\_NONE)   
> desc->irqs\_unhandled -= ok;   
> }
>
> desc->irq\_count++;   
> if (likely(desc->irq\_count < 100000))－－－－－－－－－－－（2）   
> return;
>
> desc->irq\_count = 0;   
> if (unlikely(desc->irqs\_unhandled > 99900)) {－－－－－－－－（3）   
>   
> \_\_report\_bad\_irq(irq, desc, action\_ret);－－－报告错误   
>   
> desc->istate |= IRQS\_SPURIOUS\_DISABLED;   
> desc->depth++;   
> irq\_disable(desc);
>
> mod\_timer(&poll\_spurious\_irq\_timer,－－－－－－－－－－（4）   
> jiffies + POLL\_SPURIOUS\_IRQ\_INTERVAL);   
> }   
> desc->irqs\_unhandled = 0;   
> }

（1）是否是一次有效的unhandled interrupt还要根据时间来判断。一般而言，当硬件处于异常状态的时候往往是非常短的时间触发非常多次的中断，如果距离上次unhandled interrupt的时间超过了10个jiffies（如果HZ＝100，那么时间就是100ms），那么我们要把irqs\_unhandled重新计数。如果不这么处理的话，随着时间的累计，最终irqs\_unhandled可能会达到99900次的，从而把这个IRQ错误的推上了审判台。

（2）irq\_count每次都会加一，记录IRQ被触发的次数。但只要大于100000才启动 step （3）中的检查。一旦启动检查，irq\_count会清零，irqs\_unhandled也会清零，进入下一个检查周期。

（3）如果满足条件（IRQ触发了100,000次，但是99,900次没有处理），disable该IRQ。

（4）启动timer，轮询整个系统中的handler来处理这个中断（轮询啊，绝对是真爱啊）。这个timer的callback函数定义如下：

> static void poll\_spurious\_irqs(unsigned long dummy)   
> {   
> struct irq\_desc \*desc;   
> int i;
>
> if (atomic\_inc\_return(&irq\_poll\_active) != 1)－－－－确保系统中只有一个excuting thread进入临界区   
> goto out;   
> irq\_poll\_cpu = smp\_processor\_id(); －－－－记录当前正在polling的CPU
>
> for\_each\_irq\_desc(i, desc) {－－－－－－遍历所有的中断描述符   
> unsigned int state;
>
> if (!i)－－－－－－－－－－－－－越过0号中断描述符。对于X86，这是timer的中断   
> continue;
>
> /\* Racy but it doesn't matter \*/   
> state = desc->istate;   
> barrier();   
> if (!(state & IRQS\_SPURIOUS\_DISABLED))－－－－名花有主的那些就不必考虑了   
> continue;
>
> local\_irq\_disable();   
> try\_one\_irq(i, desc, true);－－－－－－－－－OK，尝试一下是不是可以处理   
> local\_irq\_enable();   
> }   
> out:   
> atomic\_dec(&irq\_poll\_active);   
> mod\_timer(&poll\_spurious\_irq\_timer,－－－－－－－－一旦触发了该timer，就停不下来   
> jiffies + POLL\_SPURIOUS\_IRQ\_INTERVAL);   
> }

三、和high level irq event handler相关的硬件描述

1、CPU layer和Interrupt controller之间的接口

从逻辑层面上看，CPU和interrupt controller之间的接口包括：

（1）触发中断的signal。一般而言，这个（些）信号是电平触发的。对于ARM CPU，它是nIRQ和nFIQ信号线，对于X86，它是INT和NMI信号线，对于PowerPC，这些信号线包括MC（machine check）、CRIT（critical interrupt）和NON-CRIT（Non critical interrupt）。对于linux kernel的中断子系统，我们只使用其中一个信号线（例如对于ARM而言，我们只使用nIRQ这个信号线）。这样，从CPU层面看，其逻辑动作非常的简单，不区分优先级，触发中断的那个信号线一旦assert，并且CPU没有mask中断，那么软件就会转到一个异常向量执行，完毕后返回现场。

（2）Ack中断的signal。这个signal可能是物理上的一个连接CPU和interrupt controller的铜线，也可能不是。对于X86＋8259这样的结构，Ack中断的signal就是nINTA信号线，对于ARM＋GIC而言，这个信号就是总线上的一次访问（读Interrupt Acknowledge Register寄存器）。CPU ack中断标识cpu开启启动中断服务程序（specific handler）去处理该中断。对于X86而言，ack中断可以让8259将interrupt vector数据送到数据总线上，从而让CPU获取了足够的处理该中断的信息。对于ARM而言，ack中断的同时也就是获取了发生中断的HW interrupt ID，总而言之，ack中断后，CPU获取了足够开启执行中断处理的信息。

（3）结束中断（EOI，end of interrupt）的signal。这个signal用来标识CPU已经完成了对该中断的处理（specific handler或者ISR，interrupt serivce routine执行完毕）。实际的物理形态这里就不描述了，和ack中断signal是类似的。

（4）控制总线和数据总线接口。通过这些接口，CPU可以访问（读写）interrupt controller的寄存器。

2、Interrupt controller和Peripheral device之间的接口

所有的系统中，Interrupt controller和Peripheral device之间的接口都是一个Interrupt Request信号线。外设通过这个信号线上的电平或者边缘向CPU（实际上是通过interrupt controller）申请中断服务。

四、几种典型的high level irq event handler

本章主要介绍几种典型的high level irq event handler，在进行high level irq event handler的设定的时候需要注意，不是外设使用电平触发就选用handle\_level\_irq，选用什么样的high level irq event handler是和Interrupt controller的行为以及外设电平触发方式决定的。介绍每个典型的handler之前，我会简单的描述该handler要求的硬件行为，如果该外设的中断系统符合这个硬件行为，那么可以选择该handler为该中断的high level irq event handler。

1、边缘触发的handler。

使用handle\_edge\_irq这个handler的硬件中断系统行为如下：

[![xyz](/content/uploadfile/201408/1618e77f0e5a8cbc94806355a0ff3c4720140828120041.gif "xyz")](/content/uploadfile/201408/b844e701747cb80623342178d80fbe0120140828120039.gif)

我们以上升沿为例描述边缘中断的处理过程（下降沿的触发是类似的）。当interrupt controller检测到了上升沿信号，会将该上升沿状态（pending）锁存在寄存器中，并通过中断的signal向CPU触发中断。需要注意：这时候，外设和interrupt controller之间的interrupt request信号线会保持高电平，这也就意味着interrupt controller不可能检测到新的中断信号（本身是高电平，无法形成上升沿）。这个高电平信号会一直保持到软件ack该中断（调用irq chip的irq\_ack callback函数）。ack之后，中断控制器才有可能继续探测上升沿，触发下一次中断。

ARM＋GIC组成的系统不符合这个类型。虽然GIC提供了IAR（Interrupt Acknowledge Register）寄存器来让ARM来ack中断，但是，在调用high level handler之前，中断处理程序需要通过读取IAR寄存器获得HW interrpt ID并转换成IRQ number，因此实际上，对于GIC的irq chip，它是无法提供本场景中的irq\_ack函数的。很多GPIO type的interrupt controller符合上面的条件，它们会提供pending状态寄存器，读可以获取pending状态，而向pending状态寄存器写1可以ack该中断，让interrupt controller可以继续触发下一次中断。

handle\_edge\_irq代码如下：

> void handle\_edge\_irq(unsigned int irq, struct irq\_desc \*desc)   
> {   
> raw\_spin\_lock(&desc->lock); －－－－－－－－－－－－－－－－－（0）
>
> desc->istate &= ~(IRQS\_REPLAY | IRQS\_WAITING);－－－－参考上一章的描述   
>   
> if (unlikely(irqd\_irq\_disabled(&desc->irq\_data) ||－－－－－－－－－－－（1）   
> irqd\_irq\_inprogress(&desc->irq\_data) || !desc->action)) {   
> if (!irq\_check\_poll(desc)) {   
> desc->istate |= IRQS\_PENDING;   
> mask\_ack\_irq(desc);   
> goto out\_unlock;   
> }   
> }   
> kstat\_incr\_irqs\_this\_cpu(irq, desc); －－－更新该IRQ统计信息
>
> desc->irq\_data.chip->irq\_ack(&desc->irq\_data); －－－－－－－－－（2）
>
> do {   
> if (unlikely(!desc->action)) { －－－－－－－－－－－－－－－－－（3）   
> mask\_irq(desc);   
> goto out\_unlock;   
> }
>
> if (unlikely(desc->istate & IRQS\_PENDING)) { －－－－－－－－－（4）   
> if (!irqd\_irq\_disabled(&desc->irq\_data) &&   
> irqd\_irq\_masked(&desc->irq\_data))   
> unmask\_irq(desc);   
> }
>
> handle\_irq\_event(desc); －－－－－－－－－－－－－－－－－－－（5）
>
> } while ((desc->istate & IRQS\_PENDING) &&   
> !irqd\_irq\_disabled(&desc->irq\_data)); －－－－－－－－－－－－－（6）
>
> out\_unlock:   
> raw\_spin\_unlock(&desc->lock); －－－－－－－－－－－－－－－－－（7）   
> }

（0） 这时候，中断仍然是关闭的，因此不会有来自本CPU的并发，使用raw spin lock就防止其他CPU上对该IRQ的中断描述符的访问。针对该spin lock，我们直观的感觉是raw\_spin\_lock和（7）中的raw\_spin\_unlock是成对的，实际上并不是，handle\_irq\_event中的代码是这样的：

> irqreturn\_t handle\_irq\_event(struct irq\_desc \*desc)   
> {
>
> raw\_spin\_unlock(&desc->lock); －－－－－－－和上面的（0）对应
>
> 处理具体的action list
>
> raw\_spin\_lock(&desc->lock);－－－－－－－－和上面的（7）对应   
>   
> }

实际上，由于在handle\_irq\_event中处理action list的耗时还是比较长的，因此处理具体的action list的时候并没有持有中断描述符的spin lock。在如果那样的话，其他CPU在对中断描述符进行操作的时候需要spin的时间会很长的。

（1）判断是否需要执行下面的action list的处理。这里分成几种情况：

a、该中断事件已经被其他的CPU处理了

b、该中断被其他的CPU disable了

c、该中断描述符没有注册specific handler。这个比较简单，如果没有irqaction，根本没有必要调用action list的处理

如果该中断事件已经被其他的CPU处理了，那么我们仅仅是设定pending状态（为了委托正在处理的该中断的那个CPU进行处理），mask\_ack\_irq该中断并退出就OK了，并不做具体的处理。另外正在处理该中断的CPU会检查pending状态，并进行处理的。同样的，如果该中断被其他的CPU disable了，本就不应该继续执行该中断的specific handler，我们也是设定pending状态，mask and ack中断就退出了。当其他CPU的代码离开临界区，enable 该中断的时候，软件会检测pending状态并resend该中断。

这里的irq\_check\_poll代码如下：

> static bool irq\_check\_poll(struct irq\_desc \*desc)   
> {   
> if (!(desc->istate & IRQS\_POLL\_INPROGRESS))   
> return false;   
> return irq\_wait\_for\_poll(desc);   
> }

IRQS\_POLL\_INPROGRESS标识了该IRQ正在被polling（上一章有描述），如果没有被轮询，那么返回false，进行正常的设定pending标记、mask and ack中断。如果正在被轮询，那么需要等待poll结束。

（2）ack该中断。对于中断控制器，一旦被ack，表示该外设的中断被enable，硬件上已经准备好触发下一次中断了。再次触发的中断会被调度到其他的CPU上。现在，我们可以再次回到步骤（1）中，为什么这里用mask and ack而不是单纯的ack呢？如果单纯的ack则意味着后续中断还是会触发，这时候怎么处理？在pending＋in progress的情况下，我们要怎么处理？记录pending的次数，有意义吗？由于中断是完全异步的，也有可能pending的标记可能在另外的CPU上已经修改为replay的标记，这时候怎么办？当事情变得复杂的时候，那一定是本来方向就错了，因此，mask and ack就是最好的策略，我已经记录了pending状态，不再考虑pending嵌套的情况。

（3）在调用specific handler处理具体的中断的时候，由于不持有中断描述符的spin lock，因此其他CPU上有可能会注销其specific handler，因此do while循环之后，desc->action有可能是NULL，如果是这样，那么mask irq，然后退出就OK了

（4）如果中断描述符处于pending状态，那么一定是其他CPU上又触发了该interrupt source的中断，并设定了pending状态，“委托”本CPU进行处理，这时候，需要把之前mask住的中断进行unmask的操作。一旦unmask了该interrupt source，后续的中断可以继续触发，由其他的CPU处理（仍然是设定中断描述符的pending状态，委托当前正在处理该中断请求的那个CPU进行处理）。

（5）处理该中断请求事件

> irqreturn\_t handle\_irq\_event(struct irq\_desc \*desc)   
> {   
> struct irqaction \*action = desc->action;   
> irqreturn\_t ret;
>
> desc->istate &= ~IRQS\_PENDING;－－－－CPU已经准备处理该中断了，因此，清除pending状态   
> irqd\_set(&desc->irq\_data, IRQD\_IRQ\_INPROGRESS);－－设定INPROGRESS的flag   
> raw\_spin\_unlock(&desc->lock);
>
> ret = handle\_irq\_event\_percpu(desc, action); －－－遍历action list，调用specific handler
>
> raw\_spin\_lock(&desc->lock);   
> irqd\_clear(&desc->irq\_data, IRQD\_IRQ\_INPROGRESS);－－－处理完成，清除INPROGRESS标记   
> return ret;   
> }

（6）只要有pending标记，就说明该中断还在pending状态，需要继续处理。当然，如果有其他的CPU disable了该interrupt source，那么本次中断结束处理。

2、电平触发的handler

使用handle\_level\_irq这个handler的硬件中断系统行为如下：

[![level](/content/uploadfile/201408/335dea2bd22abd76c4df50e9953b759920140828120046.gif "level")](/content/uploadfile/201408/5a88d2c9e746aa35e79f6de6c1f6afd020140828120043.gif)

我们以高电平触发为例。当interrupt controller检测到了高电平信号，并通过中断的signal向CPU触发中断。这时候，对中断控制器进行ack并不能改变interrupt request signal上的电平状态，一直要等到执行具体的中断服务程序（specific handler），对外设进行ack的时候，电平信号才会恢复成低电平。在对外设ack之前，中断状态一直是pending的，如果没有mask中断，那么中断控制器就会assert CPU。

handle\_level\_irq的代码如下：

> void handle\_level\_irq(unsigned int irq, struct irq\_desc \*desc)   
> {   
> raw\_spin\_lock(&desc->lock);   
> mask\_ack\_irq(desc); －－－－－－－－－－－－－－－－－－－－－（1）
>
> if (unlikely(irqd\_irq\_inprogress(&desc->irq\_data)))－－－－－－－－－（2）   
> if (!irq\_check\_poll(desc))   
> goto out\_unlock;
>
> desc->istate &= ~(IRQS\_REPLAY | IRQS\_WAITING);－－和retrigger中断以及自动探测IRQ相关   
> kstat\_incr\_irqs\_this\_cpu(irq, desc);
>
> if (unlikely(!desc->action || irqd\_irq\_disabled(&desc->irq\_data))) {－－－－－（3）   
> desc->istate |= IRQS\_PENDING;   
> goto out\_unlock;   
> }
>
> handle\_irq\_event(desc);
>
> cond\_unmask\_irq(desc); －－－－－－－－－－－－－－（4）
>
> out\_unlock:   
> raw\_spin\_unlock(&desc->lock);   
> }

（1）考虑CPU<------>interrupt controller<------>device这样的连接方式中，我们认为high level handler主要是和interrupt controller交互，而specific handler（request\_irq注册的那个）是和device进行交互。Level类型的中断的特点就是只要外设interrupt request line的电平状态是有效状态，对于interrupt controller，该外设的interrupt总是active的。由于外设检测到了事件（比如数据到来了），因此assert了指定的电平信号，这个电平信号会一直保持，直到软件清除了外设的状态寄存器。但是，high level irq event handler这个层面只能操作Interrupt controller，不能操作具体外设的寄存器（那应该属于具体外设的specific interrupt handler处理内容，该handler会挂入中断描述符中的IRQ action list）。直到在具体的中断服务程序（specific handler中）操作具体外设的寄存器，才能让这个asserted电平信号消息。

正是因为level trigger的这个特点，因此，在high level handler中首先mask并ack该IRQ。这一点和边缘触发的high level handler有显著的不同，在handle\_edge\_irq中，我们仅仅是ack了中断，并没有mask，因为边缘触发的中断稍纵即逝，一旦mask了该中断，容易造成中断丢失。而对于电平中断，我们不得不mask住该中断，如果不mask住，只要CPU ack中断，中断控制器将持续的assert CPU中断（因为有效电平状态一直保持）。如果我们mask住该中断，中断控制器将不再转发该interrupt source来的中断，因此，所有的CPU都不会感知到该中断，直到软件unmask。这里的ack是针对interrupt controller的ack，本身ack就是为了clear interrupt controller对该IRQ的状态寄存器，不过由于外部的电平仍然是有效信号，其实未必能清除interrupt controller的中断状态，不过这是和中断控制器硬件实现相关的。

（2）对于电平触发的high level handler，我们一开始就mask并ack了中断，因此后续specific handler因该是串行化执行的，为何要判断in progress标记呢？不要忘记spurious interrupt，那里会直接调用handler来处理spurious interrupt。

（3）这里有两个场景

a、没有注册specific handler。如果没有注册handler，那么保持mask并设定pending标记（这个pending标记有什么作用还没有想明白）。

b、该中断被其他的CPU disable了。如果该中断被其他的CPU disable了，本就不应该继续执行该中断的specific handler，我们也是设定pending状态，mask and ack中断就退出了。当其他CPU的代码离开临界区，enable 该中断的时候，软件会检测pending状态并resend该中断。

（4）为何是有条件的unmask该IRQ？正常的话当然是umask就OK了，不过有些threaded interrupt（这个概念在下一份文档中描述）要求是one shot的（首次中断，specific handler中开了一枪，wakeup了irq handler thread，如果允许中断嵌套，那么在specific handler会多次开枪，这也就不是one shot了，有些IRQ的handler thread要求是one shot，也就是不能嵌套specific handler）。

3、支持EOI的handler

TODO

*原创文章，转发请注明出处。蜗窝科技。*[/irq_subsystem/High_level_irq_event_handler.html](/irq_subsystem/High_level_irq_event_handler.html)
