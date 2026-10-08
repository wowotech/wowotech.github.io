---
title: "linux kernel的中断子系统之（三）：IRQ number和中断描述符"
date: 2014-08-26T17:03:06+08:00
url: "/irq_subsystem/interrupt_descriptor.html"
gid: "82"
emlog_type: "blog"
summary: "本文主要围绕IRQ number和中断描述符（interrupt \r\ndescriptor）这两个概念描述通用中断处理过程。第二章主要描述基本概念，包括什么是IRQ \r\nnumber，什么是中断描述符等。第三章描述中断描述符数据结构的各个成员。第四章描述了初始化中断描述符相关的接口API。第五章描述中断描述符相关\r\n的接口API。"
author: "linuxer"
category: "中断子系统"
category_alias: "irq_subsystem"
tags: ["irq", "中断子系统", "中断描述符"]
views: 120413
comment_count: 79
aliases:
  - "/irq_subsystem/82.html"
  - "/82.html"
---

一、前言

本文主要围绕IRQ number和中断描述符（interrupt descriptor）这两个概念描述通用中断处理过程。第二章主要描述基本概念，包括什么是IRQ number，什么是中断描述符等。第三章描述中断描述符数据结构的各个成员。第四章描述了初始化中断描述符相关的接口API。第五章描述中断描述符相关的接口API。

二、基本概念

1、通用中断的代码处理示意图

一个关于通用中断处理的示意图如下：

[![zhongduan](/content/uploadfile/201408/c1bc605fe5555c059b2e2e3196d2862a20140826100303.gif "zhongduan")](/content/uploadfile/201408/3e79044a4981e30f35e9b19fe44a441720140826100300.gif)

在linux kernel中，对于每一个外设的IRQ都用struct irq\_desc来描述，我们称之中断描述符（struct irq\_desc）。linux kernel中会有一个数据结构保存了关于所有IRQ的中断描述符信息，我们称之中断描述符DB（上图中红色框图内）。当发生中断后，首先获取触发中断的HW interupt ID，然后通过irq domain翻译成IRQ nuber，然后通过IRQ number就可以获取对应的中断描述符。调用中断描述符中的highlevel irq-events handler来进行中断处理就OK了。而highlevel irq-events handler主要进行下面两个操作：

（1）调用中断描述符的底层irq chip driver进行mask，ack等callback函数，进行interrupt flow control。

（2）调用该中断描述符上的action list中的specific handler（我们用这个术语来区分具体中断handler和high level的handler）。这个步骤不一定会执行，这是和中断描述符的当前状态相关，实际上，interrupt flow control是软件（设定一些标志位，软件根据标志位进行处理）和硬件（mask或者unmask interrupt controller等）一起控制完成的。

2、中断的打开和关闭

我们再来看看整个通用中断处理过程中的开关中断情况，开关中断有两种：

（1）开关local CPU的中断。对于UP，关闭CPU中断就关闭了一切，永远不会被抢占。对于SMP，实际上，没有关全局中断这一说，只能关闭local CPU（代码运行的那个CPU）

（2）控制interrupt controller，关闭某个IRQ number对应的中断。更准确的术语是mask或者unmask一个 IRQ。

本节主要描述的是第一种，也就是控制CPU的中断。当进入high level handler的时候，CPU的中断是关闭的（硬件在进入IRQ processor mode的时候设定的）。

对于外设的specific handler，旧的内核（2.6.35版本之前）认为有两种：slow handler和fast handle。在request irq的时候，对于fast handler，需要传递IRQF\_DISABLED的参数，确保其中断处理过程中是关闭CPU的中断，因为是fast handler，执行很快，即便是关闭CPU中断不会影响系统的性能。但是，并不是每一种外设中断的handler都是那么快（例如磁盘），因此就有slow handler的概念，说明其在中断处理过程中会耗时比较长。对于这种情况，如果在整个specific handler中关闭CPU中断，对系统的performance会有影响。因此，对于slow handler，在从high level handler转入specific handler中间会根据IRQF\_DISABLED这个flag来决定是否打开中断，具体代码如下（来自2.6.23内核）：

