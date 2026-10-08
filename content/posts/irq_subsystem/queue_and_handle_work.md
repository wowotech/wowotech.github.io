---
title: "Concurrency Managed Workqueue之（四）：workqueue如何处理work"
date: 2015-08-17T19:41:51+08:00
url: "/irq_subsystem/queue_and_handle_work.html"
gid: "207"
emlog_type: "blog"
summary: "\r\n\t本文主要讲述下面两部分的内容：\r\n\r\n\r\n\t1、将work挂入workqueue的处理过程\r\n\r\n\r\n\t2、如何处理挂入workqueue的work\r\n"
author: "linuxer"
category: "中断子系统"
category_alias: "irq_subsystem"
tags: ["workqueue", "Concurrency", "Managed"]
views: 27773
comment_count: 17
aliases:
  - "/irq_subsystem/207.html"
  - "/207.html"
---

一、前言

本文主要讲述下面两部分的内容：

1、将work挂入workqueue的处理过程

2、如何处理挂入workqueue的work

二、用户将一个work挂入workqueue

1、queue\_work\_on函数

使用workqueue机制的模块可以调用queue\_work\_on（有其他变种的接口，这里略过，其实思路是一致的）将一个定义好的work挂入workqueue，具体代码如下：

> bool queue\_work\_on(int cpu, struct workqueue\_struct \*wq, struct work\_struct \*work)   
> {   
> ……
>
> if (!test\_and\_set\_bit(WORK\_STRUCT\_PENDING\_BIT, work\_data\_bits(work))) {   
> \_\_queue\_work(cpu, wq, work);－－－挂入work list并通知worker thread pool来处理   
> ret = true;   
> }
>
> ……   
> }

work\_struct的data member中的WORK\_STRUCT\_PENDING\_BIT这个bit标识了该work是处于pending状态还是正在处理中，pending状态的work只会挂入一次。大部分的逻辑都是在\_\_queue\_work函数中，下面的小节都是描述该函数的执行过程。

2、\_\_WQ\_DRAINING的解释

\_\_queue\_work函数一开始会校验\_\_WQ\_DRAINING这个flag，如下：

> if (unlikely(wq->flags & \_\_WQ\_DRAINING) && WARN\_ON\_ONCE(!is\_chained\_work(wq)))   
>         return;

\_\_WQ\_DRAINING这个flag表示该workqueue正在进行draining的操作，这多半是发送在销毁workqueue的时候，既然要销毁，那么挂入该workqueue的所有的work都要处理完毕，才允许它消亡。当想要将一个workqueue中所有的work都清空的时候，如果还有work挂入怎么办？一般而言，这时候当然是不允许新的work挂入了，毕竟现在的目标是清空workqueue中的work。但是有一种特例（通过is\_chained\_work判定），也就是正在清空的work（隶属于该workqueue）又触发了一个queue work的操作（也就是所谓chained work），这时候该work允许挂入。

3、选择pool workqueue

> if (req\_cpu == WORK\_CPU\_UNBOUND)   
> cpu = raw\_smp\_processor\_id();
>
> if (!(wq->flags & WQ\_UNBOUND))   
> pwq = per\_cpu\_ptr(wq->cpu\_pwqs, cpu);   
> else   
> pwq = unbound\_pwq\_by\_node(wq, cpu\_to\_node(cpu));

WORK\_CPU\_UNBOUND表示并不指定cpu，这时候，选择当前代码运行的那个cpu了。一旦确定了cpu了，对于非unbound的workqueue，当然使用per cpu的pool workqueue。如果是unbound的workqueue，那么要根据numa node id来选择。cpu\_to\_node可以从cpu id获取node id。需要注意的是：这里选择的pool wq只是备选的，可能用也可能不用，它有可能会被替换掉，具体参考下一节描述。

4、选择worker thread pool

与其说挂入workqueue，不如说挂入worker thread pool，因为毕竟是线程池来处理具体的work。pool\_workqueue有一个相关联的worker thread pool（struct pool\_workqueue的pool成员），因此看起来选择了pool wq也就选定了worker pool了，但是，不是当前选定的那个pool wq对应的worker pool就适合该work，因为有时候该work可能正在其他的worker thread上执行中，在这种情况下，为了确保work的callback function不会重入，该work最好还是挂在那个worker thread pool上，具体代码如下：

