---
title: "蜗窝微信群问题整理"
date: 2017-07-11T19:00:50+08:00
url: "/tech_discuss/question_set_1.html"
gid: "400"
emlog_type: "blog"
summary: "蜗窝微信群开张了，这个群是为那些愿意慢下来，仔细研究内核技术、愿意为了搞清楚内核代码逻辑而废寝忘食的工程师准备的，在这个群里，大家讨论了一些技术问题，当然，也有一些问题没有解决和答案。鉴于微信群的特点，我还是把大家讨论的技术整理了一下，分享出来，希望能够对其他工程师有所帮助。"
author: "linuxer"
category: "技术漫谈"
category_alias: "tech_discuss"
tags: ["蜗窝微信群"]
views: 16402
comment_count: 12
aliases:
  - "/tech_discuss/400.html"
  - "/400.html"
---

前言：蜗窝微信群开张了，这个群是为那些愿意慢下来，仔细研究内核技术、愿意为了搞清楚内核代码逻辑而废寝忘食的工程师准备的，在这个群里，大家讨论了一些技术问题，当然，也有一些问题没有解决和答案。鉴于微信群的特点，我还是把大家讨论的技术整理了一下，分享出来，希望能够对其他工程师有所帮助。

问题一：请问sysconf(\_SC\_CLK\_TCK)拿到的HZ是不是jiffies的频率呢？如果是为何我内核配置的HZ是250，但是这个函数返回的是100？这是为什么？

1、userspace需要知道内核中的HZ的配置吗？

其实用户空间应该不需要关心内核HZ的设定，所以那个接口其实是没意义，毕竟这是内核的特性，也许内核是tickless的呢？。用户空间和时间相关接口用纳秒就好，不要用tick值表示时间，否则用户空间还要转换成纳秒，而且需要知道内核HZ，封装性不好。

2、既然不需要，那么这个接口是干什么的？

这个函数返回的是USER\_TICK而不是真是内核的HZ，因此虽然你的内核配置是250，但是sysconf(**\_SC\_CLK\_TCK**)依然返回100。

虽然新的程序不建议使用这个接口，但是市面上还有众多的老的程序还是依赖这些接口的，因此，为了兼容的原因，userspace和kernel还是还是需要交互tick的，内核采用的办法是这样的：HZ是内核自己使用，定义USER\_TICK用于和userspace接口，内核在返回用户空间的时候会转换成USER\_TICK。

3、怎么实现的？

用户空间和内核空间有很多交互的形态，例如大家最熟悉的就是系统调用。不过我们这里sysconf(\_SC\_CLK\_TCK)函数并没有引发系统调用，她使用的是auxiliary vector。

一个程序的二进制文件在被加载的过程中（代码位于linux/fs/binfmt\_elf.c）, 会通过若干NEW\_AUX\_ENT来定义auxiliary vector table，具体和这个场景的代码如下：

> NEW\_AUX\_ENT(AT\_CLKTCK, CLOCKS\_PER\_SEC);
>
> # define USER\_HZ 100 /\* some user interfaces are \*/   
> # define CLOCKS\_PER\_SEC (USER\_HZ) /\* in "ticks" like times() \*/

而在程序中，可以通过调用getauxval(AT\_CLKTCK) 来或者这个tick就是固定为100。当然，还可以用sysconf(\_SC\_CLK\_TCK)，这个函数其实也是辗转调用了getauxval(AT\_CLKTCK) 来获取user tick。

4、如何使用

主要的使用场景包括：

（1）times函数计算进程时间。这个函数返回tick为单位的数值

（2）用户空间的proc接口有需要使用USER\_TICK来转换。

问题二：大家好，我碰到一个问题，关于linux
kernel workqueue的，版本是3.0。

我们的硬件平台的情况是这样的： arm 有两个 core, 内部audio DSP通过IPC与arm core通信.

软件相关的框架是这样的：

1、音频驱动使用了中断线程化处理

2、interrupt thread中接收数据并放入fifo，然后queue work通知worker线程来处理fifo中的msg

3、用户空间操作alsa audio in 和audio out设备的进程读写数据(注意，2个进程都是rt进程，rt priority是60. 并且这两个进程跑在哪个core上是随机的)

4、双核配置，其中音频中断送达其中一个CPU

5、DSP和ARM之间的中断的交互特点是这样的：

（1）DSP送往ARM的ack只是送往core 0

（2）ARM core 0和core 1都会送ack给DSP，DSP会记录该信息并将中断送达会送ack的那个ARM core

刚开始，fifo处理使用system\_wq, 但是会出现音频来不及处理的情况(从现象猜测，出现问题的时候, 发现其中一个RT进程的cpu loading 满载)，用create\_workqueue()创建了per cpu的wq，问题有改善，但是问题依然存在，最后改成了alloc\_workqueue unbond来创建wq，经过反复测试，问题就没有再出现了。按理说调用create\_wq创建per cpu的workqueue应该有很好的through表现，反倒是调用unbond才能解决问题，这有点奇怪，请问大家有什么看法？

大家分析如下：

1、我们假设中断送达cpu0，那么如果不出意外的话，interrupt
thread应该是也是在cpu0，并且优先级是50，低于用户空间的进程。

2、如果使用per cpu的workqueue的话，那么在interrupt thread中queue work的话，那么该work线程也是在cpu 0执行，work线程是普通进程。

3、整个数据处理过程是：interrupt thread ---> workqueue-> handle function -----> 用户空间RT进程

4、如果数据处理大部分位于interrupt thread 和workqueue中，那么整个数据处理是失衡的，大部分压在在中断送达的那个CPU0上

