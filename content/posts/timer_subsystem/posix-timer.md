---
title: "Linux时间子系统之（六）：POSIX timer"
date: 2015-01-22T18:12:26+08:00
url: "/timer_subsystem/posix-timer.html"
gid: "141"
emlog_type: "blog"
summary: "在 用户空间接口函数文档 中， 我们描述了和POSIX timer相关的操作，主要包括创建一个timer、设定timer、获取timer的状态、获取timer overrun的信息、删除timer。本文将沿着这些用户空间的接口定义来看看内核态的实现。虽然POSIX timer可以基于各种不同的clock创建，本文主要描述real time clock相关的timer。 本文第二章描述了POSIX "
author: "linuxer"
category: "时间子系统"
category_alias: "timer_subsystem"
tags: ["timer", "POSIX"]
views: 34171
comment_count: 15
aliases:
  - "/timer_subsystem/141.html"
  - "/141.html"
---

一、前言

在[用户空间接口函数文档](/timer_subsystem/timer_subsystem_userspace.html)中，我们描述了和POSIX timer相关的操作，主要包括创建一个timer、设定timer、获取timer的状态、获取timer overrun的信息、删除timer。本文将沿着这些用户空间的接口定义来看看内核态的实现。虽然POSIX timer可以基于各种不同的clock创建，本文主要描述real time clock相关的timer。

本文第二章描述了POSIX timer的基本原理，第三章描述系统调用的具体实现，第四章主要讲real time clock的timer callback函数的实现，第五章介绍了timer超期后，内核如何处理信号。

二、基本概念和工作原理

1、如何标识POSIX timer

POSIX.1b interval timer（后面的文章中简称POSIX timer）是用来替代传统的interval timer的，posix timer一个重要的改进是进程可以创建更多（而不是3个）timer，既然可以创建多个timer，那么就存在标识问题，我们用timer ID来标识一个具体的posix timer。这个timer ID也作为一个handler参数在用户空间和内核空间之间传递。

posix timer是一种资源，它隶属于某一个进程，。对于kernel，我们会用timer ID来标识一个POSIX timer，而这个ID是由进程自己管理和分配的。在进程控制块（struct task\_struct ）中有一个struct signal\_struct \*signal的成员，用来管理和signal相关的控制数据。timer的处理和信号的发送是有关系的，因此也放到该数据结构中：

> ……   
> int posix\_timer\_id;   
> ……

一个进程在fork的时候，posix\_timer\_id会被设定为0，因此，对于一个进程而言，其timer ID从0开始分配，随后会依次加一，达到最大值后会从0开始。由此可见，timer ID不是一个全局唯一标识符，只是能保证在一个进程内，其ID是唯一的。实际timer ID的分配算法可以参考posix\_timer\_add函数，如下：

> static int posix\_timer\_add(struct k\_itimer \*timer)   
> {   
> struct signal\_struct \*sig = current->signal;   
> int first\_free\_id = sig->posix\_timer\_id;－－－－－－－－－－－－－－－－（1）   
> struct hlist\_head \*head;   
> int ret = -ENOENT;
>
> do {－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－（2）   
> spin\_lock(&hash\_lock);   
> head = &posix\_timers\_hashtable[hash(sig, sig->posix\_timer\_id)];－－－－（3）   
> if (!\_\_posix\_timers\_find(head, sig, sig->posix\_timer\_id)) {－－－－－－－－（4）   
> hlist\_add\_head\_rcu(&timer->t\_hash, head);   
> ret = sig->posix\_timer\_id;   
> }   
> if (++sig->posix\_timer\_id < 0)－－－－－－－－－－－－－－－－－－－－（5）   
> sig->posix\_timer\_id = 0;   
> if ((sig->posix\_timer\_id == first\_free\_id) && (ret == -ENOENT))－－－－－－（6）   
> ret = -EAGAIN;   
> spin\_unlock(&hash\_lock);   
> } while (ret == -ENOENT);   
> return ret;   
> }