> irqreturn\_t handle\_IRQ\_event(unsigned int irq, struct irqaction \*action)   
> {   
> ……
>
> if (!(action->flags & IRQF\_DISABLED))   
> local\_irq\_enable\_in\_hardirq();
>
> ……   
> }

如果没有设定IRQF\_DISABLED（slow handler），则打开本CPU的中断。然而，随着软硬件技术的发展：

（1）硬件方面，CPU越来越快，原来slow handler也可以很快执行完毕

（2）软件方面，linux kernel提供了更多更好的bottom half的机制

因此，在新的内核中，比如3.14，IRQF\_DISABLED被废弃了。我们可以思考一下，为何要有slow handler？每一个handler不都是应该迅速执行完毕，返回中断现场吗？此外，任意中断可以打断slow handler执行，从而导致中断嵌套加深，对内核栈也是考验。因此，新的内核中在interrupt specific handler中是全程关闭CPU中断的。

3、IRQ number

从CPU的角度看，无论外部的Interrupt controller的结构是多么复杂，I do not care，我只关心发生了一个指定外设的中断，需要调用相应的外设中断的handler就OK了。更准确的说是通用中断处理模块不关心外部interrupt controller的组织细节（电源管理模块当然要关注具体的设备（interrupt controller也是设备）的拓扑结构）。一言以蔽之，通用中断处理模块可以用一个线性的table来管理一个个的外部中断，这个表的每个元素就是一个irq描述符，在kernel中定义如下：

> struct irq\_desc irq\_desc[NR\_IRQS] \_\_cacheline\_aligned\_in\_smp = {   
> [0 ... NR\_IRQS-1] = {   
> .handle\_irq = handle\_bad\_irq,   
> .depth = 1,   
> .lock = \_\_RAW\_SPIN\_LOCK\_UNLOCKED(irq\_desc->lock),   
> }   
> };

系统中每一个连接外设的中断线（irq request line）用一个中断描述符来描述，每一个外设的interrupt request line分配一个中断号（irq number），系统中有多少个中断线（或者叫做中断源）就有多少个中断描述符（struct irq\_desc）。NR\_IRQS定义了该硬件平台IRQ的最大数目。

总之，一个静态定义的表格，irq number作为index，每个描述符都是紧密的排在一起，一切看起来很美好，但是现实很残酷的。有些系统可能会定义一个很大的NR\_IRQS，但是只是想用其中的若干个，换句话说，这个静态定义的表格不是每个entry都是有效的，有空洞，如果使用静态定义的表格就会导致了内存很大的浪费。为什么会有这种需求？我猜是和各个interrupt controller硬件的interrupt ID映射到irq number的算法有关。在这种情况下，静态表格不适合了，我们改用一个radix tree来保存中断描述符（HW interrupt作为索引）。这时候，每一个中断描述符都是动态分配，然后插入到radix tree中。如果你的系统采用这种策略，那么需要打开CONFIG\_SPARSE\_IRQ选项。上面的示意图描述的是静态表格的中断描述符DB，如果打开CONFIG\_SPARSE\_IRQ选项，系统使用Radix tree来保存中断描述符DB，不过概念和静态表格是类似的。

此外，需要注意的是，在旧内核中，IRQ number和硬件的连接有一定的关系，但是，在引入irq domain后，IRQ number已经变成一个单纯的number，和硬件没有任何关系。

三、中断描述符数据结构

1、底层irq chip相关的数据结构

中断描述符中应该会包括底层irq chip相关的数据结构，linux kernel中把这些数据组织在一起，形成struct irq\_data，具体代码如下：

> struct irq\_data {   
> u32 mask;－－－－－－－－－－TODO   
> unsigned int irq;－－－－－－－－IRQ number   
> unsigned long hwirq;－－－－－－－HW interrupt ID   
> unsigned int node;－－－－－－－NUMA node index   
> unsigned int state\_use\_accessors;－－－－－－－－底层状态，参考IRQD\_xxxx   
> struct irq\_chip \*chip;－－－－－－－－－－该中断描述符对应的irq chip数据结构   
> struct irq\_domain \*domain;－－－－－－－－该中断描述符对应的irq domain数据结构   
> void \*handler\_data;－－－－－－－－和外设specific handler相关的私有数据   
> void \*chip\_data;－－－－－－－－－和中断控制器相关的私有数据   
> struct msi\_desc \*msi\_desc;   
> cpumask\_var\_t affinity;－－－－－－－和irq affinity相关   
> };

