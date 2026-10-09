---
title: "Concurrency Managed Workqueue之（一）：workqueue的基本概念"
date: 2015-07-15T18:47:28+08:00
url: "/irq_subsystem/workqueue.html"
gid: "199"
emlog_type: "blog"
summary: "workqueue是一个驱动工程师常用的工具，在旧的内核中（指2.6.36之前的内核版本）workqueue代码比较简单（大概800行），在2.6.36内核版本中引入了CMWQ（Concurrency Managed Workqueue），workqueue.c 的代码膨胀到5000多行，为了深入的理解CMWQ，单单一份文档很难将其描述的清楚，因此CMWQ作为一个主题将会产生一系列的文档，本文是这"
author: "linuxer"
category: "中断子系统"
category_alias: "irq_subsystem"
tags: ["workqueue"]
views: 44023
comment_count: 26
aliases:
  - "/irq_subsystem/199.html"
  - "/199.html"
---

一、前言

workqueue是一个驱动工程师常用的工具，在旧的内核中（指2.6.36之前的内核版本）workqueue代码比较简单（大概800行），在2.6.36内核版本中引入了CMWQ（Concurrency Managed Workqueue），workqueue.c的代码膨胀到5000多行，为了深入的理解CMWQ，单单一份文档很难将其描述的清楚，因此CMWQ作为一个主题将会产生一系列的文档，本文是这一系列文档中的第一篇，主要是基于2.6.23内核的代码实现来讲述workqueue的一些基本概念（之所以选择较低版本的内核，主要是因为代码简单，适合理解基本概念）。

二、为何需要workqueue

1、什么是中断上下文和进程上下文？

在继续描述workqueue之前，我们先梳理一下中断上下文和进程上下文。对于中断上下文，主要包括两种情况：

（1）执行该中断的处理函数（我们一般称之interrupt handler或者叫做top half），也就是hard interrupt context

（2）执行软中断处理函数，执行tasklet函数，执行timer callback函数。（或者统称bottom half），也就是software interrupt context。

top half当然是绝对的interrupt context，但对于上面的第二种情况，稍微有些复杂，其执行的现场包括：

（1）执行完top half，立刻启动bottom half的执行

（2）当负荷比较重的时候（中断产生的比较多），系统在一段时间内都在处理interrupt handler以及相关的softirq，从而导致无法调度到进程执行，这时候，linux kernel采用了将softirq推迟到softirqd这个内核线程中执行

（3）进程在内核态运行的时候，由于内核同步的需求，需要使用local\_bh\_disable/local\_bh\_enable来保护临界区。在临界区代码执行的时候，有可能中断触发并raise softirq，但是由于softirq处于disable状态从而在中断返回的时候没有办法invoke softirq的执行，当调用local\_bh\_enable的时候，会调用已经触发的那个softirq handler。

对于上面的情况1和情况3，毫无疑问，绝对的中断上下文，执行现场的current task和softirq handler没有任何的关系。对于情况2，虽然是在专属的内核线程中执行，但是我也倾向将其归入software interrupt context。

对于linux而言，中断上下文都是惊鸿一瞥，只有进程（线程、或者叫做task）是永恒的。整个kernel都是在各种进程中切来切去，一会儿运行在进程的用户空间，一会儿通过系统调用进入内核空间。当然，系统不是封闭的，还是需要通过外设和User或者其他的系统进行交互，这里就需要中断上下文了，在中断上下文中，完成硬件的交互，最终把数据交付进程或者进程将数据传递给外设。进程上下文有丰富的、属于自己的资源：例如有硬件上下文，有用户栈、有内核栈，有用户空间的正文段、数据段等等。而中断上下文什么也没有，只有一段执行代码及其附属的数据。那么问题来了：中断执行thread中的临时变量应该保存在栈上，那么中断上下文的栈在哪里？中断上下文没有属于自己的栈，肿么办？那么只能借了，当中断发生的时候，遇到哪一个进程就借用哪一个进程的资源（遇到就是缘分呐）。

