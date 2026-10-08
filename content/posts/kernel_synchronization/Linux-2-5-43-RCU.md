---
title: "Linux 2.5.43版本的RCU实现（废弃）"
date: 2016-01-19T12:13:03+08:00
url: "/kernel_synchronization/Linux-2-5-43-RCU.html"
gid: "258"
emlog_type: "blog"
summary: "\r\n\tRCU的工作原理虽然简单，但是实现产品级别的RCU同步机制并不是一个简单的事情，看看目前kernel中庞大的RCU数据结构，这让我望而却\r\n步。蜗窝科技在撰写其他文档的时候，往往喜欢使用最新的内核，本文和其他文章不一样，本文选择了第一个引入RCU的内核版本，即2.5.43。\r\n\r\n\r\n\t本文主要介绍了linux2.5.43版本上的RCU实现。\r\n"
author: "linuxer"
category: "内核同步机制"
category_alias: "kernel_synchronization"
tags: ["RCU"]
views: 13319
comment_count: 4
aliases:
  - "/kernel_synchronization/258.html"
  - "/258.html"
---

Note：如果你看完这篇文档就想立刻开骂，我建议你稍等，我这篇写的的确不怎么样。不过对于RCU的理解，我也是一个循序渐进的过程，在读完2.6.11内核的RCU实现之后，对RCU的理解更加深入了一步。由于种种原因，我实在是不想更新这份文档了，因此，如果你不满意，或者任何的想法，建议去2.6.11内核的RCU实现那份文档去看看，位置是[/kernel_synchronization/linux2-6-11-RCU.html](/kernel_synchronization/linux2-6-11-RCU.html)

一、前言

RCU的工作原理虽然简单，但是实现产品级别的RCU同步机制并不是一个简单的事情，看看目前kernel中庞大的RCU数据结构，这让我望而却步。蜗窝科技在撰写其他文档的时候，往往喜欢使用最新的内核，本文和其他文章不一样，本文选择了第一个引入RCU的内核版本，即2.5.43，无它，仅仅是为了理解RCU的基本工作原理。

本文主要介绍了linux2.5.43版本上的RCU实现。

二、基本术语

1、Quiescent State。对于RCU而言，quiescent state其实就是不访问RCU protected data的那些状态。更通俗一些讲，如果CPU执行的thread位于RCU read-side临界区的的话（访问受RCU保护的数据），那么其处于active状态，如果离开RCU read-side临界区，那么就处于quiescent state。

2、Grace Period。Grace Period是一段时间，有起点，有终点。在Grace Period起点的时候，处于RCU read-side临界区的thread假设有n个，T0，T1，……Tn-1。随着时间的流逝，代码不断的执行，这些thread会一个个的离开RCU read-side临界区。而对Grace Period终点的要求就是：T0，T1，……Tn-1这些thread必须在Grace Period终点之前全部离开临界区。

3、Quiescent period。Quiescent period也是一个时间段，在这个时间段内，每一个thread都至少经历了一次Quiescent State。对于linux的RCU实现，Grace Period和Quiescent period是可以互通使用（后文使用Grace Period这个术语）。

三、基本数据结构

1、RCU callback数据结构

我们用struct rcu\_head来描述一个RCU call back相关的数据结构：

> struct rcu\_head {   
> struct list\_head list;   
> void (\*func)(void \*obj);   
> void \*arg;   
> };

func是具体的callback函数，arg是传入callback函数的参数。RCU call back都是一批批处理的，list就是挂入RCU call back链表的节点。

2、记录系统中每个CPU的RCU相关的数据

我们struct rcu\_data来描述一个CPU上的和RCU相关的数据结构：

> struct rcu\_data {   
> long qsctr; －－－－－－－－－－－－－－－－－－－－（1）   
> long last\_qsctr; －－－－－－－－－－－－－－－－－－（2）   
> long batch;－－－－－－－－－－－－－－－－－－－－（3）   
> struct list\_head nxtlist;   
> struct list\_head curlist;   
> } \_\_\_\_cacheline\_aligned\_in\_smp;

（1）这个成员用来记录本CPU的quiescent state counter。这个counter是不断的累加的，开始是0值，每次CPU上执行的thread发现离开了读临界区，该counter就会加一（例如在该CPU上发生了进程切换，那么该counter会加一）。如果在A时间点，运行在该CPU的thread观察到该counter的值是n，在时间点B，运行在该CPU的thread观察到该counter的值是n+1（或者更大），那么，我们可以确定，该CPU一定已经至少经历一次Quiescent state。