中断有两种形态，一种就是直接通过signal相连，用电平或者边缘触发。另外一种是基于消息的，被称为MSI (Message Signaled Interrupts)。msi\_desc是MSI类型的中断相关，这里不再描述。

node成员用来保存中断描述符的内存位于哪一个memory node上。 对于支持NUMA（Non Uniform Memory Access Architecture）的系统，其内存空间并不是均一的，而是被划分成不同的node，对于不同的memory node，CPU其访问速度是不一样的。如果一个IRQ大部分（或者固定）由某一个CPU处理，那么在动态分配中断描述符的时候，应该考虑将内存分配在该CPU访问速度比较快的memory node上。

2、irq chip数据结构

Interrupt controller描述符（struct irq\_chip）包括了若干和具体Interrupt controller相关的callback函数，我们总结如下：

|  |  |
| --- | --- |
| 成员名字 | 描述 |
| name | 该中断控制器的名字，用于/proc/interrupts中的显示 |
| irq\_startup | start up 指定的irq domain上的HW interrupt ID。如果不设定的话，default会被设定为enable函数 |
| irq\_shutdown | shutdown 指定的irq domain上的HW interrupt ID。如果不设定的话，default会被设定为disable函数 |
| irq\_enable | enable指定的irq domain上的HW interrupt ID。如果不设定的话，default会被设定为unmask函数 |
| irq\_disable | disable指定的irq domain上的HW interrupt ID。 |
| irq\_ack | 和具体的硬件相关，有些中断控制器必须在Ack之后（清除pending的状态）才能接受到新的中断。 |
| irq\_mask | mask指定的irq domain上的HW interrupt ID |
| irq\_mask\_ack | mask并ack指定的irq domain上的HW interrupt ID。 |
| irq\_unmask | mask指定的irq domain上的HW interrupt ID |
| irq\_eoi | 有些interrupt controler（例如GIC）提供了这样的寄存器接口，让CPU可以通知interrupt controller，它已经处理完一个中断 |
| irq\_set\_affinity | 在SMP的情况下，可以通过该callback函数设定CPU affinity |
| irq\_retrigger | 重新触发一次中断，一般用在中断丢失的场景下。如果硬件不支持retrigger，可以使用软件的方法。 |
| irq\_set\_type | 设定指定的irq domain上的HW interrupt ID的触发方式，电平触发还是边缘触发 |
| irq\_set\_wake | 和电源管理相关，用来enable/disable指定的interrupt source作为唤醒的条件。 |
| irq\_bus\_lock | 有些interrupt controller是连接到慢速总线上（例如一个i2c接口的IO expander芯片），在访问这些芯片的时候需要lock住那个慢速bus（只能有一个client在使用I2C bus） |
| irq\_bus\_sync\_unlock | unlock慢速总线 |
| irq\_suspend    irq\_resume    irq\_pm\_shutdown | 电源管理相关的callback函数 |
| irq\_calc\_mask | TODO |
| irq\_print\_chip | /proc/interrupts中的信息显示 |

3、中断描述符

在linux kernel中，使用struct irq\_desc来描述一个外设的中断，我们称之中断描述符，具体代码如下：