（1）sig->posix\_timer\_id中记录了上一次分配的ID+1，该值被认为是下一个可以使用的free ID（当然，这个假设不一定成立，但是有很大的机会），也就是本次scan free timer ID的起点位置。

（2）do while是一个循环过程，如果选定的timer ID不是free的，我们还需要++sig->posix\_timer\_id，以便看看下一个timer ID是否是free的，这个过程不断的循环执行，直到找到一个free的timer ID，或者出错退出循环。一旦找到free的timer ID，则将该posix timer插入哈希表。

（3）根据分配的timer ID和该进程的signal descriptor的地址，找到该posix timer的hash链表头

（4）看看该进程中是否已经有了该timer ID的posix timer存在，如果没有，那么timer ID分配完成

（5）否则，看看下一个timer ID的情况。如果溢出（超过了INT\_MAX），那么从0开始搜索

（6）如果scan了一圈还是没有找到free timer ID，那么就出错返回。

2、如何组织POSIX timer

> static DEFINE\_HASHTABLE(posix\_timers\_hashtable, 9);   
> static DEFINE\_SPINLOCK(hash\_lock);

随着系统启动和运行，各个进程会不断的创建属于自己的POSIX timer，这些timer被放到了一个全局的hash表中，也就是posix\_timers\_hashtable。该table共计有512个入口，每个入口都是一个POSIX timer链表头的指针。每一个系统中的POSIX timer都会根据其hash key放入到其中一个入口中（挂入链表）。具体hash key的计算方法是：

> static int hash(struct signal\_struct \*sig, unsigned int nr)   
> {   
> return hash\_32(hash32\_ptr(sig) ^ nr, HASH\_BITS(posix\_timers\_hashtable));   
> }

计算key考虑的factor包括timer ID值和进程signal descriptor的地址。

hash\_lock是包含全局POSIX timer的锁，每次访问该资源的时候需要使用该锁进行保护。

除了作为一个全局资源来管理的hash table，每个进程也会管理自己分配和释放的timer资源，当然，这也是通过链表进行管理的，链表头在该进程signal descriptor的posix\_timers成员中：

> ……   
> struct list\_head posix\_timers;   
> ……

一旦进程创建了一个timer，那么就会挂入posix\_timers的链表中。

3、如何抽象POSIX timer

在内核中用struct k\_itimer 来描述一个POSIX timer：

> struct k\_itimer {   
> struct list\_head list; －－－－－－－－－－－－－－－－－－－－－－－－－－（1）   
> struct hlist\_node t\_hash;   
> spinlock\_t it\_lock; －－－－－保护本数据结构的spin lock   
> clockid\_t it\_clock;－－－－－－－－－－－－－－－－－－－－－－－－－－－－（2）   
> timer\_t it\_id;   
> int it\_overrun; －－－－－－－－－－－－－－－－－－－－－－－－－－－－－（3）   
> int it\_overrun\_last;   
> int it\_requeue\_pending; －－－－－－－－－－－－－－－－－－－－－－－－－（4）   
> #define REQUEUE\_PENDING 1   
> int it\_sigev\_notify; －－－－－－－－－－－－－－－－－－－－－－－－－－－－（5）   
> struct signal\_struct \*it\_signal; －－－－该timer对应的signal descriptor   
> union { －－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－（6）   
> struct pid \*it\_pid; /\* pid of process to send signal to \*/   
> struct task\_struct \*it\_process; /\* for clock\_nanosleep \*/   
> };   
> struct sigqueue \*sigq; －－－超期后，该sigquue成员会挂入signal pending队列   
> union { －－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－（7）   
> struct {   
> struct hrtimer timer;   
> ktime\_t interval;   
> } real;   
> struct cpu\_timer\_list cpu;   
> struct {   
> unsigned int clock;   
> unsigned int node;   
> unsigned long incr;   
> unsigned long expires;   
> } mmtimer;   
> struct {   
> struct alarm alarmtimer;   
> ktime\_t interval;   
> } alarm;   
> struct rcu\_head rcu;   
> } it;   
> };

（1）这两个成员都是和POSIX timer的组织有关。t\_hash是链接入全局hash table的节点，而list成员是和进程管理自己创建和释放timer的链表相关。

