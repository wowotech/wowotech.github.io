---
title: "Linux调度器：用户空间接口"
date: 2017-03-10T18:50:38+08:00
url: "/process_management/scheduler-API.html"
gid: "384"
emlog_type: "blog"
summary: "Linux调度器神秘而充满诱惑，每个Linux工程师都想深入其内部一探究竟。不过中国有一句古话叫做“相由心生”，一个模块精巧的内部逻辑（也就是所谓的“心”）其外延就是简洁而优雅的接口（我称之为“相”）。通过外部接口的定义，其实我们也可以收获百分之六七十的该模块的内部信息。因此，本文主要描述Linux调度器开放给用户空间的接口。"
author: "linuxer"
category: "进程管理"
category_alias: "process_management"
tags: ["调度器", "进程管理"]
views: 14527
comment_count: 3
aliases:
  - "/process_management/384.html"
  - "/384.html"
---

一、前言   
Linux调度器神秘而充满诱惑，每个Linux工程师都想深入其内部一探究竟。不过中国有一句古话叫做“相由心生”，一个模块精巧的内部逻辑（也就是所谓的“心”）其外延就是简洁而优雅的接口（我称之为“相”）。通过外部接口的定义，其实我们也可以收获百分之六七十的该模块的内部信息。因此，本文主要描述Linux调度器开放给用户空间的接口，希望可以通过用户空间的调度器接口来理解Linux调度器的行为。

二、nice函数

nice函数用来修改调用进程的nice value，其接口定义如下：

>       #include  <unistd.h>  
>        int nice(int inc);

为了方便说明该接口的作用，我们还是举实际的例子说明。程序调用nice(3)，则将当前进程的nice value增加3，这也就是意味着该进程的优先级降低3个level（提升nice value也就是对别人更加nice，自己的优先级就会低）。如果程序调用nice(-5)，则将当前进程的nice value减去5，这也就是意味着该进程的优先级提升5个level。当调用错误的时候返回-1，调用成功会稍微有一些歧义。POSIX标准规定了nice函数返回新的nice value，但是linux的系统调用和c库都是采用了操作成功返回0的方式。这样的处理方式使得在调用nice函数的时候无法得到当前的优先级，如果想要得到当前优先级，需要调用getpriority函数，我们在下一小节描述。

虽然说nice函数是用来调整优先级，实际上调整nice value就是调整调度器分配给该进程的CPU时间，具体是如何影响cpu time的呢？我们在后面描述内核代码的时候再详聊。此外，需要注意的是：根据POSIX标准，nice value是一个per process的设定，但是在linux中，nice value没有遵从这个标准，它是per-thread的一个属性。

三、getpriority/setpriority函数

从上节的描述中，我们了解到了nice的函数的限制，例如只能修改自己的nice value，无法获取当前的nice value值等，为此我们给出加强版本的nice接口，也就是getpriority/setpriority函数了。getpriority/setpriority函数定义如下：

> #include  <sys/time.h>  
> #include <sys/resource.h>
>
> int getpriority(int which, int who);   
> int setpriority(int which, int who, int prio);

你说接口增加功能是好事，怎么就把名字也改了呢？为何不是getnice/setnice呢？其实从上节的描述也看出稍许端倪，我们并没有区分调度优先级和nice value这两个值，历史上，首先被使用的是nice value，很快大家觉得这个词不是那么好理解，特别是对于初学者，因此改成优先级（priority）这样的名词可以让用户更好的理解这个API的作用，当然，事实证明这个改动并不是非常理想，我们后面会描述。

getpriority/setpriority功能比较强大，能处理多种请求，不同的请求通过which和who这两个参数来制定。当which等于PRIO\_PROCESS的时候，who需要传入一个process id的参数，getpriority将返回指定进程的nice value。当which等于PRIO\_PGRP的时候，who需要传入一个process group id的参数，此时getpriority将返回指定进程组中优先级最高的那个（BTW，nice value是最小的）。当which等于PRIO\_USER的时候，who需要user id的信息，这时候，getpriority将返回属于该user的所有进程中nice value最小的那个。who等于0说明要get或者set的对象是当前进程（或者当前进程组，或者当前的user）。