（2）qsctr是动态不断累加的counter，但是，判断Grace Period需要两个时间点：起点和终点。qsctr是当前的quiesent state counter，也就是终点的值，last\_qsctr就是起点的值啦。当last\_qsctr – qsctr < 0的时候，说明该CPU已经至少经历一次Quiescent state。

（3）batch，nxtlist和curlist这三个成员比较适合一起描述。根据第二章的描述，Quiesent state和Grace Period都是根据RCU protected data而言的，也就是说，每个RCU protected data都有自己的RCU read-side临界区，都有自己的Quiesent state和Grace Period。虽然定义如此，但是，从实现角度看，我们不可能跟踪每一个受RCU保护的数据及其临界区的出入情况，因此，实际上，Quiesent state和Grace Period都是一个全局的概念。

我们知道，每个RCU的updater会在Grace Period之后调用callback函数来完成reclamation的动作（例如回收旧版本的数据），这些请求被挂入到nxtlist为header的双向链表中。在某个时间点A，我们将收集的全部请求移入到curlist为header的双向链表中，并准备处理这一批请求。当然，需要分配一个批次号码（系统是一批一批处理，每一批当然需要ID了，这个ID就是batch成员），并记录A时间点的quiescent state counter，保存在last\_qsctr中。在时间点B，通过当前的quiescent state counter和last\_qsctr，该CPU可以知道自己已经经历至少一次Quiesenct state，但是这还不行，需要所有的CPU都经历至少一次Quiesenct state，callback function才可以被执行。在时间点C，如果Grace Period已过，那么在适当的时机，系统会从curlist链表中，依次将callback请求摘下，执行callback function。

因此，通过上面的描述，Quiesent state和Grace Period都不再是针对某个RCU protected data，而是针对整个系统而言，或者，更准确的说，它们描述的是当前处理的那一批RCU protected data的Quiesent state和Grace Period。

3、RCU control block

我们struct rcu\_ctrlblk来描述系统如何控制RCU的运作：

> struct rcu\_ctrlblk {   
> spinlock\_t mutex;   
> long curbatch; －－－－－－－－－－－－－－－－－－－－－（1）   
> long maxbatch; －－－－－－－－－－－－－－－－－－－－（2）   
> unsigned long rcu\_cpu\_mask; －－－－－－－－－－－－－－－（3）   
> };

（1）就象上一小节描述的那样，系统的callback请求都是一批一批的处理的，批次ID的控制就是通过curbatch来完成的。当启动新的批次的时候，该批次被设定为curbatch+1。curbatch是正在处理RCU call back请求的那个批次号（Grace period正在检测中）。

（2）maxbatch是当前最大的批次号。这个成员主要用来判断在完成某个批次Grace period之后，是否立刻启动一个新的批次。如果maxbatch等于current，那么就不需要启动，否则需要启动一个新的批次。

（3）struct rcu\_ctrlblk数据结构的rcu\_cpu\_mask成员就是用来管理当前批次的RCU callback是否渡过Grace Period，如果rcu\_cpu\_mask中所有的bit被清零，则说明Grace period已过，从而可以调用callback函数进行reclaimation的动作。

4、调用RCU callback函数的上下文

当渡过Grace period之后，要在哪一个上下文中调用callback函数呢？答案是tasklet context，代码如下：

> static DEFINE\_PER\_CPU(struct tasklet\_struct, rcu\_tasklet) = {NULL};

每个CPU都定义一个struct tasklet\_struct的变量，用来在本CPU发现系统渡过Grace period之后，在该上下文中调用当前需要处理的RCU callback函数们。在linux内核初始化的时候，rcu\_tasklet的处理函数被设定为rcu\_process\_callbacks。

四、如何分配和管理RCU callback请求的批次号？

1、挂入per cpu的RCU callback链表

代码调用call\_rcu接口函数的时候就会执行将该RCU callback请求挂入本cpu的RCU callback链表中的动作，具体如下：

> void call\_rcu(struct rcu\_head \*head, void (\*func)(void \*arg), void \*arg)   
> {   
> int cpu;   
> unsigned long flags;
>
> head->func = func;   
> head->arg = arg;   
> local\_irq\_save(flags);   
> cpu = smp\_processor\_id();   
> list\_add\_tail(&head->list, &RCU\_nxtlist(cpu));   
> local\_irq\_restore(flags);   
> }

代码简单的不需要任何解释，就是挂入本cpu的struct rcu\_data数据结构中的nxtlist链表。