（2）这两个成员描述了POSIX timer的基本信息的。任何一个timer都是基于clock而构建的，it\_clock说明该timer是以系统中哪一个clock为标准来计算超时时间。it\_id描述了该timer的ID，在一个进程中唯一标识该timer。

（3）理解这两个成员首先对timer overrun的概念要理解。对overrun的解释我们可以用信号异步通知的例子来描述（创建进程执行callback函数也是一样的）。假设我们当一个POSIX timer超期后，会发送信号给进程，但是也有可能该信号当前被mask而导致signal handler不会调度执行（当然也有其他的场景导致overrun，这里就不描述了）。这样，我们当然想知道这种timer的overrun的次数。假设一个timer设定超期时间是1秒，那当timer超期后，会产生一个pending的signal，但是由于种种原因，在3秒后，信号被进程捕获到，调用signal handler，这时候overrun的次数就是2次。用户空间可以通过timer\_getoverrun来获取这个overrun的次数。

根据POSIX标准，当信号被递交给进程后，timer\_getoverrun才会返回该timer ID的overrun count，因此在kernel中需要两个成员，只有信号还没有递交给进程，it\_overrun就会不断的累积，一旦完成递交，it\_overrun会保存在it\_overrun\_last成员中，而自己会被清除，准备进行下一次overrun count的计数。因此，实际上timer\_getoverrun函数实际上是获取it\_overrun\_last的数据，代码如下：

> SYSCALL\_DEFINE1(timer\_getoverrun, timer\_t, timer\_id)   
> {   
> ……
>
> overrun = timr->it\_overrun\_last;   
> ……
>
> return overrun;   
> }

（4）it\_requeue\_pending标识了该timer对应信号挂入signal pending的状态。该flag的LSB bit标识该signal已经挂入signal pending队列，其他的bit作为信号的私有数据。下面的代码会更详细的描述。

（5）it\_sigev\_notify成员说明了timer超期后如何异步通知该进程（线程）。定义如下：

> #define SIGEV\_SIGNAL 0 －－－－－使用向进程发送信号的方式来通知   
> #define SIGEV\_NONE 1 －－－－－－没有异步通知事件，用户空间的程序用轮询的方法   
> #define SIGEV\_THREAD 2 －－－－异步通知的方式是创建一个新线程来执行callback函数   
> #define SIGEV\_THREAD\_ID 4 －－－－－使用向指定线程发送信号的方式来通知

（6）这个成员用来标识进程。

（7）it这个成员是一个union类型的，用于描述和timer interval相关的信息，不同类型的timer选择使用不同的成员数据。alarm是和alarm timer相关的成员，具体可以参考alarm timer的文档。（mmtimer不知道用在什么场合，可能和Multimedia Timer相关）。real用于real time clock的场景。real time clock的timer是构建在高精度timer上的（timer成员），而interval则描述该timer的mode，如果是one shot类型的，interval等于0，否则interval描述周期性触发timer的时间间隔。更详细的内容会在本文后面的小节中描述。

三、和POSIX timer相关的系统调用

1、创建timer的系统调用。具体代码如下：

