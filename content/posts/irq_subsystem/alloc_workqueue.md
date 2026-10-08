---
title: "Concurrency Managed Workqueue之（三）：创建workqueue代码分析"
date: 2015-08-06T18:22:41+08:00
url: "/irq_subsystem/alloc_workqueue.html"
gid: "204"
emlog_type: "blog"
summary: "本文主要以__alloc_workqueue_key函数为主线，描述CMWQ中的创建一个workqueue实例的代码过程。"
author: "linuxer"
category: "中断子系统"
category_alias: "irq_subsystem"
tags: ["alloc_workqueue"]
views: 34517
comment_count: 38
aliases:
  - "/irq_subsystem/204.html"
  - "/204.html"
---

一、前言

本文主要以\_\_alloc\_workqueue\_key函数为主线，描述CMWQ中的创建一个workqueue实例的代码过程。

二、WQ\_POWER\_EFFICIENT的处理

\_\_alloc\_workqueue\_key函数的一开始有如下的代码：

> if ((flags & WQ\_POWER\_EFFICIENT) && wq\_power\_efficient)   
> flags |= WQ\_UNBOUND;

在kernel中，有两种线程池，一种是线程池是per cpu的，也就是说，系统中有多少个cpu，就会创建多少个线程池，cpu x上的线程池创建的worker线程也只会运行在cpu x上。另外一种是unbound thread pool，该线程池创建的worker线程可以调度到任意的cpu上去。由于cache locality的原因，per cpu的线程池的性能会好一些，但是对power saving有一些影响。设计往往如此，workqueue需要在performance和power saving之间平衡，想要更好的性能，那么最好让一个cpu上的worker thread来处理work，这样的话，cache命中率会比较高，性能会更好。但是，从电源管理的角度来看，最好的策略是让idle状态的cpu尽可能的保持idle，而不是反复idle，working，idle again。

我们来一个例子辅助理解上面的内容。在t1时刻，work被调度到CPU A上执行，t2时刻work执行完毕，CPU A进入idle，t3时刻有一个新的work需要处理，这时候调度work到那个CPU会好些呢？是处于working状态的CPU B还是处于idle状态的CPU A呢？如果调度到CPU A上运行，那么，由于之前处理过work，其cache内容新鲜热辣，处理起work当然是得心应手，速度很快，但是，这需要将CPU A从idle状态中唤醒。选择CPU B呢就不存在将CPU 从idle状态唤醒，从而获取power saving方面的好处。

了解了上面的基础内容之后，我们再来检视per cpu thread pool和unbound thread pool。当workqueue收到一个要处理的work，如果该workqueue是unbound类型的话，那么该work由unbound thread pool处理并把调度该work去哪一个CPU执行这样的策略交给系统的调度器模块来完成，对于scheduler而言，它会考虑CPU core的idle状态，从而尽可能的让CPU保持在idle状态，从而节省了功耗。因此，如果一个workqueue有WQ\_UNBOUND这样的flag，则说明该workqueue上挂入的work处理是考虑到power saving的。如果workqueue没有WQ\_UNBOUND flag，则说明该workqueue是per cpu的，这时候，调度哪一个CPU core运行worker thread来处理work已经不是scheduler可以控制的了，这样，也就间接影响了功耗。

有两个参数可以控制workqueue在performance和power saving之间的平衡：

1、各个workqueue需要通过WQ\_POWER\_EFFICIENT来标记自己在功耗方面的属性

2、系统级别的内核参数workqueue.power\_efficient。

使用workqueue的用户知道自己在电源管理方面的特点，如果该workqueue在unbound的时候会极大的降低功耗，那么就需要加上WQ\_POWER\_EFFICIENT的标记。这时候，如果没有标记WQ\_UNBOUND，那么缺省workqueue会创建per cpu thread pool来处理work。不过，也可以通过workqueue.power\_efficient这个内核参数来修改workqueue的行为：

> #ifdef CONFIG\_WQ\_POWER\_EFFICIENT\_DEFAULT   
> static bool wq\_power\_efficient = true;   
> #else   
> static bool wq\_power\_efficient;   
> #endif
>
> module\_param\_named(power\_efficient, wq\_power\_efficient, bool, 0444);

