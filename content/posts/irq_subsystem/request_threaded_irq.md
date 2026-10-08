---
title: "Linux kernel中断子系统之（五）：驱动申请中断API"
date: 2014-09-22T18:33:36+08:00
url: "/irq_subsystem/request_threaded_irq.html"
gid: "91"
emlog_type: "blog"
summary: "本文主要的议题是作为一个普通的驱动工程师，在撰写自己负责的驱动的时候，如何向Linux \r\nKernel中的中断子系统注册中断处理函数？为了理解注册中断的接口，必须了解一些中断线程化（threaded interrupt \r\nhandler）的基础知识，这些在第二章描述。第三章主要描述了驱动申请 interrupt line接口API \r\nrequest_threaded_irq的规格。第四章是进"
author: "linuxer"
category: "中断子系统"
category_alias: "irq_subsystem"
tags: ["request_threaded_irq"]
views: 138529
comment_count: 75
aliases:
  - "/irq_subsystem/91.html"
  - "/91.html"
---

一、前言

本文主要的议题是作为一个普通的驱动工程师，在撰写自己负责的驱动的时候，如何向Linux Kernel中的中断子系统注册中断处理函数？为了理解注册中断的接口，必须了解一些中断线程化（threaded interrupt handler）的基础知识，这些在第二章描述。第三章主要描述了驱动申请 interrupt line接口API request\_threaded\_irq的规格。第四章是进入request\_threaded\_irq的实现细节，分析整个代码的执行过程。

二、和中断相关的linux实时性分析以及中断线程化的背景介绍

1、非抢占式linux内核的实时性

在遥远的过去，linux2.4之前的内核是不支持抢占特性的，具体可以参考下图：

[![sxw](/content/uploadfile/201409/89cc8133ade45f46ce400d3d2d74ce6f20140922103326.gif "sxw")](/content/uploadfile/201409/e31cc1446eefc8742e5f01648fadba8a20140922103324.gif)

事情的开始源自高优先级任务（橘色block）由于要等待外部事件（例如网络数据）而进入睡眠，调度器调度了某个低优先级的任务（紫色block）执行。该低优先级任务欢畅的执行，直到触发了一次系统调用（例如通过read()文件接口读取磁盘上的文件等）而进入了内核态。仍然是熟悉的配方，仍然是熟悉的味道，低优先级任务正在执行不会变化，只不过从user space切换到了kernel space。外部事件总是在你不想让它来的时候到来，T0时刻，高优先级任务等待的那个中断事件发生了。

中断虽然发生了，但软件不一定立刻响应，可能由于在内核态执行的某些操作不希望被外部事件打断而主动关闭了中断（或是关闭了CPU的中断，或者MASK了该IRQ number），这时候，中断信号没有立刻得到响应，软件仍然在内核态执行低优先级任务系统调用的代码。在T1时刻，内核态代码由于退出临界区而打开中断（注意：上图中的比例是不协调的，一般而言，linux kernel不会有那么长的关中断时间，上面主要是为了表示清楚，同理，从中断触发到具体中断服务程序的执行也没有那么长，都是为了表述清楚），中断一旦打开，立刻跳转到了异常向量地址，interrupt handler抢占了低优先级任务的执行，进入中断上下文（虽然这时候的current task是低优先级任务，但是中断上下文和它没有任何关系）。

从CPU开始处理中断到具体中断服务程序被执行还需要一个分发的过程。这个期间系统要做的主要操作包括确定HW interrupt ID，确定IRQ Number，ack或者mask中断，调用中断服务程序等。T0到T2之间的delay被称为中断延迟（Interrupt Latency），主要包括两部分，一部分是HW造成的delay（硬件的中断系统识别外部的中断事件并signal到CPU），另外一部分是软件原因（内核代码中由于要保护临界区而关闭中断引起的）。

该中断的服务程序执行完毕（在其执行过程中，T3时刻，会唤醒高优先级任务，让它从sleep状态进入runable状态），返回低优先级任务的系统调用现场，这时候并不存在一个抢占点，低优先级任务要完成系统调用之后，在返回用户空间的时候才出现抢占点。漫长的等待之后，T4时刻，调度器调度高优先级任务执行。有一个术语叫做任务响应时间（Task Response Time）用来描述T3到T4之间的delay。

2、抢占式linux内核的实时性

2.6内核和2.4内核显著的不同是提供了一个CONFIG\_PREEMPT的选项，打开该选项后，linux kernel就支持了内核代码的抢占（当然不能在临界区），其行为如下：

[![pre](/content/uploadfile/201409/5d3893a4997db31f1bcbec9c8446b98020140922103329.gif "pre")](/content/uploadfile/201409/ed95106e2c04e02b2ba84fe038d70f2220140922103327.gif)