> SYSCALL\_DEFINE3(timer\_create, const clockid\_t, which\_clock,   
> struct sigevent \_\_user \*, timer\_event\_spec,   
> timer\_t \_\_user \*, created\_timer\_id)   
> {   
> struct k\_clock \*kc = clockid\_to\_kclock(which\_clock);－－根据clock ID获取内核中的struct k\_clock   
> struct k\_itimer \*new\_timer;   
> int error, new\_timer\_id;   
> sigevent\_t event;   
> int it\_id\_set = IT\_ID\_NOT\_SET;
>
> new\_timer = alloc\_posix\_timer();－－－－－分配一个POSIX timer，所有成员被初始化为0
>
> spin\_lock\_init(&new\_timer->it\_lock);   
> new\_timer\_id = posix\_timer\_add(new\_timer);－－－－－－－－－－－（1）
>
> it\_id\_set = IT\_ID\_SET;   
> new\_timer->it\_id = (timer\_t) new\_timer\_id;   
> new\_timer->it\_clock = which\_clock;   
> new\_timer->it\_overrun = -1; －－－－－－－－－－－－－－－－－－－（2）
>
> if (timer\_event\_spec) {   
> if (copy\_from\_user(&event, timer\_event\_spec, sizeof (event))) {－－－－－拷贝用户空间的参数   
> error = -EFAULT;   
> goto out;   
> }   
> rcu\_read\_lock();   
> new\_timer->it\_pid = get\_pid(good\_sigevent(&event));－－－－－－－－（3）   
> rcu\_read\_unlock();   
> } else {   
> event.sigev\_notify = SIGEV\_SIGNAL;   
> event.sigev\_signo = SIGALRM;   
> event.sigev\_value.sival\_int = new\_timer->it\_id;   
> new\_timer->it\_pid = get\_pid(task\_tgid(current));－－－－－－－－－－（4）   
> }
>
> new\_timer->it\_sigev\_notify = event.sigev\_notify;   
> new\_timer->sigq->info.si\_signo = event.sigev\_signo; －－信号ID   
> new\_timer->sigq->info.si\_value = event.sigev\_value;   
> new\_timer->sigq->info.si\_tid = new\_timer->it\_id; －－－信号发送的目的地线程ID   
> new\_timer->sigq->info.si\_code = SI\_TIMER; －－－－－－－－－－－－－（5）
>
> if (copy\_to\_user(created\_timer\_id,   
> &new\_timer\_id, sizeof (new\_timer\_id))) {－－－－－－－－－－－－－（6）   
> error = -EFAULT;   
> goto out;   
> }
>
> error = kc->timer\_create(new\_timer);－－－－－－调用具体clock的create timer函数
>
> spin\_lock\_irq(¤t->sighand->siglock);   
> new\_timer->it\_signal = current->signal;   
> list\_add(&new\_timer->list, ¤t->signal->posix\_timers);－－－－－－－（7）   
> spin\_unlock\_irq(¤t->sighand->siglock);
>
> return 0;   
> }

（1）将该timer加入到全局的哈希表中。当然，在加入之前，要分配一个timer ID，内核要确保该timer ID是在本进程内能唯一标识该timer。

（2）初始化该posix timer，设定timer ID，clock ID以及overrun的值。it\_id\_set这个变量主要用于出错处理，如果其值等于IT\_ID\_SET，说明已经完成插入全局的哈希表的操作，那么其后的出错处理要有从全局的哈希表中摘除该timer的操作（注意：上面的代码省略了出错处理，有兴趣的读者可以自行阅读）。

（3）good\_sigevent这个函数主要是用来进行参数检查。用户空间的程序可以通过sigevent\_t的数据结构来控制timer超期之后的行为。例如可以向某一个指定的线程（不是进程）发送信号（sigev\_notify设定SIGEV\_THREAD\_ID并且设定SIGEV\_SIGNAL），当然这时候要传递thread ID的信息。内核会根据这个thread ID来寻找对应的struct task\_struct，如果找不到，那么说明用户空间传递的参数有问题。如果该thread ID对应的struct task\_struct的确存在，那么还需要该thread ID对应的thread和当前thread属于同一个进程。此外，一旦程序打算用signal通知的方式来进行timer超期通知，那么传入的sigev\_signo参数必须是一个有效的signal ID。如果这些检查通过，那么good\_sigevent返回适当的pid信息。这里有两种场景，一种是指定thread ID，另外一种是发送给当前进程（实际上是返回当前的线程组leader）

（4）如果用户空间的程序没有指定sigevent\_t的参数，那么内核的缺省行为是发送SIGALRM给调用线程所属的线程组leader。

（5）初始化信号发送相关的数据结构。SI\_TIMER用来标识该信号是由于posix timer而产生的。

（6）将分配的timer ID 拷贝回用户空间

（7）建立posix timer和当前进程signal descriptor的关系（所有线程共享一个signal descriptor）

2、获取一个posix timer剩余时间的系统调用，代码如下：