如果wq\_power\_efficient设定为true，那么WQ\_POWER\_EFFICIENT的标记的workqueue就会强制按照unbound workqueue来处理，即使没有标记WQ\_UNBOUND。

三、分配workqueue的内存

> if (flags & WQ\_UNBOUND)   
> tbl\_size = nr\_node\_ids \* sizeof(wq->numa\_pwq\_tbl[0]); －－－only for unbound workqueue
>
> wq = kzalloc(sizeof(\*wq) + tbl\_size, GFP\_KERNEL);
>
> if (flags & WQ\_UNBOUND) {   
> wq->unbound\_attrs = alloc\_workqueue\_attrs(GFP\_KERNEL); －－only for unbound workqueue   
> }

代码很简单，与其要解释代码，不如来解释一些基本概念。

1、workqueue和pool workqueue的关系

我们先给出一个简化版本的workqueue\_struct定义，如下：

> struct workqueue\_struct {   
> struct list\_head pwqs;   
> struct list\_head list;
>
> struct pool\_workqueue \_\_percpu \*cpu\_pwqs; －－－－－指向per cpu的pool workqueue   
> struct pool\_workqueue \_\_rcu \*numa\_pwq\_tbl[]; －－－－指向per node的pool workqueue   
> };

这里涉及2个数据结构：workqueue\_struct和pool\_workqueue，为何如此处理呢？我们知道，在CMWQ中，workqueue和thread pool没有严格的一一对应关系了，因此，系统中的workqueue们共享一组thread pool，因此，workqueue中的成员包括两个类别：global类型和per thread pool类型的，我们把那些per thread pool类型的数据集合起来就形成了pool\_workqueue的定义。

挂入workqueue的work终究需要worker pool中的某个worker thread来处理，也就是说，workqueue要和系统中那些共享的worker thread pool进行连接，这是通过pool\_workqueue（该数据结构会包含一个指向worker pool的指针）的数据结构来管理的。和这个workqueue相关的pool\_workqueue被挂入一个链表，链表头就是workqueue\_struct中的pwqs成员。

和旧的workqueue机制一样，系统维护了一个所有workqueue的list，list head定义如下：

> static LIST\_HEAD(workqueues);

workqueue\_struct中的list成员就是挂入这个链表的节点。

workqueue有两种：unbound workqueue和per cpu workqueue。对于per cpu类型，cpu\_pwqs指向了一组per cpu的pool\_workqueue数据结构，用来维护workqueue和per cpu thread pool之间的关系。每个cpu都有两个thread pool，normal和高优先级的线程池，到底cpu\_pwqs指向哪一个pool\_workqueue（worker thread）是和workqueue的flag相关，如果标有WQ\_HIGHPRI，那么cpu\_pwqs指向高优先级的线程池。unbound workqueue对应的pool\_workqueue和workqueue属性相关，我们在下一节描述。

2、workqueue attribute

挂入workqueue的work终究是需要worker线程来处理，针对worker线程有下面几个考量点（我们称之attribute）：

（1）该worker线程的优先级

（2）该worker线程运行在哪一个CPU上

（3）如果worker线程可以运行在多个CPU上，且这些CPU属于不同的NUMA node，那么是否在所有的NUMA node中都可以获取良好的性能。

对于per-CPU的workqueue，2和3不存在问题，哪个cpu上queue的work就在哪个cpu上执行，由于只能在一个确定的cpu上执行，因此起NUMA的node也是确定的（一个CPU不可能属于两个NUMA node）。置于优先级，per-CPU的workqueue使用WQ\_HIGHPRI来标记。综上所述，per-CPU的workqueue不需要单独定义一个workqueue attribute，这也是为何在workqueue\_struct中只有unbound\_attrs这个成员来记录unbound workqueue的属性。

unbound workqueue由于不绑定在具体的cpu上，可以运行在系统中的任何一个cpu，直觉上似乎系统中有一个unbound thread pool就OK了，不过让一个thread pool创建多种属性的worker线程是一个好的设计吗？本质上，thread pool应该创建属性一样的worker thread。因此，我们通过workqueue属性来对unbound workqueue进行分类，workqueue属性定义如下：