> struct irq\_desc {   
> struct irq\_data irq\_data;   
> unsigned int \_\_percpu \*kstat\_irqs;－－－－－－IRQ的统计信息   
> irq\_flow\_handler\_t handle\_irq;－－－－－－－－（1）   
> struct irqaction \*action; －－－－－－－－－－－（2）   
> unsigned int status\_use\_accessors;－－－－－中断描述符的状态，参考IRQ\_xxxx   
> unsigned int core\_internal\_state\_\_do\_not\_mess\_with\_it;－－－－（3）   
> unsigned int depth;－－－－－－－－－－（4）   
> unsigned int wake\_depth;－－－－－－－－（5）   
> unsigned int irq\_count; －－－－－－－－－（6）   
> unsigned long last\_unhandled;   
> unsigned int irqs\_unhandled;   
> raw\_spinlock\_t lock;－－－－－－－－－－－（7）   
> struct cpumask \*percpu\_enabled;－－－－－－－（8）   
> #ifdef CONFIG\_SMP   
> const struct cpumask \*affinity\_hint;－－－－和irq affinity相关，后续单独文档描述   
> struct irq\_affinity\_notify \*affinity\_notify;   
> #ifdef CONFIG\_GENERIC\_PENDING\_IRQ   
> cpumask\_var\_t pending\_mask;   
> #endif   
> #endif   
> unsigned long threads\_oneshot; －－－－－（9）   
> atomic\_t threads\_active;   
> wait\_queue\_head\_t wait\_for\_threads;   
> #ifdef CONFIG\_PROC\_FS   
> struct proc\_dir\_entry \*dir;－－－－－－－－该IRQ对应的proc接口   
> #endif   
> int parent\_irq;   
> struct module \*owner;   
> const char \*name;   
> } \_\_\_\_cacheline\_internodealigned\_in\_smp

（1）handle\_irq就是highlevel irq-events handler，何谓high level？站在高处自然看不到细节。我认为high level是和specific相对，specific handler处理具体的事务，例如处理一个按键中断、处理一个磁盘中断。而high level则是对处理各种中断交互过程的一个抽象，根据下列硬件的不同：

（a）中断控制器

（b）IRQ trigger type

highlevel irq-events handler可以分成：

（a）处理电平触发类型的中断handler（handle\_level\_irq）

（b）处理边缘触发类型的中断handler（handle\_edge\_irq）

（c）处理简单类型的中断handler（handle\_simple\_irq）

（d）处理EOI类型的中断handler（handle\_fasteoi\_irq）

会另外有一份文档对high level handler进行更详细的描述。

（2）action指向一个struct irqaction的链表。如果一个interrupt request line允许共享，那么该链表中的成员可以是多个，否则，该链表只有一个节点。

（3）这个有着很长名字的符号core\_internal\_state\_\_do\_not\_mess\_with\_it在具体使用的时候被被简化成istate，表示internal state。就像这个名字定义的那样，我们最好不要直接修改它。

> #define istate core\_internal\_state\_\_do\_not\_mess\_with\_it

（4）我们可以通过enable和disable一个指定的IRQ来控制内核的并发，从而保护临界区的数据。对一个IRQ进行enable和disable的操作可以嵌套（当然一定要成对使用），depth是描述嵌套深度的信息。

（5）wake\_depth是和电源管理中的wake up source相关。通过irq\_set\_irq\_wake接口可以enable或者disable一个IRQ中断是否可以把系统从suspend状态唤醒。同样的，对一个IRQ进行wakeup source的enable和disable的操作可以嵌套（当然一定要成对使用），wake\_depth是描述嵌套深度的信息。

（6）irq\_count、last\_unhandled和irqs\_unhandled用于处理broken IRQ 的处理。所谓broken IRQ就是由于种种原因（例如错误firmware），IRQ handler没有定向到指定的IRQ上，当一个IRQ没有被处理的时候，kernel可以为这个没有被处理的handler启动scan过程，让系统中所有的handler来认领该IRQ。

（7）保护该中断描述符的spin lock。

（8）一个中断描述符可能会有两种情况，一种是该IRQ是global，一旦disable了该irq，那么对于所有的CPU而言都是disable的。还有一种情况，就是该IRQ是per CPU的，也就是说，在某个CPU上disable了该irq只是disable了本CPU的IRQ而已，其他的CPU仍然是enable的。percpu\_enabled是一个描述该IRQ在各个CPU上是否enable成员。

（9）threads\_oneshot、threads\_active和wait\_for\_threads是和IRQ thread相关，后续文档会专门描述。

四、初始化相关的中断描述符的接口

1、静态定义的中断描述符初始化