除了直接调用call\_rcu接口函数的场景，调用synchronize\_kernel本质上也是调用了call\_rcu接口，如下：

> void synchronize\_kernel(void)   
> {   
> struct rcu\_head rcu;   
> DECLARE\_COMPLETION(completion);   
> call\_rcu(&rcu, wakeme\_after\_rcu, &completion);   
> wait\_for\_completion(&completion);   
> }

synchronize\_kernel实际上是需要阻塞当前进程，直到渡过Grace period。这里使用了completion这种同步机制，让当前进程阻塞在wait\_for\_completion，一旦渡过Grace period，wakeme\_after\_rcu这个callback函数会被调用，从而唤醒当前进程。

2、怎么来分配批次号？

随着系统的运行，各个CPU上都会不断的有RCU callback请求挂入队列，累积到一定程度，各个CPU就会锁定当前nxtlist链表中的数据，将其移入curlist链表，从而确定了本批次要处理的RCU callback请求。之后的请求会挂入nxtlist链表，等待下一个批次再处理。

当然，一次也不能处理太多的请求，因此linux内核会在每次周期性tick到来的时候进行检查，具体方法是通过调用tasklet\_schedule(&RCU\_tasklet(cpu))函数来调度一个rcu tasklet的运行，具体代码如下（删除无关代码）：

> static void rcu\_process\_callbacks(unsigned long unused)   
> {……
>
> local\_irq\_disable();   
> if (!list\_empty(&RCU\_nxtlist(cpu)) && list\_empty(&RCU\_curlist(cpu))) {－－－－－－－（1）   
> list\_splice(&RCU\_nxtlist(cpu), &RCU\_curlist(cpu));－－－－－－－－－－－－－－－（2）   
> INIT\_LIST\_HEAD(&RCU\_nxtlist(cpu));   
> local\_irq\_enable();
>
> spin\_lock(&rcu\_ctrlblk.mutex);   
> RCU\_batch(cpu) = rcu\_ctrlblk.curbatch + 1;－－－－－－－－－－－－－－－－－（3）   
> rcu\_start\_batch(RCU\_batch(cpu));－－－－－－－－－－－－－－－－－－－－－（4）   
> spin\_unlock(&rcu\_ctrlblk.mutex);   
> } else {   
> local\_irq\_enable();   
> }   
> ……   
> }

（1）这里需要满足两个条件：第一个是必须有正在申请处理的RCU callback请求（在nxtlist链表中），第二个是已经启动处理（不保证处理完毕）上一个批次的RCU callback请求（在curlist链表中）。

（2）如果条件成立，那么将nxtlist链表中请求转移到curlist链表中。而curlist链表中的所有的RCU callback请求就是本批次需要处理的所有的请求（对该CPU而言）。

（3）分配批次ID。值得一提的是：对应某个批次的所有的RCU callback请求是分布在各个CPU的curlist链表中，因此，即便是渡过了Grace period，RCU callback请求也不是一次性的处理掉，而是由各个CPU逐个处理自己curlist链表中请求。

（4）注册这个新的batch ID。这里最重要的操作就是设定rcu\_ctrlblk.rcu\_cpu\_mask的值为cpu\_online\_map，即每一个CPU都没有渡过Grace period。

3、如何管理批次号？

批次号是由rcu\_ctrlblk.curbatch 来管理的，它描述了当前正在处理的批次号。如果批次号是A，那么A批次的RCU callback的Grace period正在检测中。除了curbatch，struct rcu\_ctrlblk数据结构还有一个maxbatch成员，该成员主要用来跟踪最大分配的那个批次号。例如，在上节中的批次号分配是这样的：

> RCU\_batch(cpu) = rcu\_ctrlblk.curbatch + 1;

当分配批次号的时候，rcu\_ctrlblk.curbatch批次还没有渡过Grace Period，因此，给本CPU分配的批次实际上不能立刻启动Grace period的检测，但是需要记录这个pending的批次请求（通过maxbatch记录）。

当rcu\_ctrlblk.curbatch批次的RCU callback请求渡过了Grace period，这时候可以进行maxbatch批次的处理。

五、如何管理Grace period

1、如何跟踪各个CPU的quiescent state

我们会在下面的两个场景来累加quiescent state counter：

（1）在进程切换的时候，具体参考schedule函数

（2）在周期性tick中，如果满足条件，也会累加quiescent state counter。具体代码如下：

