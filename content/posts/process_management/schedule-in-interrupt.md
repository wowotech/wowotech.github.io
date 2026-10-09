---
title: "中断上下文中调度会怎样？"
date: 2017-03-20T19:08:14+08:00
url: "/process_management/schedule-in-interrupt.html"
gid: "387"
emlog_type: "blog"
summary: "每一个Linux驱动工程师都知道这样一个准则：在中断上下文中不能睡眠。但是为什么interrupt context中不能调用导致睡眠的kernel API呢？如果驱动这么做会导致什么样的后果呢？这就是本文探讨的主题。为了理解这个主题，我们设计了一些非常简单的驱动程序和用户空间的程序，实际做实验观察实验效果，最后给出了结果和分析。"
author: "linuxer"
category: "进程管理"
category_alias: "process_management"
tags: ["中断", "调度"]
views: 33618
comment_count: 38
aliases:
  - "/process_management/387.html"
  - "/387.html"
---

一、前言

每一个Linux驱动工程师都知道这样一个准则：在中断上下文中不能睡眠。但是为什么interrupt context中不能调用导致睡眠的kernel API呢？如果驱动这么做会导致什么样的后果呢？这就是本文探讨的主题。为了理解这个主题，我们设计了一些非常简单的驱动程序和用户空间的程序，实际做实验观察实验效果，最后给出了结果和分析。

BTW，本文的实验在X86 64bit ＋ 标准4.4内核上完成。

二、测试程序

1、cst驱动模块

我们首先准备一个能够在中断上下文中睡眠的驱动程序，在这里我称之Context schedule test module（后文简称cst模块）。这个驱动程序类似潜伏在内核中的“捣蛋鬼”，每隔1秒随机命中一个进程，然后引发调度。首先准备一个Makefile，代码如下：

> KERNELSRC ?= /home/xxxx/work/linux-4.4.6
>
> default:   
> $(MAKE) -C $(KERNELSRC) M=$$PWD
>
> clean:   
> $(MAKE) -C $(KERNELSRC) M=$$PWD clean

按理说代码中的xxxx应该是我的名字，如果你愿意在你的环境中测试，可以修改成你的名字，当然，最重要的是需要某个版本的内核代码。在[内核升级](/linux_application/debian8-upgrade-kernel.html)文档中，我已经编译了/home/xxxx/work/linux-4.4.6目录下的内核，并把我的计算机升级到4.4.6的内核上，如果你愿意可以按照那份文档进行升级，否则可能会有一些版本问题需要处理。除了Makefile之外，还需要一个Kbuild文件：

> obj-m := cst.o

当然，最重要的是cst模块的源代码：

> #include    
> #include    
> #include    
> #include
>
> #define DRIVER\_DESC "context schedule test driver"
>
> static struct timer\_list cst\_timer;
>
> static void cst\_timer\_handler (unsigned long data)   
> {   
> struct task\_struct \*p = current;
>
> pr\_info("=====in timer handler=====\n");   
> pr\_info("cst shoot %16s [%x] task:\n", p->comm, preempt\_count());   
> mod\_timer(&cst\_timer, jiffies + HZ);   
> schedule();   
> }
>
> static int \_\_init cst\_init(void)   
> {   
> init\_timer(&cst\_timer);   
> cst\_timer.function = cst\_timer\_handler;   
> cst\_timer.expires = jiffies + HZ;   
> add\_timer(&cst\_timer);
>
> pr\_info(DRIVER\_DESC " : init on cpu:%d\n", smp\_processor\_id());   
> return 0;   
> }   
> module\_init(cst\_init);
>
> static void \_\_exit cst\_exit(void)   
> {   
> del\_timer\_sync(&cst\_timer);   
> pr\_info(DRIVER\_DESC " : exit\n");   
> }   
> module\_exit(cst\_exit);
>
> MODULE\_DESCRIPTION(DRIVER\_DESC);   
> MODULE\_AUTHOR("linuxer ");   
> MODULE\_LICENSE("GPL");

代码非常的简单，无需多说，直接make就可以编译得到cst.ko的内核模块了。

2、用户空间测试程序

为了更方便的测试，我们需要准备一个“受害者”，代码如下：

> #include    
> #include
>
> int main(int argc, char \*\*argv)   
> {   
> int i = 0;
>
> while (1) {   
> sqrt (rand ());
>
> if ((i % 0xffffff) == 0)   
> printf ("=\n");
>
> if ((i % 0xfffffff) == 0)   
> printf ("haha......still alive\n");
>
> i++;   
> }
>
> return 0;   
> }

这段代码也很简单：不断的产生一个随机数，并运算其平方根，在使得的时候，向用户输出一些字符，表明自己的状态。当程序执行起来的时候，大部分时间在用户态（运算），偶尔进入内核态（printf）。这个进程并不知道在内核态有一个cst的模块，每隔一秒就发射一只休眠之箭，可能命中用户态，也可能命中内核态，看运气吧，但是无论怎样，该进程被射中之后都会进入睡眠。