> int \_\_init early\_irq\_init(void)   
> {   
> int count, i, node = first\_online\_node;   
> struct irq\_desc \*desc;
>
> init\_irq\_default\_affinity();
>
> desc = irq\_desc;   
> count = ARRAY\_SIZE(irq\_desc);
>
> for (i = 0; i < count; i++) {－－－遍历整个lookup table，对每一个entry进行初始化   
> desc[i].kstat\_irqs = alloc\_percpu(unsigned int);－－－分配per cpu的irq统计信息需要的内存   
> alloc\_masks(&desc[i], GFP\_KERNEL, node);－－－分配中断描述符中需要的cpu mask内存   
> raw\_spin\_lock\_init(&desc[i].lock);－－－初始化spin lock   
> lockdep\_set\_class(&desc[i].lock, &irq\_desc\_lock\_class);   
> desc\_set\_defaults(i, &desc[i], node, NULL);－－－设定default值   
> }   
> return arch\_early\_irq\_init();－－－调用arch相关的初始化函数   
> }

2、使用Radix tree的中断描述符初始化

> int \_\_init early\_irq\_init(void)   
> {……
>
> initcnt = arch\_probe\_nr\_irqs();－－－体系结构相关的代码来决定预先分配的中断描述符的个数
>
> if (initcnt > nr\_irqs)－－－initcnt是需要在初始化的时候预分配的IRQ的个数   
> nr\_irqs = initcnt; －－－nr\_irqs是当前系统中IRQ number的最大值
>
> for (i = 0; i < initcnt; i++) {－－－－－－－－预先分配initcnt个中断描述符   
> desc = alloc\_desc(i, node, NULL);－－－分配中断描述符   
> set\_bit(i, allocated\_irqs);－－－设定已经alloc的flag   
> irq\_insert\_desc(i, desc);－－－－－插入radix tree   
> }   
> ……   
> }

即便是配置了CONFIG\_SPARSE\_IRQ选项，在中断描述符初始化的时候，也有机会预先分配一定数量的IRQ。这个数量由arch\_probe\_nr\_irqs决定，对于ARM而言，其arch\_probe\_nr\_irqs定义如下：

> int \_\_init arch\_probe\_nr\_irqs(void)   
> {   
> nr\_irqs = machine\_desc->nr\_irqs ? machine\_desc->nr\_irqs : NR\_IRQS;   
> return nr\_irqs;   
> }

3、分配和释放中断描述符

对于使用Radix tree来保存中断描述符DB的linux kernel，其中断描述符是动态分配的，可以使用irq\_alloc\_descs和irq\_free\_descs来分配和释放中断描述符。alloc\_desc函数也会对中断描述符进行初始化，初始化的内容和静态定义的中断描述符初始化过程是一样的。最大可以分配的ID是IRQ\_BITMAP\_BITS，定义如下：

> #ifdef CONFIG\_SPARSE\_IRQ   
> # define IRQ\_BITMAP\_BITS (NR\_IRQS + 8196)－－－对于Radix tree，除了预分配的，还可以动态   
> #else 分配8196个中断描述符   
> # define IRQ\_BITMAP\_BITS NR\_IRQS－－－对于静态定义的，IRQ最大值就是NR\_IRQS   
> #endif

五、和中断控制器相关的中断描述符的接口

这部分的接口主要有两类，irq\_desc\_get\_xxx和irq\_set\_xxx，由于get接口API非常简单，这里不再描述，主要描述set类别的接口API。此外，还有一些locked版本的set接口API，定义为\_\_irq\_set\_xxx，这些API的调用者应该已经持有保护irq desc的spinlock，因此，这些locked版本的接口没有中断描述符的spin lock进行操作。这些接口有自己特定的使用场合，这里也不详细描述了。

1、接口调用时机

kernel提供了若干的接口API可以让内核其他模块可以操作指定IRQ number的描述符结构。中断描述符中有很多的成员是和底层的中断控制器相关，例如：

（1）该中断描述符对应的irq chip

（2）该中断描述符对应的irq trigger type

（3）high level handler

在过去，系统中各个IRQ number是固定分配的，各个IRQ对应的中断控制器、触发类型等也都是清楚的，因此，一般都是在machine driver初始化的时候一次性的进行设定。machine driver的初始化过程会包括中断系统的初始化，在machine driver的中断初始化函数中，会调用本文定义的这些接口对各个IRQ number对应的中断描述符进行irq chip、触发类型的设定。