> SYSCALL\_DEFINE2(timer\_gettime, timer\_t, timer\_id,   
> struct itimerspec \_\_user \*, setting)   
> {   
> struct itimerspec cur\_setting;   
> struct k\_itimer \*timr;   
> struct k\_clock \*kc;   
> unsigned long flags;   
> int ret = 0;
>
> timr = lock\_timer(timer\_id, &flags);－－－－－－－－根据timer ID找到对应的posix timer
>
> kc = clockid\_to\_kclock(timr->it\_clock);－－－－－－根据clock ID获取内核中的struct k\_clock
>
> if (WARN\_ON\_ONCE(!kc || !kc->timer\_get))   
> ret = -EINVAL;   
> else   
> kc->timer\_get(timr, &cur\_setting); －－－－－－调用具体clock的get timer函数
>
> unlock\_timer(timr, flags);
>
> if (!ret && copy\_to\_user(setting, &cur\_setting, sizeof (cur\_setting))) －－将结果copy到用户空间   
> return -EFAULT;
>
> return ret;   
> }

3、timer\_getoverrun、timer\_settime和timer\_delete

这三个系统调用都非常简单，这里就不细述了，有兴趣的读者可以自行阅读。

四、real time clock的timer callback函数

对于real time base的那些clock（CLOCK\_REALTIME、CLOCK\_MONOTONIC等），其timer相关的函数都是构建在一个高精度timer的基础上，这个高精度timer就是posix timer中的it.real.timer成员。

1、common\_timer\_create，代码如下：

> static int common\_timer\_create(struct k\_itimer \*new\_timer)   
> {   
> hrtimer\_init(&new\_timer->it.real.timer, new\_timer->it\_clock, 0);   
> return 0;   
> }

代码很简单，就是初始化了一个高精度timer而已。具体高精度timer的内容可以参考本站其他文档。

2、common\_timer\_set，代码如下：

> common\_timer\_set(struct k\_itimer \*timr, int flags,   
> struct itimerspec \*new\_setting, struct itimerspec \*old\_setting)   
> {   
> struct hrtimer \*timer = &timr->it.real.timer;－－－获取该posix timer对应的高精度timer   
> enum hrtimer\_mode mode;
>
> if (old\_setting)   
> common\_timer\_get(timr, old\_setting); －－－－获取旧的timer设定，参考下节描述
>
> timr->it.real.interval.tv64 = 0; －－－－－－－初始化interval设定   
> if (hrtimer\_try\_to\_cancel(timer) < 0)－－－－马上就要进行新的设定了，当然要停掉该高精度timer   
> return TIMER\_RETRY;
>
> timr->it\_requeue\_pending = (timr->it\_requeue\_pending + 2) &   
> ~REQUEUE\_PENDING;   
> timr->it\_overrun\_last = 0; －－－－－－－－－－－－－－－－－－－－－－－－－－－－（1）
>
> if (!new\_setting->it\_value.tv\_sec && !new\_setting->it\_value.tv\_nsec)   
> return 0; －－－－如果新设定的时间值等于0的话，那么该函数仅仅是停掉timer并获取old value。
>
> mode = flags & TIMER\_ABSTIME ? HRTIMER\_MODE\_ABS : HRTIMER\_MODE\_REL; －－（2）   
> hrtimer\_init(&timr->it.real.timer, timr->it\_clock, mode);   
> timr->it.real.timer.function = posix\_timer\_fn; －－－－－高精度timer的mode，callback函数设定
>
> hrtimer\_set\_expires(timer, timespec\_to\_ktime(new\_setting->it\_value)); －－超期时间设定
>
> timr->it.real.interval = timespec\_to\_ktime(new\_setting->it\_interval); －－－－－－－－－－（3）
>
> if (((timr->it\_sigev\_notify & ~SIGEV\_THREAD\_ID) == SIGEV\_NONE)) { －－－－－－－－（4）   
> if (mode == HRTIMER\_MODE\_REL) {   
> hrtimer\_add\_expires(timer, timer->base->get\_time());   
> }   
> return 0;   
> }
>
> hrtimer\_start\_expires(timer, mode); －－－－启动高精度timer   
> return 0;   
> }