2、如何判定当前的context？

OK，上一节描述中断上下文和进程上下文的含义，那么代码如何知道自己的上下文呢？下面我们结合代码来进一步分析。in\_irq()是用来判断是否在hard interrupt context的，我们一起来来看看in\_irq()是如何定义的：

> #define in\_irq() (hardirq\_count())
>
> #define hardirq\_count() (preempt\_count() & HARDIRQ\_MASK)

top half的处理是被irq\_enter()和irq\_exit()所包围，在irq\_enter函数中会调用preempt\_count\_add(HARDIRQ\_OFFSET)，为hardirq count的bit field增加1。在irq\_exit函数中，会调用preempt\_count\_sub(HARDIRQ\_OFFSET)，为hardirq count的bit field减去1。因此，只要in\_irq非零，则说明在中断上下文并且处于top half部分。

解决了hard interrupt context，我们来看software interrupt context。如何判定代码当前正在执行bottom half（softirq、tasklet、timer）呢？in\_serving\_softirq给出了答案：

> #define in\_serving\_softirq() (softirq\_count() & SOFTIRQ\_OFFSET)

需要注意的是：在2.6.23内核中没有这个定义（上面的代码来自4.0的内核）。内核中还有一个类似的定义：

> #define in\_softirq() (softirq\_count())
>
> #define softirq\_count() (preempt\_count() & SOFTIRQ\_MASK)

in\_softirq定义了更大的一个区域，不仅仅包括了in\_serving\_softirq上下文，还包括了disable bottom half的场景。我们用下面一个图片来描述：

[![sir-context](/content/uploadfile/201507/77076337836fe9a30a3e8ac3044a605b20150715104416.gif "sir-context")](/content/uploadfile/201507/84d72f610311e1d3289ed70eb8da5d3420150715104303.gif)

我们知道，在进程上下文中，由于内核同步的要求可能会禁止softirq。这时候，kernel提供了local\_bf\_enable和local\_bf\_disable这样的接口函数，这种场景下，在local\_bf\_enable函数中会执行软中断handler（在临界区中，虽然raise了softirq，但是由于disable了bottom half，因此无法执行，只有等到enable的时候第一时间执行该softirq handler）。in\_softirq包括了进程上下文中disable bottom half的临界区部分，而in\_serving\_softirq精准的命中了software interrupt context。

内核中还有一个in\_interrupt的宏定义，从它的名字上看似乎是定义了hard interrupt context和software interrupt context，到底是怎样的呢？我们来看看定义：

> #define in\_interrupt()        (irq\_count())   
> #define irq\_count()    (preempt\_count() & (HARDIRQ\_MASK | SOFTIRQ\_MASK \   
>                  | NMI\_MASK))

注：上面的代码来自4.0的内核。HARDIRQ\_MASK定义了hard interrupt contxt，NMI\_MASK定义了NMI（对于ARM是FIQ）类型的hard interrupt context，SOFTIRQ\_MASK包括software interrupt context加上禁止softirq情况下的进程上下文。因此，in\_interrupt()除了包括了中断上下文的场景，还包括了进程上下文禁止softirq的场景。

还有一个in\_atomic的宏定义，大家可以自行学习，这里不再描述了。

3、为何中断上下文不能sleep？

linux驱动工程师应该都会听说过这句话：中断上下文不能sleep，但是为什么呢？这个问题可以仔细思考一下。所谓sleep就是调度器挂起当前的task，然后在run queue中选择另外一个合适的task运行。规则很简单，不过实际操作就没有那么容易了。有一次，我们调试wifi驱动的时候，有一个issue很有意思：正常工作的时候一切都是OK的，但是当进行压力测试的时候，系统就会down掉。最后发现是在timer的callback函数中辗转多次调用了kmalloc函数，我们都知道，在某些情况下，kmalloc会导致当前进程被block。