在引入了device tree、动态分配IRQ number以及irq domain这些概念之后，这些接口的调用时机移到各个中断控制器的初始化以及各个具体硬件驱动初始化过程中，具体如下：

（1）各个中断控制器定义好自己的struct irq\_domain\_ops callback函数，主要是map和translate函数。

（2）在各个具体的硬件驱动初始化过程中，通过device tree系统可以知道自己的中断信息（连接到哪一个interrupt controler、使用该interrupt controller的那个HW interrupt ID，trigger type为何），调用对应的irq domain的translate进行翻译、解析。之后可以动态申请一个IRQ number并和该硬件外设的HW interrupt ID进行映射，调用irq domain对应的map函数。在map函数中，可以调用本节定义的接口进行中断描述符底层interrupt controller相关信息的设定。

2、irq\_set\_chip

这个接口函数用来设定中断描述符中desc->irq\_data.chip成员，具体代码如下：

> int irq\_set\_chip(unsigned int irq, struct irq\_chip \*chip)   
> {   
> unsigned long flags;   
> struct irq\_desc \*desc = irq\_get\_desc\_lock(irq, &flags, 0); －－－－（1）
>
> desc->irq\_data.chip = chip;   
> irq\_put\_desc\_unlock(desc, flags);－－－－－－－－－－－－－－－（2）   
>   
> irq\_reserve\_irq(irq);－－－－－－－－－－－－－－－－－－－－－－（3）   
> return 0;   
> }

（1）获取irq number对应的中断描述符。这里用关闭中断＋spin lock来保护中断描述符，flag中就是保存的关闭中断之前的状态flag，后面在（2）中会恢复中断flag。

（3）前面我们说过，irq number有静态表格定义的，也有radix tree类型的。对于静态定义的中断描述符，没有alloc的概念。但是，对于radix tree类型，需要首先irq\_alloc\_desc或者irq\_alloc\_descs来分配一个或者一组IRQ number，在这些alloc函数值，就会set那些那些已经分配的IRQ。对于静态表格而言，其IRQ没有分配，因此，这里通过irq\_reserve\_irq函数标识该IRQ已经分配，虽然对于CONFIG\_SPARSE\_IRQ（使用radix tree）的配置而言，这个操作重复了（在alloc的时候已经设定了）。

3、irq\_set\_irq\_type

这个函数是用来设定该irq number的trigger type的。

> int irq\_set\_irq\_type(unsigned int irq, unsigned int type)   
> {   
> unsigned long flags;   
> struct irq\_desc \*desc = irq\_get\_desc\_buslock(irq, &flags, IRQ\_GET\_DESC\_CHECK\_GLOBAL);   
> int ret = 0;
>
> type &= IRQ\_TYPE\_SENSE\_MASK;   
> ret = \_\_irq\_set\_trigger(desc, irq, type);   
> irq\_put\_desc\_busunlock(desc, flags);   
> return ret;   
> }

来到这个接口函数，第一个问题就是：为何irq\_set\_chip接口函数使用irq\_get\_desc\_lock来获取中断描述符，而irq\_set\_irq\_type这个函数却需要irq\_get\_desc\_buslock呢？其实也很简单，irq\_set\_chip不需要访问底层的irq chip（也就是interrupt controller），但是irq\_set\_irq\_type需要。设定一个IRQ的trigger type最终要调用desc->irq\_data.chip->irq\_set\_type函数对底层的interrupt controller进行设定。这时候，问题来了，对于嵌入SOC内部的interrupt controller，当然没有问题，因为访问这些中断控制器的寄存器memory map到了CPU的地址空间，访问非常的快，因此，关闭中断＋spin lock来保护中断描述符当然没有问题，但是，如果该interrupt controller是一个I2C接口的IO expander芯片（这类芯片是扩展的IO，也可以提供中断功能），这时，让其他CPU进行spin操作太浪费CPU时间了（bus操作太慢了，会spin很久的）。肿么办？当然只能是用其他方法lock住bus了（例如mutex，具体实现是和irq chip中的irq\_bus\_lock实现相关）。一旦lock住了slow bus，然后就可以关闭中断了（中断状态保存在flag中）。