T0到T3的操作都是和上一节的描述一样的，不同的地方是在T4。对于2.4内核，只有返回用户空间的时候才有抢占点出现，但是对于抢占式内核而言，即便是从中断上下文返回内核空间的进程上下文，只要内核代码不在临界区内，就可以发生调度，让最高优先级的任务调度执行。

在非抢占式linux内核中，一个任务的内核态是不可以被其他进程抢占的。这里并不是说kernel space不可以被抢占，只是说进程通过系统调用陷入到内核的时候，不可以被其他的进程抢占。实际上，中断上下文当然可以抢占进程上下文（无论是内核态还是用户态），更进一步，中断上下文是拥有至高无上的权限，它甚至可以抢占其他的中断上下文。引入抢占式内核后，系统的平均任务响应时间会缩短，但是，实时性更关注的是：无论在任何的负载情况下，任务响应时间是确定的。因此，更需要关注的是worst-case的任务响应时间。这里有两个因素会影响worst case latency：

（1）为了同步，内核中总有些代码需要持有自旋锁资源，或者显式的调用preempt\_disable来禁止抢占，这时候不允许抢占

（2）中断上下文（并非只是中断handler，还包括softirq、timer、tasklet）总是可以抢占进程上下文

因此，即便是打开了PREEMPT的选项，实际上linux系统的任务响应时间仍然是不确定的。一方面内核代码的临界区非常多，我们需要找到，系统中持有锁，或者禁止抢占的最大的时间片。另外一方面，在上图的T4中，能顺利的调度高优先级任务并非易事，这时候可能有触发的软中断，也可能有新来的中断，也可能某些driver的tasklet要执行，只有在没有任何bottom half的任务要执行的时候，调度器才会启动调度。

3、进一步提高linux内核的实时性

通过上一个小节的描述，相信大家都确信中断对linux 实时性的最大的敌人。那么怎么破？我曾经接触过一款RTOS，它的中断handler非常简单，就是发送一个inter-task message到该driver thread，对任何的一个驱动都是如此处理。这样，每个中断上下文都变得非常简短，而且每个中断都是一致的。在这样的设计中，外设中断的处理线程化了，然后，系统设计师要仔细的为每个系统中的task分配优先级，确保整个系统的实时性。

在Linux kernel中，一个外设的中断处理被分成top half和bottom half，top half进行最关键，最基本的处理，而比较耗时的操作被放到bottom half（softirq、tasklet）中延迟执行。虽然bottom half被延迟执行，但始终都是先于进程执行的。为何不让这些耗时的bottom half和普通进程公平竞争呢？因此，linux kernel借鉴了RTOS的某些特性，对那些耗时的驱动interrupt handler进行线程化处理，在内核的抢占点上，让线程（无论是内核线程还是用户空间创建的线程，还是驱动的interrupt thread）在一个舞台上竞争CPU。

三、request\_threaded\_irq的接口规格

1、输入参数描述

|  |  |
| --- | --- |
| 输入参数 | 描述 |
| irq | 要注册handler的那个IRQ number。这里要注册的handler包括两个，一个是传统意义的中断handler，我们称之primary handler，另外一个是threaded interrupt handler |
| handler | primary handler。需要注意的是primary handler和threaded interrupt handler不能同时为空，否则会出错 |
| thread\_fn | threaded interrupt handler。如果该参数不是NULL，那么系统会创建一个kernel thread，调用的function就是thread\_fn |
| irqflags | 参见本章第三节 |
| devname |  |
| dev\_id | 参见第四章，第一节中的描述。 |

2、输出参数描述

0表示成功执行，负数表示各种错误原因。

3、Interrupt type flags

