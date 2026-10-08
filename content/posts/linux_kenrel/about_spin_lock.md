---
title: "关于spin_lock的问题"
date: 2014-12-12T14:10:09+08:00
url: "/linux_kenrel/about_spin_lock.html"
gid: "122"
emlog_type: "blog"
summary: "spin_lock的分析文章Google一下有很多，这里只是分享一些关于spin_lock思考过的问题。"
author: "Physh"
category: "Linux内核分析"
category_alias: "linux_kenrel"
tags: ["spin_lock"]
views: 21917
comment_count: 4
aliases:
  - "/linux_kenrel/122.html"
  - "/122.html"
---

spin\_lock的分析文章Google一下有很多，这里只是分享一些关于spin\_lock思考过的问题。

一、UP 下spin\_lock的实现

UP的情况下，spin\_lock本身并没有实现锁机制，相对应的spin\_lock()只是禁用了内核抢占而已。如下代码：

```
//@include/linux/spinlock_api_up.h

#define _raw_spin_lock(lock)                    __LOCK(lock)



/*

 * In the UP-nondebug case there's no real locking going on, so the

 * only thing we have to do is to keep the preempt counts and irq

 * flags straight, to suppress compiler warnings of unused lock

 * variables, and to add the proper checker annotations:

 */

#define __LOCK(lock) \

    do { preempt_disable(); __acquire(lock); (void)(lock); } while (0)
```

```












#define preempt_disable() \

do { \

         preempt_count_inc(); \

         barrier(); \

 } while (0)

```

由以上代码可知，UP下spin\_lock仅仅是禁用了内核抢占，而此时IRQ是可以正常触发的。那就先考虑tick中断——即，UP下，持有spin\_lock的进程会被调度器切走么？

1）UP下，spin\_lock() 是不会失败的, 但spin\_lock() 保护的临界代码还是需要一定时间执行的，这期间内核抢占被禁止，那当前进程有可能被切走么?

先假设CFS（先假设调度器用的是CFS）在禁止内核抢占的情况下不会将当前进程切走，那么，仅仅禁用内核抢占可以保证临界区代码不会被进程上下文重入；如果，CFS并不理会抢占计数，会强制剥夺当前进程的CPU使用权，那么就存在spin\_lock()保护的临界区代码被进程上下文重入的问题。

2）再考虑，spin\_lock() 临界区被中断上下文重入的问题。

以上两点，都不会造成死锁或者CPU Halt， 因为UP下spin\_lock()没有进行锁等待，所以存在的就只是代码重入问题，也即，即便用spin\_lock()进行保护，这段代码还是有被重入的可能。

那问题已经提出来了，就看看代码如何实现？先看CFS的周期调度代码，如下代码确认当前进程是否需要重新调度：

```
static void check_preempt_tick(struct cfs_rq *cfs_rq, struct sched_entity *curr)

{

	....

	ideal_runtime = sched_slice(cfs_rq, curr);

	/*

	 * 计算该进程的预期运行时间：

	 *

	 *当cfs_rq中的运行进程不大于sched_nr_latency(8)时，各个进程的ideal_runtime是一个常量

	 *之所以是常量，是因为period是常量(sysctl_sched_latency=6000000)。

	 *当cfs_rq中的运行进程大于sched_nr_latency时，period = nr_running * sysctl_sched_min_granularity;

	 *其中，sysctl_sched_min_granularity是750000.

	 *ideal_runtime *= period * weight/load;

	 */

	if (delta_exec > ideal_runtime)

	{

		//delta_exec 实际运行的时间已经超过其预计运行时间，

		//调用resched_task将该进程设置为TIF_NEED_RESCHED,即需要重新调度的；

		resched_task(rq_of(cfs_rq)->curr);

		//clear buddy cache??

		//个人的理解是buddy的缓冲信息可能会影响CFS，使其优先选择有buddy缓冲

		//的进程，更高效的利用缓冲。

		clear_buddies(cfs_rq, curr); 

		return;

	}

	//如果运行时间小于sysctl_sched_min_granularity(最小执行时间)

	//则直接返回，让当前继续执行。

	if (delta_exec < sysctl_sched_min_granularity)

			return;

	

	se = __pick_first_entity(cfs_rq);

	delta = curr->vruntime - se->vruntime;

	//如果最左边的se并不处于饥渴等待状态。

	//可能当前进程的没得到足够执行时间，或者当前进程的优先级比最左边se更高。

	//这种情况下，直接返回，让当前进程接着跑。

	if (delta < 0) 

		return;

	

	//如果最左边的se的等待时间已经大于curr的ideal_runtime，表明处于CPU饥渴

	//状态，则将当前task设置成TIF_NEED_RESCHED，触发调度；

	if (delta > ideal_runtime)

		resched_task(rq_of(cfs_rq)->curr);

}
```