5、改用unbound workqueue的话，在interrupt thread中queue的work不是固定绑定在cpu 0上执行，因此数据处理比较流畅。

6、主要的数据处理在worker线程中，但是它的优先级最低。受两端夹击，最终导致fifo满从而丢失了音频数据。

最后原因定位：

1. 在内核添加打印, 发现handle
function函数, 有的时候会卡住, 原因不明

2. 打开kernel lockup and hang detection后, 可定位到hang住时跑的backtrace。有了栈的回溯，问题容易定位了。

问题三：ps和top的优先级为何看起来不是很一样？ps的rtprio是正数，而TOP中的实时进程是负数？

通过ps –eo class,rtprio,ni,comm命令看到的是实时进程的调度优先级（rtprio）和普通进程的nice value（ni）。这个比较符合内核工程师的习惯：

1、 如果是实时进程，那么rtprio是1～99，如果不是，那么显示“－“

2、 如果是普通进程，那么rtprio显示“－“，ni显示-20~19

通过top看到的两个和优先级相关的域是PR和NI，分别表示进程的动态优先级（task\_struct中的prio成员）和nice value。

我们先看看普通进程的场景，对于CFS之前的内核（2.6.23），PR显示的是基于静态优先级NI的动态优先级，当一个进程开始运行的时候，PR=NI+20，一旦运行起来，动态优先级会在一个范围内摆动，具体的摆动范围是和进程状态相关。例如如果该进程sleep较长的时间，那么它应该多占用一些CPU，因此其动态优先级PR会降低（实际的优先级是升高的）。相关，如果一个进程占用太多的CPU时间，那么其动态优先级PR值会降升高（实际动态优先级是降低的），因此该进程更容易被其他进程抢占。

在引入CFS之后，由于调度器算法发生了变化，进程睡眠时间比较久也没有什么“折扣“了，一切都是按照最大公平的原则来调度进程，因此，这时候PR固定等于NI加20。

上面说的是普通进程，对于RT进程，PN应该展示的是基于（task\_struct中的rt\_priority成员）的动态优先级。具体在内核中如何运算大家可以自行查阅代码，但是来到用户空间（proc/pid/stat），这个动态优先级则是-100~-1。其中-100是最高优先级。

在top程序中的逻辑是：

> if (unlikely(-99 > p->priority) || unlikely(999 < p->priority)) {
>
> f = " rt"; －－输出rt这两个字符
>
> } else
>
> MKCOL((int)p->priority);－－输出实际的优先级

也就是说当用户级进程调用接口设定为最高优先级（99）的时候（top的视角是-100），显示的就只有rt两个字符，其他时候会显示出一个负值。为何是负值？猜想是延续nice的习惯，越是小的数值越是不nice，优先级高。具体的转换公式大家可以参考内核代码，而rt\_priority的50对应top 视角的-51。

问题四：小弟最近在看，经典rcu的实现（linux2.6.23），其中对于每个cpu度过一个静默期的判断有疑问。代码如下：

> void rcu\_check\_callbacks(int cpu, int user)   
> {   
> if (user || －－－－－－－－－－－－－－－－－－－A   
> (idle\_cpu(cpu) && !in\_softirq() && －－－－－－－B   
> hardirq\_count() <= (1 << HARDIRQ\_SHIFT))) {   
> rcu\_qsctr\_inc(cpu);   
> rcu\_bh\_qsctr\_inc(cpu);   
> } else if (!in\_softirq())   
> rcu\_bh\_qsctr\_inc(cpu);   
> tasklet\_schedule(&per\_cpu(rcu\_tasklet, cpu));   
> }

代码A处比较好理解，如果timer命中用户空间，那么说明至少发生了一次进程切换，当然要标记本CPU的QS状态，但是B处的判断怎么理解？

回答：对于经典RCU来说，标记本CPU的QS状态有两个条件：

1、经历一次用户态/内核态切换 ，也就是有进程切换

2、当前任务为IDLE进程，说明有其他任务切换到idle进程的动作

代码中A的判断调试针对上面的case 1，B条件对应上面的case 2，不过，在case2，我们需要排除一些其他的场景。

对于B条件，为什么要加上软中断和硬中断计数，其实也比较好理解：因为中断可以随意的打断任何任务，当然也包含IDLE任务。如果在TICK处理之前，已经有中断嵌套了，那么在上一次嵌套中断里面，很可能进入了RCU读端临界区，这种情况下，当前TICK显示不能经过静止状态。

问题五：各位大神，我在看lock dep . 什么是 hardirq safe lock？ 还有什么是 hard irq unsafe lock？看不明白，为何 hard irq safe lock -> hard irq unsafe lock 是不允许的？

回答：

1、所谓hardirq safe 就是在关中断的时候拿的锁，一般用在中断上下文和进程上下文同步的场景。

2、hardirq unsafe 的锁就是lockdep检测到没有在关中断的时候拿到的锁，所以unsafe，而获取该锁是需要关中断的。

3、如果允许hardirq safe -> hardirq unsafe, 那么可能会造成死锁

4、一个实际的例子：考虑一个情况，进程在拿到锁B (unsafe)的时候被中断，中断里先拿锁A (safe) 在去拿锁B (unsafe) 这个时候就会死锁

5、这个规则就是说在中断中用到的锁，在进程上下文中如果想要用，必须关中断。

这些信息太凌乱，其实blog这部分希望是能发表一些整理后的文章，显然，这一篇不符合要求。但是我又希望能有一个微信群讨论技术问题的输出窗口，因此后续不在整理微信群的问题整理文档，并发表在博客，后续会将微信群的讨论内容转移到蜗窝讨论区，请大家移步去哪里获取相关信息。