setpriority类似与nice，当然功能要强那么一点点，因为它可以接收PRIO\_PROCESS，PRIO\_PGRP或者PRIO\_USER参数用来设定一组进程的nice value。setpriority的返回值和其他函数类似，0表示成功，-1表示操作失败，不过getpriority就稍微有一点绕了。作为linux程序员，我们都知道的nice value是[-20, 19]，如果getpriority返回这个范围，那么这里的-1优先级就有点尴尬了，因为一般的linux c库接口函数返回-1表示调用错误，我们是如何区分-1调用错误的返回还是优先级-1的返回值呢？getpriority是少数返回-1也是有可能正确的接口函数：在调用getpriority之前，我们需要首先将errno清零，调用getpriority之后，如果返回-1，我们需要看看errno是否还是保持0值，如果是，那么说明返回的是优先级-1，否则说明发生了错误。

四、操作rt priority的接口

传统的类unix内核，调度器是采用round-robin time-sharing的算法：如果有若干个进程是runnable的，那么不着急，大家排排队、吃果果，每个进程分配一个cpu时间片，大家轮流按照分配的时间片来获取cpu资源，所有的时间片用完，那么就重新一轮的分配。在这样的模型下面，间接影响cpu时间片的nice接口函数就够用了。当然，分配了更多的时间片也就是意味着有更高的优先级，因此nice vlaue也被称为进程的优先级。

但是，新的需求层出不穷（人类的欲望是无穷D），特别是实时性方面的需求，因此，POSIX标准（2008版本）增加了实时调度的内容，并且提供了POSIX realtime scheduling API来让用户空间来修改调度策略和调度优先级。这下子有点尴尬了，原来的nice value大家已经习惯称之为进程优先级了，现在真正的进程优先级登场了，怎么区分？为了解决这个问题，我们引入一个新的名词叫做调度策略（scheduling policy）。调度器在运作的时候往往设定一组规则来决定何时，选择哪一个进程进入执行状态，执行多长的时间。那些“规则”就是调度策略。

好的调度策略依赖于对进程的分类，有一类进程是大家都灰常的熟悉了就是普通进程，使用时间片轮转算法的那些进程。当然这类进程还可以细分，例如运算密集型进程（SCHED\_BATCH，调度器最好不要太经常的唤醒这种进程），例如idle类进程（SCHED\_IDLE），idle类进程优先级非常低，也就是说如果系统有其他事情要处理就去干别的事情（调度其他进程执行），实在没有活干了，再考虑IDLE类型的进程。不论哪一种普通进程，其优先级使用nice value这样一个调度参数来描述就OK了。

除了普通进程，还有一类是严格按照优先级来调度的进程，如果熟悉RTOS的话，对priority-base的调度器应该不会陌生，官大一级压死人，只要优先级高的进程是runnable的，那么优先级低的进程是根本没有机会执行的。这里的优先级才是真正意义的优先级，但是nice value已经被称为进程优先级了，因此这里的优先级被叫做rt priority。rt进程的调度又被细分成两类：SCHED\_FIFO和SCHED\_RR。这两种调度策略在相同rt priority的时候稍有差别，SCHED\_FIFO是谁先到谁先获取cpu资源，并且一直占用，直到主动让出cpu或者退出，相同rt priority的进程才有机会执行。SCHED\_RR稍微人性化了一点，相同rt priority的进程有时间片，大家轮流执行。对于实时进程而言，rt priority这个调度参数就描述了全部。

介绍到这里，是时候总结一下了：进程优先级有两个范围，一个是nice value，用前两个小节的API来set或者get。另外一个优先级是rt priority，完全碾压nice value这种优先级，操作rt priority的接口就在这一小节描述。

OK，经过漫长的铺垫过程，我们终于可以介绍realtime process scheduling API了，具体API定义如下：

> #include <sched.h>
>
> int sched\_setscheduler(pid\_t pid, int policy, const struct sched\_param \*param);
>
> int sched\_getscheduler(pid\_t pid);
>
> int sched\_get\_priority\_max(int policy);－－返回指定policy的最大的rt priority   
> int sched\_get\_priority\_min(int policy);－－返回指定policy的最小的rt priority
>
> int sched\_setparam(pid\_t pid, const struct sched\_param \*param);   
> int sched\_getparam(pid\_t pid, struct sched\_param \*param);

sched\_get\_priority\_max和sched\_get\_priority\_min分别返回了指定调度策略的最大和最小的rt priority，不同的操作系统实现不同的优先级数量。在linux中，实时进程（SCHED\_FIFO和SCHED\_RR）的rt priority共计99个level，最小是1，最大是99。对于其他的调度策略，这些函数返回0。