三、执行测试并观察结果

1、先把用户空间的测试程序跑起来

要想测试导弹（呵呵～～我们的cst模块就是一个捣蛋） 的性能，必须要有靶机或者靶舰。当然也可以不用“靶机”程序，只不过捣蛋鬼cst总是命中swapper进程，有点无趣，因此这里需要把我们用户空间的那个测试程序跑起来，让CPU先活跃起来。

需要注意的是，在多核cpu上，我们需要多跑几个“靶机”进程才能让系统不会always进入idle状态。例如我的T450是4核cpu，因此我需要运行4个靶机程序才能让系统中的4个cpu core都燥起来。可以通过下面的命令确认：

> ps –eo comm,psr | grep cst

BTW，靶机程序是cst\_test。通过上面的命令，可以看到系统中运行了四个cst\_test进程，分别在4个cpu上。

2、插入内核模块

靶机已经就绪，是时候发射捣蛋了，命令如下：

> sudo insmod ./cst.ko

一旦插入了cst内核模块，捣蛋鬼就开始运作了，每隔1秒钟发射一次，总有一个倒霉蛋被命中，被调度。当然，在我们的测试中，一般总是cst\_test这个进程被命中。

3、观察结果

一切准备就绪，是时候搬个小板凳坐下来看好戏了。当然，我们需要一个观察的工具，输入如下命令：

> sudo tail –f /var/log/messages

在上面的cst模块中，输出并没有直接到控制台，因此我们需要通过内核日志来看看cst的运行情况。

四、结果和分析

1、结果

很奇怪，一切都是正常的，系统没有死，cst模块也运行正常，cst\_test进程也始终保持alive状态，不断的运行在无聊的平方根、打印着无聊的字符串。唯一异常的是日志，每隔1秒钟就会dump stack一次。

2、分析

当cst模块命中cst\_test进程，无论是userspace还是kernel space，都会在内核栈上保存中断发生那一点的上下文，唯一不同是如果发生在userspace，那么发生中断那一刻，内核栈是空的，而如果在kernel space，内核栈上已经有了cst\_test通过系统调用进入内核的现场以及该系统调用各个函数的stack frame，当中断发生的时候，在当前内核栈的栈顶上继续压入了中断现场，之后就是中断处理的各个函数的stack frame，最后是cst\_timer\_handler的stack frame，由于调用了schedule函数，cst\_test进程的现场被继续压入内核栈，调度器决定下一个调度的进程。

cst\_test进程虽然被调度了，但是仍然在runqueue中，调度器一定会在适当的时机调度cst\_test进程重新进入执行态，这时候恢复其执行就OK了，cpu执行cst\_timer\_handler函数schedule之后的代码，继续未完的中断上下文的执行，然后从内核栈恢复中断现场，一切又按照原路返回了。

当然，这里的测试看起来一切OK，但这并不是说可以自由的在中断上下文中调用导致睡眠的内核API，因为我们这里给出了一个简单的例子，实际上也有可能导致系统死锁。例如在内核态持有锁的时候被中断，然后发生调度。有兴趣的同学可以自己修改上面的代码实验这种情况。

3、why

最后还是回到这个具体的技术问题：为什么interrupt context中不能调用导致睡眠的kernel API？

我的看法是这样的：调度器是每一个OS的必备组件，在编码阶段之前，我们往往要制定下我们的设计概念。对于Linux 调度器，它的目标就是调度一个线程，一个线程就是调度实体（暂不考虑group sched）。中断上下文是不是调度实体呢？当然不是，它没有专属的task struct，内核无从调度。这是调度器设计者的决定，这样的决定让调度器设计起来简洁而美丽。

基于上面的设计概念，中断上下文（hard irq和softirq context）并不参与调度（暂不考虑中断线程化），它们是异步事件的处理机制，目标就是尽快完成处理，返回现场。因此，所有中断上下文的优先级都是高于进程上下文的，也就是说，对于用户进程（无论内核态还是用户态）或者内核线程，除非disable了CPU的本地中断，否则一旦中断发生，它们是没有任何能力阻挡中断上下文抢占当前进程上下文的执行的。

因此，Linux kernel的设计者制定了规则：

1、中断上下文不是调度实体

2、中断上下文的优先级高于进程上下文

而在中断上下文中调度毫无疑问会打破规则，因此不能在硬中断、软中断环境中调用阻塞函数。不过，在linux调度器的具体实现的时候，检测到了在中断上下文中调度schedule函数也并没有强制linux进入panic，可能是linux的开发者认为一个好的内核调度器无论如何也尽自己最大的努力让系统运行下去吧。但是，在厂商自己提供的内核中，往往修改调度器行为，在中断上下文中检测到调度就直接panic了，对于内核开发者而言，这样更好，可以尽早的发现问题。

*原创文章，转发请注明出处。蜗窝科技*