> struct workqueue\_attrs {   
> int nice; /\* nice level \*/   
> cpumask\_var\_t cpumask; /\* allowed CPUs \*/   
> bool no\_numa; /\* disable NUMA affinity \*/   
> };

nice是一个和thread优先级相关的属性，nice越低则优先级越高。cpumask是该workqueue挂入的work允许在哪些cpu上运行。no\_numa是一个和NUMA affinity相关的设定。

3、unbound workqueue和NUMA之间的联系

UMA系统中，所有的processor看到的内存都是一样的，访问速度也是一样，无所谓local or remote，因此，内核线程如果要分配内存，那么也是无所谓，统一安排即可。在NUMA系统中，不同的一个或者一组cpu看到的memory是不一样的，我们假设node 0中有CPU A和B，node 1中有CPU C和D，如果运行在CPU A上内核线程现在要迁移到CPU C上的时候，悲剧发生了：该线程在A CPU创建并运行的时候，分配的内存是node 0中的memory，这些memory是local的访问速度很快，当迁移到CPU C上的时候，原来local memory变成remote，性能大大降低。因此，unbound workqueue需要引入NUMA的考量点。

NUMA是内存管理的范畴，本文不会深入描述，我们暂且放开NUMA，先思考这样的一个问题：一个确定属性的unbound workqueue需要几个线程池？看起来一个就够了，毕竟workqueue的属性已经确定了，一个线程池创建相同属性的worker thread就行了。但是我们来看一个例子：假设workqueue的work是可以在node 0中的CPU A和B，以及node 1中CPU C和D上处理，如果只有一个thread pool，那么就会存在worker thread在不同node之间的迁移问题。为了解决这个问题，实际上unbound workqueue实际上是创建了per node的pool\_workqueue（thread pool）

当然，是否使用per node的pool workqueue用户是可以通过下面的参数进行设定的：

（1）workqueue attribute中的no\_numa成员

（2）通过workqueue.disable\_numa这个参数，disable所有workqueue的numa affinity的支持。

> static bool wq\_disable\_numa;   
> module\_param\_named(disable\_numa, wq\_disable\_numa, bool, 0444);

四、初始化workqueue的成员

> va\_start(args, lock\_name);   
> vsnprintf(wq->name, sizeof(wq->name), fmt, args);－－－－－set workqueue name   
> va\_end(args);
>
> max\_active = max\_active ?: WQ\_DFL\_ACTIVE;   
> max\_active = wq\_clamp\_max\_active(max\_active, flags, wq->name);   
> wq->flags = flags;   
> wq->saved\_max\_active = max\_active;   
> mutex\_init(&wq->mutex);   
> atomic\_set(&wq->nr\_pwqs\_to\_flush, 0);   
> INIT\_LIST\_HEAD(&wq->pwqs);   
> INIT\_LIST\_HEAD(&wq->flusher\_queue);   
> INIT\_LIST\_HEAD(&wq->flusher\_overflow);   
> INIT\_LIST\_HEAD(&wq->maydays);
>
> lockdep\_init\_map(&wq->lockdep\_map, lock\_name, key, 0);   
> INIT\_LIST\_HEAD(&wq->list);

除了max active，没有什么要说的，代码都简单而且直观。如果用户没有设定max active（或者说max active等于0），那么系统会给出一个缺省的设定。系统定义了两个最大值WQ\_MAX\_ACTIVE（512）和WQ\_UNBOUND\_MAX\_ACTIVE（和cpu数目有关，最大值是cpu数目乘以4，当然也不能大于WQ\_MAX\_ACTIVE），分别限定per cpu workqueue和unbound workqueue的最大可以创建的worker thread的数目。wq\_clamp\_max\_active可以将max active限制在一个确定的范围内。

五、分配pool workqueue的内存并建立workqueue和pool workqueue的关系

这部分的代码主要涉及alloc\_and\_link\_pwqs函数，如下：