（1）it\_overrun\_last实际上是和timer\_getoverrun的调用有关。在一个timer触发后到异步通知完成之间可能会产生overrun，但是，一旦重新调用timer\_settime之后，上次的overrun count要被清除。it\_requeue\_pending状态flag中的信号私有数据加一（这个私有数据是[31:1]，因此代码中加2），并且清除pending flag。

（2）这里的代码都是对该posix timer对应的高精度timer进行各种设定。该timer的callback函数会在下一章分析

（3）设置interval的值，通过该值可以设定周期性timer，用户空间传入的参数是timespec，需转换成ktime的时间格式

（4）对于轮询类型的posix timer，我们并不会真正启动该timer（插入到高精度timer的红黑树中），而是仅仅为那些设定相对事件的timer配置正确的超期时间值。

3、common\_timer\_get，代码如下：

> static void common\_timer\_get(struct k\_itimer \*timr, struct itimerspec \*cur\_setting)   
> {   
> ktime\_t now, remaining, iv;   
> struct hrtimer \*timer = &timr->it.real.timer;
>
> memset(cur\_setting, 0, sizeof(struct itimerspec));
>
> iv = timr->it.real.interval; －－－获取该posix timer对应的timer period值
>
> if (iv.tv64)－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－－（1）   
> cur\_setting->it\_interval = ktime\_to\_timespec(iv);－－－interval timer需返回timer period   
> else if (!hrtimer\_active(timer) &&   
> (timr->it\_sigev\_notify & ~SIGEV\_THREAD\_ID) != SIGEV\_NONE)－－－－－－－（2）   
> return;
>
> now = timer->base->get\_time(); －－－－－－－－－－－－－－－－－－－－－－－（3）
>
> if (iv.tv64 && (timr->it\_requeue\_pending & REQUEUE\_PENDING ||   
> (timr->it\_sigev\_notify & ~SIGEV\_THREAD\_ID) == SIGEV\_NONE))   
> timr->it\_overrun += (unsigned int) hrtimer\_forward(timer, now, iv); －－－－－－－－（4）
>
> remaining = ktime\_sub(hrtimer\_get\_expires(timer), now); －－－计算剩余时间   
> if (remaining.tv64 <= 0) { －－已经超期   
> if ((timr->it\_sigev\_notify & ~SIGEV\_THREAD\_ID) != SIGEV\_NONE)   
> cur\_setting->it\_value.tv\_nsec = 1; －－－－－－－－－－－－－－－－－－－－（5）   
> } else   
> cur\_setting->it\_value = ktime\_to\_timespec(remaining); －－－返回剩余时间信息   
> }

（1）posix timer的时间设定用struct itimerspec表示：

> struct itimerspec {   
> struct timespec it\_interval; /\* timer period \*/   
> struct timespec it\_value; /\* timer expiration \*/   
> };

如果it\_interval等于0的话，那么说明该posix timer是一个one shot类型的timer。如果非零的话，则说明该timer是一个periodic timer（或者称之为interval timer），it\_interval定义了周期性触发的时间值。这个timer period值对应内核struct k\_itimer中的it.real.interval成员。

（2）如果是one shot类型的timer，it\_interval返回0值就OK了，我们只需要设定it\_value值。对于通过信号进行异步通知的posix timer，如果对应的高精度timer已经不是active状态了，那么it\_value值也是0，表示该timer已经触发了。

（3）获取当前时间点的值。不论timer当初是如何设定的：相对或者绝对，it\_value总是返回相对于当前时间点的值，因此这里需要获取当前时间点的值。

（4）对于一个周期性触发的timer，并且设定SIGEV\_NONE，实际上，该timer是不会触发的，都是用户程序自己调用timer\_gettime来轮询情况，因此在get time函数中处理超期后，再次设定高精度timer的任务，同时计算overrun次数。