|  |  |
| --- | --- |
| flag定义 | 描述 |
| IRQF\_TRIGGER\_XXX | 描述该interrupt line触发类型的flag |
| IRQF\_DISABLED | 首先要说明的是这是一个废弃的flag，在新的内核中，该flag没有任何的作用了。具体可以参考：[Disabling IRQF\_DISABLED](http://lwn.net/Articles/380931/ "http://lwn.net/Articles/380931/")   旧的内核（2.6.35版本之前）认为有两种interrupt handler：slow handler和fast handle。在request irq的时候，对于fast handler，需要传递IRQF\_DISABLED的参数，确保其中断处理过程中是关闭CPU的中断，因为是fast handler，执行很快，即便是关闭CPU中断不会影响系统的性能。但是，并不是每一种外设中断的handler都是那么快（例如磁盘），因此就有 slow handler的概念，说明其在中断处理过程中会耗时比较长。对于这种情况，在执行interrupt handler的时候不能关闭CPU中断，否则对系统的performance会有影响。    新的内核已经不区分slow handler和fast handle，都是fast handler，都是需要关闭CPU中断的，那些需要后续处理的内容推到threaded interrupt handler中去执行。 |
| IRQF\_SHARED | 这是flag用来描述一个interrupt line是否允许在多个设备中共享。如果中断控制器可以支持足够多的interrupt source，那么在两个外设间共享一个interrupt request line是不推荐的，毕竟有一些额外的开销（发生中断的时候要逐个询问是不是你的中断，软件上就是遍历action list），因此外设的irq handler中最好是一开始就启动判断，看看是否是自己的中断，如果不是，返回IRQ\_NONE,表示这个中断不归我管。 早期PC时代，使用8259中断控制器，级联的8259最多支持15个外部中断，但是PC外设那么多，因此需要irq share。现在，ARM平台上的系统设计很少会采用外设共享IRQ方式，毕竟一般ARM SOC提供的有中断功能的GPIO非常的多，足够用的。 当然，如果确实需要两个外设共享IRQ，那也只能如此设计了。对于HW，中断控制器的一个interrupt source的引脚要接到两个外设的interrupt request line上，怎么接？直接连接可以吗？当然不行，对于低电平触发的情况，我们可以考虑用与门连接中断控制器和外设。 |
| IRQF\_PROBE\_SHARED | IRQF\_SHARED用来表示该interrupt action descriptor是允许和其他device共享一个interrupt line（IRQ number），但是实际上是否能够share还是需要其他条件：例如触发方式必须相同。有些驱动程序可能有这样的调用场景：我只是想scan一个irq table，看看哪一个是OK的，这时候，如果即便是不能和其他的驱动程序share这个interrupt line，我也没有关系，我就是想scan看看情况。这时候，caller其实可以预见sharing mismatche的发生，因此，不需要内核打印“Flags mismatch irq……“这样冗余的信息 |
| IRQF\_PERCPU | 在SMP的架构下，中断有两种mode，一种中断是在所有processor之间共享的，也就是global的，一旦中断产生，interrupt controller可以把这个中断送达多个处理器。当然，在具体实现的时候不会同时将中断送达多个CPU，一般是软件和硬件协同处理，将中断送达一个CPU处理。但是一段时间内产生的中断可以平均（或者按照既定的策略）分配到一组CPU上。这种interrupt mode下，interrupt controller针对该中断的operational register是global的，所有的CPU看到的都是一套寄存器，一旦一个CPU ack了该中断，那么其他的CPU看到的该interupt source的状态也是已经ack的状态。    和global对应的就是per cpu interrupt了，对于这种interrupt，不是processor之间共享的，而是特定属于一个CPU的。例如GIC中interrupt ID等于30的中断就是per cpu的（这个中断event被用于各个CPU的local timer），这个中断号虽然只有一个，但是，实际上控制该interrupt ID的寄存器有n组（如果系统中有n个processor），每个CPU看到的是不同的控制寄存器。在具体实现中，这些寄存器组有两种形态，一种是banked，所有CPU操作同样的寄存器地址，硬件系统会根据访问的cpu定向到不同的寄存器，另外一种是non banked，也就是说，对于该interrupt source，每个cpu都有自己独特的访问地址。 |
| IRQF\_NOBALANCING | 这也是和multi-processor相关的一个flag。对于那些可以在多个CPU之间共享的中断，具体送达哪一个processor是有策略的，我们可以在多个CPU之间进行平衡。如果你不想让你的中断参与到irq balancing的过程中那么就设定这个flag |
| IRQF\_IRQPOLL |  |
| IRQF\_ONESHOT | one shot本身的意思的只有一次的，结合到中断这个场景，则表示中断是一次性触发的，不能嵌套。对于primary handler，当然是不会嵌套，但是对于threaded interrupt handler，我们有两种选择，一种是mask该interrupt source，另外一种是unmask该interrupt source。一旦mask住该interrupt source，那么该interrupt source的中断在整个threaded interrupt handler处理过程中都是不会再次触发的，也就是one shot了。这种handler不需要考虑重入问题。    具体是否要设定one shot的flag是和硬件系统有关的，我们举一个例子，比如电池驱动，电池里面有一个电量计，是使用HDQ协议进行通信的，电池驱动会注册一个threaded interrupt handler，在这个handler中，会通过HDQ协议和电量计进行通信。对于这个handler，通过HDQ进行通信是需要一个完整的HDQ交互过程，如果中间被打断，整个通信过程会出问题，因此，这个handler就必须是one shot的。 |
| IRQF\_NO\_SUSPEND | 这个flag比较好理解，就是说在系统suspend的时候，不用disable这个中断，如果disable，可能会导致系统不能正常的resume。 |
| IRQF\_FORCE\_RESUME | 在系统resume的过程中，强制必须进行enable的动作，即便是设定了IRQF\_NO\_SUSPEND这个flag。这是和特定的硬件行为相关的。 |
| IRQF\_NO\_THREAD | 有些low level的interrupt是不能线程化的（例如系统timer的中断），这个flag就是起这个作用的。另外，有些级联的interrupt controller对应的IRQ也是不能线程化的（例如secondary GIC对应的IRQ），它的线程化可能会影响一大批附属于该interrupt controller的外设的中断响应延迟。 |
| IRQF\_EARLY\_RESUME |  |
| IRQF\_TIMER |  |

四、request\_threaded\_irq代码分析

1、request\_threaded\_irq主流程

> int request\_threaded\_irq(unsigned int irq, irq\_handler\_t handler,   
> irq\_handler\_t thread\_fn, unsigned long irqflags,   
> const char \*devname, void \*dev\_id)   
> {   
> if ((irqflags & IRQF\_SHARED) && !dev\_id)－－－－－－－－－（1）   
> return -EINVAL;
>
> desc = irq\_to\_desc(irq); －－－－－－－－－－－－－－－－－（2）   
> if (!desc) return -EINVAL;
>
> if (!irq\_settings\_can\_request(desc) || －－－－－－－－－－－－（3）   
> WARN\_ON(irq\_settings\_is\_per\_cpu\_devid(desc)))   
> return -EINVAL;
>
> if (!handler) { －－－－－－－－－－－－－－－－－－－－－－（4）   
> if (!thread\_fn)   
> return -EINVAL;   
> handler = irq\_default\_primary\_handler;   
> }
>
> action = kzalloc(sizeof(struct irqaction), GFP\_KERNEL);
>
> action->handler = handler;   
> action->thread\_fn = thread\_fn;   
> action->flags = irqflags;   
> action->name = devname;   
> action->dev\_id = dev\_id;
>
> chip\_bus\_lock(desc);   
> retval = \_\_setup\_irq(irq, desc, action); －－－－－－－－－－－（5）   
> chip\_bus\_sync\_unlock(desc);   
> }

（1）对于那些需要共享的中断，在request irq的时候需要给出dev id，否则会出错退出。为何对于IRQF\_SHARED的中断必须要给出dev id呢？实际上，在共享的情况下，一个IRQ number对应若干个irqaction，当操作irqaction的时候，仅仅给出IRQ number就不是非常的足够了，这时候，需要一个ID表示具体的irqaction，这里就是dev\_id的作用了。我们举一个例子：

> void free\_irq(unsigned int irq, void \*dev\_id)

当释放一个IRQ资源的时候，不但要给出IRQ number，还要给出device ID。只有这样，才能精准的把要释放的那个irqaction 从irq action list上移除。dev\_id在中断处理中有没有作用呢？我们来看看source code：

> irqreturn\_t handle\_irq\_event\_percpu(struct irq\_desc \*desc, struct irqaction \*action)   
> {
>
> do {   
> irqreturn\_t res;   
> res = action->handler(irq, action->dev\_id);
>
> ……   
> action = action->next;   
> } while (action);
>
> ……   
> }

linux interrupt framework虽然支持中断共享，但是它并不会协助解决识别问题，它只会遍历该IRQ number上注册的irqaction的callback函数，这样，虽然只是一个外设产生的中断，linux kernel还是把所有共享的那些中断handler都逐个调用执行。为了让系统的performance不受影响，irqaction的callback函数必须在函数的最开始进行判断，是否是自己的硬件设备产生了中断（读取硬件的寄存器），如果不是，尽快的退出。

需要注意的是，这里dev\_id并不能在中断触发的时候用来标识需要调用哪一个irqaction的callback函数，通过上面的代码也可以看出，dev\_id有些类似一个参数传递的过程，可以把具体driver的一些硬件信息，组合成一个structure，在触发中断的时候可以把这个structure传递给中断处理函数。

（2）通过IRQ number获取对应的中断描述符。在引入CONFIG\_SPARSE\_IRQ选项后，这个转换变得不是那么简单了。在过去，我们会以IRQ number为index，从irq\_desc这个全局数组中直接获取中断描述符。如果配置CONFIG\_SPARSE\_IRQ选项，则需要从radix tree中搜索。CONFIG\_SPARSE\_IRQ选项的更详细的介绍请参考[IRQ number和中断描述符](/irq_subsystem/interrupt_descriptor.html)

（3）并非系统中所有的IRQ number都可以request，有些中断描述符被标记为IRQ\_NOREQUEST，标识该IRQ number不能被其他的驱动request。一般而言，这些IRQ number有特殊的作用，例如用于级联的那个IRQ number是不能request。irq\_settings\_can\_request函数就是判断一个IRQ是否可以被request。

irq\_settings\_is\_per\_cpu\_devid函数用来判断一个中断描述符是否需要传递per cpu的device ID。per cpu的中断上面已经描述的很清楚了，这里不再细述。如果一个中断描述符对应的中断 ID是per cpu的，那么在申请其handler的时候就有两种情况，一种是传递统一的dev\_id参数（传入request\_threaded\_irq的最后一个参数），另外一种情况是针对每个CPU，传递不同的dev\_id参数。在这种情况下，我们需要调用request\_percpu\_irq接口函数而不是request\_threaded\_irq。

（4）传入request\_threaded\_irq的primary handler和threaded handler参数有下面四种组合：

|  |  |  |
| --- | --- | --- |
| primary handler | threaded handler | 描述 |
| NULL | NULL | 函数出错，返回-EINVAL |
| 设定 | 设定 | 正常流程。中断处理被合理的分配到primary handler和threaded handler中。 |
| 设定 | NULL | 中断处理都是在primary handler中完成 |
| NULL | 设定 | 这种情况下，系统会帮忙设定一个default的primary handler：irq\_default\_primary\_handler，协助唤醒threaded handler线程 |

（5）这部分的代码很简单，分配struct irqaction，赋值，调用\_\_setup\_irq进行实际的注册过程。这里要罗嗦几句的是锁的操作，在内核中，有很多函数，有的是需要调用者自己加锁保护的，有些是不需要加锁保护的。对于这些场景，linux kernel采取了统一的策略：基本函数名字是一样的，只不过需要调用者自己加锁保护的那个函数需要增加\_\_的前缀，例如内核有有下面两个函数：setup\_irq和\_\_setup\_irq。这里，我们在setup irq的时候已经调用chip\_bus\_lock进行保护，因此使用lock free的版本\_\_setup\_irq。

chip\_bus\_lock定义如下：

> static inline void chip\_bus\_lock(struct irq\_desc \*desc)   
> {   
> if (unlikely(desc->irq\_data.chip->irq\_bus\_lock))   
> desc->irq\_data.chip->irq\_bus\_lock(&desc->irq\_data);   
> }

大部分的interrupt controller并没有定义irq\_bus\_lock这个callback函数，因此chip\_bus\_lock这个函数对大多数的中断控制器而言是没有实际意义的。但是，有些interrupt controller是连接到慢速总线上的，例如一个i2c接口的IO expander芯片（这种芯片往往也提供若干有中断功能的GPIO，因此也是一个interrupt controller），在访问这种interrupt controller的时候需要lock住那个慢速bus（只能有一个client在使用I2C bus）。

2、注册irqaction

（1）nested IRQ的处理代码

在看具体的代码之前，我们首先要理解什么是nested IRQ。nested IRQ不是cascade IRQ，在[GIC代码分析](/irq_subsystem/gic_driver.html)中我们有描述过cascade IRQ这个概念，主要用在interrupt controller级联的情况下。为了方便大家理解，我还是给出一个具体的例子吧，具体的HW block请参考下图：

[![SOC-INT](/content/uploadfile/201409/f2140c5be79f3100a5c54fdf4228a51a20140922103331.gif "SOC-INT")](/content/uploadfile/201409/a03daab0b60c21e763d7f367c449fb8820140922103330.gif)

上图是一个两个GIC级联的例子，所有的HW block封装在了一个SOC chip中。为了方便描述，我们先进行编号：Secondary GIC的IRQ number是A，外设1的IRQ number是B，外设2的IRQ number是C。对于上面的硬件，linux kernel处理如下：

（a）IRQ A的中断描述符被设定为不能注册irqaction（不能注册specific interrupt handler，或者叫中断服务程序）

（b）IRQ A的highlevel irq-events handler（处理interrupt flow control）负责进行IRQ number的映射，在其irq domain上翻译出具体外设的IRQ number，并重新定向到外设IRQ number对应的highlevel irq-events handler。

（c）所有外设驱动的中断正常request irq，可以任意选择线程化的handler，或者只注册primary handler。

需要注意的是，对root GIC和Secondary GIC寄存器的访问非常快，因此ack、mask、EOI等操作也非常快。

我们再看看另外一个interrupt controller级联的情况：

[![nested](/content/uploadfile/201409/eb9047b8462ce224c9958af7e42dcc6820140922103334.gif "nested")](/content/uploadfile/201409/123d27cb3ef3f846a1f12b7ff969be0120140922103332.gif)

IO expander HW block提供了有中断功能的GPIO，因此它也是一个interrupt controller，有它自己的irq domain和irq chip。上图中外设1和外设2使用了IO expander上有中断功能的GPIO，它们有属于自己的IRQ number以及中断描述符。IO expander HW block的IRQ line连接到SOC内部的interrupt controller上，因此，这也是一个interrupt controller级联的情况，对于这种情况，我们是否可以采用和上面GIC级联的处理方式呢？

不行，对于GIC级联的情况，如果secondary GIC上的外设1产生了中断，整个关中断的时间是IRQ A的中断描述符的highlevel irq-events handler处理时间＋IRQ B的的中断描述符的highlevel irq-events handler处理时间＋外设1的primary handler的处理时间。所幸对root GIC和Secondary GIC寄存器的访问非常快，因此整个关中断的时间也不是非常的长。但是如果是IO expander这个情况，如果采取和上面GIC级联的处理方式一样的话，关中断的时间非常长。我们还是用外设1产生的中断为例子好了。这时候，由于IRQ B的的中断描述符的highlevel irq-events handler处理设计I2C的操作，因此时间非常的长，这时候，对于整个系统的实时性而言是致命的打击。对这种硬件情况，linux kernel处理如下：

（a）IRQ A的中断描述符的highlevel irq-events handler根据实际情况进行设定，并且允许注册irqaction。对于连接到IO expander上的外设，它是没有real time的要求的（否则也不会接到IO expander上），因此一般会进行线程化处理。由于threaded handler中涉及I2C操作，因此要设定IRQF\_ONESHOT的flag。

（b）在IRQ A的中断描述符的threaded interrupt handler中进行进行IRQ number的映射，在IO expander irq domain上翻译出具体外设的IRQ number，并直接调用handle\_nested\_irq函数处理该IRQ。

（c）外设对应的中断描述符设定IRQ\_NESTED\_THREAD的flag，表明这是一个nested IRQ。nested IRQ没有highlevel irq-events handler，也没有primary handler，它的threaded interrupt handler是附着在其parent IRQ的threaded handler上的。

具体的nested IRQ的处理代码如下：

> static int \_\_setup\_irq(unsigned int irq, struct irq\_desc \*desc, struct irqaction \*new)   
> {
>
> ……   
> **nested = irq\_settings\_is\_nested\_thread(desc);   
> if (nested) {   
> if (!new->thread\_fn) {   
> ret = -EINVAL;   
> goto out\_mput;   
> }   
> new->handler = irq\_nested\_primary\_handler;**  
> } else {   
> ……   
> }
>
> ……
>
> }

如果一个中断描述符是nested thread type的，说明这个中断描述符应该设定threaded interrupt handler（当然，内核是不会单独创建一个thread的，它是借着其parent IRQ的interrupt thread执行），否则就会出错返回。对于primary handler，它应该没有机会被调用到，当然为了调试，kernel将其设定为irq\_nested\_primary\_handler，以便在调用的时候打印一些信息，让工程师直到发生了什么状况。

（2）forced irq threading处理

具体的forced irq threading的处理代码如下：

> static int \_\_setup\_irq(unsigned int irq, struct irq\_desc \*desc, struct irqaction \*new)   
> {
>
> ……   
> nested = irq\_settings\_is\_nested\_thread(desc);   
> if (nested) {   
> ……   
> } else {   
>  **if (irq\_settings\_can\_thread(desc))   
> irq\_setup\_forced\_threading(new);**  
> }
>
> ……
>
> }

forced irq threading其实就是将系统中所有可以被线程化的中断handler全部线程化，即便你在request irq的时候，设定的是primary handler，而不是threaded handler。当然那些不能被线程化的中断（标注了IRQF\_NO\_THREAD的中断，例如系统timer）还是排除在外的。irq\_settings\_can\_thread函数就是判断一个中断是否可以被线程化，如果可以的话，则调用irq\_setup\_forced\_threading在set irq的时候强制进行线程化。具体代码如下：

> static void irq\_setup\_forced\_threading(struct irqaction \*new)   
> {   
> if (!force\_irqthreads)－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－（a）   
> return;   
> if (new->flags & (IRQF\_NO\_THREAD | IRQF\_PERCPU | IRQF\_ONESHOT))－－－－－－－（b）   
> return;
>
> new->flags |= IRQF\_ONESHOT; －－－－－－－－－－－－－－－－－－－－－－－－－（d）
>
> if (!new->thread\_fn) {－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－（c）   
> set\_bit(IRQTF\_FORCED\_THREAD, &new->thread\_flags);   
> new->thread\_fn = new->handler;   
> new->handler = irq\_default\_primary\_handler;   
> }   
> }

（a）系统中有一个强制线程化的选项：CONFIG\_IRQ\_FORCED\_THREADING，如果没有打开该选项，force\_irqthreads总是0，因此irq\_setup\_forced\_threading也就没有什么作用，直接return了。如果打开了CONFIG\_IRQ\_FORCED\_THREADING，说明系统支持强制线程化，但是具体是否对所有的中断进行强制线程化处理还是要看命令行参数threadirqs。如果kernel启动的时候没有传入该参数，那么同样的，irq\_setup\_forced\_threading也就没有什么作用，直接return了。只有bootloader向内核传入threadirqs这个命令行参数，内核才真正在启动过程中，进行各个中断的强制线程化的操作。

（b）看到IRQF\_NO\_THREAD选项你可能会奇怪，前面irq\_settings\_can\_thread函数不是检查过了吗？为何还要重复检查？其实一个中断是否可以进行线程化可以从两个层面看：一个是从底层看，也就是从中断描述符、从实际的中断硬件拓扑等方面看。另外一个是从中断子系统的用户层面看，也就是各个外设在注册自己的handler的时候是否想进行线程化处理。所有的IRQF\_XXX都是从用户层面看的flag，因此如果用户通过IRQF\_NO\_THREAD这个flag告知kernel，该interrupt不能被线程化，那么强制线程化的机制还是尊重用户的选择的。

PER CPU的中断都是一些较为特殊的中断，不是一般意义上的外设中断，因此对PER CPU的中断不强制进行线程化。IRQF\_ONESHOT选项说明该中断已经被线程化了（而且是特殊的one shot类型的），因此也是直接返回了。

（c）强制线程化只对那些没有设定thread\_fn的中断进行处理，这种中断将全部的处理放在了primary interrupt handler中（当然，如果中断处理比较耗时，那么也可能会采用bottom half的机制），由于primary interrupt handler是全程关闭CPU中断的，因此可能对系统的实时性造成影响，因此考虑将其强制线程化。struct irqaction中的thread\_flags是和线程相关的flag，我们给它打上IRQTF\_FORCED\_THREAD的标签，表明该threaded handler是被强制threaded的。new->thread\_fn = new->handler这段代码表示将原来primary handler中的内容全部放到threaded handler中处理，新的primary handler被设定为default handler。

（d）强制线程化是一个和实时性相关的选项，从我的角度来看是一个很不好的设计（个人观点），各个驱动工程师在撰写自己的驱动代码的时候已经安排好了自己的上下文环境。有的是进程上下文，有的是中断上下文，在各自的上下文环境中，驱动工程师又选择了适合的内核同步机制。但是，强制线程化导致原来运行在中断上下文的primary handler现在运行在进程上下文，这有可能导致一些难以跟踪和定位的bug。

当然，作为内核的开发者，既然同意将强制线程化这个特性并入linux kernel，相信他们有他们自己的考虑。我猜测这是和一些旧的驱动代码维护相关的。linux kernel中的中断子系统的API的修改会引起非常大的震动，因为内核中成千上万的驱动都是需要调用旧的接口来申请linux kernel中断子系统的服务，对每一个驱动都进行修改是一个非常耗时的工作，为了让那些旧的驱动代码可以运行在新的中断子系统上，因此，在kernel中，实际上仍然提供了旧的request\_irq接口函数，如下：

> static inline int \_\_must\_check   
> request\_irq(unsigned int irq, irq\_handler\_t handler, unsigned long flags,   
> const char \*name, void \*dev)   
> {   
> return request\_threaded\_irq(irq, handler, NULL, flags, name, dev);   
> }

接口是OK了，但是，新的中断子系统的思路是将中断处理分成primary handler和threaded handler，而旧的驱动代码一般是将中断处理分成top half和bottom half，如何将这部分的不同抹平？linux kernel是这样处理的（这是我个人的理解，不保证是正确的）：

（d-1）内核为那些被强制线程化的中断handler设定了IRQF\_ONESHOT的标识。这是因为在旧的中断处理机制中，top half是不可重入的，强制线程化之后，强制设定IRQF\_ONESHOT可以保证threaded handler是不会重入的。

（d-2）在那些被强制线程化的中断线程中，disable bottom half的处理。这是因为在旧的中断处理机制中，botton half是不可能抢占top half的执行，强制线程化之后，应该保持这一点。

（3）创建interrupt线程。代码如下：

> if (new->thread\_fn && !nested) {   
> struct task\_struct \*t;   
> static const struct sched\_param param = {   
> .sched\_priority = MAX\_USER\_RT\_PRIO/2,   
> };
>
> t = kthread\_create(irq\_thread, new, "irq/%d-%s", irq,－－－－－－－－－－－－－－－－－－（a）   
> new->name);
>
> sched\_setscheduler\_nocheck(t, SCHED\_FIFO, ¶m);
>
> get\_task\_struct(t);－－－－－－－－－－－－－－－－－－－－－－－－－－－（b）   
> new->thread = t;   
>   
> set\_bit(IRQTF\_AFFINITY, &new->thread\_flags);－－－－－－－－－－－－－－－（c）   
> }
>
> if (!alloc\_cpumask\_var(&mask, GFP\_KERNEL)) {－－－－－－－－－－－－－－－－（d）   
> ret = -ENOMEM;   
> goto out\_thread;   
> }   
> if (desc->irq\_data.chip->flags & IRQCHIP\_ONESHOT\_SAFE)－－－－－－－－－－－（e）   
> new->flags &= ~IRQF\_ONESHOT;

（a）调用kthread\_create来创建一个内核线程，并调用sched\_setscheduler\_nocheck来设定这个中断线程的调度策略和调度优先级。这些是和进程管理相关的内容，我们留到下一个专题再详细描述吧。

（b）调用get\_task\_struct可以为这个threaded handler的task struct增加一次reference count，这样，即便是该thread异常退出也可以保证它的task struct不会被释放掉。这可以保证中断系统的代码不会访问到一些被释放的内存。irqaction的thread 成员被设定为刚刚创建的task，这样，primary handler就知道唤醒哪一个中断线程了。

（c）设定IRQTF\_AFFINITY的标志，在threaded handler中会检查该标志并进行IRQ affinity的设定。

（d）分配一个cpu mask的变量的内存，后面会使用到

（e）驱动工程师是撰写具体外设驱动的，他/她未必会了解到底层的一些具体的interrupt controller的信息。有些interrupt controller（例如MSI based interrupt）本质上就是就是one shot的（通过IRQCHIP\_ONESHOT\_SAFE标记），因此驱动工程师设定的IRQF\_ONESHOT其实是画蛇添足，因此可以去掉。

（4）共享中断的检查。代码如下：

> old\_ptr = &desc->action;   
> old = \*old\_ptr;
>
> if (old) {   
> if (!((old->flags & new->flags) & IRQF\_SHARED) ||－－－－－－－－－－－－－－－－－（a）   
> ((old->flags ^ new->flags) & IRQF\_TRIGGER\_MASK) ||   
> ((old->flags ^ new->flags) & IRQF\_ONESHOT))   
> goto mismatch;
>
> /\* All handlers must agree on per-cpuness \*/   
> if ((old->flags & IRQF\_PERCPU) != (new->flags & IRQF\_PERCPU))   
> goto mismatch;
>
> /\* add new interrupt at end of irq queue \*/   
> do {－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－（b）   
> thread\_mask |= old->thread\_mask;   
> old\_ptr = &old->next;   
> old = \*old\_ptr;   
> } while (old);   
> shared = 1;   
> }

（a）old指向注册之前的action list，如果不是NULL，那么说明需要共享interrupt line。但是如果要共享，需要每一个irqaction都同意共享（IRQF\_SHARED），每一个irqaction的触发方式相同（都是level trigger或者都是edge trigger），相同的oneshot类型的中断（都是one shot或者都不是），per cpu类型的相同中断（都是per cpu的中断或者都不是）。

（b）将该irqaction挂入队列的尾部。

（5）thread mask的设定。代码如下：

> if (new->flags & IRQF\_ONESHOT) {   
> if (thread\_mask == ~0UL) {－－－－－－－－－－－－－－－－－－－－－－－－（a）   
> ret = -EBUSY;   
> goto out\_mask;   
> }   
> new->thread\_mask = 1 << ffz(thread\_mask);
>
> } else if (new->handler == irq\_default\_primary\_handler &&   
> !(desc->irq\_data.chip->flags & IRQCHIP\_ONESHOT\_SAFE)) {－－－－－－－－（b）   
> ret = -EINVAL;   
> goto out\_mask;   
> }

对于one shot类型的中断，我们还需要设定thread mask。如果一个one shot类型的中断只有一个threaded handler（不支持共享），那么事情就很简单（临时变量thread\_mask等于0），该irqaction的thread\_mask成员总是使用第一个bit来标识该irqaction。但是，如果支持共享的话，事情变得有点复杂。我们假设这个one shot类型的IRQ上有A，B和C三个irqaction，那么A，B和C三个irqaction的thread\_mask成员会有不同的bit来标识自己。例如A的thread\_mask成员是0x01，B的是0x02，C的是0x04，如果有更多共享的irqaction（必须是oneshot类型），那么其thread\_mask成员会依次设定为0x08，0x10……

（a）在上面“共享中断的检查”这个section中，thread\_mask变量保存了所有的属于该interrupt line的thread\_mask，这时候，如果thread\_mask变量如果是全1，那么说明irqaction list上已经有了太多的irq action（大于32或者64，和具体系统和编译器相关）。如果没有满，那么通过ffz函数找到第一个为0的bit作为该irq action的thread bit mask。

（b）irq\_default\_primary\_handler的代码如下：

> static irqreturn\_t irq\_default\_primary\_handler(int irq, void \*dev\_id)   
> {   
> return IRQ\_WAKE\_THREAD;   
> }

代码非常的简单，返回IRQ\_WAKE\_THREAD，让kernel唤醒threaded handler就OK了。使用irq\_default\_primary\_handler虽然简单，但是有一个风险：如果是电平触发的中断，我们需要操作外设的寄存器才可以让那个asserted的电平信号消失，否则它会一直持续。一般，我们都是直接在primary中操作外设寄存器（slow bus类型的interrupt controller不行），尽早的clear interrupt，但是，对于irq\_default\_primary\_handler，它仅仅是wakeup了threaded interrupt handler，并没有clear interrupt，这样，执行完了primary handler，外设中断仍然是asserted，一旦打开CPU中断，立刻触发下一次的中断，然后不断的循环。因此，如果注册中断的时候没有指定primary interrupt handler，并且没有设定IRQF\_ONESHOT，那么系统是会报错的。当然，有一种情况可以豁免，当底层的irq chip是one shot safe的（IRQCHIP\_ONESHOT\_SAFE）。

（6）用户IRQ flag和底层interrupt flag的同步（TODO）

*原创文章，转发请注明出处。蜗窝科技。[/irq_subsystem/request_threaded_irq.html](/irq_subsystem/request_threaded_irq.html)*