> last\_pool = get\_work\_pool(work);   
> if (last\_pool && last\_pool != pwq->pool) {   
> struct worker \*worker;
>
> spin\_lock(&last\_pool->lock);
>
> worker = find\_worker\_executing\_work(last\_pool, work);
>
> if (worker && worker->current\_pwq->wq == wq) {   
> pwq = worker->current\_pwq;   
> } else {   
> /\* meh... not running there, queue here \*/   
> spin\_unlock(&last\_pool->lock);   
> spin\_lock(&pwq->pool->lock);   
> }   
> } else {   
> spin\_lock(&pwq->pool->lock);   
> }

last\_pool记录了上一次该work是被哪一个worker pool处理的，如果last\_pool就是pool wq对应的worker pool，那么皆大欢喜，否则只能使用last pool了。使用last pool的例子比较复杂一些，因为这时候需要根据last worker pool找到对应的pool workqueue。find\_worker\_executing\_work函数可以找到具体哪一个worker线程正在处理该work，如果没有找到，那么还是使用第3节中选定的pool wq吧，否则，选择该worker线程当前的那个pool workqueue（其实也就是选定了线程池）。

5、选择work挂入的队列

队列有两个，一个是被推迟执行的队列（pwq->delayed\_works），一个是线程池要处理的队列（pwq->pool->worklist），如果挂入线程池要处理的队列，也就意味着该work进入active状态，线程池会立刻启动处理流程，如果挂入推迟执行的队列，那么该work还是pending状态：

> pwq->nr\_in\_flight[pwq->work\_color]++;   
> work\_flags = work\_color\_to\_flags(pwq->work\_color);
>
> if (likely(pwq->nr\_active < pwq->max\_active)) {   
> pwq->nr\_active++;   
> worklist = &pwq->pool->worklist;   
> } else {   
> work\_flags |= WORK\_STRUCT\_DELAYED;   
> worklist = &pwq->delayed\_works;   
> }
>
> insert\_work(pwq, work, worklist, work\_flags);

具体的挂入队列的动作是在insert\_work函数中完成的。

6、唤醒idle的worker来处理该work

在insert\_work函数中有下面的代码：

> if (\_\_need\_more\_worker(pool))   
> wake\_up\_worker(pool);

当线程池中正在运行状态的worker线程数目等于0的时候，说明需要wakeup线程池中处于idle状态的的worker线程来处理work。

三、线程池如何创建worker线程？

1、per cpu worker pool什么时候创建worker线程？

对于per-CPU workqueue，每个cpu有两个线程池，一个是normal，一个是high priority的。在初始化函数init\_workqueues中有对这两个线程池的初始化：

> for\_each\_online\_cpu(cpu) {   
> struct worker\_pool \*pool;
>
> for\_each\_cpu\_worker\_pool(pool, cpu) {   
> pool->flags &= ~POOL\_DISASSOCIATED;   
> BUG\_ON(!create\_worker(pool));   
> }   
> }

因此，在系统初始化的时候，per cpu workqueue共享的那些线程池（2 x cpu nr）就会通过create\_worker创建一个initial worker。

一旦initial worker启动，该线程会执行worker\_thread函数来处理work，在处理过程中，如果有需要， worker会创建新的线程。

2、unbound thread pool什么时候创建worker线程？

我们先看看unbound thread pool的建立，和per-CPU不同的是unbound thread pool是全局共享的，因此，每当创建不同属性的unbound workqueue的时候，都需要创建pool\_workqueue及其对应的worker pool，这时候就会调用get\_unbound\_pool函数在当前系统中现存的线程池中找是否有匹配的worker pool，如果没有就需要创建新的线程池。在创建新的线程池之后，会立刻调用create\_worker创建一个initial worker。和per cpu worker pool一样，一旦initial worker启动，随着work不断的挂入以及worker处理work的具体情况，线程池会动态创建worker。

3、如何创建worker。代码如下：