如果periodic timer设定信号异步通知的方式，那么在信号pending到信号投递到进程这段时间内，虽然由于各种情况可能导致这段时间很长，按理periodic timer应该多次触发，但是实际上，信号只有在投递到进程后才会再次restart高精度timer，因此在信号pending期间，如果用户调用了timer\_gettime，也需要自己处理timer的超期以及overrun。

（5）TODO。

4、common\_timer\_del。比较简单，不再赘述。

五、和posix timer相关的信号处理

1、发送什么信号？发向哪一个进程或者线程？

用户空间的程序可以通过timer\_create函数来创建timer，在创建timer的时候就设定了异步通知的方式（SIGEV\_SIGNAL、SIGEV\_NONE和SIGEV\_THREAD），SIGEV\_NONE方式比较简单，没有异步通知，用户空间的程序自己需要调用timer\_gettime来轮询是否超期。SIGEV\_THREAD则是创建一个线程来执行callback函数。我们这一章的场景主要描述的就是设定为SIGEV\_SIGNAL方式，也就是timer超期后，发送信号来异步通知。缺省是发送给创建timer的进程，当然，也可以设定SIGEV\_THREAD\_ID的标识，发给一个该进程内的特定的线程。

一个指定进程的timer超期后，产生的信号会挂入该进程（线程）pending队列，需要注意的是：在任意的时刻，特定timer的信号只会挂入一次，也就是说，该信号产生到该信号被投递到进程之间，如果timer又一次超期触发了，这时候，signal pending队列不会再次挂入信号（即便该signal是一个real-time signal），只会增加overrun的次数。

2、信号的产生

在set timer函数中，内核会设定高精度timer的超期回调函数为posix\_timer\_fn，代码如下：

> static enum hrtimer\_restart posix\_timer\_fn(struct hrtimer \*timer)   
> {   
> struct k\_itimer \*timr;   
> unsigned long flags;   
> int si\_private = 0;   
> enum hrtimer\_restart ret = HRTIMER\_NORESTART; －－－－－－－－－－－（1）
>
> timr = container\_of(timer, struct k\_itimer, it.real.timer);－－－－－－－－－－－（2）   
> spin\_lock\_irqsave(&timr->it\_lock, flags);
>
> if (timr->it.real.interval.tv64 != 0)   
> si\_private = ++timr->it\_requeue\_pending; －－－－－－－－－－－－－－－（3）
>
> if (posix\_timer\_event(timr, si\_private)) { －－－－－－－－－－－－－－－－－（4）   
> 如果该signal的handler设定是ignor，那么需要对interval类型的timer做特别处理   
> }   
> }
>
> unlock\_timer(timr, flags);   
> return ret;   
> }

（1）高精度timer的超期callback函数的返回值标识了是否需要再次将该timer挂入队列，以便可以再次触发timer。对于one shot类型的，需要返回HRTIMER\_NORESTART，对于periodic timer，需要返回HRTIMER\_RESTART。缺省设定不再次start该timer。

（2）POSIX timer对应的高精度timer是嵌入到k\_itimer数据结构中的，通过container\_of可以获取该高精度timer对应的那个k\_itimer数据。

（3）对于one shot类型的timer，不存在signal requeue的问题。对于周期性timer，有可能会有overrun的问题，这时候，需要传递一个signal的私有数据，以便在queue signal的时候进行标识。++timr->it\_requeue\_pending用来标记该timer处于pending状态（加一就是将LSB设定为1）

（4）具体将信号挂入进程（线程）signal pending队列的操作在posix\_timer\_event函数中，该函数会调用send\_sigqueue函数进行具体操作。如下：

> int send\_sigqueue(struct sigqueue \*q, struct task\_struct \*t, int group)   
> {……
>
> ret = 0;   
> if (unlikely(!list\_empty(&q->list))) {－－－－－－－－是否已经挂入signal pending队列？   
> q->info.si\_overrun++;－－－－－－－－－－－－如果是，那么增加overrun counter就OK了   
> return ret;   
> }   
> q->info.si\_overrun = 0; －－－－－－首次挂入signal pending队列，初始化overrun counter等于0   
> pending = group ? &t->signal->shared\_pending : &t->pending;－挂入进程的还是线程的pending队列   
> list\_add\_tail(&q->list, &pending->list);－－－－挂入pending队列   
> sigaddset(&pending->signal, sig);－－－－－－设定具体哪一个signal pending   
> complete\_signal(sig, t, group);－－－－－－－设定TIF\_SIGPENDING标记   
> ……   
> }