从操作系统设计的角度来看，大部分的OS都规定中断上下文不能sleep，有些是例外的，比如solaris，每个中断的handler都是在它自己的task中处理的，因此可以在中断handler中sleep。不过在这样的系统中（很多RTOS也是如此处理的），实际的中断上下文非常的薄，可能就是向该中断handler对应的task发送一个message，所有的处理（ack中断、mask中断、copy FIFO等）都是在该中断的task中处理。这样的系统中，当然可以在中断handler中sleep，不过这有点偷换概念，毕竟这时候的上下文不是interrupt context，更准确的说是中断处理的process context，这样的系统interrupt context非常非常的简单，几乎没有。

当然，linux的设计并非如此（其实在rt linux中已经有了这样的苗头，可以参考中断线程化的文章），中断handler以及bottom half（不包括workqueue）都是在interrupt context中执行。当然一提到context，各种资源还是要存在的，例如说内核栈、例如说memory space等，interrupt context虽然单薄，但是可以借尸还魂。当中断产生的那一个时刻，当前进程有幸成为interrupt context的壳，提供了内核栈，保存了hardware context，此外各种资源（例如mm\_struct）也是借用当前进程的。本来呢interrupt context身轻如燕，没有依赖的task，调度器其实是不知道如何调度interrupt context的（它处理的都是task），在interrupt context借了一个外壳后，从理论上将，调度器是完全可以block该interrupt context执行，并将其他的task调入进入running状态。然而，block该interrupt context执行也就block其外壳task的执行，多么的不公平，多么的不确定，中断命中你，你就活该被schedule out，拥有正常思维的linux应该不会这么做的。

因此，在中断上下文中（包括hard interrupt context和software interrupt context）不能睡眠。

4、为何需要workqueue

workqueue和其他的bottom half最大的不同是它是运行在进程上下文中的，它可以睡眠，这和其他bottom half机制有本质的不同，大大方便了驱动工程师撰写中断处理代码。当然，驱动模块也可以自己创建一个kernel thread来解决defering work，但是，如果每个driver都创建自己的kernel thread，那么内核线程数量过多，这会影响整体的性能。因此，最好的方法就是把这些需求汇集起来，提供一个统一的机制，也就是传说中的work queue了。

三、数据抽象

1、workqueue。定义如下：

> struct workqueue\_struct {   
> struct cpu\_workqueue\_struct \*cpu\_wq; －－－－－per-cpu work queue struct   
> struct list\_head list; －－－workqueue list   
> const char \*name;   
> int singlethread; －－－－single thread or multi thread   
> int freezeable; －－－－和电源管理相关的一个flag   
> };

我们知道，workqueue就是一种把某些任务（work）推迟到一个或者一组内核线程中去执行，那个内核线程被称作worker thread（每个processor上有一个work thread）。系统中所有的workqueue会挂入一个全局链表，链表头定义如下：

> static LIST\_HEAD(workqueues);

list成员就是用来挂入workqueue链表的。singlethread是workqueue的一个特殊模式，一般而言，当创建一个workqueue的时候会为每一个系统内的processor创建一个内核线程，该线程处理本cpu调度的work。但是有些场景中，创建per-cpu的worker thread有些浪费（或者有一些其他特殊的考量），这时候创建single-threaded workqueue是一个更合适的选择。freezeable成员是一个和电源管理相关的一个flag，当系统suspend的时候，有一个阶段会将所有的用户空间的进程冻结，那么是否也冻结内核线程（包括workqueue）呢？缺省情况下，所有的内核线程都是nofrezable的，当然也可以调用set\_freezable让一个内核线程是可以被冻结的。具体是否需要设定该flag是和程序逻辑相关的，具体情况具体分析。OK，上面描述的都是workqueue中各个processor共享的成员，下面我们看看per-cpu的数据结构：

> struct cpu\_workqueue\_struct {
>
> spinlock\_t lock; －－－－用来保护worklist资源的访问
>
> struct list\_head worklist;   
> wait\_queue\_head\_t more\_work; －－－－－等待队列头   
> struct work\_struct \*current\_work; －－－－当前正在处理的work
>
> struct workqueue\_struct \*wq; －－－－－－指向work queue struct   
> struct task\_struct \*thread; －－－－－－－worker thread task
>
> int run\_depth; /\* Detect run\_workqueue() recursion depth \*/   
> } \_\_\_\_cacheline\_aligned;