> static struct worker \*create\_worker(struct worker\_pool \*pool)   
> {   
> struct worker \*worker = NULL;   
> int id = -1;   
> char id\_buf[16];
>
> id = ida\_simple\_get(&pool->worker\_ida, 0, 0, GFP\_KERNEL);－－－－分配ID
>
> worker = alloc\_worker(pool->node);－－－－－分配worker struct的内存
>
> worker->pool = pool;   
> worker->id = id;
>
> if (pool->cpu >= 0)－－－－－－－－－worker的名字   
> snprintf(id\_buf, sizeof(id\_buf), "%d:%d%s", pool->cpu, id, pool->attrs->nice < 0 ? "H" : "");   
> else   
> snprintf(id\_buf, sizeof(id\_buf), "u%d:%d", pool->id, id);
>
> worker->task = kthread\_create\_on\_node(worker\_thread, worker, pool->node, "kworker/%s", id\_buf);
>
> set\_user\_nice(worker->task, pool->attrs->nice); －－－创建task并设定nice value   
> worker->task->flags |= PF\_NO\_SETAFFINITY;   
> worker\_attach\_to\_pool(worker, pool); －－－－－建立worker和线程池的关系
>
> spin\_lock\_irq(&pool->lock);   
> worker->pool->nr\_workers++;   
> worker\_enter\_idle(worker);   
> wake\_up\_process(worker->task);－－－－－－让worker运行起来   
> spin\_unlock\_irq(&pool->lock);
>
> return worker;   
> }

代码不复杂，通过线程池（struct worker\_pool）绑定的cpu信息（struct worker\_pool的cpu成员）可以知道该pool是per-CPU还是unbound，对于per-CPU线程池，pool->cpu是大于等于0的。对于对于per-CPU线程池，其worker线程的名字是kworker/*cpu*：*worker id*，如果是high priority的，后面还跟着一个H字符。对于unbound线程池，其worker线程的名字是kworker/u *pool id*：*worker id。*

四、work的处理

本章主要描述worker\_thread函数的执行流程，部分代码有删节，保留主干部分。

1、PF\_WQ\_WORKER标记

worker线程函数一开始就会通过PF\_WQ\_WORKER来标注自己：

> worker->task->flags |= PF\_WQ\_WORKER;

有了这样一个flag，调度器在调度当前进程sleep的时候可以检查这个准备sleep的进程是否是一个worker线程，如果是的话，那么调度器不能鲁莽的调度到其他的进程，这时候，还需要找到该worker对应的线程池，唤醒一个idle的worker线程。通过workqueue模块和调度器模块的交互，当work A被阻塞后（处理该work的worker线程进入sleep），调度器会唤醒其他的worker线程来处理其他的work B，work C……

2、管理线程池中的线程

> recheck:   
> if (!need\_more\_worker(pool))   
> goto sleep;
>
> if (unlikely(!may\_start\_working(pool)) && manage\_workers(worker))   
> goto recheck;

如何判断是否需要创建更多的worker线程呢？原则如下：

（1）有事情做：挂在worker pool中的work list不能是空的，如果是空的，那么当然sleep就好了

（2）比较忙：worker pool的nr\_running成员表示线程池中当前正在干活（running状态）的worker线程有多少个，当nr\_running等于0表示所有的worker线程在处理work的时候阻塞了，这时候，必须要启动新的worker线程来处理worker pool上处于active状态的work链表上的work们。

3、worker线程开始处理work

> worker\_clr\_flags(worker, WORKER\_PREP | WORKER\_REBOUND);
>
> do {   
> struct work\_struct \*work = list\_first\_entry(&pool->worklist, struct work\_struct, entry);
>
> if (likely(!(\*work\_data\_bits(work) & WORK\_STRUCT\_LINKED))) {   
> process\_one\_work(worker, work);   
> if (unlikely(!list\_empty(&worker->scheduled)))   
> process\_scheduled\_works(worker);   
> } else {   
> move\_linked\_works(work, &worker->scheduled, NULL);   
> process\_scheduled\_works(worker);   
> }   
> } while (keep\_working(pool));
>
> worker\_set\_flags(worker, WORKER\_PREP);

按理说worker线程处理work应该比较简单，从线程池的worklist中取一个work，然后调用process\_one\_work处理之就OK了，不过现实稍微复杂一些，work和work之间并不是独立的，也就是说，work A和work B可能是linked work，这些linked work应该被一个worker来处理。WORK\_STRUCT\_LINKED标记了work是属于linked work，如果是linked work，worker并不直接处理，而是将其挂入scheduled work list，然后调用process\_scheduled\_works来处理。毫无疑问，process\_scheduled\_works也是调用process\_one\_work来处理一个一个scheduled work list上的work。

scheduled work list并非仅仅应用在linked work，在worker处理work的时候，有一个原则要保证：同一个work不能被同一个cpu上的多个worker同时执行。这时候，如果worker发现自己要处理的work正在被另外一个worker线程处理，那么本worker线程将不处理该work，只需要挂入正在执行该work的worker线程的scheduled work list即可。

*原创文章，转发请注明出处。蜗窝科技*
