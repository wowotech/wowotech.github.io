---
title: "Linux内核同步机制之（六）：Seqlock"
date: 2015-09-09T11:55:00+08:00
url: "/kernel_synchronization/seqlock.html"
gid: "209"
emlog_type: "blog"
summary: "普通的spin lock对待reader和writer是一视同仁，RW spin lock给reader赋予了更高的优先级，那么有没有让writer优先的锁的机制呢？答案就是seqlock。本文主要描述linux kernel 4.0中的seqlock的机制，首先是seqlock的工作原理，如果想浅尝辄止，那么了解了概念性的东东就OK了，也就是第二章了，当然，我还是推荐 普通的驱动工程师了解seq"
author: "linuxer"
category: "内核同步机制"
category_alias: "kernel_synchronization"
tags: ["Seqlock"]
views: 27170
comment_count: 34
aliases:
  - "/kernel_synchronization/209.html"
  - "/209.html"
---

一、前言

普通的spin lock对待reader和writer是一视同仁，RW spin lock给reader赋予了更高的优先级，那么有没有让writer优先的锁的机制呢？答案就是seqlock。本文主要描述linux kernel 4.0中的seqlock的机制，首先是seqlock的工作原理，如果想浅尝辄止，那么了解了概念性的东东就OK了，也就是第二章了，当然，我还是推荐普通的驱动工程师了解seqlock的API，第三章给出了一个简单的例子，了解了这些，在驱动中（或者在其他内核模块）使用seqlock就可以易如反掌了。细节是魔鬼，概念性的东西需要天才的思考，不是说就代码实现的细节就无足轻重，如果想进入seqlock的内心世界，推荐阅读第四章seqlock的代码实现，这一章和cpu体系结构相关的内容我们选择了ARM64（呵呵～～要跟上时代的步伐）。最后一章是参考资料，如果觉得本文描述不清楚，可以参考这些经典文献，在无数不眠之夜，她们给我心灵的慰籍，也愿能够给读者带来快乐。

二、工作原理

1、overview

seqlock这种锁机制是倾向writer thread，也就是说，除非有其他的writer thread进入了临界区，否则它会长驱直入，无论有多少的reader thread都不能阻挡writer的脚步。writer thread这么霸道，reader肿么办？对于seqlock，reader这一侧需要进行数据访问的过程中检测是否有并发的writer thread操作，如果检测到并发的writer，那么重新read。通过不断的retry，直到reader thread在临界区的时候，没有任何的writer thread插入即可。这样的设计对reader而言不是很公平，特别是如果writer thread负荷比较重的时候，reader thread可能会retry多次，从而导致reader thread这一侧性能的下降。

总结一下seqlock的特点：临界区只允许一个writer thread进入，在没有writer thread的情况下，reader thread可以随意进入，也就是说reader不会阻挡reader。在临界区只有有reader thread的情况下，writer thread可以立刻执行，不会等待。

2、writer thread的操作

对于writer thread，获取seqlock操作如下：

（1）获取锁（例如spin lock），该锁确保临界区只有一个writer进入。

（2）sequence counter加一

释放seqlock操作如下：

（1）释放锁，允许其他writer thread进入临界区。

（2）sequence counter加一（注意：不是减一哦，sequence counter是一个不断累加的counter）

由上面的操作可知，如果临界区没有任何的writer thread，那么sequence counter是偶数（sequence counter初始化为0），如果临界区有一个writer thread（当然，也只能有一个），那么sequence counter是奇数。

3、reader thread的操作如下：

（1）获取sequence counter的值，如果是偶数，可以进入临界区，如果是奇数，那么等待writer离开临界区（sequence counter变成偶数）。进入临界区时候的sequence counter的值我们称之old sequence counter。

（2）进入临界区，读取数据

（3）获取sequence counter的值，如果等于old sequence counter，说明一切OK，否则回到step（1）

4、适用场景。一般而言，seqlock适用于：

（1）read操作比较频繁

（2）write操作较少，但是性能要求高，不希望被reader thread阻挡（之所以要求write操作较少主要是考虑read side的性能）

（3）数据类型比较简单，但是数据的访问又无法利用原子操作来保护。我们举一个简单的例子来描述：假设需要保护的数据是一个链表，header--->A node--->B node--->C node--->null。reader thread遍历链表的过程中，将B node的指针赋给了临时变量x，这时候，中断发生了，reader thread被preempt（注意，对于seqlock，reader并没有禁止抢占）。这样在其他cpu上执行的writer thread有充足的时间释放B node的memory（注意：reader thread中的临时变量x还指向这段内存）。当read thread恢复执行，并通过x这个指针进行内存访问（例如试图通过next找到C node），悲剧发生了……