worker thread要处理work，这些work被挂入work queue中的链表结构。由于每个processor都需要处理自己的work，因此这个work list是per cpu的。worklist成员就是这个per cpu的链表头，当worker thread被调度到的时候，就从这个队列中一个个的摘下work来处理。

2、work。定义如下：

> struct work\_struct {   
> atomic\_long\_t data;   
> struct list\_head entry;   
> work\_func\_t func;   
> };

所谓work就是异步执行的函数。你可能会觉得，反正是函数，直接调用不就OK了吗？但是，事情没有那么简单，如果该函数的代码中有些需要sleep的场景的时候，那么在中断上下文中直接调用将产生严重的问题。这时候，就需要到进程上下文中异步执行。下面我们仔细看看各个成员：func就是这个异步执行的函数，当work被调度执行的时候其实就是调用func这个callback函数，该函数的定义如下：

> typedef void (\*work\_func\_t)(struct work\_struct \*work);

work对应的callback函数需要传递该work的struct作为callback函数的参数。work是被组织成队列的，entry成员就是挂入队列的那个节点，data包含了该work的状态flag和挂入workqueue的信息。

3、总结

我们把上文中描述的各个数据结构集合在一起，具体请参考下图：

[![workqueue](/content/uploadfile/201507/8ac4ad9d9021a359edb98d1713c3ff2c20150715104623.gif "workqueue")](/content/uploadfile/201507/3f0b279644ba4646b73f303367bbe47220150715104521.gif)

我们自上而下来描述各个数据结构。首先，系统中包括若干的workqueue，最著名的workqueue就是系统缺省的的workqueue了，定义如下：

> static struct workqueue\_struct \*keventd\_wq \_\_read\_mostly;

如果没有特别的性能需求，那么一般驱动使用keventd\_wq就OK了，毕竟系统创建太多内核线程也不是什么好事情（消耗太多资源）。当然，如果有需要，驱动模块可以创建自己的workqueue。因此，系统中存在一个workqueues的链表，管理了所有的workqueue实例。一个workqueue对应一组work thread（先不考虑single thread的场景），每个cpu一个，由cpu\_workqueue\_struct来抽象，这些cpu\_workqueue\_struct们共享一个workqueue，毕竟这些worker thread是同一种type。

从底层驱动的角度来看，我们只关心如何处理deferable task（由work\_struct抽象）。驱动程序定义了work\_struct，其func成员就是deferred work，然后挂入work list就OK了（当然要唤醒worker thread了），系统的调度器调度到worker thread的时候，该work自然会被处理了。当然，挂入哪一个workqueue的那一个worker thread呢？如何选择workqueue是driver自己的事情，可以使用系统缺省的workqueue，简单，实用。当然也可以自己创建一个workqueue，并把work挂入其中。选择哪一个worker thread比较简单：work在哪一个cpu上被调度，那么就挂入哪一个worker thread。

四、接口以及内部实现

1、初始化一个work。我们可以静态定义一个work，接口如下：

> #define DECLARE\_WORK(n, f) \   
> struct work\_struct n = \_\_WORK\_INITIALIZER(n, f)
>
> #define DECLARE\_DELAYED\_WORK(n, f) \   
> struct delayed\_work n = \_\_DELAYED\_WORK\_INITIALIZER(n, f)

一般而言，work都是推迟到worker thread被调度的时刻，但是有时候，我们希望在指定的时间过去之后再调度worker thread来处理该work，这种类型的work被称作delayed work，DECLARE\_DELAYED\_WORK用来初始化delayed work，它的概念和普通work类似，本文不再描述。

动态创建也是OK的，不过初始化的时候需要把work的指针传递给INIT\_WORK，定义如下：