如果信号已经正确的产生了，挂入进程或者线程的signal pending队列（也有可能是仅仅增加overrun的计数），或者处理过程中发生了错误，posix\_timer\_event返回False，这时候整个处理就结束了。如果返回TRUE，说明该signal被进程ignor了。这时候需要一些特殊的处理。

相信大家已经注意到了，default的情况下，该高精度timer的callback返回HRTIMER\_NORESTART，即便是periodic timer也是如此，难道periodic timer不需要restart高精度timer吗？当然需要，只不过不是在这里，在投递信号的时候会处理的，具体可以参考dequeue\_signal的处理。然而，如果一个periodic timer的信号处理是ignor类型的，那么信号是不会挂入pending队列的，这时候不会有信号的投递，不会调用dequeue\_signal，这时候则需要在这个callback函数中处理的。这时候会设定下一个超期时间，并返回HRTIMER\_RESTART，让高精度timer有机会重新挂入高精度timer的红黑树中。

3、信号投递到进程

timer超期后会产生一个信号（配置了SIGEV\_SIGNAL），这个信号虽然产生了，但是具体在什么时间点被投递到进程并执行signal处理函数呢？在[ARM中断处理过程文档](/irq_subsystem/irq_handler.html)中，我们给出了一个场景（另外一个场景是系统调用返回用户空间，这里略过不表，思路是类似的），在返回用户空间之前，中断处理代码会检查struct thread\_info中的flag标记，看看是否有\_TIF\_WORK\_MASK的设定：

> #define \_TIF\_WORK\_MASK (\_TIF\_NEED\_RESCHED | \_TIF\_SIGPENDING | \_TIF\_NOTIFY\_RESUME)

如果任何一个bit有设定，那么就会调用do\_work\_pending来处理，如果设定了\_TIF\_SIGPENDING，那么就调用do\_signal来处理信号，属于当前进程的pending signal会被一一处理，首先调用dequeue\_signal，从队列中取出信号，然后调用signal handler执行。相关的dequeue\_signal代码如下：

> int dequeue\_signal(struct task\_struct \*tsk, sigset\_t \*mask, siginfo\_t \*info)   
> {……   
> if ((info->si\_code & \_\_SI\_MASK) == \_\_SI\_TIMER && info->si\_sys\_private) {   
> spin\_unlock(&tsk->sighand->siglock);   
> do\_schedule\_next\_timer(info);   
> spin\_lock(&tsk->sighand->siglock);   
> }   
> return signr;   
> }

如果你想通过发生信号的方式进行异步通知，那么必须要设定si\_code为SI\_TIMER。对于real time的clock，do\_schedule\_next\_timer函数会调用schedule\_next\_timer来处理periodic timer的restart：

> static void schedule\_next\_timer(struct k\_itimer \*timr)   
> {   
> struct hrtimer \*timer = &timr->it.real.timer;
>
> if (timr->it.real.interval.tv64 == 0)－－－one shot类型的，直接退出   
> return;
>
> timr->it\_overrun += (unsigned int) hrtimer\_forward(timer,－－－设定下次超期时间并计算overrun次数   
> timer->base->get\_time(),   
> timr->it.real.interval);
>
> timr->it\_overrun\_last = timr->it\_overrun;－－－保存该timer的overrun次数   
> timr->it\_overrun = -1;－－－－为下次初始化overrun   
> ++timr->it\_requeue\_pending;－－－－－－清除pending标记并增加信号私有数据域   
> hrtimer\_restart(timer);－－－－restart该timer   
> }

*原创文章，转发请注明出处。蜗窝科技*

[/timer_subsystem/posix-timer.html](/timer_subsystem/posix-timer.html "/timer_subsystem/posix-timer.html")