解决了bus lock的疑问后，还有一个看起来奇奇怪怪的宏：IRQ\_GET\_DESC\_CHECK\_GLOBAL。为何在irq\_set\_chip函数中不设定检查（check的参数是0），而在irq\_set\_irq\_type接口函数中要设定global的check，到底是什么意思呢？既然要检查，那么检查什么呢？和“global”对应的不是local而是“per CPU”，内核中的宏定义是：IRQ\_GET\_DESC\_CHECK\_PERCPU。SMP情况下，从系统角度看，中断有两种形态（或者叫mode）：

（1）1-N mode。只有1个processor处理中断

（2）N-N mode。所有的processor都是独立的收到中断，如果有N个processor收到中断，那么就有N个处理器来处理该中断。

听起来有些抽象，我们还是用GIC作为例子来具体描述。在GIC中，SPI使用1-N模型，而PPI和SGI使用N-N模型。对于SPI，由于采用了1-N模型，系统（硬件加上软件）必须保证一个中断被一个CPU处理。对于GIC，一个SPI的中断可以trigger多个CPU的interrupt line（如果Distributor中的Interrupt Processor Targets Registers有多个bit被设定），但是，该interrupt source和CPU的接口寄存器（例如ack
register）只有一套，也就是说，这些寄存器接口是全局的，是global的，一旦一个CPU
ack（读Interrupt Acknowledge Register，获取interrupt ID）了该中断，那么其他的CPU看到的该interupt source的状态也是已经ack的状态。在这种情况下，如果第二个CPU ack该中断的时候，将获取一个spurious interrupt ID。

对于PPI或者SGI，使用N-N mode，其interrupt source的寄存器是per CPU的，也就是每个CPU都有自己的、针对该interrupt source的寄存器接口（这些寄存器叫做banked register）。一个CPU 清除了该interrupt source的pending状态，其他的CPU感知不到这个变化，它们仍然认为该中断是pending的。

对于irq\_set\_irq\_type这个接口函数，它是for 1-N mode的interrupt source使用的。如果底层设定该interrupt是per CPU的，那么irq\_set\_irq\_type要返回错误。

4、irq\_set\_chip\_data

每个irq chip总有自己私有的数据，我们称之chip data。具体设定chip data的代码如下：

> int irq\_set\_chip\_data(unsigned int irq, void \*data)   
> {   
> unsigned long flags;   
> struct irq\_desc \*desc = irq\_get\_desc\_lock(irq, &flags, 0);   
> desc->irq\_data.chip\_data = data;   
> irq\_put\_desc\_unlock(desc, flags);   
> return 0;   
> }

多么清晰、多么明了，需要文字继续描述吗？

5、设定high level handler

这是中断处理的核心内容，\_\_irq\_set\_handler就是设定high level handler的接口函数，不过一般不会直接调用，而是通过irq\_set\_chip\_and\_handler\_name或者irq\_set\_chip\_and\_handler来进行设定。具体代码如下：

> void \_\_irq\_set\_handler(unsigned int irq, irq\_flow\_handler\_t handle, int is\_chained, const char \*name)   
> {   
> unsigned long flags;   
> struct irq\_desc \*desc = irq\_get\_desc\_buslock(irq, &flags, 0);
>
> ……   
> desc->handle\_irq = handle;   
> desc->name = name;
>
> if (handle != handle\_bad\_irq && is\_chained) {   
> irq\_settings\_set\_noprobe(desc);   
> irq\_settings\_set\_norequest(desc);   
> irq\_settings\_set\_nothread(desc);   
> irq\_startup(desc, true);   
> }   
> out:   
> irq\_put\_desc\_busunlock(desc, flags);   
> }

理解这个函数的关键是在is\_chained这个参数。这个参数是用在interrupt级联的情况下。例如中断控制器B级联到中断控制器A的第x个interrupt source上。那么对于A上的x这个interrupt而言，在设定其IRQ handler参数的时候要设定is\_chained参数等于1，由于这个interrupt source用于级联，因此不能probe、不能被request（已经被中断控制器B使用了），不能被threaded（具体中断线程化的概念在其他文档中描述）

*原创文章，转发请注明出处。蜗窝科技。*[/irq_subsystem/interrupt_descriptor.html](/irq_subsystem/interrupt_descriptor.html)