> #define INIT\_WORK(\_work, \_func) \   
> do { \   
> (\_work)->data = (atomic\_long\_t) WORK\_DATA\_INIT(); \   
> INIT\_LIST\_HEAD(&(\_work)->entry); \   
> PREPARE\_WORK((\_work), (\_func)); \   
> } while (0)

2、调度一个work执行。调度work执行有两个接口，一个是schedule\_work，将work挂入缺省的系统workqueue（keventd\_wq），另外一个是queue\_work，可以将work挂入指定的workqueue。具体代码如下：

> int fastcall queue\_work(struct workqueue\_struct \*wq, struct work\_struct \*work)   
> {   
> int ret = 0;
>
> if (!test\_and\_set\_bit(WORK\_STRUCT\_PENDING, work\_data\_bits(work))) {   
> \_\_queue\_work(wq\_per\_cpu(wq, get\_cpu()), work);－－－挂入work list并唤醒worker thread   
> put\_cpu();   
> ret = 1;   
> }   
> return ret;   
> }

处于pending状态的work不会重复挂入workqueue。我们假设A驱动模块静态定义了一个work，当中断到来并分发给cpu0的时候，中断handler会在cpu0上执行，我们在handler中会调用schedule\_work将该work挂入cpu0的worker thread，也就是keventd 0的work list。在worker thread处理A驱动的work之前，中断很可能再次触发并分发给cpu1执行，这时候，在cpu1上执行的handler在调用schedule\_work的时候实际上是没有任何具体的动作的，也就是说该work不会挂入keventd 1的work list，因为该work还pending在keventd 0的work list中。

到底插入workqueue的哪一个worker thread呢？这是由wq\_per\_cpu定义的：

> static struct cpu\_workqueue\_struct \*wq\_per\_cpu(struct workqueue\_struct \*wq, int cpu)   
> {   
> if (unlikely(is\_single\_threaded(wq)))   
> cpu = singlethread\_cpu;   
> return per\_cpu\_ptr(wq->cpu\_wq, cpu);   
> }

普通情况下，都是根据当前的cpu id，通过per\_cpu\_ptr获取cpu\_workqueue\_struct的数据结构，对于single thread而言，cpu是固定的。

3、创建workqueue，接口如下：

> #define create\_workqueue(name) \_\_create\_workqueue((name), 0, 0)   
> #define create\_freezeable\_workqueue(name) \_\_create\_workqueue((name), 1, 1)   
> #define create\_singlethread\_workqueue(name) \_\_create\_workqueue((name), 1, 0)

create\_workqueue是创建普通workqueue，也就是每个cpu创建一个worker thread的那种。当然，作为“普通”的workqueue，在freezeable属性上也是跟随缺省的行为，即在suspend的时候不冻结该内核线程的worker thread。create\_freezeable\_workqueue和create\_singlethread\_workqueue都是创建single thread workqueue，只不过一个是freezeable的，另外一个是non-freezeable的。的代码如下：

> struct workqueue\_struct \*\_\_create\_workqueue(const char \*name, int singlethread, int freezeable)   
> {   
> struct workqueue\_struct \*wq;   
> struct cpu\_workqueue\_struct \*cwq;   
> int err = 0, cpu;
>
> wq = kzalloc(sizeof(\*wq), GFP\_KERNEL);－－－－分配workqueue的数据结构
>
> wq->cpu\_wq = alloc\_percpu(struct cpu\_workqueue\_struct);－－－分配worker thread的数据结构
>
> wq->name = name;－－－－－－－－－－初始化workqueue   
> wq->singlethread = singlethread;   
> wq->freezeable = freezeable;   
> INIT\_LIST\_HEAD(&wq->list);
>
> if (singlethread) {－－－－－－－－－－－－－－－－－－－－－－－（1）   
> cwq = init\_cpu\_workqueue(wq, singlethread\_cpu); －－－初始化cpu\_workqueue\_struct   
> err = create\_workqueue\_thread(cwq, singlethread\_cpu); －－－创建worker thread   
> start\_workqueue\_thread(cwq, -1); －－－－wakeup worker thread   
> } else { －－－－－－－－－－－－－－－－－－－－－－－－－－－－－（2）   
> mutex\_lock(&workqueue\_mutex);   
> list\_add(&wq->list, &workqueues);
>
> for\_each\_possible\_cpu(cpu) {   
> cwq = init\_cpu\_workqueue(wq, cpu);   
> if (err || !cpu\_online(cpu)) －－－－没有online的cpu就不需要创建worker thread了   
> continue;   
> err = create\_workqueue\_thread(cwq, cpu);   
> start\_workqueue\_thread(cwq, cpu);   
> }   
> mutex\_unlock(&workqueue\_mutex);   
> }   
> return wq;   
> }