> static int alloc\_and\_link\_pwqs(struct workqueue\_struct \*wq)   
> {   
> bool highpri = wq->flags & WQ\_HIGHPRI;－－－－normal or high priority？   
> int cpu, ret;
>
> if (!(wq->flags & WQ\_UNBOUND)) {－－－－－per cpu workqueue的处理   
> wq->cpu\_pwqs = alloc\_percpu(struct pool\_workqueue);
>
> for\_each\_possible\_cpu(cpu) {－－－－－逐个cpu进行设定   
> struct pool\_workqueue \*pwq = per\_cpu\_ptr(wq->cpu\_pwqs, cpu);   
> struct worker\_pool \*cpu\_pools = per\_cpu(cpu\_worker\_pools, cpu);
>
> init\_pwq(pwq, wq, &cpu\_pools[highpri]);   
> link\_pwq(pwq);－－－－上面两行代码用来建立workqueue、pool wq和thread pool之间的关系   
> }   
> return 0;   
> } else if (wq->flags & \_\_WQ\_ORDERED) {－－－－－ordered unbound workqueue的处理   
> ret = apply\_workqueue\_attrs(wq, ordered\_wq\_attrs[highpri]);   
> return ret;   
> } else {－－－－－unbound workqueue的处理   
> return apply\_workqueue\_attrs(wq, unbound\_std\_wq\_attrs[highpri]);   
> }   
> }

通过alloc\_percpu可以为每一个cpu分配一个pool\_workqueue的memory。每个pool\_workqueue都有一个对应的worker thread pool，对于per-CPU workqueue，它是静态定义的，如下：

> static DEFINE\_PER\_CPU\_SHARED\_ALIGNED(struct worker\_pool [NR\_STD\_WORKER\_POOLS],   
> cpu\_worker\_pools);

init\_pwq函数初始化pool\_workqueue，最重要的是设定其对应的workqueue和worker pool。link\_pwq主要是将pool\_workqueue挂入它所属的workqueue的链表中。对于unbound workqueue，apply\_workqueue\_attrs完成分配pool workqueue并建立workqueue和pool workqueue的关系。

六、应用新的attribute到workqueue中

unbound workqueue有两种，一种是normal type，另外一种是ordered type，这种workqueue上的work是严格按照顺序执行的，不存在并发问题。ordered unbound workqueue的行为类似过去的single thread workqueue。但是，无论那种类型的unbound workqueue都使用apply\_workqueue\_attrs来建立workqueue、pool wq和thread pool之间的关系。

1、健康检查。

> if (WARN\_ON(!(wq->flags & WQ\_UNBOUND)))   
> return -EINVAL;
>
> if (WARN\_ON((wq->flags & \_\_WQ\_ORDERED) && !list\_empty(&wq->pwqs)))   
> return -EINVAL;

只有unbound类型的workqueue才有attribute，才可以apply attributes。对于ordered类型的unbound workqueue，属于它的pool workqueue（worker thread pool）只能有一个，否则无法限制work是按照顺序执行。

2、分配内存并初始化

> pwq\_tbl = kzalloc(nr\_node\_ids \* sizeof(pwq\_tbl[0]), GFP\_KERNEL);   
> new\_attrs = alloc\_workqueue\_attrs(GFP\_KERNEL);   
> tmp\_attrs = alloc\_workqueue\_attrs(GFP\_KERNEL);   
> copy\_workqueue\_attrs(new\_attrs, attrs);   
> cpumask\_and(new\_attrs->cpumask, new\_attrs->cpumask, cpu\_possible\_mask);   
> copy\_workqueue\_attrs(tmp\_attrs, new\_attrs);

pwq\_tbl数组用来保存unbound workqueue各个node的pool workqueue的指针，new\_attrs和tmp\_attrs都是一些计算workqueue attribute的中间变量，开始的时候设定为用户传入的workqueue的attribute。

3、如何为unbound workqueue的pool workqueue寻找对应的线程池？

具体的代码在get\_unbound\_pool函数中。本节不描述具体的代码，只说明基本原理，大家可以自行阅读代码。