三、API示例

在kernel中，jiffies\_64保存了从系统启动以来的tick数目，对该数据的访问（以及其他jiffies相关数据）需要持有jiffies\_lock这个seq lock。

1、reader side代码如下：

> u64 get\_jiffies\_64(void)   
> {
>
> do {   
> seq = read\_seqbegin(&jiffies\_lock);   
> ret = jiffies\_64;   
> } while (read\_seqretry(&jiffies\_lock, seq));   
> }

2、writer side代码如下：

> static void tick\_do\_update\_jiffies64(ktime\_t now)   
> {   
> write\_seqlock(&jiffies\_lock);
>
> 临界区会修改jiffies\_64等相关变量，具体代码略   
> write\_sequnlock(&jiffies\_lock);   
> }

对照上面的代码，任何工程师都可以比着葫芦画瓢，使用seqlock来保护自己的临界区。当然，seqlock的接口API非常丰富，有兴趣的读者可以自行阅读seqlock.h文件。

四、代码实现

1、seq lock的定义

> typedef struct {   
> struct seqcount seqcount;－－－－－－－－－－sequence counter   
> spinlock\_t lock;   
> } seqlock\_t;

seq lock实际上就是spin lock ＋ sequence counter。

2、write\_seqlock/write\_sequnlock

> static inline void write\_seqlock(seqlock\_t \*sl)   
> {   
> spin\_lock(&sl->lock);
>
> sl->sequence++;   
> smp\_wmb();   
> }

唯一需要说明的是smp\_wmb这个用于SMP场合下的写内存屏障，它确保了编译器以及CPU都不会打乱sequence counter内存访问以及临界区内存访问的顺序（临界区的保护是依赖sequence counter的值，因此不能打乱其顺序）。write\_sequnlock非常简单，留给大家自己看吧。

3、read\_seqbegin

> static inline unsigned read\_seqbegin(const seqlock\_t \*sl)   
> {   
> unsigned ret;
>
> repeat:   
> ret = ACCESS\_ONCE(sl->sequence); －－－进入临界区之前，先要获取sequenc counter的快照   
> if (unlikely(ret & 1)) { －－－－－如果是奇数，说明有writer thread   
> cpu\_relax();   
> goto repeat; －－－－如果有writer，那么先不要进入临界区，不断的polling sequenc counter   
> }
>
> smp\_rmb(); －－－确保sequenc counter和临界区的内存访问顺序   
> return ret;   
> }

如果有writer thread，read\_seqbegin函数中会有一个不断polling sequenc counter，直到其变成偶数的过程，在这个过程中，如果不加以控制，那么整体系统的性能会有损失（这里的性能指的是功耗和速度）。因此，在polling过程中，有一个cpu\_relax的调用，对于ARM64，其代码是：

> static inline void cpu\_relax(void)   
> {   
> asm volatile("yield" ::: "memory");   
> }

yield指令用来告知硬件系统，本cpu上执行的指令是polling操作，没有那么急迫，如果有任何的资源冲突，本cpu可以让出控制权。

4、read\_seqretry

> static inline unsigned read\_seqretry(const seqlock\_t \*sl, unsigned start)   
> {   
> smp\_rmb();－－－确保sequenc counter和临界区的内存访问顺序   
> return unlikely(sl->sequence != start);   
> }

start参数就是进入临界区时候的sequenc counter的快照，比对当前退出临界区的sequenc counter，如果相等，说明没有writer进入打搅reader thread，那么可以愉快的离开临界区。

还有一个比较有意思的逻辑问题：read\_seqbegin为何要进行奇偶判断？把一切都推到read\_seqretry中进行判断不可以吗？也就是说，为何read\_seqbegin要等到没有writer thread的情况下才进入临界区？其实有writer thread也可以进入，反正在read\_seqretry中可以进行奇偶以及相等判断，从而保证逻辑的正确性。当然，这样想也是对的，不过在performance上有欠缺，reader在检测到有writer thread在临界区后，仍然放reader thread进入，可能会导致writer thread的一些额外的开销（cache miss），因此，最好的方法是在read\_seqbegin中拦截。

五、参考文献

1、Understanding the Linux Kernel 3rd Edition

2、Linux Kernel Development 3rd Edition

3、Perfbook ([https://www.kernel.org/pub/linux/kernel/people/paulmck/perfbook/perfbook.html](https://www.kernel.org/pub/linux/kernel/people/paulmck/perfbook/perfbook.html "https://www.kernel.org/pub/linux/kernel/people/paulmck/perfbook/perfbook.html"))

*原创文章，转发请注明出处。蜗窝科技*