sched\_getscheduler函数可以获取指定进程的scheduling policy（如果pid等于0，那么是获取调用进程的调度策略）。sched\_setscheduler函数是用来设定指定进程的scheduling policy，对于实时进程，该接口函数还可以设定rt priority。如果设定进程的调度策略是非实时的调度策略的时候（例如SCHED\_NORMAL），那么param参数是没有意义的，其sched\_priority成员必须设定为0。sched\_setparam/sched\_getparam非常简单，大家自己看man page好了。

五、一统江湖的接口

看起来前面小节描述的API已经够用了，然而，故事并未结束。经过前面关于调度接口的讨论，基本上我们对调度器的行为也已经有了了解：调度器就是按照优先级（指rt priority）来工作，优先级高的永远是优先调度。范围落在[1,99]的rt priority是实时进程，而rt priority等于0的是普通进程。对于普通进程，调度器还要根据nice value（这个也曾经被称为优先级，不要和rt priority弄混了）来进行调整。用户空间的进程可以通过各种前面描述的接口API来修改调度策略、nice value以及rt priority。一切看上去已经完美，CFS类型的调度器处理普通的运算密集形（例如编译内核）和用户交互形的应用（例如vi编辑文件）。如果有应用有实时需求，可以考虑让rt类型的调度器来运筹帷幄。但是，如何混合了一些realtime的应用以及有一些timing要求的应用的时候，SCHED\_FIFO和SCHED\_RR并不能解决问题，因为在这种调度策略下，高优先级的任务会永远的delay低优先级的任务，如果低优先级的任务有一些timing的需求，这时候，你根本控制不了调度延迟时间。

为了解决上一节中描述的问题，一类新的进程被定义出来，这类进程的优先级比实时进程和普通进程的优先级都要高，这类进行有自己的特点，参考下图：

[![deadline](/content/uploadfile/201703/fb0b9a063cdff9803954f28276bff6bb20170310105036.gif "deadline")](/content/uploadfile/201703/5d416ba5e672e51561cb36cbf80ed9b320170310105036.gif)

这类进程的特点就是每隔固定的周期都会起来干活，需要一定的时间来处理事务。这类进程很牛，一上来就告诉调度器，我可是有点脾气的进程，和其他的那些妖艳的进程不一样的，我每隔一段时间（period）你就得固定分配给我一定的cpu资源（computer time），当然，分配的cpu time必须在该周期内执行完毕，因此就有deadline的概念。为了应对这种需求，3.14内核引入了一类新的进程叫做deadline进程，这类进程的调度策略是SCHED\_DEADLINE。调度器对这类进程也会高看一眼，每当一个周期的开始时间到来的时候（也就是该deadline进程被唤醒的时间），调度器要优先处理这个deadline进程对cpu timer的需求，并且在某个指定的deadline时间内调度该进程执行。执行了指定的cpu time后，可以考虑调度走该进行，不过，当下一个周期到来的时候，调度器仍然要奋不顾身的在deadline时间内，再次调度该deadline进程执行。

虽然deadline进程优先级高于其他两类进程，但是用“优先级”来描述这类进程当然是不合理的，应该使用下面的三个参数来描述：

（1）周期时间（上图中的period）

（2）deadline时间（上图中的relative deadline）

（3）一次调度周期内分配多少的cpu时间（上图中的comp. time）

至此，估计您也已经发现，前面描述的接口其实都是不适合设定这些参数的，因此，GNU/linux操作系统中增加了下面的接口API：

> #include <sched.h>
>
> int sched\_setattr(pid\_t pid, const struct sched\_attr \*attr, unsigned int flags);   
> int sched\_getattr(pid\_t pid, const struct sched\_attr \*attr, unsigned int size, unsigned int flags);

attr这个参数的数据类型是struct sched\_attr，这个数据结构囊括了一切你想要的关于调度的控制参数：policy，nice value，rt priority，period，deadline等等。用这个接口可以完成所有前面几个小节描述API能完成的任务，唯一的不好的地方就是这个接口是linux特有的，不是posix标准，是否应用这个接口就是见仁见智了。更细节的知识这里就不描述了，大家还是参考man page好了。

六、其他

上面描述的接口API都是和调度器参数相关，其实Linux调度器还有两类接口。一个是sched\_getaffinity和sched\_setaffinity，用于操作一个线程的CPU affinity。另外一个接口是sched\_yield，该接口可以让出CPU资源，让Linux调度器选择一个合适的线程执行。这些接口很简单，大家仔细学习就OK了。

参考文档：

1、POSIX标准2008

2、linux下的各种man page

3、linux 4.4.6内核源代码

*原创文章，转发请注明出处。蜗窝科技*