> void rcu\_check\_callbacks(int cpu, int user)   
> {   
> if (user ||   
> (idle\_cpu(cpu) && !in\_softirq() && hardirq\_count() <= 1))   
> RCU\_qsctr(cpu)++;   
> tasklet\_schedule(&RCU\_tasklet(cpu));   
> }

如果tick到来的时间点，中断现场是userspace，说明已经离开了内核空间，对于本CPU而言，也就可以确定thread已经离开了RCU read-side临界区。为什么呢？首先我们要给出一个前提条件：在RCU read-side临界区内不能阻塞。其次我们一起来看看如何界定RCU read-side临界区，代码如下：

> #define rcu\_read\_lock() preempt\_disable()   
> #define rcu\_read\_unlock() preempt\_enable()

对于非抢占内核（不配置CONFIG\_PREEMPT）而言，rcu\_read\_lock和rcu\_read\_unlock是空的。多么爽，进出RCU read-side临界区没有任何的开销。即便如此，内核还是能够用简单的方法来跟踪本CPU的quiescent state。如果在RCU read-side临界区内不能阻塞，并且在内核态不会发生调度，只有在返回用户空间的时候才会调度，那么一旦发生了进出切换或者返回用户空间，则说明thread已经离开RCU read-side临界区。对于抢占式内核而言，如果rcu\_read\_lock和rcu\_read\_unlock仍然是空的，那么在RCU read-side临界区中有可能会产生中断并引发调度，在这种情况下，进程切换或者返回用户空间都不能确保离开RCU read-side临界区。因此，RCU read-side临界区只有disable preempt就OK了。

还有一个特殊的场景也可以认为是本cpu的thread都离开了RCU read-side临界区，那就是没有RCU read-side临界区的内核线程上下文，虽然在内核空间，但是实际上本质还是进程上下文，当切换到该内核线程上下文的时候，必然已经离开了RCU read-side临界区，并且本内核线程又没有使用RCU来保护read-side临界区。符合这个条件，又经常会被用到的是swapper内核线程（也就是idle线程了）。因此，当tick到来的时候，如果timer中断命中了idle内核线程上下文，那么也可以认为本CPU至少经历一个Quiescent state。当然，我们要去掉softirq context和hardirq context的场景，因为这些context是有可能进入read-side临界区的。

注意：这里有一个issue，hardirq\_count() <= 1 这个判断条件应该是 hardirq\_count() <= (1 << HARDIRQ\_SHIFT)，在2.5.45版本上修复。由于执行rcu\_check\_callbacks是在timer的interrupt handler中，因此hardirq\_count() <= 1 这个判断条件永远不会成立。

2、什么时间点标记Grace period的起点？什么时间点标记Grace period的终点？

一旦确定了批次号，那么Grace period的起点就定义了，在这个时间点上，struct rcu\_ctrlblk数据结构的rcu\_cpu\_mask成员被初始化，每一个需要跟踪的CPU对应的bit都会被置位。在每一个tick到来的时候，系统会调用rcu\_check\_quiescent\_state函数来检查每一个cpu的quiesent state，具体如下：

> static void rcu\_check\_quiescent\_state(void)   
> {   
> int cpu = smp\_processor\_id();
>
> if (!test\_bit(cpu, &rcu\_ctrlblk.rcu\_cpu\_mask)) {－－－－－－－－－－－－－－－－（1）   
> return;   
> }   
> if (RCU\_last\_qsctr(cpu) == RCU\_QSCTR\_INVALID) {－－－－－－－－－－－－－（2）   
> RCU\_last\_qsctr(cpu) = RCU\_qsctr(cpu);   
> return;   
> }   
> if (RCU\_qsctr(cpu) == RCU\_last\_qsctr(cpu)) {－－－－－－－－－－－－－－－－（3）   
> return;   
> }
>
> spin\_lock(&rcu\_ctrlblk.mutex);－－－－－－－－－－－－－－－－－－－－－－－（4）   
> if (!test\_bit(cpu, &rcu\_ctrlblk.rcu\_cpu\_mask)) {－－－－－－－－－－－－－－－－（5）   
> spin\_unlock(&rcu\_ctrlblk.mutex);   
> return;   
> }   
> clear\_bit(cpu, &rcu\_ctrlblk.rcu\_cpu\_mask);－－－－－－－－－－－－－－－－－－（6）   
> RCU\_last\_qsctr(cpu) = RCU\_QSCTR\_INVALID;－－－－－－－－－－－－－－－－（7）   
> if (rcu\_ctrlblk.rcu\_cpu\_mask != 0) {－－－－－－－－－－－－－－－－－－－－－－（8）   
> spin\_unlock(&rcu\_ctrlblk.mutex);   
> return;   
> }   
> rcu\_ctrlblk.curbatch++;－－－－－－－－－－－－－－－－－－－－－－－－－－－（9）   
> rcu\_start\_batch(rcu\_ctrlblk.maxbatch);－－－－－－－－－－－－－－－－－－－－（10）   
> spin\_unlock(&rcu\_ctrlblk.mutex);   
> }