（1）不管是否是single thread workqueue，worker thread（cpu\_workqueue\_struct）的数据结构总是per cpu分配的（稍显浪费），不过实际上对于single thread workqueue而言，只会使用其中之一，那么问题来了：使用哪一个processor的cpu\_workqueue\_struct呢？workqueue代码定义了一个singlethread\_cpu的变量，如下：

> static int singlethread\_cpu \_\_read\_mostly;

该变量会在init\_workqueues函数中进行初始化。实际上，使用哪一个cpu的cpu\_workqueue\_struct是无所谓的，选择其一就OK了。由于是single thread workqueue，因此创建的worker thread并不绑定在任何的cpu上，调度器可以自由的调度该内核线程在任何的cpu上运行。

（2）对于普通的workqueue，和single thread的处理有所有不同。一方面，single thread的workqueue没有挂入workqueues的全局链表，另外一方面for\_each\_possible\_cpu确保在每一个cpu上创建了一个worker thread并通过start\_workqueue\_thread启动其运行，具体代码如下：

> static void start\_workqueue\_thread(struct cpu\_workqueue\_struct \*cwq, int cpu)   
> {   
> struct task\_struct \*p = cwq->thread;
>
> if (p != NULL) {   
> if (cpu >= 0)   
> kthread\_bind(p, cpu);   
> wake\_up\_process(p);   
> }   
> }

对于single thread，kthread\_bind不会执行，对于普通的workqueue，我们必须调用kthread\_bind以便让worker thread在特定的cpu上执行。

4、work执行的时机

work执行的时机是和调度器相关的，当系统调度到worker thread这个内核线程后，该thread就会开始工作。每个cpu上执行的worker thread的内核线程的代码逻辑都是一样的，在worker\_thread中实现：

> static int worker\_thread(void \*\_\_cwq)   
> {   
> struct cpu\_workqueue\_struct \*cwq = \_\_cwq;   
> DEFINE\_WAIT(wait);
>
> if (cwq->wq->freezeable)－－－如果是freezeable的内核线程，那么需要清除task flag中的   
> set\_freezable(); PF\_NOFREEZE标记，以便在系统suspend的时候冻结该thread
>
> set\_user\_nice(current, -5); －－－－提高进程优先级，呵呵，worker thread还是有些特权的哦
>
> for (;;) {   
> prepare\_to\_wait(&cwq->more\_work, &wait, TASK\_INTERRUPTIBLE);   
> if (!freezing(current) && !kthread\_should\_stop() && list\_empty(&cwq->worklist))   
> schedule();－－－－－－－－－－－－－－（1）   
> finish\_wait(&cwq->more\_work, &wait);
>
> try\_to\_freeze(); －－－－－－处理来自电源管理模块的冻结请求
>
> if (kthread\_should\_stop()) －－－－－处理停止该thread的请求   
> break;
>
> run\_workqueue(cwq); －－－－－－依次处理work list上的各个work   
> }
>
> return 0;   
> }

（1）导致worker thread进入sleep状态有三个条件：（a）电源管理模块没有请求冻结该worker thread。（b）该thread没有被其他模块请求停掉。（c）work list为空，也就是说没有work要处理

*原创文章，转发请注明出处。蜗窝科技*