per cpu的workqueue的pool workqueue对应的线程池也是per cpu的，每个cpu有两个线程池（normal和high priority），因此将pool workqueue和thread pool对应起来是非常简单的事情。对于unbound workqueue，对应关系没有那么直接，如果属性相同，多个unbound workqueue的pool workqueue可能对应一个thread pool。

系统使用哈希表来保存所有的unbound worker thread pool，定义如下：

> static DEFINE\_HASHTABLE(unbound\_pool\_hash, UNBOUND\_POOL\_HASH\_ORDER);

在创建unbound workqueue的时候，pool workqueue对应的worker thread pool需要在这个哈希表中搜索，如果有相同属性的worker thread pool的话，那么就不需要创建新的线程池，代码如下：

> hash\_for\_each\_possible(unbound\_pool\_hash, pool, hash\_node, hash) {   
> if (wqattrs\_equal(pool->attrs, attrs)) { －－－－检查属性是否相同   
> pool->refcnt++;   
> return pool; －－－－－－－在哈希表找到适合的unbound线程池   
> }   
> }

如果没有相同属性的thread pool，那么需要创建一个并挂入哈希表。

4、给各个node分配pool workqueue并初始化

在进入代码之前，先了解一些基础知识。缺省情况下，挂入unbound workqueue的works最好是考虑NUMA Affinity，这样可以获取更好的性能。当然，实际上用户可以通过workqueue.disable\_numa这个内核参数来关闭这个特性，这时候，系统需要一个default pool workqueue（workqueue\_struct的dfl\_pwq成员），所有的per node的pool workqueue指针都是执行default pool workqueue。

workqueue.disable\_numa是enable的情况下是否不需要default pool workqueue了呢？也不是，我们举一个简单的例子，一个系统的构成是这样的：node 0中有CPU A和B，node 1中有CPU C和D，node 2中有CPU E和F，假设workqueue的attribute规定work只能在CPU A 和C上运行，那么在node 0和node 1中创建自己的pool workqueue是ok的，毕竟node 0中有CPU A，node 1中有CPU C，该node创建的worker thread可以在A或者C上运行。但是对于node 2节点，没有任何的CPU允许处理该workqueue的work，在这种情况下，没有必要为node 2建立自己的pool workqueue，而是使用default pool workqueue。

OK，我们来看代码：

> dfl\_pwq = alloc\_unbound\_pwq(wq, new\_attrs); －－－－－分配default pool workqueue
>
> for\_each\_node(node) { －－－－遍历node   
> if (wq\_calc\_node\_cpumask(attrs, node, -1, tmp\_attrs->cpumask)) { －－－是否使用default pool wq   
> pwq\_tbl[node] = alloc\_unbound\_pwq(wq, tmp\_attrs); －－－该node使用自己的pool wq   
> } else {   
> dfl\_pwq->refcnt++;   
> pwq\_tbl[node] = dfl\_pwq; －－－－该node使用default pool wq   
> }   
> }

值得一提的是wq\_calc\_node\_cpumask这个函数，这个函数会根据该node的cpu情况以及workqueue attribute中的cpumask成员来更新tmp\_attrs->cpumask，因此，在pwq\_tbl[node] = alloc\_unbound\_pwq(wq, tmp\_attrs); 这行代码中，为该node分配pool workqueue对应的线程池的时候，去掉了本node中不存在的cpu。例如node 0中有CPU A和B，workqueue的attribute规定work只能在CPU A 和C上运行，那么创建node 0上的pool workqueue以及对应的worker thread pool的时候，需要删除CPU C，也就是说，node 0上的线程池的属性中的cpumask仅仅支持CPU A了。

5、安装

所有的node的pool workqueue及其worker thread pool已经ready，需要安装到workqueue中了：

> for\_each\_node(node)   
> pwq\_tbl[node] = numa\_pwq\_tbl\_install(wq, node, pwq\_tbl[node]);   
> link\_pwq(dfl\_pwq);   
> swap(wq->dfl\_pwq, dfl\_pwq);

代码非常简单，这里就不细述了。

*原创文章，转发请注明出处。蜗窝科技*