由此可见，这里也只是设置了RESCHED FLAG，真正的调度工作还是交给了中断返回时的do\_work\_pending()，而我们知道内核抢占被禁用的情况下，当前进程是不会被切走的，即不会重新调度，所以第一个问题就澄清了，即进程上下文重入的问题是不会发生的。

接着，中断上下文是否会发生重入？考虑这样的情况：进程A陷入内核，获取spin\_lock，正在执行临界区代码，被IRQ打断，且ISR中要获取同一个spin\_lock，在UP下，ISR不会由于锁等待而halt住，中断返回后，进程A继续执行，就像什么都没发生过一样，但是这样就没有起到防止重入的作用，临界变量可能已经改变，而进程A却不知道。而这种情况，仔细想想除了禁用本地中断之外似乎没有什么办法可以避免了。

所以，在UP情况下，如果临界区有可能被ISR访问的话，那么就应该是用 spin\_lock\_irq() 而不是仅仅用 spin\_lock() 了事。

二、SMP下 spin\_lock 的实现

spin\_lock 在SMP下实现肯定要比UP下复杂得多，看代码：

```
//@include/linux/spinlock_api_smp.h

static inline void __raw_spin_lock(raw_spinlock_t *lock)

 {

         preempt_disable();

         spin_acquire(&lock->dep_map, 0, 0, _RET_IP_);

         LOCK_CONTENDED(lock, do_raw_spin_trylock, do_raw_spin_lock);

}
```

preempt\_disable()不再解释，spin\_acquire() 是sparse检查需要，用来检查死锁的，LOCK\_CONTENDED是一个宏定义，先调用do\_raw\_spin\_trylock()尝试获得锁，不等待，如果失败在调用do\_raw\_spin\_lock() 忙等待unlock. do\_row\_spin\_trylock()的代码不分析了，和do\_raw\_spin\_lock()一样，只是不循环等待，直接看do\_raw\_spin\_lock()代码：

```
static inline void arch_spin_lock(arch_spinlock_t *lock)

{

	unsigned long tmp;



	__asm__ __volatile__(

"1:	ldrex	%0, [%1]\n"

"	teq	%0, #0\n"

	WFE("ne")

"	strexeq	%0, %2, [%1]\n"

"	teqeq	%0, #0\n"

"	bne	1b"

	: "=&r" (tmp)

	: "r" (&lock->lock), "r" (1)

	: "cc");



	smp_mb();

}
```

这段内嵌汇编首先检查lock->lock，如果等于0，就表明现在是unlock状态，就把lock->lock置位1，表示lock状态。这段汇编里边，关键的三个指令是：ldrex, strexeq, WFE, 前两个指令实现独占访问储存器，保证"读取-修改-写入”在芯片级是原子的，而WFE是wait for event， 和WFI类似，只是他可以被SEV指令唤醒，在spin\_unlock()的时候，会发出SEV。

具体可以参见蜗蜗的文章：[/armv8a_arch/wfe_wfi.html](/device_model/device_resource_management.html)

了解SMP 平台下的spin\_lock之后，还是那两个问题，进程上下文重入和中断上下文重入。第一个问题已经澄清，那第二个问题呢？重现之前的情景：进程A陷入内核，获取spin\_lock，正在执行临界区代码，被本地IRQ打断，且ISR中要获取同一个spin\_lock， 在SMP下，ISR就要调用WFE进入low-power-mode，这样持有锁的内核路径也得不到运行，所以无法释放锁资源，ISR也就只能一直WFE，本地CPU就这样挂掉了。当然，当IRQ在其他CPU上的时候，这种情况是不会发生的，另一个CPU为WFE直到本地CPU释放锁资源。

所以，这样又回到之前的解决办法，如果ISR有可能重入临界区，那么就应该使用 spin\_lock\_irq() 而非 spin\_lock()。如果不这样使用，在UP下，临界数据将错乱，而在SMP下，CPU将死锁。

（完）