（1）对于某个批次的callback请求，如果该CPU已经确认至少经历了一次quiesent state，那么其rcu\_cpu\_mask对应的bit会被clear，因此不需要后续的检查了，直接返回。

（2）确定批次号之后，第一次调用rcu\_check\_quiescent\_state函数的时候，last\_qsctr会等于RCU\_QSCTR\_INVALID，这时候会重新设定last\_qsctr的值，该值是后续对比的基础。记录了本CPU的当前Quiescent state counter值之后，没有必要进行比对，因此直接返回。

（3）如果当前的Quiescent state counter和上一次记录的counter值是一样的，说明本CPU还没有经历过Quiescent state，直接返回。

（4）执行到这里，说明CPU至少经历过一次Quiescent state，后续要修改一个全局的rcu\_ctrlblk变量，因此需要加锁。

（5）rcu\_cpu\_mask上对应本cpu的bit已经被clear了，那么直接返回即可。

（6）clear rcu\_cpu\_mask上对应本cpu的bit，标记本cpu至少经历过一次Quiescent state

（7）设定last\_qsctr会等于RCU\_QSCTR\_INVALID。这么设定主要是为了识别分配batch number之后，本cpu第一次进行Quiescent state检查的场景。

（8）是否还有其他的CPU还没有至少经历过一次Quiescent state，如果是这样，那么退出，等待其他CPU。

（9）OK，对于本批次的RCU callback请求而言，所有的CPU都至少经历过一次Quiescent state，这也就意味着Grace period已经过了，callback函数可以被执行了。如果在没有累加之前rcu\_ctrlblk.curbatch等于B，那么当前的批次号是B+1，当执行了rcu\_ctrlblk.curbatch++;之后，也就是告知系统，B+1那个批次，Grace period已过，去处理吧。

（10）启动下一批次的RCU请求。

六、如何处理RCU callback请求

具体代码如下：

> static void rcu\_process\_callbacks(unsigned long unused)   
> {   
> int cpu = smp\_processor\_id();   
> LIST\_HEAD(list);
>
> if (!list\_empty(&RCU\_curlist(cpu)) &&－－－－－－－－－－－－－－－－－（1）   
> rcu\_batch\_after(rcu\_ctrlblk.curbatch, RCU\_batch(cpu))) {   
> list\_splice(&RCU\_curlist(cpu), &list);   
> INIT\_LIST\_HEAD(&RCU\_curlist(cpu));   
> }
>
> ……   
> if (!list\_empty(&list))   
> rcu\_do\_batch(&list);－－－－－－－－－－－－－－－－－－－－－－－（2）   
> }

（1）当前批次的请求挂在curlist链表中，如果该链表为空，说明在本批次中，该CPU上没有提出任何的callback请求，那么即便是Grace Period已过，也没有什么callback函数需要调用。rcu\_ctrlblk.curbatch标记的是Grace Period已过的那个批次号码，如果等于本cpu的rcu\_data的批次号，那么说明本cpu的curlist链表中的callback请求可以处理了。

（2）在tasklet上下文中，一个一个的处理callback请求。

七、参考文献

1、ChangeLog-2.5.43

2、linux2.5.43 source code

3、[https://www.ibm.com/developerworks/cn/linux/l-rcu/](https://www.ibm.com/developerworks/cn/linux/l-rcu/ "https://www.ibm.com/developerworks/cn/linux/l-rcu/")

4、[http://www.rdrop.com/users/paulmck/paper/rclockpdcsproof.pdf](http://www.rdrop.com/users/paulmck/paper/rclockpdcsproof.pdf "http://www.rdrop.com/users/paulmck/paper/rclockpdcsproof.pdf")

Changelog：

2016-1-26，修改了描述错误的地方，不过整个算法实现其实分析的很简略（我也不想再补充了，^\_^），如果想要了解细节的同学，建议阅读Linux2.6.11的RCU实现文档，那里会写的更详细一些。

*原创文章，转发请注明出处。蜗窝科技*
